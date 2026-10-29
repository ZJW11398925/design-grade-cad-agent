"""Deterministic SVG deliverables for the autonomous design synthesis.

Pure Python + shapely: no new core dependency, no matplotlib, no timestamps,
no random ids. Every renderer writes UTF-8 with LF newlines and returns a
small dict describing the artifact (path, bytes, sha256, bounds, entity
counts), so callers can assert determinism and coverage.

Public API
----------
``render_plan_svg(building_layout, road_layout, green_layout=None, ...)``
    Site/plan overview: building footprints, road corridors and centre lines
    coloured by class, green space (when given), site boundary, focus bbox,
    north arrow, scale bar and legend.

``render_overlay_svg(base_models, candidate_models, ...)``
    Before/after overlay: the base model in grey, the candidate in red (main
    roads) / blue (buildings), with displacement vectors and the adjusted
    main-road ids labelled. Both are drawn in the same coordinate transform.

``render_candidate_comparison_svg(candidates, ...)``
    2x2 grid of candidate mini-plans with strategy labels and key metrics
    (hard checks, displacement, main-road length, overlap).

"Models" are duck-typed. A model may be an object exposing
``building_layout`` / ``road_layout`` / ``green_layout`` attributes (the
``CandidateModels`` shape), or a dict with those keys, or a lightweight
mapping with ``roads`` / ``buildings`` entries. This keeps the renderers
usable both inside the pipeline and from a candidate directory.
"""
from __future__ import annotations

import hashlib
import html
import math
from pathlib import Path
from typing import Any, Iterable, Sequence

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
)

SVG_NS = "http://www.w3.org/2000/svg"

ROAD_COLORS = {
    "main": "#d73027",
    "branch": "#fc8d59",
    "access": "#4575b4",
    "sidewalk": "#bdbdbd",
}
ROAD_ORDER = ("main", "branch", "access", "sidewalk")
FOCUS_COLOR = "#1f78b4"
BUILDING_FILL = "#e8e8e8"
BUILDING_STROKE = "#4d4d4d"
FOCUS_BUILDING_STROKE = "#b2182b"
GREEN_FILL = "#c7e9c0"
GREEN_STROKE = "#4d9221"
BASE_FILL = "#d9d9d9"
BASE_STROKE = "#8c8c8c"
BASE_ROAD = "#969696"
AFTER_BUILDING = "#2b6cb0"
AFTER_MAIN = "#c0392b"
AFTER_OTHER = "#e67e22"
SITE_BOUNDARY_STROKE = "#111111"

SCALE_BAR_METERS = (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000)
PANEL_W, PANEL_H = 780.0, 560.0
GRID_GAP = 24.0


# ---------------------------------------------------------------------------
# small helpers
# ---------------------------------------------------------------------------


def _fmt(value: float, digits: int = 2) -> str:
    text = f"{float(value):.{digits}f}"
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _escape(value: Any) -> str:
    return html.escape(str(value), quote=True)


def _model_get(models: Any, name: str, default: Any = None) -> Any:
    if models is None:
        return default
    if isinstance(models, dict):
        return models.get(name, default)
    return getattr(models, name, default)


def _iter_polygons(geometry: Any) -> Iterable[Polygon]:
    if geometry is None:
        return
    if isinstance(geometry, Polygon):
        if not geometry.is_empty:
            yield geometry
    elif isinstance(geometry, MultiPolygon):
        for part in geometry.geoms:
            if not part.is_empty:
                yield part
    elif isinstance(geometry, GeometryCollection):
        for part in geometry.geoms:
            yield from _iter_polygons(part)


def _iter_lines(geometry: Any) -> Iterable[LineString]:
    if geometry is None:
        return
    if isinstance(geometry, LineString):
        if not geometry.is_empty:
            yield geometry
    elif isinstance(geometry, MultiLineString):
        for part in geometry.geoms:
            if not part.is_empty:
                yield part
    elif isinstance(geometry, GeometryCollection):
        for part in geometry.geoms:
            yield from _iter_lines(part)


def _ring_path(ring, transform) -> str:
    coords = [(float(x), float(y)) for x, y in ring.coords]
    if not coords:
        return ""
    first = transform(*coords[0])
    parts = [f"M {_fmt(first[0])},{_fmt(first[1])}"]
    for x, y in coords[1:]:
        sx, sy = transform(x, y)
        parts.append(f"L {_fmt(sx)},{_fmt(sy)}")
    parts.append("Z")
    return " ".join(parts)


def _polygon_path(polygon: Polygon, transform) -> str:
    parts = [_ring_path(polygon.exterior, transform)]
    for interior in polygon.interiors:
        parts.append(_ring_path(interior, transform))
    return " ".join(part for part in parts if part)


def _line_path(line: LineString, transform) -> str:
    coords = [(float(x), float(y)) for x, y in line.coords]
    if not coords:
        return ""
    first = transform(*coords[0])
    parts = [f"M {_fmt(first[0])},{_fmt(first[1])}"]
    for x, y in coords[1:]:
        sx, sy = transform(x, y)
        parts.append(f"L {_fmt(sx)},{_fmt(sy)}")
    return " ".join(parts)


def _bounds_of_items(items: Iterable[Any]) -> list[float] | None:
    minx = miny = math.inf
    maxx = maxy = -math.inf
    for item in items:
        geometry = item
        if isinstance(item, dict):
            geometry = item.get("geometry")
        if geometry is None or geometry.is_empty:
            continue
        gx0, gy0, gx1, gy1 = geometry.bounds
        minx, miny = min(minx, gx0), min(miny, gy0)
        maxx, maxy = max(maxx, gx1), max(maxy, gy1)
    if not math.isfinite(minx):
        return None
    return [minx, miny, maxx, maxy]


def _transform_for(bounds: Sequence[float], width: float, pad: float = 44.0):
    minx, miny, maxx, maxy = (float(value) for value in bounds)
    span_x = max(maxx - minx, 1e-9)
    span_y = max(maxy - miny, 1e-9)
    scale = max((width - 2 * pad) / span_x, 1e-9)
    height = pad * 2 + span_y * scale

    def transform(x: float, y: float) -> tuple[float, float]:
        return pad + (float(x) - minx) * scale, height - pad - (float(y) - miny) * scale

    return transform, {"width": width, "height": height, "scale": scale,
                       "bounds": [minx, miny, maxx, maxy], "pad": pad}


def _svg_open(width: float, height: float, title: str, background: str = "#ffffff") -> list[str]:
    return [
        f'<svg xmlns="{SVG_NS}" width="{_fmt(width)}" height="{_fmt(height)}" '
        f'viewBox="0 0 {_fmt(width)} {_fmt(height)}" '
        f'font-family="DejaVu Sans, Arial, sans-serif">',
        f"<title>{_escape(title)}</title>",
        f'<rect x="0" y="0" width="{_fmt(width)}" height="{_fmt(height)}" '
        f'fill="{background}"/>',
    ]


def _text(x: float, y: float, content: str, size: float = 13,
          fill: str = "#111111", anchor: str = "start",
          weight: str = "normal") -> str:
    return (
        f'<text x="{_fmt(x)}" y="{_fmt(y)}" font-size="{_fmt(size)}" '
        f'fill="{fill}" text-anchor="{anchor}" font-weight="{weight}">'
        f"{_escape(content)}</text>"
    )


def _line(x1: float, y1: float, x2: float, y2: float, stroke: str,
          stroke_width: float = 1.5, dash: str | None = None) -> str:
    extra = f' stroke-dasharray="{dash}"' if dash else ""
    return (
        f'<line x1="{_fmt(x1)}" y1="{_fmt(y1)}" x2="{_fmt(x2)}" y2="{_fmt(y2)}" '
        f'stroke="{stroke}" stroke-width="{_fmt(stroke_width)}"{extra}/>'
    )


def _north_arrow(x: float, y: float, size: float = 30.0) -> list[str]:
    half = size / 2.0
    return [
        f'<polygon points="{_fmt(x)},{_fmt(y - size)} {_fmt(x - half)},{_fmt(y)} '
        f'{_fmt(x + half)},{_fmt(y)}" fill="#111111"/>',
        _text(x, y + size * 0.7, "N", size=size * 0.5, anchor="middle",
              weight="bold"),
    ]


def _scale_bar(x: float, y: float, scale: float) -> list[str]:
    """A scale bar whose label is a round number of metres."""
    target_px = 150.0
    metres = SCALE_BAR_METERS[0]
    for candidate in SCALE_BAR_METERS:
        if candidate * scale <= target_px:
            metres = candidate
    length_px = metres * scale
    return [
        _line(x, y, x + length_px, y, "#111111", stroke_width=2.0),
        _line(x, y - 5, x, y + 5, "#111111", stroke_width=1.5),
        _line(x + length_px, y - 5, x + length_px, y + 5, "#111111", stroke_width=1.5),
        _text(x + length_px / 2, y - 9, f"{metres} m", size=11, anchor="middle"),
    ]


def _legend(entries: Sequence[tuple[str, str]], x: float, y: float) -> list[str]:
    parts = [_text(x, y - 10, "Legend", size=13, weight="bold")]
    cursor = y + 6
    for color, label in entries:
        parts.append(
            f'<rect x="{_fmt(x)}" y="{_fmt(cursor - 9)}" width="14" height="10" '
            f'fill="{color}" stroke="#333333" stroke-width="0.5"/>'
        )
        parts.append(_text(x + 22, cursor, label, size=12))
        cursor += 19
    return parts


def _write_svg(path: str | Path, parts: Sequence[str]) -> dict[str, Any]:
    path = Path(path)
    body = "\n".join(parts) + "\n"
    data = body.encode("utf-8")
    path.parent.mkdir(parents=True, exist_ok=True)
    # newline="\n" keeps the artifact byte-identical across platforms
    with path.open("wb") as handle:
        handle.write(data.replace(b"\r\n", b"\n"))
    return {
        "path": str(path),
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
        "line_count": body.count("\n"),
    }


# ---------------------------------------------------------------------------
# model extraction
# ---------------------------------------------------------------------------


def _road_items(models: Any) -> list[dict[str, Any]]:
    road_layout = _model_get(models, "road_layout")
    items: list[dict[str, Any]] = []
    if road_layout is not None:
        for road in getattr(road_layout, "roads", ()) or ():
            items.append(
                {
                    "edge_id": str(getattr(road, "edge_id", "")),
                    "class_name": str(getattr(road, "class_name", "main")),
                    "width_m": float(getattr(road, "width_m", 0.0)),
                    "centerline": getattr(road, "centerline", None),
                    "corridor": getattr(road, "corridor", None),
                }
            )
        return items
    for entry in _model_get(models, "roads", ()) or ():
        if isinstance(entry, dict):
            items.append(
                {
                    "edge_id": str(entry.get("edge_id", "")),
                    "class_name": str(entry.get("class_name", "main")),
                    "width_m": float(entry.get("width_m", 0.0)),
                    "centerline": entry.get("centerline"),
                    "corridor": entry.get("corridor"),
                }
            )
        else:
            items.append(
                {
                    "edge_id": str(getattr(entry, "edge_id", "")),
                    "class_name": str(getattr(entry, "class_name", "main")),
                    "width_m": float(getattr(entry, "width_m", 0.0)),
                    "centerline": getattr(entry, "centerline", None),
                    "corridor": getattr(entry, "corridor", None),
                }
            )
    return items


def _building_items(models: Any) -> list[dict[str, Any]]:
    building_layout = _model_get(models, "building_layout")
    items: list[dict[str, Any]] = []
    if building_layout is not None:
        for building in getattr(building_layout, "buildings", ()) or ():
            items.append(
                {
                    "building_id": str(getattr(building, "building_id", "")),
                    "footprint": getattr(building, "footprint", None),
                }
            )
        return items
    for entry in _model_get(models, "buildings", ()) or ():
        if isinstance(entry, dict):
            items.append(
                {
                    "building_id": str(entry.get("building_id", "")),
                    "footprint": entry.get("footprint") or entry.get("geometry"),
                }
            )
        else:
            items.append(
                {
                    "building_id": str(getattr(entry, "building_id", "")),
                    "footprint": getattr(entry, "footprint", None),
                }
            )
    return items


def _green_items(models: Any) -> list[dict[str, Any]]:
    green_layout = _model_get(models, "green_layout")
    items: list[dict[str, Any]] = []
    if green_layout is None:
        return items
    for green in getattr(green_layout, "greens", ()) or ():
        items.append(
            {
                "green_id": str(getattr(green, "green_id", "")),
                "geometry": getattr(green, "geometry", None),
                "classification": str(getattr(green, "classification", "")),
            }
        )
    return items


def _model_bounds(models: Any) -> list[float] | None:
    geometries: list[Any] = []
    for item in _building_items(models):
        geometries.append(item["footprint"])
    for item in _road_items(models):
        geometries.extend([item["corridor"], item["centerline"]])
    for item in _green_items(models):
        geometries.append(item["geometry"])
    site = _model_get(models, "site_boundary")
    focus = _model_get(models, "focus_bbox")
    if site is not None:
        geometries.append(site)
    if focus is not None:
        geometries.append(Polygon([(focus[0], focus[1]), (focus[2], focus[1]),
                                   (focus[2], focus[3]), (focus[0], focus[3])]))
    return _bounds_of_items(geometries)


# ---------------------------------------------------------------------------
# A. plan renderer
# ---------------------------------------------------------------------------


def render_plan_svg(
    building_layout: Any,
    road_layout: Any,
    green_layout: Any | None = None,
    path: str | Path = "design-preview.svg",
    title: str = "Design plan",
    width: float = 1600,
    site_boundary: Any | None = None,
    focus_bbox: Sequence[float] | None = None,
) -> dict[str, Any]:
    models = {
        "building_layout": building_layout,
        "road_layout": road_layout,
        "green_layout": green_layout,
        "site_boundary": site_boundary,
        "focus_bbox": focus_bbox,
    }
    bounds = _model_bounds(models)
    if bounds is None:
        raise ValueError("render_plan_svg: no geometry to render")
    transform, frame = _transform_for(bounds, width)
    svg_w, svg_h = frame["width"], frame["height"]

    parts = _svg_open(svg_w, svg_h, title)
    parts.append(_text(24, 28, title, size=18, weight="bold"))
    subtitle = (
        f"bounds {_fmt(bounds[0])},{_fmt(bounds[1])} .. "
        f"{_fmt(bounds[2])},{_fmt(bounds[3])} m | scale 1 m = "
        f"{_fmt(frame['scale'], 3)} px"
    )
    parts.append(_text(24, 48, subtitle, size=11, fill="#555555"))

    # site boundary
    if site_boundary is not None:
        for polygon in _iter_polygons(site_boundary):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" fill="none" '
                f'stroke="{SITE_BOUNDARY_STROKE}" stroke-width="2" '
                'stroke-dasharray="10 4"/>'
            )
    # focus bbox
    if focus_bbox is not None:
        fx0, fy0, fx1, fy1 = (float(value) for value in focus_bbox)
        ring = LineString([(fx0, fy0), (fx1, fy0), (fx1, fy1), (fx0, fy1), (fx0, fy0)])
        parts.append(
            f'<path d="{_line_path(ring, transform)}" fill="none" '
            f'stroke="{FOCUS_COLOR}" stroke-width="1.6" stroke-dasharray="8 4"/>'
        )
        x0, y0 = transform(fx0, fy1)
        parts.append(_text(x0 + 4, y0 + 14, "focus bbox", size=11,
                           fill=FOCUS_COLOR))
    # green space
    for item in _green_items(models):
        for polygon in _iter_polygons(item["geometry"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" '
                f'fill="{GREEN_FILL}" fill-opacity="0.75" '
                f'stroke="{GREEN_STROKE}" stroke-width="0.7"/>'
            )
    # roads: corridors then centre lines
    road_items = _road_items(models)
    for item in road_items:
        color = ROAD_COLORS.get(item["class_name"], "#888888")
        for polygon in _iter_polygons(item["corridor"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" fill="{color}" '
                'fill-opacity="0.35" stroke="none"/>'
            )
    for item in road_items:
        color = ROAD_COLORS.get(item["class_name"], "#555555")
        for line in _iter_lines(item["centerline"]):
            parts.append(
                f'<path d="{_line_path(line, transform)}" fill="none" '
                f'stroke="{color}" stroke-width="1.4" stroke-dasharray="6 3"/>'
            )
    # buildings
    for item in _building_items(models):
        for polygon in _iter_polygons(item["footprint"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" '
                f'fill="{BUILDING_FILL}" stroke="{BUILDING_STROKE}" '
                'stroke-width="1.1"/>'
            )
    # legend
    legend_entries = [
        (BUILDING_FILL, "Building"),
        (ROAD_COLORS["main"], "Main road"),
        (ROAD_COLORS["branch"], "Branch road"),
        (ROAD_COLORS["access"], "Access road"),
        (GREEN_FILL, "Green space"),
        ("#ffffff", "Site boundary (dashed)"),
        ("#ffffff", "Focus bbox (blue dashed)"),
    ]
    parts.extend(_legend(legend_entries, 24, svg_h - 190))
    parts.extend(_north_arrow(svg_w - 60, 90))
    parts.extend(_scale_bar(24, svg_h - 26, frame["scale"]))
    parts.append("</svg>")

    artifact = _write_svg(path, parts)
    counts = {
        "buildings": len(_building_items(models)),
        "roads": len(road_items),
        "green": len(_green_items(models)),
        "main_roads": sum(1 for item in road_items
                          if item["class_name"] == "main"),
        "centerlines": sum(len(list(_iter_lines(item["centerline"])))
                           for item in road_items),
    }
    return {**artifact, "bounds": bounds, "counts": counts,
            "scale": frame["scale"], "width": svg_w, "height": svg_h}


# ---------------------------------------------------------------------------
# B. overlay renderer
# ---------------------------------------------------------------------------


def _matching_vertices(base_line: LineString, candidate_line: LineString,
                       samples: int = 9) -> list[tuple[float, float, float, float]]:
    pairs: list[tuple[float, float, float, float]] = []
    for index in range(samples):
        fraction = index / (samples - 1)
        base_point = base_line.interpolate(fraction, normalized=True)
        candidate_point = candidate_line.interpolate(fraction, normalized=True)
        pairs.append((base_point.x, base_point.y,
                      candidate_point.x, candidate_point.y))
    return pairs


def _draw_vectors(parts: list[str], pairs: Sequence[tuple[float, float, float, float]],
                  transform, edge_id: str, max_disp: float) -> None:
    """Draw displacement arrows from before to after plus the road label."""
    for bx, by, cx, cy in pairs:
        sx1, sy1 = transform(bx, by)
        sx2, sy2 = transform(cx, cy)
        if math.hypot(sx2 - sx1, sy2 - sy1) < 0.5:
            continue
        parts.append(_line(sx1, sy1, sx2, sy2, "#6a3d9a", stroke_width=1.0,
                           dash="3 2"))
        parts.append(
            f'<polygon points="{_fmt(sx2)},{_fmt(sy2)} '
            f'{_fmt(sx2 - 5)},{_fmt(sy2 + 3)} {_fmt(sx2 - 5)},{_fmt(sy2 - 3)}" '
            'fill="#6a3d9a"/>'
        )
    anchor = pairs[0]
    ax, ay = transform(anchor[2], anchor[3])
    parts.append(_text(ax + 6, ay - 6,
                       f"{edge_id} (+{_fmt(max_disp, 2)} m)", size=11,
                       fill="#6a3d9a", weight="bold"))


def render_overlay_svg(
    base_models: Any,
    candidate_models: Any,
    path: str | Path = "design-overlay.svg",
    title: str = "Main-road alignment overlay",
    width: float = 1600,
) -> dict[str, Any]:
    base_bounds = _model_bounds(base_models)
    candidate_bounds = _model_bounds(candidate_models)
    bounds = None
    if base_bounds and candidate_bounds:
        bounds = [min(base_bounds[0], candidate_bounds[0]),
                  min(base_bounds[1], candidate_bounds[1]),
                  max(base_bounds[2], candidate_bounds[2]),
                  max(base_bounds[3], candidate_bounds[3])]
    else:
        bounds = base_bounds or candidate_bounds
    if bounds is None:
        raise ValueError("render_overlay_svg: no geometry to render")
    transform, frame = _transform_for(bounds, width)
    svg_w, svg_h = frame["width"], frame["height"]

    base_buildings = _building_items(base_models)
    candidate_buildings = _building_items(candidate_models)
    base_roads = {item["edge_id"]: item
                  for item in _road_items(base_models)}
    candidate_roads = {item["edge_id"]: item
                       for item in _road_items(candidate_models)}

    parts = _svg_open(svg_w, svg_h, title)
    parts.append(_text(24, 28, title, size=18, weight="bold"))
    parts.append(_text(24, 48,
                       "grey = before (main baseline) | red = after main road | "
                       "blue = after building", size=11, fill="#555555"))

    # before: buildings grey
    for item in base_buildings:
        for polygon in _iter_polygons(item["footprint"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" '
                f'fill="{BASE_FILL}" fill-opacity="0.9" stroke="{BASE_STROKE}" '
                'stroke-width="0.8"/>'
            )
    # before: roads grey
    for item in base_roads.values():
        for line in _iter_lines(item["centerline"]):
            parts.append(
                f'<path d="{_line_path(line, transform)}" fill="none" '
                f'stroke="{BASE_ROAD}" stroke-width="{_fmt(max(1.2, item["width_m"] * 0.18))}"/>'
            )
    # after: buildings blue outline
    for item in candidate_buildings:
        for polygon in _iter_polygons(item["footprint"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" '
                f'fill="{AFTER_BUILDING}" fill-opacity="0.08" '
                f'stroke="{AFTER_BUILDING}" stroke-width="1.3"/>'
            )
    # after: roads
    for item in candidate_roads.values():
        color = AFTER_MAIN if item["class_name"] == "main" else AFTER_OTHER
        for line in _iter_lines(item["centerline"]):
            parts.append(
                f'<path d="{_line_path(line, transform)}" fill="none" '
                f'stroke="{color}" stroke-width="{_fmt(max(1.4, item["width_m"] * 0.22))}"/>'
            )

    # alignment records (before/after overlap + the original/adjusted centre
    # lines they were derived from) drive both the fallback overlay and the
    # annotation block
    records = getattr(_model_get(candidate_models, "road_layout"),
                      "main_alignment_records", ()) or ()
    if not records:
        records = _model_get(candidate_models, "alignment_records", ()) or ()

    # displacement vectors for changed roads
    changed: list[dict[str, Any]] = []
    for edge_id in sorted(candidate_roads):
        candidate = candidate_roads[edge_id]
        base = base_roads.get(edge_id)
        if base is None:
            continue
        base_lines = list(_iter_lines(base["centerline"]))
        after_lines = list(_iter_lines(candidate["centerline"]))
        if len(base_lines) != 1 or len(after_lines) != 1:
            continue
        if list(base_lines[0].coords) == list(after_lines[0].coords):
            continue
        pairs = _matching_vertices(base_lines[0], after_lines[0])
        max_disp = max(math.hypot(cx - bx, cy - by) for bx, by, cx, cy in pairs)
        changed.append({"edge_id": edge_id,
                        "class_name": candidate["class_name"],
                        "max_displacement_m": max_disp})
        _draw_vectors(parts, pairs, transform, edge_id, max_disp)

    # Fallback: when the base and candidate road sets are identical (e.g. the
    # overlay is rendered on the committed design itself), use the alignment
    # records' original/adjusted centre lines so the adjustment is still shown.
    if not changed and records:
        for profile in records:
            original = profile.get("original_centerline")
            adjusted = profile.get("adjusted_centerline")
            if not original or not adjusted:
                continue
            base_line = LineString([(float(x), float(y)) for x, y in original])
            after_line = LineString([(float(x), float(y)) for x, y in adjusted])
            parts.append(
                f'<path d="{_line_path(base_line, transform)}" fill="none" '
                f'stroke="{BASE_ROAD}" stroke-width="3" stroke-dasharray="7 4"/>'
            )
            parts.append(
                f'<path d="{_line_path(after_line, transform)}" fill="none" '
                f'stroke="{AFTER_MAIN}" stroke-width="2.4"/>'
            )
            pairs = _matching_vertices(base_line, after_line)
            max_disp = float(
                profile.get("max_displacement_m")
                or max(math.hypot(cx - bx, cy - by) for bx, by, cx, cy in pairs))
            road_id = str(profile.get("road_id", "?"))
            changed.append({"edge_id": road_id,
                            "class_name": "main",
                            "max_displacement_m": max_disp,
                            "source": "alignment_record"})
            _draw_vectors(parts, pairs, transform, road_id, max_disp)

    lines = ["Adjusted main roads:"]
    for profile in records:
        lines.append(
            f"{profile.get('road_id', '?')}: "
            f"{_fmt(profile.get('overlap_before_m2', 0.0), 3)} -> "
            f"{_fmt(profile.get('overlap_after_m2', 0.0), 3)} m2, "
            f"max disp {_fmt(profile.get('max_displacement_m', 0.0), 2)} m"
        )
    if len(lines) == 1:
        lines.append("(no alignment records in candidate models)")
    box_x = 24
    box_y = svg_h - 150
    for offset, content in enumerate(lines):
        parts.append(_text(box_x, box_y + offset * 18, content, size=12,
                           fill="#333333"))
    parts.extend(_legend([
        (BASE_STROKE, "before: building (grey)"),
        (BASE_ROAD, "before: road (grey)"),
        (AFTER_MAIN, "after: main road (red)"),
        (AFTER_BUILDING, "after: building (blue)"),
        ("#6a3d9a", "displacement vector"),
    ], svg_w - 300, svg_h - 190))
    parts.extend(_north_arrow(svg_w - 60, 90))
    parts.extend(_scale_bar(24, svg_h - 26, frame["scale"]))
    parts.append("</svg>")

    artifact = _write_svg(path, parts)
    return {**artifact, "bounds": bounds, "changed_roads": changed,
            "scale": frame["scale"], "width": svg_w, "height": svg_h}


# ---------------------------------------------------------------------------
# C. candidate comparison renderer
# ---------------------------------------------------------------------------


def _candidate_field(candidate: Any, name: str, default: Any = None) -> Any:
    return _model_get(candidate, name, default)


def _candidate_models(candidate: Any) -> Any:
    models = _candidate_field(candidate, "models")
    return models if models is not None else candidate


def _candidate_metrics(candidate: Any) -> dict[str, Any]:
    metrics = _candidate_field(candidate, "metrics") or {}
    return metrics if isinstance(metrics, dict) else {}


def _metric_text(candidate_id: str, candidate: Any) -> list[str]:
    metrics = _candidate_metrics(candidate)
    strategy = (metrics.get("strategy")
                or _candidate_field(candidate, "strategy")
                or _candidate_field(candidate, "label") or "n/a")
    hard = metrics.get("hard_pass", metrics.get("hard_checks_passed"))
    if hard is None:
        hard_text = "n/a"
    elif isinstance(hard, bool):
        hard_text = "pass" if hard else "FAIL"
    else:
        hard_text = str(hard)
    disp = metrics.get("max_displacement_m", metrics.get("displacement_m"))
    main_len = metrics.get("main_length_m", metrics.get("main_road_length_m"))
    overlap = metrics.get("road_building_overlap_m2_total",
                          metrics.get("overlap_m2", metrics.get("total_overlap_m2")))
    return [
        f"{candidate_id}  [{strategy}]",
        f"hard: {hard_text}",
        f"max disp: {_fmt(disp) if disp is not None else 'n/a'} m",
        f"main length: {_fmt(main_len) if main_len is not None else 'n/a'} m",
        f"overlap: {_fmt(overlap, 3) if overlap is not None else 'n/a'} m2",
    ]


def render_candidate_comparison_svg(
    candidates: Sequence[Any],
    path: str | Path = "design-candidate-comparison.svg",
    title: str = "Candidate comparison",
    width: float = 1600,
) -> dict[str, Any]:
    ordered = sorted(candidates, key=lambda item: str(_candidate_field(item, "candidate_id", "")))
    shown = ordered[:4]
    rows, cols = 2, 2
    panel_w = (width - GRID_GAP * (cols + 1)) / cols
    panel_h = PANEL_H
    svg_w = width
    svg_h = 80 + panel_h * rows + GRID_GAP * (rows + 1)

    parts = _svg_open(svg_w, svg_h, title)
    parts.append(_text(24, 30, title, size=18, weight="bold"))
    parts.append(_text(24, 50,
                       f"{len(ordered)} candidate(s); showing {len(shown)} in a 2x2 grid",
                       size=11, fill="#555555"))
    if len(ordered) > 4:
        parts.append(_text(24, 68, "note: only the first 4 (by candidate_id) are drawn",
                           size=11, fill="#a33"))

    for index in range(rows * cols):
        row, col = divmod(index, cols)
        x0 = GRID_GAP + col * (panel_w + GRID_GAP)
        y0 = 80 + GRID_GAP + row * (panel_h + GRID_GAP)
        parts.append(
            f'<rect x="{_fmt(x0)}" y="{_fmt(y0)}" width="{_fmt(panel_w)}" '
            f'height="{_fmt(panel_h)}" fill="#fcfcfc" stroke="#cccccc" '
            'stroke-width="1"/>'
        )
        if index >= len(shown):
            parts.append(_text(x0 + 16, y0 + 30, "(no candidate)", size=13,
                               fill="#999999"))
            continue
        candidate = shown[index]
        candidate_id = str(_candidate_field(candidate, "candidate_id", f"cand-{index}"))
        text_lines = _metric_text(candidate_id, candidate)
        parts.append(_text(x0 + 16, y0 + 26, text_lines[0], size=14,
                           weight="bold"))
        models = _candidate_models(candidate)
        detail_lines = [
            str(line) for line in
            ((_candidate_metrics(candidate).get("detail_lines")) or ())
        ][:6]
        if detail_lines:
            # Small-font supplementary lines (e.g. per-class deviation and a
            # specific terminal displacement) sit above the metric block; the
            # metric block keeps its coordinates, so a candidate without
            # detail lines renders byte-identically to the previous behaviour.
            detail_top = y0 + panel_h - 74 - len(detail_lines) * 15 - 4
            for offset, content in enumerate(detail_lines):
                parts.append(
                    _text(x0 + 16, detail_top + offset * 15, content,
                          size=10.5, fill="#455a64"))
        panel_bounds = _model_bounds(models)
        if panel_bounds is not None:
            transform, frame = _transform_for(panel_bounds, panel_w - 32, pad=20)
            dy = y0 + 60
            parts.append(f'<g transform="translate({_fmt(x0 + 16)},{_fmt(dy)})">')
            for item in _building_items(models):
                for polygon in _iter_polygons(item["footprint"]):
                    parts.append(
                        f'<path d="{_polygon_path(polygon, transform)}" '
                        f'fill="{BUILDING_FILL}" stroke="{BUILDING_STROKE}" '
                        'stroke-width="0.7"/>'
                    )
            for item in _road_items(models):
                color = ROAD_COLORS.get(item["class_name"], "#888888")
                for polygon in _iter_polygons(item["corridor"]):
                    parts.append(
                        f'<path d="{_polygon_path(polygon, transform)}" '
                        f'fill="{color}" fill-opacity="0.30" stroke="none"/>'
                    )
                for line in _iter_lines(item["centerline"]):
                    parts.append(
                        f'<path d="{_line_path(line, transform)}" fill="none" '
                        f'stroke="{color}" stroke-width="1.0"/>'
                    )
            parts.append("</g>")
        for offset, content in enumerate(text_lines[1:]):
            parts.append(_text(x0 + 16, y0 + panel_h - 74 + offset * 17,
                               content, size=12, fill="#333333"))
    parts.append("</svg>")

    artifact = _write_svg(path, parts)
    return {**artifact, "candidate_ids": [str(_candidate_field(item,
                                                               "candidate_id", ""))
                                          for item in ordered],
            "shown": len(shown), "width": svg_w, "height": svg_h}

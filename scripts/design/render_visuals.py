#!/usr/bin/env python3
"""Render the design visual deliverables (SVG always, PNG when matplotlib exists).

Reads the M4c-2 design evidence and rebuilds the design models from the same
fixtures the synthesis uses, then writes:

  * ``design-preview.svg``  — plan overview (buildings, roads, green, boundary,
    focus bbox, north arrow, scale bar, legend);
  * ``design-overlay.svg``  — before/after main-road alignment overlay with the
    adjusted road ids and displacement vectors.

The legacy raster ``design-preview.png`` is refreshed **only** when matplotlib
is importable; the script never adds a dependency and never fails when it is
missing (it prints a degrade notice and keeps the SVGs).

Usage::

    python scripts/design/render_visuals.py \
        --output-dir docs/e2e/design-synthesis-001

The output directory is explicit so callers can render into scratch during
checks without touching tracked evidence.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dgcad_design.buildings import (  # noqa: E402
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.basis import DesignBasis  # noqa: E402
from dgcad_design.green import build_green_layout  # noqa: E402
from dgcad_design.input import load_design_input  # noqa: E402
from dgcad_design.intent import build_design_intent  # noqa: E402
from dgcad_design.parking import build_parking_layout  # noqa: E402
from dgcad_design.roads import build_road_layout  # noqa: E402
from dgcad_design.visuals import (  # noqa: E402
    render_overlay_svg,
    render_plan_svg,
)
import yaml  # noqa: E402
from shapely.geometry import LineString  # noqa: E402

DEFAULT_CASE = ROOT / "docs/e2e/sketch-001"
DEFAULT_BASIS = ROOT / "fixtures/design/design-basis-001.yaml"
DEFAULT_PROFILE = ROOT / "fixtures/design/design-profile-001.yaml"
DEFAULT_EVIDENCE = ROOT / "docs/e2e/design-synthesis-001"


def build_models(case_dir: Path = DEFAULT_CASE,
                 basis_path: Path = DEFAULT_BASIS,
                 profile_path: Path = DEFAULT_PROFILE) -> dict:
    """Rebuild the design layouts exactly as ``run_design_synthesis`` does."""
    basis = DesignBasis.from_dict(
        yaml.safe_load(Path(basis_path).read_text(encoding="utf-8")))
    design_input = load_design_input(Path(case_dir), basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        design_rect,
    )
    from shapely.geometry import box
    focus_box = box(*intent.focus_bbox)
    road_layout = build_road_layout(design_input, basis, intent, building_layout)
    green_layout = build_green_layout(
        design_input, building_layout, road_layout, basis, focus_box)
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis)
    return {
        "design_input": design_input,
        "intent": intent,
        "building_layout": building_layout,
        "road_layout": road_layout,
        "green_layout": green_layout,
        "parking_layout": parking_layout,
        "site_boundary": design_input.site_boundary,
        "focus_bbox": tuple(intent.focus_bbox),
    }


def load_base_roads(roads_geojson: Path) -> dict:
    """The 'before' road set, read from committed design-roads GeoJSON."""
    payload = json.loads(Path(roads_geojson).read_text(encoding="utf-8"))
    roads = []
    for feature in payload.get("features", []):
        properties = feature.get("properties", {})
        geometry = feature.get("geometry") or {}
        if geometry.get("type") != "LineString":
            continue
        roads.append(
            {
                "edge_id": str(properties.get("edge_id", "")),
                "class_name": str(properties.get("class_name", "main")),
                "width_m": float(properties.get("width_m", 0.0)),
                "centerline": LineString(geometry["coordinates"]),
            }
        )
    return {"roads": roads}


def render_png(models: dict, path: Path, width: int = 1600) -> dict:
    """Optional raster preview. Never raises; degrades to {'status': 'unavailable'}."""
    try:
        import matplotlib  # noqa: PLC0415
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: PLC0415
        from matplotlib.patches import Polygon as MplPolygon  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return {"status": "unavailable",
                "reason": f"matplotlib not importable: {type(exc).__name__}"}
    try:
        building_layout = models["building_layout"]
        road_layout = models["road_layout"]
        fig, ax = plt.subplots(figsize=(width / 160.0, width / 160.0 * 0.62))
        for item in getattr(road_layout, "roads", ()):
            corridor = getattr(item, "corridor", None)
            if corridor is None or corridor.is_empty:
                continue
            polygons = ([corridor] if corridor.geom_type == "Polygon"
                        else list(getattr(corridor, "geoms", ())))
            for polygon in polygons:
                ax.add_patch(MplPolygon(
                    list(polygon.exterior.coords),
                    closed=True, alpha=0.28,
                    facecolor={"main": "#d73027", "branch": "#fc8d59",
                               "access": "#4575b4"}.get(
                                   getattr(item, "class_name", ""), "#888888"),
                    edgecolor="none"))
            centerline = getattr(item, "centerline", None)
            if centerline is not None and not centerline.is_empty:
                coords = list(centerline.coords)
                ax.plot([x for x, _ in coords], [y for _, y in coords],
                        color="#333333", linewidth=0.7)
        for building in getattr(building_layout, "buildings", ()):
            footprint = building.footprint
            ax.add_patch(MplPolygon(list(footprint.exterior.coords),
                                    closed=True, facecolor="#e8e8e8",
                                    edgecolor="#4d4d4d", linewidth=0.8))
        site = models.get("site_boundary")
        if site is not None and not site.is_empty:
            ax.plot([x for x, _ in site.exterior.coords],
                    [y for _, y in site.exterior.coords],
                    color="#111111", linewidth=1.0, linestyle="--")
        focus = models.get("focus_bbox")
        if focus is not None:
            x0, y0, x1, y1 = focus
            ax.plot([x0, x1, x1, x0, x0], [y0, y0, y1, y1, y0],
                    color="#1f78b4", linewidth=1.0, linestyle=":")
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title("DGCAD autonomous design draft (schematic, not human-confirmed)")
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(path, dpi=140, bbox_inches="tight", metadata={"Software": None})
        plt.close(fig)
        return {"status": "rendered", "path": str(path),
                "bytes": path.stat().st_size}
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_EVIDENCE,
                        help="directory for design-preview.svg / design-overlay.svg")
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--basis", type=Path, default=DEFAULT_BASIS)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--base-roads", type=Path,
                        default=DEFAULT_EVIDENCE / "design-roads.geojson",
                        help="committed roads GeoJSON used as the 'before' layer")
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--title", type=str, default="Design plan (schematic draft)")
    parser.add_argument("--no-png", action="store_true",
                        help="skip the optional matplotlib PNG")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    models = build_models(args.case_dir, args.basis, args.profile)
    plan = render_plan_svg(
        models["building_layout"],
        models["road_layout"],
        green_layout=models["green_layout"],
        site_boundary=models["site_boundary"],
        focus_bbox=models["focus_bbox"],
        path=output_dir / "design-preview.svg",
        title=args.title,
        width=args.width,
    )
    result: dict = {"plan": plan}

    overlay_path = output_dir / "design-overlay.svg"
    base_models = {"building_layout": models["building_layout"],
                   "roads": load_base_roads(args.base_roads)["roads"]}
    candidate_models = {
        "building_layout": models["building_layout"],
        "road_layout": models["road_layout"],
        "alignment_records": list(
            getattr(models["road_layout"], "main_alignment_records", ()) or ()),
    }
    try:
        overlay = render_overlay_svg(
            base_models, candidate_models, path=overlay_path,
            title="Main-road alignment: before (grey) vs after (red)",
            width=args.width)
    except ValueError as exc:  # no roads / no base data
        overlay = {"status": "skipped", "reason": str(exc)}
    result["overlay"] = overlay

    if args.no_png:
        result["png"] = {"status": "skipped", "reason": "--no-png"}
    else:
        result["png"] = render_png(models, output_dir / "design-preview.png",
                                   width=args.width)

    if not args.quiet:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import json
import math
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from shapely.geometry import LineString, Point, Polygon, mapping, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from dgcad_design import DesignBasis, build_design_intent, load_design_input

CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
OUT = ROOT / "docs" / "e2e" / "open-source-reuse-001"


def load() -> tuple[DesignBasis, Any, Any]:
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    return basis, design_input, intent


def save_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8"
    )


def focus_buildings(design_input, intent):
    focus_ids = set(intent.focus_building_ids)
    return [b for b in design_input.buildings if b.trace_id in focus_ids]


def local_metric(geometry, basis):
    scale = basis.scale_px_per_m
    ox, oy = basis.origin_px

    def transform_coords(coords):
        return [
            ((float(x) - ox) / scale, (oy - float(y)) / scale)
            for x, y in coords
        ]

    kind = geometry["type"]
    if kind == "Polygon":
        polygon = Polygon(
            transform_coords(geometry["coordinates"][0]),
            [
                transform_coords(ring)
                for ring in geometry["coordinates"][1:]
            ],
        )
    elif kind == "MultiPolygon":
        polygon = unary_union(
            [
                Polygon(
                    transform_coords(ring[0]),
                    [transform_coords(hole) for hole in ring[1:]],
                )
                for ring in geometry["coordinates"]
            ]
        )
    elif kind == "LineString":
        return LineString(transform_coords(geometry["coordinates"]))
    elif kind == "Point":
        x, y = geometry["coordinates"]
        return Point((float(x) - ox) / scale, (oy - float(y)) / scale)
    else:
        raise ValueError(f"unsupported geometry: {kind}")
    fixed = make_valid(polygon)
    if fixed.geom_type == "Polygon":
        return fixed
    polygons = [
        item
        for item in getattr(fixed, "geoms", [])
        if item.geom_type == "Polygon"
    ]
    return unary_union(polygons)


def road_areas(case, basis) -> list[tuple[str, Polygon]]:
    import json

    data = json.loads((case / "trace-raw.geojson").read_text(encoding="utf-8"))
    areas = []
    for feature in data["features"]:
        properties = feature["properties"]
        if properties.get("semantic_role") != "road_area_candidate":
            continue
        geometry = local_metric(feature["geometry"], basis)
        if geometry.geom_type == "MultiPolygon":
            for index, polygon in enumerate(geometry.geoms, start=1):
                areas.append(
                    (f"{properties['trace_id']}-{index}", polygon)
                )
        else:
            areas.append((str(properties["trace_id"]), geometry))
    return areas


def buildings_gdf(buildings) -> gpd.GeoDataFrame:
    rows = []
    for building in buildings:
        building_id = getattr(
            building, "trace_id", None
        ) or getattr(building, "building_id", None)
        geometry = getattr(
            building, "geometry", None
        ) or getattr(building, "footprint", None)
        rows.append(
            {
                "building_id": building_id,
                "unit_count": building.unit_count,
                "area_m2": geometry.area,
                "geometry": geometry,
            }
        )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3857")


def orientation_deg(polygon: Polygon) -> float:
    rectangle = polygon.minimum_rotated_rectangle
    coords = list(rectangle.exterior.coords)
    edges = []
    for start, end in zip(coords, coords[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        edges.append((math.hypot(dx, dy), math.degrees(math.atan2(dy, dx))))
    _, angle = max(edges, key=lambda item: item[0])
    while angle > 90:
        angle -= 180
    while angle <= -90:
        angle += 180
    return angle


def iou(first, second) -> float:
    intersection = first.intersection(second).area
    union = first.union(second).area
    return float(intersection / union) if union else 0.0


def hausdorff(first, second) -> float:
    return float(first.hausdorff_distance(second))


def centroid_shift(first, second) -> float:
    return float(first.centroid.distance(second.centroid))


def plot_buildings(
    path: Path,
    source_gdf: gpd.GeoDataFrame,
    candidate_gdf: gpd.GeoDataFrame | None,
    *,
    title: str,
    source_label: str = "source",
    candidate_label: str = "candidate",
    extra_lines: list[LineString] | None = None,
) -> None:
    fig, ax = plt.subplots(figsize=(12, 10))
    source_gdf.boundary.plot(ax=ax, color="#1f77b4", linewidth=2)
    if candidate_gdf is not None:
        candidate_gdf.boundary.plot(ax=ax, color="#d62728", linewidth=2)
    if extra_lines:
        gpd.GeoSeries(extra_lines, crs="EPSG:3857").plot(
            ax=ax, color="#ff7f0e", linewidth=1
        )
    ax.set_title(title)
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.4)
    handles = [
        plt.Line2D([], [], color="#1f77b4", label=source_label),
    ]
    if candidate_gdf is not None:
        handles.append(
            plt.Line2D([], [], color="#d62728", label=candidate_label)
        )
    if extra_lines:
        handles.append(
            plt.Line2D([], [], color="#ff7f0e", label="roads")
        )
    ax.legend(handles=handles, loc="upper right")
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def to_geojson(gdf: gpd.GeoDataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    gdf.to_file(path, driver="GeoJSON")

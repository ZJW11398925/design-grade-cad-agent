from __future__ import annotations

import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import geopandas as gpd
import momepy
from buildingregulariser import regularize_geodataframe
from shapely.validation import make_valid

from common import (
    OUT,
    centroid_shift,
    focus_buildings,
    hausdorff,
    iou,
    load,
    orientation_deg,
    plot_buildings,
    save_json,
    to_geojson,
)


def vertex_count(geometry) -> int:
    if geometry.geom_type == "Polygon":
        return len(geometry.exterior.coords)
    if geometry.geom_type == "MultiPolygon":
        return sum(len(polygon.exterior.coords) for polygon in geometry.geoms)
    return 0


def main() -> int:
    basis, design_input, intent = load()
    buildings = focus_buildings(design_input, intent)
    rows = [
        {
            "building_id": item.trace_id,
            "unit_count": item.unit_count or 0,
            "area_in_m2": item.geometry.area,
            "orientation_in_deg": orientation_deg(item.geometry),
            "geometry": make_valid(item.geometry),
        }
        for item in buildings
    ]
    source = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3857")
    started = time.perf_counter()
    status = "ok"
    error = None
    try:
        regularized = regularize_geodataframe(
            source,
            parallel_threshold=1.0,
            target_crs=None,
            simplify=True,
            simplify_tolerance=0.3,
            allow_45_degree=True,
            allow_circles=False,
            neighbor_alignment=True,
            neighbor_search_distance=40.0,
            neighbor_max_rotation=10.0,
            include_metadata=True,
        )
    except Exception as exc:  # optional dependency experiment: record failure
        status = "failed"
        error = f"{type(exc).__name__}: {exc}"
        regularized = source.copy()
    runtime = time.perf_counter() - started

    if status == "ok":
        regularized = regularized.to_crs("EPSG:3857")
        regularized = regularized.rename(
            columns={"geometry": "geometry"}
        )
        regularized["area_out_m2"] = regularized.geometry.area
        regularized["orientation_out_deg"] = regularized.geometry.map(
            orientation_deg
        )
        regularized["vertices_in"] = source.geometry.map(vertex_count)
        regularized["vertices_out"] = regularized.geometry.map(vertex_count)
        regularized["hausdorff_m"] = [
            hausdorff(a, b)
            for a, b in zip(source.geometry, regularized.geometry)
        ]
        regularized["iou"] = [
            iou(a, b) for a, b in zip(source.geometry, regularized.geometry)
        ]
        regularized["centroid_shift_m"] = [
            centroid_shift(a, b)
            for a, b in zip(source.geometry, regularized.geometry)
        ]
    output = OUT / "exp-a"
    output.mkdir(parents=True, exist_ok=True)
    to_geojson(source, output / "source.geojson")
    to_geojson(regularized, output / "regularized.geojson")
    plot_buildings(
        output / "overlay.png",
        source,
        regularized,
        title="Experiment A — Building Regulariser (focus group source footprints)",
        source_label="source sketch footprint",
        candidate_label="regularized footprint",
    )

    metrics = {
        "experiment": "A-building-regulariser",
        "status": status,
        "error": error,
        "project": "DPIRD-DMA/Building-Regulariser",
        "package": "buildingregulariser",
        "version": "0.2.5",
        "license": "MIT",
        "crs_note": (
            "The local metric sketch frame is assigned EPSG:3857 only for "
            "GeoPandas/Building Regulariser compatibility; it is not a real "
            "project or georeferenced CRS."
        ),
        "input_count": len(source),
        "runtime_s": runtime,
        "input_vertices": int(source.geometry.map(vertex_count).sum()),
        "output_vertices": int(regularized.geometry.map(vertex_count).sum()),
        "valid_input": int(source.geometry.is_valid.sum()),
        "valid_output": int(regularized.geometry.is_valid.sum()),
        "input_area_m2": float(source.geometry.area.sum()),
        "output_area_m2": float(regularized.geometry.area.sum()),
        "area_change_ratio": float(
            (regularized.geometry.area.sum() - source.geometry.area.sum())
            / source.geometry.area.sum()
        ),
        "mean_hausdorff_m": float(regularized["hausdorff_m"].mean()),
        "max_hausdorff_m": float(regularized["hausdorff_m"].max()),
        "mean_iou": float(regularized["iou"].mean()),
        "mean_centroid_shift_m": float(
            regularized["centroid_shift_m"].mean()
        ),
        "orientation_change_deg": [
            abs(
                float((b - a + 90) % 180 - 90)
            )
            for a, b in zip(
                source["orientation_in_deg"],
                regularized["orientation_out_deg"],
            )
        ],
    }
    try:
        metrics["eri_input"] = float(
            momepy.equivalent_rectangular_index(source.geometry).mean()
        )
        metrics["eri_output"] = float(
            momepy.equivalent_rectangular_index(
                regularized.geometry
            ).mean()
        )
        metrics["eri_gain"] = (
            metrics["eri_output"] - metrics["eri_input"]
        )
    except Exception as exc:
        metrics["momepy_error"] = f"{type(exc).__name__}: {exc}"
    save_json(output / "metrics.json", metrics)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0 if status == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())

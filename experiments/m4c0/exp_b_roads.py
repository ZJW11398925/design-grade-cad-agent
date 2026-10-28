from __future__ import annotations

import json
import math
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
import osmnx as ox
import pygeoops
from pyclothoids import Clothoid
from shapely.geometry import LineString

from common import CASE, OUT, load, road_areas, save_json
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.roads import build_road_layout


def build_graph(design_input) -> nx.MultiDiGraph:
    graph = nx.MultiDiGraph()
    for node_id, node in design_input.road_graph.nodes.items():
        graph.add_node(node_id, x=node.x, y=node.y)
    for road in design_input.roads:
        graph.add_edge(
            road.node_a,
            road.node_b,
            key=road.edge_id,
            geometry=road.centerline,
            length=road.length_m,
            road_class=road.class_candidate,
            name=road.edge_id,
        )
    graph.graph["crs"] = "EPSG:3857"
    graph.graph["simplified"] = False
    return graph


def graph_metrics(graph: nx.MultiDiGraph) -> dict:
    components = list(nx.weakly_connected_components(graph))
    return {
        "node_count": graph.number_of_nodes(),
        "edge_count": graph.number_of_edges(),
        "total_length_m": float(
            sum(
                float(data.get("length", 0.0))
                for _, _, _, data in graph.edges(keys=True, data=True)
            )
        ),
        "weak_components": len(components),
        "largest_component_nodes": max(
            (len(item) for item in components), default=0
        ),
    }


def graph_edges_gdf(graph: nx.MultiDiGraph) -> gpd.GeoDataFrame:
    rows = []
    for u, v, key, data in graph.edges(keys=True, data=True):
        geometry = data.get("geometry")
        if geometry is None:
            geometry = LineString(
                [
                    (graph.nodes[u]["x"], graph.nodes[u]["y"]),
                    (graph.nodes[v]["x"], graph.nodes[v]["y"]),
                ]
            )
        rows.append(
            {
                "edge_id": str(data.get("name", key)),
                "u": str(u),
                "v": str(v),
                "road_class": str(data.get("road_class", "unknown")),
                "length_m": float(data.get("length", 0.0)),
                "geometry": geometry,
            }
        )
    return gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3857")


def save_graph(graph: nx.MultiDiGraph, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    graph_edges_gdf(graph).to_file(path, driver="GeoJSON")


def run_centerlines(design_input, basis):
    rows = []
    failures = []
    areas = road_areas(CASE, basis)
    for area_id, polygon in areas:
        started = time.perf_counter()
        try:
            centerline = pygeoops.centerline(
                polygon,
                densify_distance=5.0,
                min_branch_length=5.0,
                simplifytolerance=0.3,
                extend=True,
            )
        except Exception as exc:
            failures.append(
                {
                    "road_area_id": area_id,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
            continue
        runtime = time.perf_counter() - started
        if centerline is None or centerline.is_empty:
            failures.append(
                {
                    "road_area_id": area_id,
                    "error": "centerline returned empty",
                }
            )
            continue
        parts = (
            list(centerline.geoms)
            if centerline.geom_type == "MultiLineString"
            else [centerline]
        )
        length = float(sum(part.length for part in parts))
        coverage = float(
            centerline.buffer(2.0).intersection(polygon).area
            / polygon.area
        )
        rows.append(
            {
                "road_area_id": area_id,
                "area_m2": float(polygon.area),
                "length_m": length,
                "component_count": len(parts),
                "coverage_2m_buffer": coverage,
                "runtime_s": runtime,
                "geometry": centerline,
            }
        )
    gdf = gpd.GeoDataFrame(rows, geometry="geometry", crs="EPSG:3857")
    report = {
        "road_area_count": len(areas),
        "centerline_count": len(rows),
        "failure_count": len(failures),
        "failures": failures,
        "total_length_m": float(gdf["length_m"].sum()) if len(gdf) else 0.0,
        "mean_coverage_2m_buffer": (
            float(gdf["coverage_2m_buffer"].mean()) if len(gdf) else 0.0
        ),
        "multi_component_count": int(
            (gdf["component_count"] > 1).sum()
        ) if len(gdf) else 0,
    }
    return report, gdf, areas


def run_clothoid(design_input, basis, intent) -> dict:
    standardized = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        design_rect,
    )
    road_layout = build_road_layout(design_input, basis, intent, layout)
    candidates = [
        road
        for road in road_layout.roads
        if road.class_name == "main"
        and len(list(road.centerline.coords)) >= 4
    ]
    if not candidates:
        return {
            "status": "not_applicable",
            "reason": "no main-road centerline with at least four vertices",
        }
    road = max(candidates, key=lambda item: item.centerline.length)
    coords = list(road.centerline.coords)
    x0, y0 = coords[0]
    x1, y1 = coords[1]
    xn, yn = coords[-1]
    xm, ym = coords[-2]
    t0 = math.atan2(y1 - y0, x1 - x0)
    t1 = math.atan2(yn - ym, xn - xm)
    started = time.perf_counter()
    try:
        clothoid = Clothoid.G1Hermite(x0, y0, t0, xn, yn, t1)
        sample = clothoid.SampleXY(200)
        if isinstance(sample, tuple) and len(sample) == 2:
            xs, ys = sample
        else:
            xs = [point[0] for point in sample]
            ys = [point[1] for point in sample]
        fitted = LineString(list(zip(xs, ys)))
        runtime = time.perf_counter() - started
        return {
            "status": "ok",
            "road_id": road.edge_id,
            "source_length_m": float(road.centerline.length),
            "clothoid_length_m": float(fitted.length),
            "length_delta_m": float(
                fitted.length - road.centerline.length
            ),
            "hausdorff_m": float(
                fitted.hausdorff_distance(road.centerline)
            ),
            "centroid_shift_m": float(
                fitted.centroid.distance(road.centerline.centroid)
            ),
            "source_vertex_count": len(coords),
            "clothoid_sample_count": len(xs),
            "curvature_parameters": repr(clothoid.Parameters),
            "runtime_s": runtime,
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(x), float(y)] for x, y in fitted.coords
                ],
            },
        }
    except Exception as exc:
        return {
            "status": "failed",
            "road_id": road.edge_id,
            "error": f"{type(exc).__name__}: {exc}",
            "source_length_m": float(road.centerline.length),
        }


def main() -> int:
    basis, design_input, intent = load()
    output = OUT / "exp-b"
    output.mkdir(parents=True, exist_ok=True)
    graph = build_graph(design_input)
    before = graph_metrics(graph)
    simplified = ox.simplify_graph(
        graph, remove_rings=False, track_merged=True
    )
    simplified_metrics = graph_metrics(simplified)
    tolerance_report = []
    consolidated = None
    for tolerance in (4.0, 6.0, 8.0, 10.0, 15.0):
        try:
            candidate = ox.consolidate_intersections(
                graph,
                tolerance=tolerance,
                rebuild_graph=True,
                dead_ends=False,
                reconnect_edges=True,
            )
            metrics = graph_metrics(candidate)
            tolerance_report.append(
                {"tolerance_m": tolerance, **metrics}
            )
            if tolerance == 8.0:
                consolidated = candidate
        except Exception as exc:
            tolerance_report.append(
                {
                    "tolerance_m": tolerance,
                    "error": f"{type(exc).__name__}: {exc}",
                }
            )
    if consolidated is None:
        consolidated = simplified
    consolidated_metrics = graph_metrics(consolidated)
    save_graph(graph, output / "source-network.geojson")
    save_graph(simplified, output / "osmnx-simplified.geojson")
    save_graph(consolidated, output / "osmnx-consolidated-8m.geojson")

    centerline_report, centerline_gdf, areas = run_centerlines(
        design_input, basis
    )
    if len(centerline_gdf):
        centerline_gdf.to_file(
            output / "pygeoops-centerlines.geojson", driver="GeoJSON"
        )
    clothoid_report = run_clothoid(design_input, basis, intent)
    save_json(output / "clothoid.json", clothoid_report)

    design_summary = json.loads(
        (OUT.parent / "design-synthesis-001" / "design-summary.json").read_text(
            encoding="utf-8"
        )
    )
    metrics = {
        "experiment": "B-road-reuse",
        "projects": {
            "osmnx": {
                "version": "2.1.1",
                "license": "MIT",
                "url": "https://github.com/gboeing/osmnx",
            },
            "pygeoops": {
                "version": "0.6.0",
                "license": "BSD-3-Clause",
                "url": "https://github.com/pygeoops/pygeoops",
            },
            "pyclothoids": {
                "version": "0.2.0",
                "url": "https://github.com/phillipd94/PyClothoids",
            },
        },
        "source": before,
        "osmnx_simplified": simplified_metrics,
        "osmnx_consolidated_8m": consolidated_metrics,
        "osmnx_tolerance_sweep": tolerance_report,
        "reduction": {
            "simplify_node_ratio": (
                1.0 - simplified_metrics["node_count"] / before["node_count"]
            ),
            "simplify_edge_ratio": (
                1.0 - simplified_metrics["edge_count"] / before["edge_count"]
            ),
            "consolidate_node_ratio": (
                1.0
                - consolidated_metrics["node_count"]
                / before["node_count"]
            ),
            "consolidate_edge_ratio": (
                1.0
                - consolidated_metrics["edge_count"]
                / before["edge_count"]
            ),
        },
        "pygeoops_centerlines": centerline_report,
        "clothoid": {
            key: value
            for key, value in clothoid_report.items()
            if key != "geometry"
        },
        "design_4c_road_count": design_summary["metrics"]["road_count"],
        "design_4c_road_area_m2": design_summary["metrics"]["road_area_m2"],
        "crs_note": (
            "EPSG:3857 is assigned only for GeoPandas/OSMnx compatibility; "
            "the coordinates are the local metric sketch frame, not a real "
            "projection."
        ),
    }
    save_json(output / "metrics.json", metrics)

    fig, ax = plt.subplots(figsize=(12, 11))
    for graph_item, label, color in (
        (graph, "source 309/333", "#1f77b4"),
        (simplified, "OSMnx simplified", "#d62728"),
        (consolidated, "consolidated 8 m", "#2ca02c"),
    ):
        graph_edges_gdf(graph_item).plot(
            ax=ax, color=color, linewidth=1.2, label=label
        )
    ax.set_title("Experiment B — OSMnx network simplification")
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.4)
    ax.legend()
    fig.tight_layout()
    fig.savefig(output / "overlay-osmnx.png", dpi=160)
    plt.close(fig)

    fig, ax = plt.subplots(figsize=(12, 11))
    gpd.GeoSeries(
        [polygon for _, polygon in areas], crs="EPSG:3857"
    ).plot(ax=ax, color="#dddddd", alpha=0.7)
    if len(centerline_gdf):
        centerline_gdf.plot(ax=ax, color="#1f77b4", linewidth=1.5)
    gpd.GeoSeries(
        [road.centerline for road in design_input.roads],
        crs="EPSG:3857",
    ).plot(ax=ax, color="#ff7f0e", linewidth=0.6, alpha=0.7)
    ax.set_title("Experiment B — PyGeoOps centerline vs source skeleton")
    ax.set_aspect("equal")
    ax.grid(True, linewidth=0.3, alpha=0.4)
    fig.tight_layout()
    fig.savefig(output / "overlay-centerlines.png", dpi=160)
    plt.close(fig)
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

from __future__ import annotations

import hashlib
import json
import shutil
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

import geopandas as gpd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import momepy
import networkx as nx
from shapely.geometry import box
from shapely.ops import unary_union

from common import (
    OUT,
    buildings_gdf,
    focus_buildings,
    load,
    orientation_deg,
    save_json,
)
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.consistency import check_design
from dgcad_design.green import build_green_layout
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

DESIGN_EVIDENCE = OUT.parent / "design-synthesis-001"


def road_graph_for_layout(road_layout) -> nx.Graph:
    merged = unary_union(
        [road.centerline for road in road_layout.roads]
    )
    lines = (
        list(merged.geoms)
        if merged.geom_type == "MultiLineString"
        else [merged]
    )
    graph = nx.Graph()
    for line in lines:
        coords = list(line.coords)
        start = (round(coords[0][0], 3), round(coords[0][1], 3))
        end = (round(coords[-1][0], 3), round(coords[-1][1], 3))
        graph.add_node(start, x=start[0], y=start[1])
        graph.add_node(end, x=end[0], y=end[1])
        graph.add_edge(start, end, length=line.length)
    return graph


def source_road_graph(design_input) -> nx.Graph:
    graph = nx.Graph()
    for node_id, node in design_input.road_graph.nodes.items():
        graph.add_node(node_id, x=node.x, y=node.y)
    for road in design_input.roads:
        graph.add_edge(
            road.node_a, road.node_b, length=road.length_m
        )
    return graph


def graph_metrics(graph: nx.Graph) -> dict:
    nodes = graph.number_of_nodes()
    edges = graph.number_of_edges()
    components = nx.number_connected_components(graph)
    return {
        "node_count": nodes,
        "edge_count": edges,
        "component_count": components,
        "mean_node_degree_manual": (2 * edges / nodes) if nodes else 0.0,
        "edge_node_ratio": float(
            momepy.edge_node_ratio(graph, radius=None, verbose=False)
        ),
        "cyclomatic": int(
            momepy.cyclomatic(graph, radius=None, verbose=False)
        ),
        "meshedness": float(
            momepy.meshedness(graph, radius=None, verbose=False)
        ),
    }


def building_metrics(buildings) -> dict:
    if not buildings:
        return {}
    gdf = buildings_gdf(buildings)
    return {
        "count": len(gdf),
        "area_m2": float(gdf.geometry.area.sum()),
        "mean_eri": float(
            momepy.equivalent_rectangular_index(gdf.geometry).mean()
        ),
        "mean_elongation": float(
            momepy.elongation(gdf.geometry).mean()
        ),
        "mean_convexity": float(
            momepy.convexity(gdf.geometry).mean()
        ),
        "orientations_deg": [
            float(value) for value in gdf.geometry.map(orientation_deg)
        ],
    }


def largest_buildable_rect(free, bounds):
    minx, miny, maxx, maxy = bounds
    for width in (160.0, 150.0, 140.0, 130.0, 120.0):
        for height in (140.0, 130.0, 120.0, 110.0, 100.0, 90.0):
            x = minx
            while x + width <= maxx:
                y = miny
                while y + height <= maxy:
                    if free.contains(box(x, y, x + width, y + height)):
                        return [x, y, x + width, y + height]
                    y += 5.0
                x += 5.0
    return None


def osmnx_candidate_metrics(basis, design_input, intent) -> dict:
    path = OUT / "exp-b" / "osmnx-consolidated-8m.geojson"
    if not path.is_file():
        return {"status": "missing", "path": str(path)}
    gdf = gpd.read_file(path)
    degree = {}
    for _, row in gdf.iterrows():
        degree[str(row["u"])] = degree.get(str(row["u"]), 0) + 1
        degree[str(row["v"])] = degree.get(str(row["v"]), 0) + 1
    polygons = []
    widths = []
    for _, row in gdf.iterrows():
        road_class = str(row["road_class"])
        if road_class == "main_road":
            width = basis.road_widths["main_road"]
        elif (
            min(degree.get(str(row["u"]), 0), degree.get(str(row["v"]), 0))
            <= 1
            and float(row["length_m"]) < 30.0
        ):
            width = basis.road_widths["access_road"]
        else:
            width = basis.road_widths["branch_road"]
        widths.append(width)
        polygons.append(
            row["geometry"].buffer(
                width / 2, cap_style="round", join_style="round"
            )
        )
    corridor = unary_union(polygons)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    focus = box(*intent.focus_bbox).intersection(site_inner)
    free = focus.difference(
        corridor.buffer(basis.building_road_clearance_m)
    )
    rect = largest_buildable_rect(free, focus.bounds)
    return {
        "status": "ok",
        "edge_count": len(gdf),
        "road_area_m2": float(corridor.area),
        "focus_free_area_m2": float(free.area),
        "largest_buildable_rect": rect,
        "buildable": rect is not None,
        "widths_used": sorted(set(widths)),
    }


def main() -> int:
    basis, design_input, intent = load()
    output = OUT / "exp-c"
    output.mkdir(parents=True, exist_ok=True)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standard = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    focus_box = box(*intent.focus_bbox)

    candidates = {}
    for name, rect in (("uncorrected", None), ("corrected", design_rect)):
        layout = layout_focus_region(
            design_input,
            intent,
            basis,
            standard,
            site_inner,
            rect,
        )
        roads = build_road_layout(design_input, basis, intent, layout)
        green = build_green_layout(
            design_input, layout, roads, basis, focus_box
        )
        parking = build_parking_layout(
            design_input, intent, roads, basis
        )
        consistency = check_design(
            design_input,
            basis,
            intent,
            layout,
            roads,
            green,
            parking,
        )
        conflicts = [
            building.building_id
            for building in layout.focus_buildings
            if building.footprint.intersection(
                roads.corridor_union.buffer(
                    basis.building_road_clearance_m
                )
            ).area
            > 0.01
        ]
        candidates[name] = {
            "layout": layout,
            "roads": roads,
            "green": green,
            "parking": parking,
            "consistency": consistency,
            "conflicts": conflicts,
            "metrics": {
                "status": (
                    "pass"
                    if consistency.hard_checks_ok
                    else "fail"
                ),
                "building_count": len(layout.focus_buildings),
                "unit_count": sum(
                    item.unit_count for item in layout.focus_buildings
                ),
                "households": sum(
                    item.households for item in layout.focus_buildings
                ),
                "dropped_building_ids": list(
                    layout.dropped_focus_building_ids
                ),
                "road_count": len(roads.roads),
                "road_area_m2": roads.road_area_m2,
                "green_ratio": green.green_ratio,
                "conflicts": conflicts,
                "checks": {
                    check["id"]: check["status"]
                    for check in consistency.checks
                },
                "failed_checks": [
                    check["id"]
                    for check in consistency.checks
                    if check["status"] == "fail"
                ],
            },
        }

    osmnx_candidate = osmnx_candidate_metrics(
        basis, design_input, intent
    )
    source_buildings = focus_buildings(design_input, intent)
    source_gdf = buildings_gdf(source_buildings)
    corrected = candidates["corrected"]
    uncorrected = candidates["uncorrected"]
    corrected_gdf = buildings_gdf(
        corrected["layout"].focus_buildings
    )
    uncorrected_gdf = buildings_gdf(
        uncorrected["layout"].focus_buildings
    )

    source_graph_metrics = graph_metrics(
        source_road_graph(design_input)
    )
    corrected_graph_metrics = graph_metrics(
        road_graph_for_layout(corrected["roads"])
    )
    design_summary = json.loads(
        (DESIGN_EVIDENCE / "design-summary.json").read_text(
            encoding="utf-8"
        )
    )
    metrics = {
        "experiment": "C-collaborative-design",
        "source_building_metrics": building_metrics(source_buildings),
        "uncorrected_building_metrics": building_metrics(
            uncorrected["layout"].focus_buildings
        ),
        "corrected_building_metrics": building_metrics(
            corrected["layout"].focus_buildings
        ),
        "source_road_metrics": source_graph_metrics,
        "corrected_road_metrics": corrected_graph_metrics,
        "corrected_road_topology_defect": (
            corrected_graph_metrics["component_count"] > 1
        ),
        "osmnx_candidate": osmnx_candidate,
        "candidates": {
            name: item["metrics"] for name, item in candidates.items()
        },
        "design_4c": {
            "far": design_summary["metrics"]["far"],
            "households": design_summary["metrics"]["households"],
            "parking_spaces": design_summary["metrics"]["parking_spaces"],
            "parking_entrances": design_summary["metrics"][
                "parking_entrances"
            ],
            "focus_building_count": design_summary["metrics"][
                "focus_building_count"
            ],
            "focus_unit_count": design_summary["metrics"][
                "focus_unit_count"
            ],
            "focus_min_ns_gap_m": design_summary["metrics"][
                "focus_min_ns_gap_m"
            ],
            "dxf_entity_count": design_summary["dxf"]["entity_count"],
            "readback_verdict": design_summary["readback"]["verdict"],
        },
    }
    save_json(output / "metrics.json", metrics)

    # Candidate comparison image
    fig, axes = plt.subplots(1, 3, figsize=(22, 9))
    source_gdf.boundary.plot(ax=axes[0], color="#1f77b4", linewidth=2)
    gpd.GeoSeries(
        [road.centerline for road in design_input.roads],
        crs="EPSG:3857",
    ).plot(ax=axes[0], color="#ff7f0e", linewidth=0.6, alpha=0.6)
    gpd.GeoSeries(
        [green.geometry for green in design_input.greens],
        crs="EPSG:3857",
    ).plot(ax=axes[0], color="#2ca02c", alpha=0.3)
    axes[0].set_title(
        f"Source sketch focus: {len(source_buildings)} buildings"
    )

    uncorrected_gdf.plot(
        ax=axes[1], color="#d62728", alpha=0.25, edgecolor="#d62728"
    )
    gpd.GeoSeries(
        [road.corridor for road in uncorrected["roads"].roads],
        crs="EPSG:3857",
    ).plot(ax=axes[1], color="#ff7f0e", alpha=0.25)
    for building in uncorrected["layout"].focus_buildings:
        if building.building_id in uncorrected["conflicts"]:
            gpd.GeoSeries(
                [building.footprint], crs="EPSG:3857"
            ).boundary.plot(ax=axes[1], color="#d62728", linewidth=4)
    axes[1].set_title(
        "Uncorrected: "
        f"{len(uncorrected['conflicts'])} road-clearance conflicts"
    )

    corrected_gdf.plot(
        ax=axes[2], color="#1f77b4", alpha=0.3, edgecolor="#1f77b4"
    )
    gpd.GeoSeries(
        [road.corridor for road in corrected["roads"].roads],
        crs="EPSG:3857",
    ).plot(ax=axes[2], color="#ff7f0e", alpha=0.25)
    gpd.GeoSeries(
        [strip for strip in corrected["layout"].green_strips],
        crs="EPSG:3857",
    ).plot(ax=axes[2], color="#2ca02c", alpha=0.35)
    axes[2].set_title(
        "Corrected: "
        f"{len(corrected['layout'].focus_buildings)} buildings, "
        f"20.0 m N-S, dropped "
        f"{len(corrected['layout'].dropped_focus_building_ids)}"
    )
    for ax in axes:
        ax.set_aspect("equal")
        ax.grid(True, linewidth=0.3, alpha=0.4)
    fig.suptitle(
        "Experiment C — building / road / green conflict and repair "
        "(CASE-SKETCH-001 focus block)"
    )
    fig.tight_layout()
    fig.savefig(output / "comparison.png", dpi=160)
    plt.close(fig)

    shutil.copyfile(
        DESIGN_EVIDENCE / "design-proposal.dxf",
        output / "candidate-corrected.dxf",
    )
    notes = f"""# Experiment C — collaborative design and repair

Source focus buildings: {len(source_buildings)}
Uncorrected candidate: {len(uncorrected['layout'].focus_buildings)} buildings,
failed checks: {', '.join(uncorrected['metrics']['failed_checks']) or 'none'},
road-clearance conflicts: {len(uncorrected['conflicts'])}.
Corrected candidate: {len(corrected['layout'].focus_buildings)} buildings,
dropped: {', '.join(corrected['layout'].dropped_focus_building_ids) or 'none'},
checks: {json.dumps(corrected['metrics']['checks'], ensure_ascii=False)}.

The repair is not a cosmetic move: the Agent moves the design into a
main-road-bounded free block, re-packs the rows, and drops the buildings that
cannot fit at the declared 20 m spacing, 5 m setback and 3 m road clearance.
The dropped IDs and reasons are recorded in the 4c `design-diff.json`.

Open-source contribution in this candidate:
- Building Regulariser: limited gain on already-regular sketch footprints;
  not the missing building generator.
- OSMnx: consolidated source network 309/333 -> 117/141, but with design
  widths it still leaves no 120x90 m buildable focus rectangle; it is a
  topology preprocessor, not the design hierarchy.
- PyGeoOps: 11 centerlines for 11 road areas, 10 of 11 multi-component;
  useful per-area candidates, not a connected design network.
- Clothoids: a single G1 Hermite fit on MAIN-08 deviates by 356 m Hausdorff;
  a chain/control-point adapter is required.
- The corrected 4c road centerline graph has
  {corrected_graph_metrics['component_count']} components even though the
  corridor union is one polygon. The current `ROAD_CONNECTIVITY` check uses
  the corridor union and is too weak; this is a known defect of the 4c draft.
  The next round should use the OSMnx-consolidated connected network as the
  topology base, then apply the design hierarchy.
- momepy: provides morphology metrics for comparing candidates, not a design
  generator.

The corrected candidate is the 4c standardized design DXF copied here. It is
`rule_derived`, not human-confirmed, and not code-compliant.
"""
    (output / "design-notes.md").write_text(notes, encoding="utf-8")
    print(json.dumps(metrics, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

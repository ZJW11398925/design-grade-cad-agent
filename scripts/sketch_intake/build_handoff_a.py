#!/usr/bin/env python3
"""Build CASE-SKETCH-001-HANDOFF-A from the published sketch evidence.

The human review record is an input; this script never creates or confirms a
handoff by itself. It selects a small representative subset, records the
image-space evidence and writes the local-metric domain fixture.
"""
from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path

import yaml
from shapely.geometry import shape

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_domain import SketchHandoff  # noqa: E402

CASE = ROOT / "docs" / "e2e" / "sketch-001"
OUT = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
HANDOFF_ID = "CASE-SKETCH-001-HANDOFF-A"
CASE_ID = "CASE-SKETCH-001"
SCALE_PX_PER_M = 2.438
SCALE_RANGE = [2.25, 2.89]

SITE_ID = "SK-BND-001"
BUILDING_IDS = ["SK-BLD-0007", "SK-BLD-MRG-0001"]
GREEN_ID = "SK-GRN-0001"
JUNCTION_XY = (455.0, 620.0)
ROAD_EDGE_IDS = ["SK-RDC-U-0008", "SK-RDC-U-0010", "SK-RDC-U-0017"]
MAIN_CORRIDOR = "R-SK-MAIN-001"
BRANCH_CORRIDOR = "R-SK-BRANCH-001"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_json(name: str):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def main() -> int:
    summary = load_json("case-summary.json")
    trace_features = load_json("trace-raw.geojson")["features"]
    network_features = load_json("road-network-proposed.geojson")["features"]
    node_features = load_json("road-nodes-proposed.geojson")["features"]
    trace_by_id = {
        feature["properties"]["trace_id"]: feature for feature in trace_features
    }
    network_by_id = {
        feature["properties"]["trace_id"]: feature for feature in network_features
    }
    sketch_sha = summary["source"]["sha256"]
    trace_sha = sha256(CASE / "trace-raw.geojson")
    network_sha = sha256(CASE / "road-network-proposed.geojson")

    def key(x, y):
        return (round(float(x), 3), round(float(y), 3))

    node_by_xy = {
        key(*feature["geometry"]["coordinates"]): feature["properties"]["node_id"]
        for feature in node_features
    }

    site_feature = trace_by_id[SITE_ID]
    site_polygon = shape(site_feature["geometry"])
    minx, miny, maxx, maxy = site_polygon.bounds
    origin = [float(minx), float(maxy)]

    def object_record(
        source_id,
        trace_id,
        canonical_id,
        role,
        geometry,
        source_ref,
        source_hash,
        attributes=None,
    ):
        return {
            "source_id": source_id,
            "trace_id": trace_id,
            "canonical_id": canonical_id,
            "semantic_role": role,
            "semantic_state": "confirmed",
            "geometry_state": "confirmed_for_pilot",
            "geometry": geometry,
            "provenance": {
                "source_ref": source_ref,
                "source_hash": source_hash,
                "source_kind": "CASE-SKETCH-001",
            },
            "attributes": attributes or {},
        }

    objects = [
        object_record(
            SITE_ID,
            SITE_ID,
            "SITE-001",
            "site_boundary",
            site_feature["geometry"],
            "docs/e2e/sketch-001/trace-raw.geojson#SK-BND-001",
            trace_sha,
            {"authoritative_reference": "private site reference (not published)"},
        )
    ]

    for building_id in BUILDING_IDS:
        feature = trace_by_id[building_id]
        properties = feature["properties"]
        canonical_id = (
            "B-SKETCH-MRG-0001"
            if building_id == "SK-BLD-MRG-0001"
            else "B-SKETCH-0007"
        )
        objects.append(
            object_record(
                building_id,
                building_id,
                canonical_id,
                "building",
                feature["geometry"],
                f"docs/e2e/sketch-001/trace-raw.geojson#{building_id}",
                trace_sha,
                {
                    "unit_count": properties.get("unit_count"),
                    "unit_count_state": properties.get("unit_count_state"),
                    "floor_count": properties.get("floor_count"),
                    "floor_state": properties.get("floor_state"),
                    "design_state": properties.get("design_state"),
                    "replacement_pending": properties.get("replacement_pending"),
                    "merge_state": properties.get("merge_state"),
                    "geometry_part_count": properties.get("geometry_part_count"),
                },
            )
        )

    green_feature = trace_by_id[GREEN_ID]
    objects.append(
        object_record(
            GREEN_ID,
            GREEN_ID,
            "G-001",
            "green",
            green_feature["geometry"],
            f"docs/e2e/sketch-001/trace-raw.geojson#{GREEN_ID}",
            trace_sha,
            {"semantic_role": "cluster_green_space"},
        )
    )

    for edge_id in ROAD_EDGE_IDS:
        feature = network_by_id[edge_id]
        properties = feature["properties"]
        objects.append(
            object_record(
                edge_id,
                f"TRACE-{edge_id}",
                edge_id,
                "road",
                feature["geometry"],
                f"docs/e2e/sketch-001/road-network-proposed.geojson#{edge_id}",
                network_sha,
                {
                    "sketch_class_candidate": properties["road_class_candidate"],
                    "class_state": properties["class_state"],
                    "source_edge_id": edge_id,
                },
            )
        )

    buildings = [
        {
            "object_id": "B-SKETCH-0007",
            "trace_ref": "SK-BLD-0007",
            "height": {
                "value": None,
                "unit": "metre",
                "state": "unknown",
                "source_ref": "designer: 11 floors provisional; floor height unknown",
            },
            "base_elevation": {
                "value": None,
                "unit": "metre",
                "state": "unknown",
                "source_ref": None,
            },
            "typology": None,
            "typology_state": "unknown",
            "regularization_request": "preserve_trace",
        },
        {
            "object_id": "B-SKETCH-MRG-0001",
            "trace_ref": "SK-BLD-MRG-0001",
            "height": {
                "value": None,
                "unit": "metre",
                "state": "unknown",
                "source_ref": "designer: 11 floors provisional; floor height unknown",
            },
            "base_elevation": {
                "value": None,
                "unit": "metre",
                "state": "unknown",
                "source_ref": None,
            },
            "typology": None,
            "typology_state": "unknown",
            "regularization_request": "preserve_trace",
        },
    ]

    roads = [
        {
            "corridor_id": MAIN_CORRIDOR,
            "trace_refs": [
                "TRACE-SK-RDC-U-0008",
                "TRACE-SK-RDC-U-0010",
            ],
            "edge_refs": ["SK-RDC-U-0008", "SK-RDC-U-0010"],
            "source_edge_ids": ["SK-RDC-U-0008", "SK-RDC-U-0010"],
            "hierarchy": None,
            "hierarchy_state": "unknown",
            "primary_function": "unknown",
            "permitted_modes": [],
            "special_designations": [],
            "cross_section": None,
        },
        {
            "corridor_id": BRANCH_CORRIDOR,
            "trace_refs": ["TRACE-SK-RDC-U-0017"],
            "edge_refs": ["SK-RDC-U-0017"],
            "source_edge_ids": ["SK-RDC-U-0017"],
            "hierarchy": None,
            "hierarchy_state": "unknown",
            "primary_function": "unknown",
            "permitted_modes": [],
            "special_designations": [],
            "cross_section": None,
        },
    ]

    corridor_by_edge = {
        "SK-RDC-U-0008": MAIN_CORRIDOR,
        "SK-RDC-U-0010": MAIN_CORRIDOR,
        "SK-RDC-U-0017": BRANCH_CORRIDOR,
    }
    graph_nodes = {}
    graph_edges = []
    for edge_id in ROAD_EDGE_IDS:
        feature = network_by_id[edge_id]
        properties = feature["properties"]
        a = key(*properties["from_node"])
        b = key(*properties["to_node"])
        if a not in node_by_xy or b not in node_by_xy:
            raise ValueError(f"missing road node for {edge_id}")
        for point in (a, b):
            node_id = node_by_xy[point]
            graph_nodes[node_id] = {
                "node_id": node_id,
                "x": point[0],
                "y": point[1],
                "junction": point == key(*JUNCTION_XY),
            }
        graph_edges.append(
            {
                "edge_id": edge_id,
                "corridor_id": corridor_by_edge[edge_id],
                "node_a": node_by_xy[a],
                "node_b": node_by_xy[b],
                "centerline": feature["geometry"],
            }
        )

    handoff = {
        "schema_id": "dgcad.sketch-domain-handoff.v0.1",
        "handoff_id": HANDOFF_ID,
        "case_id": CASE_ID,
        "source_sketch_sha256": sketch_sha,
        "synthetic_only": False,
        "review_ref": "review.yaml",
        "coordinate_handoff": {
            "source_frame": "image_space_unscaled",
            "target_frame": "LOCAL-ENU-XY-ZUP",
            "coordinate_state": "local_metric_scaled",
            "scale_px_per_m": SCALE_PX_PER_M,
            "scale_range_px_per_m": SCALE_RANGE,
            "origin_px": origin,
            "y_axis": "flipped",
            "project_coordinates": False,
            "calibration_ref": "private site reference (not published)",
            "review_state": "reviewed",
            "accuracy": "approximate",
            "not_survey_grade": True,
        },
        "objects": objects,
        "buildings": buildings,
        "roads": roads,
        "road_graph": {
            "nodes": list(graph_nodes.values()),
            "edges": graph_edges,
        },
        "non_claims": [
            "pilot subset only; not the full CASE-SKETCH-001 site",
            "local metric frame is approximate and not survey-grade",
            "building height, base elevation, road hierarchy and cross-section remain unknown",
            "a successful DXF readback is not a design-office compliance claim",
        ],
    }

    review_data = yaml.safe_load((OUT / "review.yaml").read_text(encoding="utf-8"))
    handoff_model = SketchHandoff.from_dicts(handoff, review_data)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "handoff.yaml").write_text(
        yaml.safe_dump(handoff, sort_keys=False), encoding="utf-8"
    )
    handoff_model.write_domain_fixture(OUT / "domain-fixture.yaml")
    mapping = {
        "handoff_id": HANDOFF_ID,
        "mapping": handoff_model.mapping(),
        "corridors": [
            {
                "corridor_id": intent.corridor_id,
                "trace_refs": list(intent.trace_refs),
                "edge_refs": list(intent.edge_refs),
                "source_edge_ids": handoff_model.source_edge_ids_by_corridor[
                    intent.corridor_id
                ],
            }
            for intent in handoff_model.roads
        ],
        "road_nodes": list(graph_nodes.values()),
        "review_scope": handoff_model.review.review_scope,
        "non_claims": list(handoff_model.non_claims),
    }
    (OUT / "mapping.json").write_text(
        json.dumps(mapping, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    print(
        json.dumps(
            {
                "handoff_id": HANDOFF_ID,
                "selected_objects": [obj["source_id"] for obj in objects],
                "buildings": [intent.object_id for intent in handoff_model.buildings],
                "corridors": [intent.corridor_id for intent in handoff_model.roads],
                "road_graph": {
                    "nodes": len(handoff_model.road_graph.nodes),
                    "edges": len(handoff_model.road_graph.edges),
                },
                "origin_px": origin,
                "scale_px_per_m": SCALE_PX_PER_M,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

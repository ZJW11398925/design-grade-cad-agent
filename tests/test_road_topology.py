from __future__ import annotations

import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
CONTRACT = ROOT / "contracts" / "sketch-evidence-v0.1.yaml"


def load_json(name: str):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_unified_road_mask_restores_design_connectivity():
    summary = load_json("road-topology-summary.json")
    assert summary["status"] == "proposed_unified_mask"
    assert summary["topology_state"] == "connected_by_unified_road_mask"

    mask = summary["mask"]
    assert mask["min_area_px"] == 300
    assert mask["closing_kernel_px"] == 5
    assert mask["components_before_close"] == 7
    assert mask["components_after_close"] == 1
    assert mask["skeleton_pixels"] == 16633

    network = summary["network"]
    assert network["node_count"] == 309
    assert network["edge_count"] == 333
    assert network["component_count"] == 1
    assert network["endpoints"] == 111
    assert network["junctions"] == 121
    assert network["cyclomatic_number"] == 25
    assert network["class_edge_counts"] == {
        "main_road": 65,
        "branch_or_access_road": 268,
    }

    baseline = summary["separate_colour_baseline"]
    assert baseline["node_count"] == 306
    assert baseline["edge_count"] == 312
    assert baseline["component_count"] == 9
    assert baseline["status"] == "superseded_wrong_process"

    assert summary["inferred_connector_count"] == 0
    assert summary["rejected_connectors"]["count"] == 8


def test_unified_network_features_and_junctions():
    summary = load_json("road-topology-summary.json")
    network = load_json("road-network-proposed.geojson")["features"]
    assert len(network) == 333
    assert all(
        feature["properties"]["network_state"] == "unified_road_mask"
        for feature in network
    )
    assert not any(
        feature["properties"].get("network_state") == "inferred_connector"
        for feature in network
    )
    classes = Counter(
        feature["properties"]["road_class_candidate"] for feature in network
    )
    assert classes["main_road"] == 65
    assert classes["branch_or_access_road"] == 268
    for feature in network:
        properties = feature["properties"]
        assert properties["class_state"] == "inferred_from_colour_majority"
        assert properties["review_state"] == "proposed"
        assert properties["topology_state"] == "proposed_unified_mask"
        basis = properties["class_basis"]
        assert basis["sampled_pixels"] > 0
        assert 0.0 <= basis["brown_fraction"] <= 1.0
        assert 0.0 <= basis["blue_fraction"] <= 1.0

    nodes = load_json("road-nodes-proposed.geojson")["features"]
    assert len(nodes) == 309
    assert sum(
        1 for feature in nodes if feature["properties"]["degree"] > 2
    ) == 121
    junctions = load_json("road-junctions-proposed.geojson")["features"]
    assert len(junctions) == 121
    for feature in junctions:
        properties = feature["properties"]
        assert properties["junction_role"] == "junction_candidate"
        assert properties["junction_state"] == "candidate_from_skeleton"
        assert properties["review_state"] == "proposed"

    rejected = load_json("road-connectors-rejected.geojson")["features"]
    assert len(rejected) == 8
    assert all(
        feature["properties"]["review_state"] == "rejected"
        for feature in rejected
    )
    assert any(
        "nearest-node" in item and "not road connectivity" in item
        for item in [
            summary["rejected_connectors"]["note"],
            summary["method"],
            *summary["rules"],
        ]
    )


def test_contract_requires_unified_mask_and_records_closing():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    topology = contract["road_topology"]
    assert topology["states"] == [
        "proposed_unified_mask",
        "reviewed",
        "confirmed",
    ]
    assert {
        "state",
        "node_count",
        "edge_count",
        "component_count",
        "junction_count",
        "method",
        "mask",
    } <= set(topology["required"])
    assert topology["mask_required"] == [
        "min_area_px",
        "closing_kernel_px",
        "components_before_close",
        "components_after_close",
    ]
    assert topology["connector_states"] == [
        "inferred_nearest_endpoint",
        "rejected",
        "confirmed",
    ]
    rules = topology["rules"]
    assert any("unified road mask" in rule for rule in rules)
    assert any("colour is a road-class attribute" in rule for rule in rules)
    assert any("closing kernel" in rule for rule in rules)
    assert any("not inferred connectors" in rule for rule in rules)
    assert any("negative evidence" in rule for rule in rules)
    assert any("no width" in rule for rule in rules)

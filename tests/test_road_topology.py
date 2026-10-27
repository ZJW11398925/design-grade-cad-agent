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


def test_as_drawn_and_connected_road_topology_stats():
    summary = load_json("road-topology-summary.json")
    as_drawn = summary["as_drawn"]
    connected = summary["connected"]

    assert as_drawn["node_count"] == 306
    assert as_drawn["edge_count"] == 312
    assert as_drawn["component_count"] == 9
    assert as_drawn["endpoints"] == 129
    assert as_drawn["junctions"] == 99
    assert as_drawn["cyclomatic_number"] == 15
    assert as_drawn["road_class_edge_counts"] == {
        "main_road": 41,
        "branch_or_access_road": 271,
    }

    assert connected["node_count"] == 306
    assert connected["edge_count"] == 320
    assert connected["component_count"] == 1
    assert connected["endpoints"] == 120
    assert connected["junctions"] == 103
    assert connected["cyclomatic_number"] == 15
    assert connected["road_class_edge_counts"] == {
        "main_road": 41,
        "branch_or_access_road": 279,
    }

    assert summary["inferred_connector_count"] == 8
    gaps = [item["gap_px"] for item in summary["inferred_connectors"]]
    assert min(gaps) == 15.62
    assert max(gaps) == 76.06


def test_inferred_connectors_are_marked_and_not_design():
    summary = load_json("road-topology-summary.json")
    network = load_json("road-network-proposed.geojson")
    features = network["features"]
    assert len(features) == 320

    connectors = [
        feature
        for feature in features
        if feature["properties"]["network_state"] == "inferred_connector"
    ]
    assert len(connectors) == 8
    for feature in connectors:
        properties = feature["properties"]
        assert properties["connector_state"] == "inferred_nearest_endpoint"
        assert properties["review_state"] == "proposed"
        assert properties["topology_state"] == "inferred"
        assert properties["gap_px"] > 0
        assert properties["length_px"] == properties["gap_px"]
        assert properties["road_class_candidate"] == (
            "branch_or_access_road"
        )
        assert "inferred connector" in properties["note"]
        for forbidden in (
            "width_m",
            "cross_section",
            "alignment",
            "surface",
            "profile",
        ):
            assert forbidden not in properties

    classes = Counter(
        feature["properties"]["road_class_candidate"]
        for feature in features
    )
    assert classes["main_road"] == 41
    assert classes["branch_or_access_road"] == 279
    assert any(
        "not designed roads" in item
        for item in summary["non_claims"]
    )


def test_road_nodes_and_topology_contract():
    nodes = load_json("road-nodes-proposed.geojson")["features"]
    assert len(nodes) == 306
    node_ids = {feature["properties"]["node_id"] for feature in nodes}
    assert len(node_ids) == 306
    for feature in nodes:
        properties = feature["properties"]
        assert properties["semantic_role"] == "road_node_candidate"
        assert properties["degree"] >= 1
        assert properties["road_classes"]
        assert properties["component_id"].startswith("RC-")
        assert properties["review_state"] == "proposed"

    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    topology = contract["road_topology"]
    assert topology["states"] == [
        "as_drawn",
        "connected_with_inferred_connectors",
        "reviewed",
        "confirmed",
    ]
    assert "inferred_nearest_endpoint" in topology["connector_states"]
    rules = topology["rules"]
    assert any("as-drawn components" in rule for rule in rules)
    assert any("marked and measured" in rule for rule in rules)
    assert any("not designed roads" in rule for rule in rules)
    assert any("no width" in rule for rule in rules)

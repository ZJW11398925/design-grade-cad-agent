from __future__ import annotations

import json
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
CONTRACT = ROOT / "contracts" / "sketch-evidence-v0.1.yaml"


def load_json(name: str):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_as_drawn_topology_is_unresolved():
    summary = load_json("road-topology-summary.json")
    drawn = summary["as_drawn"]

    assert summary["status"] == "as_drawn_unresolved"
    assert summary["topology_state"] == "as_drawn_unresolved"
    assert drawn["node_count"] == 306
    assert drawn["edge_count"] == 312
    assert drawn["component_count"] == 9
    assert drawn["endpoints"] == 129
    assert drawn["junctions"] == 99
    assert drawn["cyclomatic_number"] == 15
    assert drawn["road_class_edge_counts"] == {
        "main_road": 41,
        "branch_or_access_road": 271,
    }

    assert summary["connected"] is None
    assert summary["inferred_connector_count"] == 0
    assert summary["rejected_connector_count"] == 8
    gaps = [item["distance_px"] for item in summary["open_gaps"]]
    assert min(gaps) == 15.62
    assert max(gaps) == 76.06
    assert len(summary["rejected_connectors"]) == 8


def test_rejected_connectors_are_negative_evidence():
    summary = load_json("road-topology-summary.json")
    network = load_json("road-network-proposed.geojson")
    features = network["features"]
    assert len(features) == 312
    assert all(
        feature["properties"]["network_state"] == "as_drawn"
        for feature in features
    )
    assert not any(
        feature["properties"].get("network_state") == "inferred_connector"
        for feature in features
    )

    rejected = load_json("road-connectors-rejected.geojson")["features"]
    assert len(rejected) == 8
    for feature in rejected:
        properties = feature["properties"]
        assert properties["network_state"] == "rejected_connector"
        assert properties["connector_state"] == "inferred_nearest_endpoint"
        assert properties["review_state"] == "rejected"
        assert properties["rejection_state"] == "rejected"
        assert "not evidence of a road connection" in (
            properties["rejection_reason"]
        )
        assert properties["gap_px"] > 0
        for forbidden in (
            "width_m",
            "cross_section",
            "alignment",
            "surface",
            "profile",
        ):
            assert forbidden not in properties

    assert any(
        "no connected-graph claim" in item
        for item in summary["non_claims"]
    )


def test_road_nodes_and_topology_contract():
    nodes = load_json("road-nodes-proposed.geojson")["features"]
    assert len(nodes) == 306
    node_ids = {feature["properties"]["node_id"] for feature in nodes}
    assert len(node_ids) == 306
    assert (
        sum(1 for feature in nodes if feature["properties"]["degree"] == 1)
        == 129
    )
    assert (
        sum(1 for feature in nodes if feature["properties"]["degree"] > 2)
        == 99
    )
    for feature in nodes:
        properties = feature["properties"]
        assert properties["semantic_role"] == "road_node_candidate"
        assert properties["road_classes"]
        assert properties["component_id"].startswith("RC-")
        assert properties["review_state"] == "proposed"

    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    topology = contract["road_topology"]
    assert topology["states"] == [
        "as_drawn_unresolved",
        "connected_confirmed",
        "reviewed",
        "confirmed",
    ]
    assert topology["connector_states"] == [
        "inferred_nearest_endpoint",
        "rejected",
        "confirmed",
    ]
    rules = topology["rules"]
    assert any("only road connectivity evidence" in rule for rule in rules)
    assert any("nearest-node" in rule and "rejected" in rule for rule in rules)
    assert any("gaps remain open" in rule for rule in rules)
    assert any("negative evidence" in rule for rule in rules)
    assert any("no width" in rule for rule in rules)

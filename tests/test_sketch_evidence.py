from __future__ import annotations

import hashlib
import json
from collections import Counter
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
CONTRACT = ROOT / "contracts" / "sketch-evidence-v0.1.yaml"


def load_json(name: str):
    return json.loads((CASE / name).read_text(encoding="utf-8"))


def test_contract_defines_sketch_semantics_and_review_rules():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema_id"] == "dgcad.sketch-evidence.v0.1"
    assert contract["scope"] == "EP-R1-SKETCH-001"
    roles = set(contract["trace_object"]["semantic_roles"])
    assert {
        "building_candidate",
        "building_component",
        "garage_entrance_candidate",
        "cluster_green_space_candidate",
        "road_centerline_candidate",
        "site_boundary_candidate",
        "unknown",
    } <= roles
    assert contract["trace_object"]["label_states"] == [
        "candidate",
        "reviewed",
        "confirmed",
        "disputed",
    ]
    assert contract["trace_object"]["geometry_states"] == [
        "proposed",
        "reviewed",
        "confirmed",
    ]
    rules = contract["trace_object"]["rules"]
    assert any("does not confirm geometry" in rule for rule in rules)
    assert any("defaults to proposed" in rule for rule in rules)
    assert any("no orthogonalization" in rule for rule in rules)
    assert any(
        "must not leak coordinates" in rule
        for rule in contract["publication"]["rules"]
    )
    design = contract["building_design_state"]
    assert design["design_states"] == [
        "sketch_placeholder_pending_unit_type_library",
        "unit_type_selected",
        "final",
    ]
    assert design["unit_count_states"] == [
        "unknown",
        "confirmed",
        "not_applicable",
    ]
    assert design["floor_count_states"] == [
        "unknown",
        "proposed_initial",
        "confirmed",
    ]
    assert any(
        "does not imply height" in rule for rule in design["merge"]["rules"]
    )
    assert any(
        "preserves all source component IDs" in rule
        for rule in design["merge"]["rules"]
    )


def test_public_case_declares_sketch_only_privacy():
    summary = load_json("case-summary.json")
    privacy = summary["privacy"]
    assert summary["case_id"] == "CASE-SKETCH-001"
    assert summary["tier"] == "B_human_known_base"
    assert summary["status"] == "proposed_not_human_confirmed"
    assert "sketch raster" in privacy["published"]
    assert "DWG" in privacy["private"]
    assert "DXF" in privacy["private"]
    assert "redline and project coordinates" in privacy["private"]
    assert summary["calibration"]["reference_published"] is False
    assert summary["calibration"]["review_state"] == "reviewed"
    assert summary["calibration"]["accuracy_state"] == "conceptual_approximate"
    assert summary["merge_review"]["state"] == "partially_resolved"
    assert len(summary["merge_review"]["pairs"]) == 10
    assert sum(
        1
        for pair in summary["merge_review"]["pairs"]
        if pair["resolution"] == "merged"
    ) == 7


def test_public_trace_is_image_space_and_proposed():
    trace = load_json("trace-raw.geojson")
    assert trace["features"]
    for feature in trace["features"]:
        properties = feature["properties"]
        assert properties["coordinate_frame_id"] == "SKETCH-IMG-001"
        assert properties["review_state"] == "proposed"
        assert properties["publication_state"] == "public_image_space"
        assert "area_m2_proposed" not in properties
        assert "PROJ-" not in properties["coordinate_frame_id"]
        assert properties["geometry_review_state"] == "proposed"


def test_semantic_roles_follow_designer_confirmations():
    summary = load_json("case-summary.json")
    trace = load_json("trace-raw.geojson")
    roles = Counter(
        feature["properties"]["semantic_role"] for feature in trace["features"]
    )
    assert roles["building_candidate"] == summary["counts"]["building_candidates"]
    assert roles["garage_entrance_candidate"] == summary["counts"][
        "garage_entrance_candidates"
    ]
    assert roles["cluster_green_space_candidate"] == summary["counts"][
        "cluster_green_space_candidates"
    ]
    assert roles["road_area_candidate"] == summary["counts"][
        "road_area_candidates"
    ]
    assert roles["site_boundary_candidate"] == 1

    for feature in trace["features"]:
        properties = feature["properties"]
        role = properties["semantic_role"]
        assert properties["label_state"] == "confirmed"
        if role == "garage_entrance_candidate":
            assert properties["subtype_candidate"] == (
                "underground_garage_entrance"
            )
        if role == "road_area_candidate":
            assert properties["road_class_candidate"] in {
                "main_road",
                "branch_or_access_road",
            }
            assert properties["area_state"] == (
                "not_validated_hole_handling"
            )
        if role == "site_boundary_candidate":
            assert properties["authoritative_reference"] == (
                "private site reference (not published)"
            )


def test_merged_buildings_follow_designer_unit_decisions():
    trace = load_json("trace-raw.geojson")
    buildings = {
        feature["properties"]["trace_id"]: feature
        for feature in trace["features"]
        if feature["properties"]["semantic_role"] == "building_candidate"
    }
    first = buildings["SK-BLD-MRG-0001"]
    assert first["properties"]["unit_count"] == 3
    assert first["properties"]["unit_count_state"] == "confirmed"
    assert set(first["properties"]["unit_components"]) == {
        "SK-BLD-0046",
        "SK-BLD-0047",
        "SK-BLD-0060",
    }
    assert set(first["properties"]["connector_components"]) == {
        "SK-BLD-0062",
        "SK-BLD-0063",
    }
    assert first["properties"]["merge_state"] == "confirmed"
    assert first["geometry"]["type"] == "MultiPolygon"
    assert first["properties"]["geometry_part_count"] == 5

    second = buildings["SK-BLD-MRG-0002"]
    assert second["properties"]["unit_count"] == 3
    breakdown = {
        item["trace_id"]: item["units"]
        for item in second["properties"]["unit_breakdown"]
    }
    assert breakdown == {"SK-BLD-0030": 2, "SK-BLD-0053": 1}
    assert second["properties"]["merge_state"] == "confirmed"
    assert second["geometry"]["type"] == "MultiPolygon"

    for merged_component in (
        "SK-BLD-0030",
        "SK-BLD-0046",
        "SK-BLD-0047",
        "SK-BLD-0053",
        "SK-BLD-0060",
        "SK-BLD-0062",
        "SK-BLD-0063",
    ):
        assert merged_component not in buildings

    components = load_json("building-components.geojson")["features"]
    assert len(components) == 63
    merged = [
        feature
        for feature in components
        if feature["properties"]["merged_into"] is not None
    ]
    assert len(merged) == 7
    by_id = {
        feature["properties"]["trace_id"]: feature["properties"]
        for feature in components
    }
    assert by_id["SK-BLD-0030"]["unit_count"] == 2
    assert by_id["SK-BLD-0053"]["unit_count"] == 1
    assert by_id["SK-BLD-0062"]["component_role"] == "connector"
    assert by_id["SK-BLD-0062"]["unit_count_state"] == "not_applicable"

    pairs = load_json("merge-review-pairs.json")
    assert pairs["state"] == "partially_resolved"
    assert sum(
        1 for pair in pairs["pairs"] if pair["resolution"] == "merged"
    ) == 7
    assert sum(
        1 for pair in pairs["pairs"] if pair["resolution"] == "pending"
    ) == 3


def test_floor_count_is_provisional_and_unit_type_library_is_pending():
    summary = load_json("case-summary.json")
    trace = load_json("trace-raw.geojson")
    buildings = [
        feature
        for feature in trace["features"]
        if feature["properties"]["semantic_role"] == "building_candidate"
    ]
    assert len(buildings) == summary["counts"]["building_candidates"] == 58
    for feature in buildings:
        properties = feature["properties"]
        assert properties["floor_count"] == 11
        assert properties["floor_state"] == "proposed_initial"
        assert properties["floor_height_m"] is None
        assert properties["height_state"] == "unknown"
        assert properties["massing_state"] == (
            "not_generated_pending_unit_type_library"
        )
        assert properties["design_state"] == (
            "sketch_placeholder_pending_unit_type_library"
        )
        assert properties["replacement_pending"] == "unit_type_library"
    design = summary["building_design_state"]
    assert design["floor_count"] == 11
    assert design["floor_state"] == "proposed_initial"
    assert design["floor_height_m"] is None
    assert design["massing_state"] == (
        "not_generated_pending_unit_type_library"
    )
    assert any(
        "no floor height" in item for item in summary["non_claims"]
    )


def test_road_centerlines_are_rough_and_do_not_infer_width():
    summary = load_json("case-summary.json")
    centerlines = load_json("road-centerlines-proposed.geojson")
    features = centerlines["features"]
    assert len(features) == summary["counts"][
        "road_centerline_candidates"
    ]
    classes = Counter(
        feature["properties"]["road_class_candidate"] for feature in features
    )
    assert classes["main_road"] == summary["road_centerlines"]["main_road"][
        "edge_count"
    ]
    assert classes["branch_or_access_road"] == summary["road_centerlines"][
        "branch_or_access_road"
    ]["edge_count"]
    for feature in features:
        properties = feature["properties"]
        assert properties["semantic_role"] == "road_centerline_candidate"
        assert properties["review_state"] == "proposed"
        assert properties["topology_state"] == "proposed_rough"
        assert properties["length_px"] > 0
        assert "length_m_proposed" not in properties
        assert "no professional alignment" in properties["note"]
    assert "width inference" in centerlines["note"] or any(
        "width" in item for item in summary["road_centerlines"]["non_claims"]
    )


def test_public_sketch_hash_and_dimensions_match_summary():
    summary = load_json("case-summary.json")
    sketch = CASE / "source" / "sketch.png"
    assert sketch.is_file()
    assert (
        hashlib.sha256(sketch.read_bytes()).hexdigest()
        == summary["source"]["sha256"]
    )
    assert summary["source"]["width"] == 1023
    assert summary["source"]["height"] == 1537


def test_public_files_do_not_leak_private_reference():
    forbidden = (
        "site-master",
        ".dwg",
        ".dxf",
        "45393",
        "95119",
        "204131",
        "193009",
        "homography-bend6",
        "PROJ-SITE",
        "后湖",
    )
    for path in CASE.rglob("*"):
        if not path.is_file() or path.suffix.lower() in {".png"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for item in forbidden:
            assert item.lower() not in text, f"{item} leaked in {path.name}"
    assert not (CASE / "trace-project-proposed.geojson").exists()
    assert not (CASE / "calibration.json").exists()


def test_ambiguities_are_explicit_and_reviewable():
    ambiguities = load_json("ambiguities.geojson")
    kinds = {
        feature["properties"]["kind"] for feature in ambiguities["features"]
    }
    assert "clipped_road_only" in kinds
    assert "hand_drawn_boundary" in kinds
    assert "building_merge_split" in kinds
    assert "semantic_subtype_unseparated" in kinds
    for feature in ambiguities["features"]:
        assert feature["properties"]["review_state"] in {
            "proposed",
            "reviewed",
        }

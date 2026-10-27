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
    assert summary["merge_review"]["state"] == "default_separate"
    assert len(summary["merge_review"]["pairs"]) == 10


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

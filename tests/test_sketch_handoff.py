from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest
import yaml

from dgcad_domain import (
    MassingBlocked,
    SketchHandoff,
    SketchHandoffInvalid,
    SketchHandoffNotConfirmed,
    build_initial_scene,
    building_massing,
    road_corridor_candidate,
)
from dgcad_foundation import AuthorityState

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"


def load_data():
    handoff = yaml.safe_load((HANDOFF_DIR / "handoff.yaml").read_text(encoding="utf-8"))
    review = yaml.safe_load((HANDOFF_DIR / "review.yaml").read_text(encoding="utf-8"))
    return handoff, review


def load_handoff():
    return SketchHandoff.from_dicts(*load_data())


def test_handoff_is_real_pilot_scope_and_reviewed():
    handoff = load_handoff()
    assert handoff.synthetic_only is False
    assert handoff.handoff_id == "CASE-SKETCH-001-HANDOFF-A"
    assert handoff.review.review_scope == "pilot_subset"
    assert handoff.review.human_confirmed_trace is True
    assert handoff.review.reviewer_role == "designer"
    assert len(handoff.objects) == 7
    assert len(handoff.buildings) == 2
    assert len(handoff.roads) == 2
    assert len(handoff.road_graph.nodes) == 4
    assert len(handoff.road_graph.edges) == 3
    assert handoff.coordinate.coordinate_state == "local_metric_scaled"
    assert handoff.coordinate.project_coordinates is False
    assert handoff.coordinate.not_survey_grade is True
    assert handoff.review.review_scope != "full_case"


def test_handoff_preserves_source_trace_canonical_mapping():
    handoff = load_handoff()
    mapping = {item["source_id"]: item for item in handoff.mapping()}
    assert mapping["SK-BND-001"] == {
        "source_id": "SK-BND-001",
        "trace_id": "SK-BND-001",
        "canonical_id": "SITE-001",
        "semantic_role": "site_boundary",
    }
    assert mapping["SK-BLD-0007"]["canonical_id"] == "B-SKETCH-0007"
    assert mapping["SK-BLD-MRG-0001"]["canonical_id"] == "B-SKETCH-MRG-0001"
    assert mapping["SK-GRN-0001"]["canonical_id"] == "G-001"
    assert mapping["SK-RDC-U-0008"]["trace_id"] == "TRACE-SK-RDC-U-0008"
    assert mapping["SK-RDC-U-0008"]["canonical_id"] == "SK-RDC-U-0008"
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    for item in handoff.mapping():
        assert item["canonical_id"] in scene.objects
    assert scene.objects["SITE-001"].values["trace_ref"] == "SK-BND-001"
    assert scene.objects["B-SKETCH-0007"].values["trace_ref"] == "SK-BLD-0007"


def test_handoff_geometry_is_local_metric_not_project():
    handoff = load_handoff()
    trace_scene = handoff.to_confirmed_trace_scene()
    xs = []
    ys = []
    for trace in trace_scene.trace_objects.values():
        minx, miny, maxx, maxy = trace.geometry.bounds
        xs.extend([minx, maxx])
        ys.extend([miny, maxy])
    assert min(xs) >= 0.0
    assert min(ys) >= 0.0
    assert max(xs) < 1000.0
    assert max(ys) < 1000.0
    assert handoff.coordinate.scale_range_px_per_m == (2.25, 2.89)
    assert trace_scene.coordinate_frame == "LOCAL-ENU-XY-ZUP"
    assert trace_scene.synthetic_only is False
    assert trace_scene.human_confirmed_trace is True


def test_proposed_geometry_cannot_enter_confirmed_trace():
    handoff_data, review_data = load_data()
    for item in handoff_data["objects"]:
        if item["source_id"] == "SK-BLD-0007":
            item["geometry_state"] = "proposed"
    for decision in review_data["decisions"]:
        if decision["source_id"] == "SK-BLD-0007":
            decision["geometry"] = "proposed"
    with pytest.raises(SketchHandoffNotConfirmed):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_missing_review_decision_fails():
    handoff_data, review_data = load_data()
    review_data["decisions"] = [
        decision
        for decision in review_data["decisions"]
        if decision["source_id"] != "SK-BLD-0007"
    ]
    with pytest.raises(SketchHandoffNotConfirmed):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_agent_cannot_confirm_handoff():
    handoff_data, review_data = load_data()
    review_data["reviewer_role"] = "agent"
    with pytest.raises(SketchHandoffNotConfirmed):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_unconfirmed_human_flag_fails():
    handoff_data, review_data = load_data()
    review_data["human_confirmed_trace"] = False
    with pytest.raises(SketchHandoffNotConfirmed):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_image_space_cannot_claim_project_coordinates():
    handoff_data, review_data = load_data()
    handoff_data["coordinate_handoff"]["project_coordinates"] = True
    with pytest.raises(SketchHandoffInvalid):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_missing_provenance_fails():
    handoff_data, review_data = load_data()
    for item in handoff_data["objects"]:
        if item["source_id"] == "SK-BLD-0007":
            item["provenance"].pop("source_hash")
    with pytest.raises(SketchHandoffInvalid):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_duplicate_canonical_mapping_fails():
    handoff_data, review_data = load_data()
    for item in handoff_data["objects"]:
        if item["source_id"] == "SK-BLD-MRG-0001":
            item["canonical_id"] = "B-SKETCH-0007"
    with pytest.raises(SketchHandoffInvalid):
        SketchHandoff.from_dicts(handoff_data, review_data)


def test_unknown_height_blocks_massing():
    handoff = load_handoff()
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    building = scene.objects["B-SKETCH-0007"]
    assert building.values["height"] == {
        "value": None,
        "unit": "metre",
        "state": "unknown",
        "source_ref": "designer: 11 floors provisional; floor height unknown",
    }
    with pytest.raises(MassingBlocked) as exc:
        building_massing(scene, "B-SKETCH-0007")
    assert exc.value.code == "MASSING_BLOCKED_UNKNOWN_HEIGHT"


def test_unknown_road_class_blocks_width():
    handoff = load_handoff()
    trace_scene = handoff.to_confirmed_trace_scene()
    candidate = road_corridor_candidate(
        trace_scene, trace_scene.road("R-SK-MAIN-001")
    )
    assert candidate.hierarchy is None
    assert candidate.hierarchy_state == "unknown"
    assert candidate.cross_section is None
    assert candidate.profile_resolution.outcome == "blocked"
    assert candidate.profile_resolution.code == "ROAD_CLASS_UNCONFIRMED"
    assert candidate.profile_resolution.components == ()


def test_trace_evidence_is_immutable_and_locked():
    handoff = load_handoff()
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    for trace_id in ("SK-BND-001", "SK-BLD-0007", "SK-BLD-MRG-0001", "SK-GRN-0001"):
        obj = scene.objects[trace_id]
        assert obj.authority_state == AuthorityState.EVIDENCE_ONLY
        assert obj.locks == frozenset({"all"})
        assert obj.values["review_state"] == "confirmed"


def test_public_handoff_has_no_private_project_coordinates():
    forbidden = (
        "site-master",
        "45393",
        "95119",
        "204131",
        "193009",
        "homography-bend6",
        "PROJ-SITE",
        "后湖",
    )
    for path in HANDOFF_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for item in forbidden:
            assert item.lower() not in text, f"{item} leaked in {path.name}"
    handoff = load_handoff()
    assert handoff.coordinate.project_coordinates is False
    assert handoff.coordinate.calibration_ref == (
        "private site reference (not published)"
    )

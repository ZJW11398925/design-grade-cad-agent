from __future__ import annotations

import copy
import hashlib
import json
import shutil
from pathlib import Path

import ezdxf
import pytest
import yaml

from dgcad_domain import (
    REVIEW_SCHEMA_ID,
    MassingBlocked,
    SketchHandoff,
    SketchHandoffInvalid,
    SketchHandoffNotConfirmed,
    build_initial_scene,
    building_massing,
    geometry_sha256,
    load_confirmed_trace_fixture,
    road_corridor_candidate,
)
from dgcad_e2e import scan_dxf_privacy
from dgcad_foundation import AuthorityState

ROOT = Path(__file__).resolve().parents[1]
HANDOFF_DIR = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
EVIDENCE = ROOT / "docs" / "e2e" / "sketch-handoff-a"
SOURCE_DIR = ROOT / "docs" / "e2e" / "sketch-001"


def load_data():
    handoff = yaml.safe_load(
        (HANDOFF_DIR / "handoff.yaml").read_text(encoding="utf-8")
    )
    review = yaml.safe_load(
        (HANDOFF_DIR / "review.yaml").read_text(encoding="utf-8")
    )
    return handoff, review


def inspection_handoff():
    return SketchHandoff.from_dicts(
        *load_data(),
        require_confirmation=False,
    )


def confirmed_data():
    handoff, review = copy.deepcopy(load_data())
    review.update(
        {
            "schema_id": REVIEW_SCHEMA_ID,
            "review_kind": "test_double",
            "object_geometry_review": True,
            "human_confirmed_trace": True,
            "reviewed_at": "2026-10-27",
            "evidence_refs": ["TEST-DOUBLE", "review-packet.html"],
            "review_packet_sha256": "a" * 64,
        }
    )
    for decision in review["decisions"]:
        decision["geometry"] = "confirmed_for_pilot"
        decision["coordinate"] = "local_metric_approximate"
    for obj in handoff["objects"]:
        obj["geometry_state"] = "confirmed_for_pilot"
    return handoff, review


def load_confirmed():
    return SketchHandoff.from_dicts(
        *confirmed_data(),
        allow_test_double=True,
    )


def _copy_sources(target: Path) -> Path:
    base = target / "docs" / "e2e" / "sketch-001"
    base.mkdir(parents=True, exist_ok=True)
    for relative in (
        "source/sketch.png",
        "trace-raw.geojson",
        "road-network-proposed.geojson",
    ):
        source = SOURCE_DIR / relative
        destination = base / relative
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, destination)
    return target


def _file_sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


# ---------------------------------------------------------------------------
# Review authorization, not confirmation
# ---------------------------------------------------------------------------


def test_authorized_pilot_is_blocked_at_the_human_gate():
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(*load_data())
    assert exc.value.code == "HUMAN_OBJECT_REVIEW_REQUIRED"


def test_authorized_pilot_inspection_keeps_scope_and_proposed_geometry():
    handoff = inspection_handoff()
    assert handoff.review.review_kind == "designer_authorized_pilot"
    assert handoff.review.object_geometry_review is False
    assert handoff.review.human_confirmed_trace is False
    assert handoff.review.review_scope == "pilot_subset"
    assert handoff.site_boundary_authority == "published_sketch_boundary"
    assert {obj.geometry_state for obj in handoff.objects.values()} == {
        "proposed"
    }
    assert {decision["geometry"] for decision in handoff.review.decisions.values()} == {
        "not_reviewed"
    }


def test_authorized_record_cannot_claim_geometry_review():
    handoff_data, review_data = load_data()
    for decision in review_data["decisions"]:
        decision["geometry"] = "confirmed_for_pilot"
    with pytest.raises(SketchHandoffInvalid):
        SketchHandoff.from_dicts(
            handoff_data, review_data, require_confirmation=False
        )


def test_agent_cannot_confirm_handoff():
    handoff_data, review_data = confirmed_data()
    review_data["reviewer_role"] = "agent"
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "AGENT_CANNOT_CONFIRM_HANDOFF"


def test_test_double_requires_explicit_caller_flag():
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(*confirmed_data())
    assert exc.value.code == "TEST_DOUBLE_NOT_ALLOWED"


def test_object_geometry_review_required():
    handoff_data, review_data = confirmed_data()
    review_data["object_geometry_review"] = False
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "OBJECT_GEOMETRY_REVIEW_REQUIRED"


def test_missing_review_decision_fails():
    handoff_data, review_data = confirmed_data()
    review_data["decisions"] = [
        decision
        for decision in review_data["decisions"]
        if decision["source_id"] != "SK-BLD-0007"
    ]
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "MISSING_REVIEW_DECISION"


def test_proposed_geometry_cannot_enter_confirmed_trace():
    handoff_data, review_data = confirmed_data()
    for obj in handoff_data["objects"]:
        if obj["source_id"] == "SK-BLD-0007":
            obj["geometry_state"] = "proposed"
    for decision in review_data["decisions"]:
        if decision["source_id"] == "SK-BLD-0007":
            decision["geometry"] = "proposed"
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "OBJECT_GEOMETRY_REVIEW_REQUIRED"


def test_full_case_rejects_confirmed_for_pilot():
    handoff_data, review_data = confirmed_data()
    review_data["review_scope"] = "full_case"
    with pytest.raises(SketchHandoffNotConfirmed) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "FULL_CASE_REQUIRES_CONFIRMED_GEOMETRY"


# ---------------------------------------------------------------------------
# Scope and authority propagation
# ---------------------------------------------------------------------------


def test_handoff_preserves_source_trace_canonical_mapping():
    handoff = load_confirmed()
    mapping = {item["source_id"]: item for item in handoff.mapping()}
    assert mapping["SK-BND-001"]["canonical_id"] == "SITE-SKETCH-001"
    assert mapping["SK-BLD-0007"]["canonical_id"] == "B-SKETCH-0007"
    assert mapping["SK-BLD-MRG-0001"]["canonical_id"] == "B-SKETCH-MRG-0001"
    assert mapping["SK-GRN-0001"]["canonical_id"] == "G-001"
    assert mapping["SK-RDC-U-0008"]["trace_id"] == "TRACE-SK-RDC-U-0008"
    assert mapping["SK-RDC-U-0008"]["source_file"].endswith(
        "road-network-proposed.geojson"
    )
    assert len(mapping["SK-BND-001"]["source_geometry_sha256"]) == 64
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    for item in handoff.mapping():
        assert item["canonical_id"] in scene.objects
    assert "SITE-001" not in scene.objects
    assert scene.objects["SITE-SKETCH-001"].values["trace_ref"] == "SK-BND-001"


def test_published_sketch_boundary_is_not_authoritative_site():
    handoff = load_confirmed()
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    site = scene.objects["SITE-SKETCH-001"]
    assert site.authority_state == AuthorityState.CANDIDATE
    assert site.values["site_boundary_authority"] == "published_sketch_boundary"
    assert site.values["canonical_site_identity"] is False
    assert "SITE-001" not in scene.objects


def test_scope_propagates_to_trace_and_canonical():
    handoff = load_confirmed()
    trace_scene = handoff.to_confirmed_trace_scene()
    assert trace_scene.confirmation_scope == "pilot_subset"
    assert trace_scene.geometry_quality == "confirmed_for_pilot"
    assert trace_scene.review_kind == "test_double"
    assert trace_scene.site_boundary_authority == "published_sketch_boundary"
    assert trace_scene.site_canonical_id == "SITE-SKETCH-001"
    trace = trace_scene.trace("SK-BLD-0007")
    assert trace.review_state == "confirmed_for_pilot"
    assert trace.confirmation_scope == "pilot_subset"
    assert trace.geometry_quality == "confirmed_for_pilot"
    assert trace.review_kind == "test_double"
    scene = build_initial_scene(trace_scene)
    for object_id in (
        "SK-BLD-0007",
        "B-SKETCH-0007",
        "G-001",
        "R-SK-MAIN-001",
        "SK-RDN-0126",
        "SK-RDC-U-0008",
    ):
        obj = scene.objects[object_id]
        assert obj.values["confirmation_scope"] == "pilot_subset"
        assert obj.values["geometry_quality"] == "confirmed_for_pilot"
        assert obj.values["review_kind"] == "test_double"


def test_domain_fixture_round_trips_with_scope(tmp_path):
    handoff = load_confirmed()
    path = tmp_path / "domain-fixture.yaml"
    handoff.write_domain_fixture(path)
    loaded = load_confirmed_trace_fixture(path)
    assert loaded.confirmation_scope == "pilot_subset"
    assert loaded.geometry_quality == "confirmed_for_pilot"
    assert loaded.review_kind == "test_double"
    assert loaded.test_only is True
    assert loaded.site_boundary_authority == "published_sketch_boundary"
    assert loaded.site_canonical_id == "SITE-SKETCH-001"
    assert all(
        trace.review_state == "confirmed_for_pilot"
        and trace.confirmation_scope == "pilot_subset"
        for trace in loaded.trace_objects.values()
    )


def test_trace_evidence_is_immutable_and_locked():
    handoff = load_confirmed()
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    for trace_id in (
        "SK-BND-001",
        "SK-BLD-0007",
        "SK-BLD-MRG-0001",
        "SK-GRN-0001",
    ):
        obj = scene.objects[trace_id]
        assert obj.authority_state == AuthorityState.EVIDENCE_ONLY
        assert obj.locks == frozenset({"all"})
        assert obj.values["review_state"] == "confirmed_for_pilot"
        assert obj.values["confirmation_scope"] == "pilot_subset"


def test_unknown_height_blocks_massing():
    handoff = load_confirmed()
    scene = build_initial_scene(handoff.to_confirmed_trace_scene())
    building = scene.objects["B-SKETCH-0007"]
    assert building.values["height"]["state"] == "unknown"
    assert building.values["height"]["value"] is None
    with pytest.raises(MassingBlocked) as exc:
        building_massing(scene, "B-SKETCH-0007")
    assert exc.value.code == "MASSING_BLOCKED_UNKNOWN_HEIGHT"


def test_unknown_road_class_blocks_width():
    handoff = load_confirmed()
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


# ---------------------------------------------------------------------------
# Coordinate transform
# ---------------------------------------------------------------------------


def test_coordinate_transform_is_uniform_scale_not_homography():
    handoff = inspection_handoff()
    coordinate = handoff.coordinate
    assert coordinate.target_frame == "LOCAL-XY-ZUP"
    assert coordinate.transform_kind == "uniform_scale_translation_yflip"
    assert coordinate.homography_applied is False
    assert coordinate.shape_correction == "none"
    assert coordinate.axis_orientation == "unknown"
    assert coordinate.uncertainty_method == "scale_range_sensitivity"
    assert coordinate.scale_source
    assert coordinate.origin_source
    x, y = coordinate.transform_point(
        coordinate.origin_px[0], coordinate.origin_px[1]
    )
    assert (x, y) == (0.0, 0.0)
    assert coordinate.project_coordinates is False
    assert coordinate.not_survey_grade is True


def test_scale_sensitivity_is_recorded_per_object():
    handoff = inspection_handoff()
    report = handoff.coordinate_sensitivity_report()
    assert len(report) == len(handoff.objects)
    for item in report:
        assert item["scale_range_px_per_m"] == [2.25, 2.89]
        assert item["area_range_m2"][0] <= item["area_m2"]
        assert item["area_m2"] <= item["area_range_m2"][1]
        assert item["perimeter_range_m"][0] <= item["perimeter_m"]
        assert item["perimeter_m"] <= item["perimeter_range_m"][1]
        assert item["centroid_shift_m"] >= 0.0


# ---------------------------------------------------------------------------
# Source integrity
# ---------------------------------------------------------------------------


def test_provenance_hash_format_is_enforced():
    handoff_data, review_data = confirmed_data()
    for obj in handoff_data["objects"]:
        if obj["source_id"] == "SK-BLD-0007":
            obj["provenance"]["source_geometry_sha256"] = "not-a-hash"
    with pytest.raises(SketchHandoffInvalid):
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )


def test_source_file_hash_mismatch_fails(tmp_path):
    handoff_data, _ = load_data()
    root = _copy_sources(tmp_path / "root")
    trace = root / "docs" / "e2e" / "sketch-001" / "trace-raw.geojson"
    trace.write_bytes(trace.read_bytes() + b"\n")
    handoff = SketchHandoff.from_dicts(
        handoff_data, load_data()[1], require_confirmation=False
    )
    report = handoff.source_integrity_report(root)
    assert report["ok"] is False
    assert "SOURCE_FILE_HASH_MISMATCH" in {
        error["code"] for error in report["errors"]
    }


def test_source_object_geometry_mismatch_fails(tmp_path):
    handoff_data, review_data = load_data()
    root = _copy_sources(tmp_path / "root")
    trace = root / "docs" / "e2e" / "sketch-001" / "trace-raw.geojson"
    data = json.loads(trace.read_text(encoding="utf-8"))
    for feature in data["features"]:
        if feature["properties"]["trace_id"] == "SK-BLD-0007":
            feature["geometry"]["coordinates"][0][0][0] += 5.0
    trace.write_text(json.dumps(data), encoding="utf-8")
    new_hash = _file_sha(trace)
    for entry in handoff_data["source_files"]:
        if entry["path"].endswith("trace-raw.geojson"):
            entry["sha256"] = new_hash
    for obj in handoff_data["objects"]:
        if obj["provenance"]["source_file"].endswith("trace-raw.geojson"):
            obj["provenance"]["source_file_sha256"] = new_hash
    handoff = SketchHandoff.from_dicts(
        handoff_data, review_data, require_confirmation=False
    )
    report = handoff.source_integrity_report(root)
    assert report["ok"] is False
    codes = {error["code"] for error in report["errors"]}
    assert "SOURCE_OBJECT_HASH_MISMATCH" in codes
    assert "HANDOFF_GEOMETRY_MISMATCH" in codes


def test_source_object_missing_fails(tmp_path):
    handoff_data, review_data = load_data()
    root = _copy_sources(tmp_path / "root")
    trace = root / "docs" / "e2e" / "sketch-001" / "trace-raw.geojson"
    data = json.loads(trace.read_text(encoding="utf-8"))
    data["features"] = [
        feature
        for feature in data["features"]
        if feature["properties"]["trace_id"] != "SK-BLD-0007"
    ]
    trace.write_text(json.dumps(data), encoding="utf-8")
    new_hash = _file_sha(trace)
    for entry in handoff_data["source_files"]:
        if entry["path"].endswith("trace-raw.geojson"):
            entry["sha256"] = new_hash
    for obj in handoff_data["objects"]:
        if obj["provenance"]["source_file"].endswith("trace-raw.geojson"):
            obj["provenance"]["source_file_sha256"] = new_hash
    handoff = SketchHandoff.from_dicts(
        handoff_data, review_data, require_confirmation=False
    )
    report = handoff.source_integrity_report(root)
    assert "SOURCE_OBJECT_MISSING" in {
        error["code"] for error in report["errors"]
    }


def test_handoff_geometry_must_equal_source_geometry():
    handoff_data, review_data = confirmed_data()
    for obj in handoff_data["objects"]:
        if obj["source_id"] == "SK-GRN-0001":
            obj["geometry"]["coordinates"][0][0][0] += 1.0
            obj["provenance"]["source_geometry_sha256"] = geometry_sha256(
                obj["geometry"]
            )
    handoff = SketchHandoff.from_dicts(
        handoff_data, review_data, allow_test_double=True
    )
    report = handoff.source_integrity_report(ROOT)
    codes = {error["code"] for error in report["errors"]}
    assert "HANDOFF_GEOMETRY_MISMATCH" in codes
    assert "SOURCE_OBJECT_HASH_MISMATCH" in codes


# ---------------------------------------------------------------------------
# Road topology
# ---------------------------------------------------------------------------


def test_road_topology_is_consistent_within_declared_tolerance():
    handoff = inspection_handoff()
    report = handoff.road_topology_report()
    assert report["ok"] is True
    assert report["component_count"] == 1
    assert report["node_count"] == 4
    assert report["edge_count"] == 3
    assert report["junction_node_ids"] == ["SK-RDN-0126"]
    assert report["endpoint_node_ids"] == [
        "SK-RDN-0067",
        "SK-RDN-0125",
        "SK-RDN-0209",
    ]
    assert report["max_endpoint_offset_px"] <= report["endpoint_tolerance_px"]


def test_road_endpoint_mismatch_fails_closed():
    handoff_data, review_data = confirmed_data()
    for edge in handoff_data["road_graph"]["edges"]:
        if edge["edge_id"] == "SK-RDC-U-0008":
            edge["centerline"]["coordinates"][0][0] += 10.0
    with pytest.raises(SketchHandoffInvalid) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "ROAD_EDGE_ENDPOINT_MISMATCH"


def test_road_junction_flag_mismatch_fails_closed():
    handoff_data, review_data = confirmed_data()
    for node in handoff_data["road_graph"]["nodes"]:
        if node["node_id"] == "SK-RDN-0209":
            node["junction"] = True
    with pytest.raises(SketchHandoffInvalid) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "ROAD_JUNCTION_FLAG_MISMATCH"


def test_road_graph_disconnected_fails_closed():
    handoff_data, review_data = confirmed_data()
    handoff_data["road_graph"]["nodes"].append(
        {
            "node_id": "SK-RDN-ISOLATED",
            "x": 0.0,
            "y": 0.0,
            "junction": False,
        }
    )
    with pytest.raises(SketchHandoffInvalid) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "ROAD_GRAPH_DISCONNECTED"


def test_road_corridor_edge_mismatch_fails_closed():
    handoff_data, review_data = confirmed_data()
    handoff_data["roads"][0]["source_edge_ids"] = ["SK-RDC-U-0008"]
    with pytest.raises(SketchHandoffInvalid) as exc:
        SketchHandoff.from_dicts(
            handoff_data, review_data, allow_test_double=True
        )
    assert exc.value.code == "ROAD_CORRIDOR_EDGE_MISMATCH"


# ---------------------------------------------------------------------------
# Publication and review packet
# ---------------------------------------------------------------------------


def test_review_confirmation_template_is_not_a_confirmation():
    template = yaml.safe_load(
        (EVIDENCE / "review-confirmation-template.yaml").read_text(
            encoding="utf-8"
        )
    )
    handoff_data = yaml.safe_load(
        (EVIDENCE / "handoff.yaml").read_text(encoding="utf-8")
    )
    with pytest.raises((SketchHandoffInvalid, SketchHandoffNotConfirmed)):
        SketchHandoff.from_dicts(
            handoff_data, template, allow_test_double=True
        )


def test_review_packet_marks_the_pilot_as_not_reviewed():
    packet = json.loads(
        (EVIDENCE / "review-packet.json").read_text(encoding="utf-8")
    )
    assert packet["status"] == "review_required"
    assert packet["review_kind"] == "designer_authorized_pilot"
    assert packet["object_geometry_review"] is False
    assert packet["human_confirmation_claimed"] is False
    assert len(packet["objects"]) == 7
    assert packet["coordinate_handoff"]["target_frame"] == "LOCAL-XY-ZUP"
    assert packet["coordinate_handoff"]["homography_applied"] is False
    assert packet["coordinate_handoff"]["axis_orientation"] == "unknown"


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
        "LOCAL-ENU-XY-ZUP",
    )
    for path in HANDOFF_DIR.rglob("*"):
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for item in forbidden:
            assert item.lower() not in text, f"{item} leaked in {path.name}"


def test_dxf_privacy_scan_detects_text_xdata_and_layer(tmp_path):
    path = tmp_path / "leak.dxf"
    doc = ezdxf.new("R2010")
    doc.appids.add("DESIGN_GRADE")
    doc.layers.add("PROJ-SITE")
    msp = doc.modelspace()
    msp.add_text("site-master")
    line = msp.add_line((0, 0), (1, 1))
    line.set_xdata("DESIGN_GRADE", [(1000, "homography-bend6")])
    doc.saveas(path)

    report = scan_dxf_privacy(path)
    assert report["ok"] is False
    assert report["code"] == "PRIVACY_LEAK"
    sources = {finding["source"] for finding in report["findings"]}
    assert {"layer", "text", "xdata"} <= sources

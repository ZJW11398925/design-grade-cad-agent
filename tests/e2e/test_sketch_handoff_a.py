from __future__ import annotations

import copy
import json
from pathlib import Path

import ezdxf
import yaml

from dgcad_domain import REVIEW_SCHEMA_ID
from dgcad_e2e import SketchHandoffProject, scan_dxf_privacy

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
EVIDENCE = ROOT / "docs" / "e2e" / "sketch-handoff-a"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _test_double_paths(tmp_path: Path) -> tuple[Path, Path]:
    handoff = yaml.safe_load(
        (HANDOFF_DIR / "handoff.yaml").read_text(encoding="utf-8")
    )
    review = yaml.safe_load(
        (HANDOFF_DIR / "review.yaml").read_text(encoding="utf-8")
    )
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
    handoff_path = tmp_path / "handoff.yaml"
    review_path = tmp_path / "review.yaml"
    handoff_path.write_text(
        yaml.safe_dump(handoff, sort_keys=False), encoding="utf-8"
    )
    review_path.write_text(
        yaml.safe_dump(review, sort_keys=False), encoding="utf-8"
    )
    return handoff_path, review_path


def test_authorized_pilot_evidence_is_blocked_and_reviewable():
    blocked = load_json(EVIDENCE / "blocked.json")
    summary = load_json(EVIDENCE / "handoff-summary.json")
    packet = load_json(EVIDENCE / "review-packet.json")
    integrity = load_json(EVIDENCE / "integrity.json")
    topology = load_json(EVIDENCE / "road-topology.json")
    sensitivity = load_json(EVIDENCE / "coordinate-sensitivity.json")
    request = yaml.safe_load(
        (EVIDENCE / "review-request.yaml").read_text(encoding="utf-8")
    )
    template = yaml.safe_load(
        (EVIDENCE / "review-confirmation-template.yaml").read_text(
            encoding="utf-8"
        )
    )

    assert blocked["status"] == "blocked"
    assert blocked["code"] == "HUMAN_OBJECT_REVIEW_REQUIRED"
    assert blocked["review_kind"] == "designer_authorized_pilot"
    assert blocked["object_geometry_review"] is False
    assert blocked["human_confirmation_claimed"] is False
    assert summary["status"] == "blocked"
    assert summary["pipeline_executed"] is False
    assert summary["dxf"] is None
    assert summary["canonical"] is None
    assert summary["cad_ir"] is None
    assert summary["confirmation_scope"] == "pilot_subset"
    assert summary["geometry_quality"] == "proposed"
    assert summary["site_boundary_authority"] == "published_sketch_boundary"
    assert summary["site_canonical_id"] == "SITE-SKETCH-001"

    assert packet["status"] == "review_required"
    assert packet["review_kind"] == "designer_authorized_pilot"
    assert packet["object_geometry_review"] is False
    assert packet["human_confirmation_claimed"] is False
    assert len(packet["objects"]) == 7
    assert packet["coordinate_handoff"]["target_frame"] == "LOCAL-XY-ZUP"
    assert packet["coordinate_handoff"]["homography_applied"] is False
    assert packet["coordinate_handoff"]["axis_orientation"] == "unknown"

    assert request["template_not_signed"] is True
    assert len(request["objects"]) == 7
    assert template["template_not_signed"] is True
    assert template["human_confirmed_trace"] is False
    assert template["object_geometry_review"] is True
    assert len(template["review_packet_sha256"]) == 64

    assert integrity["ok"] is True
    assert len(integrity["files"]) == 3
    assert len(integrity["objects"]) == 7
    assert topology["ok"] is True
    assert topology["component_count"] == 1
    assert topology["node_count"] == 4
    assert topology["edge_count"] == 3
    assert topology["junction_node_ids"] == ["SK-RDN-0126"]
    assert topology["max_endpoint_offset_px"] <= topology[
        "endpoint_tolerance_px"
    ]
    assert len(sensitivity["objects"]) == 7
    assert sensitivity["homography_applied"] is False
    assert sensitivity["transform_kind"] == (
        "uniform_scale_translation_yflip"
    )

    for absent in (
        "pilot.dxf",
        "canonical-snapshot.json",
        "cad-ir.json",
        "domain-fixture.yaml",
        "readback-manifest.json",
    ):
        assert not (EVIDENCE / absent).exists()


def test_committed_evidence_has_no_private_tokens():
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
    for path in EVIDENCE.iterdir():
        if not path.is_file():
            continue
        if path.suffix.lower() in {".png", ".jpg", ".jpeg"}:
            continue
        if path.name in {"blocked.json", "handoff-summary.json"}:
            continue
        if path.name == "review-packet.json":
            continue
        text = path.read_text(encoding="utf-8").lower()
        for item in forbidden:
            assert item.lower() not in text, f"{item} leaked in {path.name}"


def test_history_0_12_0_is_clearly_superseded():
    history = EVIDENCE / "history-0.12.0"
    assert history.is_dir()
    readme = (history / "README.md").read_text(encoding="utf-8")
    assert "superseded" in readme.lower()
    assert "not as current evidence" in readme.lower()
    assert (history / "review-record-as-executed.yaml").is_file()
    assert (history / "pilot.dxf").is_file()


def test_human_reviewed_pilot_reaches_dxf_with_scope(tmp_path):
    handoff_path, review_path = _test_double_paths(tmp_path)
    project = SketchHandoffProject.create(
        handoff_path,
        review_path,
        tmp_path / "pilot",
        allow_test_double=True,
        root=ROOT,
    )
    summary = project.run_pilot()

    assert summary["status"] == "executed"
    assert summary["review_kind"] == "test_double"
    assert summary["test_only"] is True
    assert summary["human_confirmation_claimed"] is False
    assert summary["runtime_approval_kind"] == "simulated_human_session"
    assert summary["confirmation_scope"] == "pilot_subset"
    assert summary["geometry_quality"] == "confirmed_for_pilot"
    assert summary["site_boundary_authority"] == "published_sketch_boundary"
    assert summary["site_canonical_id"] == "SITE-SKETCH-001"

    assert summary["dxf"]["entity_count"] == 11
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["confirmation_scopes"] == ["pilot_subset"]
    assert summary["privacy"]["ok"] is True
    assert summary["integrity"]["ok"] is True
    assert summary["road_topology"]["ok"] is True
    assert all(summary["trace_immutable"].values())

    canonical = load_json(tmp_path / "pilot" / "canonical-snapshot.json")
    assert "SITE-001" not in canonical["objects"]
    site = canonical["objects"]["SITE-SKETCH-001"]
    assert site["authority_state"] == "candidate"
    assert site["values"]["canonical_site_identity"] is False
    assert site["values"]["site_boundary_authority"] == (
        "published_sketch_boundary"
    )
    assert site["values"]["confirmation_scope"] == "pilot_subset"
    assert site["values"]["geometry_quality"] == "confirmed_for_pilot"
    for object_id in (
        "B-SKETCH-0007",
        "G-001",
        "R-SK-MAIN-001",
        "SK-RDN-0126",
        "SK-RDC-U-0008",
    ):
        obj = canonical["objects"][object_id]
        assert obj["values"]["confirmation_scope"] == "pilot_subset"
        assert obj["values"]["geometry_quality"] == "confirmed_for_pilot"

    cad_ir = load_json(tmp_path / "pilot" / "cad-ir.json")
    cad_objects = {obj["object_id"]: obj for obj in cad_ir["objects"]}
    assert cad_objects["SITE-SKETCH-001"]["provenance"][
        "confirmation_scope"
    ] == "pilot_subset"
    assert cad_objects["SITE-SKETCH-001"]["provenance"][
        "canonical_site_identity"
    ] is False
    assert cad_objects["R-SK-MAIN-001"]["provenance"][
        "confirmation_scope"
    ] == "pilot_subset"

    manifest = load_json(tmp_path / "pilot" / "readback-manifest.json")
    assert manifest["confirmation_scopes"] == ["pilot_subset"]
    assert {
        entity["confirmation_scope"] for entity in manifest["entities"]
    } == {"pilot_subset"}

    provenance = {item["source_id"]: item for item in summary["provenance"]}
    assert provenance["SK-BND-001"]["canonical_id"] == "SITE-SKETCH-001"
    assert provenance["SK-BND-001"]["canonical_authority_state"] == "candidate"
    assert provenance["SK-BND-001"]["source_geometry_sha256"]
    assert provenance["SK-BLD-MRG-0001"]["readback_entity_count"] == 5
    for edge_id in ("SK-RDC-U-0008", "SK-RDC-U-0010", "SK-RDC-U-0017"):
        assert provenance[edge_id]["canonical_object_found"] is True
        assert provenance[edge_id]["readback_entity_count"] > 0

    buildings = {item["object_id"]: item for item in summary["buildings"]}
    for building in buildings.values():
        assert building["height"]["state"] == "unknown"
        assert building["massing"]["code"] == "MASSING_BLOCKED_UNKNOWN_HEIGHT"
    roads = {item["corridor_id"]: item for item in summary["roads"]}
    for road in roads.values():
        assert road["profile"]["profile_resolution"]["code"] == (
            "ROAD_CLASS_UNCONFIRMED"
        )
        assert road["profile"]["width_claim"] == "none"


def test_scope_mismatch_in_dxf_is_detected(tmp_path):
    handoff_path, review_path = _test_double_paths(tmp_path)
    project = SketchHandoffProject.create(
        handoff_path,
        review_path,
        tmp_path / "pilot",
        allow_test_double=True,
        root=ROOT,
    )
    project.run_pilot()
    dxf_path = tmp_path / "pilot" / "pilot.dxf"
    doc = ezdxf.readfile(dxf_path)
    entity = next(iter(doc.modelspace()))
    values = list(entity.get_xdata("DESIGN_GRADE"))
    values[10] = (1000, "full_case")
    entity.set_xdata("DESIGN_GRADE", values)
    mutated = tmp_path / "scope-mismatch.dxf"
    doc.saveas(mutated)
    from dgcad_cad import validate_dxf

    result = validate_dxf(mutated, project.latest_cad_ir, project.profile)
    assert result.verdict == "fail"
    assert "CONFIRMATION_SCOPE_MISMATCH" in result.codes


def test_dxf_privacy_scan_detects_leak(tmp_path):
    handoff_path, review_path = _test_double_paths(tmp_path)
    project = SketchHandoffProject.create(
        handoff_path,
        review_path,
        tmp_path / "pilot",
        allow_test_double=True,
        root=ROOT,
    )
    project.run_pilot()
    dxf_path = tmp_path / "pilot" / "pilot.dxf"
    doc = ezdxf.readfile(dxf_path)
    doc.modelspace().add_text("site-master")
    leaked = tmp_path / "leaked.dxf"
    doc.saveas(leaked)
    report = scan_dxf_privacy(leaked)
    assert report["ok"] is False
    assert report["code"] == "PRIVACY_LEAK"
    assert "site-master" in {finding["token"] for finding in report["findings"]}

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from dgcad_e2e import SketchHandoffProject

ROOT = Path(__file__).resolve().parents[2]
HANDOFF_DIR = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
EVIDENCE = ROOT / "docs" / "e2e" / "sketch-handoff-a"


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def test_handoff_pilot_reaches_dxf_with_provenance(tmp_path):
    project = SketchHandoffProject.create(
        HANDOFF_DIR / "handoff.yaml",
        HANDOFF_DIR / "review.yaml",
        tmp_path / "pilot",
    )
    summary = project.run_pilot()

    assert summary["handoff_id"] == "CASE-SKETCH-001-HANDOFF-A"
    assert summary["review_scope"] == "pilot_subset"
    assert summary["pilot_scope"] is True
    assert summary["ep_r1_sketch_complete"] is False
    assert summary["coordinate_handoff"]["project_coordinates"] is False
    assert summary["coordinate_handoff"]["not_survey_grade"] is True

    assert summary["dxf"]["entity_count"] == 11
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["entity_count"] == 11
    assert summary["readback"]["expected_entity_count"] == 11
    assert summary["cad_ir_validation"]["verdict"] == "pass_with_scope_limits"
    assert "UNKNOWN_HEIGHT_ALLOWED" in {
        issue["code"] for issue in summary["cad_ir_validation"]["issues"]
    }

    assert all(summary["trace_immutable"].values())
    for building in summary["buildings"]:
        assert building["height"]["state"] == "unknown"
        assert building["height"]["value"] is None
        assert building["massing"] == {
            "state": "blocked",
            "code": "MASSING_BLOCKED_UNKNOWN_HEIGHT",
        }
    for road in summary["roads"]:
        assert road["hierarchy"] is None
        assert road["hierarchy_state"] == "unknown"
        assert road["cross_section"] is None
        assert road["profile"]["profile_resolution"]["outcome"] == "blocked"
        assert road["profile"]["profile_resolution"]["code"] == (
            "ROAD_CLASS_UNCONFIRMED"
        )
        assert road["profile"]["width_claim"] == "none"

    provenance = {item["source_id"]: item for item in summary["provenance"]}
    assert provenance["SK-BND-001"]["canonical_id"] == "SITE-001"
    assert provenance["SK-BLD-0007"]["readback_entity_count"] == 1
    assert provenance["SK-BLD-MRG-0001"]["readback_entity_count"] == 5
    assert provenance["SK-GRN-0001"]["readback_entity_count"] == 1
    for edge_id in ("SK-RDC-U-0008", "SK-RDC-U-0010", "SK-RDC-U-0017"):
        assert provenance[edge_id]["canonical_object_found"] is True
        assert provenance[edge_id]["cad_ir_object_found"] is False
        assert provenance[edge_id]["edge_exported_as_corridor"] is not None
        assert provenance[edge_id]["readback_entity_count"] > 0

    corridors = {
        item["corridor_id"]: item for item in summary["corridor_provenance"]
    }
    assert corridors["R-SK-MAIN-001"]["source_edge_ids"] == [
        "SK-RDC-U-0008",
        "SK-RDC-U-0010",
    ]
    assert corridors["R-SK-MAIN-001"]["readback_entity_count"] == 2
    assert corridors["R-SK-BRANCH-001"]["source_edge_ids"] == [
        "SK-RDC-U-0017"
    ]

    canonical = load_json(tmp_path / "pilot" / "canonical-snapshot.json")
    assert summary["handoff_audit_object"] in canonical["objects"]
    assert (
        canonical["objects"][summary["handoff_audit_object"]]["authority_state"]
        == "human_confirmed"
    )
    manifest = load_json(tmp_path / "pilot" / "readback-manifest.json")
    assert manifest["dxf_sha256"] == summary["dxf"]["sha256"]
    assert manifest["cad_ir_dependency_fingerprint"] == (
        summary["cad_ir_dependency_fingerprint"]
    )
    assert "SITE-001" in manifest["object_ids"]
    assert "B-SKETCH-MRG-0001" in manifest["object_ids"]
    assert "R-SK-MAIN-001" in manifest["object_ids"]


def test_committed_handoff_evidence_is_pilot_scope_and_traceable():
    summary = load_json(EVIDENCE / "handoff-summary.json")
    validation = load_json(EVIDENCE / "validation.json")
    provenance = load_json(EVIDENCE / "provenance-map.json")
    canonical = load_json(EVIDENCE / "canonical-snapshot.json")
    manifest = load_json(EVIDENCE / "readback-manifest.json")

    assert summary["review_scope"] == "pilot_subset"
    assert summary["pilot_scope"] is True
    assert summary["ep_r1_sketch_complete"] is False
    assert summary["readback"]["verdict"] == "pass"
    assert validation["verdicts"]["dxf_readback"] == "pass"
    assert validation["verdicts"]["cad_ir"] == "pass_with_scope_limits"
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0
    dxf_path = EVIDENCE / "pilot.dxf"
    assert (
        hashlib.sha256(dxf_path.read_bytes()).hexdigest()
        == summary["dxf"]["sha256"]
        == manifest["dxf_sha256"]
    )
    assert summary["handoff_audit_object"] in canonical["objects"]
    assert provenance["handoff_id"] == "CASE-SKETCH-001-HANDOFF-A"
    assert len(provenance["mapping"]) == 7
    assert {item["source_id"] for item in provenance["mapping"]} == {
        "SK-BND-001",
        "SK-BLD-0007",
        "SK-BLD-MRG-0001",
        "SK-GRN-0001",
        "SK-RDC-U-0008",
        "SK-RDC-U-0010",
        "SK-RDC-U-0017",
    }
    assert all(
        item["canonical_object_found"] for item in provenance["mapping"]
    )

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
    for path in EVIDENCE.iterdir():
        if not path.is_file() or path.suffix.lower() in {
            ".png",
            ".jpg",
            ".jpeg",
            ".dxf",
        }:
            continue
        text = path.read_text(encoding="utf-8").lower()
        for item in forbidden:
            assert item.lower() not in text, f"{item} leaked in {path.name}"

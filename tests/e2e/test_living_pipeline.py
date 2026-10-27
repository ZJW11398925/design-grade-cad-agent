from __future__ import annotations

import json
from pathlib import Path

import pytest

from dgcad_e2e import run_living_pipeline

E2E_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "e2e"
    / "living-pipeline-001.yaml"
)


@pytest.fixture(scope="module")
def result(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("living-e2e")
    return run_living_pipeline(E2E_FIXTURE, output_dir)


def test_pipeline_commits_domain_objects_through_runtime(result):
    assert result.fixture_id == "E2E-LIVING-001"
    assert result.synthetic_only is True
    assert result.canonical_scene.scene_revision == 6
    assert {
        "B-001",
        "B-002",
        "B-003",
        "R-001",
        "R-002",
    } <= set(result.commit_responses)
    assert all(
        response["status"] == "committed"
        for response in result.commit_responses.values()
    )

    scene = result.canonical_scene
    for building_id in ("B-001", "B-002", "B-003"):
        assert (
            scene.objects[building_id].values["professional_footprint"]
            is not None
        )
    assert scene.objects["B-002"].values["height"]["state"] == "unknown"
    assert scene.objects["R-001"].values["hierarchy_state"] == "unknown"
    assert (
        scene.objects["R-001"].values["profile_resolution"]["outcome"]
        == "blocked"
    )
    assert (
        scene.objects["R-002"].values["profile_resolution"]["outcome"]
        == "resolved"
    )
    assert scene.objects["R-001"].values["trace_ref"] == "TRACE-R-001"
    assert scene.objects["R-002"].values["trace_ref"] == "TRACE-R-002"


def test_massing_and_rebuild_closure(result):
    assert set(result.massing) == {"B-001", "B-003"}
    assert result.massing_blocked == {
        "B-002": "MASSING_BLOCKED_UNKNOWN_HEIGHT"
    }
    assert result.rebuild["status"] == "queued"
    assert result.rebuild["rebuild_order"] == [
        "MASS-B-001",
        "MASS-B-003",
        "SURFACE-R-002",
    ]
    assert len(result.rebuild["job_ids"]) == 3


def test_shadow_baseline_statuses(result):
    assert result.shadow.solar_position.elevation_deg == pytest.approx(
        72.0467, abs=1e-3
    )
    assert result.shadow.solar_position.azimuth_deg == pytest.approx(
        32.3093, abs=1e-3
    )
    statuses = {
        sample.sample_id: sample.status for sample in result.shadow.samples
    }
    assert statuses == {
        "SAMPLE-01": "confirmed_sunlit_given_declared_context",
        "SAMPLE-02": "confirmed_shaded",
        "SAMPLE-03": "unknown_obstruction_height",
        "SAMPLE-04": "confirmed_sunlit_given_declared_context",
    }
    assert result.shadow.status == "bounded_or_unknown"
    assert result.shadow.dependency_fingerprint


def test_cad_ir_identity_and_provenance(result):
    objects = {obj.object_id: obj for obj in result.cad_ir.objects}
    assert len(objects) == 11
    assert objects["B-001"].massing["height_m"] == 18.0
    assert objects["B-001"].massing["height_state"] == "confirmed"
    assert objects["B-002"].massing["height_m"] is None
    assert objects["B-002"].massing["height_state"] == "unknown"
    assert objects["R-001"].provenance["source_trace_ref"] == "TRACE-R-001"
    assert objects["R-002"].provenance["source_trace_ref"] == "TRACE-R-002"
    assert objects["SAMPLE-01"].source_world == "analysis"
    assert (
        objects["SAMPLE-01"].provenance["analysis_dependency_fingerprint"]
        == result.shadow.dependency_fingerprint
    )
    assert result.cad_ir.dependency_fingerprint


def test_dxf_delivery_and_readback_manifest(result):
    assert result.dxf_path.exists()
    assert result.dxf_compile.entity_count == 15
    assert result.dxf_compile.audit_errors == 0
    assert result.dxf_compile.audit_fixes == 0
    assert result.dxf_readback.verdict == "pass"
    manifest = result.dxf_readback.manifest
    assert manifest["entity_count"] == 15
    assert manifest["expected_entity_count"] == 15
    assert manifest["audit_errors"] == 0
    assert manifest["audit_fixes"] == 0
    assert manifest["object_ids"] == sorted(
        obj.object_id for obj in result.cad_ir.objects
    )
    assert (
        manifest["cad_ir_dependency_fingerprint"]
        == result.cad_ir.dependency_fingerprint
    )
    assert "A-BUILDING-OUTLINE" in manifest["layer_names"]
    assert manifest["insunits"] == 6


def test_domain_validation_reports_only_declared_unknowns(result):
    assert result.domain_validation.verdict == "blocked"
    assert set(result.domain_validation.codes) == {
        "UNKNOWN_HEIGHT_BLOCKS_MASSING",
        "ROAD_CLASS_UNCONFIRMED",
    }
    assert "TRACE_REF_MISSING" not in result.domain_validation.codes
    assert "INVALID_FOOTPRINT" not in result.domain_validation.codes


def test_evidence_files_are_written(result):
    required = (
        "cad-ir.json",
        "shadow-result.json",
        "readback-manifest.json",
        "cad-ir-validation.json",
        "domain-validation.json",
        "pipeline-summary.json",
        "living-pipeline-001.dxf",
    )
    for name in required:
        assert (result.output_dir / name).exists(), name
    summary = json.loads(
        (result.output_dir / "pipeline-summary.json").read_text(encoding="utf-8")
    )
    assert summary["cad_ir"]["object_count"] == 11
    assert summary["dxf_readback"]["verdict"] == "pass"
    assert summary["massing_blocked"]["B-002"] == (
        "MASSING_BLOCKED_UNKNOWN_HEIGHT"
    )


def test_pipeline_uses_only_living_packages():
    root = Path(__file__).resolve().parents[2]
    for package in ("dgcad_e2e", "dgcad_cad", "dgcad_analysis"):
        for path in (root / "src" / package).rglob("*.py"):
            source = path.read_text(encoding="utf-8")
            assert "research/archive" not in source, path
            assert "working/e2e-integration" not in source, path

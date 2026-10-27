from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from dgcad_e2e import LivingProject

E2E_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "e2e"
    / "living-pipeline-001.yaml"
)


@pytest.fixture()
def project(tmp_path):
    living = LivingProject.create(E2E_FIXTURE, tmp_path / "project")
    living.bootstrap()
    return living


def test_height_change_scopes_stale_and_rebuilds_delivery(project):
    scene = project.scene
    footprint_before = scene.objects["B-001"].values[
        "professional_footprint"
    ]
    revisions_before = scene.objects["B-001"].revisions
    old_shadow_fingerprint = project.latest_shadow.dependency_fingerprint
    old_cad_fingerprint = project.latest_cad_ir.dependency_fingerprint
    old_manifest = dict(project.latest_manifest)

    response = project.mutate_building_height("B-001", 24.0)
    assert response["status"] == "committed"

    assert project.artifact_state("MASS-B-001") == "stale"
    assert project.artifact_state("SHADOW-E2E-002") == "stale"
    assert project.artifact_state("CAD-IR-E2E-002") == "stale"
    assert project.artifact_state("DXF-E2E-002") == "stale"
    assert project.artifact_state("PLAN-B-001") == "current"
    assert project.artifact_state("MASS-B-003") == "current"

    building = project.scene.objects["B-001"]
    assert building.revisions.parameter == revisions_before.parameter + 1
    assert building.revisions.geometry == revisions_before.geometry
    assert (
        building.values["professional_footprint"] == footprint_before
    )

    report = project.rebuild_all()
    rebuilt = {job["job"]["artifact_id"] for job in report.jobs}
    assert rebuilt == {
        "MASS-B-001",
        "SHADOW-E2E-002",
        "CAD-IR-E2E-002",
        "DXF-E2E-002",
    }
    assert all(
        job["completion"]["status"] == "succeeded"
        for job in report.jobs
    )
    assert project.stale_artifacts == set()

    massing = json.loads(
        (project.output_dir / "artifacts" / "MASS-B-001.json").read_text(
            encoding="utf-8"
        )
    )
    assert massing["height_m"] == 24.0
    assert massing["height_state"] == "confirmed"
    assert massing["footprint_area_m2"] > 0

    assert (
        project.latest_shadow.dependency_fingerprint
        != old_shadow_fingerprint
    )
    assert (
        project.latest_cad_ir.dependency_fingerprint
        != old_cad_fingerprint
    )
    cad_b001 = next(
        obj
        for obj in project.latest_cad_ir.objects
        if obj.object_id == "B-001"
    )
    assert cad_b001.massing["height_m"] == 24.0
    assert (
        cad_b001.provenance["canonical_revisions"]["geometry"]
        == revisions_before.geometry
    )
    assert (
        cad_b001.provenance["canonical_revisions"]["parameter"]
        == revisions_before.parameter + 1
    )
    cad_b003 = next(
        obj
        for obj in project.latest_cad_ir.objects
        if obj.object_id == "B-003"
    )
    assert cad_b003.massing["height_m"] == 12.0
    assert project.latest_manifest["audit_errors"] == 0
    assert project.latest_manifest["sha256"] != old_manifest["sha256"]


def test_node_move_rebuilds_corridor_from_latest_canonical_edges(project):
    before_centerline = project.scene.objects["R-001"].values[
        "centerline"
    ]["coordinates"]
    before_scene_revision = project.scene.scene_revision
    old_cad_fingerprint = project.latest_cad_ir.dependency_fingerprint

    response = project.mutate_road_node("RN-003", 21.0, 12.0)
    assert response["node_move"]["status"] == "committed"
    assert response["node_move"]["scene_revision"] == before_scene_revision + 1
    assert response["affected_corridors"] == ["R-001", "R-002"]
    assert all(
        item["status"] == "committed"
        for item in response["corridor_rebuilds"].values()
    )

    assert project.scene.objects["RN-003"].values["x"] == 21.0
    assert project.scene.objects["RN-003"].values["y"] == 12.0
    for edge_id in ("RE-001", "RE-002", "RE-003"):
        coords = project.scene.objects[edge_id].values["centerline"][
            "coordinates"
        ]
        assert [21.0, 12.0] in coords

    corridor = project.scene.objects["R-001"]
    assert corridor.values["centerline_state"] == "confirmed"
    centerline_after = corridor.values["centerline"]["coordinates"]
    assert centerline_after != before_centerline
    assert [21.0, 12.0] in centerline_after
    assert [20.0, 11.0] not in centerline_after
    r002_centerline = project.scene.objects["R-002"].values["centerline"][
        "coordinates"
    ]
    assert r002_centerline[0] == [21.0, 12.0]

    assert project.artifact_state("CAD-IR-E2E-002") == "stale"
    assert project.artifact_state("DXF-E2E-002") == "stale"
    assert project.artifact_state("SHADOW-E2E-002") == "current"
    assert project.artifact_state("PLAN-B-001") == "current"
    assert project.artifact_state("MASS-B-001") == "current"

    report = project.rebuild_all()
    assert {job["job"]["artifact_id"] for job in report.jobs} == {
        "CAD-IR-E2E-002",
        "DXF-E2E-002",
    }
    cad_r001 = next(
        obj
        for obj in project.latest_cad_ir.objects
        if obj.object_id == "R-001"
    )
    assert [21.0, 12.0] in cad_r001.geometry["coordinates"]
    assert [20.0, 11.0] not in cad_r001.geometry["coordinates"]
    assert (
        project.latest_cad_ir.dependency_fingerprint
        != old_cad_fingerprint
    )
    assert project.latest_manifest["audit_errors"] == 0


def test_north_bearing_is_versioned_and_scopes_stale(project):
    old_shadow_fingerprint = project.latest_shadow.dependency_fingerprint
    old_statuses = {
        sample.sample_id: sample.status
        for sample in project.latest_shadow.samples
    }
    old_geometry_revision = project.scene.objects["B-001"].revisions.geometry
    old_parameter_revision = project.project_context.revisions.parameter

    response = project.mutate_north_bearing(90.0)
    assert response["status"] == "committed"

    context = project.project_context
    assert context.values["north_bearing_deg"] == 90.0
    assert context.values["north_bearing_source"] == "human_override"
    assert context.revisions.parameter == old_parameter_revision + 1

    assert project.artifact_state("SHADOW-E2E-002") == "stale"
    assert project.artifact_state("CAD-IR-E2E-002") == "stale"
    assert project.artifact_state("DXF-E2E-002") == "stale"
    assert project.artifact_state("PLAN-B-001") == "current"
    assert project.artifact_state("MASS-B-001") == "current"
    assert project.artifact_state("MASS-B-003") == "current"
    assert (
        project.scene.objects["B-001"].revisions.geometry
        == old_geometry_revision
    )

    report = project.rebuild_all()
    assert {job["job"]["artifact_id"] for job in report.jobs} == {
        "SHADOW-E2E-002",
        "CAD-IR-E2E-002",
        "DXF-E2E-002",
    }
    assert (
        project.latest_shadow.dependency_fingerprint
        != old_shadow_fingerprint
    )
    new_statuses = {
        sample.sample_id: sample.status
        for sample in project.latest_shadow.samples
    }
    assert new_statuses != old_statuses
    assert project.latest_manifest["audit_errors"] == 0


def test_rebuild_worker_recomputes_writes_and_validates(project):
    project.mutate_building_height("B-001", 24.0)
    assert project.stale_artifacts
    report = project.rebuild_all()

    assert report.queued["job_ids"]
    assert all(
        job["completion"]["status"] == "succeeded"
        for job in report.jobs
    )
    for job in report.jobs:
        assert job["content_hash"]
        assert (project.output_dir / job["payload_ref"]).exists()
    assert project.stale_artifacts == set()
    assert project.artifact_state("DXF-E2E-002") == "current"
    assert project.latest_manifest["audit_errors"] == 0

    dxf_jobs = [
        job
        for job in report.jobs
        if job["job"]["artifact_id"] == "DXF-E2E-002"
    ]
    assert len(dxf_jobs) == 1
    dxf_path = project.output_dir / dxf_jobs[0]["payload_ref"]
    assert (
        hashlib.sha256(dxf_path.read_bytes()).hexdigest()
        == dxf_jobs[0]["content_hash"]
    )


def test_manifest_comparison_uses_ids_revisions_and_fingerprints(project):
    old_manifest = dict(project.latest_manifest)
    old_objects = {
        obj.object_id: obj for obj in project.latest_cad_ir.objects
    }

    project.mutate_building_height("B-001", 24.0)
    project.rebuild_all()

    new_manifest = project.latest_manifest
    new_objects = {
        obj.object_id: obj for obj in project.latest_cad_ir.objects
    }
    assert set(old_objects) == set(new_objects)
    assert set(new_manifest["object_ids"]) == set(new_objects)
    assert old_manifest["entity_count"] == new_manifest["entity_count"] == 15
    assert old_manifest["audit_errors"] == new_manifest["audit_errors"] == 0
    assert old_manifest["sha256"] != new_manifest["sha256"]
    assert (
        old_manifest["cad_ir_dependency_fingerprint"]
        != new_manifest["cad_ir_dependency_fingerprint"]
    )
    assert (
        old_objects["B-001"].provenance["canonical_revisions"]["geometry"]
        == new_objects["B-001"].provenance["canonical_revisions"]["geometry"]
    )
    assert (
        old_objects["B-001"].provenance["canonical_revisions"]["parameter"]
        != new_objects["B-001"].provenance["canonical_revisions"]["parameter"]
    )
    assert old_objects["B-001"].massing["height_m"] == 18.0
    assert new_objects["B-001"].massing["height_m"] == 24.0
    assert (
        old_objects["B-003"].provenance["canonical_revisions"]
        == new_objects["B-003"].provenance["canonical_revisions"]
    )


def test_road_surface_geometry_is_explicitly_deferred(project):
    assert project.road_surface_status == "deferred_no_geometry_generator"
    assert "SURFACE-R-002" not in project.artifact_states
    assert not (
        project.output_dir / "artifacts" / "SURFACE-R-002.json"
    ).exists()

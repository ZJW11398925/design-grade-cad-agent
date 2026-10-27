from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import ezdxf
import pytest
from shapely.geometry import MultiPolygon, Polygon

from dgcad_cad import (
    CadIR,
    CadObject,
    build_cad_ir,
    compile_to_dxf,
    validate_dxf,
)
from dgcad_cad.validator import symbol_name_equal
from dgcad_domain import geometry_to_geojson
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


def test_unrelated_node_flag_does_not_stale_cad_ir_or_change_fingerprint(
    project,
):
    before = project.latest_cad_ir
    before_scene_revision = project.scene.scene_revision
    assert "built_from_scene_revision" in before.project
    assert "canonical_scene_revision" not in before.project

    response = project.mutate_road_node_flag("RN-001", junction=True)
    assert response["status"] == "committed"
    assert project.scene.scene_revision == before_scene_revision + 1

    assert project.artifact_state("CAD-IR-E2E-002") == "current"
    assert project.artifact_state("DXF-E2E-002") == "current"

    rebuilt = build_cad_ir(
        project.scene,
        project.profile,
        project.latest_shadow,
        sample_points=project.base_shadow_config.samples,
    )
    assert rebuilt.dependency_fingerprint == before.dependency_fingerprint
    assert (
        rebuilt.project["built_from_scene_revision"]
        != before.project["built_from_scene_revision"]
    )


def test_road_semantic_change_stales_cad_ir_and_changes_fingerprint(project):
    before = project.latest_cad_ir.dependency_fingerprint
    response = project.mutate_road_class("R-001", "site_primary")
    assert response["status"] == "committed"
    assert project.artifact_state("CAD-IR-E2E-002") == "stale"
    assert project.artifact_state("DXF-E2E-002") == "stale"

    rebuilt = build_cad_ir(
        project.scene,
        project.profile,
        project.latest_shadow,
        sample_points=project.base_shadow_config.samples,
    )
    assert rebuilt.dependency_fingerprint != before

    report = project.rebuild_all()
    rebuilt_ids = {job["job"]["artifact_id"] for job in report.jobs}
    assert rebuilt_ids == {"CAD-IR-E2E-002", "DXF-E2E-002"}
    assert project.artifact_state("CAD-IR-E2E-002") == "current"
    assert project.artifact_state("DXF-E2E-002") == "current"


XDATA_APPID = "DESIGN_GRADE"


def _entity(doc, object_id: str, role: str):
    msp = doc.modelspace() if hasattr(doc, "modelspace") else doc
    for entity in msp:
        if not entity.has_xdata(XDATA_APPID):
            continue
        values = list(entity.get_xdata(XDATA_APPID))
        if str(values[0][1]) == object_id and str(values[5][1]) == role:
            return entity
    raise AssertionError(f"entity {object_id}/{role} not found")


def _mutate(project, tmp_path, name: str, mutate):
    source = project.output_dir / "living-mutations-002.dxf"
    doc = ezdxf.readfile(source)
    mutate(doc)
    path = tmp_path / f"{name}.dxf"
    doc.saveas(path)
    return path


def test_symbol_name_equivalence_covers_all_table_classes():
    pairs = (
        ("A-LAYER", "a-layer"),
        ("Continuous", "CONTINUOUS"),
        ("Standard", "STANDARD"),
        ("BLOCK-A", "block-a"),
        ("DIM-A", "dim-a"),
    )
    for first, second in pairs:
        assert symbol_name_equal(first, second, "case_insensitive")
        assert not symbol_name_equal(first, second, "exact")


def test_layer_name_case_is_semantically_equal(project, tmp_path):
    def mutate(doc):
        doc.layers.get("A-BUILDING-OUTLINE").dxf.name = "a-building-outline"
        for entity in doc.modelspace():
            if entity.dxf.layer == "A-BUILDING-OUTLINE":
                entity.dxf.layer = "a-building-outline"

    path = _mutate(project, tmp_path, "lower_layer", mutate)
    result = validate_dxf(path, project.latest_cad_ir, project.profile)
    assert result.verdict == "pass"

    exact_profile = replace(project.profile, symbol_name_policy="exact")
    exact_result = validate_dxf(path, project.latest_cad_ir, exact_profile)
    assert exact_result.verdict == "fail"
    assert "LAYER_MISSING" in exact_result.codes


def test_text_style_case_is_semantically_equal(project, tmp_path):
    def mutate(doc):
        entity = _entity(
            doc.modelspace(), "SAMPLE-01", "point_marker_label"
        )
        entity.dxf.style = "standard"

    path = _mutate(project, tmp_path, "lower_text_style", mutate)
    result = validate_dxf(path, project.latest_cad_ir, project.profile)
    assert result.verdict == "pass"


def test_text_style_mismatch_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(
            doc.modelspace(), "SAMPLE-01", "point_marker_label"
        )
        entity.dxf.style = "Other"

    path = _mutate(project, tmp_path, "wrong_text_style", mutate)
    result = validate_dxf(path, project.latest_cad_ir, project.profile)
    assert result.verdict == "fail"
    issue = next(
        issue
        for issue in result.issues
        if issue.code == "TEXT_STYLE_MISMATCH"
    )
    assert issue.category == "profile_violation"


def test_required_symbol_tables_accept_case_differences(project, tmp_path):
    profile = replace(
        project.profile,
        required_blocks=("BLOCK-A",),
        required_dimstyles=("DIM-A",),
        required_text_styles=("Standard",),
    )
    source = project.output_dir / "living-mutations-002.dxf"
    doc = ezdxf.readfile(source)
    doc.blocks.new("block-a")
    doc.dimstyles.add("dim-a")
    path = tmp_path / "symbol_tables.dxf"
    doc.saveas(path)
    result = validate_dxf(path, project.latest_cad_ir, profile)
    assert result.verdict == "pass"


def test_missing_symbol_table_is_detected(project):
    profile = replace(
        project.profile, required_blocks=("BLOCK-MISSING",)
    )
    source = project.output_dir / "living-mutations-002.dxf"
    result = validate_dxf(source, project.latest_cad_ir, profile)
    assert result.verdict == "fail"
    issue = next(
        issue for issue in result.issues if issue.code == "BLOCK_MISSING"
    )
    assert issue.category == "profile_violation"


def _ring_ir(project, multipolygon):
    cad_object = CadObject(
        object_id="MP-RING-001",
        object_class="building_footprint",
        geometry=geometry_to_geojson(multipolygon),
        geometry_revision=1,
        layer_key="A-BUILDING-OUTLINE",
        representation_kind="polygon_ring",
        source_world="canonical_current",
        provenance={
            "source_trace_ref": "TRACE-MP-RING",
            "canonical_object_id": "MP-RING-001",
            "canonical_revisions": {
                "semantic": 1,
                "geometry": 1,
                "parameter": 0,
            },
        },
    )
    return CadIR(
        project={
            "project_id": "MP-RING-001",
            "built_from_scene_revision": 1,
            "units": project.profile.units,
            "coordinate_frame_ref": project.profile.coordinate_frame_ref,
            "coordinate_state": project.profile.coordinate_state,
            "profile_ref": project.profile.profile_id,
            "profile_version": project.profile.profile_version,
        },
        objects=(cad_object,),
        dependency_fingerprint="ring-key-stability",
    )


def _ring_keys(project, multipolygon, tmp_path, name):
    cad_ir = _ring_ir(project, multipolygon)
    path = tmp_path / f"{name}.dxf"
    compile_to_dxf(cad_ir, project.profile, path)
    readback = validate_dxf(path, cad_ir, project.profile)
    assert readback.verdict == "pass"
    return {
        (item["ring_role"], item["ring_key"])
        for item in readback.manifest["entities"]
        if item["entity_role"] == "polygon_ring"
    }


def test_ring_key_is_stable_when_sibling_part_is_inserted(project, tmp_path):
    part_a = Polygon([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)])
    part_b = Polygon(
        [(6.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0)],
        holes=[[(7.0, 1.0), (9.0, 1.0), (9.0, 3.0), (7.0, 3.0)]],
    )
    part_c = Polygon([(12.0, 0.0), (16.0, 0.0), (16.0, 4.0), (12.0, 4.0)])
    original = MultiPolygon([part_a, part_b])
    with_inserted_part = MultiPolygon([part_c, part_a, part_b])

    original_keys = _ring_keys(project, original, tmp_path, "rings_v1")
    shifted_keys = _ring_keys(
        project, with_inserted_part, tmp_path, "rings_v2"
    )
    assert original_keys <= shifted_keys
    assert len(original_keys) == 3
    assert len(shifted_keys) == 4


def test_serialization_difference_is_distinct_from_profile_violation(
    project, tmp_path
):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        entity.dxf.linetype = "DASHED"

    path = _mutate(project, tmp_path, "serialization", mutate)
    result = validate_dxf(path, project.latest_cad_ir, project.profile)
    assert result.verdict == "fail"
    profile_issue = next(
        issue
        for issue in result.issues
        if issue.code == "ENTITY_LINETYPE_OVERRIDE"
    )
    assert profile_issue.category == "profile_violation"
    if "AUDIT_FIX" in result.codes:
        serialization_issue = next(
            issue for issue in result.issues if issue.code == "AUDIT_FIX"
        )
        assert serialization_issue.category == "serialization_difference"


def test_readback_manifest_preserves_raw_and_canonical_geometry(project):
    entries = project.latest_manifest["entities"]
    ring = next(
        entry
        for entry in entries
        if entry["object_id"] == "B-001"
        and entry["entity_role"] == "polygon_ring"
    )
    assert ring["canonical_target"]["coords"]
    assert ring["raw_dxf_semantics"]["thickness"] == 0.0
    assert ring["raw_dxf_semantics"]["const_width"] == 0.0
    assert all(value == 0.0 for value in ring["raw_dxf_semantics"]["bulge"])
    assert ring["raw_dxf_semantics"]["extrusion"] == [0.0, 0.0, 1.0]

    label = next(
        entry
        for entry in entries
        if entry["entity_role"] == "point_marker_label"
    )
    assert label["canonical_target"]["style"] == "Standard"
    assert label["raw_dxf_semantics"]["style"] == "Standard"

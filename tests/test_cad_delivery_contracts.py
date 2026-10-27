from __future__ import annotations

from pathlib import Path

import ezdxf
import pytest
import yaml

from dgcad_cad import (
    DeliveryProfile,
    validate_cad_ir,
    validate_dxf,
)
from dgcad_e2e import run_living_pipeline

E2E_FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "e2e"
    / "living-pipeline-001.yaml"
)
XDATA_APPID = "DESIGN_GRADE"


@pytest.fixture(scope="module")
def pipeline_artifacts(tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("cad-delivery")
    result = run_living_pipeline(E2E_FIXTURE, output_dir)
    data = yaml.safe_load(E2E_FIXTURE.read_text(encoding="utf-8"))
    profile = DeliveryProfile.from_dict(data["delivery"])
    return result, profile


def _xdata(entity):
    if not entity.has_xdata(XDATA_APPID):
        return None
    return list(entity.get_xdata(XDATA_APPID))


def _entity_with_object_id(msp, object_id: str, role: str | None = None):
    for entity in msp:
        values = _xdata(entity)
        if not values:
            continue
        if str(values[0][1]) != object_id:
            continue
        if role is not None and str(values[5][1]) != role:
            continue
        return entity
    raise AssertionError(f"entity {object_id}/{role} not found")


def _save_copy(source: Path, target: Path, mutate) -> Path:
    doc = ezdxf.readfile(source)
    mutate(doc)
    doc.saveas(target)
    return target


def test_cad_ir_maps_canonical_objects_with_revisions_and_worlds(
    pipeline_artifacts,
):
    result, _ = pipeline_artifacts
    cad_ir = result.cad_ir
    ids = {obj.object_id for obj in cad_ir.objects}
    assert {
        "SITE-001",
        "G-001",
        "B-001",
        "B-002",
        "B-003",
        "R-001",
        "R-002",
        "SAMPLE-01",
        "SAMPLE-02",
        "SAMPLE-03",
        "SAMPLE-04",
    } == ids
    for obj in cad_ir.objects:
        assert obj.provenance
        assert "canonical_revisions" in obj.provenance
        if obj.object_class in {
            "site_boundary",
            "green_space",
            "building_footprint",
            "road_centerline",
        }:
            assert obj.source_world == "canonical_current"
            assert obj.provenance["canonical_object_id"] == obj.object_id
        if obj.object_class == "environment_sensor":
            assert obj.source_world == "analysis"
    roads = {
        obj.object_id: obj
        for obj in cad_ir.objects
        if obj.object_class == "road_centerline"
    }
    assert roads["R-001"].provenance["source_trace_ref"] == "TRACE-R-001"
    assert roads["R-002"].provenance["source_trace_ref"] == "TRACE-R-002"
    building = next(
        obj for obj in cad_ir.objects if obj.object_id == "B-002"
    )
    assert building.massing["height_state"] == "unknown"
    assert building.massing["height_m"] is None


def test_cad_ir_validation_keeps_unknown_height_as_warning(pipeline_artifacts):
    result, profile = pipeline_artifacts
    validation = validate_cad_ir(result.cad_ir, profile)
    assert validation.verdict == "pass_with_scope_limits"
    assert "UNKNOWN_HEIGHT_ALLOWED" in validation.codes
    assert "INVALID_GEOMETRY" not in validation.codes


def test_compile_and_readback_are_semantically_equal(pipeline_artifacts):
    result, profile = pipeline_artifacts
    assert result.dxf_path.exists()
    assert result.dxf_compile.entity_count == 15
    assert result.dxf_compile.audit_errors == 0
    assert result.dxf_compile.audit_fixes == 0
    readback = validate_dxf(result.dxf_path, result.cad_ir, profile)
    assert readback.verdict == "pass"
    assert readback.manifest["entity_count"] == 15
    assert readback.manifest["expected_entity_count"] == 15
    assert readback.manifest["audit_errors"] == 0
    assert readback.manifest["audit_fixes"] == 0
    assert (
        readback.manifest["cad_ir_dependency_fingerprint"]
        == result.cad_ir.dependency_fingerprint
    )
    assert "B-001" in readback.manifest["object_ids"]
    assert "R-001" in readback.manifest["object_ids"]


def test_readback_detects_vertex_mutation(pipeline_artifacts, tmp_path):
    result, profile = pipeline_artifacts

    def mutate(doc):
        entity = _entity_with_object_id(
            doc.modelspace(), "B-001", "polygon_ring"
        )
        points = list(entity.get_points("xy"))
        points[0] = (points[0][0] + 0.5, points[0][1])
        entity.set_points(points, format="xy")

    mutated = _save_copy(result.dxf_path, tmp_path / "vertex.dxf", mutate)
    readback = validate_dxf(mutated, result.cad_ir, profile)
    assert readback.verdict == "fail"
    assert "COORDINATE_MISMATCH" in readback.codes


def test_readback_detects_unexpected_layer(pipeline_artifacts, tmp_path):
    result, profile = pipeline_artifacts

    def mutate(doc):
        doc.layers.add("UNEXPECTED-LAYER", color=7)

    mutated = _save_copy(result.dxf_path, tmp_path / "layer.dxf", mutate)
    readback = validate_dxf(mutated, result.cad_ir, profile)
    assert readback.verdict == "fail"
    assert "UNEXPECTED_LAYER" in readback.codes


def test_readback_detects_entity_type_substitution_without_crashing(
    pipeline_artifacts, tmp_path
):
    result, profile = pipeline_artifacts

    def mutate(doc):
        msp = doc.modelspace()
        entity = _entity_with_object_id(msp, "B-001", "polygon_ring")
        values = _xdata(entity)
        msp.delete_entity(entity)
        circle = msp.add_circle(
            (13.0, 15.0), 0.5, dxfattribs={"layer": "A-BUILDING-OUTLINE"}
        )
        circle.set_xdata(XDATA_APPID, values)

    mutated = _save_copy(result.dxf_path, tmp_path / "type.dxf", mutate)
    readback = validate_dxf(mutated, result.cad_ir, profile)
    assert readback.verdict == "fail"
    assert "ENTITY_TYPE_MISMATCH" in readback.codes


@pytest.mark.xfail(
    reason="DEV-CAD-003 / issue #3: bulge is not validated in E2E-001",
    strict=True,
)
def test_known_gap_bulge_mutation_is_not_detected(pipeline_artifacts, tmp_path):
    result, profile = pipeline_artifacts

    def mutate(doc):
        entity = _entity_with_object_id(
            doc.modelspace(), "B-001", "polygon_ring"
        )
        points = list(entity.get_points("xyb"))
        points[0] = (points[0][0], points[0][1], 0.5)
        entity.set_points(points, format="xyb")

    mutated = _save_copy(result.dxf_path, tmp_path / "bulge.dxf", mutate)
    readback = validate_dxf(mutated, result.cad_ir, profile)
    assert readback.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-003 / issue #3: constant width is not validated in E2E-001",
    strict=True,
)
def test_known_gap_constant_width_mutation_is_not_detected(
    pipeline_artifacts, tmp_path
):
    result, profile = pipeline_artifacts

    def mutate(doc):
        entity = _entity_with_object_id(
            doc.modelspace(), "B-001", "polygon_ring"
        )
        entity.dxf.const_width = 2.0

    mutated = _save_copy(result.dxf_path, tmp_path / "width.dxf", mutate)
    readback = validate_dxf(mutated, result.cad_ir, profile)
    assert readback.verdict == "fail"


def test_third_party_roundtrip_is_not_claimed(pipeline_artifacts):
    result, _ = pipeline_artifacts
    assert any(
        "no third-party CAD round-trip" in limit
        for limit in result.dxf_readback.coverage_limits
    )

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ezdxf
import pytest
import yaml
from shapely.geometry import MultiPolygon, Polygon

from dgcad_cad import (
    CadIR,
    CadObject,
    DxfIssue,
    compile_to_dxf,
    validate_dxf,
)
from dgcad_cad.validator import DEFAULT_CATEGORY, ISSUE_CATEGORIES
from dgcad_domain import geometry_to_geojson
from dgcad_e2e import LivingProject

E2E_FIXTURE = (
    Path(__file__).resolve().parents[2]
    / "fixtures"
    / "e2e"
    / "living-pipeline-001.yaml"
)
XDATA_APPID = "DESIGN_GRADE"


@pytest.fixture()
def project(tmp_path):
    living = LivingProject.create(E2E_FIXTURE, tmp_path / "project")
    living.bootstrap()
    return living


def _xdata(entity):
    if not entity.has_xdata(XDATA_APPID):
        return None
    return list(entity.get_xdata(XDATA_APPID))


def _entity(doc, object_id: str, role: str):
    msp = doc.modelspace() if hasattr(doc, "modelspace") else doc
    for entity in msp:
        values = _xdata(entity)
        if not values:
            continue
        if str(values[0][1]) != object_id:
            continue
        if str(values[5][1]) != role:
            continue
        return entity
    raise AssertionError(f"entity {object_id}/{role} not found")


def _mutate(project, tmp_path, name: str, mutate):
    source = project.output_dir / "living-mutations-002.dxf"
    doc = ezdxf.readfile(source)
    mutate(doc)
    path = tmp_path / f"{name}.dxf"
    doc.saveas(path)
    return validate_dxf(path, project.latest_cad_ir, project.profile)


# ---------------------------------------------------------------------------
# Positive adversarial checks (current validator handles these)
# ---------------------------------------------------------------------------


def test_lwpolyline_elevation_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        entity.dxf.elevation = 5.0

    result = _mutate(project, tmp_path, "elevation", mutate)
    assert result.verdict == "fail"
    issue = next(issue for issue in result.issues if issue.code == "NONZERO_Z")
    assert issue.category == "cad_format_semantics"


def test_multipolygon_two_parts_and_hole_roundtrip(project, tmp_path):
    multipolygon = MultiPolygon(
        [
            Polygon([(0.0, 0.0), (4.0, 0.0), (4.0, 4.0), (0.0, 4.0)]),
            Polygon(
                [(6.0, 0.0), (10.0, 0.0), (10.0, 4.0), (6.0, 4.0)],
                holes=[[(7.0, 1.0), (9.0, 1.0), (9.0, 3.0), (7.0, 3.0)]],
            ),
        ]
    )
    cad_object = CadObject(
        object_id="MP-001",
        object_class="building_footprint",
        geometry=geometry_to_geojson(multipolygon),
        geometry_revision=1,
        layer_key="A-BUILDING-OUTLINE",
        representation_kind="polygon_ring",
        source_world="canonical_current",
        provenance={
            "source_trace_ref": "TRACE-MP-001",
            "canonical_object_id": "MP-001",
            "canonical_revisions": {
                "semantic": 1,
                "geometry": 1,
                "parameter": 0,
            },
        },
    )
    cad_ir = CadIR(
        project={
            "project_id": "MP-001",
            "canonical_scene_revision": 1,
            "units": project.profile.units,
            "coordinate_frame_ref": project.profile.coordinate_frame_ref,
            "coordinate_state": project.profile.coordinate_state,
            "profile_ref": project.profile.profile_id,
            "profile_version": project.profile.profile_version,
        },
        objects=(cad_object,),
        dependency_fingerprint="multipolygon-fixture",
    )
    path = tmp_path / "multipolygon.dxf"
    compiled = compile_to_dxf(cad_ir, project.profile, path)
    readback = validate_dxf(path, cad_ir, project.profile)
    assert compiled.entity_count == 3
    assert compiled.audit_errors == 0
    assert readback.verdict == "pass"
    rings = sorted(
        (item["part_index"], item["ring_index"], item["ring_role"])
        for item in readback.manifest["entities"]
    )
    assert rings == [(0, 0, "outer"), (1, 1, "outer"), (1, 2, "hole")]


def test_symbol_table_name_case_is_semantically_equal(project, tmp_path):
    def mutate(doc):
        doc.layers.get("A-BUILDING-OUTLINE").dxf.linetype = "Continuous"

    result = _mutate(project, tmp_path, "linetype_case", mutate)
    assert result.verdict == "pass"
    assert "LAYER_PROPERTY_MISMATCH" not in result.codes


def test_missing_xdata_is_structured(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        entity.discard_xdata(XDATA_APPID)

    result = _mutate(project, tmp_path, "missing_xdata", mutate)
    assert result.verdict == "fail"
    issue = next(
        issue for issue in result.issues if issue.code == "MISSING_XDATA"
    )
    assert issue.category == "interoperability"


def test_delivery_comparison_artifact_has_required_fields(project):
    path = project.output_dir / "delivery-comparison.json"
    assert path.exists()
    comparison = json.loads(path.read_text(encoding="utf-8"))
    assert comparison["schema_id"] == "dgcad.e2e.delivery-comparison.v0.1"
    assert comparison["object_ids"] == sorted(
        obj.object_id for obj in project.latest_cad_ir.objects
    )
    assert (
        comparison["cad_ir_dependency_fingerprint"]
        == project.latest_cad_ir.dependency_fingerprint
    )
    assert comparison["dxf_readback_verdict"] == "pass"
    assert comparison["audit_errors"] == 0
    assert comparison["manifest_ref"] == "readback-manifest-002.json"
    assert comparison["profile_id"] == project.profile.profile_id
    assert comparison["canonical_revisions"]["B-001"]["geometry"] == 1
    dxf_path = project.output_dir / "living-mutations-002.dxf"
    manifest_path = project.output_dir / comparison["manifest_ref"]
    assert comparison["dxf_sha256"] == hashlib.sha256(
        dxf_path.read_bytes()
    ).hexdigest()
    assert comparison["dxf_sha256"] == project.latest_manifest["dxf_sha256"]
    assert comparison["readback_manifest_sha256"] == hashlib.sha256(
        manifest_path.read_bytes()
    ).hexdigest()


def test_issue_categories_are_complete_and_contract_synced():
    contract_path = (
        Path(__file__).resolve().parents[2]
        / "contracts"
        / "e2e-adversarial-v0.1.yaml"
    )
    contract = yaml.safe_load(contract_path.read_text(encoding="utf-8"))
    declared = {
        code
        for group in contract["issue_categories"].values()
        for code in group.get("codes", [])
    }
    assert set(ISSUE_CATEGORIES) == declared
    assert DEFAULT_CATEGORY == "unclassified"
    assert (
        DxfIssue("UNKNOWN_FUTURE_CODE", "error", None, "future").category
        == "unclassified"
    )


def test_issue_categories_distinguish_failure_domains(project, tmp_path):
    def unexpected_layer(doc):
        doc.layers.add("UNEXPECTED-LAYER")

    layer_result = _mutate(project, tmp_path, "cat_layer", unexpected_layer)
    layer_issue = next(
        issue
        for issue in layer_result.issues
        if issue.code == "UNEXPECTED_LAYER"
    )
    assert layer_issue.category == "profile_violation"

    def vertex_mutation(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        points = list(entity.get_points("xy"))
        points[0] = (points[0][0] + 0.5, points[0][1])
        entity.set_points(points, format="xy")

    vertex_result = _mutate(project, tmp_path, "cat_vertex", vertex_mutation)
    vertex_issue = next(
        issue
        for issue in vertex_result.issues
        if issue.code == "COORDINATE_MISMATCH"
    )
    assert vertex_issue.category == "cad_format_semantics"


# ---------------------------------------------------------------------------
# Strict xfails: known gaps with accurate issue mapping
# ---------------------------------------------------------------------------


@pytest.mark.xfail(
    reason="DEV-CAD-010 / issue #18: CIRCLE center Z is not validated",
    strict=True,
)
def test_circle_nonzero_z_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "SAMPLE-01", "point_marker")
        entity.dxf.center = (35.0, 5.0, 5.0)

    result = _mutate(project, tmp_path, "circle_z", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-010 / issue #18: TEXT insertion Z is not validated",
    strict=True,
)
def test_text_nonzero_z_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(
            doc.modelspace(), "SAMPLE-01", "point_marker_label"
        )
        entity.dxf.insert = (35.3, 5.3, 5.0)

    result = _mutate(project, tmp_path, "text_z", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-010 / issue #18: TEXT rotation is not validated",
    strict=True,
)
def test_text_rotation_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(
            doc.modelspace(), "SAMPLE-01", "point_marker_label"
        )
        entity.dxf.rotation = 90.0

    result = _mutate(project, tmp_path, "text_rotation", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-010 / issue #18: TEXT width/alignment is not validated",
    strict=True,
)
def test_text_width_and_alignment_are_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(
            doc.modelspace(), "SAMPLE-01", "point_marker_label"
        )
        entity.dxf.width = 2.0
        entity.dxf.halign = 1
        entity.dxf.valign = 1

    result = _mutate(project, tmp_path, "text_alignment", mutate)
    assert result.verdict == "fail"


STYLE_MUTATIONS = (
    pytest.param(
        "color",
        lambda entity: setattr(entity.dxf, "color", 1),
        id="color",
    ),
    pytest.param(
        "linetype",
        lambda entity: setattr(entity.dxf, "linetype", "DASHED"),
        id="linetype",
    ),
    pytest.param(
        "lineweight",
        lambda entity: setattr(entity.dxf, "lineweight", 211),
        id="lineweight",
    ),
    pytest.param(
        "true_color",
        lambda entity: setattr(entity.dxf, "true_color", 0xFF0000),
        id="true_color",
    ),
    pytest.param(
        "transparency",
        lambda entity: setattr(entity.dxf, "transparency", 0x020000FF),
        id="transparency",
    ),
)


@pytest.mark.parametrize("name,mutation", STYLE_MUTATIONS)
@pytest.mark.xfail(
    reason="DEV-CAD-009 / issue #17: entity style overrides are not validated",
    strict=True,
)
def test_entity_style_override_is_detected(project, tmp_path, name, mutation):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        mutation(entity)

    result = _mutate(project, tmp_path, f"style_{name}", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-003 / issue #3: LWPOLYLINE start/end width is not validated",
    strict=True,
)
def test_lwpolyline_start_end_width_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        points = list(entity.get_points("xyseb"))
        points[0] = (points[0][0], points[0][1], 1.0, 1.0, points[0][4])
        entity.set_points(points, format="xyseb")

    result = _mutate(project, tmp_path, "start_end_width", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-003 / issue #3: LWPOLYLINE thickness is not validated",
    strict=True,
)
def test_lwpolyline_thickness_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        entity.dxf.thickness = 2.0

    result = _mutate(project, tmp_path, "thickness", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-003 / issue #3: LWPOLYLINE extrusion is not validated",
    strict=True,
)
def test_lwpolyline_extrusion_is_detected(project, tmp_path):
    def mutate(doc):
        entity = _entity(doc.modelspace(), "B-001", "polygon_ring")
        entity.dxf.extrusion = (0.0, 0.0, -1.0)

    result = _mutate(project, tmp_path, "extrusion", mutate)
    assert result.verdict == "fail"


@pytest.mark.xfail(
    reason="DEV-CAD-007 / issue #7: validator errors are not structured",
    strict=True,
)
def test_validator_error_is_structured(project, tmp_path):
    bad = tmp_path / "malformed.dxf"
    bad.write_text("not a dxf file", encoding="utf-8")
    result = validate_dxf(
        bad, project.latest_cad_ir, project.profile
    )
    assert result.verdict == "fail"
    assert any(issue.code == "VALIDATOR_ERROR" for issue in result.issues)

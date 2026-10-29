"""M4d full-site (A-102) DXF / evidence tests.

These tests generate the full-site sheet into a temporary directory from the
current case fixtures and assert the delivery properties the sheet must keep:

* all 55 buildings appear with their design geometry (footprint + unit lines +
  label) — not just the 7 focus buildings;
* the DXF readback counts are consistent with the CAD-IR (one entity per ring /
  line / text) and the 11-field XDATA contract is intact on every entity;
* the privacy scan passes and every object stays ``design_draft`` /
  ``human_confirmed: False``;
* the title block keeps the non-claim text;
* the drawing is deterministic in content (the DXF bytes are not: ezdxf header
  timestamps/GUIDs are volatile, so determinism is checked on the canonical
  readback manifest, not on the file hash);
* the focus sheet (A-101) drawing rules are unchanged: it still draws exactly
  the focus buildings, never the context buildings.

The fixture is module-scoped because road generation dominates the runtime
(~20 s); the tests reuse the same built models.
"""
from __future__ import annotations

import json
from pathlib import Path

import ezdxf
import pytest

from dgcad_cad import compile_to_dxf, validate_dxf
from dgcad_cad.dxf import XDATA_APPID, XDATA_FIELDS
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.drawing import (
    FULL_SITE_PLAN_ORIGIN,
    FULL_SITE_PLAN_SCALE,
    build_drawing_elements,
    build_full_site_drawing_elements,
)
from dgcad_design.project import (
    FULL_SITE_PROJECT_ID,
    FULL_SITE_SCENE_ID,
    build_design_cad_ir,
    build_full_site_models,
    run_full_site_evidence,
)
from dgcad_design.scene import design_scene
from dgcad_domain import parse_geometry
from dgcad_e2e import scan_dxf_privacy
from shapely.geometry import box

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
FRAME = box(10.0, 290.0, 560.0, 670.0)


@pytest.fixture(scope="module")
def models():
    return build_full_site_models(CASE, BASIS, PROFILE)


@pytest.fixture(scope="module")
def evidence(models, tmp_path_factory):
    output_dir = tmp_path_factory.mktemp("full-site-evidence")
    summary = run_full_site_evidence(
        CASE, BASIS, PROFILE, output_dir, models=models
    )
    return summary, output_dir


def _load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


def _xdata(entity):
    if not entity.has_xdata(XDATA_APPID):
        return None
    return list(entity.get_xdata(XDATA_APPID))


def _object_ids(msp) -> set[str]:
    ids = set()
    for entity in msp:
        values = _xdata(entity)
        if values:
            ids.add(str(values[0][1]))
    return ids


def _texts(msp) -> list[str]:
    return [
        entity.dxf.text
        for entity in msp
        if entity.dxftype() == "TEXT"
    ]


def _read_doc(evidence):
    summary, output_dir = evidence
    return summary, output_dir, ezdxf.readfile(
        output_dir / "full-site-proposal.dxf"
    )


def _open_space_ratio(metrics) -> float | None:
    """Auxiliary open-space tiling ratio (renamed during M4d-1a)."""
    for key in (
        "full_site_potential_open_space_ratio",
        "full_site_open_space_account_ratio",
        "full_site_open_space_ratio",
        "full_site_designed_green_ratio",
    ):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _open_space_target(metrics) -> float | None:
    for key in (
        "full_site_green_target_ratio",
        "full_site_open_space_account_target_ratio",
        "target_ratio",
    ):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _open_space_parcel_count(metrics) -> int | None:
    for key in (
        "full_site_open_space_account_parcel_count",
        "full_site_green_parcel_count",
    ):
        value = metrics.get(key)
        if isinstance(value, int):
            return value
    return None


def _open_space_block(summary):
    """The auxiliary potential-open-space account (never the designed-green one)."""
    block = summary.get("full_site_open_space_account")
    if block:
        return block
    full_site_green = summary.get("full_site_green") or {}
    return full_site_green.get("open_space_account") or full_site_green


def test_full_site_evidence_contains_all_55_buildings(evidence, models):
    summary, output_dir, doc = _read_doc(evidence)
    msp = doc.modelspace()
    layout = models["building_layout"]
    building_ids = {item.building_id for item in layout.buildings}
    assert len(building_ids) == 55
    assert summary["building_count"] == 55
    assert summary["unit_count"] == 109
    assert summary["households"] == 2398

    object_ids = _object_ids(msp)
    assert {f"B-{building_id}" for building_id in building_ids} <= object_ids
    texts = _texts(msp)
    for building_id in building_ids:
        assert any(building_id in text for text in texts), building_id

    footprints = [
        entity
        for entity in msp
        if entity.dxftype() == "LWPOLYLINE"
        and entity.dxf.layer == "A-BUILDING-OUTLINE"
        and _xdata(entity)
        and str(_xdata(entity)[1][1]) == "building_footprint"
    ]
    assert len(footprints) == 55
    unit_lines = [
        object_id for object_id in object_ids if object_id.startswith("UL-")
    ]
    assert len(unit_lines) == sum(
        len(item.unit_lines) for item in layout.buildings
    )
    headings = [
        object_id
        for object_id in object_ids
        if object_id.startswith("LBL-") and object_id.endswith("-HEAD")
    ]
    assert len(headings) == 55


def test_full_site_geometry_is_the_scaled_design_geometry(evidence, models):
    _, _, doc = _read_doc(evidence)
    elements = {
        element.element_id: element
        for element in build_full_site_drawing_elements(
            models["design_input"],
            models["intent"],
            models["building_layout"],
            models["road_layout"],
            models["green_layout"],
            models["parking_layout"],
            models["basis"],
            models["metrics"],
        )
    }
    assert len(elements) == len(
        design_scene(
            tuple(elements.values()),
            models["basis"],
            scene_id="check",
        ).objects
    )
    for building in models["building_layout"].buildings:
        geometry = parse_geometry(elements[f"B-{building.building_id}"].geometry)
        assert geometry.area == pytest.approx(
            building.footprint.area * FULL_SITE_PLAN_SCALE**2, rel=1e-9
        )
        assert FRAME.contains(geometry), building.building_id
        assert geometry.is_valid


def test_full_site_readback_counts_are_consistent(evidence):
    summary, output_dir, doc = _read_doc(evidence)
    msp = doc.modelspace()
    manifest = _load_json(output_dir / "full-site-readback-manifest.json")
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["codes"] == []
    assert manifest["entity_count"] == len(msp)
    assert manifest["expected_entity_count"] == manifest["entity_count"]
    assert summary["dxf"]["entity_count"] == manifest["entity_count"]
    assert len(manifest["object_ids"]) == summary["scene_object_count"]
    assert manifest["confirmation_scopes"] == ["design_draft"]
    assert manifest["audit_errors"] == 0
    assert manifest["audit_fixes"] == 0
    # entity_count must exceed the focus sheet: the full site adds 48 buildings
    # plus their unit lines/labels and the full road/green set.
    assert manifest["entity_count"] > 211


def test_full_site_xdata_keeps_the_eleven_field_contract(evidence):
    _, _, doc = _read_doc(evidence)
    expected_codes = [1000, 1000, 1070, 1000, 1000, 1000, 1070, 1070,
                      1000, 1000, 1000]
    entities = list(doc.modelspace())
    assert entities
    for entity in entities:
        values = _xdata(entity)
        assert values is not None, entity.dxftype()
        assert len(values) == 11
        assert len(values) == len(XDATA_FIELDS)
        assert [tag[0] for tag in values] == expected_codes
        assert str(values[0][1])
        assert str(values[10][1]) == "design_draft"


def test_full_site_privacy_and_authority_are_non_claims(evidence):
    summary, output_dir, _ = _read_doc(evidence)
    assert summary["privacy"]["ok"] is True
    assert scan_dxf_privacy(output_dir / "full-site-proposal.dxf")["ok"] is True
    assert summary["human_confirmed"] is False
    assert summary["design_authority"] == "rule_derived"
    assert summary["status"] == "autonomous_full_site_draft"
    assert summary["readback"]["confirmation_scopes"] == ["design_draft"]
    assert summary["non_claims"]
    assert any(
        "not a construction or permit drawing" in claim
        for claim in summary["non_claims"]
    )


def test_full_site_title_block_stays_non_claiming(evidence):
    _, _, doc = _read_doc(evidence)
    texts = _texts(doc.modelspace())
    joined = " | ".join(texts)
    assert "CASE-SKETCH-001 / AUTONOMOUS DESIGN DRAFT" in joined
    assert "NOT HUMAN-CONFIRMED" in joined
    assert "NOT CODE-COMPLIANCE" in joined
    assert "FULL SITE" in joined
    assert "55B / 109U" in joined
    assert "SCALE 1:2000 (A2)" in joined
    assert "SHEET A-102" in joined
    assert "human_confirmed" not in joined
    assert "HUMAN_CONFIRMED" not in joined


def test_full_site_title_declares_incomplete_green_semantics(evidence):
    """The sheet must not present the 61% open-space tiling as designed green."""
    summary, _, doc = _read_doc(evidence)
    texts = _texts(doc.modelspace())
    joined = " | ".join(texts)
    metrics = summary["metrics"]
    designed = metrics["designed_green_ratio"]
    potential = _open_space_ratio(metrics)
    target = _open_space_target(metrics)
    assert potential is not None
    assert target is not None
    # Legacy designed green (cluster+strip) is incomplete, and the sheet says so.
    assert designed < target
    assert (
        f"DESIGNED GREEN {designed * 100:.2f}% - INCOMPLETE" in joined
    )
    assert (
        f"POTENTIAL OPEN SPACE {potential * 100:.2f}% - NOT LANDSCAPE DESIGN"
        in joined
    )
    assert "INCOMPLETE: ROAD ACCESS 0/17" in joined
    assert "DEAD ENDS 17 UNRESOLVED" in joined
    assert "DESIGNED GREEN < 30%" in joined
    # Never present the auxiliary open-space account as green.
    assert "GREEN 61.1" not in joined
    assert "DESIGNED GREEN 61" not in joined
    assert f"GREEN {potential * 100:.1f}%" not in joined


def test_full_site_drawing_is_deterministic(models, tmp_path):
    first = build_full_site_drawing_elements(
        models["design_input"],
        models["intent"],
        models["building_layout"],
        models["road_layout"],
        models["green_layout"],
        models["parking_layout"],
        models["basis"],
        models["metrics"],
    )
    second = build_full_site_drawing_elements(
        models["design_input"],
        models["intent"],
        models["building_layout"],
        models["road_layout"],
        models["green_layout"],
        models["parking_layout"],
        models["basis"],
        models["metrics"],
    )
    assert first == second
    assert [element.element_id for element in first] == [
        element.element_id for element in second
    ]

    manifests = []
    entity_counts = []
    for index, elements in enumerate((first, second)):
        scene = design_scene(
            elements, models["basis"], scene_id=FULL_SITE_SCENE_ID
        )
        cad_ir = build_design_cad_ir(
            scene,
            models["profile"],
            models["basis"],
            models["metrics"],
            project_id=FULL_SITE_PROJECT_ID,
        )
        dxf_path = (
            tmp_path / f"determinism-{index}" / "full-site-proposal.dxf"
        )
        result = compile_to_dxf(cad_ir, models["profile"], dxf_path)
        readback = validate_dxf(dxf_path, cad_ir, models["profile"])
        assert readback.verdict == "pass"
        entity_counts.append(result.entity_count)
        manifest = dict(readback.manifest)
        # The DXF file hash is volatile (ezdxf header timestamps/GUIDs); the
        # canonical readback manifest is the deterministic content artefact.
        manifest.pop("dxf_sha256", None)
        manifests.append(manifest)
    assert entity_counts[0] == entity_counts[1]
    assert manifests[0] == manifests[1]


def test_focus_sheet_still_draws_only_the_focus_buildings(models):
    design_input = models["design_input"]
    intent = models["intent"]
    basis = models["basis"]
    if models["layout_source"] == "focus_region_fallback":
        # The current full-site models already use the focus-region layout.
        focus_layout = models["building_layout"]
    else:
        standardized = standardize_all(design_input, basis)
        design_rect = find_focus_design_rect(design_input, intent, basis)
        focus_layout = layout_focus_region(
            design_input,
            intent,
            basis,
            standardized,
            design_input.site_boundary.buffer(-basis.boundary_setback_m),
            design_rect,
        )
    elements = build_drawing_elements(
        design_input,
        intent,
        focus_layout,
        models["road_layout"],
        models["green_layout"],
        models["parking_layout"],
        basis,
        models["metrics"],
    )
    drawn_buildings = {
        element.element_id.removeprefix("B-")
        for element in elements
        if element.element_id.startswith("B-")
    }
    assert drawn_buildings == {
        item.building_id for item in focus_layout.focus_buildings
    }
    assert len(drawn_buildings) == 7
    assert not any(
        "SHEET A-102" in (element.text or "") for element in elements
    )
    assert all(
        element.layer_key in models["profile"].layers
        for element in elements
    )


def test_full_site_models_are_explicit_about_the_layout_source(models):
    assert models["layout_source"] in {
        "focus_region_fallback",
        "full_site_layout",
        "supplied",
    }
    layout = models["building_layout"]
    assert len(layout.buildings) == 55
    assert len(layout.focus_buildings) == 7
    assert sum(item.unit_count for item in layout.buildings) == 109
    assert sum(item.households for item in layout.buildings) == 2398
    # The sheet transform must be an exact 1:2000 affine map.
    assert FULL_SITE_PLAN_SCALE == 0.5
    assert FULL_SITE_PLAN_ORIGIN == (30.0, 320.0)


def test_full_site_metrics_match_the_measured_geometry(models):
    metrics = models["metrics"]
    assert metrics["building_count"] == 55
    assert metrics["unit_count"] == 109
    assert metrics["households"] == 2398
    assert metrics["focus_building_count"] == 7
    assert metrics["road_groups_total"] == 17
    assert metrics["road_access_relation_error_count"] == len(
        models["road_access"].relation_errors
    )
    if models["layout_source"] != "full_site_layout":
        pytest.skip("full-site layout engine not available in this tree")
    required = metrics["road_clearance_required_m"]
    assert required == 3.0
    assert metrics["min_road_clearance_m"] >= required - 1e-9
    assert metrics["road_clearance_violation_count"] == 0
    assert metrics["min_ns_spacing_m"] == pytest.approx(20.0, abs=0.01)
    assert metrics["ns_spacing_violation_count"] == 0
    # The legacy designed-green account stays the incomplete one; the open-space
    # tiling is an auxiliary account and is never used to claim the target.
    target = _open_space_target(metrics)
    potential = _open_space_ratio(metrics)
    assert target is not None
    assert potential is not None
    assert metrics["designed_green_ratio"] < target
    assert potential >= target
    assert potential != pytest.approx(metrics["designed_green_ratio"])
    gap = metrics.get("full_site_open_space_account_gap_m2")
    if gap is None:
        gap = metrics.get("full_site_green_gap_m2")
    if gap is not None:
        assert gap == pytest.approx(0.0, abs=1e-6)
    designed_gap = metrics.get("full_site_green_gap_m2")
    if designed_gap is not None:
        assert designed_gap > 0.0
    assert _open_space_parcel_count(metrics) is not None
    assert _open_space_parcel_count(metrics) > 0


def test_full_site_roads_are_the_committed_design_network(models):
    geojson_path = (
        ROOT / "docs" / "e2e" / "design-synthesis-001" / "design-roads.geojson"
    )
    if not geojson_path.exists():
        pytest.skip("committed design-roads.geojson is not present")
    payload = _load_json(geojson_path)
    committed = {
        str(feature["id"]): feature["geometry"]["coordinates"]
        for feature in payload["features"]
    }
    assert len(committed) == 44
    roads = models["road_layout"].roads
    assert len(roads) == 44
    for road in roads:
        assert road.edge_id in committed
        coords = [
            [float(x), float(y)] for x, y in road.centerline.coords
        ]
        expected = committed[road.edge_id]
        assert len(coords) == len(expected), road.edge_id
        for (x1, y1), (x2, y2) in zip(coords, expected):
            assert abs(x1 - x2) <= 1e-6, road.edge_id
            assert abs(y1 - y2) <= 1e-6, road.edge_id


def test_full_site_potential_open_space_is_not_drawn_as_designed_green(
    evidence, models
):
    summary, _, doc = _read_doc(evidence)
    msp = doc.modelspace()
    potential_entities = [
        entity
        for entity in msp
        if entity.dxf.layer == "L-OPEN-SPACE"
        and _xdata(entity)
        and str(_xdata(entity)[1][1]) == "green_space"
    ]
    assert potential_entities
    # No open-space tiling polygon may be drawn on the designed-green layer.
    green_space_on_l_green = [
        entity
        for entity in msp
        if entity.dxf.layer == "L-GREEN"
        and _xdata(entity)
        and str(_xdata(entity)[1][1]) == "green_space"
    ]
    assert green_space_on_l_green == []
    assert "L-OPEN-SPACE" in {
        layer.dxf.name for layer in doc.layers
    }
    assert "L-OPEN-SPACE" in models["profile"].layers

    texts = _texts(msp)
    potential_labels = [
        text for text in texts if text.startswith("POTENTIAL OPEN SPACE ")
    ]
    assert potential_labels
    assert not any(
        text.startswith("DESIGNED GREEN ") and text.endswith("m2")
        for text in texts
    )
    assert "POTENTIAL OPEN SPACE (NOT LANDSCAPE DESIGN)" in texts
    assert "DESIGNED GREEN" in texts
    legend_labels = [
        text for text in texts if "NOT LANDSCAPE DESIGN" in text
    ]
    assert legend_labels
    block = _open_space_block(summary)
    assert block is not None
    parcel_count = block.get("parcel_count")
    if parcel_count is None:
        parcel_count = block.get("potential_open_space_parcel_count")
    assert parcel_count == _open_space_parcel_count(models["metrics"])
    ratio = block.get("ratio")
    if ratio is None:
        ratio = block.get("potential_open_space_ratio")
    assert ratio == pytest.approx(_open_space_ratio(models["metrics"]))

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ezdxf
import pytest
import yaml

from dgcad_design import (
    DesignBasis,
    build_design_intent,
    load_design_input,
    run_design_synthesis,
)
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.consistency import check_design
from dgcad_design.green import build_green_layout
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout
from dgcad_e2e import scan_dxf_privacy

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"


def load_basis() -> DesignBasis:
    return DesignBasis.from_dict(
        yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    )


def test_basis_math_hits_the_declared_constraints():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    assert design_input.site_area_m2 == pytest.approx(
        204122.7864634952, rel=1e-9
    )
    assert design_input.staircase_count == 109
    assert design_input.facility_count == 1
    households = basis.households(109)
    assert households == 2398
    assert basis.parking_spaces(households) == 2398
    assert basis.required_entrances(2398) == 5
    far = basis.far(design_input.site_area_m2, 109)
    assert 1.55 <= far <= 1.60
    assert far == pytest.approx(1.5654107291796402, rel=1e-9)
    assert basis.building_width(3) == 72.0
    assert basis.building_height_m() == 33.0
    assert basis.human_confirmed is False
    assert basis.design_authority == "rule_derived"


def test_basis_rejects_human_confirmation_and_short_spacing():
    data = yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    data["human_confirmed"] = True
    with pytest.raises(ValueError):
        DesignBasis.from_dict(data)
    data = yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    data["north_south_spacing_m"] = 19.0
    with pytest.raises(ValueError):
        DesignBasis.from_dict(data)


def test_design_input_loads_all_site_objects():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    assert len(design_input.buildings) == 55
    assert len(design_input.greens) == 12
    assert len(design_input.entrances) == 3
    assert len(design_input.roads) == 333
    assert len(design_input.road_graph.nodes) == 309
    assert len(design_input.road_graph.edges) == 333
    assert design_input.source_manifest["source_sketch_sha256"]


def test_intent_groups_and_focus_region():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    assert len(intent.groups) >= 10
    focus = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    assert focus.building_ids
    assert focus.unit_count >= 19
    assert intent.focus_building_ids == focus.building_ids
    assert intent.focus_bbox[0] < intent.focus_bbox[2]
    assert intent.focus_road_ids
    assert intent.principles
    assert intent.road_hierarchy["main_edges"] == 65


def test_focus_block_is_buildable_and_road_clear():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    rect = find_focus_design_rect(design_input, intent, basis)
    assert rect is not None
    minx, miny, maxx, maxy = rect
    assert maxx - minx >= 120.0
    assert maxy - miny >= 90.0
    assert design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    ).contains(
        __import__("shapely.geometry", fromlist=["box"]).box(*rect)
    )


def test_design_synthesis_end_to_end(tmp_path):
    summary = run_design_synthesis(
        CASE, BASIS, PROFILE, tmp_path / "design"
    )
    metrics = summary["metrics"]
    checks = {
        check["id"]: check
        for check in summary["consistency"]["checks"]
    }
    assert summary["status"] == "autonomous_design_draft"
    assert summary["design_authority"] == "rule_derived"
    assert summary["human_confirmed"] is False
    assert 1.55 <= metrics["far"] <= 1.60
    assert metrics["parking_spaces"] >= metrics["households"]
    assert metrics["parking_entrances"] >= metrics[
        "parking_entrances_required"
    ]
    assert metrics["focus_min_ns_gap_m"] >= 20.0 - 1e-6
    assert metrics["green_ratio"] >= 0.30
    assert metrics["road_components"] == 1
    for name in (
        "FAR_RANGE",
        "PARKING_MIN_ONE_PER_HOUSEHOLD",
        "PARKING_ENTRANCES",
        "UNIT_COUNT_PRESERVED",
        "FOCUS_NS_SPACING",
        "FOCUS_BOUNDARY_SETBACK",
        "FOCUS_BUILDING_OVERLAP",
        "FOCUS_ROAD_CLEARANCE",
        "ROAD_CONNECTIVITY",
        "ROAD_WIDTHS",
        "GREEN_RATIO",
    ):
        assert checks[name]["status"] == "pass", checks[name]
    assert checks["FULL_SITE_NS_SPACING"]["status"] == "deferred"
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["confirmation_scopes"] == ["design_draft"]
    assert summary["cad_ir_validation"]["verdict"] == (
        "pass_with_scope_limits"
    )
    assert {
        issue["code"] for issue in summary["cad_ir_validation"]["issues"]
    } == {"UNKNOWN_HEIGHT_ALLOWED"}
    assert summary["privacy"]["ok"] is True
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0

    dxf_path = tmp_path / "design" / "design-proposal.dxf"
    doc = ezdxf.readfile(dxf_path)
    layers = {layer.dxf.name for layer in doc.layers}
    for layer in (
        "A-BUILDING-OUTLINE",
        "A-UNIT-LINE",
        "C-ROAD-MAIN",
        "C-ROAD-BRANCH",
        "C-ROAD-ACCESS",
        "C-SIDEWALK",
        "L-GREEN",
        "A-TITLE",
        "A-LEGEND",
        "A-NORTH",
        "A-SCALE",
        "A-KEYPLAN",
    ):
        assert layer in layers
    texts = [
        entity.dxf.text
        for entity in doc.modelspace()
        if entity.dxftype() == "TEXT"
    ]
    assert any("AUTONOMOUS DESIGN DRAFT" in text for text in texts)
    assert any("NOT HUMAN-CONFIRMED" in text for text in texts)
    assert any("FAR 1.565" in text for text in texts)
    assert any("SK-BLD-0007" in text for text in texts)
    assert not any("human_confirmed" in text for text in texts)

    draft = json.loads(
        (tmp_path / "design" / "draft-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert draft["status"] == "autonomous_draft"
    assert draft["human_confirmed"] is False
    assert draft["design_authority"] == "rule_derived"
    scene = json.loads(
        (tmp_path / "design" / "scene-snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert scene["world"] == "proposal_preview"
    assert scene["objects"]
    assert {
        obj["authority_state"] for obj in scene["objects"]
    } == {"rule_derived"}


def test_design_diff_records_design_changes_and_drops():
    summary = json.loads(
        (EVIDENCE / "design-summary.json").read_text(encoding="utf-8")
    )
    diff = summary["diff"]
    assert len(diff["buildings"]) == 7
    assert diff["dropped_focus_building_ids"] == [
        "SK-BLD-0038",
        "SK-BLD-0061",
    ]
    assert diff["changed"]
    assert diff["preserved"]
    assert diff["roads"]["corridor_generator"] == (
        "round_buffer_hierarchy_v0.1"
    )
    assert diff["roads"]["not_professional_alignment"] is True
    assert diff["parking"]["proposed_entrances"] == 2
    assert diff["parking"]["existing_entrances"] == 3


def test_committed_design_evidence_is_consistent():
    summary = json.loads(
        (EVIDENCE / "design-summary.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (EVIDENCE / "readback-manifest.json").read_text(encoding="utf-8")
    )
    privacy = scan_dxf_privacy(EVIDENCE / "design-proposal.dxf")
    assert summary["status"] == "autonomous_design_draft"
    assert summary["human_confirmed"] is False
    assert summary["design_authority"] == "rule_derived"
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["confirmation_scopes"] == ["design_draft"]
    assert manifest["confirmation_scopes"] == ["design_draft"]
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0
    assert summary["focus_design_rect"] is not None
    assert summary["diff"]["focus_design_rect"] == summary["focus_design_rect"]
    assert hashlib.sha256(
        (EVIDENCE / "design-proposal.dxf").read_bytes()
    ).hexdigest() == summary["dxf"]["sha256"] == manifest["dxf_sha256"]
    assert privacy["ok"] is True
    assert (EVIDENCE / "design-preview.png").is_file()
    assert (EVIDENCE / "design-basis.yaml").is_file()
    assert (EVIDENCE / "design-diff.json").is_file()
    assert (EVIDENCE / "design-intent.json").is_file()

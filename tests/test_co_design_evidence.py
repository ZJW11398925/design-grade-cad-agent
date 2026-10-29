"""M4d-2 A/B co-design evidence contract tests (committed evidence)."""
from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

import ezdxf
import pytest
import yaml

from dgcad_cad import compile_to_dxf, validate_dxf
from dgcad_cad.dxf import XDATA_APPID, XDATA_FIELDS
from dgcad_e2e import scan_dxf_privacy
from dgcad_foundation import canonical_hash

from dgcad_design.basis import DesignBasis
from dgcad_design.buildings import standardize_all
from dgcad_design.input import load_design_input
from dgcad_design.intent import build_design_intent
from dgcad_design.project import build_design_cad_ir, build_full_site_models
from dgcad_design.scene import design_scene, scene_objects_for_export

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "e2e" / "design-co-design-001"
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
CANDIDATE_IDS = ("A", "B")


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def _load_candidate(candidate_id: str) -> dict:
    return _load(f"{candidate_id}/candidate-summary.json")


def _candidate_dxf(candidate_id: str):
    return ezdxf.readfile(
        EVIDENCE / candidate_id / f"candidate-{candidate_id.lower()}.dxf"
    )


def _xdata(entity):
    if not entity.has_xdata(XDATA_APPID):
        return None
    return list(entity.get_xdata(XDATA_APPID))


def _texts(msp) -> list[str]:
    return [
        entity.dxf.text
        for entity in msp
        if entity.dxftype() == "TEXT"
    ]


def _object_ids(msp) -> set[str]:
    ids = set()
    for entity in msp:
        values = _xdata(entity)
        if values:
            ids.add(str(values[0][1]))
    return ids


def test_candidates_are_complete_objects():
    payload = _load("candidates.json")
    candidates = {item["candidate_id"]: item for item in payload["candidates"]}
    assert set(candidates) == {"A", "B"}
    for item in candidates.values():
        assert item["building_count"] == 55
        assert item["unit_count"] == 109
        assert item["group_metrics"]["group_count"] == 17
        assert item["group_metrics"]["groups_preserved"] == 17
        assert item["group_metrics"]["missing_building_count"] == 0
        assert item["group_metrics"]["duplicate_building_count"] == 0
        assert item["access_truth"]["coverage"] == pytest.approx(1.0)
        assert item["access_truth"]["groups_served"] == 17
        assert item["access_truth"]["relation_error_count"] == 0
        assert item["access_truth"]["dead_ends"]["unresolved"] == 0


def test_candidate_a_fails_clearance_and_candidate_b_is_hard_valid():
    payload = _load("candidates.json")
    candidates = {item["candidate_id"]: item for item in payload["candidates"]}
    assert candidates["A"]["hard_ok"] is False
    assert candidates["A"]["failed_hard_checks"] == [
        "FULL_SITE_ROAD_CLEARANCE"
    ]
    assert candidates["B"]["hard_ok"] is True
    assert candidates["B"]["failed_hard_checks"] == []
    statuses = candidates["B"]["check_status"]
    assert statuses.get("fail", 0) == 0
    assert statuses["pass"] + statuses.get("info", 0) + statuses.get(
        "deferred", 0
    ) == 29


def test_baseline_access_gap_is_preserved():
    payload = _load("candidates.json")
    baseline = payload["baseline"]
    assert baseline["access_truth"]["coverage"] == pytest.approx(0.0)
    assert baseline["access_truth"]["relation_error_count"] == 17


def test_recommendation_is_hard_first_and_has_no_score():
    payload = _load("evaluation.json")
    assert payload["recommendation"] == "B"
    assert payload["hard_first"] is True
    assert "A" in payload["reasons"] and "B" in payload["reasons"]
    text = json.dumps(payload).lower()
    assert "no single opaque score" in text
    comparison = payload.get("comparison") or {}
    assert comparison.get("ranking") is None
    assert comparison.get("scoring") is None


# ---------------------------------------------------------------------------
# rendered deliverables (DXF / readback / preview / comparison)
# ---------------------------------------------------------------------------


def test_candidate_render_artifacts_exist():
    manifest = _load("render-manifest.json")
    assert manifest["schema_id"] == "dgcad.co-design-render.v0.1"
    assert manifest["recommendation"] == "B"
    assert manifest["hard_first"] is True
    for candidate_id in CANDIDATE_IDS:
        candidate_dir = EVIDENCE / candidate_id
        for name in (
            f"candidate-{candidate_id.lower()}.dxf",
            "candidate-summary.json",
            "readback-manifest.json",
            "validation.json",
            "privacy.json",
            "scene-snapshot.json",
            f"candidate-{candidate_id.lower()}-preview.svg",
        ):
            assert (candidate_dir / name).exists(), (candidate_id, name)
        summary = _load_candidate(candidate_id)
        assert summary["candidate_id"] == candidate_id
        assert summary["building_count"] == 55
        assert summary["unit_count"] == 109
        assert summary["households"] == 2398
    assert (EVIDENCE / "comparison.svg").exists()


def test_candidate_dxfs_contain_all_55_buildings():
    for candidate_id in CANDIDATE_IDS:
        msp = _candidate_dxf(candidate_id).modelspace()
        object_ids = _object_ids(msp)
        building_ids = {
            object_id[2:]
            for object_id in object_ids
            if object_id.startswith("B-")
        }
        assert len(building_ids) == 55, candidate_id
        footprints = [
            entity
            for entity in msp
            if entity.dxftype() == "LWPOLYLINE"
            and entity.dxf.layer == "A-BUILDING-OUTLINE"
            and _xdata(entity)
            and str(_xdata(entity)[1][1]) == "building_footprint"
        ]
        assert len(footprints) == 55, candidate_id
        unit_lines = [
            object_id
            for object_id in object_ids
            if object_id.startswith("UL-")
        ]
        assert len(unit_lines) == 55, candidate_id
        headings = [
            object_id
            for object_id in object_ids
            if object_id.startswith("LBL-") and object_id.endswith("-HEAD")
        ]
        assert len(headings) == 55, candidate_id
        texts = _texts(msp)
        assert any(candidate_id in text for text in texts), candidate_id


def test_candidate_readback_xdata_and_privacy():
    for candidate_id in CANDIDATE_IDS:
        summary = _load_candidate(candidate_id)
        manifest = json.loads(
            (
                EVIDENCE
                / candidate_id
                / "readback-manifest.json"
            ).read_text(encoding="utf-8")
        )
        msp = _candidate_dxf(candidate_id).modelspace()
        assert summary["readback"]["verdict"] == "pass"
        assert manifest["entity_count"] == len(msp)
        assert manifest["expected_entity_count"] == len(msp)
        assert summary["dxf"]["entity_count"] == len(msp)
        assert manifest["confirmation_scopes"] == ["design_draft"]
        assert manifest["audit_errors"] == 0
        assert manifest["audit_fixes"] == 0
        for entity in msp:
            values = _xdata(entity)
            assert values is not None, entity.dxftype()
            assert len(values) == 11
            assert len(values) == len(XDATA_FIELDS)
            assert str(values[10][1]) == "design_draft"
        assert summary["privacy"]["ok"] is True
        assert scan_dxf_privacy(
            EVIDENCE / candidate_id / f"candidate-{candidate_id.lower()}.dxf"
        )["ok"] is True


def test_candidate_status_marking_is_honest():
    a = _load_candidate("A")
    b = _load_candidate("B")
    assert a["status"] == "incomplete_candidate"
    assert a["hard_ok"] is False
    assert a["failed_hard_checks"] == ["FULL_SITE_ROAD_CLEARANCE"]
    assert a["sheet_id"] == "A-201"
    assert b["status"] == "hard_valid_candidate"
    assert b["hard_ok"] is True
    assert b["failed_hard_checks"] == []
    assert b["sheet_id"] == "A-202"

    texts_a = " | ".join(_texts(_candidate_dxf("A").modelspace()))
    texts_b = " | ".join(_texts(_candidate_dxf("B").modelspace()))
    assert "CANDIDATE A" in texts_a
    assert "INCOMPLETE: FULL_SITE_ROAD_CLEARANCE FAIL" in texts_a
    assert "2.825 m < 3.0 m" in texts_a
    assert "CANDIDATE B" in texts_b
    assert "HARD-VALID CANDIDATE" in texts_b
    assert "ROAD ACCESS 17/17" in texts_b
    for joined in (texts_a, texts_b):
        assert "DESIGNED GREEN" in joined
        assert "POTENTIAL OPEN SPACE" in joined
        assert "NOT LANDSCAPE DESIGN" in joined
        assert "GREEN 61.1" not in joined
        assert "DESIGNED GREEN 61" not in joined


def test_candidate_open_space_is_not_drawn_as_designed_green():
    for candidate_id in CANDIDATE_IDS:
        doc = _candidate_dxf(candidate_id)
        msp = doc.modelspace()
        potential = [
            entity
            for entity in msp
            if entity.dxf.layer == "L-OPEN-SPACE"
            and _xdata(entity)
            and str(_xdata(entity)[1][1]) == "green_space"
        ]
        assert potential, candidate_id
        green_space_on_l_green = [
            entity
            for entity in msp
            if entity.dxf.layer == "L-GREEN"
            and _xdata(entity)
            and str(_xdata(entity)[1][1]) == "green_space"
        ]
        assert green_space_on_l_green == [], candidate_id
        assert "L-OPEN-SPACE" in {layer.dxf.name for layer in doc.layers}
        texts = _texts(msp)
        assert "POTENTIAL OPEN SPACE (NOT LANDSCAPE DESIGN)" in texts
        assert "DESIGNED GREEN" in texts
        assert not any(
            text.startswith("DESIGNED GREEN ") and text.endswith("m2")
            for text in texts
        )


def test_comparison_svg_has_three_same_scale_panels_and_metrics():
    text = (EVIDENCE / "comparison.svg").read_text(encoding="utf-8")
    for label in (
        "M4D1-BASELINE",
        "CANDIDATE A",
        "CANDIDATE B",
        "access coverage",
        "group centroid displacement",
        "added road length",
        "group split",
        "55 / 109",
        "hard check failures",
    ):
        assert label in text, label
    assert "hard-first" in text
    assert "score" not in text.lower()


def _load_render_module():
    path = ROOT / "scripts" / "design" / "render_co_design.py"
    spec = importlib.util.spec_from_file_location("render_co_design", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(scope="module")
def rebuilt_candidates():
    module = _load_render_module()
    basis = DesignBasis.from_dict(
        yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    )
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    frozen = build_full_site_models(CASE, BASIS, PROFILE)
    candidates = {
        candidate_id: module.build_candidate(
            candidate_id,
            frozen,
            basis,
            design_input,
            intent,
            standardized,
            site_inner,
        )
        for candidate_id in CANDIDATE_IDS
    }
    return module, frozen, candidates


def test_candidate_rendering_is_deterministic(rebuilt_candidates, tmp_path):
    module, frozen, candidates = rebuilt_candidates
    basis = frozen["basis"]
    profile = frozen["profile"]
    design_input = frozen["design_input"]
    intent = frozen["intent"]
    for candidate_id in CANDIDATE_IDS:
        candidate = candidates[candidate_id]
        status_line = module._status_line(candidate, basis)

        def build():
            return module.build_full_site_drawing_elements(
                design_input,
                intent,
                candidate["building_layout"],
                candidate["road_layout"],
                candidate["green_layout"],
                candidate["parking_layout"],
                basis,
                candidate["metrics"],
                sheet_id=module.SHEET_IDS[candidate_id],
                candidate_id=candidate_id,
                status_line=status_line,
            )

        first = build()
        second = build()
        assert first == second
        scene = design_scene(
            first, basis, scene_id=f"check-CO-DESIGN-{candidate_id}"
        )
        payload = scene_objects_for_export(scene)
        committed = _load_candidate(candidate_id)
        assert canonical_hash(payload) == committed["scene_sha256"]
        cad_ir = build_design_cad_ir(
            scene,
            profile,
            basis,
            candidate["metrics"],
            project_id=f"check-CO-DESIGN-{candidate_id}",
        )
        manifests = []
        for index in range(2):
            dxf_path = tmp_path / f"{candidate_id}-{index}.dxf"
            compile_to_dxf(cad_ir, profile, dxf_path)
            readback = validate_dxf(dxf_path, cad_ir, profile)
            assert readback.verdict == "pass"
            manifest = dict(readback.manifest)
            # The file name and the DXF byte hash are volatile (ezdxf header
            # timestamps/GUIDs); the canonical content must be deterministic.
            manifest.pop("dxf_sha256", None)
            manifest.pop("file", None)
            manifests.append(manifest)
        assert manifests[0] == manifests[1]


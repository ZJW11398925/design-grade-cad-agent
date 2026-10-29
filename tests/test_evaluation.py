"""Independent candidate evaluation tests (M4c-3a).

The evaluator must recompute hard gates from geometry, bind candidates to the
parent basis by fingerprint, publish eleven single-unit objectives (never a composite
score), and keep auxiliary diagnostics out of the Pareto front. Historical
boundary facts are archival evidence and are never current-candidate verdicts.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from shapely.geometry import LineString, box

from dgcad_design.basis import DesignBasis
from dgcad_design.evaluation import (
    AUXILIARY_METRICS,
    DEFAULT_PRIORITIES,
    DEFAULT_PRIORITY_RATIONALE,
    HARD_CHECKS,
    HISTORICAL_BOUNDARY_ARCHIVE,
    KNOWN_BOUNDARY_VIOLATIONS,
    OBJECTIVE_ORDER,
    OBJECTIVES,
    SOFT_METRICS,
    basis_fingerprint,
    compare,
    evaluate_candidate,
    pareto_front,
)
from dgcad_design.topology import noded_road_topology

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
CONTRACT = ROOT / "contracts" / "design-candidates-v0.2.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"
CASE = ROOT / "docs" / "e2e" / "sketch-001"
SITE = box(-20.0, -20.0, 120.0, 120.0)


@lru_cache(maxsize=1)
def _basis():
    return DesignBasis.load(str(BASIS))


def _road(edge_id, class_name, coordinates, *, width_m=7.0, serves=(), terminal=None):
    line = LineString(coordinates)
    return SimpleNamespace(
        edge_id=edge_id,
        class_name=class_name,
        width_m=width_m,
        centerline=line,
        corridor=line.buffer(width_m / 2.0),
        serves_group_ids=tuple(serves),
        access_terminal_xy=terminal,
    )


def _building(building_id, x, y, unit_count=4, size=10.0):
    return SimpleNamespace(
        building_id=building_id,
        unit_count=unit_count,
        is_facility=False,
        footprint=box(x, y, x + size, y + size),
    )


def _models(
    *,
    candidate_id="C-1",
    strategy="synthetic",
    ring_shift_y=0.0,
    building_shift=(0.0, 0.0),
    source_coverage=0.90,
    designed_green_ratio=0.05,
    overlap_variant=False,
    basis_binding=True,
    fingerprint_override=None,
    parent_basis_override=None,
):
    if overlap_variant:
        buildings = (_building("B-1", -10.0, 20.0),)
    else:
        buildings = (
            _building(
                "B-1",
                110.0 + building_shift[0],
                60.0 + building_shift[1],
            ),
        )
    top = 114.0 + ring_shift_y
    bottom = 0.0 + ring_shift_y
    junction_y = 60.0 + ring_shift_y
    main = _road(
        "MAIN-1", "main",
        [
            (0.0, bottom), (100.0, bottom), (100.0, junction_y),
            (100.0, top), (5.0, top), (0.0, top), (0.0, bottom),
        ],
        width_m=12.0,
    )
    branch = _road(
        "BR-1", "branch",
        [(106.5, 60.0), (100.0, junction_y)],
        width_m=7.0,
        serves=("G-1",),
        terminal=(106.5, 60.0),
    )
    roads = (main, branch)
    topology = noded_road_topology(roads)
    source_segment_map = {
        "MAIN-1": [
            {
                "source_edge_id": "SK-RDC-U-0001",
                "coverage_ratio": source_coverage,
                "distance_m": 1.0,
                "heading_delta_deg": 2.0,
            }
        ]
    }
    road_layout = SimpleNamespace(
        roads=roads,
        noded_topology=topology,
        dead_end_resolutions=(),
        explicit_junctions=(),
        main_alignment_records=(),
        source_segment_map=source_segment_map,
    )
    intent = SimpleNamespace(
        groups=(SimpleNamespace(group_id="G-1", building_ids=("B-1",)),)
    )
    green_layout = SimpleNamespace(
        designed_green_ratio=designed_green_ratio,
        candidate_open_space_ratio=0.60,
        unbuilt_ratio=0.65,
    )
    basis = _basis()
    actual_fingerprint = basis_fingerprint(basis) if basis_binding else None
    actual_parent = str(getattr(basis, "basis_id", "")) if basis_binding else None
    if fingerprint_override is not None:
        actual_fingerprint = fingerprint_override
    if parent_basis_override is not None:
        actual_parent = parent_basis_override
    return SimpleNamespace(
        candidate_id=candidate_id,
        strategy=strategy,
        parent_basis_id=actual_parent,
        basis_fingerprint=actual_fingerprint,
        building_layout=SimpleNamespace(
            buildings=buildings,
            focus_buildings=(),
            rows=(),
            green_strips=(),
            dropped_focus_building_ids=(),
        ),
        road_layout=road_layout,
        green_layout=green_layout,
        parking_layout=SimpleNamespace(entrances=()),
        intent=intent,
        site_boundary=SITE,
        changes={},
    )


def _evaluation(**kwargs):
    return evaluate_candidate(_models(**kwargs), _basis(), reference=_models())


# ----------------------------------------------------------------- structure
def test_evaluation_structure_is_complete():
    evaluation = _evaluation(candidate_id="C-A", strategy="road_priority")
    payload = evaluation.to_dict()
    assert payload["schema_id"] == "dgcad.design-candidates-evaluation.v0.2"
    assert payload["candidate_id"] == "C-A"
    assert set(payload["hard"]) == set(HARD_CHECKS)
    assert payload["hard_pass"] is True, payload["hard_details"]
    assert set(payload["soft"]) >= set(SOFT_METRICS) | {
        "objectives", "objective_metadata", "auxiliary"
    }
    assert set(payload["soft"]["objectives"]) == set(OBJECTIVE_ORDER)
    assert len(payload["soft"]["objectives"]) == 11
    assert payload["soft"]["auxiliary"]["not_in_pareto"] is True
    assert payload["reasons"]


def test_objectives_are_single_unit_values_from_single_fields():
    evaluation = _evaluation()
    objectives = evaluation.soft["objectives"]
    road = evaluation.soft["road_change"]
    building = evaluation.soft["building_change"]
    group = evaluation.soft["group_integrity"]
    source = evaluation.soft["source_preservation"]
    green = evaluation.soft["green_change"]
    assert objectives["building_count_change"] == abs(building["building_delta"])
    assert objectives["building_displaced_count"] == building["displaced_count"]
    assert objectives["building_displacement_max_m"] == building["max_displacement_m"]
    assert objectives["main_length_delta_abs_m"] == abs(road["main_length_delta_m"])
    assert objectives["main_route_deviation_max_m"] == road["main_route_deviation_max_m"]
    assert (
        objectives["branch_access_route_deviation_max_m"]
        == road["branch_access_route_deviation_max_m"]
    )
    assert objectives["access_terminal_max_delta_m"] == group["terminal_max_delta_m"]
    assert objectives["source_preservation_coverage"] == source["mean_coverage_ratio"]
    assert objectives["source_preservation_distance_m"] == source["mean_distance_m"]
    assert (
        objectives["source_preservation_heading_deg"]
        == source["mean_heading_delta_deg"]
    )
    assert objectives["green_designed_ratio_delta"] == green["designed_green_ratio_delta"]
    for name, definition in OBJECTIVES.items():
        assert definition["direction"] in ("minimize", "maximize")
        assert definition["unit"] in ("count", "m", "ratio", "deg")
    assert len({definition["unit"] for definition in OBJECTIVES.values()}) == 4


def test_building_displaced_count_is_a_separate_objective():
    moved = _evaluation(candidate_id="C-MOVED", building_shift=(0.0, -0.5))
    still = _evaluation(candidate_id="C-STILL")
    assert still.soft["objectives"]["building_displaced_count"] == 0.0
    assert moved.soft["objectives"]["building_displaced_count"] == 1.0
    # building count is unchanged, the displaced count separates the candidates
    assert moved.soft["objectives"]["building_count_change"] == 0.0
    comparison = compare([still, moved])
    assert comparison["recommendation"] == "C-STILL"
    assert comparison["preferences"][1]["objective"] == "building_displaced_count"


def test_reference_same_geometry_has_zero_objectives():
    evaluation = _evaluation()
    objectives = evaluation.soft["objectives"]
    assert objectives["building_count_change"] == 0.0
    assert objectives["building_displaced_count"] == 0.0
    assert objectives["building_displacement_max_m"] == 0.0
    assert objectives["main_length_delta_abs_m"] == 0.0
    assert objectives["main_route_deviation_max_m"] == 0.0
    assert objectives["branch_access_route_deviation_max_m"] == 0.0
    assert objectives["access_terminal_max_delta_m"] == 0.0
    assert evaluation.soft["space_utilization"]["gfa_unchanged"] is True


# ----------------------------------------------------------------- hard filtering
def test_hard_overlap_failure_excludes_candidate():
    evaluation = _evaluation(candidate_id="C-OVERLAP", overlap_variant=True)
    assert evaluation.hard["overlap_ok"] is False
    assert evaluation.hard_pass is False
    comparison = compare([evaluation, _evaluation(candidate_id="C-OK")])
    assert comparison["recommendation"] == "C-OK"
    assert "C-OVERLAP" in comparison["excluded"]


def test_self_reported_values_are_not_trusted():
    candidate = _models(candidate_id="C-LIAR", overlap_variant=True)
    candidate.self_reported = {"hard_pass": True, "overlap_ok": True}
    candidate.claimed_metrics = {
        "overlap_m2": 0.0,
        "objectives": {"building_count_change": 0.0},
    }
    evaluation = evaluate_candidate(candidate, _basis(), reference=_models())
    assert evaluation.hard_pass is False
    assert evaluation.hard["overlap_ok"] is False


def test_boundary_violation_fails_hard():
    evaluation = _evaluation(candidate_id="C-OUT", building_shift=(300.0, 0.0))
    assert evaluation.hard["boundary_ok"] is False
    assert evaluation.hard_pass is False


def test_corridor_edge_boundary_violation_is_distinguished_from_centreline():
    evaluation = _evaluation(candidate_id="C-EDGE", ring_shift_y=3.0)
    detail = evaluation.hard_details["boundary_ok"]
    assert evaluation.hard["boundary_ok"] is False
    assert detail["boundary_violation_m"] == pytest.approx(3.0, abs=1e-6)
    assert detail["centerline_violation_m"] == 0.0
    assert detail["known_boundary_violation"] is True


def test_boundary_tolerance_allows_only_one_centimetre_of_corridor_overhang():
    within = _evaluation(candidate_id="C-TOL-OK", ring_shift_y=0.005)
    beyond = _evaluation(candidate_id="C-TOL-BAD", ring_shift_y=0.02)
    assert within.hard["boundary_ok"] is True
    assert beyond.hard["boundary_ok"] is False


def test_capacity_change_fails_hard():
    candidate = _models(candidate_id="C-UNITS")
    candidate.building_layout = SimpleNamespace(
        buildings=(_building("B-1", 110.0, 60.0, unit_count=3),),
        focus_buildings=(),
        rows=(),
        green_strips=(),
        dropped_focus_building_ids=(),
    )
    evaluation = evaluate_candidate(candidate, _basis(), reference=_models())
    assert evaluation.hard["capacity_ok"] is False


# ----------------------------------------------------------------- basis binding
def test_matching_basis_fingerprint_passes():
    evaluation = _evaluation()
    assert evaluation.hard["basis_ok"] is True
    detail = evaluation.hard_details["basis_ok"]
    assert detail["actual_basis_fingerprint"] == detail["expected_basis_fingerprint"]
    assert detail["actual_parent_basis_id"] == detail["expected_parent_basis_id"]


def test_missing_basis_fingerprint_fails():
    evaluation = _evaluation(basis_binding=False)
    assert evaluation.hard["basis_ok"] is False
    detail = evaluation.hard_details["basis_ok"]
    assert "basis_fingerprint" in detail["missing"]
    assert "parent_basis_id" in detail["missing"]
    assert detail["actual_basis_fingerprint"] is None
    assert detail["expected_basis_fingerprint"]


def test_mismatched_basis_fingerprint_fails():
    evaluation = _evaluation(fingerprint_override="0" * 64)
    assert evaluation.hard["basis_ok"] is False
    detail = evaluation.hard_details["basis_ok"]
    assert detail["actual_basis_fingerprint"] == "0" * 64
    assert detail["actual_basis_fingerprint"] != detail["expected_basis_fingerprint"]


def test_wrong_parent_basis_id_fails():
    evaluation = _evaluation(parent_basis_override="some-other-basis")
    assert evaluation.hard["basis_ok"] is False


def test_basis_fingerprint_is_canonical():
    basis = _basis()
    assert basis_fingerprint(basis) == basis_fingerprint(_basis())
    expected = hashlib.sha256(
        json.dumps(basis.to_dict(), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    assert basis_fingerprint(basis) == expected


# ----------------------------------------------------------------- historical archive
def _evidence():
    return json.loads((EVIDENCE / "design-summary.json").read_text(encoding="utf-8"))


def test_historical_archive_66_235_belongs_to_main_19_geometry():
    archive = {entry["road_id"]: entry for entry in HISTORICAL_BOUNDARY_ARCHIVE}
    main_19 = archive["MAIN-19"]
    assert main_19["kind"] == "main_road_diversion"
    assert main_19["max_displacement_m"] == pytest.approx(66.23545861756293)
    records = _evidence()["road_alignment"]["records"]
    record = next(item for item in records if item["road_id"] == "MAIN-19")
    assert record["max_displacement_m"] == pytest.approx(66.23545861756293)
    recomputed = LineString(record["original_centerline"]).hausdorff_distance(
        LineString(record["adjusted_centerline"])
    )
    assert recomputed == pytest.approx(66.23545861756293, rel=1e-9)
    assert archive["MAIN-08"]["max_displacement_m"] != pytest.approx(66.23545861756293)


def test_historical_archive_341_6908_belongs_to_main_08_repair():
    archive = {entry["road_id"]: entry for entry in HISTORICAL_BOUNDARY_ARCHIVE}
    main_08 = archive["MAIN-08"]
    assert main_08["kind"] == "source_corridor_boundary_repair"
    assert main_08["outside_area_m2"] == pytest.approx(341.6908310814502)
    assert main_08["status"] == "resolved_by_boundary_repair"
    repairs = {
        item["road_id"]: item
        for item in _evidence()["road_alignment"]["boundary_repairs"]
    }
    assert repairs["MAIN-08"]["outside_area_before_m2"] == pytest.approx(
        341.6908310814502
    )
    assert repairs["MAIN-08"]["boundary_ok_after"] is True
    assert archive["MAIN-16"]["outside_area_m2"] == pytest.approx(2.417804558565924)
    assert archive["MAIN-18"]["outside_area_m2"] == pytest.approx(8.290901115044374)


def test_known_boundary_violations_are_current_geometry_only():
    assert KNOWN_BOUNDARY_VIOLATIONS == ()
    evaluation = _evaluation(candidate_id="C-CURRENT", ring_shift_y=3.0)
    assert evaluation.hard_details["boundary_ok"]["known_boundary_violation"] is True
    passing = _evaluation(candidate_id="C-PASS")
    assert "known_boundary_violation" not in passing.hard_details["boundary_ok"]


# ----------------------------------------------------------------- pareto / compare
def test_auxiliary_metrics_never_enter_pareto_or_objectives():
    evaluation = _evaluation(candidate_id="C-1")
    comparison = compare([evaluation])
    assert set(comparison["auxiliary_metrics_not_in_pareto"]) == set(AUXILIARY_METRICS)
    assert set(OBJECTIVE_ORDER).isdisjoint(AUXILIARY_METRICS)
    for metric in AUXILIARY_METRICS:
        assert metric not in OBJECTIVES
    assert comparison["objectives"] == {
        name: dict(OBJECTIVES[name]) for name in OBJECTIVE_ORDER
    }


def test_pareto_front_uses_independent_objectives():
    dominant = _evaluation(candidate_id="C-DOM", source_coverage=0.90)
    better_source = _evaluation(
        candidate_id="C-SOURCE", building_shift=(0.0, -0.5), source_coverage=0.98
    )
    dominated = _evaluation(
        candidate_id="C-DOMINATED", building_shift=(0.0, -0.8), source_coverage=0.80
    )
    front = pareto_front([dominant, better_source, dominated])
    front_ids = {item.candidate_id for item in front}
    assert "C-DOM" in front_ids
    assert "C-SOURCE" in front_ids
    assert "C-DOMINATED" not in front_ids


def test_compare_requires_objective_reason_for_every_candidate():
    evaluations = [
        _evaluation(candidate_id="C-1"),
        _evaluation(candidate_id="C-2", building_shift=(0.0, -0.5)),
        _evaluation(candidate_id="C-3", overlap_variant=True),
    ]
    comparison = compare(evaluations)
    assert comparison["recommendation"] == "C-1"
    for evaluation in evaluations:
        assert comparison["reasons"].get(evaluation.candidate_id)
    assert comparison["excluded"]["C-3"].startswith("hard gate failure")
    assert comparison["priority_rationale"] == DEFAULT_PRIORITY_RATIONALE


def test_compare_preferences_are_objective_level_and_directional():
    evaluations = [
        _evaluation(candidate_id="C-1"),
        _evaluation(candidate_id="C-2", building_shift=(0.0, -0.5), source_coverage=0.99),
    ]
    by_default = compare(evaluations)
    assert by_default["recommendation"] == "C-1"
    by_source = compare(
        evaluations,
        preferences=[
            {"objective": "source_preservation_coverage", "direction": "maximize"}
        ],
    )
    assert by_source["recommendation"] == "C-2"
    assert by_source["priority_rationale"] is None


def test_compare_rejects_unknown_objective_and_direction_conflict():
    with pytest.raises(ValueError):
        compare([_evaluation()], preferences=[{"objective": "vibes", "direction": "maximize"}])
    with pytest.raises(ValueError):
        compare(
            [_evaluation()],
            preferences=[{"objective": "building_count_change", "direction": "maximize"}],
        )


def test_compare_without_hard_passing_candidate_recommends_nothing():
    comparison = compare([_evaluation(candidate_id="C-BAD", overlap_variant=True)])
    assert comparison["recommendation"] is None
    assert comparison["pareto_front"] == []
    assert "nothing is recommended" in comparison["note"]


def test_evaluation_is_deterministic():
    first = _evaluation(candidate_id="C-1").to_dict()
    second = _evaluation(candidate_id="C-1").to_dict()
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


# ----------------------------------------------------------------- contract
def test_candidate_contract_v02_declares_archive_objectives_and_basis():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema_id"] == "dgcad.design-candidates.v0.2"
    assert contract["status"] == "living_contract"
    assert contract["supersedes"] == "design-candidates-v0.1.yaml"
    assert set(contract["candidate"]["required"]) >= {
        "parent_basis_id", "basis_fingerprint", "geometry_change"
    }
    assert contract["evaluation"]["schema_id"] == "dgcad.design-candidates-evaluation.v0.2"
    assert contract["evaluation"]["hard"]["required"] == list(HARD_CHECKS)
    assert contract["evaluation"]["objectives"]["required"] == list(OBJECTIVE_ORDER)
    definitions = contract["evaluation"]["objectives"]["definitions"]
    for name, definition in OBJECTIVES.items():
        assert definitions[name]["direction"] == definition["direction"]
        assert definitions[name]["unit"] == definition["unit"]
    default_order = [priority["objective"] for priority in DEFAULT_PRIORITIES]
    assert contract["evaluation"]["recommendation"]["default_preferences"] == default_order
    archive = {
        entry["road_id"]: entry
        for entry in contract["historical_boundary_archive"]["entries"]
    }
    assert archive["MAIN-19"]["max_displacement_m"] == pytest.approx(66.23545861756293)
    assert archive["MAIN-08"]["outside_area_m2"] == pytest.approx(341.6908310814502)
    rules = " | ".join(
        contract["rules"] + contract["evaluation"]["objectives"]["rules"]
    )
    assert "objectives are never summed into a composite score" in rules
    assert "mixed-unit composites" in rules
    assert "never enter the Pareto front" in rules
    assert "recomputed from geometry; candidate self-reported values are ignored" in rules
    assert "historical boundary archives are not current-candidate verdicts" in " | ".join(
        contract["rules"]
    )


# ----------------------------------------------------------------- integration
HAS_CANDIDATES = importlib.util.find_spec("dgcad_design.candidates") is not None


def _candidate_has_basis_binding(candidate) -> bool:
    spec = getattr(candidate, "spec", None)
    return bool(
        getattr(candidate, "basis_fingerprint", None)
        or getattr(spec, "basis_fingerprint", None)
    )


@pytest.mark.skipif(not HAS_CANDIDATES, reason="candidates.py not ready")
def test_four_experiment_candidates_are_evaluable_when_basis_binding_ready():
    from dgcad_design import build_design_intent, load_design_input  # noqa: PLC0415
    from dgcad_design.candidates import CandidateSpec, build_candidate  # noqa: PLC0415

    basis = _basis()
    specs = [
        CandidateSpec("A", "road_priority", ""),
        CandidateSpec("B1", "building_priority_diversion", ""),
        CandidateSpec("B2", "building_priority_alternate", ""),
        CandidateSpec("C", "coordinated", ""),
    ]
    models = {spec.candidate_id: build_candidate(CASE, basis, spec) for spec in specs}
    if not _candidate_has_basis_binding(models["A"]):
        pytest.skip("waiting for task-71 candidate basis fingerprint fields")
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    reference = models["B1"]
    evaluations = [
        evaluate_candidate(
            models[cid],
            basis,
            reference=reference,
            intent=intent,
            site_boundary=design_input.site_boundary,
        )
        for cid in ("A", "B1", "B2", "C")
    ]
    for evaluation in evaluations:
        assert set(evaluation.soft["objectives"]) == set(OBJECTIVE_ORDER)
        assert evaluation.hard_pass == all(evaluation.hard.values())
    comparison = compare(evaluations)
    assert comparison["recommendation"] is None or (
        comparison["recommendation"] in comparison["pareto_front"]
    )
    for evaluation in evaluations:
        assert comparison["reasons"].get(evaluation.candidate_id)

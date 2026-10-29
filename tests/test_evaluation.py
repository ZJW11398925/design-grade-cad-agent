"""Independent candidate evaluation tests (M4c-3).

The evaluator must recompute hard gates from geometry, keep soft trade-offs
separate, and never trust a candidate's own report. The tests use small synthetic
candidate models unless the real ``candidates`` module is available (then one
integration test builds the four experiment candidates and evaluates them).
"""
from __future__ import annotations

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
    HARD_CHECKS,
    SOFT_METRICS,
    SOFT_OBJECTIVES,
    compare,
    evaluate_candidate,
    pareto_front,
)
from dgcad_design.topology import noded_road_topology

ROOT = Path(__file__).resolve().parents[1]
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
CONTRACT = ROOT / "contracts" / "design-candidates-v0.1.yaml"
CASE = ROOT / "docs" / "e2e" / "sketch-001"
SITE = box(-20.0, -20.0, 120.0, 120.0)


@lru_cache(maxsize=1)
def _basis():
    return DesignBasis.load(str(BASIS))


def _road(
    edge_id,
    class_name,
    coordinates,
    *,
    width_m=7.0,
    serves=(),
    terminal=None,
):
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
    extra_source=None,
    overlap_variant=False,
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
    if extra_source:
        source_segment_map["MAIN-1"][0]["coverage_ratio"] = extra_source
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
    return SimpleNamespace(
        candidate_id=candidate_id,
        strategy=strategy,
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
    assert payload["schema_id"] == "dgcad.design-candidates-evaluation.v0.1"
    assert payload["candidate_id"] == "C-A"
    assert payload["strategy"] == "road_priority"
    assert set(payload["hard"]) == set(HARD_CHECKS)
    assert payload["hard_pass"] is True, payload["hard_details"]
    for objective in SOFT_OBJECTIVES:
        assert objective in payload["soft"], objective
    assert payload["soft"]["source_preservation"]["available"] is True
    assert payload["reasons"]


def test_reference_same_geometry_has_zero_change():
    evaluation = _evaluation()
    assert evaluation.soft["road_change"]["max_displacement_m"] == 0.0
    assert evaluation.soft["building_change"]["displaced_count"] == 0
    assert evaluation.soft["space_utilization"]["gfa_unchanged"] is True
    assert evaluation.soft["group_integrity"]["declared_relations_preserved"] is True


# ----------------------------------------------------------------- hard filtering
def test_hard_overlap_failure_excludes_candidate():
    evaluation = _evaluation(candidate_id="C-OVERLAP", overlap_variant=True)
    assert evaluation.hard["overlap_ok"] is False
    assert evaluation.hard_pass is False
    assert "overlap_ok" in evaluation.to_dict()["reasons"][0]
    comparison = compare([evaluation, _evaluation(candidate_id="C-OK")])
    assert comparison["recommendation"] == "C-OK"
    assert "C-OVERLAP" in comparison["excluded"]
    assert "C-OVERLAP" not in comparison["pareto_front"]


def test_self_reported_values_are_not_trusted():
    candidate = _models(candidate_id="C-LIAR", overlap_variant=True)
    candidate.self_reported = {
        "hard_pass": True,
        "overlap_ok": True,
        "access_ok": True,
    }
    candidate.claimed_metrics = {"overlap_m2": 0.0}
    evaluation = evaluate_candidate(
        candidate, _basis(), reference=_models()
    )
    assert evaluation.hard_pass is False  # geometry wins over the claim
    assert evaluation.hard["overlap_ok"] is False


def test_boundary_violation_fails_hard():
    # shift the building outside the published site boundary
    evaluation = _evaluation(candidate_id="C-OUT", building_shift=(300.0, 0.0))
    assert evaluation.hard["boundary_ok"] is False
    assert evaluation.hard_pass is False


def test_corridor_edge_boundary_violation_is_distinguished_from_centreline():
    # the ring top corridor edge is already tangent to the boundary; shifting the
    # ring up by 3 m overhangs the corridor while the centreline stays inside
    evaluation = _evaluation(candidate_id="C-EDGE", ring_shift_y=3.0)
    detail = evaluation.hard_details["boundary_ok"]
    assert evaluation.hard["boundary_ok"] is False
    assert detail["boundary_violation_m"] == pytest.approx(3.0, abs=1e-6)
    assert detail["centerline_violation_m"] == 0.0
    assert detail["status"] == "known_boundary_violation"
    assert detail["known_boundary_violation"] is True


def test_boundary_tolerance_allows_only_one_centimetre_of_corridor_overhang():
    within = _evaluation(candidate_id="C-TOL-OK", ring_shift_y=0.005)
    beyond = _evaluation(candidate_id="C-TOL-BAD", ring_shift_y=0.02)
    assert within.hard_details["boundary_ok"]["boundary_violation_m"] == pytest.approx(0.005, abs=1e-6)
    assert within.hard["boundary_ok"] is True
    assert beyond.hard_details["boundary_ok"]["boundary_violation_m"] == pytest.approx(0.02, abs=1e-6)
    assert beyond.hard["boundary_ok"] is False


def test_known_b1_diversion_is_recorded_as_a_boundary_violation():
    from dgcad_design.evaluation import KNOWN_BOUNDARY_VIOLATIONS  # noqa: PLC0415

    record = KNOWN_BOUNDARY_VIOLATIONS[0]
    assert record["candidate_id"] == "B1"
    assert record["road_id"] == "MAIN-08"
    assert record["max_displacement_m"] == pytest.approx(66.23545861756293)
    assert record["status"] == "known_boundary_violation"
    assert "not a hard pass" in record["note"]


def test_capacity_change_fails_hard():
    candidate = _models(candidate_id="C-UNITS")
    candidate.building_layout = SimpleNamespace(
        buildings=(_building("B-1", 0.0, 20.0, unit_count=3),),
        focus_buildings=(),
        rows=(),
        green_strips=(),
        dropped_focus_building_ids=(),
    )
    evaluation = evaluate_candidate(candidate, _basis(), reference=_models())
    assert evaluation.hard["capacity_ok"] is False


def test_basis_change_fails_hard():
    class ClaimedBasis:
        def to_dict(self):
            data = _basis().to_dict()
            data["floors"] = data["floors"] + 1
            return data

    candidate = _models(candidate_id="C-BASIS")
    candidate.basis = ClaimedBasis()
    evaluation = evaluate_candidate(candidate, _basis(), reference=_models())
    assert evaluation.hard["basis_ok"] is False
    assert "floors" in evaluation.hard_details["basis_ok"]["changed_fields"]


# ----------------------------------------------------------------- pareto
def test_pareto_front_keeps_only_non_dominated_candidates():
    reference = _evaluation(candidate_id="C-REF")
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
    assert "C-SOURCE" in front_ids  # better source trade-off stays visible
    assert "C-DOMINATED" not in front_ids
    assert reference.candidate_id == "C-REF"


# ----------------------------------------------------------------- recommendation
def test_compare_requires_reasons_for_every_candidate():
    evaluations = [
        _evaluation(candidate_id="C-1"),
        _evaluation(candidate_id="C-2", building_shift=(0.0, -0.5)),
        _evaluation(candidate_id="C-3", overlap_variant=True),
    ]
    comparison = compare(evaluations)
    assert comparison["recommendation"] == "C-1"
    for evaluation in evaluations:
        assert comparison["reasons"].get(evaluation.candidate_id), (
            f"no reason for {evaluation.candidate_id}"
        )
    assert comparison["pareto_front"]
    assert "note" in comparison
    assert "no single black-box score" in comparison["note"]
    assert comparison["excluded"]["C-3"].startswith("hard gate failure")


def test_compare_preferences_are_explicit_and_matter():
    evaluations = [
        _evaluation(candidate_id="C-1"),
        _evaluation(
            candidate_id="C-2", building_shift=(0.0, -0.5), source_coverage=0.99
        ),
    ]
    by_building = compare(evaluations)
    assert by_building["recommendation"] == "C-1"
    by_source = compare(
        evaluations,
        preferences=[{"objective": "source_preservation", "direction": "maximize"}],
    )
    assert by_source["recommendation"] == "C-2"
    assert by_source["preferences"][0]["objective"] == "source_preservation"


def test_compare_rejects_unknown_objectives():
    with pytest.raises(ValueError):
        compare([_evaluation()], preferences=[{"objective": "vibes", "direction": "maximize"}])


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
def test_candidate_contract_declares_the_evaluation_boundaries():
    contract = yaml.safe_load(CONTRACT.read_text(encoding="utf-8"))
    assert contract["schema_id"] == "dgcad.design-candidates.v0.1"
    assert contract["status"] == "living_contract"
    assert contract["candidate"]["required"] == [
        "candidate_id", "strategy", "spec", "version", "changes"
    ]
    assert contract["evaluation"]["hard"]["required"] == list(HARD_CHECKS)
    assert contract["evaluation"]["soft"]["required"] == list(SOFT_METRICS)
    assert contract["evaluation"]["pareto"]["objectives"] == [
        "building_change", "road_change", "source_preservation", "green_change"
    ]
    rules = " | ".join(contract["rules"] + contract["evaluation"]["recommendation"]["rules"])
    assert "the generator never evaluates or recommends its own candidates" in rules
    assert "recomputed from geometry" in rules
    assert "relabel parameters or widen a tolerance" in rules
    assert "an unmet constraint is reported" in rules
    assert "never combined into a single black-box score" in rules
    assert "every candidate, recommended or not, gets a reason" in rules


# ----------------------------------------------------------------- integration
HAS_CANDIDATES = importlib.util.find_spec("dgcad_design.candidates") is not None


@pytest.mark.skipif(not HAS_CANDIDATES, reason="candidates.py not ready (design-topology M4c-3 step 1)")
def test_four_experiment_candidates_are_evaluable():
    from dgcad_design import build_design_intent, load_design_input  # noqa: PLC0415
    from dgcad_design.candidates import CandidateSpec, build_candidate  # noqa: PLC0415

    basis = _basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    specs = [
        CandidateSpec("A", "road_priority", "keep original main routes, shift buildings"),
        CandidateSpec("B1", "building_priority_diversion", "current diversion"),
        CandidateSpec("B2", "building_priority_alternate", "alternate diversion"),
        CandidateSpec("C", "coordinated", "small building shift + local road change"),
    ]
    models = {
        spec.candidate_id: build_candidate(CASE, basis, spec) for spec in specs
    }
    reference = models["A"]
    evaluations = [
        evaluate_candidate(
            models[spec.candidate_id],
            basis,
            reference=reference,
            intent=intent,
            site_boundary=design_input.site_boundary,
        )
        for spec in specs
    ]
    assert len(evaluations) == 4
    comparison = compare(evaluations)
    for evaluation in evaluations:
        assert set(evaluation.hard) == set(HARD_CHECKS)
        assert set(evaluation.soft) >= set(SOFT_METRICS)
        assert evaluation.hard_pass == all(evaluation.hard.values())
        assert comparison["reasons"].get(evaluation.candidate_id), (
            f"no reason for {evaluation.candidate_id}"
        )
        if not evaluation.hard_pass:
            assert evaluation.candidate_id in comparison["excluded"]
    assert (
        comparison["recommendation"] is None
        or comparison["recommendation"] in comparison["pareto_front"]
    )

"""M4c-3 candidate generator tests.

Four candidates start from the same input/basis:
A road priority (buildings move), B1 building priority (M4c-2 diversion),
B2 building priority alternate (different diversion fold), C coordinated
(small building shift + medium road adjustment).  Every candidate must remove
the main-road/building overlap, keep one noded component with no crossing-only
connections, preserve road ids and keep the 17 declared access relations.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest
from shapely.geometry import Point

from dgcad_design import DesignBasis, load_design_input
from dgcad_design.candidates import (
    CANDIDATE_SPECS,
    CandidateModels,
    build_all_candidates,
    build_candidate,
    candidate_by_id,
)
from dgcad_design.topology import topology_violations

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"

BASIS = DesignBasis.load(str(BASIS_PATH))


@lru_cache(maxsize=1)
def _candidates() -> dict[str, CandidateModels]:
    return build_all_candidates(CASE, BASIS)


def _by_id(candidate_id: str) -> CandidateModels:
    return _candidates()[candidate_id]


def _main19(models: CandidateModels):
    return next(
        road
        for road in models.road_layout.roads
        if road.edge_id == "MAIN-19"
    )


def _route_change(models: CandidateModels, road_id: str) -> dict:
    for item in models.changes["road_route_changes"]:
        if item["road_id"] == road_id:
            return item
    raise AssertionError(f"no route change recorded for {road_id}")


def _max_vertex_distance(first, second) -> float:
    return max(
        max(
            second.distance(Point(float(x), float(y)))
            for x, y in first.coords
        ),
        max(
            first.distance(Point(float(x), float(y)))
            for x, y in second.coords
        ),
    )


def _signature(models: CandidateModels) -> tuple:
    roads = tuple(
        (
            road.edge_id,
            tuple(
                (round(float(x), 9), round(float(y), 9))
                for x, y in road.centerline.coords
            ),
        )
        for road in models.road_layout.roads
    )
    buildings = tuple(
        (
            item.building_id,
            round(item.design_centroid[0], 9),
            round(item.design_centroid[1], 9),
        )
        for item in models.building_layout.buildings
    )
    return roads, buildings, json.dumps(models.changes, sort_keys=True)


# ------------------------------------------------------------- catalogue
def test_four_candidates_build_with_expected_strategies():
    models = _candidates()
    assert set(models) == {"A", "B1", "B2", "C"}
    expected = {
        "A": "road_priority",
        "B1": "building_priority_diversion",
        "B2": "building_priority_alternate",
        "C": "coordinated",
    }
    for candidate_id, strategy in expected.items():
        assert models[candidate_id].spec.strategy == strategy
        assert models[candidate_id].spec.candidate_id == candidate_id
    assert {spec.candidate_id for spec in CANDIDATE_SPECS} == set(expected)


def test_baseline_geometry_loaded_from_same_input():
    design_input = load_design_input(CASE, BASIS)
    source_main = [
        road
        for road in design_input.roads
        if road.class_candidate == "main_road"
    ]
    assert len(source_main) == 65
    models = _candidates()
    for candidate in models.values():
        assert len(candidate.road_layout.roads) == 44
        assert candidate.changes["building_count"] == 55


# ------------------------------------------------------ candidate A (roads)
def test_candidate_a_moves_buildings_and_keeps_raw_roads():
    models = _by_id("A")
    changes = models.changes
    # the base geometry already repairs MAIN-08/16/18 boundary overhangs, so
    # only the MAIN-19 conflict remains for the road-priority building shifts
    assert changes["displaced_buildings"] == ["SK-BLD-0006"]
    assert changes["building_shift_total_m"] > 0.0
    # the main roads keep their raw source geometry (no main-road alignment);
    # shifting SK-BLD-0006 does trim the adjacent MAIN-15 stub by 2.320271 m,
    # which the route-change record now captures as a pure trim (C1)
    route_changes = changes["road_route_changes"]
    assert len(route_changes) == 1
    trim = route_changes[0]
    assert trim["road_id"] == "MAIN-15"
    assert trim["kind"] == "trim"
    assert trim["length_delta_m"] == pytest.approx(
        -2.3202710858196465, rel=1e-9
    )
    assert trim["max_vertex_displacement_m"] <= 1e-6
    assert changes["road_max_displacement_m"] <= 1e-6
    assert models.road_layout.main_alignment_records == ()
    assert changes["hard_overlap_after_m2"] <= 0.01
    for shift in changes["building_shifts"]:
        assert shift["distance_m"] > 0.0
        assert shift["building_id"].startswith("SK-BLD-")
    # capacities are unaffected by translating a footprint
    reference = _by_id("B1")
    assert changes["unit_count_total"] == reference.changes["unit_count_total"]
    assert (
        changes["household_count_total"]
        == reference.changes["household_count_total"]
    )


# ------------------------------------------- building-priority B1 / B2
def test_b1_is_the_reference_building_priority_design():
    models = _by_id("B1")
    changes = models.changes
    assert changes["displaced_buildings"] == []
    assert changes["building_shift_total_m"] == 0.0
    main19 = _route_change(models, "MAIN-19")
    assert main19["max_displacement_m"] > 30.0
    main20 = _route_change(models, "MAIN-20")
    assert main20["max_displacement_m"] > 1.0
    assert changes["hard_overlap_after_m2"] <= 0.01
    record = next(
        item
        for item in models.road_layout.main_alignment_records
        if item["road_id"] == "MAIN-19"
    )
    assert record["alignment_strategy"] == "diversion"
    assert record["local_search_exhausted"] is True
    # the original 66.235 m diversion was a known boundary violation: the
    # boundary-safe base design now carries it inside the published boundary
    assert changes["hard_boundary_ok"] is True
    assert changes["boundary"]["boundary_violation_m"] <= 0.01
    assert changes["boundary"]["boundary_margin_m"] >= 0.0


def test_b2_is_a_visibly_different_alternate_route():
    b1 = _by_id("B1")
    b2 = _by_id("B2")
    assert b2.changes["displaced_buildings"] == []
    assert b2.changes["hard_overlap_after_m2"] <= 0.01
    main19_b1 = _main19(b1).centerline
    main19_b2 = _main19(b2).centerline
    assert _max_vertex_distance(main19_b1, main19_b2) > 1.0
    displacement_b1 = _route_change(b1, "MAIN-19")[
        "max_displacement_m"
    ]
    displacement_b2 = _route_change(b2, "MAIN-19")[
        "max_displacement_m"
    ]
    assert abs(displacement_b1 - displacement_b2) > 1.0
    assert abs(
        main19_b1.length - main19_b2.length
    ) > 1.0
    for candidate in (b1, b2):
        assert candidate.changes["hard_boundary_ok"] is True
        assert candidate.changes["boundary"]["boundary_violation_m"] <= 0.0
        assert candidate.changes["boundary"]["boundary_margin_m"] >= 0.0


# ---------------------------------------------------- candidate C coordinated
def test_candidate_c_is_coordinated():
    models = _by_id("C")
    changes = models.changes
    a_changes = _by_id("A").changes
    b1_changes = _by_id("B1").changes
    assert changes["displaced_buildings"] == ["SK-BLD-0006"]
    assert changes["building_shift_total_m"] > 0.0
    assert changes["road_route_changes"]
    # both interventions are smaller than the corresponding single-strategy ones
    assert (
        changes["building_shift_total_m"]
        < a_changes["building_shift_total_m"]
    )
    assert (
        changes["road_max_displacement_m"]
        < b1_changes["road_max_displacement_m"]
    )
    assert changes["hard_overlap_after_m2"] <= 0.01
    assert changes["hard_boundary_ok"] is True
    assert changes["boundary"]["boundary_violation_m"] <= 0.0
    assert changes["boundary"]["boundary_margin_m"] >= 0.0


# --------------------------------------------- global invariants / determinism
def test_all_candidates_share_hard_invariants():
    models = _candidates()
    reference_ids = {
        road.edge_id for road in models["B1"].road_layout.roads
    }
    reference_units = models["B1"].changes["unit_count_total"]
    reference_households = models["B1"].changes[
        "household_count_total"
    ]
    for candidate_id, candidate in models.items():
        changes = candidate.changes
        assert changes["hard_overlap_after_m2"] <= 0.01, candidate_id
        assert changes["main_overlap_resolved"] is True, candidate_id
        # arch-core published-boundary hard gate: corridor edge inside <= 0.01
        assert changes["hard_boundary_ok"] is True, candidate_id
        boundary = changes["boundary"]
        assert boundary["boundary_violation_m"] <= 0.01, candidate_id
        assert boundary["centerline_violation_m"] <= 0.01, candidate_id
        assert boundary["boundary_margin_m"] >= 0.0, candidate_id
        assert boundary["outside_building_ids"] == [], candidate_id
        topology = candidate.road_layout.noded_topology
        assert topology.component_count == 1, candidate_id
        assert topology.max_endpoint_gap_m == 0.0, candidate_id
        assert topology_violations(topology) == (), candidate_id
        assert changes["topology"]["violation_codes"] == [], candidate_id
        assert changes["access"]["declared_total"] == 17, candidate_id
        assert changes["access"]["coverage"] == pytest.approx(
            1.0, abs=1e-9
        ), candidate_id
        assert changes["access"]["served_groups"] == 17, candidate_id
        assert (
            changes["access"]["dead_ends_unresolved"] == 0
        ), candidate_id
        assert {
            road.edge_id for road in candidate.road_layout.roads
        } == reference_ids, candidate_id
        assert changes["unit_count_total"] == reference_units
        assert changes["household_count_total"] == reference_households
        assert candidate.parking_layout is not None
        assert candidate.green_layout is not None
        for lane in candidate.road_layout.roads:
            if lane.class_name != "main":
                continue
            corridor = lane.corridor
            boundary_geom = candidate.road_layout  # noqa: F841 - readability
            design_input = load_design_input(CASE, BASIS)
            assert design_input.site_boundary.buffer(0.01).covers(
                corridor
            ), (candidate_id, lane.edge_id)


def test_candidates_are_deterministic():
    spec = candidate_by_id("B2")
    rebuilt = build_candidate(CASE, BASIS, spec)
    cached = _by_id("B2")
    assert _signature(rebuilt) == _signature(cached)


# ------------------------------------------------ Phase 0 evidence fixes
def test_phase0_alignment_semantics_are_honest():
    models = _by_id("B1")
    record = next(
        item
        for item in models.road_layout.main_alignment_records
        if item["road_id"] == "MAIN-19"
    )
    assert record["local_search_exhausted"] is True
    assert "local_detour_infeasible" not in record
    reason = record["reason"]
    assert "local search family" in reason
    assert "passage between the two buildings is infeasible" in reason
    assert "legal candidate" in reason
    assert "provably infeasible" not in reason
    assert "can clear both" not in reason


def test_source_segment_map_is_published():
    models = _by_id("B1")
    mapping = models.road_layout.source_segment_map
    assert len(mapping) == 25
    assert all(key.startswith("MAIN-") for key in mapping)
    design_input = load_design_input(CASE, BASIS)
    source_ids = {
        road.edge_id
        for road in design_input.roads
        if road.class_candidate == "main_road"
    }
    mapped_ids: set[str] = set()
    for design_road_id, entries in mapping.items():
        assert entries, design_road_id
        for entry in entries:
            assert set(entry) == {
                "source_edge_id",
                "overlap_length_m",
                "distance_m",
                "coverage_ratio",
                "heading_delta_deg",
            }
            assert 0.0 <= entry["coverage_ratio"] <= 1.0
            assert 0.0 <= entry["heading_delta_deg"] <= 90.0
            assert entry["overlap_length_m"] >= 0.0
            assert entry["distance_m"] >= 0.0
            mapped_ids.add(entry["source_edge_id"])
    # the coarse map covers every source main edge (65)
    assert mapped_ids == source_ids
    payload = models.road_layout.to_dict()
    assert "source_segment_map" in payload
    assert len(payload["source_segment_map"]) == 25


def test_candidate_models_to_dict_summary():
    payload = _by_id("C").to_dict()
    assert payload["candidate_id"] == "C"
    assert payload["strategy"] == "coordinated"
    assert payload["changes"]["hard_overlap_after_m2"] <= 0.01
    assert payload["changes"]["hard_boundary_ok"] is True
    assert payload["changes"]["boundary"]["boundary_violation_m"] <= 0.01
    assert payload["metrics"]["road_count"] == 44
    json.dumps(payload)

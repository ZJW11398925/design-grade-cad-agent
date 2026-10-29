"""Declared road-access evidence tests (M4c-1e).

A group is served only when a road **declares** it (``serves_group_ids``) and
carries an explicit ``access_terminal_xy`` that passes the geometric band and
footprint rules. Proximity to the nearest road is no longer evidence of access.

Two layers:
* synthetic unit tests pin the declarative rules and the negative cases
  (no declaration, duplicate declaration, out-of-band terminal, terminal inside a
  footprint, route crossing, main road claiming a group, corridor-edge clearance);
* integration tests build the real CASE-SKETCH-001 R1 design and assert the
  M4c-1e acceptance targets. They need the ``serves_group_ids`` /
  ``access_terminal_xy`` fields from ``roads.py`` (design-topology, M4c-1e step 1)
  and report "waiting for roads declarative fields" until they land.
"""
from __future__ import annotations

import dataclasses
import json
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString, Point, box

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import (
    ORPHAN_DECLARED_GROUP,
    RELATION_MISSING_TERMINAL,
    RELATION_MULTIPLE_DECLARATIONS,
    RELATION_NO_DECLARATION,
    RELATION_NOT_ACCESS_CLASS,
    RELATION_ROUTE_CROSSING,
    RELATION_TERMINAL_DISTANCE,
    RELATION_TERMINAL_INSIDE_FOOTPRINT,
    RELATION_TERMINAL_NOT_ON_ROAD,
    TERMINAL_DISTANCE_MAX_M,
    TERMINAL_DISTANCE_MIN_M,
    build_road_access,
    main_road_building_overlap,
)
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


# ----------------------------------------------------------------- synthetic helpers
def _road(
    edge_id: str,
    class_name: str,
    coordinates,
    *,
    width_m: float = 7.0,
    serves=(),
    terminal=None,
    corridor=None,
):
    line = LineString(coordinates)
    return SimpleNamespace(
        edge_id=edge_id,
        class_name=class_name,
        width_m=width_m,
        centerline=line,
        serves_group_ids=tuple(serves),
        access_terminal_xy=terminal,
        corridor=corridor if corridor is not None else line.buffer(width_m / 2.0),
    )


def _building(building_id: str, x: float, y: float, size: float = 10.0):
    return SimpleNamespace(
        building_id=building_id,
        footprint=box(x, y, x + size, y + size),
    )


def _basis(clearance: float = 3.0):
    return SimpleNamespace(building_road_clearance_m=clearance)


def _access(roads, buildings, groups, entrances=(), clearance: float = 3.0):
    return build_road_access(
        SimpleNamespace(buildings=tuple(buildings)),
        SimpleNamespace(roads=tuple(roads)),
        SimpleNamespace(groups=tuple(groups)),
        SimpleNamespace(entrances=tuple(entrances)),
        _basis(clearance),
    )


def _declared_group_case(
    *,
    terminal_x: float = -3.45,
    serves=("G-1",),
    class_name: str = "branch",
    extra_road_kwargs=None,
):
    road = _road(
        "BR-1",
        class_name,
        [(terminal_x, 5.0), (terminal_x - 30.0, 5.0)],
        serves=serves,
        terminal=(terminal_x, 5.0),
        **(extra_road_kwargs or {}),
    )
    return _access(
        [road],
        [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )


# ----------------------------------------------------------------- served by declaration
def test_group_is_served_by_a_declared_relation():
    layout = _declared_group_case()
    group = layout.groups[0]
    assert group.declared is True
    assert group.served_by_relation is True
    assert group.served is True
    assert group.access_road_id == "BR-1"
    assert group.terminal_xy == (-3.45, 5.0)
    assert group.terminal_centerline_distance_m == pytest.approx(3.45)
    assert group.terminal_to_building_m == pytest.approx(3.45)
    assert group.route_crossing_length_m == 0.0
    assert group.terminal_corridor_edge_clearance_m is not None
    assert group.relation_errors == ()
    assert layout.groups_served == 1
    assert layout.road_access_coverage == 1.0
    assert layout.relation_errors == ()


def test_group_without_declaration_is_unserved_even_next_to_a_road():
    road = _road("BR-PROXIMITY", "branch", [(-3.0, 5.0), (-40.0, 5.0)], terminal=(-3.0, 5.0))
    layout = _access(
        [road], [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    group = layout.groups[0]
    assert group.declared is False
    assert group.served is False
    assert group.served_by_relation is False
    assert group.terminal_centerline_distance_m is None
    assert [item["code"] for item in group.relation_errors] == [RELATION_NO_DECLARATION]
    assert layout.road_access_coverage == 0.0
    assert layout.unserved_group_ids == ("G-1",)


def test_multiple_declared_roads_fail_the_relation():
    roads = [
        _road("BR-A", "branch", [(-3.45, 2.0), (-40.0, 2.0)], serves=("G-1",), terminal=(-3.45, 2.0)),
        _road("BR-B", "branch", [(-3.45, 8.0), (-40.0, 8.0)], serves=("G-1",), terminal=(-3.45, 8.0)),
    ]
    layout = _access(
        roads, [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    group = layout.groups[0]
    assert group.declared is True
    assert group.served is False
    assert [item["code"] for item in group.relation_errors] == [RELATION_MULTIPLE_DECLARATIONS]


def test_declared_road_without_terminal_is_an_error():
    road = _road("BR-NOTERM", "branch", [(-3.45, 5.0), (-40.0, 5.0)], serves=("G-1",), terminal=None)
    layout = _access(
        [road], [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    group = layout.groups[0]
    assert group.served is False
    assert [item["code"] for item in group.relation_errors] == [RELATION_MISSING_TERMINAL]


def test_main_road_cannot_declare_a_group_access_relation():
    layout = _declared_group_case(class_name="main")
    group = layout.groups[0]
    assert group.served is False
    assert RELATION_NOT_ACCESS_CLASS in [item["code"] for item in group.relation_errors]


# ----------------------------------------------------------------- terminal band
def test_terminal_below_the_band_is_rejected():
    layout = _declared_group_case(terminal_x=-3.0)  # 3.0 m < 3.4 m lower bound
    group = layout.groups[0]
    assert group.served is False
    assert RELATION_TERMINAL_DISTANCE in [item["code"] for item in group.relation_errors]
    assert group.terminal_centerline_distance_m == 3.0


def test_terminal_above_the_band_is_rejected():
    layout = _declared_group_case(terminal_x=-3.6)  # 3.6 m > 3.5 m upper bound
    group = layout.groups[0]
    assert group.served is False
    assert RELATION_TERMINAL_DISTANCE in [item["code"] for item in group.relation_errors]


def test_band_constants():
    assert (TERMINAL_DISTANCE_MIN_M, TERMINAL_DISTANCE_MAX_M) == (3.4, 3.5)


def test_terminal_inside_a_footprint_is_rejected():
    layout = _declared_group_case(terminal_x=5.0)  # inside box(0,0,10,10)
    group = layout.groups[0]
    assert group.served is False
    codes = [item["code"] for item in group.relation_errors]
    assert RELATION_TERMINAL_INSIDE_FOOTPRINT in codes


def test_route_crossing_the_footprint_is_rejected():
    road = _road(
        "BR-CUT", "branch", [(5.0, 5.0), (-3.45, 5.0)],  # starts inside, ends outside
        serves=("G-1",), terminal=(-3.45, 5.0),
    )
    layout = _access(
        [road], [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    group = layout.groups[0]
    assert group.served is False
    assert RELATION_ROUTE_CROSSING in [item["code"] for item in group.relation_errors]
    assert group.route_crossing_length_m > 0.1


def test_declared_terminal_must_sit_on_the_serving_road():
    # ATTACK1: the claim is near the building but 100 m away from its own road.
    road = _road(
        "BR-FABRICATED", "branch", [(100.0, 5.0), (200.0, 5.0)],
        serves=("G-1",), terminal=(-3.45, 5.0),
    )
    layout = _access(
        [road], [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    group = layout.groups[0]
    assert group.served is False
    assert group.relation_errors
    assert RELATION_TERMINAL_NOT_ON_ROAD in [item["code"] for item in group.relation_errors]


def test_orphan_declared_group_is_reported():
    # ATTACK2: G-99 does not exist, but a road declares it.
    road = _road(
        "BR-1", "branch", [(-3.45, 5.0), (-33.45, 5.0)],
        serves=("G-1", "G-99"), terminal=(-3.45, 5.0),
    )
    layout = _access(
        [road], [_building("B1", 0.0, 0.0)],
        [SimpleNamespace(group_id="G-1", building_ids=("B1",))],
    )
    assert layout.groups[0].served is True  # the real group is still served
    orphans = [
        item for item in layout.relation_errors
        if item["code"] == ORPHAN_DECLARED_GROUP
    ]
    assert [item["group_id"] for item in orphans] == ["G-99"]
    payload = layout.to_dict()
    assert payload["orphan_declared_group_ids"] == ["G-99"]
    assert payload["relation_error_count"] == 1


def test_corridor_edge_clearance_is_recorded_separately_from_the_terminal_band():
    branch = _declared_group_case()
    tangent = branch.groups[0].terminal_corridor_edge_clearance_m
    inset = _declared_group_case(
        extra_road_kwargs={"corridor": box(-8.0, -2.0, -2.0, 12.0)}
    )
    access_clearance = inset.groups[0].terminal_corridor_edge_clearance_m
    assert tangent is not None and access_clearance is not None
    assert tangent == 0.0  # 7 m branch round cap tangent to the facade
    assert access_clearance == 2.0  # 4 m access corridor offset from the facade
    assert tangent != access_clearance


# ----------------------------------------------------------------- entrances
def test_entrance_proximity_is_not_a_designed_driveway():
    road = _road("MAIN-1", "main", [(0.0, 0.0), (100.0, 0.0)], width_m=12.0)
    near = SimpleNamespace(entrance_id="E-NEAR", status="proposed", point=Point(20.0, 6.0))
    existing = SimpleNamespace(entrance_id="SK-GAR-0001", status="existing", point=Point(20.0, 25.0))
    layout = _access([road], [_building("B1", 300.0, 300.0)], [], [near, existing])
    by_id = {item.entrance_id: item for item in layout.entrances}
    near_record = by_id["E-NEAR"]
    assert near_record.proximity_connected is True
    assert near_record.connected is True
    assert near_record.driveway_designed is False
    assert "proximity only" in near_record.reason
    assert "driveway geometry not designed" in near_record.reason
    existing_record = by_id["SK-GAR-0001"]
    assert existing_record.connected is False
    assert existing_record.driveway_designed is False
    assert "garage face" in existing_record.reason


# ----------------------------------------------------------------- dead ends
def test_dead_end_classification_and_t_junction_exclusion():
    buildings = [_building("B-NEAR", 0.0, 0.0), _building("B-FAR", 200.0, 200.0)]
    roads = [
        _road("BR-J", "branch", [(-2.0, 5.0), (-40.0, 5.0)]),
        _road("MAIN-U", "main", [(500.0, 500.0), (540.0, 500.0)]),
        _road("MAIN-C", "main", [(-5.0, 12.0), (-60.0, 12.0)]),
        _road("BR-T", "branch", [(50.0, 0.0), (50.0, 40.0)]),
        _road("MAIN-T", "main", [(0.0, 0.0), (100.0, 0.0)]),
    ]
    layout = _access(roads, buildings, [])
    coordinates = {record.coordinate for record in layout.dead_ends}
    assert (50.0, 0.0) not in coordinates  # T junction on MAIN-T interior
    by_road = {}
    for record in layout.dead_ends:
        by_road.setdefault(record.road_id, []).append(record)
    justified = next(r for r in by_road["BR-J"] if r.coordinate == (-2.0, 5.0))
    assert justified.classification == "group_terminal_justified"
    unfinished = next(r for r in by_road["MAIN-U"] if r.coordinate == (500.0, 500.0))
    assert unfinished.classification == "main_stub_unfinished"
    unclassified = next(r for r in by_road["MAIN-C"] if r.coordinate == (-5.0, 12.0))
    assert unclassified.classification == "unclassified"
    assert layout.dead_ends_unresolved == sum(
        1 for record in layout.dead_ends if not record.justified
    )
    assert layout.dead_ends_justified + layout.dead_ends_unresolved == len(layout.dead_ends)


# ----------------------------------------------------------------- overlap helper
def test_main_road_building_overlap_is_listed_per_road_and_building():
    main = _road(
        "MAIN-OVERLAP", "main", [(0.0, 5.0), (100.0, 5.0)], width_m=12.0,
        corridor=box(0.0, -1.0, 100.0, 11.0),
    )
    building = _building("B-1", 20.0, 2.0)  # overlaps corridor: 10 m x 8 m = 80 m2
    overlap = main_road_building_overlap(
        SimpleNamespace(buildings=(building,)), SimpleNamespace(roads=(main,))
    )
    assert overlap["status"] == "known_unresolved"
    assert overlap["area_m2"] > 0.0
    assert overlap["conflicts"] == [
        {"road_id": "MAIN-OVERLAP", "building_id": "B-1", "area_m2": overlap["area_m2"]}
    ]


def test_main_road_building_overlap_empty_when_clear():
    main = _road(
        "MAIN-CLEAR", "main", [(0.0, 100.0), (100.0, 100.0)],
        corridor=box(0.0, 94.0, 100.0, 106.0),
    )
    overlap = main_road_building_overlap(
        SimpleNamespace(buildings=(_building("B-1", 20.0, 0.0),)),
        SimpleNamespace(roads=(main,)),
    )
    assert overlap["area_m2"] == 0.0
    assert overlap["conflicts"] == []
    assert overlap["status"] == "resolved"


# ----------------------------------------------------------------- M4c-2 alignment / resolutions
def test_dead_end_resolution_binds_criterion_and_geometry():
    # A site-edge terminus is only "resolved" when criterion_met is True AND the
    # geometry proves it: the road's corridor is clipped at the boundary (its
    # corridor reaches the boundary but does not leave it) and the centreline is
    # inside.
    road = _road("MAIN-S", "main", [(-96.5, 5.0), (50.0, 5.0)], width_m=7.0)
    site = box(-100.0, 0.0, 100.0, 100.0)
    resolutions = [{
        "node_id": "DE-01",
        "road_id": "MAIN-S",
        "strategy": "site_edge_terminus",
        "criterion_met": True,
        "original_xy": [-96.5, 5.0],
        "adjusted_xy": [-96.5, 5.0],
        "extended_to_site_boundary": False,
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=()),
        SimpleNamespace(roads=(road,), dead_end_resolutions=tuple(resolutions)),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
        site_boundary=site,
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-01"].resolution == "site_edge_terminus"
    assert by_id["DE-01"].resolved is True
    assert by_id["DE-01"].resolution_verified is True
    assert by_id["DE-02"].resolved is False  # the far end has no resolution
    assert layout.dead_ends_unresolved == 1
    assert layout.dead_ends_resolved == 1
    payload = layout.to_dict()
    assert payload["dead_ends_resolved"] == 1
    assert payload["dead_ends"][0]["resolution_verified"] is True


def test_forged_criterion_met_false_is_unresolved():
    road = _road("MAIN-S", "main", [(-98.0, 5.0), (50.0, 5.0)])
    site = box(-100.0, 0.0, 100.0, 100.0)
    resolutions = [{
        "node_id": "DE-01",
        "road_id": "MAIN-S",
        "strategy": "site_edge_terminus",
        "criterion_met": False,  # forged/self-reported failure must not resolve
        "adjusted_xy": [-98.0, 5.0],
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=()),
        SimpleNamespace(roads=(road,), dead_end_resolutions=tuple(resolutions)),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
        site_boundary=site,
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-01"].resolution == "site_edge_terminus"
    assert by_id["DE-01"].resolved is False
    assert by_id["DE-01"].resolution_verified is False
    assert layout.dead_ends_unresolved == 2


def test_forged_resolution_coordinates_are_unresolved():
    road = _road("MAIN-S", "main", [(-98.0, 5.0), (50.0, 5.0)])
    site = box(-100.0, 0.0, 100.0, 100.0)
    resolutions = [{
        "node_id": "DE-01",
        "road_id": "MAIN-S",
        "strategy": "site_edge_terminus",
        "criterion_met": True,
        "adjusted_xy": [-98.0, 40.0],  # not on the resolving road
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=()),
        SimpleNamespace(roads=(road,), dead_end_resolutions=tuple(resolutions)),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
        site_boundary=site,
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-01"].resolved is False
    assert by_id["DE-01"].resolution_verified is False


def test_trimmed_resolution_still_degree_one_is_unresolved():
    road = _road("MAIN-U", "main", [(500.0, 500.0), (540.0, 500.0)])
    resolutions = [{
        "node_id": "DE-01",
        "road_id": "MAIN-U",
        "strategy": "trimmed",
        "criterion_met": True,
        "adjusted_xy": [500.0, 500.0],  # unchanged: still a degree-1 endpoint
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=()),
        SimpleNamespace(roads=(road,), dead_end_resolutions=tuple(resolutions)),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-01"].resolved is False


def test_bridged_resolution_crossing_a_building_is_unresolved():
    main = _road("MAIN-X", "main", [(0.0, 0.0), (100.0, 0.0)])
    target = _road("MAIN-Y", "main", [(-50.0, -50.0), (50.0, -50.0)])
    building = _building("B-BLOCK", -5.0, -40.0)  # sits on the bridge segment
    resolutions = [{
        "node_id": "DE-01",
        "road_id": "MAIN-X",
        "strategy": "bridged",
        "criterion_met": True,
        "adjusted_xy": [0.0, 0.0],
        "junction_id": "J-1",
        "bridge_road_id": "MAIN-Y",
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=(building,)),
        SimpleNamespace(
            roads=(main, target),
            dead_end_resolutions=tuple(resolutions),
            explicit_junctions=({"id": "J-1", "x": 0.0, "y": -50.0,
                                 "road_ids": ["MAIN-X", "MAIN-Y"]},),
        ),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-01"].resolution == "bridged"
    assert by_id["DE-01"].resolved is False
    assert by_id["DE-01"].resolution_verified is False


def test_bridged_resolution_with_clear_span_is_verified():
    main = _road("MAIN-X", "main", [(0.0, 0.0), (100.0, 0.0)])
    target = _road("MAIN-Y", "main", [(-50.0, -50.0), (50.0, -50.0)])
    building = _building("B-AWAY", 200.0, 200.0)
    resolutions = [{
        "node_id": "DE-02",  # (0, 0): the MAIN-X stub next to the junction
        "road_id": "MAIN-X",
        "strategy": "bridged",
        "criterion_met": True,
        "original_xy": [0.0, 0.0],
        "adjusted_xy": [0.0, 0.0],
        "junction_id": "J-1",
        "bridge_road_id": "MAIN-Y",
    }]
    layout = build_road_access(
        SimpleNamespace(buildings=(building,)),
        SimpleNamespace(
            roads=(main, target),
            dead_end_resolutions=tuple(resolutions),
            explicit_junctions=({"id": "J-1", "x": 0.0, "y": -50.0,
                                 "road_ids": ["MAIN-X", "MAIN-Y"]},),
        ),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
    )
    by_id = {record.node_id: record for record in layout.dead_ends}
    assert by_id["DE-02"].resolution == "bridged"
    assert by_id["DE-02"].resolved is True
    assert by_id["DE-02"].resolution_verified is True
    assert layout.dead_ends_unresolved < len(layout.dead_ends)


def test_alignment_records_are_passed_through():
    road = _road("MAIN-1", "main", [(0.0, 0.0), (100.0, 0.0)])
    layout = build_road_access(
        SimpleNamespace(buildings=()),
        SimpleNamespace(
            roads=(road,),
            main_alignment_records=(
                {"road_id": "MAIN-19", "max_displacement_m": 4.2,
                 "overlap_before_m2": 38.19, "overlap_after_m2": 0.0},
            ),
        ),
        SimpleNamespace(groups=()),
        SimpleNamespace(entrances=()),
        _basis(),
    )
    assert layout.road_alignment_count == 1
    payload = layout.to_dict()
    assert payload["main_alignment_records"][0]["road_id"] == "MAIN-19"
    assert payload["road_alignment_count"] == 1


def test_unresolved_dead_ends_count_only_without_resolution_and_justification():
    roads = [
        _road("MAIN-U", "main", [(500.0, 500.0), (540.0, 500.0)]),  # two unresolved stubs
        _road("BR-J", "branch", [(-2.0, 5.0), (-40.0, 5.0)]),  # near end justified
    ]
    layout = _access(
        roads,
        [_building("B-NEAR", 0.0, 0.0)],
        [],
    )
    assert layout.dead_ends_justified == 1
    # 2 unfinished MAIN-U stubs + the far BR-J end, none of them resolved
    assert layout.dead_ends_unresolved == 3


def test_missing_dead_end_resolution_fields_are_backwards_compatible():
    layout = _access(
        [_road("MAIN-U", "main", [(500.0, 500.0), (540.0, 500.0)])],
        [_building("B-NEAR", 0.0, 0.0)],
        [],
    )
    assert layout.main_alignment_records == ()
    assert layout.dead_end_resolutions == ()
    assert all(record.resolution is None for record in layout.dead_ends)
    assert layout.dead_ends_unresolved == len(layout.dead_ends)



# ----------------------------------------------------------------- serialisation / coverage
def test_layout_serialisation_and_coverage_arithmetic():
    layout = _declared_group_case()
    payload = layout.to_dict()
    assert payload["schema_id"] == "dgcad.design-road-access.v0.2"
    assert payload["groups_served"] == 1
    assert payload["road_access_coverage"] == 1.0
    assert payload["dead_ends_unresolved"] == layout.dead_ends_unresolved
    assert payload["relation_error_count"] == 0
    assert "main_road_overlap" in payload
    assert payload["groups"][0]["declared"] is True
    assert payload["groups"][0]["served_by_relation"] is True
    assert payload["groups"][0]["terminal_corridor_edge_clearance_m"] is not None
    json.dumps(payload)


def test_empty_inputs_do_not_divide_by_zero():
    layout = _access([], [], [])
    assert layout.groups_total == 0
    assert layout.road_access_coverage == 0.0
    assert layout.dead_ends == ()
    assert layout.main_road_overlap["area_m2"] == 0.0


# ----------------------------------------------------------------- integration (R1 design)
def _waiting_for_roads(road_layout) -> bool:
    return not hasattr(road_layout.roads[0], "serves_group_ids")


@lru_cache(maxsize=1)
def _r1_models():
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)
    standard = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input, intent, basis, standard, site_inner, design_rect
    )
    road_layout = build_road_layout(design_input, basis, intent, building_layout)
    parking = build_parking_layout(design_input, intent, road_layout, basis)
    access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking,
        basis,
        site_boundary=design_input.site_boundary,
    )
    return basis, building_layout, road_layout, parking, access


def test_r1_design_groups_are_served_by_declared_relations():
    basis, building_layout, road_layout, parking, access = _r1_models()
    assert not _waiting_for_roads(road_layout), (
        "waiting for roads declarative fields (serves_group_ids / "
        "access_terminal_xy) from M4c-1e step 1"
    )
    assert access.groups_total == 17
    assert access.groups_served == 17, (
        "unserved groups: " + ", ".join(access.unserved_group_ids)
        + " (waiting for roads declarative fields)"
    )
    assert access.road_access_coverage == 1.0
    assert access.relation_errors == ()
    clearance = basis.building_road_clearance_m + 0.5
    declared_counts = {}
    for road in road_layout.roads:
        for group_id in getattr(road, "serves_group_ids", ()) or ():
            declared_counts[group_id] = declared_counts.get(group_id, 0) + 1
    for group in access.groups:
        assert group.declared is True
        assert group.served_by_relation is True
        assert declared_counts.get(group.group_id) == 1
        assert TERMINAL_DISTANCE_MIN_M <= group.terminal_centerline_distance_m <= TERMINAL_DISTANCE_MAX_M
        assert group.terminal_corridor_edge_clearance_m is not None
        assert group.terminal_corridor_edge_clearance_m <= clearance
    by_id = {group.group_id: group for group in access.groups}
    assert by_id["G-08"].access_road_id == "BR-G-08"
    assert by_id["G-13"].access_road_id == "BR-G-13"


def test_r1_design_removing_a_declaration_breaks_that_group_only():
    basis, building_layout, road_layout, parking, access = _r1_models()
    assert not _waiting_for_roads(road_layout), (
        "waiting for roads declarative fields (serves_group_ids / "
        "access_terminal_xy) from M4c-1e step 1"
    )
    copied_roads = []
    for road in road_layout.roads:
        data = {
            field.name: getattr(road, field.name)
            for field in dataclasses.fields(road)
        }
        if "G-08" in (data.get("serves_group_ids") or ()):
            data["serves_group_ids"] = ()
        copied_roads.append(SimpleNamespace(**data))
    intent = build_design_intent(load_design_input(CASE, basis), basis)
    mutated = build_road_access(
        building_layout,
        SimpleNamespace(roads=tuple(copied_roads)),
        intent,
        parking,
        basis,
    )
    by_id = {group.group_id: group for group in mutated.groups}
    assert by_id["G-08"].served is False
    assert by_id["G-08"].declared is False
    assert mutated.road_access_coverage < 1.0
    assert "G-08" in mutated.unserved_group_ids


def test_r1_dead_ends_match_noded_topology_and_are_classified():
    _, _, road_layout, _, access = _r1_models()
    assert len(access.dead_ends) == road_layout.noded_topology.dead_end_count
    for record in access.dead_ends:
        assert record.classification in (
            "group_terminal_justified",
            "main_stub_unfinished",
            "unclassified",
        )
    assert access.dead_ends_justified + access.dead_ends_unresolved <= len(access.dead_ends)
    if hasattr(road_layout, "dead_end_resolutions"):
        assert access.dead_ends_unresolved == 0, (
            "unresolved dead ends: "
            + ", ".join(
                record.node_id for record in access.dead_ends
                if not record.resolved and not record.justified
            )
        )
        assert all(record.resolution for record in access.dead_ends if not record.justified)


def test_r1_main_road_overlap_is_resolved_not_hidden():
    _, building_layout, road_layout, _, access = _r1_models()
    if not hasattr(road_layout, "main_alignment_records"):
        raise AssertionError(
            "waiting for roads alignment fields (main_alignment_records / "
            "dead_end_resolutions) from M4c-2 step 1"
        )
    overlap = access.main_road_overlap
    assert overlap["area_m2"] <= 0.01, (
        f"main-road/building overlap still {overlap['area_m2']} m2 after alignment"
    )
    assert overlap["status"] == "resolved"
    assert overlap["conflicts"] == []


def test_r1_main_alignment_evidence_is_recorded():
    _, _, road_layout, _, access = _r1_models()
    if not hasattr(road_layout, "main_alignment_records"):
        raise AssertionError(
            "waiting for roads alignment fields (main_alignment_records / "
            "dead_end_resolutions) from M4c-2 step 1"
        )
    assert access.main_alignment_records
    records = [record for record in access.to_dict()["main_alignment_records"]]
    for record in records:
        assert record["road_id"]
        assert "max_displacement_m" in record or "displacement_m" in record
    assert road_layout.main_overlap_resolved is True
    assert access.dead_end_resolutions

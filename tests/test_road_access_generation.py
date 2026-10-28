"""Design-aware road access generation (M4c-1b).

M4c-1a made the network topologically connected. M4c-1b makes it *reach the
buildings*: every building group gets a design access branch whose terminal is
3.5 m outside the nearest group frontage (clearance 3.0 m + 0.5 m allowed
tolerance), the route does not cut through any footprint, the junction to the
existing network is an explicit shared vertex, the access loop no longer
overlaps a building, and new access corridors stay within the 1.0 m2
per-building overlap budget.

The MAIN-road corridors still overlap the coarse full-site building context by
~38.2 m2; that is a pre-existing source-alignment conflict and is asserted as a
*known baseline* here (M4c-2 / full-site scope), never as a pass.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
from shapely.geometry import Point
from shapely.ops import unary_union

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.roads import (
    ACCESS_CORRIDOR_OVERLAP_MAX_M2,
    ACCESS_ROUTE_FOOTPRINT_CROSS_MAX_M,
    ACCESS_TERMINAL_DISTANCE_M,
    build_road_layout,
)
from dgcad_design.topology import (
    VIOLATION_COMPONENT_COUNT,
    VIOLATION_CROSSING_ONLY,
    VIOLATION_UNDECLARED_RING,
    topology_violations,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"

#: pre-existing MAIN corridor vs coarse full-site context (source alignment)
MAIN_OVERLAP_KNOWN_BASELINE_M2 = 38.19068149970835
MAIN_OVERLAP_BASELINE_RANGE_M2 = (38.0, 38.5)


@lru_cache(maxsize=1)
def _r1_design():
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standard = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standard,
        site_inner,
        design_rect,
    )
    layout = build_road_layout(
        design_input, basis, intent, building_layout
    )
    return basis, design_input, intent, building_layout, layout


def _layout():
    return _r1_design()[4]


def _road_by_id(edge_id: str):
    for road in _layout().roads:
        if road.edge_id == edge_id:
            return road
    raise AssertionError(f"road {edge_id} not found")


def _group_access_road(group_id: str):
    """Group access connector: BR-<gid> (7 m branch) or ACC-<gid> (4 m lane)."""
    layout = _layout()
    for edge_id, expected_class in (
        (f"BR-{group_id}", "branch"),
        (f"ACC-{group_id}", "access"),
    ):
        for road in layout.roads:
            if road.edge_id == edge_id:
                assert road.class_name == expected_class, (
                    edge_id, road.class_name
                )
                return road
    raise AssertionError(f"no access road for {group_id}")


def _group_buildings(group):
    building_layout = _r1_design()[3]
    by_id = {item.building_id: item for item in building_layout.buildings}
    return [by_id[bid] for bid in group.building_ids if bid in by_id]


def _groups_with_buildings():
    intent = _r1_design()[2]
    return [
        group for group in intent.groups if _group_buildings(group)
    ]


def _terminal(road) -> Point:
    coords = list(road.centerline.coords)
    return Point(float(coords[-1][0]), float(coords[-1][1]))


def _all_footprints():
    building_layout = _r1_design()[3]
    return [item.footprint for item in building_layout.buildings]


def _junction_map():
    return {item["id"]: item for item in _layout().explicit_junctions}


# --------------------------------------------------------- group access
def test_every_group_with_buildings_has_a_clean_access_branch():
    footprints = _all_footprints()
    groups = _groups_with_buildings()
    assert len(groups) == 17
    for group in groups:
        road = _group_access_road(group.group_id)
        assert road.class_name in {"branch", "access"}
        expected_width = 7.0 if road.class_name == "branch" else 4.0
        assert road.width_m == expected_width, road.edge_id
        assert road.start_junction_id is not None
        terminal = _terminal(road)
        group_union = unary_union(
            [item.footprint for item in _group_buildings(group)]
        )
        distance = terminal.distance(group_union)
        assert distance <= ACCESS_TERMINAL_DISTANCE_M + 1e-6, (
            group.group_id, distance
        )
        assert distance >= 3.4, (group.group_id, distance)
        assert not any(
            footprint.intersects(terminal) for footprint in footprints
        ), group.group_id
        crossing = sum(
            road.centerline.intersection(footprint).length
            for footprint in footprints
        )
        assert crossing <= ACCESS_ROUTE_FOOTPRINT_CROSS_MAX_M, (
            group.group_id, crossing
        )


def test_g05_and_g12_are_served_by_new_branches():
    groups = {group.group_id: group for group in _groups_with_buildings()}
    for group_id in ("G-05", "G-12"):
        assert group_id in groups
        road = _group_access_road(group_id)
        group_union = unary_union(
            [item.footprint for item in _group_buildings(groups[group_id])]
        )
        distance = _terminal(road).distance(group_union)
        assert 3.4 <= distance <= ACCESS_TERMINAL_DISTANCE_M + 1e-6
        junction = _junction_map()[road.start_junction_id]
        other_roads = [
            road_id
            for road_id in junction["road_ids"]
            if road_id != road.edge_id
        ]
        assert other_roads, group_id


def test_focus_group_also_has_an_access_branch():
    focus_group_id = _r1_design()[2].focus_group_id
    road = _group_access_road(focus_group_id)
    assert road.class_name in {"branch", "access"}
    assert road.start_junction_id is not None


def test_focus_road_clearance_holds_for_the_new_design():
    """Hard design check: detailed focus buildings clear every road corridor.

    A 7 m branch next to the focus block collided with SK-BLD-0035, so that
    group's connector is generated as a 4 m access lane; the corridor-edge
    distance must be >= 3.0 m.
    """
    layout = _layout()
    focus_footprints = [
        item.footprint for item in _r1_design()[3].focus_buildings
    ]
    minimum = min(
        footprint.distance(layout.corridor_union)
        for footprint in focus_footprints
    )
    assert minimum >= 3.0 - 1e-6, minimum


# ------------------------------------------------- service binding (M4c-1e)
def _declared_road_for_group(group_id: str):
    matches = [
        road
        for road in _layout().roads
        if group_id in road.serves_group_ids
    ]
    assert len(matches) == 1, (group_id, [r.edge_id for r in matches])
    return matches[0]


def test_service_relations_are_explicit_and_single_valued():
    layout = _layout()
    groups = _groups_with_buildings()
    declared: dict[str, list] = {}
    for road in layout.roads:
        for group_id in road.serves_group_ids:
            declared.setdefault(group_id, []).append(road)
    group_ids = {group.group_id for group in groups}
    # total declared relations: exactly one per served group, no stray ids
    assert sum(len(items) for items in declared.values()) == 17
    assert set(declared) == group_ids
    for group in groups:
        assert len(declared[group.group_id]) == 1, group.group_id
        road = _declared_road_for_group(group.group_id)
        assert road.edge_id in (
            f"BR-{group.group_id}",
            f"ACC-{group.group_id}",
        ), road.edge_id
    # network connector / loop are not group access roads
    for edge_id in ("BR-FOCUS", "ACC-FOCUS-01"):
        road = _road_by_id(edge_id)
        assert road.serves_group_ids == ()
        assert road.access_terminal_xy is None


def test_access_terminal_metadata_matches_generated_terminal():
    footprints = _all_footprints()
    for group in _groups_with_buildings():
        road = _declared_road_for_group(group.group_id)
        assert road.access_terminal_xy is not None
        terminal_xy = tuple(road.access_terminal_xy)
        # the recorded terminal is the non-junction endpoint of the centerline
        assert road.start_junction_id is not None
        assert road.end_junction_id is None
        assert terminal_xy == tuple(
            float(value) for value in road.centerline.coords[-1]
        )
        terminal = Point(terminal_xy)
        group_union = unary_union(
            [item.footprint for item in _group_buildings(group)]
        )
        assert 3.4 <= terminal.distance(group_union) <= (
            ACCESS_TERMINAL_DISTANCE_M + 1e-6
        ), (group.group_id, terminal.distance(group_union))
        assert not any(
            footprint.intersects(terminal) for footprint in footprints
        ), group.group_id


def test_road_to_dict_emits_service_binding():
    payload = _declared_road_for_group("G-12").to_dict()
    assert payload["serves_group_ids"] == ["G-12"]
    assert payload["access_terminal_xy"] is not None
    assert len(payload["access_terminal_xy"]) == 2
    main_payload = _road_by_id("MAIN-01").to_dict()
    assert main_payload["serves_group_ids"] == []
    assert main_payload["access_terminal_xy"] is None
    focus_payload = _road_by_id("BR-FOCUS").to_dict()
    assert focus_payload["serves_group_ids"] == []
    assert focus_payload["access_terminal_xy"] is None


# ------------------------------------------------------------ loop geometry
def test_access_loop_no_longer_overlaps_buildings():
    layout = _layout()
    footprint_union = unary_union(_all_footprints())
    loop = _road_by_id("ACC-FOCUS-01")
    assert loop.centerline.is_ring
    assert loop.corridor.intersection(footprint_union).area == pytest.approx(
        0.0, abs=1e-9
    )
    # the fixed-point hull included every focus building and the buildings that
    # previously collided with the loop (G-05: SK-BLD-0002/0017/0033)
    included = set(
        layout.simplification["loop_hull_included_building_ids"]
    )
    focus_ids = {
        item.building_id for item in _r1_design()[3].focus_buildings
    }
    assert focus_ids <= included
    g05_ids = {
        item.building_id
        for item in _group_buildings(
            next(
                group
                for group in _groups_with_buildings()
                if group.group_id == "G-05"
            )
        )
    }
    assert g05_ids <= included


# ------------------------------------------------------- overlap budget/evidence
def test_new_access_corridors_stay_within_overlap_budget():
    layout = _layout()
    new_access = [
        road for road in layout.roads
        if road.class_name in {"branch", "access"}
    ]
    new_union = unary_union([road.corridor for road in new_access])
    for footprint in _all_footprints():
        overlap = footprint.intersection(new_union).area
        assert overlap <= ACCESS_CORRIDOR_OVERLAP_MAX_M2 + 1e-9, overlap
    # recorded evidence agrees with the geometry
    assert layout.road_building_overlap_m2_new_access == pytest.approx(
        new_union.intersection(unary_union(_all_footprints())).area,
        rel=1e-12,
    )
    assert layout.road_building_overlap_m2_new_access < 2.5


def test_main_road_overlap_is_recorded_as_known_baseline():
    """MAIN corridors are now realigned; the old conflict is kept as history.

    ``road_building_overlap_m2_main`` preserves the historical source-alignment
    conflict (before M4c-2), while ``road_building_overlap_m2_main_after`` is the
    repaired residual, which is zero.
    """
    layout = _layout()
    main_roads = [
        road for road in layout.roads if road.class_name == "main"
    ]
    footprint_union = unary_union(_all_footprints())
    before_field = layout.road_building_overlap_m2_main
    after_field = layout.road_building_overlap_m2_main_after
    assert before_field == pytest.approx(
        MAIN_OVERLAP_KNOWN_BASELINE_M2, rel=1e-6
    )
    low, high = MAIN_OVERLAP_BASELINE_RANGE_M2
    assert low <= before_field <= high
    computed_after = unary_union(
        [road.corridor for road in main_roads]
    ).intersection(footprint_union).area
    assert after_field == pytest.approx(computed_after, abs=1e-9)
    assert after_field <= 0.01
    assert layout.main_overlap_resolved is True
    assert layout.road_building_overlap_m2_total == pytest.approx(
        layout.corridor_union.intersection(footprint_union).area,
        rel=1e-12,
    )
    assert layout.road_building_overlap_m2_total < before_field
    assert layout.simplification["main_overlap_resolved"] is True
    assert layout.simplification[
        "road_building_overlap_m2_main_after"
    ] == pytest.approx(after_field, rel=1e-12)


# --------------------------------------------------------------- topology
def test_noded_network_stays_connected_without_crossing_only():
    layout = _layout()
    topology = layout.noded_topology
    assert topology.component_count == 1
    assert topology.max_endpoint_gap_m == 0.0
    assert layout.corridor_union_pieces == 1
    codes = {item["code"] for item in topology_violations(topology)}
    for forbidden in (
        VIOLATION_COMPONENT_COUNT,
        VIOLATION_CROSSING_ONLY,
        VIOLATION_UNDECLARED_RING,
    ):
        assert forbidden not in codes, codes
    crossing_only = [
        item
        for item in topology.connector_states
        if item["state"] == "crossing_only"
    ]
    assert crossing_only == []
    # every group access branch is a justified dead-end terminal
    justified = [
        item
        for item in topology.connector_states
        if item["state"] == "dead_end"
    ]
    assert len(justified) == len(_groups_with_buildings())
    assert len(layout.junction_nodes) == topology.junction_count
    assert len(layout.dead_end_nodes) == topology.dead_end_count


def test_edge_and_junction_ids_are_consistent():
    layout = _layout()
    edge_ids = [road.edge_id for road in layout.roads]
    assert len(edge_ids) == len(set(edge_ids))
    junction_ids = [item["id"] for item in layout.explicit_junctions]
    assert len(junction_ids) == len(set(junction_ids))
    junctions = _junction_map()
    road_ids = set(edge_ids)
    for junction in layout.explicit_junctions:
        assert junction["id"]
        assert len(junction["road_ids"]) >= 2
        for referenced in junction["road_ids"]:
            assert referenced in road_ids
        coordinate = (float(junction["x"]), float(junction["y"]))
        for referenced in junction["road_ids"]:
            road = _road_by_id(referenced)
            vertices = {
                (float(x), float(y))
                for x, y in road.centerline.coords
            }
            assert coordinate in vertices, (junction["id"], referenced)
    for road in layout.roads:
        for attribute in ("start_junction_id", "end_junction_id"):
            junction_id = getattr(road, attribute)
            if junction_id is None:
                continue
            assert junction_id in junctions, (road.edge_id, attribute)
    assert _road_by_id("BR-FOCUS").start_junction_id is not None
    assert _road_by_id("BR-FOCUS").end_junction_id is not None
    assert _road_by_id("ACC-FOCUS-01").start_junction_id is None
    assert _road_by_id("ACC-FOCUS-01").end_junction_id is None


def test_simplification_counts_track_the_new_design():
    layout = _layout()
    counts = {
        name: sum(
            1 for road in layout.roads if road.class_name == name
        )
        for name in ("main", "branch", "access")
    }
    group_lanes = sum(
        1
        for road in layout.roads
        if road.edge_id.startswith("ACC-G-")
    )
    group_branches = sum(
        1
        for road in layout.roads
        if road.edge_id.startswith("BR-G-")
    )
    # G-12 (7 m branch collided with the focus block) falls back to 4 m access
    assert counts == {"main": 25, "branch": 17, "access": 2}
    assert len(layout.roads) == 44
    assert group_branches + group_lanes == 17
    assert group_lanes == 1
    assert layout.simplification["design_branch_count"] == 17
    assert layout.simplification["design_access_count"] == 2
    assert layout.simplification["design_group_access_count"] == 17
    assert layout.simplification["design_group_access_branch_count"] == 16
    assert layout.simplification["design_group_access_lane_count"] == 1
    assert layout.simplification["access_terminal_distance_m"] == 3.5
    assert layout.group_access_unserved == ()
    assert layout.simplification["group_access_unserved_ids"] == []

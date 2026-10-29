"""M4c-3 boundary-safe base design + alignment / dead-end evidence.

The published-boundary hard gate (arch-core ``evaluation``): every main-road
corridor (centreline +/- width/2) must stay inside ``site_boundary`` with at most
0.01 m tolerance.  The base design repairs the source corridor overhangs
(MAIN-08/16/18) by re-routing inside the boundary-safe free space, keeps the
MAIN-19 building-cluster diversion (the *original* 66.235 m diversion was a known
boundary violation and is not a hard pass), and resolves all seven dead ends.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import pytest
from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import build_road_access
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout
from dgcad_design.topology import topology_violations

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001" / "design-roads.geojson"

MAIN_WIDTH_M = 12.0
MAIN19_GAP_M = 11.565220076201857
MAIN19_BEFORE_M2 = 34.421783197612406
MAIN19_DISPLACEMENT_M = 66.23545861756293
MAIN08_OUTSIDE_BEFORE_M2 = 341.6908310814502
MAIN08_REPAIR_MARGIN_M = 2.446306837399009
MAIN16_OUTSIDE_BEFORE_M2 = 2.417804558565924
MAIN18_OUTSIDE_BEFORE_M2 = 8.290901115044374
BASE_BOUNDARY_MARGIN_M = 0.6735131264650868
MAIN18_DEAD_END_XY = (245.73765149901087, 19.268734294755518)
MAIN25_DEAD_END_XY = (382.2805578342904, 340.8531583264971)
MAIN18_MARGIN_M = 0.6735131264650868
MAIN25_MARGIN_M = 1.1000400835865636

EXPECTED_ROAD_IDS = {
    "MAIN-01", "MAIN-02", "MAIN-03", "MAIN-04", "MAIN-05", "MAIN-06",
    "MAIN-07", "MAIN-08", "MAIN-09", "MAIN-10", "MAIN-11", "MAIN-12",
    "MAIN-13", "MAIN-14", "MAIN-15", "MAIN-16", "MAIN-17", "MAIN-18",
    "MAIN-19", "MAIN-20", "MAIN-21", "MAIN-22", "MAIN-23", "MAIN-24",
    "MAIN-25",
    "BR-FOCUS",
    "BR-G-01", "BR-G-02", "BR-G-03", "BR-G-04", "BR-G-05", "BR-G-06",
    "BR-G-07", "BR-G-08", "BR-G-09", "BR-G-10", "BR-G-11",
    "ACC-G-12",
    "BR-G-13", "BR-G-14", "BR-G-15", "BR-G-16", "BR-G-17",
    "ACC-FOCUS-01",
}
EXPECTED_DEAD_END_ROADS = {
    "MAIN-03", "MAIN-05", "MAIN-09", "MAIN-18", "MAIN-20", "MAIN-22",
    "MAIN-25",
}
EXPECTED_STRATEGIES = {
    "MAIN-03": "trimmed",
    "MAIN-05": "trimmed",
    "MAIN-09": "bridged",
    "MAIN-18": "site_edge_terminus",
    "MAIN-20": "bridged",
    "MAIN-22": "bridged",
    "MAIN-25": "site_edge_terminus",
}


@lru_cache(maxsize=1)
def _r1_design():
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)
    standard = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input, intent, basis, standard, site_inner, design_rect
    )
    layout = build_road_layout(design_input, basis, intent, building_layout)
    return basis, design_input, intent, building_layout, layout


def _layout():
    return _r1_design()[4]


def _site_boundary():
    return _r1_design()[1].site_boundary


def _road_by_id(edge_id: str):
    for road in _layout().roads:
        if road.edge_id == edge_id:
            return road
    raise AssertionError(f"road {edge_id} not found")


def _footprint_union():
    building_layout = _r1_design()[3]
    return unary_union(
        [item.footprint for item in building_layout.buildings]
    )


def _committed_evidence() -> dict:
    return json.loads(EVIDENCE.read_text(encoding="utf-8"))


def _main_corridor_inside_boundary(road) -> bool:
    return _site_boundary().buffer(0.01).covers(road.corridor)


def _boundary_margin(road) -> float:
    boundary = _site_boundary()
    corridor = road.corridor
    if _main_corridor_inside_boundary(road):
        return float(boundary.exterior.distance(corridor))
    outside = corridor.difference(boundary)
    penetration = 0.0
    for polygon in getattr(outside, "geoms", [outside]):
        if polygon.is_empty:
            continue
        for x_value, y_value in polygon.exterior.coords:
            penetration = max(
                penetration,
                float(
                    boundary.exterior.distance(
                        Point(float(x_value), float(y_value))
                    )
                ),
            )
    return -penetration


def _degree_one_endpoints() -> set[tuple[float, float]]:
    centerlines = unary_union(
        [LineString(road.centerline.coords) for road in _layout().roads]
    )
    degree: dict[tuple[float, float], int] = {}
    lines = getattr(centerlines, "geoms", [centerlines])
    for line in lines:
        if line.geom_type != "LineString":
            continue
        coordinates = list(line.coords)
        start = (float(coordinates[0][0]), float(coordinates[0][1]))
        end = (float(coordinates[-1][0]), float(coordinates[-1][1]))
        if start == end:
            degree[start] = degree.get(start, 0) + 2
        else:
            degree[start] = degree.get(start, 0) + 1
            degree[end] = degree.get(end, 0) + 1
    return {point for point, value in degree.items() if value == 1}


# ------------------------------------------------- published-boundary gate
def test_every_main_corridor_is_inside_the_published_boundary():
    boundary = _site_boundary()
    margins = []
    for road in _layout().roads:
        if road.class_name != "main":
            continue
        assert _main_corridor_inside_boundary(road), road.edge_id
        margin = _boundary_margin(road)
        assert margin >= -1e-9, (road.edge_id, margin)
        margins.append(margin)
        for x_value, y_value in road.centerline.coords:
            assert boundary.covers(
                Point(float(x_value), float(y_value))
            ), road.edge_id
    assert min(margins) == pytest.approx(
        BASE_BOUNDARY_MARGIN_M, abs=1e-6
    )
    assert min(margins) >= 0.0
    simplification = _layout().simplification
    assert simplification["main_boundary_ok"] is True
    assert simplification["main_boundary_margin_m"] == pytest.approx(
        BASE_BOUNDARY_MARGIN_M, abs=1e-6
    )
    assert simplification["main_boundary_repair_count"] == 3


def test_main08_source_overhang_is_repaired_at_the_boundary():
    layout = _layout()
    record = next(
        item
        for item in layout.main_boundary_repairs
        if item["road_id"] == "MAIN-08"
    )
    assert record["boundary_ok_before"] is False
    assert record["boundary_ok_after"] is True
    assert record["outside_area_before_m2"] == pytest.approx(
        MAIN08_OUTSIDE_BEFORE_M2, rel=1e-6
    )
    assert record["outside_area_after_m2"] == pytest.approx(0.0, abs=1e-9)
    assert record["boundary_margin_after_m"] == pytest.approx(
        MAIN08_REPAIR_MARGIN_M, abs=1e-6
    )
    assert record["vertices_before"] == 14
    assert record["vertices_after"] > record["vertices_before"]
    road = _road_by_id("MAIN-08")
    assert _main_corridor_inside_boundary(road)
    assert road.corridor.intersection(_footprint_union()).area <= 1e-9
    # MAIN-08 is repaired in the base geometry, not by the alignment record
    assert all(
        item["road_id"] != "MAIN-08"
        for item in layout.main_alignment_records
    )


def test_main16_and_main18_source_overhangs_are_repaired():
    layout = _layout()
    repairs = {
        item["road_id"]: item for item in layout.main_boundary_repairs
    }
    assert set(repairs) == {"MAIN-08", "MAIN-16", "MAIN-18"}
    assert repairs["MAIN-16"]["outside_area_before_m2"] == pytest.approx(
        MAIN16_OUTSIDE_BEFORE_M2, rel=1e-6
    )
    assert repairs["MAIN-18"]["outside_area_before_m2"] == pytest.approx(
        MAIN18_OUTSIDE_BEFORE_M2, rel=1e-6
    )
    for road_id in ("MAIN-16", "MAIN-18"):
        assert repairs[road_id]["boundary_ok_after"] is True
        assert repairs[road_id]["outside_area_after_m2"] == pytest.approx(
            0.0, abs=1e-9
        )
        assert _main_corridor_inside_boundary(_road_by_id(road_id))


# ------------------------------------------------- main-road alignment
def test_main19_diversion_is_boundary_safe_and_keeps_endpoints():
    layout = _layout()
    record = next(
        item
        for item in layout.main_alignment_records
        if item["road_id"] == "MAIN-19"
    )
    assert record["alignment_strategy"] == "diversion"
    assert set(record["conflict_building_ids"]) == {"SK-BLD-0006"}
    assert set(record["obstacle_building_ids"]) == {"SK-BLD-0029"}
    assert record["overlap_before_m2"] == pytest.approx(
        MAIN19_BEFORE_M2, rel=1e-9
    )
    assert record["overlap_after_m2"] == pytest.approx(0.0, abs=1e-9)
    assert record["constraint_satisfied"] is True
    assert record["local_search_exhausted"] is True
    assert record["conflicting_building_gap_m"] == pytest.approx(
        MAIN19_GAP_M, rel=1e-9
    )
    assert record["max_displacement_m"] == pytest.approx(
        MAIN19_DISPLACEMENT_M, rel=1e-9
    )
    assert record["vertices_added"] == 29
    reason = record["reason"]
    assert "local search family" in reason
    assert "passage between the two buildings is infeasible" in reason
    assert "legal candidate" in reason
    assert "provably infeasible" not in reason
    assert "can clear both" not in reason
    original = record["original_centerline"]
    adjusted = record["adjusted_centerline"]
    assert adjusted[0] == pytest.approx(original[0], abs=1e-9)
    assert adjusted[-1] == pytest.approx(original[-1], abs=1e-9)
    road = _road_by_id("MAIN-19")
    assert _main_corridor_inside_boundary(road)
    assert road.corridor.intersection(_footprint_union()).area <= 1e-9


def test_main_overlap_evidence_is_honest():
    layout = _layout()
    assert layout.road_building_overlap_m2_main == pytest.approx(
        38.19068149970835, rel=1e-6
    )
    assert layout.road_building_overlap_m2_main_after == pytest.approx(
        0.0, abs=1e-9
    )
    assert layout.main_overlap_resolved is True
    footprint_union = _footprint_union()
    computed_total = layout.corridor_union.intersection(
        footprint_union
    ).area
    assert layout.road_building_overlap_m2_total == pytest.approx(
        computed_total, rel=1e-12
    )
    assert computed_total < layout.road_building_overlap_m2_main
    assert layout.simplification["main_overlap_resolved"] is True


# ------------------------------------------------------ dead-end resolution
def test_seven_dead_ends_each_have_a_recorded_strategy():
    layout = _layout()
    resolutions = list(layout.dead_end_resolutions)
    assert len(resolutions) == 7
    assert {item["road_id"] for item in resolutions} == (
        EXPECTED_DEAD_END_ROADS
    )
    for item in resolutions:
        road_id = item["road_id"]
        assert item["strategy"] == EXPECTED_STRATEGIES[road_id]
        assert item["node_id"] == f"DE-{road_id}"
        assert item["criterion_met"] is True
        assert item["boundary_distance_m"] >= 0.0
        if item["strategy"] == "site_edge_terminus":
            # no extension to the published boundary anymore: the base design
            # already insets the corridor-safe terminus, so the road ends where
            # its corridor edge is inside the boundary (margin >= 0)
            assert item["extended_to_site_boundary"] is False
            assert item["boundary_margin_m"] is not None
            assert item["boundary_margin_m"] >= 0.0
            assert item["adjusted_xy"] == pytest.approx(
                item["original_xy"], abs=1e-9
            )
            assert "corridor-safe boundary line" in item["reason"]
            assert "continues outside the site" not in item["reason"]
        elif item["strategy"] == "bridged":
            assert item["bridge_road_id"] in EXPECTED_ROAD_IDS
            assert item["bridge_road_id"] != road_id
            assert 0.0 < item["displacement_m"] <= 40.0
            junction = next(
                junction
                for junction in layout.explicit_junctions
                if junction["id"] == item["junction_id"]
            )
            assert road_id in junction["road_ids"]
            assert item["bridge_road_id"] in junction["road_ids"]
            target = _road_by_id(item["bridge_road_id"])
            vertices = {
                (float(x), float(y)) for x, y in target.centerline.coords
            }
            assert (
                float(junction["x"]), float(junction["y"])
            ) in vertices
        else:  # trimmed
            road = _road_by_id(road_id)
            vertices = {
                (float(x), float(y)) for x, y in road.centerline.coords
            }
            assert tuple(item["adjusted_xy"]) in vertices
            assert item["displacement_m"] > 0.0
            assert road.centerline.length > 1.0
    assert all(item["criterion_met"] is True for item in resolutions)
    main_18 = next(
        item for item in resolutions if item["road_id"] == "MAIN-18"
    )
    assert main_18["original_xy"] == pytest.approx(
        MAIN18_DEAD_END_XY, abs=1e-9
    )
    assert main_18["boundary_margin_m"] == pytest.approx(
        MAIN18_MARGIN_M, abs=1e-6
    )
    main_25 = next(
        item for item in resolutions if item["road_id"] == "MAIN-25"
    )
    assert main_25["original_xy"] == pytest.approx(
        MAIN25_DEAD_END_XY, abs=1e-9
    )
    assert main_25["boundary_margin_m"] == pytest.approx(
        MAIN25_MARGIN_M, abs=1e-6
    )


def test_remaining_dead_ends_are_only_justified_site_edge_and_branch_tips():
    layout = _layout()
    topology = layout.noded_topology
    assert topology.dead_end_count == 19
    assert (
        sum(
            1
            for item in topology.connector_states
            if item["state"] == "dead_end"
        )
        == 17
    )
    dead = _degree_one_endpoints()
    main_dead_road_ids = set()
    for road in layout.roads:
        if road.class_name != "main":
            continue
        coordinates = list(road.centerline.coords)
        for position in (coordinates[0], coordinates[-1]):
            xy = (float(position[0]), float(position[1]))
            if xy in dead:
                main_dead_road_ids.add(road.edge_id)
    assert main_dead_road_ids == {"MAIN-18", "MAIN-25"}


# ---------------------------------------------------- topology / access
def test_topology_ids_and_vertex_budget_are_preserved():
    layout = _layout()
    topology = layout.noded_topology
    assert topology.component_count == 1
    assert topology.max_endpoint_gap_m == 0.0
    assert topology_violations(topology) == ()
    assert layout.corridor_union_pieces == 1
    assert topology.node_count == 58
    assert topology.edge_count == 68
    assert topology.cyclomatic == 11
    assert topology.degree_histogram == {1: 19, 2: 3, 3: 33, 4: 3}
    assert topology.junction_count == 36
    assert topology.explicit_junction_count == 24
    assert topology.closed_ring_count == 3
    assert {road.edge_id for road in layout.roads} == EXPECTED_ROAD_IDS
    assert len(layout.roads) == 44
    assert layout.simplification["main_alignment_road_count"] == 1
    assert layout.simplification["main_alignment_vertices_added"] == 29
    assert layout.simplification["main_alignment_vertices_removed"] == 0
    assert layout.simplification["main_boundary_repair_count"] == 3
    assert layout.simplification["dead_end_resolution_count"] == 7
    assert layout.simplification["dead_end_resolution_strategies"] == {
        "site_edge_terminus": 2,
        "bridged": 3,
        "trimmed": 2,
    }


def test_service_binding_and_access_coverage_survive_realignment():
    basis, design_input, intent, building_layout, layout = _r1_design()
    parking = build_parking_layout(design_input, intent, layout, basis)
    access = build_road_access(
        building_layout,
        layout,
        intent,
        parking,
        basis,
        design_input.site_boundary,
    )
    assert access.road_access_coverage == pytest.approx(1.0)
    assert len(access.groups) == 17
    assert all(group.served for group in access.groups)
    assert access.dead_ends_unresolved == 0
    assert layout.group_access_unserved == ()
    assert layout.simplification["terminal_frozen_violations"] == []
    declared = {
        group_id: road
        for road in layout.roads
        for group_id in road.serves_group_ids
    }
    assert len(declared) == 17
    assert sum(len(road.serves_group_ids) for road in layout.roads) == 17
    for group_id, road in declared.items():
        terminal = Point(road.access_terminal_xy)
        group = next(
            item for item in intent.groups if item.group_id == group_id
        )
        by_id = {
            item.building_id: item
            for item in building_layout.buildings
        }
        group_union = unary_union(
            [
                by_id[building_id].footprint
                for building_id in group.building_ids
                if building_id in by_id
            ]
        )
        assert 3.4 <= terminal.distance(group_union) <= 3.5 + 1e-6
        assert not any(
            item.footprint.intersects(terminal)
            for item in building_layout.buildings
        )
    for edge_id in ("BR-FOCUS", "ACC-FOCUS-01"):
        road = _road_by_id(edge_id)
        assert road.serves_group_ids == ()
        assert road.access_terminal_xy is None


def test_access_terminals_match_committed_evidence_exactly():
    evidence = _committed_evidence()
    expected: dict[str, tuple[list[str], tuple[float, float], str, float]] = {}
    for feature in evidence["features"]:
        properties = feature["properties"]
        terminal = properties.get("access_terminal_xy")
        if terminal is None:
            continue
        expected[properties["edge_id"]] = (
            list(properties["serves_group_ids"]),
            (float(terminal[0]), float(terminal[1])),
            properties["class_name"],
            float(properties["width_m"]),
        )
    assert len(expected) == 17
    layout = _layout()
    assert {
        feature["properties"]["edge_id"]
        for feature in evidence["features"]
    } == {road.edge_id for road in layout.roads}
    for edge_id, (serves, terminal_xy, class_name, width) in expected.items():
        road = _road_by_id(edge_id)
        assert list(road.serves_group_ids) == serves
        assert road.class_name == class_name
        assert road.width_m == pytest.approx(width, abs=1e-9)
        assert road.access_terminal_xy == pytest.approx(
            terminal_xy, abs=1e-6
        )


def test_layout_to_dict_exposes_alignment_and_boundary_evidence():
    payload = _layout().to_dict()
    for key in (
        "main_alignment_records",
        "main_boundary_repairs",
        "dead_end_resolutions",
        "road_building_overlap_m2_main_after",
        "main_overlap_resolved",
    ):
        assert key in payload
    assert payload["main_overlap_resolved"] is True
    assert len(payload["dead_end_resolutions"]) == 7
    assert len(payload["main_alignment_records"]) == 1
    assert len(payload["main_boundary_repairs"]) == 3
    simplification = payload["simplification"]
    assert simplification["main_boundary_ok"] is True
    assert simplification["main_boundary_repair_count"] == 3
    json.dumps(payload)

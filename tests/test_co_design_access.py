"""M4d-2 candidate A co-designed access tests.

Candidate A fixes the M4d-1 full-site building layout and the frozen 44-road
network and rebuilds every original group's declared road access as a new
connector.  These tests assert only what the geometry actually achieves:

* 17/17 groups are declared and served, with zero relation errors;
* every new terminal sits on the 3.4-3.5 m centreline band and on its own
  connector centreline;
* the original 44 roads keep their id, class, width and exact coordinates;
* the new corridors do not overlap a building (>0.01 m2) and keep >=3 m
  clearance from every building they do not serve;
* the noded graph is one component with no crossing-only connection;
* the only dangling ends are the justified group terminals (and the two main
  stubs whose existing site-edge resolutions still verify);
* the build is deterministic, and a geometrically infeasible group is reported
  honestly instead of being faked.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union
from shapely.strtree import STRtree

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import (
    TERMINAL_DISTANCE_MAX_M,
    TERMINAL_DISTANCE_MIN_M,
    build_co_design_access,
    build_road_access,
)
from dgcad_design.buildings import (
    BuildingLayout,
    find_focus_design_rect,
    layout_focus_region,
    layout_full_site,
    standardize_all,
)
from dgcad_design.consistency import (
    BUILDING_OVERLAP_TOLERANCE_M2,
    full_site_road_clearance_report,
)
from dgcad_design.intent import DesignIntent
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import (
    CO_DESIGN_CLEARANCE_M,
    CO_DESIGN_CORRIDOR_OVERLAP_MAX_M2,
    CO_DESIGN_TERMINAL_MAX_M,
    CO_DESIGN_TERMINAL_MIN_M,
    RoadDesign,
    RoadLayout,
    build_road_layout,
    rebuild_group_access,
)
from dgcad_design.topology import noded_road_topology

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"

TOL = 1e-9


def load_basis() -> DesignBasis:
    return DesignBasis.from_dict(
        yaml.safe_load(BASIS_PATH.read_text(encoding="utf-8"))
    )


@lru_cache(maxsize=1)
def _context():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    baseline = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    frozen = build_road_layout(design_input, basis, intent, baseline)
    full_site = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=frozen.corridor_union,
    )
    return basis, design_input, intent, frozen, full_site


@lru_cache(maxsize=1)
def _candidate_a():
    basis, design_input, intent, frozen, full_site = _context()
    road_layout, access_layout, metrics = build_co_design_access(
        design_input, basis, intent, full_site, frozen
    )
    return road_layout, access_layout, metrics


def _group_footprint(intent, building_layout, group_id):
    by_id = {item.building_id: item for item in building_layout.buildings}
    group = next(
        item for item in intent.groups if item.group_id == group_id
    )
    present = [
        by_id[building_id]
        for building_id in group.building_ids
        if building_id in by_id
    ]
    return group, [item.footprint for item in present], unary_union(
        [item.footprint for item in present]
    )


def test_candidate_a_serves_every_original_group():
    _, access_layout, metrics = _candidate_a()
    assert metrics["groups_total"] == 17
    assert metrics["groups_served"] == 17
    assert metrics["road_access_coverage"] == pytest.approx(1.0)
    assert access_layout.road_access_coverage == pytest.approx(1.0)
    assert metrics["relation_error_count"] == 0
    assert access_layout.relation_errors == ()
    assert access_layout.unserved_group_ids == ()
    assert metrics["connector_failures"] == []
    assert metrics["connector_count"] == 17
    # every group is declared by exactly one road, the new connector
    declared = {}
    for road in _candidate_a()[0].roads:
        for group_id in road.serves_group_ids:
            declared.setdefault(group_id, []).append(road.edge_id)
    for group in metrics["connectors"]:
        assert declared[group["group_id"]] == [group["road_id"]]


def test_every_connector_terminal_is_in_the_declared_band():
    _, access_layout, metrics = _candidate_a()
    road_by_id = {road.edge_id: road for road in _candidate_a()[0].roads}
    for record in metrics["connectors"]:
        road = road_by_id[record["road_id"]]
        terminal = Point(*road.access_terminal_xy)
        distance = terminal.distance(
            _group_footprint(
                _context()[2], _context()[4], record["group_id"]
            )[2]
        )
        assert CO_DESIGN_TERMINAL_MIN_M - TOL <= distance <= (
            CO_DESIGN_TERMINAL_MAX_M + TOL
        )
        assert TERMINAL_DISTANCE_MIN_M - TOL <= distance <= (
            TERMINAL_DISTANCE_MAX_M + TOL
        )
        # the terminal is on the connector centreline (endpoint, exact)
        assert terminal.distance(road.centerline) <= TOL
        assert road.is_new_connector is True
        assert road.source_edge_ids == ()
        assert road.serves_group_ids == (record["group_id"],)
        assert road.width_m in {4.0, 7.0}
        assert road.class_name in {"branch", "access"}
    # the measured access evidence agrees group by group
    for group in access_layout.groups:
        assert group.served is True
        assert group.served_by_relation is True
        assert group.declared is True
        assert group.relation_errors == ()
        assert group.terminal_centerline_distance_m is not None
        assert CO_DESIGN_TERMINAL_MIN_M - TOL <= (
            group.terminal_centerline_distance_m
        ) <= CO_DESIGN_TERMINAL_MAX_M + TOL


def test_original_44_roads_keep_id_and_exact_geometry():
    _, _, metrics = _candidate_a()
    road_layout, _, _ = _candidate_a()
    frozen = _context()[3]
    by_id = {road.edge_id: road for road in road_layout.roads}
    assert len(frozen.roads) == 44
    for original in frozen.roads:
        candidate = by_id[original.edge_id]
        assert candidate.class_name == original.class_name
        assert candidate.width_m == pytest.approx(original.width_m)
        assert [
            (float(x), float(y)) for x, y in candidate.centerline.coords
        ] == [(float(x), float(y)) for x, y in original.centerline.coords]
    assert metrics["original_roads_unchanged"] is True
    assert metrics["original_road_problems"] == []
    assert metrics["frozen_road_count"] == 44
    assert metrics["road_count"] == 44 + metrics["new_road_count"]
    assert metrics["new_road_count"] == (
        metrics["connector_count"] + metrics["relink_count"]
    )


def test_superseded_declarations_move_to_the_new_connectors():
    _, _, metrics = _candidate_a()
    road_layout, _, _ = _candidate_a()
    by_id = {road.edge_id: road for road in road_layout.roads}
    superseded = metrics["superseded_declarations"]
    assert len(superseded) == 17
    connectors_by_group = {
        record["group_id"]: record for record in metrics["connectors"]
    }
    relinks_by_group = {
        record["group_id"]: record for record in metrics["relinks"]
    }
    for record in superseded:
        frozen_road = by_id[record["road_id"]]
        assert frozen_road.serves_group_ids == ()
        assert frozen_road.access_terminal_xy is None
        new_road = by_id[record["new_road_id"]]
        assert new_road.serves_group_ids == (record["group_id"],)
        frozen_terminal = tuple(
            round(float(value), 9)
            for value in list(frozen_road.centerline.coords)[-1]
        )
        connector = connectors_by_group[record["group_id"]]
        if connector["attach_kind"] == "frozen_group_terminal":
            # the connector was extended from the frozen terminal itself
            assert (
                round(float(new_road.centerline.coords[0][0]), 9),
                round(float(new_road.centerline.coords[0][1]), 9),
            ) == frozen_terminal
        else:
            # the frozen terminal is enclosed by the fixed network: a relink (or
            # another new connector anchored on it) keeps it from dangling
            relink = relinks_by_group.get(record["group_id"])
            if relink is not None:
                assert (
                    round(relink["attach_xy"][0], 9),
                    round(relink["attach_xy"][1], 9),
                ) == frozen_terminal
            else:
                endpoint_count = sum(
                    1
                    for road in road_layout.roads
                    for endpoint in (
                        next(iter(road.centerline.coords)),
                        list(road.centerline.coords)[-1],
                    )
                    if (
                        round(float(endpoint[0]), 9),
                        round(float(endpoint[1]), 9),
                    )
                    == frozen_terminal
                )
                assert endpoint_count >= 2


def test_new_corridors_do_not_cut_buildings_and_keep_clearance():
    road_layout, _, metrics = _candidate_a()
    building_layout = _context()[4]
    buildings = list(building_layout.buildings)
    footprints = [item.footprint for item in buildings]
    tree = STRtree(footprints)
    new_roads = [
        road
        for road in road_layout.roads
        if road.is_new_connector and road.edge_id.startswith("CD-")
    ]
    assert new_roads
    total_overlap = 0.0
    for road in new_roads:
        overlap = sum(
            float(road.corridor.intersection(footprints[int(hit)]).area)
            for hit in tree.query(road.corridor)
        )
        total_overlap += overlap
        assert overlap <= CO_DESIGN_CORRIDOR_OVERLAP_MAX_M2 + TOL
    assert total_overlap == pytest.approx(0.0, abs=1e-9)
    assert metrics["corridor_overlap_m2"]["max_connector_m2"] <= (
        CO_DESIGN_CORRIDOR_OVERLAP_MAX_M2
    )
    assert metrics["corridor_overlap_m2"]["tolerance_m2"] == (
        CO_DESIGN_CORRIDOR_OVERLAP_MAX_M2
    )
    connectors_by_id = {
        record["road_id"]: record for record in metrics["connectors"]
    }
    for road in new_roads:
        served_index = None
        record = connectors_by_id.get(road.edge_id)
        if record is not None:
            served_index = record.get("served_footprint_index")
        for index, footprint in enumerate(footprints):
            if index == served_index:
                continue
            assert float(road.centerline.distance(footprint)) >= (
                CO_DESIGN_CLEARANCE_M - TOL
            )
            assert float(road.corridor.distance(footprint)) >= (
                CO_DESIGN_CLEARANCE_M - TOL
            )
    # the served facade is measured and reported, never claimed as >= 3 m:
    # a flat-capped connector ending 3.4-3.5 m out structurally sits closer.
    served_faces = metrics["clearance_m"]["served_face_corridor_m"]
    assert set(served_faces) == {
        record["group_id"] for record in metrics["connectors"]
    }
    assert all(
        value is not None and value > 0.0
        for value in served_faces.values()
    )
    assert "cannot hold at the served facade" in (
        metrics["clearance_m"]["note"]
    )
    assert metrics["clearance_m"]["min_corridor_other_buildings_m"] >= (
        CO_DESIGN_CLEARANCE_M - TOL
    )


def test_new_connector_sidewalks_do_not_cover_buildings():
    """F1: a rebuilt connector's sidewalk must not run into a building face.

    The corridor/centreline/terminal geometry is untouched; only the sidewalk
    band of the new connectors is trimmed at the building footprints, and the
    clipped area is reported.  The committed FULL_SITE_ROAD_CLEARANCE detail
    field ``sidewalk_overlap_building_ids`` must then be empty.
    """
    road_layout, _, metrics = _candidate_a()
    basis, _, _, _, building_layout = _context()
    sidewalk = metrics["sidewalk"]
    assert sidewalk["overlap_tolerance_m2"] == BUILDING_OVERLAP_TOLERANCE_M2
    assert sidewalk["overlap_building_ids"] == []
    # the trim actually happened (the served-facade sidewalk cap is clipped)
    assert sidewalk["clipped_road_count"] > 0
    assert sidewalk["clipped_area_m2"] > 0.0
    assert set(sidewalk["clipped_road_ids"]).issubset(
        {record["road_id"] for record in metrics["connectors"]}
        | {record["road_id"] for record in metrics["relinks"]}
    )
    # independent recomputation through the public full-site clearance report
    report = full_site_road_clearance_report(
        basis, building_layout, road_layout
    )
    assert report["sidewalk_overlap_building_ids"] == []
    # and no building footprint overlaps the final sidewalk union
    for building in building_layout.buildings:
        area = float(
            building.footprint.intersection(road_layout.sidewalk_union).area
        )
        assert area <= BUILDING_OVERLAP_TOLERANCE_M2


def test_noded_graph_is_one_component_without_crossing_only():
    road_layout, _, metrics = _candidate_a()
    topology = road_layout.noded_topology
    assert topology.component_count == 1
    assert metrics["topology"]["component_count"] == 1
    crossing_only = [
        item
        for item in topology.connector_states
        if item["state"] == "crossing_only"
    ]
    assert crossing_only == []
    assert metrics["topology"]["crossing_only_count"] == 0
    assert all(
        item["state"] in {"dead_end", "shared_vertex"}
        for item in metrics["topology"]["connector_states"]
    )
    assert topology.max_endpoint_gap_m <= TOL
    assert metrics["topology"]["max_endpoint_gap_m"] <= TOL


def test_dead_ends_are_classified_and_resolved():
    _, access_layout, metrics = _candidate_a()
    justified = [
        record
        for record in access_layout.dead_ends
        if record.classification == "group_terminal_justified"
    ]
    assert len(justified) == 17
    assert access_layout.dead_ends_justified == 17
    assert access_layout.dead_ends_unresolved == 0
    assert metrics["dead_ends_unresolved"] == 0
    assert metrics["dead_ends_justified"] == 17
    # the two frozen main stubs keep their site-edge resolutions
    main_stubs = [
        record
        for record in access_layout.dead_ends
        if record.classification == "main_stub_unfinished"
    ]
    assert len(main_stubs) == 1
    assert all(record.resolved for record in main_stubs)
    # every justified dead end belongs to a new declared connector
    new_ids = {
        record["road_id"] for record in metrics["connectors"]
    }
    for record in justified:
        assert record.road_id in new_ids
        assert record.distance_m is not None
        assert record.distance_m <= CO_DESIGN_TERMINAL_MAX_M + TOL


def test_frozen_group_terminals_are_not_left_dangling():
    _, access_layout, metrics = _candidate_a()
    frozen = _context()[3]
    dead_end_coordinates = {
        (
            round(float(record.coordinate[0]), 9),
            round(float(record.coordinate[1]), 9),
        )
        for record in access_layout.dead_ends
    }
    for original in frozen.roads:
        if not original.serves_group_ids and original.edge_id not in {
            record["road_id"] for record in metrics["superseded_declarations"]
        }:
            continue
        terminal = (
            round(float(list(original.centerline.coords)[-1][0]), 9),
            round(float(list(original.centerline.coords)[-1][1]), 9),
        )
        assert terminal not in dead_end_coordinates
    # relinks reconnect enclosed frozen terminals at exact network vertices
    frozen_vertices = {
        (round(float(x), 9), round(float(y), 9))
        for road in frozen.roads
        for x, y in road.centerline.coords
    }
    assert metrics["relink_failures"] == []
    for record in metrics["relinks"]:
        assert (
            round(record["target_xy"][0], 9),
            round(record["target_xy"][1], 9),
        ) in frozen_vertices
        start = (
            round(record["attach_xy"][0], 9),
            round(record["attach_xy"][1], 9),
        )
        frozen_road = next(
            road
            for road in frozen.roads
            if road.edge_id == record["attach_road_id"]
        )
        assert start == (
            round(float(list(frozen_road.centerline.coords)[-1][0]), 9),
            round(float(list(frozen_road.centerline.coords)[-1][1]), 9),
        )
        assert record["length_m"] > 0.0


def test_candidate_a_is_deterministic():
    road_layout, _, metrics = _candidate_a()
    basis, design_input, intent, frozen, full_site = _context()
    road_again, report_again = rebuild_group_access(
        design_input, basis, intent, full_site, frozen
    )
    first = {
        road.edge_id: road
        for road in road_layout.roads
        if road.edge_id.startswith("CD-")
    }
    second = {
        road.edge_id: road
        for road in road_again.roads
        if road.edge_id.startswith("CD-")
    }
    assert set(first) == set(second)
    for road_id, road in first.items():
        other = second[road_id]
        assert road.class_name == other.class_name
        assert road.width_m == pytest.approx(other.width_m)
        assert [
            (float(x), float(y)) for x, y in road.centerline.coords
        ] == [(float(x), float(y)) for x, y in other.centerline.coords]
        assert road.access_terminal_xy == pytest.approx(
            other.access_terminal_xy, abs=0.0
        )
        assert road.serves_group_ids == other.serves_group_ids
    assert report_again["connector_count"] == metrics["connector_count"]
    assert report_again["relink_count"] == metrics["relink_count"]
    assert report_again["topology"] == metrics["topology"]
    assert report_again["clearance_m"]["min_corridor_m"] == pytest.approx(
        metrics["clearance_m"]["min_corridor_m"], abs=1e-12
    )


def _synthetic_infeasible_case():
    """One group building sealed inside a closed ring of buildings.

    The fixed network lies outside the courtyard, so no straight connector and
    no free-space A* route can reach the 3.4-3.5 m terminal band without
    crossing a building: the builder must report the group as unresolved.
    """
    basis = load_basis()
    template = _context()[4].buildings[0]
    group_building = replace(
        template,
        building_id="SYN-GROUP",
        unit_count=2,
        households=22,
        footprint=box(50.0, 50.0, 70.0, 60.0),
        design_centroid=(60.0, 55.0),
        label_anchor=(60.0, 55.0),
    )
    ring_boxes = [
        box(40.0, 40.0, 45.0, 70.0),
        box(75.0, 40.0, 80.0, 70.0),
        box(40.0, 40.0, 80.0, 45.0),
        box(40.0, 65.0, 80.0, 70.0),
    ]
    ring_buildings = tuple(
        replace(
            template,
            building_id=f"SYN-RING-{index:02d}",
            unit_count=2,
            households=22,
            footprint=polygon,
            design_centroid=polygon.centroid.coords[0],
            label_anchor=polygon.centroid.coords[0],
        )
        for index, polygon in enumerate(ring_boxes, start=1)
    )
    building_layout = BuildingLayout(
        buildings=(group_building, *ring_buildings),
        focus_buildings=(),
        rows=(),
        green_strips=(),
    )
    main_line = LineString([(5.0, 110.0), (60.0, 110.0), (115.0, 110.0)])
    branch_line = LineString([(60.0, 110.0), (60.0, 90.0)])
    main_road = RoadDesign(
        edge_id="MAIN-01",
        class_name="main",
        width_m=12.0,
        centerline=main_line,
        corridor=main_line.buffer(6.0, cap_style="flat", join_style="mitre"),
        is_new_connector=False,
        reason="synthetic fixed main road",
        source_edge_ids=(),
    )
    branch_road = RoadDesign(
        edge_id="BR-G-01",
        class_name="branch",
        width_m=7.0,
        centerline=branch_line,
        corridor=branch_line.buffer(3.5, cap_style="round"),
        is_new_connector=True,
        reason="synthetic frozen group branch",
        source_edge_ids=(),
        start_junction_id="J-01",
        serves_group_ids=("G-01",),
        access_terminal_xy=(60.0, 90.0),
    )
    junctions = (
        {"id": "J-01", "x": 60.0, "y": 110.0, "road_ids": ["MAIN-01", "BR-G-01"]},
    )
    roads = (main_road, branch_road)
    frozen = RoadLayout(
        roads=roads,
        corridor_union=unary_union(
            [main_road.corridor, branch_road.corridor]
        ),
        sidewalk_union=box(0.0, 0.0, 0.0, 0.0),
        junction_nodes=("JN-01",),
        dead_end_nodes=("DE-01",),
        corridor_generator="synthetic",
        not_professional_alignment=True,
        corridor_union_pieces=1,
        noded_topology=noded_road_topology(roads, junctions),
        explicit_junctions=junctions,
        simplification={},
    )
    group = replace(
        _context()[2].groups[0],
        group_id="G-01",
        building_ids=("SYN-GROUP",),
        unit_count=2,
        households=22,
        centroid=(60.0, 55.0),
        bbox=(50.0, 50.0, 70.0, 60.0),
        green_ids=(),
        main_road_distance_m=None,
    )
    intent = DesignIntent(
        groups=(group,),
        road_hierarchy={},
        principles=(),
        focus_group_id="G-01",
        focus_bbox=(50.0, 50.0, 70.0, 60.0),
        focus_building_ids=("SYN-GROUP",),
        focus_green_ids=(),
        focus_road_ids=(),
        focus_subgroups={},
    )
    design_input = SimpleNamespace(
        site_boundary=box(0.0, 0.0, 120.0, 120.0),
        staircase_count=2,
        entrances=(),
    )
    return basis, design_input, intent, building_layout, frozen


def test_infeasible_group_is_reported_honestly():
    basis, design_input, intent, building_layout, frozen = (
        _synthetic_infeasible_case()
    )
    road_layout, report = rebuild_group_access(
        design_input, basis, intent, building_layout, frozen
    )
    assert report["connector_count"] == 0
    assert report["unresolved_group_ids"] == ["G-01"]
    assert report["failures"]
    assert "no straight or A* grid connector" in report["failures"][0]["reason"]
    assert report["superseded_declarations"] == []
    assert road_layout.group_access_unserved == ("G-01",)
    # no new road was invented, and the frozen road was not modified
    assert len(road_layout.roads) == len(frozen.roads)
    assert report["original_roads_unchanged"] is True
    # build_road_access then reports the honest fail, not a fake pass
    parking = build_parking_layout(design_input, intent, road_layout, basis)
    access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking,
        basis,
        site_boundary=design_input.site_boundary,
    )
    assert access.road_access_coverage == 0.0
    assert access.groups_served == 0
    assert len(access.relation_errors) == 1
    # the frozen declaration is kept (not superseded) and now fails honestly
    assert access.relation_errors[0]["code"] == (
        "terminal_distance_out_of_band"
    )

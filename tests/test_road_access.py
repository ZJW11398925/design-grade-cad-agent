"""Design-aware road access evidence tests (M4c-1b).

Two layers:

* synthetic unit tests pin the decision rules exactly (terminal distance,
  footprint containment, route crossing, dead-end classification, entrance
  connection, coverage arithmetic) without depending on the evolving road
  generator;
* one integration test builds the real CASE-SKETCH-001 R1 design and asserts the
  M4c-1b acceptance targets (17 groups, coverage 1.0, G-05/G-12 served). That
  test needs the per-group access roads from ``roads.py`` (design-topology,
  M4c-1b step 1) and will report "waiting for roads generation" until it lands.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

from shapely.geometry import LineString, Point, box

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import (
    ACCESS_ROAD_CLASSES,
    ENTRANCE_CONNECTION_MARGIN_M,
    TERMINAL_DISTANCE_TOLERANCE_M,
    build_road_access,
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
def _road(edge_id: str, class_name: str, coordinates, width_m: float = 7.0):
    return SimpleNamespace(
        edge_id=edge_id,
        class_name=class_name,
        width_m=width_m,
        centerline=LineString(coordinates),
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


# ----------------------------------------------------------------- group served rules
def test_group_is_served_by_a_near_branch_terminal():
    building = _building("B1", 0.0, 0.0)
    # terminal 2.0 m to the left of the footprint edge, road pointing away
    road = _road("BR-1", "branch", [(-2.0, 5.0), (-30.0, 5.0)])
    layout = _access([road], [building], [SimpleNamespace(group_id="G-1", building_ids=("B1",))])
    group = layout.groups[0]
    assert group.served is True
    assert group.access_road_id == "BR-1"
    assert group.terminal_to_building_m == 2.0
    assert group.route_crossing_length_m == 0.0
    assert group.nearest_building_id == "B1"
    assert "2.000 m" in group.reason


def test_group_is_not_served_when_the_terminal_is_inside_the_footprint():
    road = _road("BR-IN", "branch", [(5.0, 5.0), (-30.0, 5.0)])
    layout = _access([road], [_building("B1", 0.0, 0.0)], [SimpleNamespace(group_id="G-1", building_ids=("B1",))])
    assert layout.groups[0].served is False


def test_group_is_not_served_beyond_clearance_plus_tolerance():
    tolerance = TERMINAL_DISTANCE_TOLERANCE_M
    # 3.0 clearance + 0.5 tolerance = 3.5; put the terminal at 4.0 m
    road = _road("BR-FAR", "branch", [(-4.0, 5.0), (-40.0, 5.0)])
    layout = _access([road], [_building("B1", 0.0, 0.0)], [SimpleNamespace(group_id="G-1", building_ids=("B1",))])
    assert layout.groups[0].served is False
    assert str(tolerance) in layout.groups[0].reason


def test_group_is_not_served_when_the_route_cuts_through_the_footprint():
    # terminal 2 m outside on the right, but the road runs through the building
    road = _road("BR-CUT", "branch", [(12.0, 5.0), (2.0, 5.0)])
    layout = _access([road], [_building("B1", 0.0, 0.0)], [SimpleNamespace(group_id="G-1", building_ids=("B1",))])
    assert layout.groups[0].served is False


def test_main_roads_never_serve_a_group():
    road = _road("MAIN-1", "main", [(-2.0, 5.0), (-60.0, 5.0)], width_m=12.0)
    layout = _access([road], [_building("B1", 0.0, 0.0)], [SimpleNamespace(group_id="G-1", building_ids=("B1",))])
    assert layout.groups[0].served is False
    assert "branch" in layout.groups[0].reason
    assert "main" not in ACCESS_ROAD_CLASSES


# ----------------------------------------------------------------- dead ends
def test_dead_end_classification_justified_unfinished_unclassified():
    buildings = [_building("B-NEAR", 0.0, 0.0), _building("B-FAR", 200.0, 200.0)]
    roads = [
        _road("BR-J", "branch", [(-2.0, 5.0), (-40.0, 5.0)]),       # near building
        _road("MAIN-U", "main", [(500.0, 500.0), (540.0, 500.0)]),  # far from any building
        _road("MAIN-C", "main", [(-5.0, 12.0), (-60.0, 12.0)]),     # near building: unclassified
        _road("BR-SHARED", "branch", [(100.0, 100.0), (140.0, 100.0)]),
        _road("BR-SHARED2", "branch", [(140.0, 100.0), (140.0, 140.0)]),
    ]
    layout = _access(roads, buildings, [])  # no groups needed for dead-end analysis

    by_road = {}
    for record in layout.dead_ends:
        by_road.setdefault(record.road_id, []).append(record)

    # the shared endpoint (140,100) appears twice -> not a dead end
    assert len(by_road["BR-SHARED"]) == 1
    assert len(by_road["BR-SHARED2"]) == 1
    justified = next(
        record for record in by_road["BR-J"] if record.coordinate == (-2.0, 5.0)
    )
    assert justified.classification == "group_terminal_justified"
    assert justified.justified is True
    assert justified.distance_m == 2.0
    unfinished = next(
        record for record in by_road["MAIN-U"] if record.coordinate == (500.0, 500.0)
    )
    assert unfinished.classification == "main_stub_unfinished"
    assert unfinished.justified is False
    assert unfinished.distance_m > 10.0
    unclassified = next(
        record for record in by_road["MAIN-C"] if record.coordinate == (-5.0, 12.0)
    )
    assert unclassified.classification == "unclassified"
    assert unclassified.justified is False
    assert layout.dead_ends_justified == 1
    assert layout.dead_ends_unfinished == 3  # both MAIN-U endpoints + MAIN-C far end
    assert len(layout.dead_ends) == 8  # 10 endpoints - the shared pair


def test_closed_ring_endpoints_are_not_dead_ends():
    ring = LineString([(0.0, 0.0), (0.0, 10.0), (10.0, 10.0), (10.0, 0.0), (0.0, 0.0)])
    road = SimpleNamespace(edge_id="ACC-RING", class_name="access", width_m=4.0, centerline=ring)
    layout = _access([road], [_building("B1", 100.0, 100.0)], [])
    assert layout.dead_ends == ()


def test_t_junction_endpoint_on_another_centreline_is_not_a_dead_end():
    # BR-T ends on the interior of MAIN-1: after noding that is a degree-3
    # junction, not a dead end, even though its coordinate has one road endpoint.
    main = _road("MAIN-1", "main", [(0.0, 0.0), (100.0, 0.0)], width_m=12.0)
    tee = _road("BR-T", "branch", [(50.0, 0.0), (50.0, 40.0)])
    layout = _access([main, tee], [_building("B1", 200.0, 200.0)], [])
    coordinates = {record.coordinate for record in layout.dead_ends}
    assert (50.0, 0.0) not in coordinates  # T junction, not a dead end
    assert (100.0, 0.0) in coordinates  # genuine main stub end
    assert (50.0, 40.0) in coordinates  # genuine branch end


def test_entrance_reason_is_honest_for_disconnected_garage_faces():
    road = _road("MAIN-1", "main", [(0.0, 0.0), (100.0, 0.0)], width_m=12.0)
    existing = SimpleNamespace(entrance_id="SK-GAR-0001", status="existing", point=Point(20.0, 25.0))
    proposed = SimpleNamespace(entrance_id="P-01", status="proposed", point=Point(20.0, 2.0))
    layout = _access([road], [_building("B1", 300.0, 300.0)], [], [existing, proposed])
    by_id = {item.entrance_id: item for item in layout.entrances}
    assert by_id["SK-GAR-0001"].connected is False
    assert "garage face" in by_id["SK-GAR-0001"].reason
    assert "driveway connection not designed" in by_id["SK-GAR-0001"].reason
    assert by_id["P-01"].connected is True
    assert by_id["P-01"].reason


# ----------------------------------------------------------------- entrance connection
def test_entrance_connection_uses_half_width_plus_one_metre():
    road = _road("MAIN-1", "main", [(0.0, 0.0), (100.0, 0.0)], width_m=12.0)  # limit 7.0
    near = SimpleNamespace(entrance_id="E-NEAR", status="proposed", point=Point(20.0, 6.0))
    far = SimpleNamespace(entrance_id="E-FAR", status="existing", point=Point(20.0, 9.0))
    layout = _access([road], [_building("B1", 300.0, 300.0)], [], [near, far])
    by_id = {item.entrance_id: item for item in layout.entrances}
    assert by_id["E-NEAR"].connected is True
    assert by_id["E-NEAR"].distance_m == 6.0
    assert by_id["E-NEAR"].nearest_road_id == "MAIN-1"
    assert by_id["E-FAR"].connected is False
    assert by_id["E-FAR"].distance_m == 9.0
    assert ENTRANCE_CONNECTION_MARGIN_M == 1.0


# ----------------------------------------------------------------- coverage / serialisation
def test_coverage_arithmetic_and_serialisation():
    roads = [
        _road("BR-1", "branch", [(-2.0, 5.0), (-40.0, 5.0)]),
        _road("BR-2", "branch", [(200.0, 200.0), (240.0, 200.0)]),
    ]
    buildings = [_building("B1", 0.0, 0.0), _building("B2", 500.0, 500.0)]
    groups = [
        SimpleNamespace(group_id="G-1", building_ids=("B1",)),
        SimpleNamespace(group_id="G-2", building_ids=("B2",)),
    ]
    layout = _access(roads, buildings, groups)
    assert layout.groups_total == 2
    assert layout.groups_served == 1
    assert layout.road_access_coverage == 0.5
    assert layout.unserved_group_ids == ("G-2",)
    payload = layout.to_dict()
    assert payload["schema_id"] == "dgcad.design-road-access.v0.1"
    assert payload["groups_total"] == 2
    assert payload["groups_served"] == 1
    assert payload["road_access_coverage"] == 0.5
    assert payload["unserved_group_ids"] == ["G-2"]
    assert len(payload["groups"]) == 2
    assert len(payload["dead_ends"]) == len(layout.dead_ends)
    import json

    json.dumps(payload)


def test_empty_inputs_do_not_divide_by_zero():
    layout = _access([], [], [])
    assert layout.groups_total == 0
    assert layout.road_access_coverage == 0.0
    assert layout.dead_ends == ()


# ----------------------------------------------------------------- integration (R1 design)
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
        building_layout, road_layout, intent, parking, basis
    )
    return basis, building_layout, road_layout, parking, access


def test_r1_design_every_group_is_served_by_an_access_road():
    basis, building_layout, road_layout, parking, access = _r1_models()
    assert access.groups_total == 17, (
        f"expected 17 building groups, got {access.groups_total}; "
        "waiting for roads.py per-group access generation (M4c-1b step 1)"
    )
    by_id = {group.group_id: group for group in access.groups}
    assert by_id["G-05"].served is True, "G-05 must be served by an access road"
    assert by_id["G-12"].served is True, "G-12 must be served by an access road"
    assert access.road_access_coverage == 1.0, (
        "unserved groups: " + ", ".join(access.unserved_group_ids)
        + " (waiting for roads.py per-group access generation)"
    )
    clearance = basis.building_road_clearance_m + TERMINAL_DISTANCE_TOLERANCE_M
    for group in access.groups:
        if group.served:
            assert group.terminal_to_building_m is not None
            assert group.terminal_to_building_m <= clearance
            assert group.route_crossing_length_m is not None
            assert group.route_crossing_length_m <= 0.1


def test_r1_access_dead_ends_match_the_noded_topology():
    _, _, road_layout, _, access = _r1_models()
    # a T-junction endpoint is not a dead end: the access count must equal the
    # noded graph's degree-1 count for the same design network
    assert len(access.dead_ends) == road_layout.noded_topology.dead_end_count, (
        f"access dead ends {len(access.dead_ends)} != noded "
        f"{road_layout.noded_topology.dead_end_count}"
    )
    assert access.dead_ends_justified + access.dead_ends_unfinished <= len(access.dead_ends)


def test_r1_entrance_points_are_points_and_serialisable():
    _, _, _, parking, access = _r1_models()
    assert all(item.point.geom_type == "Point" for item in parking.entrances)
    assert len(access.entrances) == len(parking.entrances)
    import json

    json.dumps(access.to_dict())


def test_r1_dead_ends_are_all_classified_or_explicitly_unclassified():
    _, _, _, _, access = _r1_models()
    assert access.dead_ends, "the current design still has dead ends"
    assert access.dead_ends_justified + access.dead_ends_unfinished <= len(access.dead_ends)
    for record in access.dead_ends:
        assert record.classification in (
            "group_terminal_justified",
            "main_stub_unfinished",
            "unclassified",
        )
        assert record.justified is (record.classification == "group_terminal_justified")

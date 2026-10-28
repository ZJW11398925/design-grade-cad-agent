"""Parking entrance geometry repair (M4c-1b, R18).

The published sketch marks the three existing garage-entrance candidates
(SK-GAR-0001..0003) as **polygons**, while the design model needs a point for
distance/connection checks. Before M4c-1b the polygon was stored in
``ParkingEntrance.point`` and ``ParkingLayout.to_dict()`` crashed with
``AttributeError: 'Polygon' object has no attribute 'x'``. These tests pin the
repaired contract:

* every entrance ``point`` is a shapely ``Point``;
* the original polygon is retained as ``footprint`` on existing entrances only,
  and the point lies inside that footprint;
* ``to_dict()`` is serialisable (the R18 regression);
* proposed entrances still sit exactly on the main-road network.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from shapely.ops import unary_union

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.parking import ParkingLayout, build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


@lru_cache(maxsize=1)
def _models() -> tuple:
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
    return design_input, road_layout, parking


def _parking() -> ParkingLayout:
    return _models()[2]


def test_all_entrance_points_are_points():
    parking = _parking()
    assert parking.entrances
    for entrance in parking.entrances:
        assert entrance.point.geom_type == "Point", entrance.entrance_id
        assert entrance.point.has_z is False


def test_existing_entrances_keep_polygon_footprint_and_point_inside_it():
    parking = _parking()
    existing = [item for item in parking.entrances if item.status == "existing"]
    assert [item.entrance_id for item in existing] == [
        "SK-GAR-0001",
        "SK-GAR-0002",
        "SK-GAR-0003",
    ]
    for entrance in existing:
        assert entrance.footprint is not None, entrance.entrance_id
        assert entrance.footprint.geom_type == "Polygon"
        assert entrance.footprint.contains(entrance.point) or (
            entrance.footprint.covers(entrance.point)
        ), entrance.entrance_id


def test_proposed_entrances_have_no_footprint():
    parking = _parking()
    proposed = [item for item in parking.entrances if item.status == "proposed"]
    assert len(proposed) == 2
    for entrance in proposed:
        assert entrance.footprint is None
        assert entrance.point.geom_type == "Point"


def test_parking_layout_to_dict_is_serialisable_r18_regression():
    parking = _parking()
    payload = parking.to_dict()  # used to raise AttributeError: 'Polygon' ... 'x'
    assert payload["entrance_count"] == 5
    assert len(payload["entrances"]) == 5
    for item in payload["entrances"]:
        assert isinstance(item["point"], list) and len(item["point"]) == 2
        assert all(isinstance(value, float) for value in item["point"])
        assert "footprint" not in item  # kept lean: point is the evidence value


def test_proposed_entrance_points_lie_on_the_main_road_network():
    _, road_layout, parking = _models()
    main_network = unary_union(
        [road.centerline for road in road_layout.roads if road.class_name == "main"]
    )
    proposed = [item for item in parking.entrances if item.status == "proposed"]
    assert proposed
    for entrance in proposed:
        assert entrance.point.distance(main_network) <= 1e-9, entrance.entrance_id


def test_parking_numbers_unchanged_by_the_geometry_repair():
    parking = _parking()
    assert parking.households == 2398
    assert parking.spaces_required == 2398
    assert parking.entrances_required == 5
    assert parking.assumed_nominal_capacity_spaces == 1000
    assert parking.garage_layout == "not_designed"

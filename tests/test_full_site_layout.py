"""M4d full-site building layout tests.

The full-site layout must place all 55 buildings (109 staircase units, 2398
households) on one 31 m north-south row lattice inside the fixed 44-road
corridor, keep the existing focus row layout, and report measured (not
assumed) geometry.  These tests only assert what the geometry actually
achieves; they do not widen any basis tolerance.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from shapely.geometry import Point
from shapely.ops import unary_union

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import build_road_access
from dgcad_design.buildings import (
    BuildingLayout,
    find_focus_design_rect,
    full_site_layout_report,
    layout_focus_region,
    layout_full_site,
    standardize_all,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"

ROW_KEYS = {
    "row",
    "subgroup_id",
    "y",
    "building_ids",
    "north_south_gap_m",
}


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
    road_layout = build_road_layout(
        design_input, basis, intent, baseline
    )
    return (
        basis,
        design_input,
        intent,
        standardized,
        site_inner,
        baseline,
        road_layout,
    )


@lru_cache(maxsize=1)
def _layouts():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    default_layout = layout_full_site(
        design_input, basis, intent, standardized, site_inner
    )
    layout = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    report = full_site_layout_report(layout, basis, site_inner, corridor)
    return default_layout, layout, report


def _signature(layout: BuildingLayout):
    return [
        (
            building.building_id,
            round(building.design_centroid[0], 9),
            round(building.design_centroid[1], 9),
            building.row_index,
            building.subgroup_id,
            round(building.displacement_m, 9),
        )
        for building in layout.buildings
    ]


def test_full_site_places_every_building_exactly_once():
    basis, design_input, _, _, site_inner, _, _ = _context()
    _, layout, report = _layouts()
    expected_ids = {item.trace_id for item in design_input.buildings}
    placed_ids = [item.building_id for item in layout.buildings]
    assert len(placed_ids) == 55
    assert len(set(placed_ids)) == 55
    assert set(placed_ids) == expected_ids
    assert report["building_count"] == 55
    assert report["unique_building_ids"] == 55
    # unit / household conservation
    assert sum(item.unit_count for item in layout.buildings) == 109
    assert sum(item.households for item in layout.buildings) == 2398
    assert report["unit_count_total"] == 109
    assert report["households_total"] == 2398
    assert report["facility_count"] == 1
    for item in layout.buildings:
        expected = next(
            entry
            for entry in design_input.buildings
            if entry.trace_id == item.building_id
        )
        if expected.is_facility:
            assert item.unit_count == 0
            assert item.households == 0
        else:
            assert item.unit_count == int(expected.unit_count or 0)
            assert item.households == basis.households(item.unit_count)
        # every building carries a global row and a superblock identifier
        assert isinstance(item.row_index, int) and item.row_index >= 1
        assert isinstance(item.subgroup_id, str) and item.subgroup_id
        assert item.design_orientation_deg == 0.0
        assert report["dropped_building_ids"] == []
        assert report["dropped_focus_building_ids"] == []


def test_focus_group_row_layout_is_preserved():
    _, _, _, _, _, baseline, _ = _context()
    _, layout, report = _layouts()
    baseline_ids = [item.building_id for item in baseline.focus_buildings]
    assert len(baseline_ids) == 7
    assert report["focus_building_count"] == 7
    assert report["focus_unit_count"] == 16
    assert len(layout.focus_buildings) == 7
    assert [
        item.building_id for item in layout.focus_buildings
    ] == baseline_ids
    for original, placed in zip(
        baseline.focus_buildings, layout.focus_buildings
    ):
        assert original.building_id == placed.building_id
        assert placed.footprint.equals_exact(original.footprint, 1e-9)
        assert placed.design_centroid == pytest.approx(
            original.design_centroid, abs=1e-9
        )
        assert placed.subgroup_id in {"FOCUS-1", "FOCUS-2"}
    assert layout.dropped_focus_building_ids == ()
    # the two buildings layout_focus_region could not place are ordinary row
    # buildings now: the full-site layout drops nothing.
    focus_ids = set(baseline_ids)
    assert focus_ids.issubset({item.building_id for item in layout.buildings})
    assert "SK-BLD-0038" in {
        item.building_id for item in layout.buildings
    }
    assert "SK-BLD-0061" in {
        item.building_id for item in layout.buildings
    }


def test_all_footprints_stay_inside_the_site_boundary():
    basis, _, _, _, site_inner, _, _ = _context()
    _, layout, report = _layouts()
    tolerant = site_inner.buffer(0.01)
    outside = [
        item.building_id
        for item in layout.buildings
        if not tolerant.contains(item.footprint)
    ]
    assert outside == []
    assert report["boundary_violations"] == []
    inner_bounds = site_inner.bounds
    for item in layout.buildings:
        minx, miny, maxx, maxy = item.footprint.bounds
        assert minx >= inner_bounds[0] - 0.01
        assert miny >= inner_bounds[1] - 0.01
        assert maxx <= inner_bounds[2] + 0.01
        assert maxy <= inner_bounds[3] + 0.01


def test_adjacent_rows_keep_twenty_metre_north_south_spacing():
    basis, _, _, _, _, _, _ = _context()
    _, layout, report = _layouts()
    expected = basis.north_south_spacing_m
    pairs = []
    buildings = list(layout.buildings)
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            second_bounds = second.footprint.bounds
            x_overlap = min(first_bounds[2], second_bounds[2]) - max(
                first_bounds[0], second_bounds[0]
            )
            if x_overlap <= 0.0:
                continue
            gap = max(
                second_bounds[1] - first_bounds[3],
                first_bounds[1] - second_bounds[3],
            )
            pairs.append((first.building_id, second.building_id, gap))
    assert pairs
    violations = [
        (a, b, gap)
        for a, b, gap in pairs
        if gap < expected - 0.01
    ]
    assert violations == []
    assert report["north_south_violations"] == []
    assert report["north_south_min_gap_m"] == pytest.approx(
        expected, abs=0.01
    )
    # the lattice itself: every occupied row band sits on the 31 m (11 + 20)
    # pitch, so consecutive occupied rows are a whole number of pitches apart.
    depth = basis.staircase_depth_m
    pitch = depth + expected
    row_ys = sorted(
        {
            round(float(row["y"]), 6)
            for row in layout.rows
        }
    )
    assert len(row_ys) >= 2
    for first, second in zip(row_ys, row_ys[1:]):
        # every row between the southernmost and northernmost must be occupied:
        # consecutive occupied rows are exactly one pitch apart, so no whole
        # empty row can hide a 62 m (over-spaced) gap
        assert abs((second - first) - pitch) <= 1e-6


def test_row_ordinals_are_contiguous_with_no_empty_row():
    _, _, _, _, _, _, _ = _context()
    _, layout, report = _layouts()
    ordinals = sorted({int(item.row_index) for item in layout.buildings})
    assert ordinals == list(range(1, len(ordinals) + 1))
    assert report["row_index_contiguous"] is True
    assert report["row_index_range"] == [1, len(ordinals)]
    # every ordinal in between is physically populated by at least one building
    assert len(ordinals) == report["row_count"]
    row_values = sorted({int(row["row"]) for row in layout.rows})
    assert row_values == ordinals
    # adjacent ordinal pairs keep exactly the 20 m gap: neither under nor over
    assert report["north_south_adjacent_pair_count"] > 0
    assert report["north_south_under_spacing_violations"] == []
    assert report["north_south_over_spacing_violations"] == []
    assert report["north_south_adjacent_min_gap_m"] == pytest.approx(
        20.0, abs=0.01
    )


def test_same_row_buildings_keep_side_spacing_and_do_not_overlap():
    basis, _, _, _, _, _, _ = _context()
    _, layout, report = _layouts()
    assert report["side_spacing_violations"] == []
    assert report["overlap_pairs"] == []
    by_row: dict[int, list] = {}
    for item in layout.buildings:
        by_row.setdefault(int(item.row_index), []).append(item)
    for row_index, row_buildings in by_row.items():
        for index, first in enumerate(row_buildings):
            for second in row_buildings[index + 1 :]:
                first_bounds = first.footprint.bounds
                second_bounds = second.footprint.bounds
                assert (
                    first.footprint.intersection(second.footprint).area
                    <= 0.01
                )
                y_overlap = min(first_bounds[3], second_bounds[3]) - max(
                    first_bounds[1], second_bounds[1]
                )
                if y_overlap <= 0.0:
                    continue
                gap = max(
                    second_bounds[0] - first_bounds[2],
                    first_bounds[0] - second_bounds[2],
                )
                assert gap >= basis.side_spacing_m - 1e-6


def test_buildings_clear_the_fixed_road_corridors_by_three_metres():
    basis, _, _, _, _, _, road_layout = _context()
    _, layout, report = _layouts()
    corridor = road_layout.corridor_union
    assert len(road_layout.roads) == 44
    assert report["road_clearance_required_m"] == pytest.approx(3.0)
    assert report["road_clearance_violations"] == []
    assert report["road_clearance_min_m"] >= 3.0 - 1e-6
    clearance_buffer = corridor.buffer(basis.building_road_clearance_m)
    for item in layout.buildings:
        assert item.footprint.distance(corridor) >= 3.0 - 1e-6
        assert item.footprint.intersection(clearance_buffer).area <= 0.01


def test_layout_is_deterministic():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    first = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    second = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    assert _signature(first) == _signature(second)


def test_default_corridor_matches_frozen_road_corridor():
    default_layout, layout, _ = _layouts()
    assert _signature(default_layout) == _signature(layout)


def test_rows_records_cover_the_whole_site():
    _, design_input, _, _, _, _, _ = _context()
    _, layout, report = _layouts()
    assert layout.rows
    for row in layout.rows:
        assert set(row.keys()) == ROW_KEYS
        assert isinstance(row["row"], int)
        assert isinstance(row["subgroup_id"], str) and row["subgroup_id"]
        assert isinstance(row["building_ids"], list) and row["building_ids"]
        assert isinstance(row["y"], float)
        assert row["north_south_gap_m"] == pytest.approx(20.0)
    seen = [trace_id for row in layout.rows for trace_id in row["building_ids"]]
    assert len(seen) == 55
    assert len(set(seen)) == 55
    assert set(seen) == {item.trace_id for item in design_input.buildings}
    # row ordinals agree with the stated row y and each building's record
    by_id = {item.building_id: item for item in layout.buildings}
    for row in layout.rows:
        for trace_id in row["building_ids"]:
            building = by_id[trace_id]
            assert building.row_index == row["row"]
            assert building.subgroup_id == row["subgroup_id"]
            assert (
                abs(building.footprint.bounds[1] - row["y"]) <= 1e-6
            ) or building.is_facility
    assert report["row_count"] == len({item.row_index for item in layout.buildings})
    assert report["row_records"] == len(layout.rows)
    assert report["superblock_count"] >= 1


def test_displacement_statistics_are_measured_and_consistent():
    _, design_input, intent, _, _, baseline, _ = _context()
    _, layout, report = _layouts()
    recomputed = []
    for item in layout.buildings:
        source = next(
            entry
            for entry in design_input.buildings
            if entry.trace_id == item.building_id
        )
        dx = item.design_centroid[0] - source.centroid[0]
        dy = item.design_centroid[1] - source.centroid[1]
        expected = math.hypot(dx, dy)
        assert item.displacement_m == pytest.approx(expected, abs=1e-9)
        recomputed.append(expected)
    assert report["displacement_sum_m"] == pytest.approx(
        sum(recomputed), abs=1e-6
    )
    assert report["displacement_max_m"] == pytest.approx(
        max(recomputed), abs=1e-6
    )
    assert report["displacement_min_m"] >= 0.0
    assert report["displacement_mean_m"] == pytest.approx(
        sum(recomputed) / 55, abs=1e-6
    )
    focus_ids = {item.building_id for item in baseline.focus_buildings}
    non_focus = [
        item.displacement_m
        for item in layout.buildings
        if item.building_id not in focus_ids
    ]
    assert report["displacement_sum_non_focus_m"] == pytest.approx(
        sum(non_focus), abs=1e-6
    )
    assert report["displacement_max_focus_m"] == pytest.approx(
        max(item.displacement_m for item in layout.focus_buildings),
        abs=1e-6,
    )
    assert len(report["displacements"]) == 55
    for entry in report["displacements"]:
        assert set(entry) == {
            "building_id",
            "row",
            "subgroup_id",
            "displacement_m",
            "dx_m",
            "dy_m",
        }


def test_green_strips_and_layout_interface_compatibility():
    basis, design_input, intent, standardized, site_inner, baseline, _ = (
        _context()
    )
    _, layout, _ = _layouts()
    assert layout.green_strips
    for strip in layout.green_strips:
        assert strip.area > 0.0
        assert site_inner.buffer(0.01).contains(strip)
    assert isinstance(layout, BuildingLayout)
    # the pre-existing focus entry point still behaves exactly as before
    again = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    assert len(again.buildings) == 55
    assert len(again.focus_buildings) == 7
    assert sum(item.unit_count for item in again.focus_buildings) == 16
    assert again.dropped_focus_building_ids == (
        "SK-BLD-0038",
        "SK-BLD-0061",
    )
    assert _signature(again) == _signature(baseline)

# ---------------------------------------------------------------------------
# Group-anchored variant (M4d follow-up): displacement cap + access coupling
# ---------------------------------------------------------------------------

GROUP_ANCHORED_CAP_M = 147.0


@lru_cache(maxsize=1)
def _group_anchored_layout():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    layout = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
        max_displacement_m=GROUP_ANCHORED_CAP_M,
        preserve_focus=True,
    )
    return layout


@lru_cache(maxsize=1)
def _parking_and_access():
    basis, design_input, intent, standardized, site_inner, baseline, road_layout = (
        _context()
    )
    parking = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    baseline_access = build_road_access(
        baseline,
        road_layout,
        intent,
        parking,
        basis,
        site_boundary=design_input.site_boundary,
    )
    group_layout = _group_anchored_layout()
    group_access = build_road_access(
        group_layout,
        road_layout,
        intent,
        parking,
        basis,
        site_boundary=design_input.site_boundary,
    )
    return baseline_access, group_access


def test_group_anchored_variant_respects_displacement_cap_and_hard_geometry():
    basis, design_input, _, _, site_inner, baseline, road_layout = _context()
    layout = _group_anchored_layout()
    report = full_site_layout_report(
        layout, basis, site_inner, road_layout.corridor_union
    )
    assert report["building_count"] == 55
    assert len({item.building_id for item in layout.buildings}) == 55
    assert report["unit_count_total"] == 109
    assert report["households_total"] == 2398
    # the whole point of the variant: every displacement obeys the cap
    assert report["displacement_max_m"] <= GROUP_ANCHORED_CAP_M + 1e-6
    for item in layout.buildings:
        assert item.displacement_m <= GROUP_ANCHORED_CAP_M + 1e-6
    # hard geometry is unchanged by the cap
    assert report["boundary_violations"] == []
    assert report["overlap_pairs"] == []
    assert report["side_spacing_violations"] == []
    assert report["north_south_violations"] == []
    assert report["road_clearance_violations"] == []
    assert report["road_clearance_min_m"] >= 3.0 - 1e-6
    assert report["north_south_min_gap_m"] == pytest.approx(20.0, abs=0.01)
    # the 7 focus buildings / 16 units are still the preserved focus layout
    assert report["focus_building_count"] == 7
    assert report["focus_unit_count"] == 16
    assert report["dropped_focus_building_ids"] == []
    assert report["dropped_building_ids"] == []
    for original, placed in zip(
        baseline.focus_buildings, layout.focus_buildings
    ):
        assert placed.footprint.equals_exact(original.footprint, 1e-9)


def test_group_anchored_cap_below_geometric_floor_is_rejected():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    with pytest.raises(ValueError) as excinfo:
        layout_full_site(
            design_input,
            basis,
            intent,
            standardized,
            site_inner,
            road_corridor=road_layout.corridor_union,
            max_displacement_m=25.0,
            preserve_focus=True,
        )
    message = str(excinfo.value)
    assert "max_displacement_m=25" in message
    assert "cannot place every building" in message


def test_group_anchored_layout_cannot_keep_the_declared_access_relations():
    baseline_access, group_access = _parking_and_access()
    # reference: the frozen road network's declarations are valid for the
    # baseline layout the roads were generated from
    assert baseline_access.road_access_coverage == 1.0
    assert baseline_access.relation_errors == ()
    # measured coupling: once the buildings move off that baseline (any
    # full-site layout does, to satisfy the 3 m clearance), the frozen
    # declared terminals no longer sit in the 3.4-3.5 m band
    assert group_access.road_access_coverage == 0.0
    assert len(group_access.relation_errors) == 17
    assert {
        error["code"] for error in group_access.relation_errors
    } == {"terminal_distance_out_of_band"}
    assert group_access.dead_ends_unresolved == 17


def test_group_anchored_variant_is_deterministic():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    first = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
        max_displacement_m=GROUP_ANCHORED_CAP_M,
        preserve_focus=True,
    )
    second = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
        max_displacement_m=GROUP_ANCHORED_CAP_M,
        preserve_focus=True,
    )
    assert _signature(first) == _signature(second)

"""M4d-2 candidate B: group-preserving full-site layout tests.

Candidate B keeps each of the 17 ``intent.groups`` together near its source
bbox while still regularising rows (20 m row pitch inside a group, 13 m side
spacing).  These tests assert only what the geometry achieves on the reference
case; cross-group conflicts are asserted against the measured report rather
than assumed away.
"""
from __future__ import annotations

import math
from functools import lru_cache
from pathlib import Path

import pytest
import yaml

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    BuildingLayout,
    find_focus_design_rect,
    group_preserving_layout_report,
    layout_focus_region,
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


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
def _layout_and_report():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    layout = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    report = group_preserving_layout_report(
        layout,
        basis,
        design_input,
        intent,
        site_inner,
        corridor,
    )
    return layout, report, corridor


def _signature(layout: BuildingLayout):
    return [
        (
            building.building_id,
            round(building.design_centroid[0], 9),
            round(building.design_centroid[1], 9),
            building.row_index,
            building.subgroup_id,
        )
        for building in layout.buildings
    ]


def test_conservation_and_group_identity():
    basis, design_input, intent, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    assert len(layout.buildings) == 55
    assert len({item.building_id for item in layout.buildings}) == 55
    assert {item.building_id for item in layout.buildings} == {
        item.trace_id for item in design_input.buildings
    }
    assert sum(item.unit_count for item in layout.buildings) == 109
    assert sum(item.households for item in layout.buildings) == 2398
    assert report["unit_count_total"] == 109
    assert report["households_total"] == 2398
    assert report["facility_count"] == 1
    assert report["dropped_building_ids"] == []
    assert report["group_count"] == 17
    assert report["present_group_count"] == 17
    # every building keeps the original intent group as its subgroup id
    expected: dict[str, str] = {}
    for group in intent.groups:
        for trace_id in group.building_ids:
            expected[trace_id] = group.group_id
    assert len(expected) == 55
    for item in layout.buildings:
        assert item.subgroup_id == expected[item.building_id]
        assert isinstance(item.row_index, int) and item.row_index >= 1
        assert item.design_orientation_deg == 0.0
    # every group reports its full membership
    for group_report in report["groups"]:
        assert group_report["present"] is True
        assert group_report["building_count"] == sum(
            1
            for item in layout.buildings
            if item.subgroup_id == group_report["group_id"]
        )


def test_focus_group_is_preserved():
    _, _, _, _, _, baseline, _ = _context()
    layout, report, _ = _layout_and_report()
    assert report["focus_building_count"] == 7
    assert report["focus_unit_count"] == 16
    assert report["focus_building_ids"] == sorted(
        item.building_id for item in baseline.focus_buildings
    )
    assert len(layout.focus_buildings) == 7
    for original, placed in zip(
        baseline.focus_buildings, layout.focus_buildings
    ):
        assert placed.building_id == original.building_id
        assert placed.footprint.equals_exact(original.footprint, 1e-9)
        assert placed.design_centroid == pytest.approx(
            original.design_centroid, abs=1e-9
        )
        assert placed.subgroup_id == "G-01"
    assert layout.dropped_focus_building_ids == ()


def test_boundary_containment_and_no_overlap():
    basis, design_input, _, _, site_inner, _, _ = _context()
    layout, report, _ = _layout_and_report()
    tolerant = site_inner.buffer(0.01)
    assert report["boundary_violations"] == []
    assert report["overlap_pairs"] == []
    for item in layout.buildings:
        assert tolerant.contains(item.footprint)
    bounds = site_inner.bounds
    for item in layout.buildings:
        minx, miny, maxx, maxy = item.footprint.bounds
        assert minx >= bounds[0] - 0.01
        assert miny >= bounds[1] - 0.01
        assert maxx <= bounds[2] + 0.01
        assert maxy <= bounds[3] + 0.01
    for index, first in enumerate(layout.buildings):
        for second in layout.buildings[index + 1 :]:
            assert (
                first.footprint.intersection(second.footprint).area
                <= 0.01
            )


def test_within_group_rows_keep_twenty_metre_spacing():
    basis, _, _, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    assert report["within_group_ns_violations"] == []
    # independent check: inside one group, any x-overlapping pair is exactly
    # one row pitch apart (gap 20 m), never less
    by_group: dict[str, list] = {}
    for item in layout.buildings:
        by_group.setdefault(str(item.subgroup_id), []).append(item)
    for group_id, members in by_group.items():
        for index, first in enumerate(members):
            first_bounds = first.footprint.bounds
            for second in members[index + 1 :]:
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
                assert gap >= basis.north_south_spacing_m - 0.01
        # group rows all sit on one 31 m pitch lattice
        row_ys = sorted(
            {round(item.footprint.bounds[1], 6) for item in members}
        )
        for first, second in zip(row_ys, row_ys[1:]):
            difference = second - first
            assert difference >= (
                basis.staircase_depth_m
                + basis.north_south_spacing_m
                - 1e-6
            )
            multiple = round(
                difference / (basis.staircase_depth_m + basis.north_south_spacing_m)
            )
            assert abs(
                difference
                - multiple
                * (basis.staircase_depth_m + basis.north_south_spacing_m)
            ) <= 1e-6


def test_cross_group_row_conflicts_are_measured_not_hidden():
    basis, _, _, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    measured = report["cross_group_ns_violations"]
    # recompute independently: any x-overlapping pair from different groups
    # closer than 20 m must appear in the report list
    recomputed = []
    buildings = list(layout.buildings)
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            if first.subgroup_id == second.subgroup_id:
                continue
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
            if gap < basis.north_south_spacing_m - 0.01:
                recomputed.append((first.building_id, second.building_id))
    reported = [
        tuple(sorted((item["a"], item["b"]))) for item in measured
    ]
    assert reported == sorted(tuple(sorted(pair)) for pair in recomputed)
    # on the reference case no cross-group conflict is unavoidable
    assert measured == []


def test_consecutive_row_ordinals_are_exactly_twenty_metres_apart():
    basis, _, _, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    # the global row check compares consecutive row ordinals: any x-overlapping
    # pair across them must be exactly one 20 m row pitch apart
    assert report["consecutive_row_ns_pairs"] >= 1
    assert report["consecutive_row_under_spacing_violations"] == []
    assert report["consecutive_row_over_spacing_violations"] == []
    assert report["consecutive_row_ns_min_gap_m"] == pytest.approx(
        basis.north_south_spacing_m, abs=0.01
    )
    assert report["consecutive_row_ns_max_gap_m"] == pytest.approx(
        basis.north_south_spacing_m, abs=0.01
    )
    buildings = list(layout.buildings)
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            if abs(first.row_index - second.row_index) != 1:
                continue
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
            assert gap == pytest.approx(
                basis.north_south_spacing_m, abs=0.01
            )


def test_side_spacing_and_road_clearance():
    basis, _, _, _, _, _, road_layout = _context()
    layout, report, corridor = _layout_and_report()
    assert report["side_spacing_violations"] == []
    assert report["road_clearance_violations"] == []
    assert report["road_clearance_min_m"] >= 3.0 - 1e-6
    assert len(road_layout.roads) == 44
    clearance_buffer = corridor.buffer(basis.building_road_clearance_m)
    buildings = list(layout.buildings)
    for item in buildings:
        assert item.footprint.distance(corridor) >= 3.0 - 1e-6
        assert item.footprint.intersection(clearance_buffer).area <= 0.01
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            second_bounds = second.footprint.bounds
            if (
                min(first_bounds[3], second_bounds[3])
                - max(first_bounds[1], second_bounds[1])
                <= 0.0
            ):
                continue
            gap = max(
                second_bounds[0] - first_bounds[2],
                first_bounds[0] - second_bounds[2],
            )
            assert gap >= basis.side_spacing_m - 1e-6


def test_displacement_and_group_bbox_statistics():
    _, design_input, _, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    recomputed = []
    for item in layout.buildings:
        source = next(
            entry
            for entry in design_input.buildings
            if entry.trace_id == item.building_id
        )
        expected = math.hypot(
            item.design_centroid[0] - source.centroid[0],
            item.design_centroid[1] - source.centroid[1],
        )
        assert item.displacement_m == pytest.approx(expected, abs=1e-9)
        recomputed.append(expected)
    assert report["building_displacement_sum_m"] == pytest.approx(
        sum(recomputed), abs=1e-6
    )
    assert report["building_displacement_max_m"] == pytest.approx(
        max(recomputed), abs=1e-6
    )
    assert len(report["displacements"]) == 55
    assert len(report["groups"]) == 17
    group_centroids = []
    for group_report in report["groups"]:
        members = [
            item
            for item in layout.buildings
            if item.subgroup_id == group_report["group_id"]
        ]
        source_cx = sum(
            item.source_centroid[0] for item in members
        ) / len(members)
        source_cy = sum(
            item.source_centroid[1] for item in members
        ) / len(members)
        design_cx = sum(
            item.design_centroid[0] for item in members
        ) / len(members)
        design_cy = sum(
            item.design_centroid[1] for item in members
        ) / len(members)
        centroid_displacement = math.hypot(
            design_cx - source_cx, design_cy - source_cy
        )
        assert group_report["centroid_displacement_m"] == pytest.approx(
            centroid_displacement, abs=1e-3
        )
        group_centroids.append(centroid_displacement)
        for field in (
            "source_bbox",
            "design_bbox",
            "bbox_center_dx_m",
            "bbox_center_dy_m",
            "bbox_width_change_m",
            "bbox_height_change_m",
        ):
            assert field in group_report
    assert report["group_centroid_displacement_max_m"] == pytest.approx(
        max(group_centroids), abs=1e-3
    )
    assert report["group_centroid_displacement_mean_m"] == pytest.approx(
        sum(group_centroids) / len(group_centroids), abs=1e-3
    )
    assert report["dropped_building_ids"] == []


def test_layout_is_deterministic():
    basis, design_input, intent, standardized, site_inner, _, road_layout = (
        _context()
    )
    corridor = road_layout.corridor_union
    first = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    second = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=corridor,
    )
    assert _signature(first) == _signature(second)


def test_rows_and_layout_interface():
    _, design_input, _, _, _, _, _ = _context()
    layout, report, _ = _layout_and_report()
    assert isinstance(layout, BuildingLayout)
    assert layout.rows
    assert report["row_count"] == len(
        {item.row_index for item in layout.buildings}
    )
    assert report["row_records"] == len(layout.rows)
    seen = [
        trace_id
        for row in layout.rows
        for trace_id in row["building_ids"]
    ]
    assert len(seen) == 55
    assert len(set(seen)) == 55
    assert set(seen) == {item.trace_id for item in design_input.buildings}
    by_id = {item.building_id: item for item in layout.buildings}
    for row in layout.rows:
        assert set(row.keys()) == {
            "row",
            "subgroup_id",
            "y",
            "building_ids",
            "north_south_gap_m",
        }
        for trace_id in row["building_ids"]:
            building = by_id[trace_id]
            assert building.row_index == row["row"]
            assert building.subgroup_id == row["subgroup_id"]
    assert layout.green_strips
    for strip in layout.green_strips:
        assert strip.area > 0.0

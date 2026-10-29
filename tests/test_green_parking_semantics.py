"""Honest green / parking semantics (M4c-1c / M4c-1d).

The R1 design is built through the committed pipeline (same call sequence as
``tests/test_design_synthesis.py``) and the green/parking data models are
checked for the semantics split:

* green space has **two accounts**: ``candidate_open_space_*`` (current filter
  rules, sum of classified areas) and ``unbuilt_area_m2`` / ``unbuilt_ratio``
  (plain geometric union area, no extra buffer and no area filter);
* ``designed_green_ratio`` covers only the designed classifications
  (cluster green + green strips); supplementary green is the remaining
  occupiable space;
* parking capacity is an **assumption** under ``spaces_per_entrance``, not a
  verified capacity.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
from shapely.geometry import box
from shapely.ops import unary_union

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.green import (
    OPEN_SPACE_FILTERS,
    GreenLayout,
    build_green_layout,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


@lru_cache(maxsize=1)
def _r1_models():
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
    road_layout = build_road_layout(
        design_input, basis, intent, building_layout
    )
    green = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        box(*intent.focus_bbox),
    )
    parking = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    return design_input, building_layout, road_layout, green, parking


def _site_area() -> float:
    design_input, _, _, _, _ = _r1_models()
    return design_input.site_area_m2


def _green() -> GreenLayout:
    _, _, _, green, _ = _r1_models()
    return green


# ------------------------------------------------- candidate open space account
def test_candidate_open_space_ratio_is_filtered_and_not_designed_green():
    green = _green()
    assert green.candidate_open_space_ratio == pytest.approx(
        0.616391083609783, rel=1e-12
    )
    assert green.candidate_open_space_area_m2 == pytest.approx(
        125819.46553768215, rel=1e-9
    )
    # the candidate account is the sum of the classified areas
    assert green.candidate_open_space_area_m2 == pytest.approx(
        green.cluster_area_m2
        + green.strip_area_m2
        + green.supplementary_area_m2,
        rel=1e-12,
    )
    # designed green is only cluster + strip
    assert green.designed_green_area_m2 == pytest.approx(
        green.cluster_area_m2 + green.strip_area_m2, rel=1e-12
    )


def test_open_space_filters_are_declared():
    assert OPEN_SPACE_FILTERS == {
        "boundary_setback_m": 5.0,
        "obstacle_buffer_m": 0.5,
        "min_supplementary_polygon_m2": 100.0,
    }
    payload = _empty_green_layout().to_dict()
    assert payload["open_space_filters"] == OPEN_SPACE_FILTERS


# ------------------------------------------------------ strict unbuilt account
def test_unbuilt_account_is_plain_geometric_union_area():
    green = _green()
    design_input, building_layout, road_layout, _, _ = _r1_models()
    site_inner = design_input.site_boundary.buffer(-5.0)
    obstacles = unary_union(
        [item.footprint for item in building_layout.buildings]
        + [road_layout.corridor_union, road_layout.sidewalk_union]
    )
    expected_unbuilt_area = site_inner.difference(obstacles).area
    assert green.unbuilt_area_m2 == pytest.approx(
        expected_unbuilt_area, rel=1e-12
    )
    assert green.unbuilt_area_m2 == pytest.approx(
        130788.70473514873, rel=1e-9
    )
    assert green.unbuilt_ratio == pytest.approx(
        green.unbuilt_area_m2 / _site_area(), rel=1e-12
    )
    assert green.unbuilt_ratio == pytest.approx(
        0.6407354465472117, rel=1e-9
    )
    # dual accounting: the strict geometric account is larger than the filtered
    # classified one (no 0.5 m buffer, no 100 m2 drop)
    assert green.unbuilt_area_m2 > green.candidate_open_space_area_m2
    assert green.unbuilt_ratio > green.candidate_open_space_ratio


# ------------------------------------------------------- designed green account
def test_designed_green_ratio_is_smaller_and_defined_by_designed_area():
    green = _green()
    site_area = _site_area()
    assert green.designed_green_ratio == pytest.approx(
        green.designed_green_area_m2 / site_area, rel=1e-12
    )
    assert green.designed_green_ratio == pytest.approx(
        0.06538561066069971, rel=1e-3
    )
    # the honest headline: most open space is supplementary, not designed green
    supplementary_share = (
        green.supplementary_area_m2 / green.candidate_open_space_area_m2
    )
    assert supplementary_share == pytest.approx(
        0.8939218746030837, rel=1e-3
    )
    designed_share = (
        green.designed_green_area_m2 / green.candidate_open_space_area_m2
    )
    assert designed_share == pytest.approx(0.10607812539691636, rel=1e-3)
    assert green.designed_green_ratio < green.candidate_open_space_ratio


# ------------------------------------------------------------- field contract
def _empty_green_layout() -> GreenLayout:
    return GreenLayout(
        greens=(),
        focus_greens=(),
        cluster_area_m2=0.0,
        strip_area_m2=0.0,
        supplementary_area_m2=0.0,
        candidate_open_space_area_m2=0.0,
        candidate_open_space_ratio=0.0,
        unbuilt_area_m2=0.0,
        unbuilt_ratio=0.0,
        designed_green_area_m2=0.0,
        designed_green_ratio=0.0,
        target_ratio=0.30,
        dropped_cluster_ids=(),
    )


def test_old_green_names_are_gone():
    green = _green()
    for old_name in (
        "green_ratio",
        "total_area_m2",
        "open_space_area_m2",
        "open_space_ratio",
    ):
        assert not hasattr(green, old_name), old_name
    payload = _empty_green_layout().to_dict()
    for old_name in (
        "green_ratio",
        "total_area_m2",
        "open_space_area_m2",
        "open_space_ratio",
    ):
        assert old_name not in payload, old_name
    for key in (
        "candidate_open_space_area_m2",
        "candidate_open_space_ratio",
        "unbuilt_area_m2",
        "unbuilt_ratio",
        "designed_green_area_m2",
        "designed_green_ratio",
        "open_space_filters",
    ):
        assert key in payload, key
    assert set(GreenLayout.__dataclass_fields__) == {
        "greens",
        "focus_greens",
        "cluster_area_m2",
        "strip_area_m2",
        "supplementary_area_m2",
        "candidate_open_space_area_m2",
        "candidate_open_space_ratio",
        "unbuilt_area_m2",
        "unbuilt_ratio",
        "designed_green_area_m2",
        "designed_green_ratio",
        "target_ratio",
        "dropped_cluster_ids",
        "full_site_green",
    }


def test_empty_green_layout_has_zero_ratios():
    empty = _empty_green_layout()
    assert empty.candidate_open_space_area_m2 == 0.0
    assert empty.candidate_open_space_ratio == 0.0
    assert empty.unbuilt_area_m2 == 0.0
    assert empty.unbuilt_ratio == 0.0
    assert empty.designed_green_area_m2 == 0.0
    assert empty.designed_green_ratio == 0.0


# ------------------------------------------------------------ parking semantics
def test_parking_capacity_is_assumed_nominal_not_verified():
    """Nominal assumption under ``spaces_per_entrance``, not verified capacity."""
    _, _, _, _, parking = _r1_models()
    assert parking.spaces_required == 2398
    assert parking.entrances_required == 5
    assert parking.assumed_nominal_capacity_spaces == 1000
    assert parking.assumed_nominal_capacity_spaces == sum(
        entrance.capacity_spaces for entrance in parking.entrances
    )
    # the honest gap: the nominal assumption does not cover the requirement
    assert parking.assumed_nominal_capacity_spaces < parking.spaces_required
    assert not hasattr(parking, "recorded_capacity_spaces")


def test_parking_entrance_composition_is_unchanged():
    _, _, _, _, parking = _r1_models()
    existing = [
        item for item in parking.entrances if item.status == "existing"
    ]
    proposed = [
        item for item in parking.entrances if item.status == "proposed"
    ]
    assert len(existing) == 3
    assert len(proposed) == 2
    assert all(item.capacity_spaces == 0 for item in existing)
    assert all(item.capacity_spaces == 500 for item in proposed)
    assert parking.garage_layout == "not_designed"
    assert parking.underground is True


def test_parking_to_dict_carries_assumed_nominal_capacity_and_garage_layout():
    from dgcad_design.parking import ParkingLayout

    payload = ParkingLayout(
        households=2398,
        spaces_required=2398,
        spaces_per_entrance=500,
        entrances_required=5,
        entrances=(),
        underground=True,
        garage_layout="not_designed",
        assumed_nominal_capacity_spaces=1000,
    ).to_dict()
    assert payload["assumed_nominal_capacity_spaces"] == 1000
    assert payload["garage_layout"] == "not_designed"
    assert "recorded_capacity_spaces" not in payload

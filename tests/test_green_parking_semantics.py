"""Honest green / parking semantics (M4c-1c).

The R1 design is built through the committed pipeline (same call sequence as
``tests/test_design_synthesis.py``) and the green/parking data models are
checked for the semantics split:

* ``open_space_ratio`` is open space, **not** designed green;
* ``designed_green_ratio`` covers only the designed classifications
  (cluster green + green strips), supplementary green is the remaining
  occupiable space;
* parking ``recorded_capacity_spaces`` is what the entrances can actually
  serve, which is not the same as the parking requirement.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pytest
from shapely.geometry import box

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.green import GreenLayout, build_green_layout
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
    return design_input, green, parking


def _site_area() -> float:
    design_input, _, _ = _r1_models()
    return design_input.site_area_m2


def _green() -> GreenLayout:
    _, green, _ = _r1_models()
    return green


# ------------------------------------------------------- open space semantics
def test_open_space_ratio_is_open_space_not_designed_green():
    green = _green()
    assert green.open_space_ratio == pytest.approx(
        0.6303863597090935, rel=1e-12
    )
    assert green.open_space_area_m2 == pytest.approx(
        128676.22029239938, rel=1e-9
    )
    # open space is the sum of all three classifications
    assert green.open_space_area_m2 == pytest.approx(
        green.cluster_area_m2
        + green.strip_area_m2
        + green.supplementary_area_m2,
        rel=1e-12,
    )
    # designed green is only cluster + strip
    assert green.designed_green_area_m2 == pytest.approx(
        green.cluster_area_m2 + green.strip_area_m2, rel=1e-12
    )


def test_designed_green_ratio_is_smaller_and_defined_by_designed_area():
    green = _green()
    site_area = _site_area()
    assert green.designed_green_ratio == pytest.approx(
        green.designed_green_area_m2 / site_area, rel=1e-12
    )
    assert green.designed_green_ratio == pytest.approx(
        0.06587448969490359, rel=1e-3
    )
    # the honest headline: most open space is supplementary, not designed green
    supplementary_share = (
        green.supplementary_area_m2 / green.open_space_area_m2
    )
    assert supplementary_share == pytest.approx(0.8955, rel=1e-3)
    designed_share = green.designed_green_area_m2 / green.open_space_area_m2
    assert designed_share == pytest.approx(0.1045, rel=1e-3)
    assert green.designed_green_ratio < green.open_space_ratio


def test_old_green_names_are_gone():
    green = _green()
    assert not hasattr(green, "green_ratio")
    assert not hasattr(green, "total_area_m2")
    payload = _empty_green_layout().to_dict()
    assert "green_ratio" not in payload
    assert "total_area_m2" not in payload
    for key in (
        "open_space_area_m2",
        "designed_green_area_m2",
        "open_space_ratio",
        "designed_green_ratio",
    ):
        assert key in payload
    assert set(GreenLayout.__dataclass_fields__) == {
        "greens",
        "focus_greens",
        "cluster_area_m2",
        "strip_area_m2",
        "supplementary_area_m2",
        "open_space_area_m2",
        "designed_green_area_m2",
        "open_space_ratio",
        "designed_green_ratio",
        "target_ratio",
        "dropped_cluster_ids",
    }


def _empty_green_layout() -> GreenLayout:
    return GreenLayout(
        greens=(),
        focus_greens=(),
        cluster_area_m2=0.0,
        strip_area_m2=0.0,
        supplementary_area_m2=0.0,
        open_space_area_m2=0.0,
        designed_green_area_m2=0.0,
        open_space_ratio=0.0,
        designed_green_ratio=0.0,
        target_ratio=0.30,
        dropped_cluster_ids=(),
    )


def test_empty_green_layout_has_zero_designed_ratio():
    empty = _empty_green_layout()
    assert empty.open_space_area_m2 == 0.0
    assert empty.designed_green_area_m2 == 0.0
    assert empty.open_space_ratio == 0.0
    assert empty.designed_green_ratio == 0.0


# ------------------------------------------------------------ parking semantics
def test_parking_capacity_is_recorded_not_assumed():
    _, _, parking = _r1_models()
    assert parking.spaces_required == 2398
    assert parking.entrances_required == 5
    assert parking.recorded_capacity_spaces == 1000
    assert parking.recorded_capacity_spaces == sum(
        entrance.capacity_spaces for entrance in parking.entrances
    )
    # the honest gap: recorded entrance capacity does not cover the requirement
    assert parking.recorded_capacity_spaces < parking.spaces_required


def test_parking_entrance_composition_is_unchanged():
    _, _, parking = _r1_models()
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


def test_parking_to_dict_carries_recorded_capacity_and_garage_layout():
    from dgcad_design.parking import ParkingLayout

    payload = ParkingLayout(
        households=2398,
        spaces_required=2398,
        spaces_per_entrance=500,
        entrances_required=5,
        entrances=(),
        underground=True,
        garage_layout="not_designed",
        recorded_capacity_spaces=1000,
    ).to_dict()
    assert payload["recorded_capacity_spaces"] == 1000
    assert payload["garage_layout"] == "not_designed"

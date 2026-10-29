"""Group-integrity and access-truth metrics (M4d-2-3).

The metrics are independent, geometry-derived evidence for the M4d-2 candidate
comparison. The tests build two real reference models:

* the committed served layout (focus rows placed, the other 48 buildings at
  their source positions; declared access coverage 1.0, 0 relation errors);
* the real M4d-1 full-site layout on the published 44-road corridor (declared
  access coverage 0.0, 17 relation errors - the M4d-1 baseline defect).

Forged layouts / access records prove the metrics detect a dropped building, a
duplicated building, a split group and a terminal that is not on its serving
road. Thresholds are the declared contract values and the tests assert they are
not widened.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest
from shapely.affinity import translate

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import build_road_access
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    layout_full_site,
    standardize_all,
)
from dgcad_design.group_metrics import (
    BAND_EPSILON_M,
    SCHEMA_ID,
    TERMINAL_BAND_M,
    TERMINAL_ON_ROAD_TOLERANCE_M,
    access_truth_metrics,
    candidate_comparison_metrics,
    group_integrity_metrics,
    terminal_band_ok,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


@lru_cache(maxsize=1)
def _models() -> dict:
    """The committed served reference: access coverage 1.0, 0 relation errors."""

    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standardized = standardize_all(design_input, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    road_layout = build_road_layout(
        design_input, basis, intent, building_layout
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    road_access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=design_input.site_boundary,
    )
    return {
        "basis": basis,
        "design_input": design_input,
        "intent": intent,
        "standardized": standardized,
        "building_layout": building_layout,
        "road_layout": road_layout,
        "parking_layout": parking_layout,
        "road_access": road_access,
        "site_boundary": design_input.site_boundary,
    }


@lru_cache(maxsize=1)
def _full_site_models() -> dict:
    """The real M4d-1 full-site layout on the published corridor (0/17 access)."""

    models = _models()
    basis = models["basis"]
    design_input = models["design_input"]
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    building_layout = layout_full_site(
        design_input,
        basis,
        models["intent"],
        models["standardized"],
        site_inner,
        road_corridor=models["road_layout"].corridor_union,
    )
    road_access = build_road_access(
        building_layout,
        models["road_layout"],
        models["intent"],
        models["parking_layout"],
        basis,
        site_boundary=design_input.site_boundary,
    )
    return {
        **models,
        "building_layout": building_layout,
        "road_access": road_access,
    }


def _group(layout, group_id: str):
    return next(
        group
        for group in _models()["intent"].groups
        if group.group_id == group_id
    )


def _forged_layout(dropped_id: str | None = None, duplicate: bool = False):
    layout = _models()["building_layout"]
    buildings = list(layout.buildings)
    if dropped_id is not None:
        buildings = [
            item for item in buildings if item.building_id != dropped_id
        ]
    if duplicate:
        buildings = buildings + [buildings[0]]
    return replace(layout, buildings=tuple(buildings))


# ------------------------------------------------------- group integrity
def test_group_integrity_keeps_all_17_groups_in_the_served_layout():
    models = _models()
    integrity = group_integrity_metrics(
        models["intent"], models["building_layout"], models["road_access"]
    )
    assert integrity["schema_id"] == SCHEMA_ID
    assert integrity["group_count"] == 17
    assert integrity["groups_preserved"] == 17
    assert integrity["groups_with_missing_buildings"] == 0
    assert integrity["groups_with_duplicate_buildings"] == 0
    assert integrity["missing_building_count"] == 0
    assert integrity["duplicate_building_count"] == 0
    assert integrity["unexpected_building_ids"] == []
    assert integrity["groups_split"] == 0
    assert integrity["access_served_count"] == 17
    assert integrity["access_relation_error_count"] == 0
    # the served layout only row-places the focus rows; the two dropped focus
    # buildings and the other groups are still at source positions, so no group
    # has a complete row assignment (honest: row cohesion is not verifiable)
    assert integrity["groups_row_unverified"] == 17
    focus_record = next(
        record
        for record in integrity["groups"]
        if record["group_id"] == models["intent"].focus_group_id
    )
    assert focus_record["row_cohesion"] == "no_row_assignment"
    assert focus_record["split"] is None
    # a non-focus group has zero centroid displacement (source positions)
    other_record = next(
        record
        for record in integrity["groups"]
        if record["group_id"] != models["intent"].focus_group_id
    )
    assert other_record["centroid_displacement_m"] == pytest.approx(
        0.0, abs=1e-9
    )
    assert other_record["relative_position"]["max_distance_change_m"] == (
        pytest.approx(0.0, abs=1e-9)
    )


def test_group_integrity_detects_a_dropped_building():
    models = _models()
    group = _group(models["building_layout"], models["intent"].focus_group_id)
    dropped_id = group.building_ids[0]
    forged = _forged_layout(dropped_id=dropped_id)
    integrity = group_integrity_metrics(
        models["intent"], forged, models["road_access"]
    )
    assert integrity["groups_preserved"] == 16
    assert integrity["missing_building_count"] == 1
    assert integrity["groups_with_missing_buildings"] == 1
    record = next(
        item
        for item in integrity["groups"]
        if item["group_id"] == models["intent"].focus_group_id
    )
    assert record["missing_building_ids"] == [dropped_id]
    assert record["preserved"] is False


def test_group_integrity_detects_a_duplicated_building():
    models = _models()
    forged = _forged_layout(duplicate=True)
    integrity = group_integrity_metrics(
        models["intent"], forged, models["road_access"]
    )
    assert integrity["duplicate_building_count"] == 1
    assert integrity["groups_with_duplicate_buildings"] == 1
    assert integrity["groups_preserved"] == 16
    duplicated_id = models["building_layout"].buildings[0].building_id
    record = next(
        item
        for item in integrity["groups"]
        if duplicated_id in item["duplicate_building_ids"]
    )
    assert record["preserved"] is False


def test_group_integrity_detects_a_split_group():
    models = _full_site_models()
    layout = models["building_layout"]
    focus_id = models["intent"].focus_group_id
    focus_buildings = [
        item
        for item in layout.buildings
        if item.building_id in _group(layout, focus_id).building_ids
    ]
    assert all(item.row_index is not None for item in focus_buildings)
    max_row = max(item.row_index for item in focus_buildings)
    moved = focus_buildings[0]
    moved_building = replace(
        moved,
        row_index=max_row + 3,
        footprint=translate(moved.footprint, yoff=100.0),
        design_centroid=(
            moved.design_centroid[0],
            moved.design_centroid[1] + 100.0,
        ),
        label_anchor=(
            moved.label_anchor[0],
            moved.label_anchor[1] + 100.0,
        ),
    )
    buildings = tuple(
        moved_building if item.building_id == moved.building_id else item
        for item in layout.buildings
    )
    forged = replace(layout, buildings=buildings)
    integrity = group_integrity_metrics(
        models["intent"], forged, models["road_access"]
    )
    assert integrity["groups_split"] >= 1
    record = next(
        item for item in integrity["groups"] if item["group_id"] == focus_id
    )
    assert record["split"] is True
    assert record["row_cohesion"] == "non_contiguous_rows"
    assert record["row_runs"] >= 2


# ---------------------------------------------------------- access truth
def test_access_truth_served_layout_is_geometry_verified():
    models = _models()
    truth = access_truth_metrics(
        models["road_layout"],
        models["road_access"],
        models["site_boundary"],
        models["building_layout"],
    )
    assert truth["groups_total"] == 17
    assert truth["groups_served"] == 17
    assert truth["coverage"] == pytest.approx(1.0)
    assert truth["groups_geometry_verified_served"] == 17
    assert truth["geometry_verified_coverage"] == pytest.approx(1.0)
    assert truth["relation_error_count"] == 0
    assert truth["terminal_band_violation_group_ids"] == []
    assert truth["terminal_on_serving_road_violation_group_ids"] == []
    assert truth["field_geometry_disagreement_group_ids"] == []
    assert truth["terminal_band_required_m"] == list(TERMINAL_BAND_M)
    assert truth["terminal_band_min_m"] >= TERMINAL_BAND_M[0] - BAND_EPSILON_M
    assert truth["terminal_band_max_m"] <= TERMINAL_BAND_M[1] + BAND_EPSILON_M
    assert truth["dead_ends"]["unresolved"] == 0
    assert all(
        record["terminal_band_source"] == "geometry"
        for record in truth["groups"]
    )


def test_access_truth_reports_the_real_full_site_baseline_zero_coverage():
    models = _full_site_models()
    truth = access_truth_metrics(
        models["road_layout"],
        models["road_access"],
        models["site_boundary"],
        models["building_layout"],
    )
    assert truth["groups_total"] == 17
    assert truth["groups_served"] == 0
    assert truth["coverage"] == 0.0
    assert truth["groups_geometry_verified_served"] == 0
    assert truth["relation_error_count"] == 17
    assert len(truth["terminal_band_violation_group_ids"]) == 17
    assert truth["terminal_band_min_m"] is not None
    assert not any(record["terminal_band_ok"] for record in truth["groups"])
    # the generator flag and the geometry agree that nothing is served
    assert truth["field_geometry_disagreement_group_ids"] == []
    # group ids are still complete even though access is not
    integrity = group_integrity_metrics(
        models["intent"],
        models["building_layout"],
        models["road_access"],
    )
    assert integrity["groups_preserved"] == 17
    assert integrity["missing_building_count"] == 0


def test_access_truth_detects_a_terminal_not_on_its_serving_road():
    models = _models()
    target = next(
        group
        for group in models["road_access"].groups
        if group.served_by_relation and group.terminal_xy is not None
    )
    forged_groups = tuple(
        replace(
            group,
            terminal_xy=(group.terminal_xy[0] + 5.0, group.terminal_xy[1]),
        )
        if group.group_id == target.group_id
        else group
        for group in models["road_access"].groups
    )
    forged_access = replace(models["road_access"], groups=forged_groups)
    truth = access_truth_metrics(
        models["road_layout"],
        forged_access,
        models["site_boundary"],
        models["building_layout"],
    )
    assert target.group_id in truth["terminal_on_serving_road_violation_group_ids"]
    assert truth["groups_geometry_verified_served"] == 16
    assert target.group_id in truth["field_geometry_disagreement_group_ids"]
    record = next(
        item
        for item in truth["groups"]
        if item["group_id"] == target.group_id
    )
    assert record["terminal_on_serving_road"] is False
    assert record["geometry_verified_served"] is False
    assert "terminal_not_on_serving_road" in record["geometry_reasons"]


# ------------------------------------------------------- threshold honesty
def test_terminal_band_thresholds_are_declared_and_not_widened():
    assert TERMINAL_BAND_M == (3.4, 3.5)
    assert BAND_EPSILON_M == 1e-9
    assert TERMINAL_ON_ROAD_TOLERANCE_M == 1e-6
    assert terminal_band_ok(None) is None
    assert terminal_band_ok(3.39) is False
    assert terminal_band_ok(3.4) is True
    assert terminal_band_ok(3.5) is True
    assert terminal_band_ok(3.51) is False
    # only float noise is tolerated, never a widened band
    assert terminal_band_ok(3.4 - 1e-10) is True
    assert terminal_band_ok(3.4 - 2e-9) is False
    assert terminal_band_ok(3.5 + 1e-10) is True
    assert terminal_band_ok(3.5 + 2e-9) is False


# ------------------------------------------------- candidate comparison
def test_candidate_comparison_is_an_objective_table_without_ranking():
    served = _models()
    baseline = _full_site_models()
    group = _group(served["building_layout"], served["intent"].focus_group_id)
    dropped = _forged_layout(dropped_id=group.building_ids[0])
    target = next(
        access
        for access in served["road_access"].groups
        if access.served_by_relation and access.terminal_xy is not None
    )
    forged_groups = tuple(
        replace(
            access,
            terminal_xy=(access.terminal_xy[0] + 5.0, access.terminal_xy[1]),
        )
        if access.group_id == target.group_id
        else access
        for access in served["road_access"].groups
    )
    forged = {
        **served,
        "building_layout": dropped,
        "road_access": replace(
            served["road_access"], groups=forged_groups
        ),
    }
    comparison = candidate_comparison_metrics(served, forged, baseline)
    assert comparison["schema_id"] == SCHEMA_ID
    assert comparison["comparison_kind"] == (
        "objective_metric_table_no_score_no_ranking"
    )
    assert comparison["ranking"] is None
    assert comparison["scoring"] is None
    assert "no score" in comparison["note"]
    table = {
        row["metric"]: row for row in comparison["comparison_table"]
    }
    assert table["groups_preserved"]["A"] == 17
    assert table["groups_preserved"]["B"] == 16
    assert table["groups_preserved"]["baseline"] == 17
    assert table["coverage"]["A"] == pytest.approx(1.0)
    assert table["coverage"]["baseline"] == 0.0
    assert table["field_geometry_disagreement_count"]["B"] == 1
    deltas = comparison["deltas"]
    assert deltas["A_minus_baseline"]["coverage"] == pytest.approx(1.0)
    assert deltas["A_minus_baseline"]["groups_preserved"] == 0.0
    assert deltas["B_minus_baseline"]["groups_preserved"] == -1.0
    assert len(comparison["per_group_table"]) == 17
    row = next(
        item
        for item in comparison["per_group_table"]
        if item["group_id"] == served["intent"].focus_group_id
    )
    assert set(row) == {"group_id", "A", "B", "baseline"}
    assert row["A"]["preserved"] is True
    assert row["B"]["preserved"] is False


def test_candidate_comparison_rejects_incomplete_models():
    models = _models()
    with pytest.raises(ValueError, match="missing required keys"):
        candidate_comparison_metrics({}, models, models)


def test_candidate_comparison_same_model_has_zero_deltas():
    models = _models()
    comparison = candidate_comparison_metrics(models, models, models)
    for delta in comparison["deltas"].values():
        assert all(
            value is None or value == pytest.approx(0.0)
            for value in delta.values()
        )
    assert comparison["ranking"] is None

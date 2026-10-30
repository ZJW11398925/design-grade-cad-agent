"""Inferred-group provenance and group-quality metrics (M4d-2a-1).

The 17 groups are inferred by ``intent.py`` (45 m centroid radius + 8 m
main-road buffer + Union-Find single linkage), not designer-confirmed. These
tests bind the provenance record and the descriptive quality metrics to the
real baseline / candidate A / candidate B building layouts:

* baseline and candidate A share the M4d-1 full-site building layout (candidate
  A only rebuilds access), so their group-quality metrics are identical;
* candidate B uses ``layout_group_preserving`` (17 groups on local row
  lattices, 39 rows).

The metrics are descriptive: the tests assert there is no score, ranking or
pass/fail gate, and that thresholds are not invented (the only distance reused
is the declared 45 m inference radius, used to describe isolated members).
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest
from shapely.affinity import translate

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    layout_full_site,
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.intent import BuildingGroup
from dgcad_design.intent_metrics import (
    DEFAULT_GROUP_DISTANCE_M,
    MAIN_ROAD_GROUP_BUFFER_M,
    SCHEMA_ID,
    compare_group_quality,
    group_quality_metrics,
    inferred_group_provenance,
)
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


@lru_cache(maxsize=1)
def _context() -> dict:
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standardized = standardize_all(design_input, basis)
    focus_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    road_layout = build_road_layout(
        design_input, basis, intent, focus_layout
    )
    a_layout = layout_full_site(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=road_layout.corridor_union,
    )
    b_layout = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=road_layout.corridor_union,
    )
    return {
        "basis": basis,
        "design_input": design_input,
        "intent": intent,
        "focus_layout": focus_layout,
        "a_layout": a_layout,
        "b_layout": b_layout,
    }


def _models() -> dict[str, dict]:
    context = _context()
    intent = context["intent"]
    # baseline and candidate A share the M4d-1 full-site building layout
    return {
        "baseline": {
            "intent": intent,
            "building_layout": context["a_layout"],
        },
        "a": {
            "intent": intent,
            "building_layout": context["a_layout"],
        },
        "b": {
            "intent": intent,
            "building_layout": context["b_layout"],
        },
    }


# --------------------------------------------------------------- provenance
def test_inferred_group_provenance_declares_the_inference_method():
    context = _context()
    provenance = inferred_group_provenance(
        context["intent"], context["basis"], context["focus_layout"]
    )
    assert provenance["schema_id"] == SCHEMA_ID
    assert provenance["groups_are_inferred"] is True
    assert provenance["designer_confirmed"] is False
    assert provenance["method"] == "single_linkage_union_find"
    assert provenance["group_distance_m"] == (
        context["basis"].group_distance_m
    ) == DEFAULT_GROUP_DISTANCE_M == 45.0
    assert provenance["main_road_buffer_m"] == (
        MAIN_ROAD_GROUP_BUFFER_M
    ) == 8.0
    assert provenance["transitive"] is True
    # cross-check the provenance declared on the intent object, if present
    declared = provenance["intent_declared_provenance"]
    if declared:
        assert provenance["matches_intent_declaration"] is True
        assert declared["kind"] == "inferred_groups"
        assert declared["not_designer_confirmed"] is True
    assert provenance["group_count"] == 17
    assert "Union-Find" in provenance["pair_rule"]
    assert "single linkage" in provenance["chaining_note"]
    building_ids = [
        building_id
        for group in provenance["groups"]
        for building_id in group["building_ids"]
    ]
    assert len(building_ids) == 55
    assert len(set(building_ids)) == 55
    for group in provenance["groups"]:
        for field in (
            "group_id",
            "building_ids",
            "unit_count",
            "households",
            "bbox",
            "centroid",
            "main_road_distance_m",
            "max_pairwise_source_distance_m",
            "chain_ratio_to_group_distance",
        ):
            assert field in group
    # single-linkage transitivity chains a group far beyond the 45 m radius
    max_chained = max(
        group["max_pairwise_source_distance_m"]
        for group in provenance["groups"]
    )
    assert max_chained > DEFAULT_GROUP_DISTANCE_M
    assert max_chained == pytest.approx(209.73801637008503, abs=1e-6)


def test_inferred_group_provenance_focus_group_9_inferred_vs_7_placed():
    context = _context()
    provenance = inferred_group_provenance(
        context["intent"], context["basis"], context["focus_layout"]
    )
    focus = provenance["focus_group"]
    assert focus["group_id"] == context["intent"].focus_group_id == "G-01"
    assert focus["inferred_building_count"] == 9
    assert focus["focus_layout_building_count"] == 7
    assert len(focus["focus_layout_building_ids"]) == 7
    assert focus["dropped_from_focus_layout"] == [
        "SK-BLD-0038",
        "SK-BLD-0061",
    ]


def test_inferred_group_provenance_without_layout_claims_no_placement():
    context = _context()
    provenance = inferred_group_provenance(
        context["intent"], context["basis"]
    )
    focus = provenance["focus_group"]
    assert focus["inferred_building_count"] == 9
    assert focus["focus_layout_building_ids"] is None
    assert focus["focus_layout_building_count"] is None
    assert focus["dropped_from_focus_layout"] is None


# ---------------------------------------------------------- group quality
def test_group_quality_baseline_real_readings():
    context = _context()
    metrics = group_quality_metrics(
        context["intent"], context["a_layout"]
    )
    assert metrics["schema_id"] == SCHEMA_ID
    assert metrics["group_count"] == 17
    assert metrics["building_count"] == 55
    cohesion = metrics["cohesion"]
    assert cohesion["mean_pairwise_distance_m"] == pytest.approx(
        88.0087266508199, abs=1e-6
    )
    assert cohesion["p90_pairwise_distance_m"] == pytest.approx(
        156.11857355343471, abs=1e-6
    )
    assert cohesion["max_span_m"] == pytest.approx(
        271.8415026925421, abs=1e-6
    )
    assert cohesion["isolated_member_count"] == 14
    fragmentation = metrics["fragmentation"]
    assert fragmentation["groups_non_contiguous"] == 10
    assert fragmentation["groups_with_row_runs_gt1"] == 10
    assert fragmentation["total_row_runs"] == 29
    assert fragmentation["groups_row_unverified"] == 0
    assert fragmentation["max_row_gap"] == 5
    relative = metrics["relative_position"]
    assert relative["distance_change_mean_m"] == pytest.approx(
        34.30609544001679, abs=1e-6
    )
    assert relative["distance_change_max_m"] == pytest.approx(
        191.84099134152473, abs=1e-6
    )
    assert relative["distance_change_p90_m"] == pytest.approx(
        85.90783434160322, abs=1e-6
    )
    assert relative["orientation_change_mean_deg"] == pytest.approx(
        27.048543289135743, abs=1e-6
    )
    assert relative["nearest_neighbor_preservation_rate"] == pytest.approx(
        0.6, abs=1e-9
    )
    shape = metrics["shape_distortion"]
    assert shape["bbox_area_ratio_mean"] == pytest.approx(
        2.526080976800568, abs=1e-6
    )
    assert shape["bbox_area_ratio_max"] == pytest.approx(
        10.803349866524815, abs=1e-6
    )
    assert shape["group_centroid_displacement_mean_m"] == pytest.approx(
        37.00276024188745, abs=1e-6
    )
    assert shape["group_centroid_displacement_max_m"] == pytest.approx(
        110.73498252036941, abs=1e-6
    )
    displacement = metrics["displacement"]
    assert displacement["count"] == 55
    assert displacement["mean_m"] == pytest.approx(
        42.34448247926142, abs=1e-6
    )
    assert displacement["max_m"] == pytest.approx(
        147.25157520912134, abs=1e-6
    )
    assert displacement["p90_m"] == pytest.approx(
        108.35090244973908, abs=1e-6
    )
    assert displacement["median_m"] == pytest.approx(
        14.811285480651918, abs=1e-6
    )


def test_group_quality_candidate_b_real_readings():
    context = _context()
    metrics = group_quality_metrics(
        context["intent"], context["b_layout"]
    )
    assert metrics["group_count"] == 17
    assert metrics["building_count"] == 55
    cohesion = metrics["cohesion"]
    assert cohesion["mean_pairwise_distance_m"] == pytest.approx(
        83.58729138347255, abs=1e-6
    )
    assert cohesion["p90_pairwise_distance_m"] == pytest.approx(
        129.11489364334008, abs=1e-6
    )
    assert cohesion["max_span_m"] == pytest.approx(
        294.5004295872598, abs=1e-6
    )
    assert cohesion["isolated_member_count"] == 16
    fragmentation = metrics["fragmentation"]
    assert fragmentation["groups_non_contiguous"] == 12
    assert fragmentation["total_row_runs"] == 43
    assert fragmentation["max_row_gap"] == 12
    relative = metrics["relative_position"]
    assert relative["distance_change_mean_m"] == pytest.approx(
        35.144093402467206, abs=1e-6
    )
    assert relative["distance_change_max_m"] == pytest.approx(
        258.76509721607476, abs=1e-6
    )
    assert relative["distance_change_p90_m"] == pytest.approx(
        67.79632462885765, abs=1e-6
    )
    assert relative["nearest_neighbor_preservation_rate"] == pytest.approx(
        0.66, abs=1e-9
    )
    shape = metrics["shape_distortion"]
    assert shape["group_centroid_displacement_mean_m"] == pytest.approx(
        33.99167167875439, abs=1e-6
    )
    assert shape["group_centroid_displacement_max_m"] == pytest.approx(
        140.1229138140712, abs=1e-6
    )
    displacement = metrics["displacement"]
    assert displacement["mean_m"] == pytest.approx(
        47.920354757238925, abs=1e-6
    )
    assert displacement["max_m"] == pytest.approx(
        278.4615666910247, abs=1e-6
    )
    assert displacement["p90_m"] == pytest.approx(
        102.82590494042707, abs=1e-6
    )


def test_group_quality_detects_a_dropped_member():
    context = _context()
    intent = context["intent"]
    layout = context["a_layout"]
    group = next(
        item
        for item in intent.groups
        if item.group_id == intent.focus_group_id
    )
    dropped_id = group.building_ids[0]
    forged = replace(
        layout,
        buildings=tuple(
            item
            for item in layout.buildings
            if item.building_id != dropped_id
        ),
    )
    metrics = group_quality_metrics(intent, forged)
    record = next(
        item
        for item in metrics["groups"]
        if item["group_id"] == group.group_id
    )
    assert dropped_id in record["missing_member_ids"]
    assert len(record["present_member_ids"]) == len(group.building_ids) - 1
    expected_pairs = (
        (len(group.building_ids) - 1) * (len(group.building_ids) - 2) // 2
    )
    assert record["cohesion"]["pair_count"] == expected_pairs
    provenance = inferred_group_provenance(
        intent, context["basis"], forged
    )
    provenance_record = next(
        item
        for item in provenance["groups"]
        if item["group_id"] == group.group_id
    )
    assert dropped_id in provenance_record["missing_building_ids"]


def test_group_quality_detects_a_split_group():
    context = _context()
    intent = context["intent"]
    layout = context["b_layout"]
    group = next(
        item
        for item in intent.groups
        if len(item.building_ids) >= 2
    )
    members = [
        item
        for item in layout.buildings
        if item.building_id in group.building_ids
    ]
    assert members and all(item.row_index is not None for item in members)
    max_row = max(item.row_index for item in members)
    moved = members[0]
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
    forged = replace(
        layout,
        buildings=tuple(
            moved_building
            if item.building_id == moved.building_id
            else item
            for item in layout.buildings
        ),
    )
    metrics = group_quality_metrics(intent, forged)
    record = next(
        item
        for item in metrics["groups"]
        if item["group_id"] == group.group_id
    )
    assert record["fragmentation"]["non_contiguous"] is True
    assert record["fragmentation"]["row_runs"] >= 2
    assert metrics["fragmentation"]["groups_non_contiguous"] >= 1


def test_group_quality_detects_a_rigid_large_displacement():
    context = _context()
    intent = context["intent"]
    layout = context["a_layout"]

    def shifted(item):
        target = (
            item.source_centroid[0],
            item.source_centroid[1] + 100.0,
        )
        dx = target[0] - item.design_centroid[0]
        dy = target[1] - item.design_centroid[1]
        return replace(
            item,
            footprint=translate(item.footprint, xoff=dx, yoff=dy),
            design_centroid=target,
            label_anchor=(
                item.label_anchor[0] + dx,
                item.label_anchor[1] + dy,
            ),
        )

    shifted_layout = replace(
        layout,
        buildings=tuple(shifted(item) for item in layout.buildings),
    )
    metrics = group_quality_metrics(intent, shifted_layout)
    displacement = metrics["displacement"]
    assert displacement["mean_m"] == pytest.approx(100.0, abs=1e-9)
    assert displacement["max_m"] == pytest.approx(100.0, abs=1e-9)
    assert displacement["median_m"] == pytest.approx(100.0, abs=1e-9)
    # a rigid translation preserves every relative position and orientation
    relative = metrics["relative_position"]
    assert relative["distance_change_max_m"] == pytest.approx(0.0, abs=1e-9)
    # acos near 1 leaves float noise in the reported angle; it is not a
    # displacement and no gate uses it
    assert relative["orientation_change_max_deg"] == pytest.approx(
        0.0, abs=1e-5
    )
    assert relative["nearest_neighbor_preservation_rate"] == pytest.approx(
        1.0, abs=1e-12
    )
    assert metrics["shape_distortion"][
        "group_centroid_displacement_mean_m"
    ] == pytest.approx(100.0, abs=1e-9)


def test_group_quality_handles_a_single_member_group():
    context = _context()
    intent = context["intent"]
    layout = context["a_layout"]
    member = layout.buildings[0]
    group = BuildingGroup(
        group_id="G-SYN",
        building_ids=(member.building_id,),
        unit_count=member.unit_count,
        households=member.households,
        centroid=member.source_centroid,
        bbox=member.footprint.bounds,
        green_ids=(),
        main_road_distance_m=None,
    )
    synthetic_intent = replace(
        intent,
        groups=(group,),
        focus_group_id="G-SYN",
        focus_building_ids=(member.building_id,),
        focus_green_ids=(),
        focus_road_ids=(),
        focus_subgroups={},
    )
    synthetic_layout = replace(
        layout, buildings=(member,), focus_buildings=()
    )
    metrics = group_quality_metrics(synthetic_intent, synthetic_layout)
    record = metrics["groups"][0]
    assert record["cohesion"]["pair_count"] == 0
    assert record["cohesion"]["mean_pairwise_distance_m"] is None
    assert record["cohesion"]["max_span_m"] is None
    assert record["relative_position"]["pair_count"] == 0
    assert (
        record["relative_position"]["nearest_neighbor_preservation_rate"]
        is None
    )
    assert record["displacement"]["count"] == 1
    assert record["displacement"]["mean_m"] == pytest.approx(
        record["displacement"]["max_m"], abs=1e-12
    )
    assert metrics["relative_position"][
        "nearest_neighbor_preservation_rate"
    ] is None


def test_isolation_uses_the_declared_inference_radius_only():
    context = _context()
    intent = context["intent"]
    layout = context["a_layout"]
    group = next(
        item
        for item in intent.groups
        if len(item.building_ids) >= 2
    )
    members = [
        item
        for item in layout.buildings
        if item.building_id in group.building_ids
    ]
    moved = members[0]
    moved_building = replace(
        moved,
        footprint=translate(moved.footprint, yoff=200.0),
        design_centroid=(
            moved.design_centroid[0],
            moved.design_centroid[1] + 200.0,
        ),
        label_anchor=(
            moved.label_anchor[0],
            moved.label_anchor[1] + 200.0,
        ),
    )
    forged = replace(
        layout,
        buildings=tuple(
            moved_building
            if item.building_id == moved.building_id
            else item
            for item in layout.buildings
        ),
    )
    metrics = group_quality_metrics(intent, forged)
    record = next(
        item
        for item in metrics["groups"]
        if item["group_id"] == group.group_id
    )
    # the moved member's nearest neighbour is now far beyond the declared 45 m
    # inference radius: the description is "isolated", it is not a gate
    assert record["cohesion"]["isolated_member_count"] >= 1
    assert DEFAULT_GROUP_DISTANCE_M == 45.0


def test_group_quality_has_no_score_ranking_or_gate_fields():
    context = _context()
    metrics = group_quality_metrics(
        context["intent"], context["a_layout"]
    )
    for forbidden in (
        "status",
        "verdict",
        "pass",
        "fail",
        "score",
        "ranking",
        "scoring",
        "pass_fail_gate",
    ):
        assert forbidden not in metrics


# ------------------------------------------------------------ comparison
def test_compare_group_quality_is_descriptive_without_ranking():
    models = _models()
    comparison = compare_group_quality(
        models["baseline"], models["a"], models["b"]
    )
    assert comparison["schema_id"] == SCHEMA_ID
    assert comparison["comparison_kind"] == (
        "descriptive_group_quality_table_no_score_no_ranking"
    )
    assert comparison["groups_are_inferred"] is True
    assert comparison["ranking"] is None
    assert comparison["scoring"] is None
    assert comparison["pass_fail_gate"] is None
    assert "no pass/fail gate" in comparison["note"]
    assert len(comparison["comparison_table"]) == 23
    assert set(comparison["candidates"]) == {"baseline", "A", "B"}


def test_compare_group_quality_a_equals_baseline_and_b_deltas():
    models = _models()
    comparison = compare_group_quality(
        models["baseline"], models["a"], models["b"]
    )
    table = {
        row["metric"]: row for row in comparison["comparison_table"]
    }
    # candidate A only rebuilds access; its building layout is the baseline
    for row in comparison["comparison_table"]:
        a_value = row["A"]
        baseline_value = row["baseline"]
        if a_value is None or baseline_value is None:
            assert a_value is None and baseline_value is None
        else:
            assert a_value == pytest.approx(baseline_value, abs=1e-12)
    deltas = comparison["deltas"]
    assert deltas["A_minus_baseline"]["displacement.mean_m"] == (
        pytest.approx(0.0, abs=1e-12)
    )
    assert deltas["B_minus_baseline"]["displacement.mean_m"] == (
        pytest.approx(47.920354757238925 - 42.34448247926142, abs=1e-6)
    )
    assert deltas["B_minus_baseline"]["displacement.max_m"] > 0.0
    assert deltas["B_minus_baseline"]["fragmentation.groups_non_contiguous"] == 2.0
    assert table["cohesion.mean_pairwise_distance_m"]["B"] < (
        table["cohesion.mean_pairwise_distance_m"]["baseline"]
    )
    per_group = comparison["per_group_table"]
    assert len(per_group) == 17
    focus_row = next(
        row for row in per_group if row["group_id"] == "G-01"
    )
    assert set(focus_row) == {"group_id", "baseline", "A", "B"}
    assert "cohesion.max_span_m" in focus_row["A"]
    assert "fragmentation.non_contiguous" in focus_row["A"]


def test_compare_group_quality_rejects_incomplete_models():
    models = _models()
    with pytest.raises(ValueError, match="intent.*building_layout"):
        compare_group_quality({}, models["a"], models["b"])

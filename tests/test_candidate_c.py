"""M4d-2b candidate C tests: bounded generate-and-test co-design.

The candidate is explicitly a *bounded* search over 20 declared variants, not a
joint optimiser; these tests assert the honest mechanics (deterministic plan,
hard-first selection, measured comparison against candidate B, honest failure
when nothing passes) and the reference-case result.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString

from dgcad_design.co_design import (
    BOUNDED_SEARCH_NOTE,
    HARD_CHECK_IDS,
    accept_local_repair,
    added_road_length,
    build_candidate_c,
    candidate_signature,
    load_candidate_context,
    local_repair_plan,
    run_candidate_variant,
    select_candidate_c,
    variant_plan,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"

#: Bounded subset used by the integration tests (the full plan is 20 variants;
#: the default covers candidate B; one hard-failing and one detail-perturbed
#: variant exercise the table/selection logic without a multi-minute build).
SUBSET = ("default", "focus_first_y_asc", "x_asc", "y_asc_swap01")


@lru_cache(maxsize=1)
def _context():
    return load_candidate_context(CASE, BASIS)


@lru_cache(maxsize=1)
def _candidate_c():
    return build_candidate_c(
        CASE,
        BASIS,
        variant_names=SUBSET,
        context=_context(),
        max_repair_candidates=3,
        max_repair_steps=2,
    )


def test_variant_plan_is_deterministic_with_declared_bounded_set():
    context = _context()
    intent = context["intent"]
    plan = variant_plan(intent)
    assert 12 <= len(plan) <= 20
    assert len({entry["variant"] for entry in plan}) == len(plan)
    assert plan == variant_plan(intent)
    names = [entry["variant"] for entry in plan]
    for required in (
        "default",
        "y_asc",
        "y_desc",
        "focus_first_y_asc",
        "focus_last_y_asc",
        "focus_first_y_desc",
        "focus_last_y_desc",
    ):
        assert required in names
    assert plan[0]["variant"] == "default"
    assert plan[0]["order"] is None
    for entry in plan[1:]:
        order = entry["order"]
        assert order is not None
        assert sorted(order) == sorted(
            set(entry["order"])
        )
        assert len(order) == len(intent.groups)


def test_selection_is_hard_first_then_lexicographic():
    def record(name, *, hard, noncontig, disp, cd, road, signature=None):
        return {
            "variant": name,
            "hard_ok": hard,
            "failed_hard_checks": [] if hard else ["FULL_SITE_NS_SPACING"],
            "groups_non_contiguous": noncontig,
            "total_row_runs": noncontig + 1,
            "displacement_max_m": disp,
            "displacement_mean_m": disp / 2.0,
            "group_centroid_displacement_max_m": cd,
            "group_centroid_displacement_mean_m": cd / 2.0,
            "added_road_length_m": road,
            "signature": signature or f"sig-{name}",
            "sidewalk_overlap_count": 0,
            "sidewalk_overlap_building_ids": [],
            "access_coverage": 1.0,
            "relation_error_count": 0,
            "dead_ends_unresolved": 0,
            "checks_total": 29,
        }

    records = [
        # a hard failure with attractive metrics must never win
        record("bad", hard=False, noncontig=0, disp=10.0, cd=5.0, road=10.0),
        record("good_b", hard=True, noncontig=12, disp=278.0, cd=140.0, road=190.0),
        record("good_c", hard=True, noncontig=11, disp=300.0, cd=150.0, road=200.0),
        record("good_d", hard=True, noncontig=12, disp=250.0, cd=140.0, road=180.0),
    ]
    selection = select_candidate_c(records, b_signature="sig-good_b")
    assert selection["decision"] == "hard_valid_candidate"
    assert selection["hard_valid"] is True
    # fewest non-contiguous groups first, then displacement max
    assert selection["selected_variant"] == "good_c"
    assert selection["same_as_b"] is False

    same = select_candidate_c(records, b_signature="sig-good_c")
    assert same["decision"] == "no_improvement_same_as_b"
    assert same["same_as_b"] is True

    all_fail = select_candidate_c(
        [record("f1", hard=False, noncontig=1, disp=5, cd=5, road=5)]
    )
    assert all_fail["decision"] == "no_hard_valid_variant"
    assert all_fail["hard_valid"] is False
    assert all_fail["selected_variant"] is None
    assert all_fail["selected_record"] is not None
    assert all_fail["failures"]["f1"] == ["FULL_SITE_NS_SPACING"]


def test_helpers_measure_added_roads_and_layout_signature():
    frozen = SimpleNamespace(
        roads=[
            SimpleNamespace(
                edge_id="MAIN-01", centerline=LineString([(0, 0), (10, 0)])
            )
        ]
    )
    current = SimpleNamespace(
        roads=[
            SimpleNamespace(
                edge_id="MAIN-01", centerline=LineString([(0, 0), (10, 0)])
            ),
            SimpleNamespace(
                edge_id="CD-R-001", centerline=LineString([(0, 0), (3, 4)])
            ),
        ]
    )
    assert added_road_length(current, frozen) == pytest.approx(5.0)
    layout = SimpleNamespace(
        buildings=[
            SimpleNamespace(
                building_id="B1", design_centroid=(1.0, 2.0), row_index=1
            ),
            SimpleNamespace(
                building_id="B2", design_centroid=(3.0, 4.0), row_index=2
            ),
        ]
    )
    first = candidate_signature(layout)
    assert first == candidate_signature(layout)
    layout.buildings[0].design_centroid = (1.5, 2.0)
    assert candidate_signature(layout) != first


def test_candidate_c_variant_table_and_hard_status():
    result = _candidate_c()
    assert result["schema_id"] == "dgcad.candidate-c.v0.1"
    assert result["candidate_id"] == "C"
    assert result["method"] == BOUNDED_SEARCH_NOTE
    assert "bounded generate-and-test" in result["method"]
    assert result["variant_count"] == len(SUBSET)
    assert [row["variant"] for row in result["variant_table"]] == list(SUBSET)
    # plan always declares the full bounded set even when a subset is evaluated
    assert len(result["variant_plan"]) >= 12
    for row in result["variant_table"]:
        assert row["order"] is None or list(row["order"])
        if "error" in row:
            assert row["hard_ok"] is False
            continue
        assert row["checks_total"] == 29
        assert row["hard_ok"] is (
            not row["failed_hard_checks"]
            and not row["sidewalk_overlap_building_ids"]
        )
        for field in (
            "groups_non_contiguous",
            "displacement_max_m",
            "group_centroid_displacement_max_m",
            "added_road_length_m",
        ):
            assert row[field] is not None
    selected = result["selected_record"]
    assert selected["variant"] == result["selected_variant"]
    assert result["hard_ok"] == selected["hard_ok"]
    assert result["failed_hard_checks"] == selected["failed_hard_checks"]
    if result["decision"] in {"hard_valid_candidate", "no_improvement_same_as_b"}:
        assert result["hard_ok"] is True
        assert result["failed_hard_checks"] == []
        assert result["sidewalk_overlap_building_ids"] == []
        assert selected["checks_total"] == 29
        assert selected["access_coverage"] == pytest.approx(1.0)
        assert selected["dead_ends_unresolved"] == 0
    else:
        assert result["decision"] == "no_hard_valid_variant"
        assert result["hard_ok"] is False


def test_candidate_c_versus_candidate_b_is_measured():
    result = _candidate_c()
    b_control = result["b_control"]
    assert b_control["hard_ok"] is True
    assert b_control["failed_hard_checks"] == []
    comparison = result["comparison_vs_b"]
    expected_keys = {
        "groups_non_contiguous_delta",
        "total_row_runs_delta",
        "displacement_max_delta_m",
        "displacement_mean_delta_m",
        "group_centroid_displacement_max_delta_m",
        "group_centroid_displacement_mean_delta_m",
        "added_road_length_delta_m",
        "candidate_equals_b",
    }
    assert set(comparison) == expected_keys
    selected = result["selected_record"]
    if result["same_as_b"]:
        assert result["decision"] == "no_improvement_same_as_b"
        assert comparison["candidate_equals_b"] is True
        assert selected["signature"] == result["b_signature"]
        assert comparison["groups_non_contiguous_delta"] == pytest.approx(0)
        assert comparison["displacement_max_delta_m"] == pytest.approx(0)
        assert comparison["added_road_length_delta_m"] == pytest.approx(0)
    else:
        assert result["decision"] == "hard_valid_candidate"
        assert comparison["candidate_equals_b"] is False
        assert selected["signature"] != result["b_signature"]
        assert comparison["groups_non_contiguous_delta"] is not None
        # delta is the measured difference, never a rewritten value
        assert comparison["groups_non_contiguous_delta"] == pytest.approx(
            selected["groups_non_contiguous"]
            - b_control["groups_non_contiguous"]
        )
        assert comparison["displacement_max_delta_m"] == pytest.approx(
            selected["displacement_max_m"] - b_control["displacement_max_m"]
        )
        assert comparison["added_road_length_delta_m"] == pytest.approx(
            selected["added_road_length_m"]
            - b_control["added_road_length_m"]
        )


def test_candidate_c_rebuild_is_deterministic():
    context = _context()
    variants = {
        entry["variant"]: entry for entry in variant_plan(context["intent"])
    }
    entry = variants["y_asc_swap01"]
    first = run_candidate_variant(
        context["design_input"],
        context["basis"],
        context["intent"],
        context["standardized"],
        context["site_inner"],
        context["frozen_road_layout"],
        entry,
        candidate_id="C-y_asc_swap01",
    )
    second = run_candidate_variant(
        context["design_input"],
        context["basis"],
        context["intent"],
        context["standardized"],
        context["site_inner"],
        context["frozen_road_layout"],
        entry,
        candidate_id="C-y_asc_swap01",
    )
    assert candidate_signature(first["building_layout"]) == candidate_signature(
        second["building_layout"]
    )
    for field in (
        "hard_ok",
        "failed_hard_checks",
        "checks_total",
        "check_status",
        "groups_non_contiguous",
        "displacement_max_m",
        "group_centroid_displacement_max_m",
        "added_road_length_m",
        "access_coverage",
    ):
        assert first["record"][field] == second["record"][field]
    # the pure selection over the same records is deterministic too
    first_selection = select_candidate_c(
        [first["record"]], b_signature="other"
    )
    second_selection = select_candidate_c(
        [second["record"]], b_signature="other"
    )
    assert first_selection["decision"] == second_selection["decision"]
    assert first_selection["selected_variant"] == second_selection["selected_variant"]
    assert (
        first_selection["selected_record"]["signature"]
        == second_selection["selected_record"]["signature"]
    )


def test_candidate_c_full_build_is_deterministic_for_subset():
    context = _context()
    first = build_candidate_c(
        CASE,
        BASIS,
        variant_names=("default",),
        context=context,
        local_repair=False,
    )
    second = build_candidate_c(
        CASE,
        BASIS,
        variant_names=("default",),
        context=context,
        local_repair=False,
    )
    for key in (
        "decision",
        "selected_variant",
        "hard_ok",
        "same_as_b",
        "b_signature",
    ):
        assert first[key] == second[key]
    assert (
        first["selected_record"]["signature"]
        == second["selected_record"]["signature"]
    )
    assert first["comparison_vs_b"] == second["comparison_vs_b"]


def test_no_hard_valid_variant_is_reported_honestly():
    context = _context()
    result = build_candidate_c(
        CASE,
        BASIS,
        variant_names=("y_asc",),
        context=context,
        local_repair=False,
    )
    assert result["decision"] == "no_hard_valid_variant"
    assert result["hard_ok"] is False
    assert result["same_as_b"] is False
    assert result["selected_variant"] is None
    assert result["failed_hard_checks"]
    assert result["selected_record"]["variant"] == "y_asc"
    # the partial model is returned for inspection and labelled as failing
    assert result["selected_record"]["hard_ok"] is False
    assert result["variant_table"]
    assert any(
        "bounded generate-and-test" in note
        for note in result["non_claims"]
    )
    # unknown variant names are rejected rather than silently ignored
    with pytest.raises(ValueError):
        build_candidate_c(
            CASE, BASIS, variant_names=("does-not-exist",), context=context
        )


def test_local_repair_plan_is_deterministic_and_targets_worst_groups():
    result = _candidate_c()
    context = _context()
    first = local_repair_plan(
        context, result["building_layout"], result["group_quality"]
    )
    second = local_repair_plan(
        context, result["building_layout"], result["group_quality"]
    )
    assert first == second
    assert first
    # at least the four worst groups are attempted (Lead's bounded-repair floor)
    assert len({proposal["group_id"] for proposal in first}) >= 4
    group_ids = {
        group.group_id for group in context["intent"].groups
    }
    for proposal in first:
        assert proposal["group_id"] in group_ids
        assert proposal["kind"] in {
            "merge_into_neighbour_row",
            "adjacent_row",
            "compact_within_row",
        }
        assert proposal["target_row_y"] is not None
        # infeasible proposals are recorded honestly, feasible ones carry a spot
        assert (
            "target_center" in proposal
        )
        if proposal["target_center"] is None:
            assert proposal["infeasible_reason"] == "no_feasible_position"


def test_local_repair_acceptance_is_hard_first_and_strict():
    def record(name, *, hard, noncontig, disp_max, disp_mean, failed=None):
        return {
            "variant": name,
            "hard_ok": hard,
            "failed_hard_checks": [] if hard else (failed or ["FULL_SITE_NS_SPACING"]),
            "groups_non_contiguous": noncontig,
            "displacement_max_m": disp_max,
            "displacement_mean_m": disp_mean,
        }

    current = record("B", hard=True, noncontig=12, disp_max=278.0, disp_mean=48.0)
    # a hard failure is rejected even with better quality
    accepted, reason = accept_local_repair(
        current, record("bad", hard=False, noncontig=0, disp_max=10.0, disp_mean=5.0)
    )
    assert accepted is False
    assert "hard gates failed" in reason
    # fewer non-contiguous groups: accepted
    accepted, reason = accept_local_repair(
        current, record("fewer", hard=True, noncontig=11, disp_max=300.0, disp_mean=50.0)
    )
    assert accepted is True
    assert "strictly improved" in reason
    # same non-contiguous count but smaller displacement max: accepted
    accepted, _ = accept_local_repair(
        current, record("smaller_max", hard=True, noncontig=12, disp_max=250.0, disp_mean=48.0)
    )
    assert accepted is True
    # only displacement mean improves (max equal): accepted
    accepted, _ = accept_local_repair(
        current, record("smaller_mean", hard=True, noncontig=12, disp_max=278.0, disp_mean=47.0)
    )
    assert accepted is True
    # equal or worse quality: rejected
    accepted, reason = accept_local_repair(current, record("same", hard=True, noncontig=12, disp_max=278.0, disp_mean=48.0))
    assert accepted is False
    assert "no strict improvement" in reason
    accepted, _ = accept_local_repair(
        current, record("worse", hard=True, noncontig=12, disp_max=280.0, disp_mean=48.5)
    )
    assert accepted is False


def test_local_repair_is_bounded_and_reports_no_gain_honestly():
    result = _candidate_c()
    repair = result["local_repair"]
    assert repair is not None
    assert repair["schema_id"] == "dgcad.candidate-c-local-repair.v0.1"
    assert repair["candidate_count"] <= 3  # bounded by the test fixture
    assert repair["accepted_steps"] <= 2
    assert repair["stopped"] in {
        "no_candidate_accepted",
        "candidates_exhausted",
        "max_steps_reached",
    }
    assert repair["improved"] == result["local_repair_improved"]
    for entry in repair["log"]:
        assert entry["accepted"] is False or entry["accepted"] is True
        assert isinstance(entry["reason"], str) and entry["reason"]
        if entry["accepted"]:
            assert entry["candidate_hard_ok"] is True
            assert entry["candidate_quality_key"] < entry["current_quality_key"]
            assert entry["candidate_failed_hard_checks"] == []
    if not result["local_repair_improved"]:
        # honest no-gain: candidate C stays the hard-valid B-equivalent variant
        assert result["decision"] in {
            "no_improvement_same_as_b",
            "hard_valid_candidate",
        }
        if result["selected_variant"] in {"default", "B_control"}:
            assert result["same_as_b"] is True
            assert result["decision"] == "no_improvement_same_as_b"
    else:
        assert result["hard_ok"] is True
        assert result["selected_variant"] == "local_repair"
        assert result["same_as_b"] is False
        assert result["local_repair_improved"] is True

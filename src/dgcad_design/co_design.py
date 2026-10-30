"""M4d-2b candidate C: bounded generate-and-test co-design.

This module is deliberately **not** a joint optimiser.  It enumerates a fixed,
deterministic set of group-preserving building layouts (``variant_plan``), runs
the same rebuilt group-access generator on each of them against the frozen
44-road network, measures the full check set, and applies a hard-first
lexicographic selection.  The honest name for the method is *bounded
generate-and-test co-design*: the search space is 12 hand-declared variants and
no geometry is optimised jointly.

Hard gate definition (recomputed from geometry, never assumed):

* no check in :data:`HARD_CHECK_IDS` has status ``fail``;
* ``DesignConsistency.hard_checks_ok`` is true (no other check fails);
* the full-site road-clearance check reports zero sidewalk-overlap buildings.

When no variant passes, the best partial variant is returned with
``hard_ok=False`` and the failed checks listed; nothing is relabelled as a pass.

Selection (hard-first, then lexicographic, no opaque score):
fewest non-contiguous groups -> smallest per-building displacement max ->
smallest group-centroid displacement max -> smallest added road length ->
variant name.
"""
from __future__ import annotations

import hashlib
import time
from pathlib import Path
from typing import Any

import yaml
from shapely.geometry import box

from .access import build_co_design_access
from .basis import DesignBasis
from .buildings import (
    _standard_building,
    find_focus_design_rect,
    layout_focus_region,
    layout_group_preserving,
    standardize_all,
)
from .consistency import check_design
from .green import build_green_layout
from .input import load_design_input
from .intent import build_design_intent
from .intent_metrics import group_quality_metrics
from .parking import build_parking_layout
from .roads import build_road_layout

SCHEMA_ID = "dgcad.candidate-c.v0.1"

#: Hard checks used by the A/B evidence script (same definition, same ids).
HARD_CHECK_IDS = (
    "FULL_SITE_BOUNDARY_SETBACK",
    "FULL_SITE_BUILDING_OVERLAP",
    "FULL_SITE_ROAD_CLEARANCE",
    "FULL_SITE_NS_SPACING",
    "ROAD_ACCESS_COVERAGE",
    "DEAD_END_RESOLUTION",
)

#: Honest method description carried in every returned payload.
BOUNDED_SEARCH_NOTE = (
    "bounded generate-and-test co-design, not a joint optimisation: a fixed "
    "deterministic set of group-preserving layouts is generated, the same "
    "rebuilt group-access generator is applied to each, and the selection is "
    "hard-first lexicographic; no continuous geometry is optimised jointly "
    "and no opaque score or ranking is produced"
)


def candidate_signature(building_layout) -> str:
    """Deterministic short fingerprint of a building layout."""
    payload = "|".join(
        f"{item.building_id}:{round(item.design_centroid[0], 6)}:"
        f"{round(item.design_centroid[1], 6)}:{item.row_index}"
        for item in building_layout.buildings
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def added_road_length(road_layout, frozen_road_layout) -> float:
    """Total centreline length of roads that are not part of the frozen net."""
    frozen_ids = {road.edge_id for road in frozen_road_layout.roads}
    return float(
        sum(
            road.centerline.length
            for road in road_layout.roads
            if road.edge_id not in frozen_ids
        )
    )


def _variant_members(intent) -> tuple[list[str], list[str]]:
    group_ids = [group.group_id for group in intent.groups]
    focus_ids = {
        group.group_id
        for group in intent.groups
        if any(
            building_id in set(intent.focus_building_ids)
            for building_id in group.building_ids
        )
    }
    return group_ids, sorted(focus_ids)


def _swap(values, first: int, second: int) -> tuple[str, ...]:
    items = list(values)
    if 0 <= first < len(items) and 0 <= second < len(items):
        items[first], items[second] = items[second], items[first]
    return tuple(items)


def _rotate(values, count: int) -> tuple[str, ...]:
    items = list(values)
    if not items:
        return tuple()
    count %= len(items)
    return tuple(items[count:] + items[:count])


def _interleave(values) -> tuple[str, ...]:
    items = list(values)
    result: list[str] = []
    left, right = 0, len(items) - 1
    while left <= right:
        result.append(items[left])
        left += 1
        if left <= right:
            result.append(items[right])
            right -= 1
    return tuple(result)


def variant_plan(intent) -> list[dict[str, Any]]:
    """The 20 deterministic candidate-C variants (no randomness)."""
    group_ids, focus_ids = _variant_members(intent)
    by_id = {group.group_id: group for group in intent.groups}
    rest = [group_id for group_id in group_ids if group_id not in focus_ids]

    def centroid_y(group_id: str) -> float:
        return float(by_id[group_id].centroid[1])

    def centroid_x(group_id: str) -> float:
        return float(by_id[group_id].centroid[0])

    def y_asc(values) -> tuple[str, ...]:
        return tuple(sorted(values, key=lambda v: (centroid_y(v), v)))

    def y_desc(values) -> tuple[str, ...]:
        return tuple(sorted(values, key=lambda v: (-centroid_y(v), v)))

    def x_asc(values) -> tuple[str, ...]:
        return tuple(sorted(values, key=lambda v: (centroid_x(v), v)))

    def x_desc(values) -> tuple[str, ...]:
        return tuple(sorted(values, key=lambda v: (-centroid_x(v), v)))

    detail_variants = [
        ("y_asc_swap01", _swap(y_asc(rest), 0, 1),
         "focus first, y ascending detail with the first pair swapped"),
        ("y_asc_swap12", _swap(y_asc(rest), 1, 2),
         "focus first, y ascending detail with the second pair swapped"),
        ("y_asc_swap23", _swap(y_asc(rest), 2, 3),
         "focus first, y ascending detail with the third pair swapped"),
        ("y_asc_rotate1", _rotate(y_asc(rest), 1),
         "focus first, y ascending detail rotated by one group"),
        ("focus_first_x_asc", x_asc(rest),
         "focus-owning groups first, then x ascending"),
        ("focus_first_x_desc", x_desc(rest),
         "focus-owning groups first, then x descending"),
        ("focus_first_id_desc", tuple(sorted(rest, reverse=True)),
         "focus-owning groups first, then group id descending"),
    ]
    plan = [
        ("default", None, "engine default group order (same as candidate B)"),
        ("y_asc", y_asc(group_ids), "source group centroid y ascending"),
        ("y_desc", y_desc(group_ids), "source group centroid y descending"),
        ("x_asc", x_asc(group_ids), "source group centroid x ascending"),
        ("x_desc", x_desc(group_ids), "source group centroid x descending"),
        ("id_asc", tuple(sorted(group_ids)), "group id ascending"),
        ("id_desc", tuple(sorted(group_ids, reverse=True)),
         "group id descending"),
        ("count_desc",
         tuple(sorted(group_ids,
                      key=lambda v: (-len(by_id[v].building_ids), v))),
         "largest groups first"),
        ("focus_first_y_asc", tuple(focus_ids) + y_asc(rest),
         "focus-owning groups first, then y ascending"),
        ("focus_last_y_asc", y_asc(rest) + tuple(focus_ids),
         "focus-owning groups last, then y ascending"),
        ("focus_first_y_desc", tuple(focus_ids) + y_desc(rest),
         "focus-owning groups first, then y descending"),
        ("focus_last_y_desc", y_desc(rest) + tuple(focus_ids),
         "focus-owning groups last, then y descending"),
        (
            "xspan_asc",
            tuple(sorted(
                group_ids,
                key=lambda v: (round(by_id[v].bbox[2] - by_id[v].bbox[0], 6), v),
            )),
            "narrowest source group bbox first",
        ),
    ]
    plan.extend(
        (name, tuple(focus_ids) + order, description)
        for name, order, description in detail_variants
    )
    return [
        {"variant": name, "order": order, "description": description}
        for name, order, description in plan
    ]


def _hard_components(consistency, checks: dict[str, Any]) -> dict[str, Any]:
    failed = [
        check_id
        for check_id in HARD_CHECK_IDS
        if checks.get(check_id, {}).get("status") == "fail"
    ]
    sidewalk = list(
        checks.get("FULL_SITE_ROAD_CLEARANCE", {})
        .get("detail", {})
        .get("sidewalk_overlap_building_ids")
        or []
    )
    hard_ok = (
        not failed
        and consistency.hard_checks_ok
        and not sidewalk
    )
    return {
        "hard_ok": bool(hard_ok),
        "failed_hard_checks": failed,
        "sidewalk_overlap_building_ids": sidewalk,
        "sidewalk_overlap_count": len(sidewalk),
    }


def _variant_record(
    *,
    variant: str,
    order,
    layout,
    consistency,
    quality,
    road_layout,
    road_access,
    frozen_road_layout,
    seconds: float,
) -> dict[str, Any]:
    checks = {check["id"]: check for check in consistency.checks}
    status_counts: dict[str, int] = {}
    for check in consistency.checks:
        status_counts[check["status"]] = (
            status_counts.get(check["status"], 0) + 1
        )
    hard = _hard_components(consistency, checks)
    record = {
        "variant": variant,
        "order": None if order is None else list(order),
        "signature": candidate_signature(layout),
        "seconds": round(seconds, 2),
        "checks_total": len(consistency.checks),
        "check_status": status_counts,
        "hard_ok": hard["hard_ok"],
        "failed_hard_checks": hard["failed_hard_checks"],
        "sidewalk_overlap_count": hard["sidewalk_overlap_count"],
        "sidewalk_overlap_building_ids": hard[
            "sidewalk_overlap_building_ids"
        ],
        "groups_non_contiguous": quality["fragmentation"][
            "groups_non_contiguous"
        ],
        "total_row_runs": quality["fragmentation"]["total_row_runs"],
        "displacement_max_m": quality["displacement"]["max_m"],
        "displacement_mean_m": quality["displacement"]["mean_m"],
        "group_centroid_displacement_max_m": quality["shape_distortion"][
            "group_centroid_displacement_max_m"
        ],
        "group_centroid_displacement_mean_m": quality["shape_distortion"][
            "group_centroid_displacement_mean_m"
        ],
        "added_road_length_m": added_road_length(
            road_layout, frozen_road_layout
        ),
        "access_coverage": road_access.road_access_coverage,
        "relation_error_count": len(road_access.relation_errors),
        "dead_ends_unresolved": road_access.dead_ends_unresolved,
    }
    del checks
    return record


def run_candidate_variant(
    design_input,
    basis: DesignBasis,
    intent,
    standardized: dict[str, Any],
    site_inner,
    frozen_road_layout,
    variant: dict[str, Any],
    *,
    candidate_id: str,
) -> dict[str, Any]:
    """Run one candidate-C variant end to end and return its models + record."""
    started = time.perf_counter()
    layout = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=frozen_road_layout.corridor_union,
        group_order=variant.get("order"),
    )
    road_layout, road_access, access_meta = build_co_design_access(
        design_input,
        basis,
        intent,
        layout,
        frozen_road_layout,
        candidate_id=candidate_id,
    )
    green_layout = build_green_layout(
        design_input,
        layout,
        road_layout,
        basis,
        box(*intent.focus_bbox),
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    consistency = check_design(
        design_input,
        basis,
        intent,
        layout,
        road_layout,
        green_layout,
        parking_layout,
        road_access,
    )
    quality = group_quality_metrics(intent, layout)
    record = _variant_record(
        variant=str(variant["variant"]),
        order=variant.get("order"),
        layout=layout,
        consistency=consistency,
        quality=quality,
        road_layout=road_layout,
        road_access=road_access,
        frozen_road_layout=frozen_road_layout,
        seconds=time.perf_counter() - started,
    )
    return {
        "record": record,
        "building_layout": layout,
        "road_layout": road_layout,
        "road_access": road_access,
        "green_layout": green_layout,
        "parking_layout": parking_layout,
        "consistency": consistency,
        "group_quality": quality,
        "access_meta": access_meta,
    }


def _failed_variant_record(
    entry: dict[str, Any], error: Exception
) -> dict[str, Any]:
    """Honest record for a variant whose layout could not be generated."""
    return {
        "variant": str(entry["variant"]),
        "order": None
        if entry.get("order") is None
        else list(entry["order"]),
        "signature": None,
        "seconds": None,
        "checks_total": 0,
        "check_status": {},
        "hard_ok": False,
        "failed_hard_checks": [],
        "sidewalk_overlap_count": 0,
        "sidewalk_overlap_building_ids": [],
        "groups_non_contiguous": None,
        "total_row_runs": None,
        "displacement_max_m": None,
        "displacement_mean_m": None,
        "group_centroid_displacement_max_m": None,
        "group_centroid_displacement_mean_m": None,
        "added_road_length_m": None,
        "access_coverage": None,
        "relation_error_count": None,
        "dead_ends_unresolved": None,
        "error": f"{type(error).__name__}: {error}",
    }


def _delta(value, reference):
    if value is None or reference is None:
        return None
    return float(value) - float(reference)


def select_candidate_c(
    records: list[dict[str, Any]],
    *,
    b_signature: str | None = None,
) -> dict[str, Any]:
    """Hard-first lexicographic selection (no score, no ranking)."""

    def key(record: dict[str, Any]):
        return (
            int(record.get("groups_non_contiguous") or 0),
            float(record.get("displacement_max_m") or 0.0),
            float(record.get("group_centroid_displacement_max_m") or 0.0),
            float(record.get("added_road_length_m") or 0.0),
            str(record.get("variant") or ""),
        )

    eligible = [
        record for record in records if bool(record.get("hard_ok"))
    ]
    if not eligible:
        partial = (
            sorted(
                records,
                key=lambda record: (
                    len(record.get("failed_hard_checks") or []),
                    key(record),
                ),
            )[0]
            if records
            else None
        )
        return {
            "decision": "no_hard_valid_variant",
            "hard_valid": False,
            "selected_variant": None,
            "selected_record": partial,
            "failures": {
                str(record["variant"]): list(
                    record.get("failed_hard_checks") or []
                )
                for record in records
                if not record.get("hard_ok")
            },
            "note": (
                "no variant passed the hard gates; the best partial variant is "
                "returned and every failure is listed - no pass is claimed"
            ),
        }
    best = min(eligible, key=key)
    same_as_b = (
        b_signature is not None
        and str(best.get("signature")) == str(b_signature)
    )
    return {
        "decision": (
            "no_improvement_same_as_b"
            if same_as_b
            else "hard_valid_candidate"
        ),
        "hard_valid": True,
        "same_as_b": bool(same_as_b),
        "selected_variant": str(best["variant"]),
        "selected_record": best,
        "failures": {
            str(record["variant"]): list(record.get("failed_hard_checks") or [])
            for record in records
            if not record.get("hard_ok")
        },
        "note": (
            "candidate C is identical to the candidate B control variant"
            if same_as_b
            else "hard-first lexicographic selection among hard-valid variants"
        ),
    }


def load_candidate_context(
    case_dir: str | Path,
    basis_path: str | Path,
) -> dict[str, Any]:
    """Load the shared candidate-C context (input, intent, frozen roads).

    The frozen road network is built on the focus layout exactly as the A/B
    evidence does (``build_road_layout`` default auto alignment), so the 44
    roads are the published design network.
    """
    basis = DesignBasis.from_dict(
        yaml.safe_load(Path(basis_path).read_text(encoding="utf-8"))
    )
    design_input = load_design_input(case_dir, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)
    baseline_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    frozen_road_layout = build_road_layout(
        design_input, basis, intent, baseline_layout
    )
    return {
        "basis": basis,
        "design_input": design_input,
        "intent": intent,
        "standardized": standardized,
        "site_inner": site_inner,
        "baseline_layout": baseline_layout,
        "frozen_road_layout": frozen_road_layout,
    }


# ---------------------------------------------------------------------------
# Bounded local repair layer (starting from candidate B)
# ---------------------------------------------------------------------------

#: A local repair candidate is a single deterministic building micro-move.
GROUP_REPAIR_GROUPS = 4
GROUP_REPAIR_PROPOSALS = 2
LOCAL_REPAIR_MAX_CANDIDATES = 8
LOCAL_REPAIR_MAX_STEPS = 5
LOCAL_REPAIR_MAX_GROUPS = 4


def _group_by_id(intent) -> dict[str, Any]:
    return {group.group_id: group for group in intent.groups}


def _group_severity_order(quality: dict[str, Any]) -> list[str]:
    """Worst-fragmentation groups first (deterministic)."""
    scored = []
    for record in quality.get("groups", ()) or ():
        fragmentation = record.get("fragmentation", {})
        cohesion = record.get("cohesion", {})
        scored.append(
            (
                int(fragmentation.get("row_runs") or 0),
                float(fragmentation.get("max_row_gap") or 0.0),
                float(cohesion.get("max_span_m") or 0.0),
                str(record.get("group_id")),
            )
        )
    scored.sort(key=lambda item: (-item[0], -item[1], -item[2], item[3]))
    return [item[3] for item in scored]


def _center_feasible(
    context: dict[str, Any],
    building_layout,
    trace_id: str,
    center: tuple[float, float],
) -> bool:
    """Cheap analytic feasibility for one moved footprint (no access rebuild)."""
    basis = context["basis"]
    site_inner = context["site_inner"]
    corridor = context["frozen_road_layout"].corridor_union
    mover = next(
        item
        for item in building_layout.buildings
        if item.building_id == trace_id
    )
    bounds = mover.footprint.bounds
    width = bounds[2] - bounds[0]
    depth = bounds[3] - bounds[1]
    rect = box(
        center[0] - width / 2.0,
        center[1] - depth / 2.0,
        center[0] + width / 2.0,
        center[1] + depth / 2.0,
    )
    if not site_inner.buffer(0.01).contains(rect):
        return False
    if rect.distance(corridor) < basis.building_road_clearance_m - 1e-6:
        return False
    rect_bounds = rect.bounds
    for other in building_layout.buildings:
        if other.building_id == trace_id:
            continue
        other_bounds = other.footprint.bounds
        if rect.intersection(other.footprint).area > 0.01:
            return False
        y_overlap = min(rect_bounds[3], other_bounds[3]) - max(
            rect_bounds[1], other_bounds[1]
        )
        if y_overlap > 0.0:
            gap = max(
                other_bounds[0] - rect_bounds[2],
                rect_bounds[0] - other_bounds[2],
            )
            if gap < basis.side_spacing_m - 1e-6:
                return False
            continue
        x_overlap = min(rect_bounds[2], other_bounds[2]) - max(
            rect_bounds[0], other_bounds[0]
        )
        if x_overlap <= 0.0:
            continue
        vertical_gap = max(
            0.0,
            rect_bounds[1] - other_bounds[3],
            other_bounds[1] - rect_bounds[3],
        )
        if vertical_gap < basis.north_south_spacing_m - 1e-6:
            return False
    return True


def _score_center(
    context: dict[str, Any], trace_id: str, center: tuple[float, float]
) -> float:
    source = context["standardized"][trace_id].source_centroid
    return float(
        (
            (center[0] - source[0]) ** 2 + (center[1] - source[1]) ** 2
        )
        ** 0.5
    )


def _find_repair_center(
    context: dict[str, Any],
    building_layout,
    trace_id: str,
    target_row_y: float,
) -> tuple[float, float] | None:
    """Deterministic scan for the least-displaced feasible position in a row."""
    mover = next(
        item
        for item in building_layout.buildings
        if item.building_id == trace_id
    )
    bounds = mover.footprint.bounds
    width = bounds[2] - bounds[0]
    depth = bounds[3] - bounds[1]
    desired_y = target_row_y + depth / 2.0
    source = context["standardized"][trace_id].source_centroid
    anchors = [mover.design_centroid[0], source[0]]
    for other in building_layout.buildings:
        if other.building_id == trace_id:
            continue
        if abs(other.footprint.bounds[1] - target_row_y) <= 1e-6:
            other_bounds = other.footprint.bounds
            anchors.append(
                other_bounds[0] - 13.0 - width / 2.0
            )
            anchors.append(
                other_bounds[2] + 13.0 + width / 2.0
            )
            anchors.append(
                (other_bounds[0] + other_bounds[2]) / 2.0
            )
    best: tuple[float, tuple[float, float]] | None = None
    for anchor in sorted({round(value, 6) for value in anchors}):
        for step in range(-24, 25):
            center = (anchor + step * 2.0, desired_y)
            if not _center_feasible(
                context, building_layout, trace_id, center
            ):
                continue
            cost = _score_center(context, trace_id, center)
            if best is None or cost < best[0] - 1e-9:
                best = (cost, center)
        if best is not None and abs(best[1][0] - anchor) <= 2.0:
            break
    return None if best is None else best[1]


def local_repair_plan(
    context: dict[str, Any],
    building_layout,
    group_quality: dict[str, Any],
    *,
    max_groups: int = LOCAL_REPAIR_MAX_GROUPS,
    proposals_per_group: int = GROUP_REPAIR_PROPOSALS,
) -> list[dict[str, Any]]:
    """Deterministic micro-move proposals for the worst groups.

    Groups are ordered by fragmentation severity and then by their worst
    member displacement.  For each group up to two movers (largest building
    displacement first) are tried on three deterministic targets: (a) the row
    of the nearest group neighbour (merge), (b) the adjacent 31 m row towards
    the group centroid, (c) a compacted position inside the current row.  The
    x position is chosen by a deterministic feasible-position scan keeping the
    boundary, overlap, 13 m side spacing, 20 m row spacing and the fixed-road
    3 m corridor clearance.
    """
    basis = context["basis"]
    depth = basis.staircase_depth_m
    pitch = depth + basis.north_south_spacing_m
    buildings = {item.building_id: item for item in building_layout.buildings}
    groups = _group_by_id(context["intent"])
    quality_records = {
        str(record.get("group_id")): record
        for record in group_quality.get("groups", ()) or ()
    }
    severity = _group_severity_order(group_quality)
    displacement_order = sorted(
        (
            (
                -float(
                    (quality_records.get(group_id) or {})
                    .get("displacement", {})
                    .get("max_m")
                    or 0.0
                ),
                group_id,
            )
            for group_id in severity
        ),
        key=lambda item: (item[0], item[1]),
    )
    ordered_groups: list[str] = []
    for group_id in severity[:max_groups]:
        if group_id not in ordered_groups:
            ordered_groups.append(group_id)
    for _, group_id in displacement_order:
        if len(ordered_groups) >= max_groups + 2:
            break
        if group_id not in ordered_groups:
            ordered_groups.append(group_id)

    proposals: list[dict[str, Any]] = []
    for group_id in ordered_groups:
        group = groups.get(group_id)
        if group is None:
            continue
        members = [
            buildings[trace_id]
            for trace_id in group.building_ids
            if trace_id in buildings
        ]
        if len(members) < 2:
            continue
        movers = sorted(
            members,
            key=lambda item: (
                -round(float(item.displacement_m), 6),
                item.building_id,
            ),
        )[:2]
        centroid_y = sum(
            item.design_centroid[1] for item in members
        ) / len(members)
        group_proposals: list[dict[str, Any]] = []
        for mover in movers:
            if len(group_proposals) >= proposals_per_group:
                break
            others = [
                item
                for item in members
                if item.building_id != mover.building_id
            ]
            nearest = min(
                others,
                key=lambda item: (
                    round(
                        (
                            (item.design_centroid[0] - mover.design_centroid[0])
                            ** 2
                            + (
                                item.design_centroid[1]
                                - mover.design_centroid[1]
                            )
                            ** 2
                        )
                        ** 0.5,
                        6,
                    ),
                    item.building_id,
                ),
            )
            mover_row_y = mover.footprint.bounds[1]
            adjacent_y = (
                mover_row_y + pitch
                if centroid_y >= mover.design_centroid[1]
                else mover_row_y - pitch
            )
            targets = [
                (nearest.footprint.bounds[1], "merge_into_neighbour_row"),
                (adjacent_y, "adjacent_row"),
                (mover_row_y, "compact_within_row"),
            ]
            seen_targets: set[float] = set()
            for target_y, kind in targets:
                if len(group_proposals) >= proposals_per_group:
                    break
                key_y = round(target_y, 6)
                if key_y in seen_targets:
                    continue
                seen_targets.add(key_y)
                center = _find_repair_center(
                    context, building_layout, mover.building_id, target_y
                )
                if center is None:
                    group_proposals.append(
                        {
                            "group_id": group_id,
                            "building_id": mover.building_id,
                            "kind": kind,
                            "target_center": None,
                            "target_row_y": target_y,
                            "current_displacement_m": round(
                                float(mover.displacement_m), 3
                            ),
                            "infeasible_reason": "no_feasible_position",
                        }
                    )
                    continue
                if (
                    (center[0] - mover.design_centroid[0]) ** 2
                    + (center[1] - mover.design_centroid[1]) ** 2
                ) ** 0.5 <= 1e-6:
                    continue
                group_proposals.append(
                    {
                        "group_id": group_id,
                        "building_id": mover.building_id,
                        "kind": kind,
                        "target_center": center,
                        "target_row_y": target_y,
                        "current_displacement_m": round(
                            float(mover.displacement_m), 3
                        ),
                    }
                )
        proposals.extend(group_proposals)
    return proposals


def _relayout_with_center(
    context: dict[str, Any],
    building_layout,
    trace_id: str,
    center: tuple[float, float],
):
    """Return a new BuildingLayout with one building moved (rows re-derived)."""
    basis = context["basis"]
    design_input = context["design_input"]
    site_inner = context["site_inner"]
    groups = _group_by_id(context["intent"])
    group_by_building: dict[str, str] = {}
    for group_id, group in groups.items():
        for building_id in group.building_ids:
            group_by_building[building_id] = group_id
    input_by_id = {item.trace_id: item for item in design_input.buildings}

    placed = []
    for item in building_layout.buildings:
        target = center if item.building_id == trace_id else item.design_centroid
        placed.append(
            _standard_building(
                input_by_id[item.building_id],
                basis,
                center=tuple(target),
                angle=0.0,
                row_index=0,
                subgroup_id=group_by_building.get(
                    item.building_id, str(item.subgroup_id)
                ),
            )
        )
    row_ys = sorted(
        {round(item.footprint.bounds[1], 6) for item in placed}
    )
    row_order = {y: index + 1 for index, y in enumerate(row_ys)}
    indexed = [
        _standard_building(
            input_by_id[item.building_id],
            basis,
            center=item.design_centroid,
            angle=0.0,
            row_index=row_order[round(item.footprint.bounds[1], 6)],
            subgroup_id=str(item.subgroup_id),
        )
        for item in placed
    ]
    by_id = {item.building_id: item for item in indexed}
    segments: dict[tuple[int, str], list[str]] = {}
    for item in indexed:
        segments.setdefault(
            (int(item.row_index), str(item.subgroup_id)), []
        ).append(item.building_id)
    rows = []
    green_strips = []
    ns_spacing = basis.north_south_spacing_m
    depth = basis.staircase_depth_m
    for (row_index, subgroup_id), building_ids in sorted(
        segments.items(), key=lambda entry: (entry[0][0], entry[0][1])
    ):
        ordered_ids = sorted(
            building_ids,
            key=lambda value: (
                by_id[value].footprint.bounds[0],
                value,
            ),
        )
        row_y = min(
            by_id[value].footprint.bounds[1] for value in ordered_ids
        )
        row_height = max(
            by_id[value].footprint.bounds[3] - row_y
            for value in ordered_ids
        )
        rows.append(
            {
                "row": row_index,
                "subgroup_id": subgroup_id,
                "y": row_y,
                "building_ids": ordered_ids,
                "north_south_gap_m": ns_spacing,
            }
        )
        strip = box(
            min(by_id[value].footprint.bounds[0] for value in ordered_ids),
            row_y + row_height + ns_spacing / 2.0 - 4.0,
            max(by_id[value].footprint.bounds[2] for value in ordered_ids),
            row_y + row_height + ns_spacing / 2.0 + 4.0,
        ).intersection(site_inner)
        if not strip.is_empty and strip.area >= 1.0:
            green_strips.append(strip)
    focus_buildings = tuple(
        by_id[item.building_id]
        for item in building_layout.focus_buildings
        if item.building_id in by_id
    )
    return type(building_layout)(
        buildings=tuple(
            by_id[item.building_id] for item in building_layout.buildings
        ),
        focus_buildings=focus_buildings,
        rows=tuple(rows),
        green_strips=tuple(green_strips),
        dropped_focus_building_ids=(),
    )


def _quick_repair_reject(
    context: dict[str, Any], building_layout, trace_id: str
) -> str | None:
    """Cheap geometric rejection before rebuilding the access network."""
    basis = context["basis"]
    site_inner = context["site_inner"]
    corridor = context["frozen_road_layout"].corridor_union
    mover = next(
        item
        for item in building_layout.buildings
        if item.building_id == trace_id
    )
    if not site_inner.buffer(0.01).contains(mover.footprint):
        return "outside_boundary_setback"
    if mover.footprint.distance(corridor) < (
        basis.building_road_clearance_m - 1e-6
    ):
        return "road_corridor_clearance"
    mover_bounds = mover.footprint.bounds
    for other in building_layout.buildings:
        if other.building_id == trace_id:
            continue
        other_bounds = other.footprint.bounds
        if (
            mover.footprint.intersection(other.footprint).area
            > 0.01
        ):
            return "building_overlap"
        if (
            min(mover_bounds[3], other_bounds[3])
            - max(mover_bounds[1], other_bounds[1])
            > 0.0
        ):
            gap = max(
                other_bounds[0] - mover_bounds[2],
                mover_bounds[0] - other_bounds[2],
            )
            if gap < basis.side_spacing_m - 1e-6:
                return "side_spacing"
        x_overlap = min(
            mover_bounds[2], other_bounds[2]
        ) - max(mover_bounds[0], other_bounds[0])
        if x_overlap > 0.0:
            vertical_gap = max(
                0.0,
                mover_bounds[1] - other_bounds[3],
                other_bounds[1] - mover_bounds[3],
            )
            if vertical_gap < basis.north_south_spacing_m - 1e-6:
                return "north_south_spacing"
    return None


def _repair_quality_key(record: dict[str, Any]) -> tuple:
    return (
        int(record.get("groups_non_contiguous") or 0),
        float(record.get("displacement_max_m") or 0.0),
        float(record.get("displacement_mean_m") or 0.0),
    )


def accept_local_repair(
    current_record: dict[str, Any],
    candidate_record: dict[str, Any],
) -> tuple[bool, str]:
    """Hard-first acceptance: hard pass and a strict quality-key decrease."""
    if not candidate_record.get("hard_ok"):
        failed = ", ".join(candidate_record.get("failed_hard_checks") or [])
        return False, (
            "rejected: hard gates failed"
            + (f" ({failed})" if failed else "")
        )
    current_key = _repair_quality_key(current_record)
    candidate_key = _repair_quality_key(candidate_record)
    if candidate_key < current_key:
        return True, (
            "accepted: quality key strictly improved "
            f"{current_key} -> {candidate_key}"
        )
    return False, (
        "rejected: no strict improvement in (non-contiguous groups, "
        f"displacement max, displacement mean): {current_key} -> "
        f"{candidate_key}"
    )


def _evaluate_layout_candidate(
    context: dict[str, Any], layout, candidate_id: str
) -> dict[str, Any]:
    design_input = context["design_input"]
    basis = context["basis"]
    intent = context["intent"]
    frozen_road_layout = context["frozen_road_layout"]
    road_layout, road_access, access_meta = build_co_design_access(
        design_input,
        basis,
        intent,
        layout,
        frozen_road_layout,
        candidate_id=candidate_id,
    )
    green_layout = build_green_layout(
        design_input,
        layout,
        road_layout,
        basis,
        box(*intent.focus_bbox),
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    consistency = check_design(
        design_input,
        basis,
        intent,
        layout,
        road_layout,
        green_layout,
        parking_layout,
        road_access,
    )
    quality = group_quality_metrics(intent, layout)
    record = _variant_record(
        variant=candidate_id,
        order=None,
        layout=layout,
        consistency=consistency,
        quality=quality,
        road_layout=road_layout,
        road_access=road_access,
        frozen_road_layout=frozen_road_layout,
        seconds=0.0,
    )
    return {
        "record": record,
        "building_layout": layout,
        "road_layout": road_layout,
        "road_access": road_access,
        "green_layout": green_layout,
        "parking_layout": parking_layout,
        "consistency": consistency,
        "group_quality": quality,
        "access_meta": access_meta,
    }


def run_local_repair(
    context: dict[str, Any],
    base_models: dict[str, Any],
    *,
    max_candidates: int = LOCAL_REPAIR_MAX_CANDIDATES,
    max_steps: int = LOCAL_REPAIR_MAX_STEPS,
) -> dict[str, Any]:
    """Bounded deterministic local repair starting from candidate B.

    Each proposal is one building micro-move; it is evaluated through the full
    rebuilt-access + 29-check pipeline and accepted only when hard gates pass
    and the lexicographic quality key strictly decreases.  Nothing is accepted
    on a trade-off that worsens the key.
    """
    started = time.perf_counter()
    current = base_models
    current_record = current["record"]
    proposals = local_repair_plan(
        context,
        current["building_layout"],
        current["group_quality"],
    )[:max_candidates]
    log: list[dict[str, Any]] = []
    accepted_steps = 0
    stopped = "candidates_exhausted"
    for index, proposal in enumerate(proposals):
        if accepted_steps >= max_steps:
            stopped = "max_steps_reached"
            break
        if proposal.get("target_center") is None:
            log.append(
                {
                    **proposal,
                    "accepted": False,
                    "reason": (
                        "rejected: no feasible position inside the fixed-road "
                        "buildable area for this target row"
                    ),
                }
            )
            continue
        candidate_layout = _relayout_with_center(
            context,
            current["building_layout"],
            proposal["building_id"],
            proposal["target_center"],
        )
        quick = _quick_repair_reject(
            context, candidate_layout, proposal["building_id"]
        )
        if quick is not None:
            log.append(
                {
                    **proposal,
                    "accepted": False,
                    "reason": f"rejected: quick geometric check ({quick})",
                }
            )
            continue
        candidate = _evaluate_layout_candidate(
            context,
            candidate_layout,
            f"C-repair-{index + 1:02d}",
        )
        accept, reason = accept_local_repair(
            current_record, candidate["record"]
        )
        log.append(
            {
                **proposal,
                "accepted": accept,
                "reason": reason,
                "candidate_quality_key": list(
                    _repair_quality_key(candidate["record"])
                ),
                "current_quality_key": list(
                    _repair_quality_key(current_record)
                ),
                "candidate_hard_ok": candidate["record"]["hard_ok"],
                "candidate_failed_hard_checks": list(
                    candidate["record"]["failed_hard_checks"]
                ),
                "candidate_added_road_length_m": candidate["record"][
                    "added_road_length_m"
                ],
            }
        )
        if accept:
            current = candidate
            current_record = candidate["record"]
            accepted_steps += 1
    if accepted_steps == 0 and stopped == "candidates_exhausted":
        stopped = "no_candidate_accepted"
    return {
        "schema_id": "dgcad.candidate-c-local-repair.v0.1",
        "method": (
            "bounded deterministic local repair from candidate B: one-building "
            "micro-moves on the worst-fragmentation groups, full rebuilt-access "
            "+ 29-check evaluation per candidate, hard-first acceptance"
        ),
        "proposals": proposals,
        "log": log,
        "candidate_count": len(log),
        "accepted_steps": accepted_steps,
        "stopped": stopped,
        "improved": accepted_steps > 0,
        "current": current,
        "current_record": current_record,
        "elapsed_s": round(time.perf_counter() - started, 1),
    }


def build_candidate_c(
    case_dir: str | Path,
    basis_path: str | Path,
    *,
    variant_names: tuple[str, ...] | None = None,
    context: dict[str, Any] | None = None,
    local_repair: bool = True,
    max_repair_candidates: int = LOCAL_REPAIR_MAX_CANDIDATES,
    max_repair_steps: int = LOCAL_REPAIR_MAX_STEPS,
) -> dict[str, Any]:
    """Build candidate C: generate the variant set, test it, select hard-first.

    ``variant_names`` is an optional bounded subset (used by tests); it never
    changes a variant's geometry, only how many of the declared variants are
    evaluated.  The default evaluates the full 20-variant plan.
    ``context`` is an optional prebuilt :func:`load_candidate_context` result
    so callers can reuse the loaded case and frozen road network.

    ``local_repair`` adds the bounded deterministic local-repair layer that
    starts from candidate B: worst-fragmentation groups get 1-2 one-building
    micro-moves, each evaluated through the rebuilt-access + 29-check pipeline
    and accepted only when hard gates pass and the quality key strictly
    improves.  ``max_repair_candidates`` / ``max_repair_steps`` bound the work.
    """
    started = time.perf_counter()
    if context is None:
        context = load_candidate_context(case_dir, basis_path)
    basis = context["basis"]
    design_input = context["design_input"]
    intent = context["intent"]
    standardized = context["standardized"]
    site_inner = context["site_inner"]
    frozen_road_layout = context["frozen_road_layout"]

    plan = variant_plan(intent)
    by_name = {entry["variant"]: entry for entry in plan}
    if variant_names is None:
        selected_plan = plan
    else:
        unknown = [
            name for name in variant_names if name not in by_name
        ]
        if unknown:
            raise ValueError(
                "unknown candidate C variant(s): " + ", ".join(sorted(unknown))
            )
        selected_plan = [by_name[name] for name in variant_names]

    # candidate B control: the engine default group-preserving layout
    b_variant = {
        "variant": "B_control",
        "order": None,
        "description": "candidate B control (engine default group order)",
    }
    b_models = run_candidate_variant(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        frozen_road_layout,
        b_variant,
        candidate_id="B",
    )
    b_record = dict(b_models["record"])
    b_record["variant"] = "B_control"
    b_signature = str(b_record["signature"])

    variant_rows: list[dict[str, Any]] = []
    models: dict[str, dict[str, Any]] = {}
    for entry in selected_plan:
        if entry["variant"] == "default":
            # the default order is exactly candidate B; reuse the measured model
            record = dict(b_record)
            record["variant"] = "default"
            variant_rows.append(record)
            models["default"] = b_models
            continue
        try:
            result = run_candidate_variant(
                design_input,
                basis,
                intent,
                standardized,
                site_inner,
                frozen_road_layout,
                entry,
                candidate_id=f"C-{entry['variant']}",
            )
        except Exception as exc:  # noqa: BLE001 - record the honest failure
            variant_rows.append(_failed_variant_record(entry, exc))
            continue
        variant_rows.append(result["record"])
        models[entry["variant"]] = result

    selection = select_candidate_c(variant_rows, b_signature=b_signature)
    selected_variant = selection.get("selected_variant")
    chosen = models.get(selected_variant) if selected_variant else None
    if chosen is None:
        # no hard-valid variant: return the best partial model for inspection
        partial_name = (
            None
            if selection.get("selected_record") is None
            else selection["selected_record"]["variant"]
        )
        if partial_name is not None:
            chosen = models.get(partial_name)
        if chosen is None:
            for row in variant_rows:
                if row["variant"] in models:
                    chosen = models[row["variant"]]
                    break
    if chosen is None:
        raise ValueError(
            "candidate C: no variant produced a building layout; failures: "
            + "; ".join(
                f"{row['variant']}: {row.get('error', 'hard gate failure')}"
                for row in variant_rows
            )
        )

    decision = selection["decision"]
    same_as_b = bool(selection.get("same_as_b", False))
    local_repair_result: dict[str, Any] | None = None
    repair_improved = False
    if local_repair:
        repair = run_local_repair(
            context,
            b_models,
            max_candidates=max_repair_candidates,
            max_steps=max_repair_steps,
        )
        local_repair_result = {
            key: value
            for key, value in repair.items()
            if key not in {"current", "current_record"}
        }
        local_repair_result["current_record"] = repair["current_record"]
        repair_improved = bool(repair["improved"])
        if repair_improved:
            chosen = repair["current"]
            decision = "hard_valid_candidate"
            same_as_b = (
                chosen["record"]["signature"] == b_signature
            )

    b_metrics = {
        key_name: b_record[key_name]
        for key_name in (
            "groups_non_contiguous",
            "total_row_runs",
            "displacement_max_m",
            "displacement_mean_m",
            "group_centroid_displacement_max_m",
            "group_centroid_displacement_mean_m",
            "added_road_length_m",
            "access_coverage",
            "hard_ok",
            "failed_hard_checks",
        )
    }
    chosen_record = chosen["record"]
    if repair_improved:
        chosen_record = dict(chosen_record)
        chosen_record["variant"] = "local_repair"
        selected_variant = "local_repair"
        local_repair_result["current_record"] = dict(chosen_record)
    elif selected_variant is not None:
        # the "default" variant reuses the candidate-B model; normalise the
        # record label to the variant actually selected
        chosen_record = dict(chosen_record)
        chosen_record["variant"] = selected_variant
    comparison = {
        "groups_non_contiguous_delta": _delta(
            chosen_record["groups_non_contiguous"],
            b_record["groups_non_contiguous"],
        ),
        "total_row_runs_delta": _delta(
            chosen_record["total_row_runs"], b_record["total_row_runs"]
        ),
        "displacement_max_delta_m": _delta(
            chosen_record["displacement_max_m"],
            b_record["displacement_max_m"],
        ),
        "displacement_mean_delta_m": _delta(
            chosen_record["displacement_mean_m"],
            b_record["displacement_mean_m"],
        ),
        "group_centroid_displacement_max_delta_m": _delta(
            chosen_record["group_centroid_displacement_max_m"],
            b_record["group_centroid_displacement_max_m"],
        ),
        "group_centroid_displacement_mean_delta_m": _delta(
            chosen_record["group_centroid_displacement_mean_m"],
            b_record["group_centroid_displacement_mean_m"],
        ),
        "added_road_length_delta_m": _delta(
            chosen_record["added_road_length_m"],
            b_record["added_road_length_m"],
        ),
        "candidate_equals_b": (
            chosen_record["signature"] is not None
            and chosen_record["signature"] == b_signature
        ),
    }

    return {
        "schema_id": SCHEMA_ID,
        "candidate_id": "C",
        "method": BOUNDED_SEARCH_NOTE,
        "decision": decision,
        "hard_ok": bool(chosen_record["hard_ok"]),
        "failed_hard_checks": list(
            chosen_record["failed_hard_checks"]
        ),
        "sidewalk_overlap_building_ids": list(
            chosen_record["sidewalk_overlap_building_ids"]
        ),
        "same_as_b": same_as_b,
        "selected_variant": selected_variant,
        "selected_record": chosen_record,
        "local_repair": local_repair_result,
        "local_repair_improved": repair_improved,
        "variant_plan": [
            {
                "variant": entry["variant"],
                "order": None
                if entry.get("order") is None
                else list(entry["order"]),
                "description": entry["description"],
            }
            for entry in plan
        ],
        "variant_table": variant_rows,
        "variant_count": len(variant_rows),
        "b_control": b_metrics,
        "b_signature": b_signature,
        "comparison_vs_b": comparison,
        "building_layout": chosen["building_layout"],
        "road_layout": chosen["road_layout"],
        "road_access": chosen["road_access"],
        "green_layout": chosen["green_layout"],
        "parking_layout": chosen["parking_layout"],
        "consistency": chosen["consistency"],
        "group_quality": chosen["group_quality"],
        "access_meta": chosen["access_meta"],
        "variants_evaluated": [row["variant"] for row in variant_rows],
        "elapsed_s": round(time.perf_counter() - started, 1),
        "non_claims": [
            BOUNDED_SEARCH_NOTE,
            "the selected variant is the hard-first lexicographic best of a "
            "fixed 12-variant set, not a globally optimal co-design",
            "no candidate-C output is a construction drawing or a "
            "designer-confirmed site plan",
        ],
    }

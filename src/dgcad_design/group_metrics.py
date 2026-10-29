"""Group-integrity and access-truth metrics for M4d-2 candidate comparison.

M4d-2 evaluates candidate A (access/connector rebuild) and candidate B
(group-anchored layout) against the M4d-1 baseline. This module supplies
**independent, geometry-derived** metrics so a generator cannot self-report its
own quality:

* :func:`group_integrity_metrics` - are the original 17 building groups still
  complete (ids kept, no duplicates), where did each group move, how did its
  bounding box and internal relative positions change, does it still occupy one
  row / adjacent rows or was it split, and what does its access relation look
  like;
* :func:`access_truth_metrics` - is the declared group access actually true in
  the geometry (serving road exists, terminal lies on that road, terminal is in
  the declared ``[3.4, 3.5] m`` band from the group footprint, terminal is
  inside the site boundary and outside every building footprint), independent of
  the generator's ``served`` flag;
* :func:`candidate_comparison_metrics` - an objective metric table for
  A / B / baseline with per-metric values, per-group values and numeric deltas.

The module deliberately does **not** score or rank candidates. Thresholds are
the declared contract values and are never widened: the terminal band is
``[3.4, 3.5] m`` with a float-noise epsilon only (``1e-9``), and a terminal must
sit on its serving road centreline within ``1e-6 m``.
"""
from __future__ import annotations

import math
from collections import Counter
from typing import Any, Mapping

from shapely.geometry import Point
from shapely.ops import unary_union

SCHEMA_ID = "dgcad.group-metrics.v0.1"

#: Declared group-access terminal band (m) from the access contract.  These are
#: not tunable metrics and are never widened to make a candidate pass.
TERMINAL_BAND_M = (3.4, 3.5)

#: A declared terminal must sit on its serving road centreline within this
#: tolerance (m); otherwise the relation is fabricated.
TERMINAL_ON_ROAD_TOLERANCE_M = 1e-6

#: Float-noise-only epsilon for the terminal band comparison (m).  A terminal at
#: 3.399 m fails; this epsilon does not widen the declared band.
BAND_EPSILON_M = 1e-9

#: Row ordinals differing by at most this are adjacent rows.
ROW_ADJACENCY_GAP = 1


def terminal_band_ok(distance_m: float | None) -> bool | None:
    """Whether ``distance_m`` lies in the declared terminal band.

    ``None`` stays ``None`` (not verifiable).  The band is the declared
    ``[3.4, 3.5] m`` with a ``1e-9 m`` float-noise epsilon only: 3.39 m and
    3.51 m fail, and the thresholds are not widened.
    """

    if distance_m is None:
        return None
    return (
        TERMINAL_BAND_M[0] - BAND_EPSILON_M
        <= distance_m
        <= TERMINAL_BAND_M[1] + BAND_EPSILON_M
    )


def _get(models: Any, key: str, default: Any = None) -> Any:
    if isinstance(models, Mapping):
        return models.get(key, default)
    return getattr(models, key, default)


def _building_map(building_layout: Any) -> dict[str, Any]:
    """First occurrence per building id (duplicates are counted separately)."""

    buildings: dict[str, Any] = {}
    for item in building_layout.buildings:
        buildings.setdefault(item.building_id, item)
    return buildings


def _footprints(
    ids: list[str], buildings: Mapping[str, Any]
) -> list[Any]:
    return [buildings[bid].footprint for bid in ids if bid in buildings]


def _bbox(footprints: list[Any]) -> list[float] | None:
    if not footprints:
        return None
    minx = min(item.bounds[0] for item in footprints)
    miny = min(item.bounds[1] for item in footprints)
    maxx = max(item.bounds[2] for item in footprints)
    maxy = max(item.bounds[3] for item in footprints)
    return [float(minx), float(miny), float(maxx), float(maxy)]


def _pair_angle_change_deg(
    source_a: tuple[float, float],
    source_b: tuple[float, float],
    design_a: tuple[float, float],
    design_b: tuple[float, float],
) -> float | None:
    source = (source_b[0] - source_a[0], source_b[1] - source_a[1])
    design = (design_b[0] - design_a[0], design_b[1] - design_a[1])
    source_len = math.hypot(*source)
    design_len = math.hypot(*design)
    if source_len <= 1e-12 or design_len <= 1e-12:
        return None
    cosine = (
        source[0] * design[0] + source[1] * design[1]
    ) / (source_len * design_len)
    cosine = max(-1.0, min(1.0, cosine))
    return math.degrees(math.acos(cosine))


def _relative_position(
    ids: list[str], buildings: Mapping[str, Any]
) -> dict[str, Any]:
    """Pairwise source-vs-design distance and orientation changes."""

    distance_changes: list[float] = []
    angle_changes: list[float] = []
    for index, first_id in enumerate(ids):
        for second_id in ids[index + 1 :]:
            first = buildings[first_id]
            second = buildings[second_id]
            source_distance = math.dist(
                first.source_centroid, second.source_centroid
            )
            design_distance = math.dist(
                first.design_centroid, second.design_centroid
            )
            distance_changes.append(abs(design_distance - source_distance))
            angle = _pair_angle_change_deg(
                first.source_centroid,
                second.source_centroid,
                first.design_centroid,
                second.design_centroid,
            )
            if angle is not None:
                angle_changes.append(angle)
    return {
        "pair_count": len(distance_changes),
        "max_distance_change_m": (
            max(distance_changes) if distance_changes else None
        ),
        "mean_distance_change_m": (
            sum(distance_changes) / len(distance_changes)
            if distance_changes
            else None
        ),
        "max_orientation_change_deg": (
            max(angle_changes) if angle_changes else None
        ),
        "mean_orientation_change_deg": (
            sum(angle_changes) / len(angle_changes)
            if angle_changes
            else None
        ),
    }


def _row_cohesion(row_indices: list[int | None]) -> dict[str, Any]:
    """Classify the design rows of one group (same row / adjacent / split)."""

    if any(index is None for index in row_indices):
        return {
            "row_indices": [],
            "row_span": None,
            "row_contiguous": None,
            "row_runs": None,
            "row_cohesion": "no_row_assignment",
            "split": None,
        }
    unique_rows = sorted({int(index) for index in row_indices})
    if not unique_rows:
        return {
            "row_indices": [],
            "row_span": None,
            "row_contiguous": None,
            "row_runs": None,
            "row_cohesion": "no_row_assignment",
            "split": None,
        }
    span = unique_rows[-1] - unique_rows[0]
    gaps = [
        second - first
        for first, second in zip(unique_rows, unique_rows[1:])
    ]
    contiguous = all(gap == ROW_ADJACENCY_GAP for gap in gaps)
    runs = 1 + sum(1 for gap in gaps if gap > ROW_ADJACENCY_GAP)
    if len(unique_rows) == 1:
        cohesion = "single_row"
    elif contiguous and span == 1:
        cohesion = "adjacent_rows"
    elif contiguous:
        cohesion = "contiguous_rows"
    else:
        cohesion = "non_contiguous_rows"
    return {
        "row_indices": unique_rows,
        "row_span": span,
        "row_contiguous": contiguous,
        "row_runs": runs,
        "row_cohesion": cohesion,
        "split": runs > 1,
    }


def _access_record(group_access: Any | None) -> dict[str, Any]:
    if group_access is None:
        return {"available": False}
    return {
        "available": True,
        "served": bool(group_access.served),
        "served_by_relation": bool(group_access.served_by_relation),
        "declared": bool(group_access.declared),
        "access_road_id": group_access.access_road_id,
        "terminal_xy": (
            None
            if group_access.terminal_xy is None
            else [float(group_access.terminal_xy[0]), float(group_access.terminal_xy[1])]
        ),
        "terminal_band_distance_m": group_access.terminal_centerline_distance_m,
        "terminal_corridor_edge_clearance_m": (
            group_access.terminal_corridor_edge_clearance_m
        ),
        "connector_length_m": group_access.route_crossing_length_m,
        "relation_error_codes": [
            error["code"] for error in group_access.relation_errors
        ],
    }


def group_integrity_metrics(
    intent: Any,
    building_layout: Any,
    road_access: Any,
) -> dict[str, Any]:
    """Completeness and geometry-drift metrics for the original 17 groups.

    Every number is computed from the layout geometry and the declared access
    relation; nothing is scored or ranked.  A group is ``preserved`` only when
    every original building id is present exactly once in the layout.
    """

    buildings_list = list(building_layout.buildings)
    buildings = _building_map(building_layout)
    counts = Counter(item.building_id for item in buildings_list)
    expected_ids = [
        building_id
        for group in intent.groups
        for building_id in group.building_ids
    ]
    expected_set = set(expected_ids)
    unexpected = sorted(set(counts) - expected_set)
    access_by_group = {
        item.group_id: item for item in road_access.groups
    }

    records: list[dict[str, Any]] = []
    for group in intent.groups:
        retained = [
            building_id
            for building_id in group.building_ids
            if counts.get(building_id, 0) >= 1
        ]
        missing = [
            building_id
            for building_id in group.building_ids
            if counts.get(building_id, 0) == 0
        ]
        duplicates = [
            building_id
            for building_id in group.building_ids
            if counts.get(building_id, 0) > 1
        ]
        design_footprints = _footprints(retained, buildings)
        design_bbox = _bbox(design_footprints)
        source_bbox = [float(value) for value in group.bbox]
        source_width = source_bbox[2] - source_bbox[0]
        source_depth = source_bbox[3] - source_bbox[1]
        source_area = source_width * source_depth
        design_width = (
            None if design_bbox is None else design_bbox[2] - design_bbox[0]
        )
        design_depth = (
            None if design_bbox is None else design_bbox[3] - design_bbox[1]
        )
        design_area = (
            None if design_bbox is None else design_width * design_depth
        )
        design_centroid = None
        if retained:
            design_centroid = [
                float(
                    sum(
                        buildings[building_id].design_centroid[0]
                        for building_id in retained
                    )
                    / len(retained)
                ),
                float(
                    sum(
                        buildings[building_id].design_centroid[1]
                        for building_id in retained
                    )
                    / len(retained)
                ),
            ]
        displacement = (
            None
            if design_centroid is None
            else float(
                math.dist(
                    group.centroid,
                    (design_centroid[0], design_centroid[1]),
                )
            )
        )
        relative = _relative_position(retained, buildings)
        row_info = _row_cohesion(
            [
                buildings[building_id].row_index
                for building_id in retained
            ]
        )
        records.append(
            {
                "group_id": group.group_id,
                "source_building_count": len(group.building_ids),
                "retained_building_ids": retained,
                "missing_building_ids": missing,
                "duplicate_building_ids": duplicates,
                "preserved": (
                    bool(group.building_ids)
                    and not missing
                    and not duplicates
                ),
                "source_centroid": [
                    float(group.centroid[0]),
                    float(group.centroid[1]),
                ],
                "design_centroid": design_centroid,
                "centroid_displacement_m": displacement,
                "source_bbox": source_bbox,
                "design_bbox": design_bbox,
                "bbox_area_change_ratio": (
                    None
                    if design_area is None or source_area <= 0
                    else float(design_area / source_area)
                ),
                "bbox_width_change_m": (
                    None if design_width is None else design_width - source_width
                ),
                "bbox_depth_change_m": (
                    None if design_depth is None else design_depth - source_depth
                ),
                "relative_position": relative,
                "row_indices": row_info["row_indices"],
                "row_span": row_info["row_span"],
                "row_contiguous": row_info["row_contiguous"],
                "row_runs": row_info["row_runs"],
                "row_cohesion": row_info["row_cohesion"],
                "split": row_info["split"],
                "access": _access_record(access_by_group.get(group.group_id)),
            }
        )

    displacements = [
        record["centroid_displacement_m"]
        for record in records
        if record["centroid_displacement_m"] is not None
    ]
    area_changes = [
        record["bbox_area_change_ratio"]
        for record in records
        if record["bbox_area_change_ratio"] is not None
    ]
    distance_changes = [
        record["relative_position"]["max_distance_change_m"]
        for record in records
        if record["relative_position"]["max_distance_change_m"] is not None
    ]
    angle_changes = [
        record["relative_position"]["max_orientation_change_deg"]
        for record in records
        if record["relative_position"]["max_orientation_change_deg"]
        is not None
    ]
    access_served = sum(
        1
        for record in records
        if record["access"].get("served_by_relation")
    )
    return {
        "schema_id": SCHEMA_ID,
        "group_count": len(records),
        "groups_preserved": sum(1 for record in records if record["preserved"]),
        "groups_with_missing_buildings": sum(
            1 for record in records if record["missing_building_ids"]
        ),
        "groups_with_duplicate_buildings": sum(
            1 for record in records if record["duplicate_building_ids"]
        ),
        "missing_building_count": sum(
            len(record["missing_building_ids"]) for record in records
        ),
        "duplicate_building_count": sum(
            len(record["duplicate_building_ids"]) for record in records
        ),
        "unexpected_building_ids": unexpected,
        "unexpected_building_count": len(unexpected),
        "groups_split": sum(
            1 for record in records if record["split"] is True
        ),
        "groups_row_unverified": sum(
            1
            for record in records
            if record["row_cohesion"] == "no_row_assignment"
        ),
        "max_centroid_displacement_m": (
            max(displacements) if displacements else None
        ),
        "mean_centroid_displacement_m": (
            sum(displacements) / len(displacements)
            if displacements
            else None
        ),
        "max_bbox_area_change_ratio": (
            max(area_changes) if area_changes else None
        ),
        "max_relative_distance_change_m": (
            max(distance_changes) if distance_changes else None
        ),
        "max_orientation_change_deg": (
            max(angle_changes) if angle_changes else None
        ),
        "access_served_count": access_served,
        "access_relation_error_count": len(road_access.relation_errors),
        "groups": records,
    }


def _serving_roads(road_layout: Any, group_id: str) -> list[Any]:
    roads = []
    for road in road_layout.roads:
        if group_id in tuple(getattr(road, "serves_group_ids", ()) or ()):
            roads.append(road)
    return roads


def access_truth_metrics(
    road_layout: Any,
    road_access: Any,
    site_boundary: Any | None = None,
    building_layout: Any | None = None,
) -> dict[str, Any]:
    """Geometry-derived access truth for every group.

    The generator's ``served`` flag is not trusted: for each group this function
    re-derives whether a serving road is declared, whether the declared terminal
    lies on that road (``1e-6 m`` tolerance), whether the terminal is in the
    declared ``[3.4, 3.5] m`` band from the group footprint, whether it lies
    inside the published site boundary and whether it is outside every building
    footprint.  ``field_geometry_disagreement_group_ids`` lists groups whose
    generator flag disagrees with the geometry.

    ``building_layout`` is optional for compatibility, but without it the band
    can only fall back to the recorded field distance (``band_source =
    "field"``) and the geometry verification is not claimed.
    """

    buildings = (
        _building_map(building_layout)
        if building_layout is not None
        else {}
    )
    records: list[dict[str, Any]] = []
    for group_access in road_access.groups:
        serving = _serving_roads(road_layout, group_access.group_id)
        serving_ids = sorted(road.edge_id for road in serving)
        terminal = (
            None
            if group_access.terminal_xy is None
            else Point(
                float(group_access.terminal_xy[0]),
                float(group_access.terminal_xy[1]),
            )
        )
        serving_road_present = bool(serving)
        access_road_declared = (
            group_access.access_road_id in serving_ids
            if group_access.access_road_id is not None
            else False
        )
        centerline_distance = None
        on_serving_road = None
        if terminal is not None and serving:
            centerline_distance = min(
                float(terminal.distance(road.centerline))
                for road in serving
            )
            on_serving_road = (
                centerline_distance <= TERMINAL_ON_ROAD_TOLERANCE_M
            )
        elif terminal is not None:
            on_serving_road = False

        band_distance = None
        band_source = "unavailable"
        if terminal is not None and building_layout is not None:
            footprints = _footprints(
                list(group_access.building_ids), buildings
            )
            if footprints:
                band_distance = float(
                    terminal.distance(unary_union(footprints))
                )
                band_source = "geometry"
        if band_distance is None and (
            group_access.terminal_centerline_distance_m is not None
        ):
            band_distance = float(
                group_access.terminal_centerline_distance_m
            )
            band_source = "field"
        band_ok = terminal_band_ok(band_distance)

        inside_boundary = (
            None
            if terminal is None or site_boundary is None
            else bool(site_boundary.covers(terminal))
        )
        inside_footprint_ids = (
            []
            if terminal is None or building_layout is None
            else [
                item.building_id
                for item in building_layout.buildings
                if item.footprint.intersects(terminal)
            ]
        )
        reasons: list[str] = []
        if not serving_road_present:
            reasons.append("no_declared_serving_road")
        if group_access.access_road_id is None:
            reasons.append("missing_access_road_id")
        elif not access_road_declared:
            reasons.append("access_road_id_not_declared")
        if terminal is None:
            reasons.append("missing_terminal")
        elif on_serving_road is not True:
            reasons.append("terminal_not_on_serving_road")
        if band_ok is not True:
            reasons.append(
                "terminal_band_not_verified"
                if band_ok is None
                else "terminal_distance_out_of_band"
            )
        if inside_boundary is False:
            reasons.append("terminal_outside_site_boundary")
        if inside_footprint_ids:
            reasons.append("terminal_inside_building_footprint")
        geometry_verified = not reasons
        field_served = bool(
            group_access.served_by_relation or group_access.served
        )
        records.append(
            {
                "group_id": group_access.group_id,
                "building_ids": list(group_access.building_ids),
                "field_served": field_served,
                "served_by_relation": bool(group_access.served_by_relation),
                "declared": bool(group_access.declared),
                "access_road_id": group_access.access_road_id,
                "serving_road_ids": serving_ids,
                "serving_road_present": serving_road_present,
                "access_road_declared": access_road_declared,
                "terminal_xy": (
                    None
                    if terminal is None
                    else [float(terminal.x), float(terminal.y)]
                ),
                "terminal_to_serving_road_m": centerline_distance,
                "terminal_on_serving_road": on_serving_road,
                "terminal_band_distance_m": band_distance,
                "terminal_band_source": band_source,
                "terminal_band_ok": band_ok,
                "terminal_inside_site_boundary": inside_boundary,
                "terminal_inside_footprint_ids": inside_footprint_ids,
                "geometry_verified_served": geometry_verified,
                "geometry_reasons": reasons,
                "field_geometry_disagreement": (
                    field_served != geometry_verified
                ),
            }
        )

    band_distances = [
        record["terminal_band_distance_m"]
        for record in records
        if record["terminal_band_distance_m"] is not None
    ]
    served_count = sum(1 for record in records if record["field_served"])
    geometry_verified_count = sum(
        1 for record in records if record["geometry_verified_served"]
    )
    dead_ends = tuple(road_access.dead_ends)
    return {
        "schema_id": SCHEMA_ID,
        "groups_total": len(records),
        "groups_served": served_count,
        "coverage": (served_count / len(records)) if records else 0.0,
        "groups_geometry_verified_served": geometry_verified_count,
        "geometry_verified_coverage": (
            geometry_verified_count / len(records) if records else 0.0
        ),
        "relation_error_count": len(road_access.relation_errors),
        "relation_error_codes": dict(
            Counter(
                error["code"] for error in road_access.relation_errors
            )
        ),
        "terminal_band_required_m": list(TERMINAL_BAND_M),
        "terminal_band_min_m": min(band_distances) if band_distances else None,
        "terminal_band_max_m": max(band_distances) if band_distances else None,
        "terminal_band_violation_group_ids": [
            record["group_id"]
            for record in records
            if record["terminal_band_ok"] is False
        ],
        "terminal_on_serving_road_violation_group_ids": [
            record["group_id"]
            for record in records
            if record["terminal_on_serving_road"] is False
        ],
        "terminal_outside_boundary_group_ids": [
            record["group_id"]
            for record in records
            if record["terminal_inside_site_boundary"] is False
        ],
        "terminal_inside_footprint_group_ids": [
            record["group_id"]
            for record in records
            if record["terminal_inside_footprint_ids"]
        ],
        "field_geometry_disagreement_group_ids": [
            record["group_id"]
            for record in records
            if record["field_geometry_disagreement"]
        ],
        "dead_ends": {
            "count": len(dead_ends),
            "unresolved": road_access.dead_ends_unresolved,
            "justified": road_access.dead_ends_justified,
            "resolved": road_access.dead_ends_resolved,
        },
        "site_boundary_provided": site_boundary is not None,
        "building_layout_provided": building_layout is not None,
        "groups": records,
    }


def _numeric_delta(current: Any, baseline: Any) -> float | None:
    if (
        isinstance(current, (int, float))
        and not isinstance(current, bool)
        and isinstance(baseline, (int, float))
        and not isinstance(baseline, bool)
    ):
        return float(current) - float(baseline)
    return None


def _candidate_summary(
    integrity: dict[str, Any], truth: dict[str, Any]
) -> dict[str, Any]:
    return {
        "group_count": integrity["group_count"],
        "groups_preserved": integrity["groups_preserved"],
        "groups_with_missing_buildings": integrity[
            "groups_with_missing_buildings"
        ],
        "groups_with_duplicate_buildings": integrity[
            "groups_with_duplicate_buildings"
        ],
        "missing_building_count": integrity["missing_building_count"],
        "duplicate_building_count": integrity["duplicate_building_count"],
        "unexpected_building_count": integrity["unexpected_building_count"],
        "groups_split": integrity["groups_split"],
        "groups_row_unverified": integrity["groups_row_unverified"],
        "max_centroid_displacement_m": integrity[
            "max_centroid_displacement_m"
        ],
        "mean_centroid_displacement_m": integrity[
            "mean_centroid_displacement_m"
        ],
        "max_bbox_area_change_ratio": integrity[
            "max_bbox_area_change_ratio"
        ],
        "max_relative_distance_change_m": integrity[
            "max_relative_distance_change_m"
        ],
        "max_orientation_change_deg": integrity[
            "max_orientation_change_deg"
        ],
        "access_served_count": integrity["access_served_count"],
        "access_relation_error_count": integrity[
            "access_relation_error_count"
        ],
        "coverage": truth["coverage"],
        "geometry_verified_coverage": truth["geometry_verified_coverage"],
        "terminal_band_min_m": truth["terminal_band_min_m"],
        "terminal_band_max_m": truth["terminal_band_max_m"],
        "terminal_band_violation_count": len(
            truth["terminal_band_violation_group_ids"]
        ),
        "terminal_on_serving_road_violation_count": len(
            truth["terminal_on_serving_road_violation_group_ids"]
        ),
        "field_geometry_disagreement_count": len(
            truth["field_geometry_disagreement_group_ids"]
        ),
        "dead_ends_unresolved": truth["dead_ends"]["unresolved"],
    }


def _candidate_payload(label: str, models: Any) -> dict[str, Any]:
    required = ("intent", "building_layout", "road_layout", "road_access")
    missing = [key for key in required if _get(models, key) is None]
    if missing:
        raise ValueError(
            f"candidate {label!r} model is missing required keys: {missing}"
        )
    intent = _get(models, "intent")
    building_layout = _get(models, "building_layout")
    road_layout = _get(models, "road_layout")
    road_access = _get(models, "road_access")
    site_boundary = _get(models, "site_boundary")
    integrity = group_integrity_metrics(
        intent, building_layout, road_access
    )
    truth = access_truth_metrics(
        road_layout, road_access, site_boundary, building_layout
    )
    return {
        "label": label,
        "group_integrity": integrity,
        "access_truth": truth,
        "summary": _candidate_summary(integrity, truth),
    }


def candidate_comparison_metrics(
    models_a: Any,
    models_b: Any,
    baseline: Any,
) -> dict[str, Any]:
    """Objective A / B / baseline metric table (no score, no ranking).

    Each model is a mapping (or attribute object) with at least ``intent``,
    ``building_layout``, ``road_layout`` and ``road_access``; ``site_boundary``
    is optional but required to verify terminal containment.  The result carries
    per-candidate metric families, a flat comparison table, a per-group table
    and numeric deltas against the baseline.  ``ranking`` and ``scoring`` are
    explicitly ``None``: choosing a candidate is the Lead's single-objective
    decision, not this module's.
    """

    payloads = {
        "A": _candidate_payload("A", models_a),
        "B": _candidate_payload("B", models_b),
        "baseline": _candidate_payload("baseline", baseline),
    }
    metric_names = sorted(
        set().union(
            *(payload["summary"].keys() for payload in payloads.values())
        )
    )
    comparison_table = [
        {
            "metric": name,
            **{
                label: payloads[label]["summary"].get(name)
                for label in ("A", "B", "baseline")
            },
        }
        for name in metric_names
    ]
    baseline_summary = payloads["baseline"]["summary"]
    deltas = {
        f"{label}_minus_baseline": {
            name: _numeric_delta(
                payloads[label]["summary"].get(name),
                baseline_summary.get(name),
            )
            for name in metric_names
        }
        for label in ("A", "B")
    }
    group_ids = sorted(
        {
            record["group_id"]
            for payload in payloads.values()
            for record in payload["group_integrity"]["groups"]
        }
    )
    per_group_table = []
    for group_id in group_ids:
        row: dict[str, Any] = {"group_id": group_id}
        for label in ("A", "B", "baseline"):
            integrity = next(
                (
                    record
                    for record in payloads[label]["group_integrity"]["groups"]
                    if record["group_id"] == group_id
                ),
                None,
            )
            truth = next(
                (
                    record
                    for record in payloads[label]["access_truth"]["groups"]
                    if record["group_id"] == group_id
                ),
                None,
            )
            row[label] = (
                None
                if integrity is None and truth is None
                else {
                    "preserved": (
                        None if integrity is None else integrity["preserved"]
                    ),
                    "missing_building_ids": (
                        None
                        if integrity is None
                        else integrity["missing_building_ids"]
                    ),
                    "duplicate_building_ids": (
                        None
                        if integrity is None
                        else integrity["duplicate_building_ids"]
                    ),
                    "centroid_displacement_m": (
                        None
                        if integrity is None
                        else integrity["centroid_displacement_m"]
                    ),
                    "row_cohesion": (
                        None if integrity is None else integrity["row_cohesion"]
                    ),
                    "split": (
                        None if integrity is None else integrity["split"]
                    ),
                    "served": (
                        None if integrity is None
                        else integrity["access"].get("served_by_relation")
                    ),
                    "geometry_verified_served": (
                        None
                        if truth is None
                        else truth["geometry_verified_served"]
                    ),
                    "terminal_band_distance_m": (
                        None
                        if truth is None
                        else truth["terminal_band_distance_m"]
                    ),
                    "terminal_band_ok": (
                        None if truth is None else truth["terminal_band_ok"]
                    ),
                }
            )
        per_group_table.append(row)
    return {
        "schema_id": SCHEMA_ID,
        "comparison_kind": "objective_metric_table_no_score_no_ranking",
        "candidates": payloads,
        "comparison_table": comparison_table,
        "per_group_table": per_group_table,
        "deltas": deltas,
        "ranking": None,
        "scoring": None,
        "note": (
            "objective metric table only: no score, no ranking and no "
            "candidate preference; the Lead applies the M4c-3a single-objective "
            "comparison framework"
        ),
    }

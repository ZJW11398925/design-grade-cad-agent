"""Inferred-group provenance and group-quality metrics (M4d-2a-1).

The 17 "groups" are **inferred**, not designer-confirmed: ``intent.py`` links
two buildings when their centroid distance is at most ``basis.group_distance_m``
(45 m) and the straight segment between them does not cross the 8 m main-road
buffer, then closes the relation with a Union-Find (single-linkage, transitive)
pass. A group can therefore contain buildings farther than 45 m apart when a
chain of pairwise links connects them, and a group is a spatial inference, not
a designed cluster.

This module reports that provenance and objective group-quality numbers:

* :func:`inferred_group_provenance` - how the groups were derived (45 m radius,
  8 m main-road buffer, single-linkage/Union-Find transitivity), the 17 groups,
  and the focus group's inferred members vs the members actually placed by the
  focus layout (G-01 infers 9 buildings; the focus layout places 7, leaving
  SK-BLD-0038 / SK-BLD-0061 at source positions);
* :func:`group_quality_metrics` - cohesion, fragmentation, relative-position
  preservation, shape distortion and displacement distributions for the whole
  site and for each group;
* :func:`compare_group_quality` - an A / B / baseline metric table with numeric
  deltas and **no score, no ranking, no pass/fail gate**.

Everything is pure geometry computed from the layout and the declared intent; no
new hard threshold is introduced. The only distance constant reused is the
declared inference radius (45 m), used to describe an isolated member - it is a
description, never a gate.
"""
from __future__ import annotations

import math
from typing import Any, Mapping

from shapely.geometry import MultiPoint

SCHEMA_ID = "dgcad.intent-metrics.v0.1"

#: The declared inference radius of ``intent.build_design_intent`` (basis
#: ``group_distance_m``).  Used only to describe isolated members, never as a
#: gate.
DEFAULT_GROUP_DISTANCE_M = 45.0

#: The main-road barrier buffer (m) hard-coded in ``intent.build_design_intent``
#: when deciding whether two buildings may be linked.
MAIN_ROAD_GROUP_BUFFER_M = 8.0

#: How the inferred groups are derived.
INFERRED_GROUP_METHOD = "single_linkage_union_find"

#: The source function that derives the groups.
INFERRED_GROUP_SOURCE = "dgcad_design.intent.build_design_intent"


def _get(models: Any, key: str, default: Any = None) -> Any:
    if isinstance(models, Mapping):
        return models.get(key, default)
    return getattr(models, key, default)


def _percentile(values: list[float], quantile: float) -> float | None:
    if not values:
        return None
    ordered = sorted(float(value) for value in values)
    if len(ordered) == 1:
        return ordered[0]
    position = quantile * (len(ordered) - 1)
    lower = int(math.floor(position))
    upper = min(lower + 1, len(ordered) - 1)
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def _stats(values: list[float]) -> dict[str, float | None]:
    if not values:
        return {
            "count": 0,
            "mean_m": None,
            "max_m": None,
            "p90_m": None,
            "median_m": None,
        }
    return {
        "count": len(values),
        "mean_m": sum(values) / len(values),
        "max_m": max(values),
        "p90_m": _percentile(values, 0.9),
        "median_m": _percentile(values, 0.5),
    }


def _bbox(footprints: list[Any]) -> list[float] | None:
    if not footprints:
        return None
    return [
        float(min(item.bounds[0] for item in footprints)),
        float(min(item.bounds[1] for item in footprints)),
        float(max(item.bounds[2] for item in footprints)),
        float(max(item.bounds[3] for item in footprints)),
    ]


def _bbox_area(bbox: list[float] | None) -> float | None:
    if bbox is None:
        return None
    return float((bbox[2] - bbox[0]) * (bbox[3] - bbox[1]))


def _hull_area(points: list[tuple[float, float]]) -> float:
    if len(points) < 3:
        return 0.0
    return float(MultiPoint(points).convex_hull.area)


def _angle_change_deg(
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


def _nearest_neighbours(
    points: dict[str, tuple[float, float]]
) -> dict[str, tuple[float, str] | None]:
    result: dict[str, tuple[float, str] | None] = {}
    for building_id, point in points.items():
        candidates = [
            (math.dist(point, other), other_id)
            for other_id, other in points.items()
            if other_id != building_id
        ]
        result[building_id] = min(candidates) if candidates else None
    return result


def _rows(row_indices: list[int | None]) -> dict[str, Any]:
    if any(index is None for index in row_indices):
        return {
            "row_indices": [],
            "row_span": None,
            "row_runs": None,
            "max_row_gap": None,
            "non_contiguous": None,
            "row_unverified": True,
            "row_cohesion": "no_row_assignment",
        }
    unique_rows = sorted({int(index) for index in row_indices})
    if not unique_rows:
        return {
            "row_indices": [],
            "row_span": None,
            "row_runs": None,
            "max_row_gap": None,
            "non_contiguous": None,
            "row_unverified": True,
            "row_cohesion": "no_row_assignment",
        }
    gaps = [
        second - first
        for first, second in zip(unique_rows, unique_rows[1:])
    ]
    runs = 1 + sum(1 for gap in gaps if gap > 1)
    span = unique_rows[-1] - unique_rows[0]
    if len(unique_rows) == 1:
        cohesion = "single_row"
    elif runs == 1 and span == 1:
        cohesion = "adjacent_rows"
    elif runs == 1:
        cohesion = "contiguous_rows"
    else:
        cohesion = "non_contiguous_rows"
    return {
        "row_indices": unique_rows,
        "row_span": span,
        "row_runs": runs,
        "max_row_gap": max(gaps) if gaps else None,
        "non_contiguous": runs > 1,
        "row_unverified": False,
        "row_cohesion": cohesion,
    }


def inferred_group_provenance(
    intent: Any,
    basis: Any | None = None,
    building_layout: Any | None = None,
) -> dict[str, Any]:
    """Provenance of the inferred 17 groups (not designer-confirmed).

    ``basis`` supplies the declared ``group_distance_m`` (defaults to 45.0);
    ``building_layout`` lets the focus-group block compare the inferred members
    with the members the focus layout actually placed.  Nothing here is scored.
    """

    group_distance = getattr(basis, "group_distance_m", None)
    if group_distance is None:
        group_distance = DEFAULT_GROUP_DISTANCE_M
    declared_provenance = dict(
        getattr(intent, "grouping_provenance", {}) or {}
    )
    matches_declaration = None
    if declared_provenance:
        matches_declaration = bool(
            declared_provenance.get("group_distance_m") == group_distance
            and declared_provenance.get("main_road_buffer_m")
            == MAIN_ROAD_GROUP_BUFFER_M
            and declared_provenance.get("transitive_merge") is True
        )
    buildings = (
        {item.building_id: item for item in building_layout.buildings}
        if building_layout is not None
        else {}
    )
    group_records = []
    for group in intent.groups:
        present = [
            building_id
            for building_id in group.building_ids
            if building_id in buildings
        ]
        missing = [
            building_id
            for building_id in group.building_ids
            if building_id not in buildings
        ]
        source_points = [
            buildings[building_id].source_centroid for building_id in present
        ]
        max_pairwise = 0.0
        for index, first in enumerate(source_points):
            for second in source_points[index + 1 :]:
                max_pairwise = max(max_pairwise, math.dist(first, second))
        group_records.append(
            {
                "group_id": group.group_id,
                "building_ids": list(group.building_ids),
                "inferred_building_count": len(group.building_ids),
                "present_building_count": len(present),
                "missing_building_ids": missing,
                "unit_count": group.unit_count,
                "households": group.households,
                "bbox": [float(value) for value in group.bbox],
                "centroid": [
                    float(group.centroid[0]),
                    float(group.centroid[1]),
                ],
                "main_road_distance_m": group.main_road_distance_m,
                # single-linkage transitivity can chain a group beyond the
                # 45 m radius; this exposes it instead of hiding it
                "max_pairwise_source_distance_m": (
                    max_pairwise if len(source_points) > 1 else 0.0
                ),
                "chain_ratio_to_group_distance": (
                    max_pairwise / float(group_distance)
                    if len(source_points) > 1 and group_distance
                    else None
                ),
            }
        )

    focus_record = next(
        (
            record
            for record in group_records
            if record["group_id"] == intent.focus_group_id
        ),
        None,
    )
    focus_block: dict[str, Any] = {
        "group_id": intent.focus_group_id,
        "inferred_building_ids": (
            [] if focus_record is None else focus_record["building_ids"]
        ),
        "inferred_building_count": (
            0 if focus_record is None else focus_record["inferred_building_count"]
        ),
    }
    if building_layout is not None and focus_record is not None:
        placed_ids = sorted(
            item.building_id for item in building_layout.focus_buildings
        )
        focus_block.update(
            {
                "focus_layout_building_ids": placed_ids,
                "focus_layout_building_count": len(placed_ids),
                "dropped_from_focus_layout": sorted(
                    set(focus_record["building_ids"]) - set(placed_ids)
                ),
                "note": (
                    "the focus layout row-places only the buildings it can fit; "
                    "the remaining inferred G-01 members stay at source "
                    "positions, so inferred membership and focus placement are "
                    "different sets"
                ),
            }
        )
    else:
        focus_block.update(
            {
                "focus_layout_building_ids": None,
                "focus_layout_building_count": None,
                "dropped_from_focus_layout": None,
            }
        )
    return {
        "schema_id": SCHEMA_ID,
        "groups_are_inferred": True,
        "designer_confirmed": False,
        "method": INFERRED_GROUP_METHOD,
        "source": INFERRED_GROUP_SOURCE,
        "group_distance_m": float(group_distance),
        "main_road_buffer_m": MAIN_ROAD_GROUP_BUFFER_M,
        "transitive": True,
        # cross-check against the provenance declared on the intent object (if
        # the intent publishes one); recomputed here, never trusted blindly
        "intent_declared_provenance": declared_provenance,
        "matches_intent_declaration": matches_declaration,
        "pair_rule": (
            "two buildings are linked when their centroid distance is at most "
            "group_distance_m AND the straight segment between the centroids "
            "does not cross the main-road buffer; links are then closed "
            "transitively by Union-Find (single linkage)"
        ),
        "chaining_note": (
            "single linkage means a group may contain members farther apart "
            "than group_distance_m when a chain of pairwise links connects "
            "them; see max_pairwise_source_distance_m per group"
        ),
        "group_count": len(group_records),
        "groups": group_records,
        "focus_group": focus_block,
    }


def group_quality_metrics(
    intent: Any,
    building_layout: Any,
) -> dict[str, Any]:
    """Cohesion, fragmentation, relative position, shape and displacement.

    Pure geometry: source positions come from each placed building's
    ``source_centroid``; design positions from ``design_centroid``.  Groups are
    the inferred intent groups, so a group can legitimately span several rows.
    No value is a pass/fail verdict; there is no score and no ranking.
    """

    buildings = {
        item.building_id: item for item in building_layout.buildings
    }
    records: list[dict[str, Any]] = []
    global_design_pairwise: list[float] = []
    global_source_pairwise: list[float] = []
    global_distance_changes: list[float] = []
    global_orientation_changes: list[float] = []
    nn_preserved = 0
    nn_total = 0
    isolated_total = 0
    for group in intent.groups:
        present_ids = [
            building_id
            for building_id in group.building_ids
            if building_id in buildings
        ]
        missing_ids = [
            building_id
            for building_id in group.building_ids
            if building_id not in buildings
        ]
        members = [buildings[building_id] for building_id in present_ids]
        source_points = {
            item.building_id: item.source_centroid for item in members
        }
        design_points = {
            item.building_id: item.design_centroid for item in members
        }
        source_distances: list[float] = []
        design_distances: list[float] = []
        distance_changes: list[float] = []
        orientation_changes: list[float] = []
        for index, first_id in enumerate(present_ids):
            for second_id in present_ids[index + 1 :]:
                source_distance = math.dist(
                    source_points[first_id], source_points[second_id]
                )
                design_distance = math.dist(
                    design_points[first_id], design_points[second_id]
                )
                source_distances.append(source_distance)
                design_distances.append(design_distance)
                distance_changes.append(
                    abs(design_distance - source_distance)
                )
                angle = _angle_change_deg(
                    source_points[first_id],
                    source_points[second_id],
                    design_points[first_id],
                    design_points[second_id],
                )
                if angle is not None:
                    orientation_changes.append(angle)
        global_design_pairwise.extend(design_distances)
        global_source_pairwise.extend(source_distances)
        global_distance_changes.extend(distance_changes)
        global_orientation_changes.extend(orientation_changes)

        source_nn = _nearest_neighbours(source_points)
        design_nn = _nearest_neighbours(design_points)
        preserved = 0
        compared = 0
        for building_id in present_ids:
            source_nearest = source_nn.get(building_id)
            design_nearest = design_nn.get(building_id)
            if source_nearest is None or design_nearest is None:
                continue
            compared += 1
            if source_nearest[1] == design_nearest[1]:
                preserved += 1
        nn_preserved += preserved
        nn_total += compared
        design_nn_distances = [
            item[0] for item in design_nn.values() if item is not None
        ]
        isolated = sum(
            1
            for distance in design_nn_distances
            if distance > float(DEFAULT_GROUP_DISTANCE_M)
        )
        isolated_total += isolated

        rows = _rows([item.row_index for item in members])
        footprints = [item.footprint for item in members]
        design_bbox = _bbox(footprints)
        design_bbox_area = _bbox_area(design_bbox)
        source_bbox = [float(value) for value in group.bbox]
        source_bbox_area = _bbox_area(source_bbox)
        footprint_area = float(sum(item.area for item in footprints))
        source_width = source_bbox[2] - source_bbox[0]
        source_depth = source_bbox[3] - source_bbox[1]
        design_width = (
            None
            if design_bbox is None
            else design_bbox[2] - design_bbox[0]
        )
        design_depth = (
            None
            if design_bbox is None
            else design_bbox[3] - design_bbox[1]
        )
        design_centroid = (
            None
            if not members
            else (
                float(
                    sum(item.design_centroid[0] for item in members)
                    / len(members)
                ),
                float(
                    sum(item.design_centroid[1] for item in members)
                    / len(members)
                ),
            )
        )
        centroid_displacement = (
            None
            if design_centroid is None
            else float(
                math.dist(group.centroid, design_centroid)
            )
        )
        member_displacements = [
            float(
                math.dist(item.source_centroid, item.design_centroid)
            )
            for item in members
        ]
        source_hull = _hull_area(list(source_points.values()))
        design_hull = _hull_area(list(design_points.values()))
        records.append(
            {
                "group_id": group.group_id,
                "inferred_member_count": len(group.building_ids),
                "present_member_ids": present_ids,
                "missing_member_ids": missing_ids,
                "cohesion": {
                    "pair_count": len(design_distances),
                    "mean_pairwise_distance_m": (
                        sum(design_distances) / len(design_distances)
                        if design_distances
                        else None
                    ),
                    "max_pairwise_distance_m": (
                        max(design_distances) if design_distances else None
                    ),
                    "p90_pairwise_distance_m": _percentile(
                        design_distances, 0.9
                    ),
                    "source_mean_pairwise_distance_m": (
                        sum(source_distances) / len(source_distances)
                        if source_distances
                        else None
                    ),
                    "source_max_pairwise_distance_m": (
                        max(source_distances) if source_distances else None
                    ),
                    "max_span_m": (
                        max(design_distances) if design_distances else None
                    ),
                    "nearest_neighbor_min_m": (
                        min(design_nn_distances)
                        if design_nn_distances
                        else None
                    ),
                    "nearest_neighbor_max_m": (
                        max(design_nn_distances)
                        if design_nn_distances
                        else None
                    ),
                    "isolated_member_count": isolated,
                },
                "fragmentation": {
                    "row_indices": rows["row_indices"],
                    "row_runs": rows["row_runs"],
                    "row_span": rows["row_span"],
                    "max_row_gap": rows["max_row_gap"],
                    "non_contiguous": rows["non_contiguous"],
                    "row_unverified": rows["row_unverified"],
                    "row_cohesion": rows["row_cohesion"],
                    "bbox_area_m2": design_bbox_area,
                    "bbox_fill_ratio": (
                        footprint_area / design_bbox_area
                        if design_bbox_area
                        else None
                    ),
                },
                "relative_position": {
                    "pair_count": len(distance_changes),
                    "distance_change_mean_m": (
                        sum(distance_changes) / len(distance_changes)
                        if distance_changes
                        else None
                    ),
                    "distance_change_max_m": (
                        max(distance_changes) if distance_changes else None
                    ),
                    "distance_change_p90_m": _percentile(
                        distance_changes, 0.9
                    ),
                    "orientation_change_mean_deg": (
                        sum(orientation_changes) / len(orientation_changes)
                        if orientation_changes
                        else None
                    ),
                    "orientation_change_max_deg": (
                        max(orientation_changes)
                        if orientation_changes
                        else None
                    ),
                    "orientation_change_p90_deg": _percentile(
                        orientation_changes, 0.9
                    ),
                    "nearest_neighbor_preservation_rate": (
                        preserved / compared if compared else None
                    ),
                },
                "shape_distortion": {
                    "source_bbox": source_bbox,
                    "design_bbox": design_bbox,
                    "bbox_area_ratio": (
                        design_bbox_area / source_bbox_area
                        if design_bbox_area is not None
                        and source_bbox_area
                        else None
                    ),
                    "source_aspect_ratio": (
                        source_width / source_depth
                        if source_depth
                        else None
                    ),
                    "design_aspect_ratio": (
                        design_width / design_depth
                        if design_width is not None
                        and design_depth
                        else None
                    ),
                    "aspect_ratio_change": (
                        (design_width / design_depth)
                        - (source_width / source_depth)
                        if design_width is not None
                        and design_depth
                        and source_depth
                        else None
                    ),
                    "source_centroid_hull_area_m2": source_hull,
                    "design_centroid_hull_area_m2": design_hull,
                    "centroid_hull_area_ratio": (
                        design_hull / source_hull if source_hull else None
                    ),
                    "centroid_displacement_m": centroid_displacement,
                },
                "displacement": _stats(member_displacements),
            }
        )

    building_displacements = [
        float(
            math.dist(item.source_centroid, item.design_centroid)
        )
        for item in building_layout.buildings
    ]
    non_contiguous_groups = sum(
        1
        for record in records
        if record["fragmentation"]["non_contiguous"] is True
    )
    row_unverified_groups = sum(
        1
        for record in records
        if record["fragmentation"]["row_unverified"] is True
    )
    row_runs = [
        record["fragmentation"]["row_runs"]
        for record in records
        if record["fragmentation"]["row_runs"] is not None
    ]
    row_gaps = [
        record["fragmentation"]["max_row_gap"]
        for record in records
        if record["fragmentation"]["max_row_gap"] is not None
    ]
    bbox_area_ratios = [
        record["shape_distortion"]["bbox_area_ratio"]
        for record in records
        if record["shape_distortion"]["bbox_area_ratio"] is not None
    ]
    aspect_changes = [
        abs(record["shape_distortion"]["aspect_ratio_change"])
        for record in records
        if record["shape_distortion"]["aspect_ratio_change"] is not None
    ]
    hull_ratios = [
        record["shape_distortion"]["centroid_hull_area_ratio"]
        for record in records
        if record["shape_distortion"]["centroid_hull_area_ratio"] is not None
    ]
    group_centroid_displacements = [
        record["shape_distortion"]["centroid_displacement_m"]
        for record in records
        if record["shape_distortion"]["centroid_displacement_m"] is not None
    ]
    group_spans = [
        record["cohesion"]["max_span_m"]
        for record in records
        if record["cohesion"]["max_span_m"] is not None
    ]
    group_mean_pairwise = [
        record["cohesion"]["mean_pairwise_distance_m"]
        for record in records
        if record["cohesion"]["mean_pairwise_distance_m"] is not None
    ]
    preservation_rates = [
        record["relative_position"]["nearest_neighbor_preservation_rate"]
        for record in records
        if record["relative_position"][
            "nearest_neighbor_preservation_rate"
        ]
        is not None
    ]
    return {
        "schema_id": SCHEMA_ID,
        "group_count": len(records),
        "building_count": len(building_layout.buildings),
        "cohesion": {
            "pair_count": len(global_design_pairwise),
            "mean_pairwise_distance_m": (
                sum(global_design_pairwise) / len(global_design_pairwise)
                if global_design_pairwise
                else None
            ),
            "max_pairwise_distance_m": (
                max(global_design_pairwise)
                if global_design_pairwise
                else None
            ),
            "p90_pairwise_distance_m": _percentile(
                global_design_pairwise, 0.9
            ),
            "source_mean_pairwise_distance_m": (
                sum(global_source_pairwise) / len(global_source_pairwise)
                if global_source_pairwise
                else None
            ),
            "source_max_pairwise_distance_m": (
                max(global_source_pairwise)
                if global_source_pairwise
                else None
            ),
            "group_mean_pairwise_distance_mean_m": (
                sum(group_mean_pairwise) / len(group_mean_pairwise)
                if group_mean_pairwise
                else None
            ),
            "group_mean_pairwise_distance_max_m": (
                max(group_mean_pairwise) if group_mean_pairwise else None
            ),
            "max_span_m": max(group_spans) if group_spans else None,
            "isolated_member_count": isolated_total,
            "groups_with_isolated_members": sum(
                1
                for record in records
                if record["cohesion"]["isolated_member_count"] > 0
            ),
        },
        "fragmentation": {
            "groups_with_row_runs_gt1": non_contiguous_groups,
            "groups_non_contiguous": non_contiguous_groups,
            "groups_row_unverified": row_unverified_groups,
            "total_row_runs": sum(row_runs) if row_runs else 0,
            "max_row_runs": max(row_runs) if row_runs else None,
            "max_row_gap": max(row_gaps) if row_gaps else None,
        },
        "relative_position": {
            "pair_count": len(global_distance_changes),
            "distance_change_mean_m": (
                sum(global_distance_changes) / len(global_distance_changes)
                if global_distance_changes
                else None
            ),
            "distance_change_max_m": (
                max(global_distance_changes)
                if global_distance_changes
                else None
            ),
            "distance_change_p90_m": _percentile(
                global_distance_changes, 0.9
            ),
            "orientation_change_mean_deg": (
                sum(global_orientation_changes)
                / len(global_orientation_changes)
                if global_orientation_changes
                else None
            ),
            "orientation_change_max_deg": (
                max(global_orientation_changes)
                if global_orientation_changes
                else None
            ),
            "orientation_change_p90_deg": _percentile(
                global_orientation_changes, 0.9
            ),
            "nearest_neighbor_preservation_rate": (
                nn_preserved / nn_total if nn_total else None
            ),
            "group_nearest_neighbor_preservation_rate_mean": (
                sum(preservation_rates) / len(preservation_rates)
                if preservation_rates
                else None
            ),
        },
        "shape_distortion": {
            "bbox_area_ratio_mean": (
                sum(bbox_area_ratios) / len(bbox_area_ratios)
                if bbox_area_ratios
                else None
            ),
            "bbox_area_ratio_max": (
                max(bbox_area_ratios) if bbox_area_ratios else None
            ),
            "aspect_ratio_change_mean": (
                sum(aspect_changes) / len(aspect_changes)
                if aspect_changes
                else None
            ),
            "aspect_ratio_change_max": (
                max(aspect_changes) if aspect_changes else None
            ),
            "centroid_hull_area_ratio_mean": (
                sum(hull_ratios) / len(hull_ratios) if hull_ratios else None
            ),
            "centroid_hull_area_ratio_max": (
                max(hull_ratios) if hull_ratios else None
            ),
            "group_centroid_displacement_mean_m": (
                sum(group_centroid_displacements)
                / len(group_centroid_displacements)
                if group_centroid_displacements
                else None
            ),
            "group_centroid_displacement_max_m": (
                max(group_centroid_displacements)
                if group_centroid_displacements
                else None
            ),
        },
        "displacement": _stats(building_displacements),
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


#: Aggregate metrics flattened into the comparison table.
COMPARISON_METRICS: tuple[tuple[str, str], ...] = (
    ("cohesion.mean_pairwise_distance_m", "cohesion"),
    ("cohesion.p90_pairwise_distance_m", "cohesion"),
    ("cohesion.max_span_m", "cohesion"),
    ("cohesion.isolated_member_count", "cohesion"),
    ("fragmentation.groups_non_contiguous", "fragmentation"),
    ("fragmentation.groups_row_unverified", "fragmentation"),
    ("fragmentation.total_row_runs", "fragmentation"),
    ("fragmentation.max_row_gap", "fragmentation"),
    ("relative_position.distance_change_mean_m", "relative_position"),
    ("relative_position.distance_change_max_m", "relative_position"),
    ("relative_position.distance_change_p90_m", "relative_position"),
    ("relative_position.orientation_change_mean_deg", "relative_position"),
    ("relative_position.orientation_change_max_deg", "relative_position"),
    (
        "relative_position.nearest_neighbor_preservation_rate",
        "relative_position",
    ),
    ("shape_distortion.bbox_area_ratio_mean", "shape_distortion"),
    ("shape_distortion.bbox_area_ratio_max", "shape_distortion"),
    ("shape_distortion.aspect_ratio_change_max", "shape_distortion"),
    (
        "shape_distortion.group_centroid_displacement_mean_m",
        "shape_distortion",
    ),
    (
        "shape_distortion.group_centroid_displacement_max_m",
        "shape_distortion",
    ),
    ("displacement.mean_m", "displacement"),
    ("displacement.max_m", "displacement"),
    ("displacement.p90_m", "displacement"),
    ("displacement.median_m", "displacement"),
)

#: Per-group metrics flattened into the per-group table.
PER_GROUP_METRICS: tuple[tuple[str, str], ...] = (
    ("cohesion.mean_pairwise_distance_m", "cohesion"),
    ("cohesion.max_span_m", "cohesion"),
    ("cohesion.isolated_member_count", "cohesion"),
    ("fragmentation.row_runs", "fragmentation"),
    ("fragmentation.non_contiguous", "fragmentation"),
    ("relative_position.distance_change_mean_m", "relative_position"),
    ("relative_position.distance_change_max_m", "relative_position"),
    (
        "relative_position.nearest_neighbor_preservation_rate",
        "relative_position",
    ),
    ("shape_distortion.bbox_area_ratio", "shape_distortion"),
    ("shape_distortion.centroid_displacement_m", "shape_distortion"),
    ("displacement.mean_m", "displacement"),
    ("displacement.max_m", "displacement"),
)


def _flatten(
    metrics: dict[str, Any], entries: tuple[tuple[str, str], ...]
) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for name, section in entries:
        key = name.split(".", 1)[1]
        flat[name] = metrics[section][key]
    return flat


def _quality_payload(label: str, models: Any) -> dict[str, Any]:
    intent = _get(models, "intent")
    building_layout = _get(models, "building_layout")
    if intent is None or building_layout is None:
        raise ValueError(
            f"candidate {label!r} model needs 'intent' and 'building_layout'"
        )
    metrics = group_quality_metrics(intent, building_layout)
    return {
        "label": label,
        "group_quality": metrics,
        "summary": _flatten(metrics, COMPARISON_METRICS),
    }


def compare_group_quality(
    baseline: Any,
    a: Any,
    b: Any,
) -> dict[str, Any]:
    """A / B / baseline group-quality table (no score, no ranking, no gate).

    Each model is a mapping (or attribute object) with ``intent`` and
    ``building_layout``.  The result carries the per-candidate metric families,
    a flat comparison table, a per-group table and numeric deltas against the
    baseline.  ``ranking``, ``scoring`` and ``pass_fail_gate`` are explicitly
    ``None``: these are descriptive metrics, not a decision rule.
    """

    payloads = {
        "baseline": _quality_payload("baseline", baseline),
        "A": _quality_payload("A", a),
        "B": _quality_payload("B", b),
    }
    metric_names = [name for name, _ in COMPARISON_METRICS]
    comparison_table = [
        {
            "metric": name,
            **{
                label: payloads[label]["summary"].get(name)
                for label in ("baseline", "A", "B")
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
            for record in payload["group_quality"]["groups"]
        }
    )
    per_group_table = []
    for group_id in group_ids:
        row: dict[str, Any] = {"group_id": group_id}
        for label in ("baseline", "A", "B"):
            record = next(
                (
                    item
                    for item in payloads[label]["group_quality"]["groups"]
                    if item["group_id"] == group_id
                ),
                None,
            )
            row[label] = (
                None if record is None else _flatten(record, PER_GROUP_METRICS)
            )
        per_group_table.append(row)
    return {
        "schema_id": SCHEMA_ID,
        "comparison_kind": "descriptive_group_quality_table_no_score_no_ranking",
        "groups_are_inferred": True,
        "candidates": payloads,
        "comparison_table": comparison_table,
        "per_group_table": per_group_table,
        "deltas": deltas,
        "ranking": None,
        "scoring": None,
        "pass_fail_gate": None,
        "note": (
            "descriptive group-quality metrics only: no score, no ranking and "
            "no pass/fail gate; the groups are inferred by intent.py, not "
            "designer-confirmed"
        ),
    }

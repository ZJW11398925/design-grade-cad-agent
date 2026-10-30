"""M4d-2a access semantics — four independent access layers (L1-L4).

The delivered ``ROAD_ACCESS_COVERAGE`` is a **group-level external access**
statement: a road declares that it serves a group and a terminal is validated
against that group's footprint union.  It is *not* a statement that all 55
buildings can be entered, that internal group roads exist, or that a car can
drive into a garage.  This module publishes the four layers separately and
never collapses them into one "coverage":

* **L1 — group external access** (``group_level_declared_access``): read-only
  re-derivation of the ``RoadAccessLayout`` group evidence (served / declared /
  relation errors / terminal band / serving road).  Scope is explicit:
  *group*, not building.
* **L2 — internal group roads** (``internal_group_roads``): not designed in the
  current pipeline; every group reports ``not_designed`` and the L1 connector is
  not used as a substitute.
* **L3 — single-building geometric frontage** (``frontage_geometry_only``): per
  building, the distance from its footprint to the nearest road **corridor
  edge**, whether that distance is inside the declared road frontage reserve
  (basis ``building_road_clearance_m`` + ``sidewalk_width_m``), and whether the
  straight frontage segment is obstructed by another building footprint / a
  designed green parcel.  This is geometry only: no entrance, door, gate,
  address or plot access is claimed.
* **L4 — underground garage driveway** (``driveway_deferred``): reuses the
  parking-entrance *proximity* evidence; proximity is not a designed driveway
  and no driveway geometry exists.

Every layer carries its own ``status`` / ``label`` / ``claims`` block.  Nothing
here mutates ``RoadAccessLayout``, ``RoadLayout`` or any declared threshold.
"""
from __future__ import annotations

import statistics
from typing import Any

from shapely.geometry import LineString
from shapely.ops import nearest_points

SCHEMA_ID = "dgcad.access-semantics.v0.1"

LAYER_ORDER = (
    "l1_group_external_access",
    "l2_internal_group_roads",
    "l3_building_frontage",
    "l4_garage_driveway",
)

#: Echo of the declared terminal band used by the access evidence.  This is a
#: read-only mirror for reporting; the access code and thresholds are untouched.
TERMINAL_BAND_M = (3.4, 3.5)

#: Tie-break epsilon for inclusive band comparisons (geometry, not a tolerance
#: widening: the band itself is unchanged).
BAND_EPSILON_M = 1e-9

#: A frontage segment must be intersected by an obstruction for more than this
#: length to count as blocked (touching a corner is not a blockage).
BLOCKING_MIN_LENGTH_M = 0.01

#: Designed-green classifications that can obstruct a frontage segment.
GREEN_OBSTRUCTION_CLASSIFICATIONS = ("cluster_green", "green_strip")

#: Per-building frontage bands, from the pavement edge outwards.  The reserve is
#: the declared basis clearance + sidewalk; bands beyond it are descriptive.
FRONTAGE_BAND_IN_SIDEWALK = "within_sidewalk_width"
FRONTAGE_BAND_IN_RESERVE = "within_frontage_reserve"
FRONTAGE_BAND_CLOSE_SETBACK = "close_setback_5_to_10_m"
FRONTAGE_BAND_FAR = "far_setback_over_10_m"


def _as_float(value: Any) -> float | None:
    if value is None:
        return None
    return float(value)


def _layer(
    layer_id: str,
    *,
    status: str,
    label: str,
    scope: str,
    summary: dict[str, Any],
    claims: dict[str, Any],
    detail_key: str,
    detail: list[dict[str, Any]],
    note: str,
) -> dict[str, Any]:
    return {
        "layer": layer_id,
        "status": status,
        "label": label,
        "scope": scope,
        "summary": summary,
        "claims": claims,
        detail_key: detail,
        "note": note,
    }


def _serving_road(road_layout: Any, group_id: str) -> Any | None:
    for road in road_layout.roads:
        if group_id in tuple(getattr(road, "serves_group_ids", ()) or ()):
            return road
    return None


def _terminal_band_ok(distance_m: float | None) -> bool | None:
    if distance_m is None:
        return None
    low, high = TERMINAL_BAND_M
    return bool(
        low - BAND_EPSILON_M <= float(distance_m) <= high + BAND_EPSILON_M
    )


def _frontage_band(distance_m: float, sidewalk_m: float, reserve_m: float) -> str:
    if distance_m <= sidewalk_m + BAND_EPSILON_M:
        return FRONTAGE_BAND_IN_SIDEWALK
    if distance_m <= reserve_m + BAND_EPSILON_M:
        return FRONTAGE_BAND_IN_RESERVE
    if distance_m <= reserve_m + 5.0 + BAND_EPSILON_M:
        return FRONTAGE_BAND_CLOSE_SETBACK
    return FRONTAGE_BAND_FAR


def _green_obstructions(green_layout: Any | None) -> list[tuple[str, Any]]:
    if green_layout is None:
        return []
    obstructions: list[tuple[str, Any]] = []
    for item in getattr(green_layout, "greens", ()) or ():
        classification = str(getattr(item, "classification", ""))
        if classification not in GREEN_OBSTRUCTION_CLASSIFICATIONS:
            continue
        geometry = getattr(item, "geometry", None)
        if geometry is None or geometry.is_empty:
            continue
        obstructions.append((str(getattr(item, "green_id", "?")), geometry))
    return obstructions


def _nearest_road(
    footprint: Any, road_layout: Any
) -> tuple[float | None, Any | None]:
    best_distance: float | None = None
    best_road: Any | None = None
    for road in road_layout.roads:
        corridor = getattr(road, "corridor", None)
        if corridor is None:
            continue
        distance = float(footprint.distance(corridor))
        if best_distance is None or distance < best_distance - BAND_EPSILON_M:
            best_distance = distance
            best_road = road
    return best_distance, best_road


def _blocking(
    footprint: Any,
    corridor: Any,
    other_footprints: list[Any],
    green_obstructions: list[tuple[str, Any]],
) -> tuple[list[str], list[str]]:
    point_building, point_corridor = nearest_points(footprint, corridor)
    segment = LineString([point_building, point_corridor])
    blocked_by_building: list[str] = []
    for other in other_footprints:
        intersection = segment.intersection(other.footprint)
        if float(getattr(intersection, "length", 0.0) or 0.0) > (
            BLOCKING_MIN_LENGTH_M
        ):
            blocked_by_building.append(other.building_id)
    blocked_by_green: list[str] = []
    for green_id, geometry in green_obstructions:
        intersection = segment.intersection(geometry)
        if float(getattr(intersection, "length", 0.0) or 0.0) > (
            BLOCKING_MIN_LENGTH_M
        ):
            blocked_by_green.append(green_id)
    return blocked_by_building, blocked_by_green


def _l1_group_external_access(
    intent: Any,
    road_layout: Any,
    road_access: Any,
) -> dict[str, Any]:
    access_by_group = {
        group.group_id: group
        for group in getattr(road_access, "groups", ()) or ()
    }
    detail: list[dict[str, Any]] = []
    for group in intent.groups:
        record = access_by_group.get(group.group_id)
        road = _serving_road(road_layout, group.group_id)
        terminal_distance = (
            None
            if record is None
            else _as_float(record.terminal_centerline_distance_m)
        )
        detail.append(
            {
                "group_id": group.group_id,
                "building_ids": list(group.building_ids),
                "declared": None if record is None else bool(record.declared),
                "served": None if record is None else bool(record.served),
                "served_by_relation": (
                    None
                    if record is None
                    else bool(record.served_by_relation)
                ),
                "serving_road_id": (
                    None if road is None else road.edge_id
                ),
                "serving_road_class": (
                    None if road is None else road.class_name
                ),
                "serving_road_width_m": (
                    None if road is None else float(road.width_m)
                ),
                "terminal_xy": (
                    None
                    if record is None or record.terminal_xy is None
                    else [
                        float(record.terminal_xy[0]),
                        float(record.terminal_xy[1]),
                    ]
                ),
                "terminal_distance_m": terminal_distance,
                "terminal_band_m": list(TERMINAL_BAND_M),
                "terminal_band_ok": _terminal_band_ok(terminal_distance),
                "relation_errors": [
                    dict(item)
                    for item in (
                        () if record is None else record.relation_errors
                    )
                ],
            }
        )
    groups_total = len(getattr(intent, "groups", ()) or ())
    groups_in_evidence = road_access.groups_total
    groups_served = sum(
        1 for record in detail if record["served"] is True
    )
    group_coverage = (
        None if groups_total == 0 else groups_served / groups_total
    )
    relation_errors = [
        dict(item) for item in road_access.relation_errors
    ]
    if groups_total == 0:
        status = "not_applicable"
    elif groups_served == groups_total and not relation_errors:
        status = "designed"
    elif groups_served == 0:
        status = "not_designed"
    else:
        status = "incomplete"
    summary: dict[str, Any] = {
        "groups_total": groups_total,
        "groups_in_access_evidence": groups_in_evidence,
        "groups_served": groups_served,
        "group_coverage": group_coverage,
        "road_access_coverage": road_access.road_access_coverage,
        "evidence_matches_road_access": bool(
            groups_in_evidence == groups_total
            and groups_served == road_access.groups_served
        ),
        "relation_error_count": len(relation_errors),
        "dead_ends_unresolved": road_access.dead_ends_unresolved,
        "terminal_band_m": list(TERMINAL_BAND_M),
    }
    if groups_in_evidence != groups_total:
        summary["groups_missing_from_access_evidence"] = (
            groups_total - groups_in_evidence
        )
    return _layer(
        "l1_group_external_access",
        status=status,
        label="group_level_declared_access",
        scope="group",
        summary=summary,
        claims={
            "access_scope": "group_level",
            "claims_single_building_access": False,
            "claims_internal_group_roads": False,
            "claims_garage_driveway": False,
        },
        detail_key="groups",
        detail=detail,
        note=(
            "a served group means one road declares serves_group_ids for the "
            "group and its terminal is validated against the group footprint "
            "union (3.4-3.5 m band, outside footprints, route crossing <= 0.1 "
            "m); it says nothing about any single building's entrance"
        ),
    )


def _l2_internal_group_roads(intent: Any) -> dict[str, Any]:
    detail = [
        {
            "group_id": group.group_id,
            "internal_road_count": 0,
            "designed_length_m": 0.0,
            "status": "not_designed",
        }
        for group in intent.groups
    ]
    return _layer(
        "l2_internal_group_roads",
        status="not_designed",
        label="internal_group_roads",
        scope="group",
        summary={
            "groups_total": len(detail),
            "groups_with_internal_roads": 0,
            "internal_road_length_m": 0.0,
        },
        claims={
            "internal_roads_designed": False,
            "l1_connector_is_not_internal_road": True,
        },
        detail_key="groups",
        detail=detail,
        note=(
            "the L1 connector ends at the group footprint ring; no road inside "
            "the group block is designed, so internal circulation is reported "
            "as not_designed and is not inferred from the L1 coverage"
        ),
    )


def _l3_building_frontage(
    intent: Any,
    basis: Any,
    building_layout: Any,
    road_layout: Any,
    green_layout: Any | None,
) -> dict[str, Any]:
    clearance_m = float(getattr(basis, "building_road_clearance_m", 3.0))
    sidewalk_m = float(getattr(basis, "sidewalk_width_m", 2.0))
    reserve_m = clearance_m + sidewalk_m
    buildings = list(building_layout.buildings)
    green_obstructions = _green_obstructions(green_layout)
    detail: list[dict[str, Any]] = []
    distances: list[float] = []
    for building in buildings:
        distance, road = _nearest_road(building.footprint, road_layout)
        if distance is not None:
            distances.append(distance)
        if road is None or distance is None:
            blocked_by_building: list[str] = []
            blocked_by_green: list[str] = []
        else:
            blocked_by_building, blocked_by_green = _blocking(
                building.footprint,
                road.corridor,
                [
                    item
                    for item in buildings
                    if item.building_id != building.building_id
                ],
                green_obstructions,
            )
        detail.append(
            {
                "building_id": building.building_id,
                "group_id": _group_of(intent, building.building_id),
                "distance_to_corridor_edge_m": distance,
                "nearest_road_id": None if road is None else road.edge_id,
                "nearest_road_class": (
                    None if road is None else road.class_name
                ),
                "nearest_road_width_m": (
                    None if road is None else float(road.width_m)
                ),
                "fronts_road": bool(
                    distance is not None
                    and distance <= reserve_m + BAND_EPSILON_M
                ),
                "frontage_band": (
                    None
                    if distance is None
                    else _frontage_band(distance, sidewalk_m, reserve_m)
                ),
                "sidewalk_adjacent": bool(
                    distance is not None
                    and distance <= sidewalk_m + BAND_EPSILON_M
                ),
                "blocked_by_building_ids": blocked_by_building,
                "blocked_by_green_ids": (
                    None if green_layout is None else blocked_by_green
                ),
            }
        )
    group_detail: list[dict[str, Any]] = []
    for group in intent.groups:
        ids = set(group.building_ids)
        rows = [row for row in detail if row["building_id"] in ids]
        group_distances = [
            row["distance_to_corridor_edge_m"]
            for row in rows
            if row["distance_to_corridor_edge_m"] is not None
        ]
        group_detail.append(
            {
                "group_id": group.group_id,
                "building_count": len(rows),
                "building_ids": [row["building_id"] for row in rows],
                "min_distance_m": (
                    None if not group_distances else min(group_distances)
                ),
                "max_distance_m": (
                    None if not group_distances else max(group_distances)
                ),
                "fronts_road_count": sum(
                    1 for row in rows if row["fronts_road"]
                ),
                "blocked_by_building_count": sum(
                    1 for row in rows if row["blocked_by_building_ids"]
                ),
                "blocked_by_green_count": (
                    None
                    if green_layout is None
                    else sum(
                        1 for row in rows if row["blocked_by_green_ids"]
                    )
                ),
            }
        )
    fronting = [row for row in detail if row["fronts_road"]]
    status = "not_applicable" if not detail else "geometry_measured"
    return _layer(
        "l3_building_frontage",
        status=status,
        label="frontage_geometry_only",
        scope="building",
        summary={
            "building_count": len(detail),
            "group_count": len(group_detail),
            "fronts_road_count": len(fronting),
            "sidewalk_adjacent_count": sum(
                1 for row in detail if row["sidewalk_adjacent"]
            ),
            "blocked_by_building_count": sum(
                1 for row in detail if row["blocked_by_building_ids"]
            ),
            "blocked_by_green_count": (
                None
                if green_layout is None
                else sum(1 for row in detail if row["blocked_by_green_ids"])
            ),
            "distance_stats_m": _distance_stats(distances),
            "frontage_reserve_m": reserve_m,
            "declared_clearance_m": clearance_m,
            "declared_sidewalk_width_m": sidewalk_m,
            "frontage_definition": (
                "fronts_road = footprint is within the declared frontage "
                "reserve of the nearest pavement edge (building_road_"
                "clearance_m + sidewalk_width_m); it is a geometric proximity, "
                "not an entrance, address or plot access"
            ),
        },
        claims={
            "geometry_only": True,
            "entrance_designed": False,
            "address_assigned": False,
            "plot_access_designed": False,
        },
        detail_key="buildings",
        detail=detail,
        note=(
            "L3 is measured for every building independently of L1: a group can "
            "be served (L1) while its buildings are still set back far from any "
            "road edge.  Distances are footprint-to-pavement-edge (corridor) "
            "polygon distances"
        ),
    ) | {"group_summary": group_detail}


def _distance_stats(values: list[float]) -> dict[str, Any]:
    if not values:
        return {
            "count": 0,
            "min": None,
            "median": None,
            "max": None,
            "mean": None,
        }
    ordered = sorted(values)
    return {
        "count": len(ordered),
        "min": ordered[0],
        "median": statistics.median(ordered),
        "max": ordered[-1],
        "mean": sum(ordered) / len(ordered),
    }


def _group_of(intent: Any, building_id: str) -> str | None:
    for group in intent.groups:
        if building_id in group.building_ids:
            return group.group_id
    return None


def _l4_garage_driveway(
    road_access: Any,
    parking_layout: Any,
) -> dict[str, Any]:
    entrances = list(getattr(road_access, "entrances", ()) or ())
    detail = [
        {
            "entrance_id": item.entrance_id,
            "status": item.status,
            "point_xy": [float(item.point_xy[0]), float(item.point_xy[1])],
            "nearest_road_id": item.nearest_road_id,
            "distance_m": _as_float(item.distance_m),
            "proximity_connected": bool(item.proximity_connected),
            "driveway_designed": bool(item.driveway_designed),
            "reason": item.reason,
        }
        for item in entrances
    ]
    parking_count = (
        None
        if parking_layout is None
        else len(getattr(parking_layout, "entrances", ()) or ())
    )
    driveway_designed = sum(
        1 for item in detail if item["driveway_designed"]
    )
    return _layer(
        "l4_garage_driveway",
        status="not_applicable" if not detail else "driveway_deferred",
        label="underground_garage_entrance_proximity",
        scope="entrance",
        summary={
            "entrance_count": len(detail),
            "proximity_connected_count": sum(
                1 for item in detail if item["proximity_connected"]
            ),
            "driveway_designed_count": driveway_designed,
            "parking_entrance_count": parking_count,
            "garage_layout": (
                None
                if parking_layout is None
                else getattr(parking_layout, "garage_layout", None)
            ),
        },
        claims={
            "entrance_proximity_only": True,
            "driveway_designed": False,
            "garage_layout_designed": False,
        },
        detail_key="entrances",
        detail=detail,
        note=(
            "the entrances only report proximity to the nearest road "
            "centreline (half road width + margin); no driveway geometry, ramp "
            "or garage layout is designed, so the driveway is deferred"
        ),
    )


def access_semantics_report(
    design_input: Any,
    intent: Any,
    building_layout: Any,
    road_layout: Any,
    road_access: Any,
    parking_layout: Any,
    *,
    basis: Any | None = None,
    green_layout: Any | None = None,
    candidate_id: str | None = None,
) -> dict[str, Any]:
    """Four independent access layers (L1-L4) for one site model.

    ``road_access`` is read only: the L1 block re-publishes its group evidence,
    the L4 block re-publishes its entrance proximity evidence.  No threshold is
    widened and no layer is merged into a single coverage number.  ``basis`` is
    the declared ``DesignBasis`` (the full-site model carries it; a bare
    ``DesignInput`` does not); when it is omitted the documented CASE-SKETCH-001
    fallback values are used and the L3 summary says so.  ``green_layout`` is
    optional; without it, green obstruction is reported as ``None`` (unknown),
    never as "not blocked".
    """
    if not hasattr(road_access, "road_access_coverage"):
        raise TypeError(
            "access_semantics_report expects a RoadAccessLayout with group "
            "evidence"
        )
    resolved_basis = basis
    if resolved_basis is None:
        resolved_basis = getattr(design_input, "basis", None)
    basis_source = "declared_design_basis"
    if resolved_basis is None:
        resolved_basis = _FallbackBasis()
        basis_source = "documented_case_default_constants"
    building_count = len(building_layout.buildings)
    layers = {
        "l1_group_external_access": _l1_group_external_access(
            intent, road_layout, road_access
        ),
        "l2_internal_group_roads": _l2_internal_group_roads(intent),
        "l3_building_frontage": _l3_building_frontage(
            intent,
            resolved_basis,
            building_layout,
            road_layout,
            green_layout,
        ),
        "l4_garage_driveway": _l4_garage_driveway(
            road_access, parking_layout
        ),
    }
    layers["l3_building_frontage"]["summary"]["basis_source"] = basis_source
    report: dict[str, Any] = {
        "schema_id": SCHEMA_ID,
        "case_id": getattr(design_input, "case_id", None),
        "building_count": building_count,
        "group_count": len(intent.groups),
        "layers": layers,
        "layer_order": list(LAYER_ORDER),
        "no_combined_coverage": True,
        "notes": [
            (
                "the four layers are independent evidence; there is no "
                "combined access coverage and none of them implies another"
            ),
            (
                "L1 is group-level declared external access; L2 is not "
                "designed; L3 is building-level geometry only (no "
                "entrance/address); L4 is entrance proximity only (no driveway)"
            ),
            (
                "nothing in this report changes RoadAccessLayout, RoadLayout "
                "or any declared threshold"
            ),
        ],
    }
    if candidate_id is not None:
        report["candidate_id"] = candidate_id
    return report


class _FallbackBasis:
    """Last-resort basis constants used only when no declared basis is supplied.

    These are the CASE-SKETCH-001 declared values (3.0 m clearance, 2.0 m
    sidewalk); a caller that passes the real ``DesignBasis`` (as the full-site
    model does) uses that basis instead and the L3 summary reports which source
    was used.
    """

    building_road_clearance_m = 3.0
    sidewalk_width_m = 2.0

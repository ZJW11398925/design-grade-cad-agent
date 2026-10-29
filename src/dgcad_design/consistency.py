from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.strtree import STRtree
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout, row_spacing_report
from .green import OPEN_SPACE_FILTERS, GreenLayout
from .input import DesignInput
from .intent import DesignIntent
from .parking import ParkingLayout
from .roads import RoadLayout
from .topology import topology_violations
from .access import RoadAccessLayout, build_road_access


#: Declared full-site row rhythm tolerance (metre).  The 20.0 m north-south
#: spacing is a declared design-basis constraint, not a measurement tolerance:
#: under- and over-spacing are both recorded as violations.
FULL_SITE_SPACING_TOLERANCE_M = 0.01
#: Containment tolerance for the boundary-setback check (metre).
BOUNDARY_SETBACK_TOLERANCE_M = 0.01
#: Maximum allowed pairwise building-footprint overlap area (m2).
BUILDING_OVERLAP_TOLERANCE_M2 = 0.01
#: Numerical-only epsilon for distance comparisons (metre).  This absorbs
#: floating-point noise only; it is never widened to manufacture a pass.
NUMERICAL_EPSILON_M = 1e-9
#: Numerical-only epsilon for the designed-green ratio comparison.
GREEN_RATIO_NUMERICAL_EPSILON = 1e-9



@dataclass(frozen=True)
class DesignConsistency:
    checks: tuple[dict[str, Any], ...]
    metrics: dict[str, Any]

    @property
    def hard_checks_ok(self) -> bool:
        return all(
            check["status"] != "fail"
            for check in self.checks
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "dgcad.design-consistency.v0.1",
            "ok": self.hard_checks_ok,
            "checks": list(self.checks),
            "metrics": self.metrics,
        }


def _design_subgroups(
    building_layout: BuildingLayout,
) -> dict[str, list[str]]:
    subgroups: dict[str, list[str]] = {}
    for row in building_layout.rows:
        subgroups.setdefault(row["subgroup_id"], []).extend(
            row["building_ids"]
        )
    return subgroups


def full_site_layout_state(
    building_layout: BuildingLayout,
) -> dict[str, Any]:
    """Whether ``building_layout`` is a full-site layout.

    The full-site layout contract is: every building (all 55) is placed and
    carries an integer ``row_index`` (global 1-based row ordinal, ascending y)
    and a ``subgroup_id``.  When the layout is still the focus layout, the 48
    non-focus buildings sit at their *source* positions with ``row_index is
    None``; those positions are source evidence, not a full-site design, so the
    full-site checks must stay deferred instead of passing or failing.
    """

    buildings = tuple(building_layout.buildings)
    missing = [
        item.building_id for item in buildings if item.row_index is None
    ]
    rows: dict[int, list[Any]] = {}
    for item in buildings:
        if item.row_index is not None:
            rows.setdefault(int(item.row_index), []).append(item)
    return {
        "ready": bool(buildings) and not missing,
        "building_count": len(buildings),
        "row_count": len(rows),
        "rows": {key: rows[key] for key in sorted(rows)},
        "missing_row_index_ids": missing,
    }


def full_site_ns_spacing_report(
    building_layout: BuildingLayout,
    basis: DesignBasis,
) -> dict[str, Any]:
    """North-south gap between adjacent global rows, all buildings.

    Adjacent rows are global row ordinals ``r`` and ``r + 1`` (the layout
    publishes ``row_index`` ascending y).  For every building pair with a
    positive x-overlap the vertical gap is ``north.miny - south.maxy``; the
    declared rhythm is ``basis.north_south_spacing_m`` and the tolerance is
    :data:`FULL_SITE_SPACING_TOLERANCE_M`.  Both under-spacing (a hard
    constraint violation) and over-spacing (a rhythm violation) are recorded;
    the tolerance is not widened to hide either.
    """

    state = full_site_layout_state(building_layout)
    required = float(basis.north_south_spacing_m)
    if not state["ready"]:
        return {
            "ready": False,
            "ok": None,
            "value": None,
            "required": required,
            "tolerance": FULL_SITE_SPACING_TOLERANCE_M,
            "row_count": state["row_count"],
            "missing_row_index_ids": state["missing_row_index_ids"],
            "row_pairs": [],
            "violations": [],
            "violation_count": 0,
            "min_gap_m": None,
        }
    rows = state["rows"]
    keys = sorted(rows)
    row_pairs: list[dict[str, Any]] = []
    violations: list[dict[str, Any]] = []
    for first_key, second_key in zip(keys, keys[1:]):
        ordinal_gap = second_key - first_key
        if ordinal_gap != 1:
            violations.append(
                {
                    "row_pair": [first_key, second_key],
                    "kind": "row_ordinal_gap",
                    "ordinal_gap": ordinal_gap,
                }
            )
        min_gap: float | None = None
        pair_count = 0
        for south in rows[first_key]:
            south_bounds = south.footprint.bounds
            for north in rows[second_key]:
                north_bounds = north.footprint.bounds
                x_overlap = min(south_bounds[2], north_bounds[2]) - max(
                    south_bounds[0], north_bounds[0]
                )
                if x_overlap <= 0:
                    continue
                pair_count += 1
                gap = north_bounds[1] - south_bounds[3]
                if min_gap is None or gap < min_gap:
                    min_gap = gap
                if gap < required - FULL_SITE_SPACING_TOLERANCE_M:
                    violations.append(
                        {
                            "row_pair": [first_key, second_key],
                            "a": south.building_id,
                            "b": north.building_id,
                            "gap_m": gap,
                            "kind": "under_spacing",
                        }
                    )
                elif gap > required + FULL_SITE_SPACING_TOLERANCE_M:
                    violations.append(
                        {
                            "row_pair": [first_key, second_key],
                            "a": south.building_id,
                            "b": north.building_id,
                            "gap_m": gap,
                            "kind": "over_spacing",
                        }
                    )
        row_pairs.append(
            {
                "row_pair": [first_key, second_key],
                "building_pair_count": pair_count,
                "min_gap_m": min_gap,
                "ordinal_gap": ordinal_gap,
            }
        )
    min_gap_all = min(
        (
            item["min_gap_m"]
            for item in row_pairs
            if item["min_gap_m"] is not None
        ),
        default=None,
    )
    return {
        "ready": True,
        "ok": not violations,
        "value": min_gap_all,
        "required": required,
        "tolerance": FULL_SITE_SPACING_TOLERANCE_M,
        "row_count": len(keys),
        "row_pairs": row_pairs,
        "violations": violations,
        "violation_count": len(violations),
        "min_gap_m": min_gap_all,
    }


def full_site_boundary_report(
    design_input: DesignInput,
    basis: DesignBasis,
    building_layout: BuildingLayout,
) -> dict[str, Any]:
    """Every full-site footprint inside ``site_boundary.buffer(-setback)``.

    Containment uses :data:`BOUNDARY_SETBACK_TOLERANCE_M` (0.01 m); each
    violating building records the area outside the setback boundary and its
    distance to that boundary.
    """

    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    tolerant = site_inner.buffer(BOUNDARY_SETBACK_TOLERANCE_M)
    outside: list[dict[str, Any]] = []
    for item in building_layout.buildings:
        if tolerant.covers(item.footprint):
            continue
        outside.append(
            {
                "building_id": item.building_id,
                "outside_area_m2": float(
                    item.footprint.difference(site_inner).area
                ),
                "distance_to_setback_boundary_m": float(
                    item.footprint.distance(site_inner)
                ),
            }
        )
    return {
        "ok": not outside,
        "value": [item["building_id"] for item in outside],
        "required": basis.boundary_setback_m,
        "tolerance": BOUNDARY_SETBACK_TOLERANCE_M,
        "outside": outside,
        "outside_count": len(outside),
    }


def full_site_building_overlap_report(
    building_layout: BuildingLayout,
) -> dict[str, Any]:
    """Pairwise footprint overlap area must be at most 0.01 m2."""

    buildings = tuple(building_layout.buildings)
    if len(buildings) < 2:
        return {
            "ok": True,
            "value": [],
            "pairs": [],
            "pair_count": 0,
            "max_overlap_m2": 0.0,
        }
    footprints = [item.footprint for item in buildings]
    tree = STRtree(footprints)
    pairs: list[dict[str, Any]] = []
    for index, footprint in enumerate(footprints):
        for candidate in tree.query(footprint):
            other = int(candidate)
            if other <= index:
                continue
            intersection = footprint.intersection(footprints[other])
            if intersection.is_empty:
                continue
            area = float(intersection.area)
            if area <= BUILDING_OVERLAP_TOLERANCE_M2:
                continue
            pairs.append(
                {
                    "a": buildings[index].building_id,
                    "b": buildings[other].building_id,
                    "overlap_area_m2": area,
                }
            )
    pairs.sort(key=lambda item: (-item["overlap_area_m2"], item["a"], item["b"]))
    return {
        "ok": not pairs,
        "value": pairs,
        "pairs": pairs,
        "pair_count": len(pairs),
        "max_overlap_m2": max(
            (item["overlap_area_m2"] for item in pairs), default=0.0
        ),
        "tolerance_m2": BUILDING_OVERLAP_TOLERANCE_M2,
    }


def full_site_road_clearance_report(
    basis: DesignBasis,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
) -> dict[str, Any]:
    """Every footprint at least ``building_road_clearance_m`` from road edges.

    The clearance is the polygon-to-corridor-union distance (0 when the
    footprint intersects a corridor).  A violating building records the
    measured clearance, the shortfall and the nearest design road.  The
    comparison epsilon is floating-point noise only
    (:data:`NUMERICAL_EPSILON_M`); the required clearance is never reduced.
    ``achievable_uniform_clearance_m`` is the largest uniform clearance the
    fixed road network currently supports (the measured minimum), published so
    an infeasible fixed-road state is reported honestly instead of passing.
    """

    required = float(basis.building_road_clearance_m)
    corridor = road_layout.corridor_union
    buildings = tuple(building_layout.buildings)
    violations: list[dict[str, Any]] = []
    min_clearance: float | None = None
    min_building_id: str | None = None
    for item in buildings:
        clearance = float(item.footprint.distance(corridor))
        if min_clearance is None or clearance < min_clearance:
            min_clearance = clearance
            min_building_id = item.building_id
        if clearance >= required - NUMERICAL_EPSILON_M:
            continue
        nearest_road = min(
            road_layout.roads,
            key=lambda road: item.footprint.distance(road.corridor),
        )
        violations.append(
            {
                "building_id": item.building_id,
                "clearance_m": clearance,
                "shortfall_m": required - clearance,
                "nearest_road_id": nearest_road.edge_id,
                "nearest_road_clearance_m": float(
                    item.footprint.distance(nearest_road.corridor)
                ),
            }
        )
    sidewalk_overlaps = [
        item.building_id
        for item in buildings
        if item.footprint.intersection(road_layout.sidewalk_union).area
        > BUILDING_OVERLAP_TOLERANCE_M2
    ]
    return {
        "ok": not violations,
        "value": min_clearance,
        "required": required,
        "epsilon_m": NUMERICAL_EPSILON_M,
        "min_clearance_m": min_clearance,
        "min_building_id": min_building_id,
        "violations": violations,
        "violation_count": len(violations),
        "achievable_uniform_clearance_m": min_clearance,
        "sidewalk_overlap_building_ids": sidewalk_overlaps,
        "road_count": len(road_layout.roads),
    }


def designed_green_report(
    green_layout: GreenLayout,
) -> dict[str, Any]:
    """Full-site designed-green ratio against the declared target.

    The account is ``green_layout.full_site_green`` (generated green parcels
    outside all buildings, road corridors and sidewalks).  A missing account is
    reported as not ready and must stay deferred, never pass.
    """

    full = getattr(green_layout, "full_site_green", None)
    target = float(green_layout.target_ratio)
    if full is None:
        return {
            "ready": False,
            "ok": None,
            "value": None,
            "required": target,
            "area_m2": None,
            "target_area_m2": None,
            "gap_m2": None,
            "gap_ratio": None,
            "parcel_count": 0,
            "residual_area_m2": None,
            "open_space_area_m2": None,
            "criteria": {},
        }
    return {
        "ready": True,
        "ok": full.ratio >= target - GREEN_RATIO_NUMERICAL_EPSILON,
        "value": full.ratio,
        "required": target,
        "area_m2": full.area_m2,
        "target_area_m2": full.target_area_m2,
        "gap_m2": full.gap_m2,
        "gap_ratio": full.gap_ratio,
        "parcel_count": len(full.parcels),
        "parcels": [
            {
                "green_id": item.green_id,
                "area_m2": item.area_m2,
                "bounds": list(item.geometry.bounds),
                "vertex_count": (
                    len(item.geometry.exterior.coords)
                    if item.geometry.geom_type == "Polygon"
                    else sum(
                        len(part.exterior.coords)
                        for part in item.geometry.geoms
                    )
                ),
                "label_anchor": list(item.label_anchor),
            }
            for item in full.parcels
        ],
        "parcels_geometry_ref": "green_layout.full_site_green.parcels[].geometry",
        "residual_area_m2": full.residual_area_m2,
        "open_space_area_m2": full.open_space_area_m2,
        "criteria": dict(full.criteria),
        "epsilon": GREEN_RATIO_NUMERICAL_EPSILON,
    }



def full_site_checks(
    design_input: DesignInput,
    basis: DesignBasis,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
) -> tuple[dict[str, Any], ...]:
    """The four full-site geometry checks, in contract order.

    Status rule: ``deferred`` while the full-site layout is not integrated (at
    least one building still has ``row_index is None``); otherwise ``pass`` /
    ``fail`` from the measured geometry.  A deferred check records its
    diagnostic measurement but is never a pass.
    """

    state = full_site_layout_state(building_layout)
    ready = bool(state["ready"])
    spacing = full_site_ns_spacing_report(building_layout, basis)
    boundary = full_site_boundary_report(
        design_input, basis, building_layout
    )
    overlap = full_site_building_overlap_report(building_layout)
    clearance = full_site_road_clearance_report(
        basis, building_layout, road_layout
    )
    layout_note = (
        "the full-site layout is not integrated yet: "
        f"{len(state['missing_row_index_ids'])} of "
        f"{state['building_count']} buildings carry no row_index (source "
        "positions are coarse context, not a full-site design), so this check "
        "is deferred; the measured value is recorded as a diagnostic only and "
        "is never a pass"
        if not ready
        else "full-site layout: every building carries a row_index"
    )

    def _status(report: dict[str, Any]) -> str:
        if not ready:
            return "deferred"
        return "pass" if report["ok"] else "fail"

    return (
        {
            "id": "FULL_SITE_BOUNDARY_SETBACK",
            "status": _status(boundary),
            "value": boundary["value"],
            "required": boundary["required"],
            "message": (
                "all 55 building footprints must lie inside the published site "
                "boundary reduced by the declared setback, tolerance "
                f"{BOUNDARY_SETBACK_TOLERANCE_M} m. {layout_note}"
            ),
            "detail": {
                "tolerance_m": boundary["tolerance"],
                "outside_count": boundary["outside_count"],
                "outside": boundary["outside"],
            },
        },
        {
            "id": "FULL_SITE_BUILDING_OVERLAP",
            "status": _status(overlap),
            "value": overlap["value"],
            "required": "none",
            "message": (
                "any two of the 55 building footprints may overlap by at most "
                f"{BUILDING_OVERLAP_TOLERANCE_M2} m2. {layout_note}"
            ),
            "detail": {
                "tolerance_m2": overlap["tolerance_m2"],
                "pair_count": overlap["pair_count"],
                "max_overlap_m2": overlap["max_overlap_m2"],
            },
        },
        {
            "id": "FULL_SITE_ROAD_CLEARANCE",
            "status": _status(clearance),
            "value": clearance["value"],
            "required": clearance["required"],
            "message": (
                "every building footprint must be at least "
                f"{clearance['required']} m from every road corridor edge "
                "(corridor union as designed; the roads are fixed). The "
                "minimum measured clearance and every violating building/road "
                "pair are recorded; the comparison epsilon is floating-point "
                f"noise only ({NUMERICAL_EPSILON_M} m) and the requirement is "
                f"never reduced. {layout_note}"
            ),
            "detail": {
                "min_clearance_m": clearance["min_clearance_m"],
                "min_building_id": clearance["min_building_id"],
                "achievable_uniform_clearance_m": clearance[
                    "achievable_uniform_clearance_m"
                ],
                "epsilon_m": clearance["epsilon_m"],
                "road_count": clearance["road_count"],
                "violation_count": clearance["violation_count"],
                "violations": clearance["violations"],
                "sidewalk_overlap_building_ids": clearance[
                    "sidewalk_overlap_building_ids"
                ],
            },
        },
        {
            "id": "FULL_SITE_NS_SPACING",
            "status": _status(spacing),
            "value": spacing["value"],
            "required": spacing["required"],
            "message": (
                "adjacent full-site rows (global row_index ascending y) must "
                f"keep {spacing['required']} m +/- "
                f"{FULL_SITE_SPACING_TOLERANCE_M} m between x-overlapping "
                "footprints; under-spacing and over-spacing are both recorded "
                "as violations. " + layout_note
            ),
            "detail": {
                "tolerance_m": spacing["tolerance"],
                "row_count": spacing["row_count"],
                "row_pairs": spacing["row_pairs"],
                "violation_count": spacing["violation_count"],
                "violations": spacing["violations"],
            },
        },
    )



def check_design(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    green_layout: GreenLayout,
    parking_layout: ParkingLayout,
    road_access: RoadAccessLayout | None = None,
) -> DesignConsistency:
    if road_access is None:
        road_access = build_road_access(
            building_layout, road_layout, intent, parking_layout, basis
        )
    site_area = design_input.site_area_m2
    staircases = design_input.staircase_count
    far = basis.far(site_area, staircases)
    households = basis.households(staircases)
    spaces = basis.parking_spaces(households)
    required_entrances = basis.required_entrances(spaces)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    focus = building_layout.focus_buildings
    focus_union = unary_union([item.footprint for item in focus])
    focus_area = focus_union.area
    site_inner_tolerant = site_inner.buffer(0.01)
    outside = [
        item.building_id
        for item in focus
        if not site_inner_tolerant.contains(item.footprint)
    ]
    overlap_pairs = []
    for index, first in enumerate(focus):
        for second in focus[index + 1 :]:
            if first.footprint.intersection(second.footprint).area > 0.01:
                overlap_pairs.append(
                    [first.building_id, second.building_id]
                )
    road_clear = road_layout.corridor_union.buffer(
        basis.building_road_clearance_m
    )
    road_conflicts = [
        item.building_id
        for item in focus
        if item.footprint.intersection(road_clear).area > 0.01
    ]
    spacing = row_spacing_report(building_layout, basis)
    green_designed = designed_green_report(green_layout)
    full_site_state = full_site_layout_state(building_layout)
    full_site_spacing = full_site_ns_spacing_report(building_layout, basis)
    full_site_boundary = full_site_boundary_report(
        design_input, basis, building_layout
    )
    full_site_overlap = full_site_building_overlap_report(building_layout)
    full_site_clearance = full_site_road_clearance_report(
        basis, building_layout, road_layout
    )
    noded_topology = road_layout.noded_topology
    topology_issues = topology_violations(noded_topology)
    components = noded_topology.component_count
    width_values = {
        road.width_m for road in road_layout.roads
    }
    allowed_widths = set(basis.road_widths.values())
    checks = (
        {
            "id": "FAR_ARITHMETIC_SCENARIO",
            "status": (
                "fail"
                if not (basis.far_min <= far <= basis.far_max)
                else "info"
            ),
            "value": far,
            "required": [basis.far_min, basis.far_max],
            "derived_from": "design_basis_arithmetic",
            "message": (
                "FAR under the current (all-unconfirmed) design-basis "
                "assumptions; a scenario calculation, not a spatial design "
                "result and not a pass. The final FAR verification is deferred"
            ),
        },
        {
            "id": "PARKING_REQUIREMENT_ARITHMETIC",
            "status": "info",
            "value": spaces / households if households else 0,
            "required": basis.parking_spaces_per_household,
            "derived_from": "design_basis_arithmetic",
            "message": (
                "required parking is households x declared ratio; this is an "
                "arithmetic requirement, not a parking layout verification"
            ),
        },
        {
            "id": "PARKING_ENTRANCE_COUNT",
            "status": (
                "fail"
                if len(parking_layout.entrances) < required_entrances
                else "info"
            ),
            "value": len(parking_layout.entrances),
            "required": required_entrances,
            "derived_from": "design_basis_arithmetic",
            "message": (
                "entrance COUNT under the declared 500-spaces-per-entrance "
                "assumption; this is not a parking capacity or layout check"
            ),
        },
        {
            "id": "PARKING_CAPACITY",
            "status": "deferred",
            "value": parking_layout.assumed_nominal_capacity_spaces,
            "required": spaces,
            "message": (
                "the recorded capacity is the Agent's assumed nominal capacity "
                "(2 proposed entrances x declared spaces/entrance), not a "
                "verified capacity; no garage layout exists, so capacity is "
                "deferred"
            ),
        },
        {
            "id": "PARKING_ENTRANCE_PROXIMITY",
            "status": "info",
            "value": (
                sum(
                    1
                    for item in road_access.entrances
                    if item.proximity_connected
                )
                / len(road_access.entrances)
                if road_access.entrances
                else 0.0
            ),
            "required": "entrances near a design road",
            "message": (
                "proximity only: the entrance point is a Point and lies within "
                "half the nearest road width + 1 m of its centreline. This is "
                "NOT a designed driveway; all entrances report "
                "driveway_designed: false"
            ),
            "detail": {
                "entrances": [
                    {
                        "entrance_id": item.entrance_id,
                        "status": item.status,
                        "proximity_connected": item.proximity_connected,
                        "driveway_designed": item.driveway_designed,
                        "distance_m": item.distance_m,
                        "nearest_road_id": item.nearest_road_id,
                        "reason": item.reason,
                    }
                    for item in road_access.entrances
                ],
                "not_near_road_ids": [
                    item.entrance_id
                    for item in road_access.entrances
                    if not item.proximity_connected
                ],
            },
        },
        {
            "id": "PARKING_DRIVEWAY_CONNECTION",
            "status": "deferred",
            "value": "not_designed",
            "required": "designed driveway connection per garage entrance",
            "message": (
                "no driveway, apron, ramp or parking-space geometry is designed; "
                "entrance proximity is not a driveway connection, so this stays "
                "deferred rather than passing on point distances"
            ),
        },
        {
            "id": "PARKING_LAYOUT",
            "status": "deferred",
            "value": parking_layout.garage_layout,
            "required": "designed garage layout",
            "message": (
                "no garage geometry, aisle geometry or parking-space layout is "
                "designed; entrance count is not parking provision"
            ),
        },
        {
            "id": "UNIT_COUNT_BASIS_INVARIANT",
            "status": (
                "fail"
                if sum(item.unit_count for item in building_layout.buildings)
                != staircases
                else "info"
            ),
            "value": sum(
                item.unit_count for item in building_layout.buildings
            ),
            "required": staircases,
            "derived_from": "design_basis_arithmetic",
            "message": (
                "55 buildings / 109 units is a basis count that still includes "
                "the 2 buildings (3 units) dropped from the detailed focus "
                "layout; it is not a focus-layout preservation result"
            ),
        },
        {
            "id": "FOCUS_NS_SPACING",
            "status": "pass" if spacing["ok"] else "fail",
            "value": spacing["min_gap_m"],
            "required": basis.north_south_spacing_m,
            "message": "focus-group north-south building gap",
        },
        {
            "id": "FOCUS_BOUNDARY_SETBACK",
            "status": "pass" if not outside else "fail",
            "value": outside,
            "required": basis.boundary_setback_m,
            "message": "focus buildings must stay inside the setback",
        },
        {
            "id": "FOCUS_BUILDING_OVERLAP",
            "status": "pass" if not overlap_pairs else "fail",
            "value": overlap_pairs,
            "required": "none",
            "message": "focus buildings must not overlap",
        },
        {
            "id": "FOCUS_ROAD_CLEARANCE",
            "status": "pass" if not road_conflicts else "fail",
            "value": road_conflicts,
            "required": basis.building_road_clearance_m,
            "message": "focus buildings must clear the schematic road corridor",
        },
        {
            "id": "ROAD_CONNECTIVITY",
            "status": "pass" if not topology_issues else "fail",
            "value": components,
            "required": 1,
            "message": (
                "the design road graph must be one connected component with "
                "explicit shared-vertex junctions"
            ),
            "detail": {
                "violations": [issue["code"] for issue in topology_issues],
                "max_endpoint_gap_m": noded_topology.max_endpoint_gap_m,
                "crossing_only_count": sum(
                    1
                    for item in noded_topology.connector_states
                    if item["state"] == "crossing_only"
                ),
            },
        },
        {
            "id": "ROAD_CORRIDOR_COVERAGE",
            "status": "info",
            "value": road_layout.corridor_union_pieces,
            "required": "coverage only",
            "message": (
                "corridor-union piece count is paved coverage, not centreline "
                "topology; it is published for continuity and does not gate"
            ),
        },
        {
            "id": "ROAD_ACCESS_COVERAGE",
            "status": (
                "pass"
                if not road_access.unserved_group_ids
                and not road_access.relation_errors
                else "fail"
            ),
            "value": road_access.road_access_coverage,
            "required": 1.0,
            "message": (
                "each group is served by its DECLARED access road "
                "(serves_group_ids), not by the nearest endpoint: the declared "
                "terminal centreline distance must be within [3.4, 3.5] m, lie "
                "outside every footprint and cross footprints by <= 0.1 m. A "
                "separate corridor-edge clearance is recorded per group; it is "
                "not the 3.0 m corridor setback"
            ),
            "detail": {
                "groups_total": road_access.groups_total,
                "groups_served": road_access.groups_served,
                "unserved_group_ids": list(road_access.unserved_group_ids),
                "relation_error_count": len(road_access.relation_errors),
                "relation_errors": [
                    dict(item) for item in road_access.relation_errors
                ],
                "group_access": [item.to_dict() for item in road_access.groups],
            },
        },
        {
            "id": "ROAD_BOUNDARY_CONTAINMENT",
            "status": (
                "pass"
                if road_layout.simplification.get("main_boundary_ok")
                else "fail"
            ),
            "value": road_layout.simplification.get(
                "main_boundary_margin_m"
            ),
            "required": 0.0,
            "message": (
                "every main-road corridor edge (centreline ± width/2) must lie "
                "inside the published site boundary; this is a geometric "
                "containment check, not a source-alignment claim. Repaired "
                "source overhangs are recorded per road, and the repaired "
                "MAIN-08 route is functional but not a polished alignment"
            ),
            "detail": {
                "boundary_ok": road_layout.simplification.get(
                    "main_boundary_ok"
                ),
                "boundary_margin_m": road_layout.simplification.get(
                    "main_boundary_margin_m"
                ),
                "repair_count": road_layout.simplification.get(
                    "main_boundary_repair_count"
                ),
                "repairs": [
                    dict(item)
                    for item in road_layout.main_boundary_repairs
                ],
            },
        },
        {
            "id": "MAIN_ROAD_BUILDING_OVERLAP",
            "status": (
                "pass"
                if road_access.main_road_overlap.get("status") == "resolved"
                and (
                    road_access.main_road_overlap.get("area_m2") or 0.0
                )
                <= 0.01
                else "fail"
            ),
            "value": road_access.main_road_overlap.get("area_m2"),
            "required": 0.01,
            "message": (
                "main roads were aligned to clear building footprints: the "
                "previously known 38.19 m2 conflict (MAIN-19/SK-BLD-0006, "
                "MAIN-08/SK-BLD-0038, MAIN-08/SK-BLD-0061) is resolved; the "
                "remaining overlap area must be <= 0.01 m2 for a pass"
            ),
            "detail": {
                "status": road_access.main_road_overlap.get("status"),
                "remaining_conflicts": road_access.main_road_overlap.get(
                    "conflicts", []
                ),
                "alignment_records": [
                    {
                        key: record[key]
                        for key in (
                            "road_id",
                            "alignment_strategy",
                            "max_displacement_m",
                            "overlap_before_m2",
                            "overlap_after_m2",
                            "constraint_satisfied",
                        )
                        if key in record
                    }
                    for record in road_access.main_alignment_records
                ],
                "overlap_before_m2": sum(
                    record.get("overlap_before_m2") or 0.0
                    for record in road_access.main_alignment_records
                ),
            },
        },
        {
            "id": "ROAD_ALIGNMENT_EVIDENCE",
            "status": "info",
            "value": len(road_access.main_alignment_records),
            "required": "recorded source-to-aligned main-road changes",
            "message": (
                "every adjusted main road publishes its source edges, alignment "
                "strategy, original and adjusted centreline, maximum "
                "displacement, vertex budget and overlap before/after; source "
                "edges remain evidence and no road id was silently deleted"
            ),
            "detail": {
                "record_count": len(road_access.main_alignment_records),
                "max_displacement_m": max(
                    (
                        record.get("max_displacement_m") or 0.0
                        for record in road_access.main_alignment_records
                    ),
                    default=0.0,
                ),
                "records": [
                    dict(record)
                    for record in road_access.main_alignment_records
                ],
            },
        },
        *full_site_checks(
            design_input,
            basis,
            building_layout,
            road_layout,
        ),
        {
            "id": "DEAD_END_JUSTIFICATION",
            "status": "info",
            "value": (
                f"{road_access.dead_ends_justified}/{len(road_access.dead_ends)}"
            ),
            "required": "classified dead ends",
            "message": (
                "all dead ends are classified, not all justified: a branch/"
                "access terminal within the access band of a group is a planned "
                "terminal, a main-road stub far from buildings is unfinished, "
                "anything else is unclassified. The unresolved items are "
                "reported below and are a deferred resolution item"
            ),
            "detail": {
                "classes": {
                    name: sum(
                        1
                        for item in road_access.dead_ends
                        if item.classification == name
                    )
                    for name in (
                        "group_terminal_justified",
                        "main_stub_unfinished",
                        "unclassified",
                    )
                },
                "unfinished_ids": [
                    item.node_id
                    for item in road_access.dead_ends
                    if item.classification == "main_stub_unfinished"
                ],
                "unclassified_ids": [
                    item.node_id
                    for item in road_access.dead_ends
                    if item.classification == "unclassified"
                ],
            },
        },
        {
            "id": "DEAD_END_RESOLUTION",
            "status": "pass" if road_access.dead_ends_unresolved == 0 else "fail",
            "value": f"{road_access.dead_ends_unresolved} unresolved",
            "required": 0,
            "message": (
                "all 7 previously unresolved dead ends are resolved: 2 trimmed "
                "to junctions, 3 bridged to another main road with explicit "
                "shared-vertex junctions and 2 justified as site-edge termini "
                "(MAIN-25 extended to the published site boundary); the 19 "
                "remaining dead ends are the 17 planned group-access terminals "
                "plus those 2 site-edge termini"
            ),
            "detail": {
                "unresolved_count": road_access.dead_ends_unresolved,
                "resolved_count": len(road_access.dead_end_resolutions),
                "resolutions": [
                    dict(item) for item in road_access.dead_end_resolutions
                ],
            },
        },
        {
            "id": "ROAD_WIDTH_ASSIGNMENT",
            "status": (
                "fail"
                if not width_values <= allowed_widths
                else "info"
            ),
            "value": sorted(width_values),
            "required": sorted(allowed_widths),
            "derived_from": "design_basis_assignment",
            "message": (
                "widths are assigned from the declared basis and checked for "
                "set membership; they are not an alignment or cross-section "
                "design result"
            ),
        },
        {
            "id": "CANDIDATE_OPEN_SPACE_RATIO",
            "status": "info",
            "value": green_layout.candidate_open_space_ratio,
            "required": "none",
            "message": (
                "candidate open-space share under the recorded filters "
                "(5 m boundary setback, 0.5 m obstacle buffer, supplementary "
                "polygons >= 100 m2, area = sum of recorded classifications); "
                "it is not designed green"
            ),
            "detail": {"filters": dict(OPEN_SPACE_FILTERS)},
        },
        {
            "id": "UNBUILT_RATIO",
            "status": "info",
            "value": green_layout.unbuilt_ratio,
            "required": "none",
            "message": (
                "geometric unbuilt-area ratio: area of "
                "(site boundary - 5 m setback) minus (buildings + road "
                "corridors + sidewalks), computed as a polygon-union area"
            ),
        },
        {
            "id": "DESIGNED_GREEN_RATIO",
            "status": "deferred",
            "value": green_layout.designed_green_ratio,
            "required": green_layout.target_ratio,
            "message": (
                "designed green is not designed yet. The full-site tiling "
                "account is an open-space allocation (parcels outside "
                "buildings/roads/sidewalks) and is not counted as designed "
                "green; the existing cluster/strip/supplementary designed "
                "green ratio is below the declared target 0.30, so the check "
                "stays deferred. Both accounts are reported in the detail "
                "(designed_green vs open_space_account); no green-quality, "
                "landscape or continuity claim is made"
            ),
            "detail": {
                "designed_green_area_m2": green_layout.designed_green_area_m2,
                "designed_green_ratio": green_layout.designed_green_ratio,
                "target_ratio": green_layout.target_ratio,
                "target_area_m2": (
                    green_layout.designed_green_area_m2
                    / green_layout.designed_green_ratio
                    * green_layout.target_ratio
                    if green_layout.designed_green_ratio
                    else None
                ),
                "open_space_account_area_m2": green_designed["area_m2"],
                "open_space_account_ratio": green_designed["value"],
                "open_space_account_parcel_count": green_designed[
                    "parcel_count"
                ],
                "open_space_account_criteria": green_designed["criteria"],
                "open_space_account_residual_m2": green_designed[
                    "residual_area_m2"
                ],
                "note": (
                    "the open-space tiling account is published as an "
                    "auxiliary diagnostic, not as designed green"
                ),
            },
        },
        {
            "id": "FAR_FINAL_VERIFICATION",
            "status": "deferred",
            "value": None,
            "required": "confirmed design basis + full-site design",
            "message": (
                "the final FAR check can only be answered after the 21 design-"
                "basis parameters are confirmed and the full-site design exists; "
                "all parameters are currently unconfirmed assumptions"
            ),
        },
    )
    metrics = {
        "site_area_m2": site_area,
        "basis_id": basis.basis_id,
        "staircase_count": staircases,
        "facility_count": design_input.facility_count,
        "households": households,
        "residential_gfa_m2": sum(
            item.gfa_m2
            for item in building_layout.buildings
            if not item.is_facility
        ),
        "facility_gfa_m2": sum(
            item.gfa_m2
            for item in building_layout.buildings
            if item.is_facility
        ),
        "total_gfa_m2": sum(
            item.gfa_m2 for item in building_layout.buildings
        ),
        "far": far,
        "parking_spaces": spaces,
        "parking_entrances": len(parking_layout.entrances),
        "parking_entrances_required": required_entrances,
        "parking_assumed_nominal_capacity": (
            parking_layout.assumed_nominal_capacity_spaces
        ),
        "parking_capacity_required": spaces,
        "garage_layout": parking_layout.garage_layout,
        "focus_building_count": len(focus),
        "focus_unit_count": sum(item.unit_count for item in focus),
        "focus_households": sum(item.households for item in focus),
        "focus_area_m2": focus_area,
        "focus_min_ns_gap_m": spacing["min_gap_m"],
        "full_site_layout_ready": full_site_state["ready"],
        "full_site_building_count": full_site_state["building_count"],
        "full_site_row_count": full_site_state["row_count"],
        "full_site_missing_row_index_count": len(
            full_site_state["missing_row_index_ids"]
        ),
        "full_site_min_ns_gap_m": full_site_spacing["min_gap_m"],
        "full_site_ns_spacing_violation_count": full_site_spacing[
            "violation_count"
        ],
        "full_site_outside_setback_ids": full_site_boundary["value"],
        "full_site_overlap_pair_count": full_site_overlap["pair_count"],
        "full_site_max_overlap_m2": full_site_overlap["max_overlap_m2"],
        "full_site_min_road_clearance_m": full_site_clearance[
            "min_clearance_m"
        ],
        "full_site_road_clearance_violation_count": full_site_clearance[
            "violation_count"
        ],
        "full_site_achievable_uniform_clearance_m": full_site_clearance[
            "achievable_uniform_clearance_m"
        ],
        "full_site_sidewalk_overlap_count": len(
            full_site_clearance["sidewalk_overlap_building_ids"]
        ),
        "full_site_designed_green_area_m2": green_designed["area_m2"],
        "full_site_designed_green_ratio": green_designed["value"],
        "full_site_designed_green_target_ratio": green_designed["required"],
        "full_site_designed_green_gap_m2": green_designed["gap_m2"],
        "full_site_designed_green_parcel_count": green_designed[
            "parcel_count"
        ],
        "full_site_green_residual_area_m2": green_designed[
            "residual_area_m2"
        ],
        "road_area_m2": road_layout.road_area_m2,
        "sidewalk_area_m2": road_layout.sidewalk_area_m2,
        "candidate_open_space_area_m2": (
            green_layout.candidate_open_space_area_m2
        ),
        "candidate_open_space_ratio": green_layout.candidate_open_space_ratio,
        "unbuilt_area_m2": green_layout.unbuilt_area_m2,
        "unbuilt_ratio": green_layout.unbuilt_ratio,
        "open_space_filters": dict(OPEN_SPACE_FILTERS),
        "designed_green_area_m2": green_layout.designed_green_area_m2,
        "designed_green_ratio": green_layout.designed_green_ratio,
        "green_target_ratio": green_layout.target_ratio,
        "road_noded_component_count": components,
        "corridor_union_pieces": road_layout.corridor_union_pieces,
        "road_topology": noded_topology.to_dict(),
        "road_count": len(road_layout.roads),
        "road_class_counts": {
            name: sum(
                1 for road in road_layout.roads if road.class_name == name
            )
            for name in ("main", "branch", "access")
        },
        "road_access_coverage": road_access.road_access_coverage,
        "road_groups_total": road_access.groups_total,
        "road_groups_served": road_access.groups_served,
        "road_groups_unserved": list(road_access.unserved_group_ids),
        "dead_end_justified_count": road_access.dead_ends_justified,
        "dead_end_unfinished_count": road_access.dead_ends_unfinished,
        "dead_end_unclassified_count": sum(
            1
            for item in road_access.dead_ends
            if item.classification == "unclassified"
        ),
        "entrance_count": len(road_access.entrances),
        "entrance_proximity_connected_count": sum(
            1
            for item in road_access.entrances
            if item.proximity_connected
        ),
        "entrance_driveway_designed_count": sum(
            1 for item in road_access.entrances if item.driveway_designed
        ),
        "road_relation_error_count": len(road_access.relation_errors),
        "main_boundary_ok": road_layout.simplification.get("main_boundary_ok"),
        "main_boundary_margin_m": road_layout.simplification.get(
            "main_boundary_margin_m"
        ),
        "main_boundary_repair_count": road_layout.simplification.get(
            "main_boundary_repair_count"
        ),
        "source_segment_map_road_count": len(
            road_layout.source_segment_map
        ),
        "dead_end_unresolved_count": road_access.dead_ends_unresolved,
        "dead_end_resolved_count": len(road_access.dead_end_resolutions),
        "main_road_building_overlap_m2": road_access.main_road_overlap.get(
            "area_m2"
        ),
        "main_road_building_overlap_before_m2": (
            road_layout.road_building_overlap_m2_main
        ),
        "main_road_overlap_before_records_m2": sum(
            record.get("overlap_before_m2") or 0.0
            for record in road_access.main_alignment_records
        ),
        "main_road_overlap_before_boundary_replaced_m2": max(
            0.0,
            road_layout.road_building_overlap_m2_main
            - sum(
                record.get("overlap_before_m2") or 0.0
                for record in road_access.main_alignment_records
            ),
        ),
        "main_road_building_overlap_status": road_access.main_road_overlap.get(
            "status"
        ),
        "main_alignment_adjusted_count": len(
            road_access.main_alignment_records
        ),
        "main_alignment_max_displacement_m": max(
            (
                record.get("max_displacement_m") or 0.0
                for record in road_access.main_alignment_records
            ),
            default=0.0,
        ),
        "road_building_overlap_m2_new_access": (
            road_layout.road_building_overlap_m2_new_access
        ),
        "road_building_overlap_m2_main_before": (
            road_layout.road_building_overlap_m2_main
        ),
        "road_building_overlap_m2_main_after": (
            road_layout.road_building_overlap_m2_main_after
        ),
        "road_building_overlap_m2_total": (
            road_layout.road_building_overlap_m2_total
        ),
        "junction_count": noded_topology.junction_count,
        "dead_end_count": noded_topology.dead_end_count,
        "explicit_junction_count": noded_topology.explicit_junction_count,
        "closed_ring_count": noded_topology.closed_ring_count,
        "max_endpoint_gap_m": noded_topology.max_endpoint_gap_m,
        "focus_group_id": intent.focus_group_id,
        "focus_subgroups": {
            subgroup_id: list(building_ids)
            for subgroup_id, building_ids in _design_subgroups(
                building_layout
            ).items()
        },
        "dropped_focus_building_ids": list(
            building_layout.dropped_focus_building_ids
        ),
    }
    return DesignConsistency(checks=checks, metrics=metrics)

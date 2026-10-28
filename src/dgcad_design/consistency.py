from __future__ import annotations

from dataclasses import dataclass
from typing import Any

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
            "id": "PARKING_ENTRANCE_CONNECTION",
            "status": "info",
            "value": (
                sum(1 for item in road_access.entrances if item.connected)
                / len(road_access.entrances)
                if road_access.entrances
                else 0.0
            ),
            "required": "connected entrances",
            "message": (
                "entrance points are Points (not polygon faces); connection is "
                "distance to the nearest road centreline <= half width + 1 m. "
                "Existing designer-marked garage faces have no designed driveway, "
                "so they are reported as not connected rather than assumed"
            ),
            "detail": {
                "entrances": [
                    {
                        "entrance_id": item.entrance_id,
                        "status": item.status,
                        "connected": item.connected,
                        "distance_m": item.distance_m,
                        "nearest_road_id": item.nearest_road_id,
                        "reason": item.reason,
                    }
                    for item in road_access.entrances
                ],
                "disconnected_ids": [
                    item.entrance_id
                    for item in road_access.entrances
                    if not item.connected
                ],
            },
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
            "status": "pass" if not road_access.unserved_group_ids else "fail",
            "value": road_access.road_access_coverage,
            "required": 1.0,
            "message": (
                "every group with buildings has an access road whose terminal "
                "is within clearance + 0.5 m of that group's buildings, lies "
                "outside the footprints and whose route crosses them by <= 0.1 "
                "m; this is a geometric access relation, not merely a "
                "connected-component count"
            ),
            "detail": {
                "groups_total": road_access.groups_total,
                "groups_served": road_access.groups_served,
                "unserved_group_ids": list(road_access.unserved_group_ids),
                "max_terminal_distance_m": max(
                    (
                        item.terminal_to_building_m
                        for item in road_access.groups
                        if item.terminal_to_building_m is not None
                    ),
                    default=None,
                ),
                "group_access": [item.to_dict() for item in road_access.groups],
            },
        },
        {
            "id": "DEAD_END_JUSTIFICATION",
            "status": "info",
            "value": (
                f"{road_access.dead_ends_justified}/{len(road_access.dead_ends)}"
            ),
            "required": "justified dead ends",
            "message": (
                "a branch/access terminal within clearance + 0.5 m of a group "
                "is a planned terminal; a main-road stub far from buildings is "
                "reported as an unfinished connection; anything else remains "
                "unclassified and must be reviewed"
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
            "required": basis.green_ratio_min,
            "message": (
                "only classified cluster/strip green counts; usable-area, "
                "continuity and green-quality criteria are not defined, so the "
                "declared target is not met under this definition yet"
            ),
        },
        {
            "id": "FULL_SITE_NS_SPACING",
            "status": "deferred",
            "value": None,
            "required": basis.north_south_spacing_m,
            "message": (
                "the full-site layout is a coarse context; the 20 m gap is "
                "enforced in the focus group and must be extended group by group"
            ),
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
        "entrance_connected_count": sum(
            1 for item in road_access.entrances if item.connected
        ),
        "road_building_overlap_m2_new_access": (
            road_layout.road_building_overlap_m2_new_access
        ),
        "road_building_overlap_m2_main": (
            road_layout.road_building_overlap_m2_main
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

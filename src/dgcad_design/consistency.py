from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout, row_spacing_report
from .green import GreenLayout
from .input import DesignInput
from .intent import DesignIntent
from .parking import ParkingLayout
from .roads import RoadLayout
from .topology import topology_violations


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
) -> DesignConsistency:
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
            "id": "FAR_RANGE",
            "status": "pass" if basis.far_min <= far <= basis.far_max else "fail",
            "value": far,
            "required": [basis.far_min, basis.far_max],
            "message": "site FAR must be inside the declared range",
        },
        {
            "id": "PARKING_MIN_ONE_PER_HOUSEHOLD",
            "status": "pass" if spaces >= households else "fail",
            "value": spaces / households if households else 0,
            "required": 1.0,
            "message": "at least one parking space per household",
        },
        {
            "id": "PARKING_ENTRANCES",
            "status": (
                "pass"
                if len(parking_layout.entrances) >= required_entrances
                else "fail"
            ),
            "value": len(parking_layout.entrances),
            "required": required_entrances,
            "message": "entrances must serve the declared spaces",
        },
        {
            "id": "UNIT_COUNT_PRESERVED",
            "status": (
                "pass"
                if sum(item.unit_count for item in building_layout.buildings)
                == staircases
                else "fail"
            ),
            "value": sum(
                item.unit_count for item in building_layout.buildings
            ),
            "required": staircases,
            "message": "standardized buildings preserve the inferred unit counts",
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
            "id": "ROAD_WIDTHS",
            "status": (
                "pass"
                if width_values <= allowed_widths
                else "fail"
            ),
            "value": sorted(width_values),
            "required": sorted(allowed_widths),
            "message": "each road width comes from the declared class",
        },
        {
            "id": "GREEN_RATIO",
            "status": (
                "pass"
                if green_layout.green_ratio >= basis.green_ratio_min
                else "fail"
            ),
            "value": green_layout.green_ratio,
            "required": basis.green_ratio_min,
            "message": "site green ratio",
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
    )
    metrics = {
        "site_area_m2": site_area,
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
        "focus_building_count": len(focus),
        "focus_unit_count": sum(item.unit_count for item in focus),
        "focus_households": sum(item.households for item in focus),
        "focus_area_m2": focus_area,
        "focus_min_ns_gap_m": spacing["min_gap_m"],
        "road_area_m2": road_layout.road_area_m2,
        "sidewalk_area_m2": road_layout.sidewalk_area_m2,
        "green_area_m2": green_layout.total_area_m2,
        "green_ratio": green_layout.green_ratio,
        "green_ratio_target": green_layout.target_ratio,
        "road_noded_component_count": components,
        "corridor_union_pieces": road_layout.corridor_union_pieces,
        "road_topology": noded_topology.to_dict(),
        "road_count": len(road_layout.roads),
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

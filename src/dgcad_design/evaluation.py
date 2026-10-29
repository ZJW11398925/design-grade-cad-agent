"""Independent multi-candidate design evaluator (M4c-3a).

This module never *generates* a candidate and never trusts a candidate's
self-reported metrics or verdicts. It re-computes the hard gates from the
candidate geometry (road corridors vs building footprints, noded topology, site
boundary, declared group access, capacity, basis fingerprint) and derives the
trade-off objectives by comparing the candidate against a fixed reference.

The comparison contract uses **independent, single-unit objectives** — never a
composite count+metre or length+displacement score:

1. hard gates first — a candidate that fails any hard gate is excluded;
2. among the surviving candidates the Pareto front over the eleven independent
   objectives is kept visible; auxiliary diagnostics (open-space/unbuilt/green
   deltas, space utilization, group-integrity details) never enter the front;
3. a recommendation is made only by explicit, ordered preferences, compared
   objective by objective, and every candidate gets a reason.

See ``contracts/design-candidates-v0.2.yaml`` for the machine-readable contract.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any, Iterable

from shapely.geometry import Point

from .access import (
    TERMINAL_DISTANCE_MAX_M,
    TERMINAL_DISTANCE_MIN_M,
    build_road_access,
    main_road_building_overlap,
)
from .basis import DesignBasis
from .buildings import BuildingLayout
from .green import GreenLayout
from .roads import RoadLayout
from .topology import topology_violations

SCHEMA_ID = "dgcad.design-candidates-evaluation.v0.2"

#: Hard gates, in contract order. Every one must be True for ``hard_pass``.
HARD_CHECKS = (
    "overlap_ok",
    "topology_ok",
    "boundary_ok",
    "access_ok",
    "capacity_ok",
    "basis_ok",
)

#: Soft evidence containers (kept for the evidence/README tables).
SOFT_METRICS = (
    "source_preservation",
    "road_change",
    "building_change",
    "group_integrity",
    "green_change",
    "space_utilization",
)

#: The eleven independent objectives used for the Pareto front and comparison.
#: Each objective is a single physical quantity with its own unit/direction; the
#: evaluator never adds objectives of different units together.
OBJECTIVES: dict[str, dict[str, str]] = {
    "building_count_change": {
        "direction": "minimize",
        "unit": "count",
        "definition": "change in building count versus the reference",
    },
    "building_displaced_count": {
        "direction": "minimize",
        "unit": "count",
        "definition": "number of building footprints displaced versus the reference",
    },
    "building_displacement_max_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "largest building footprint displacement versus the reference",
    },
    "main_length_delta_abs_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "absolute change of total main-road length",
    },
    "main_route_deviation_max_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "largest main-road centreline deviation versus the reference",
    },
    "branch_access_route_deviation_max_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "largest branch/access centreline deviation versus the reference",
    },
    "access_terminal_max_delta_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "largest declared access-terminal movement versus the reference",
    },
    "source_preservation_coverage": {
        "direction": "maximize",
        "unit": "ratio",
        "definition": "mean source-main-segment coverage by design main roads",
    },
    "source_preservation_distance_m": {
        "direction": "minimize",
        "unit": "m",
        "definition": "mean source-to-design segment distance",
    },
    "source_preservation_heading_deg": {
        "direction": "minimize",
        "unit": "deg",
        "definition": "mean absolute heading delta to the source main segments",
    },
    "green_designed_ratio_delta": {
        "direction": "maximize",
        "unit": "ratio",
        "definition": "change of the designed-green ratio versus the reference",
    },
}
OBJECTIVE_ORDER = tuple(OBJECTIVES)

#: Diagnostics that are reported but never enter the Pareto front.
AUXILIARY_METRICS = (
    "green_open_space_ratio_delta",
    "green_unbuilt_ratio_delta",
    "space_utilization",
    "group_integrity_detail",
    "road_added_vertices",
)

#: Historical, already-repaired boundary facts (pre-repair evidence). These are
#: archival: they describe past versions and are NOT current-candidate verdicts.
HISTORICAL_BOUNDARY_ARCHIVE = (
    {
        "road_id": "MAIN-19",
        "version": "M4c-2",
        "kind": "main_road_diversion",
        "max_displacement_m": 66.23545861756293,
        "outside_area_m2": None,
        "status": "resolved_by_main_alignment",
        "evidence": "docs/e2e/design-synthesis-001/design-summary.json"
        "#road_alignment.records[MAIN-19]",
    },
    {
        "road_id": "MAIN-08",
        "version": "M4c-3",
        "kind": "source_corridor_boundary_repair",
        "max_displacement_m": 44.1586496117478,
        "outside_area_m2": 341.6908310814502,
        "status": "resolved_by_boundary_repair",
        "evidence": "docs/e2e/design-synthesis-001/design-summary.json"
        "#road_alignment.boundary_repairs[MAIN-08]",
    },
    {
        "road_id": "MAIN-16",
        "version": "M4c-3",
        "kind": "source_corridor_boundary_repair",
        "max_displacement_m": 1.7423799066510406,
        "outside_area_m2": 2.417804558565924,
        "status": "resolved_by_boundary_repair",
        "evidence": "docs/e2e/design-synthesis-001/design-summary.json"
        "#road_alignment.boundary_repairs[MAIN-16]",
    },
    {
        "road_id": "MAIN-18",
        "version": "M4c-3",
        "kind": "source_corridor_boundary_repair",
        "max_displacement_m": 2.4984359701101364,
        "outside_area_m2": 8.290901115044374,
        "status": "resolved_by_boundary_repair",
        "evidence": "docs/e2e/design-synthesis-001/design-summary.json"
        "#road_alignment.boundary_repairs[MAIN-18]",
    },
)

#: Current-candidate boundary violations are computed per evaluation and are not
#: a pre-set list; this constant stays empty on purpose.
KNOWN_BOUNDARY_VIOLATIONS: tuple[dict[str, Any], ...] = ()

#: Hard overlap budget for the main-road corridor against any building footprint.
HARD_OVERLAP_MAX_M2 = 0.01

#: Tolerance for corridor-edge containment inside the published site boundary.
BOUNDARY_TOLERANCE_M = 0.01

#: Displacement below this is treated as "not moved".
DISPLACEMENT_EPSILON_M = 1e-6

#: Default preference order over the independent objectives (building
#: preservation and access stability first, then road disruption, then fidelity
#: to the source sketch, then green benefit). Mixed-unit scores are not allowed.
DEFAULT_PRIORITIES = (
    {"objective": "building_count_change", "direction": "minimize"},
    {"objective": "building_displaced_count", "direction": "minimize"},
    {"objective": "building_displacement_max_m", "direction": "minimize"},
    {"objective": "access_terminal_max_delta_m", "direction": "minimize"},
    {"objective": "main_route_deviation_max_m", "direction": "minimize"},
    {"objective": "main_length_delta_abs_m", "direction": "minimize"},
    {"objective": "source_preservation_coverage", "direction": "maximize"},
    {"objective": "green_designed_ratio_delta", "direction": "maximize"},
)

#: Human-readable rationale for the default preference order.
DEFAULT_PRIORITY_RATIONALE = (
    "building count loss is scored first because it is irreversible and violates "
    "the design basis; the number of displaced buildings is second because moving "
    "buildings is a discrete design decision; the largest building displacement is "
    "third because it measures how far those buildings move; access-terminal "
    "movement is fourth because declared group access must stay stable; main-road "
    "route deviation and length change follow because road geometry is less "
    "consequential than buildings; source preservation and designed-green gain "
    "are last because they are fidelity/quality signals, not survival signals. "
    "Each step compares one single-unit objective; no composite score exists."
)


def basis_fingerprint(basis: DesignBasis) -> str:
    """Canonical sha256 of the full basis payload (basis binding for candidates)."""
    payload = basis.to_dict() if callable(getattr(basis, "to_dict", None)) else basis
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


# --------------------------------------------------------------------- helpers
def _main_roads(road_layout: RoadLayout) -> list[Any]:
    return [road for road in road_layout.roads if road.class_name == "main"]


def _total_length(road_layout: RoadLayout) -> float:
    return float(sum(road.centerline.length for road in road_layout.roads))


def _total_main_length(road_layout: RoadLayout) -> float:
    return float(sum(road.centerline.length for road in _main_roads(road_layout)))


def _vertex_count(road_layout: RoadLayout) -> int:
    return sum(len(list(road.centerline.coords)) for road in road_layout.roads)


def _road_overlap_total(
    building_layout: BuildingLayout, road_layout: RoadLayout
) -> float:
    total = 0.0
    for road in road_layout.roads:
        corridor = getattr(road, "corridor", None)
        if corridor is None:
            continue
        for building in building_layout.buildings:
            total += float(corridor.intersection(building.footprint).area)
    return total


def _penetration_depth(outside: Any, site_boundary: Any) -> float:
    """Maximum distance from the outside piece to the site boundary (metres)."""
    if outside is None or outside.is_empty:
        return 0.0
    points: list[tuple[float, float]] = []
    geometries = getattr(outside, "geoms", (outside,))
    for geometry in geometries:
        if geometry.is_empty:
            continue
        exterior = getattr(geometry, "exterior", None)
        if exterior is None:
            continue
        points.extend(list(exterior.coords))
    if not points:
        return 0.0
    return max(
        float(site_boundary.exterior.distance(Point(x_value, y_value)))
        for x_value, y_value in points
    )


def _boundary_metrics(
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    site_boundary: Any | None,
) -> dict[str, Any]:
    """Boundary containment with corridor-edge truth and centreline diagnosis.

    The hard constraint is about the **main-road corridor edge** (centreline plus
    half width): the whole corridor must lie inside the published site boundary
    with a tolerance of at most ``BOUNDARY_TOLERANCE_M``. The centreline violation
    is computed separately so a corridor-overhang is distinguishable from a road
    that is itself routed outside.

    * ``boundary_violation_m`` = how far the corridor sticks out of the boundary
      (0.0 when contained); ``boundary_margin_m`` = signed distance of the
      corridor edge to the boundary while contained (negative = violation);
    * ``centerline_violation_m`` = distance of the worst centreline vertex outside
      the boundary (0.0 when the centreline is inside).

    The same definition is used for every candidate and for the reference/base.
    """
    if site_boundary is None:
        return {
            "ok": False,
            "reason": "site boundary not supplied",
            "boundary_violation_m": None,
            "boundary_margin_m": None,
            "centerline_violation_m": None,
        }
    allowed = site_boundary.buffer(BOUNDARY_TOLERANCE_M)
    allowed_no_tolerance = site_boundary
    corridor_records: list[dict[str, Any]] = []
    worst_corridor = 0.0
    worst_centerline = 0.0
    for road in road_layout.roads:
        corridor = getattr(road, "corridor", None)
        if corridor is None:
            continue
        outside = corridor.difference(allowed_no_tolerance)
        violation = _penetration_depth(outside, site_boundary)
        centerline_outside: list[float] = []
        for x_value, y_value in road.centerline.coords:
            point = Point(float(x_value), float(y_value))
            if not allowed_no_tolerance.covers(point):
                centerline_outside.append(
                    float(site_boundary.exterior.distance(point))
                )
        centerline_violation = max(centerline_outside) if centerline_outside else 0.0
        if road.class_name == "main":
            worst_corridor = max(worst_corridor, violation)
            worst_centerline = max(worst_centerline, centerline_violation)
        corridor_records.append(
            {
                "road_id": road.edge_id,
                "road_class": road.class_name,
                "corridor_violation_m": violation,
                "centerline_violation_m": centerline_violation,
                "corridor_margin_m": (
                    -violation
                    if violation > 0
                    else float(site_boundary.exterior.distance(corridor))
                ),
            }
        )
    outside_buildings = [
        building.building_id
        for building in building_layout.buildings
        if not allowed_no_tolerance.covers(building.footprint)
    ]
    ok = (
        worst_corridor <= BOUNDARY_TOLERANCE_M
        and worst_centerline == 0.0
        and not outside_buildings
    )
    main_margins = [
        float(site_boundary.exterior.distance(road.corridor))
        for road in road_layout.roads
        if road.class_name == "main" and getattr(road, "corridor", None) is not None
    ]
    return {
        "ok": ok,
        "boundary_violation_m": worst_corridor,
        "boundary_margin_m": (
            -worst_corridor
            if worst_corridor > 0
            else min(main_margins)
            if main_margins
            else None
        ),
        "centerline_violation_m": worst_centerline,
        "tolerance_m": BOUNDARY_TOLERANCE_M,
        "outside_building_ids": outside_buildings,
        "roads": corridor_records,
        "status": "contained" if ok else "known_boundary_violation",
    }


def _max_centerline_displacement(
    candidate: RoadLayout, reference: RoadLayout
) -> float:
    reference_by_id = {road.edge_id: road for road in reference.roads}
    maximum = 0.0
    for road in candidate.roads:
        other = reference_by_id.get(road.edge_id)
        if other is None:
            continue
        maximum = max(
            maximum,
            float(road.centerline.hausdorff_distance(other.centerline)),
        )
    return maximum


def _max_displacement_for_classes(
    candidate: RoadLayout, reference: RoadLayout, class_names: Iterable[str]
) -> float:
    allowed = set(class_names)
    reference_by_id = {road.edge_id: road for road in reference.roads}
    maximum = 0.0
    for road in candidate.roads:
        if road.class_name not in allowed:
            continue
        other = reference_by_id.get(road.edge_id)
        if other is None:
            continue
        maximum = max(
            maximum,
            float(road.centerline.hausdorff_distance(other.centerline)),
        )
    return maximum


def _building_displacements(
    candidate: BuildingLayout, reference: BuildingLayout
) -> dict[str, Any]:
    reference_by_id = {item.building_id: item for item in reference.buildings}
    displacements: list[float] = []
    moved: list[str] = []
    for building in candidate.buildings:
        other = reference_by_id.get(building.building_id)
        if other is None:
            continue
        distance = float(
            building.footprint.hausdorff_distance(other.footprint)
        )
        if distance > DISPLACEMENT_EPSILON_M:
            moved.append(building.building_id)
            displacements.append(distance)
    candidate_units = sum(item.unit_count for item in candidate.buildings)
    reference_units = sum(item.unit_count for item in reference.buildings)
    return {
        "displaced_count": len(moved),
        "displaced_building_ids": sorted(moved),
        "max_displacement_m": max(displacements) if displacements else 0.0,
        "mean_displacement_m": (
            sum(displacements) / len(displacements) if displacements else 0.0
        ),
        "unit_delta": candidate_units - reference_units,
        "building_delta": len(candidate.buildings) - len(reference.buildings),
    }


def _source_preservation(road_layout: RoadLayout) -> dict[str, Any]:
    mapping = getattr(road_layout, "source_segment_map", None)
    if not mapping:
        return {"available": False, "reason": "roads.source_segment_map not present"}
    entries = [
        entry
        for records in mapping.values()
        for entry in records
        if isinstance(entry, dict)
    ]
    if not entries:
        return {"available": False, "reason": "source_segment_map is empty"}
    coverage = [
        float(entry["coverage_ratio"])
        for entry in entries
        if entry.get("coverage_ratio") is not None
    ]
    distances = [
        float(entry["distance_m"])
        for entry in entries
        if entry.get("distance_m") is not None
    ]
    headings = [
        abs(float(entry["heading_delta_deg"]))
        for entry in entries
        if entry.get("heading_delta_deg") is not None
    ]
    return {
        "available": True,
        "design_road_count": len(mapping),
        "segment_count": len(entries),
        "mean_coverage_ratio": (
            sum(coverage) / len(coverage) if coverage else None
        ),
        "mean_distance_m": (
            sum(distances) / len(distances) if distances else None
        ),
        "mean_heading_delta_deg": (
            sum(headings) / len(headings) if headings else None
        ),
    }


def _green_metrics(green_layout: GreenLayout | None) -> dict[str, Any] | None:
    if green_layout is None:
        return None
    return {
        "designed_green_ratio": getattr(green_layout, "designed_green_ratio", None),
        "candidate_open_space_ratio": getattr(
            green_layout, "candidate_open_space_ratio", None
        ),
        "unbuilt_ratio": getattr(green_layout, "unbuilt_ratio", None),
    }


def _green_change(
    candidate: GreenLayout | None, reference: GreenLayout | None
) -> dict[str, Any] | None:
    candidate_metrics = _green_metrics(candidate)
    reference_metrics = _green_metrics(reference)
    if candidate_metrics is None or reference_metrics is None:
        return None
    return {
        "designed_green_ratio_delta": (
            candidate_metrics["designed_green_ratio"]
            - reference_metrics["designed_green_ratio"]
        ),
        "candidate_open_space_ratio_delta": (
            candidate_metrics["candidate_open_space_ratio"]
            - reference_metrics["candidate_open_space_ratio"]
        ),
        "unbuilt_ratio_delta": (
            candidate_metrics["unbuilt_ratio"] - reference_metrics["unbuilt_ratio"]
        ),
    }


def _approx_floor_area(building_layout: BuildingLayout, floors: int) -> float:
    return float(
        sum(building.footprint.area * floors for building in building_layout.buildings)
    )


# --------------------------------------------------------------------- dataclass
@dataclass(frozen=True)
class CandidateEvaluation:
    candidate_id: str
    strategy: str
    hard: dict[str, bool]
    hard_details: dict[str, Any]
    hard_pass: bool
    soft: dict[str, Any]
    reasons: tuple[str, ...] = ()
    schema_id: str = SCHEMA_ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "candidate_id": self.candidate_id,
            "strategy": self.strategy,
            "hard": dict(self.hard),
            "hard_pass": self.hard_pass,
            "hard_details": self.hard_details,
            "soft": self.soft,
            "reasons": list(self.reasons),
        }


# --------------------------------------------------------------------- evaluation
def evaluate_candidate(
    candidate: Any,
    basis: DesignBasis,
    *,
    reference: Any | None = None,
    intent: Any | None = None,
    site_boundary: Any | None = None,
    design_input: Any | None = None,
) -> CandidateEvaluation:
    """Evaluate one candidate from its geometry (never from self-reported values).

    ``intent``/``design_input`` provide the building groups for the declared
    access check when the candidate model does not carry them; ``reference`` is
    the baseline candidate used for the soft change metrics.
    """
    building_layout = candidate.building_layout
    road_layout = candidate.road_layout
    green_layout = getattr(candidate, "green_layout", None)
    parking_layout = getattr(candidate, "parking_layout", None)
    reference_building = getattr(reference, "building_layout", None)
    reference_road = getattr(reference, "road_layout", None)
    reference_green = getattr(reference, "green_layout", None)
    candidate_id = str(
        getattr(candidate, "candidate_id", None)
        or getattr(getattr(candidate, "spec", None), "candidate_id", None)
        or getattr(candidate, "id", "candidate")
    )
    strategy = str(
        getattr(candidate, "strategy", None)
        or getattr(getattr(candidate, "spec", None), "strategy", None)
        or "unknown"
    )
    boundary = site_boundary
    if boundary is None:
        boundary = getattr(candidate, "site_boundary", None)
    candidate_input = design_input or getattr(candidate, "design_input", None)
    if boundary is None:
        boundary = getattr(
            candidate_input, "site_boundary", None
        )
    resolved_intent = intent or getattr(candidate, "intent", None) or getattr(
        candidate, "design_intent", None
    )
    if resolved_intent is None:
        if candidate_input is not None:
            from .intent import build_design_intent

            resolved_intent = build_design_intent(candidate_input, basis)
        else:
            resolved_intent = getattr(candidate, "intent_models", None)
    intent = resolved_intent

    hard: dict[str, bool] = {}
    details: dict[str, Any] = {}

    total_overlap = _road_overlap_total(building_layout, road_layout)
    main_overlap = main_road_building_overlap(building_layout, road_layout)
    reference_total_overlap = (
        _road_overlap_total(reference_building, reference_road)
        if reference_building is not None and reference_road is not None
        else None
    )
    overlap_ok = float(main_overlap["area_m2"]) <= HARD_OVERLAP_MAX_M2 and (
        reference_total_overlap is None
        or total_overlap <= reference_total_overlap + HARD_OVERLAP_MAX_M2
    )
    hard["overlap_ok"] = overlap_ok
    details["overlap_ok"] = {
        "main_road_building_overlap_m2": main_overlap["area_m2"],
        "total_road_building_overlap_m2": total_overlap,
        "reference_total_overlap_m2": reference_total_overlap,
        "total_overlap_delta_m2": (
            None
            if reference_total_overlap is None
            else total_overlap - reference_total_overlap
        ),
        "budget_m2": HARD_OVERLAP_MAX_M2,
        "main_road_overlap": main_overlap,
    }

    topology = road_layout.noded_topology
    violations = topology_violations(topology)
    hard["topology_ok"] = (
        topology.component_count == 1 and not violations
    )
    details["topology_ok"] = {
        "component_count": topology.component_count,
        "node_count": topology.node_count,
        "edge_count": topology.edge_count,
        "dead_end_count": topology.dead_end_count,
        "violations": [dict(item) for item in violations],
    }

    boundary_detail = _boundary_metrics(building_layout, road_layout, boundary)
    hard["boundary_ok"] = bool(boundary_detail["ok"])
    if not boundary_detail["ok"]:
        boundary_detail["known_boundary_violation"] = True
        boundary_detail["note"] = (
            "the main-road corridor edge leaves the published site boundary "
            "(or a building/centreline is outside); the candidate cannot be a "
            "hard pass"
        )
    details["boundary_ok"] = boundary_detail

    access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=boundary,
    ) if intent is not None else None
    if access is None:
        hard["access_ok"] = False
        details["access_ok"] = {
            "reason": "design intent / building groups not supplied to the evaluator"
        }
        access_ok = False
    else:
        terminal_distances = [
            group.terminal_centerline_distance_m
            for group in access.groups
            if group.served and group.terminal_centerline_distance_m is not None
        ]
        access_ok = (
            access.groups_total > 0
            and access.groups_served == access.groups_total
            and not access.relation_errors
            and all(
                TERMINAL_DISTANCE_MIN_M - 1e-9
                <= distance
                <= TERMINAL_DISTANCE_MAX_M + 1e-9
                for distance in terminal_distances
            )
            and access.dead_ends_unresolved == 0
        )
        hard["access_ok"] = access_ok
        details["access_ok"] = {
            "groups_total": access.groups_total,
            "groups_served": access.groups_served,
            "unserved_group_ids": list(access.unserved_group_ids),
            "relation_error_count": len(access.relation_errors),
            "dead_ends_unresolved": access.dead_ends_unresolved,
            "road_access_coverage": access.road_access_coverage,
        }

    candidate_units = sum(item.unit_count for item in building_layout.buildings)
    candidate_buildings = len(building_layout.buildings)
    expected_units = None
    expected_buildings = None
    if reference_building is not None:
        expected_units = sum(item.unit_count for item in reference_building.buildings)
        expected_buildings = len(reference_building.buildings)
    if expected_units is None:
        expected_units = getattr(candidate, "expected_units", candidate_units)
        expected_buildings = getattr(
            candidate, "expected_buildings", candidate_buildings
        )
    hard["capacity_ok"] = bool(
        candidate_units == expected_units
        and candidate_buildings == expected_buildings
        and candidate_units > 0
    )
    details["capacity_ok"] = {
        "units": candidate_units,
        "expected_units": expected_units,
        "buildings": candidate_buildings,
        "expected_buildings": expected_buildings,
    }

    basis_ok = True
    basis_detail: dict[str, Any] = {
        "missing": [],
        "expected_parent_basis_id": None,
        "expected_basis_fingerprint": None,
        "actual_parent_basis_id": None,
        "actual_basis_fingerprint": None,
        "changed_fields": [],
    }
    expected_payload = basis.to_dict() if callable(getattr(basis, "to_dict", None)) else {}
    expected_basis_id = str(
        getattr(basis, "basis_id", None) or expected_payload.get("basis_id", "")
    )
    expected_fingerprint = basis_fingerprint(basis)
    basis_detail["expected_parent_basis_id"] = expected_basis_id
    basis_detail["expected_basis_fingerprint"] = expected_fingerprint
    spec = getattr(candidate, "spec", None)
    changes = getattr(candidate, "changes", None)

    def _pick_candidate_field(name: str) -> str | None:
        for source in (candidate, spec):
            if source is None:
                continue
            value = getattr(source, name, None)
            if value:
                return str(value)
        if isinstance(changes, dict):
            for key in ("spec", "basis"):
                nested = changes.get(key)
                if isinstance(nested, dict) and nested.get(name):
                    return str(nested[name])
            if changes.get(name):
                return str(changes[name])
        return None

    actual_parent = _pick_candidate_field("parent_basis_id")
    actual_fingerprint = _pick_candidate_field("basis_fingerprint")
    basis_detail["actual_parent_basis_id"] = actual_parent
    basis_detail["actual_basis_fingerprint"] = actual_fingerprint
    if not actual_parent:
        basis_ok = False
        basis_detail["missing"].append("parent_basis_id")
    elif actual_parent != expected_basis_id:
        basis_ok = False
    if not actual_fingerprint:
        basis_ok = False
        basis_detail["missing"].append("basis_fingerprint")
    elif actual_fingerprint != expected_fingerprint:
        basis_ok = False
    candidate_basis = getattr(candidate, "basis", None)
    if candidate_basis is not None:
        candidate_data = (
            candidate_basis.to_dict()
            if callable(getattr(candidate_basis, "to_dict", None))
            else candidate_basis
        )
        if isinstance(candidate_data, dict):
            changed = [
                key
                for key in ("parameter_sources", "floors", "dwelling_gfa_m2",
                            "household_per_staircase_per_floor", "far_min", "far_max")
                if key in candidate_data and candidate_data[key] != expected_payload.get(key)
            ]
            if changed:
                basis_ok = False
                basis_detail["changed_fields"] = changed
    if isinstance(changes, dict) and changes.get("basis_changes"):
        basis_ok = False
        basis_detail["declared_basis_changes"] = changes["basis_changes"]
    hard["basis_ok"] = basis_ok
    details["basis_ok"] = basis_detail

    hard_pass = all(hard[name] is True for name in HARD_CHECKS)

    soft: dict[str, Any] = {}
    soft["source_preservation"] = _source_preservation(road_layout)
    if reference_road is not None:
        soft["road_change"] = {
            "main_length_delta_m": _total_main_length(road_layout)
            - _total_main_length(reference_road),
            "total_length_delta_m": _total_length(road_layout)
            - _total_length(reference_road),
            "max_displacement_m": _max_centerline_displacement(
                road_layout, reference_road
            ),
            "main_route_deviation_max_m": _max_displacement_for_classes(
                road_layout, reference_road, ("main",)
            ),
            "branch_access_route_deviation_max_m": _max_displacement_for_classes(
                road_layout, reference_road, ("branch", "access")
            ),
            "added_vertices": _vertex_count(road_layout)
            - _vertex_count(reference_road),
        }
        soft["building_change"] = _building_displacements(
            building_layout, reference_building
        )
        reference_access = build_road_access(
            reference_building,
            reference_road,
            intent,
            None,
            basis,
            site_boundary=boundary,
        )
        candidate_terminals = (
            {group.group_id: group.terminal_xy for group in access.groups}
            if access is not None
            else {}
        )
        reference_terminals = {
            group.group_id: group.terminal_xy for group in reference_access.groups
        }
        terminal_delta = 0.0
        for group_id, terminal in candidate_terminals.items():
            other = reference_terminals.get(group_id)
            if terminal is None or other is None:
                continue
            terminal_delta = max(
                terminal_delta,
                float(Point(terminal).distance(Point(other))),
            )
        soft["group_integrity"] = {
            "groups_served": access.groups_served if access is not None else None,
            "reference_groups_served": reference_access.groups_served,
            "declared_relations_preserved": (
                all(
                    group.access_road_id
                    == next(
                        (
                            other.access_road_id
                            for other in reference_access.groups
                            if other.group_id == group.group_id
                        ),
                        None,
                    )
                    for group in access.groups
                )
                if access is not None
                else None
            ),
            "terminal_max_delta_m": terminal_delta,
        }
        soft["green_change"] = _green_change(green_layout, reference_green)
        floors = int(getattr(basis, "floors", 0) or 0)
        candidate_gfa = _approx_floor_area(building_layout, floors)
        reference_gfa = _approx_floor_area(reference_building, floors)
        soft["space_utilization"] = {
            "approx_floor_area_m2": candidate_gfa,
            "approx_floor_area_delta_m2": candidate_gfa - reference_gfa,
            "gfa_unchanged": abs(candidate_gfa - reference_gfa)
            <= DISPLACEMENT_EPSILON_M,
        }
    else:
        soft["road_change"] = None
        soft["building_change"] = None
        soft["group_integrity"] = {
            "groups_served": access.groups_served if access is not None else None,
            "declared_relations_preserved": None,
            "terminal_max_delta_m": None,
        }
        soft["green_change"] = None
        soft["space_utilization"] = None

    reasons: list[str] = []
    if hard_pass:
        reasons.append("all hard gates pass")
    else:
        failed = [name for name in HARD_CHECKS if not hard[name]]
        reasons.append("hard gate failure: " + ", ".join(failed))

    # ---- explicit, single-unit objectives (no composite score) --------------
    source = soft.get("source_preservation") or {}
    road = soft.get("road_change") or {}
    building_change = soft.get("building_change") or {}
    group_integrity = soft.get("group_integrity") or {}
    green = soft.get("green_change") or {}
    raw_objectives = {
        "building_count_change": (
            abs(float(building_change.get("building_delta", 0.0)))
            if building_change
            else None
        ),
        "building_displaced_count": (
            float(building_change.get("displaced_count", 0))
            if building_change
            else None
        ),
        "building_displacement_max_m": (
            float(building_change.get("max_displacement_m", 0.0))
            if building_change
            else None
        ),
        "main_length_delta_abs_m": (
            abs(float(road.get("main_length_delta_m", 0.0))) if road else None
        ),
        "main_route_deviation_max_m": (
            float(road.get("main_route_deviation_max_m", 0.0)) if road else None
        ),
        "branch_access_route_deviation_max_m": (
            float(road.get("branch_access_route_deviation_max_m", 0.0))
            if road
            else None
        ),
        "access_terminal_max_delta_m": group_integrity.get(
            "terminal_max_delta_m"
        ),
        "source_preservation_coverage": source.get("mean_coverage_ratio"),
        "source_preservation_distance_m": source.get("mean_distance_m"),
        "source_preservation_heading_deg": source.get("mean_heading_delta_deg"),
        "green_designed_ratio_delta": green.get("designed_green_ratio_delta"),
    }
    soft["objectives"] = {
        name: (None if value is None else float(value))
        for name, value in raw_objectives.items()
    }
    soft["objective_metadata"] = {
        name: dict(OBJECTIVES[name]) for name in OBJECTIVE_ORDER
    }
    soft["auxiliary"] = {
        "not_in_pareto": True,
        "green_open_space_ratio_delta": green.get(
            "candidate_open_space_ratio_delta"
        ),
        "green_unbuilt_ratio_delta": green.get("unbuilt_ratio_delta"),
        "space_utilization": soft.get("space_utilization"),
        "group_integrity_detail": {
            "groups_served": group_integrity.get("groups_served"),
            "reference_groups_served": group_integrity.get(
                "reference_groups_served"
            ),
            "declared_relations_preserved": group_integrity.get(
                "declared_relations_preserved"
            ),
        },
        "road_added_vertices": road.get("added_vertices") if road else None,
        "note": "auxiliary diagnostics are reported for the README but never "
        "enter the Pareto front or the preference comparison",
    }
    return CandidateEvaluation(
        candidate_id=candidate_id,
        strategy=strategy,
        hard=hard,
        hard_details=details,
        hard_pass=hard_pass,
        soft=soft,
        reasons=tuple(reasons),
    )


# --------------------------------------------------------------------- pareto
def _normalized_objective(evaluation: CandidateEvaluation, objective: str) -> float:
    """Objective value normalised so that smaller is always better."""
    values = (evaluation.soft or {}).get("objectives") or {}
    value = values.get(objective)
    if value is None:
        return float("inf")  # missing objective is fail-closed (worst)
    value = float(value)
    direction = OBJECTIVES[objective]["direction"]
    return -value if direction == "maximize" else value


def _objective_vector(evaluation: CandidateEvaluation) -> tuple[float, ...]:
    return tuple(_normalized_objective(evaluation, name) for name in OBJECTIVE_ORDER)


def _dominates(left: tuple[float, ...], right: tuple[float, ...]) -> bool:
    return all(a <= b for a, b in zip(left, right)) and any(
        a < b for a, b in zip(left, right)
    )


def pareto_front(
    evaluations: Iterable[CandidateEvaluation],
) -> tuple[CandidateEvaluation, ...]:
    """Non-dominated candidates among the hard-passing evaluations.

    Dominance is computed over the eleven independent objectives; auxiliary
    diagnostics never enter the front.
    """
    passing = [item for item in evaluations if item.hard_pass]
    vectors = {item.candidate_id: _objective_vector(item) for item in passing}
    front = []
    for candidate in passing:
        vector = vectors[candidate.candidate_id]
        if not any(
            _dominates(vectors[other.candidate_id], vector)
            for other in passing
            if other.candidate_id != candidate.candidate_id
        ):
            front.append(candidate)
    return tuple(front)


def _priority_value(evaluation: CandidateEvaluation, objective: str) -> float:
    return _normalized_objective(evaluation, objective)


def compare(
    evaluations: Iterable[CandidateEvaluation],
    preferences: list[dict[str, str]] | None = None,
) -> dict[str, Any]:
    """Recommend one candidate by explicit ordered single-unit preferences."""
    evaluations = list(evaluations)
    priorities = list(preferences or DEFAULT_PRIORITIES)
    for priority in priorities:
        objective = priority.get("objective")
        if objective not in OBJECTIVES:
            raise ValueError(f"unknown evaluation objective: {objective!r}")
        if priority.get("direction") not in ("minimize", "maximize"):
            raise ValueError(
                f"unknown preference direction: {priority.get('direction')!r}"
            )
        if priority["direction"] != OBJECTIVES[objective]["direction"]:
            raise ValueError(
                f"preference direction for {objective!r} conflicts with the "
                f"contract direction {OBJECTIVES[objective]['direction']!r}"
            )
    front = pareto_front(evaluations)
    reasons: dict[str, list[str]] = {}
    excluded: dict[str, str] = {}
    for evaluation in evaluations:
        if not evaluation.hard_pass:
            failed = [name for name in HARD_CHECKS if not evaluation.hard[name]]
            reason = "excluded from comparison: hard gate failure: " + ", ".join(failed)
            excluded[evaluation.candidate_id] = "hard gate failure: " + ", ".join(failed)
            reasons[evaluation.candidate_id] = [reason]
    if not front:
        return {
            "recommendation": None,
            "pareto_front": [],
            "reasons": reasons,
            "excluded": excluded,
            "preferences": priorities,
            "objectives": {name: dict(OBJECTIVES[name]) for name in OBJECTIVE_ORDER},
            "auxiliary_metrics_not_in_pareto": list(AUXILIARY_METRICS),
            "priority_rationale": (
                DEFAULT_PRIORITY_RATIONALE if preferences is None else None
            ),
            "note": "no candidate passes the hard gates; nothing is recommended",
        }
    front_ids = {item.candidate_id for item in front}

    def sort_key(evaluation: CandidateEvaluation) -> tuple[float, ...]:
        return tuple(
            _priority_value(evaluation, priority["objective"])
            for priority in priorities
        )

    ordered = sorted(front, key=sort_key)
    recommendation = ordered[0]
    front_vectors = {item.candidate_id: _objective_vector(item) for item in front}
    recommendation_values = (recommendation.soft or {}).get("objectives") or {}
    for evaluation in evaluations:
        if evaluation.candidate_id == recommendation.candidate_id:
            reasons[evaluation.candidate_id] = [
                "hard gates pass and it is first under the declared preference order ("
                + ", ".join(priority["objective"] for priority in priorities)
                + ")",
            ]
            continue
        if evaluation.candidate_id in front_ids:
            dominated_by = [
                other.candidate_id
                for other in front
                if _dominates(
                    front_vectors[other.candidate_id],
                    front_vectors[evaluation.candidate_id],
                )
            ]
            if dominated_by:
                reasons[evaluation.candidate_id] = [
                    "dominated by " + ", ".join(sorted(dominated_by)),
                ]
                continue
            values = (evaluation.soft or {}).get("objectives") or {}
            first_difference = None
            for priority in priorities:
                objective = priority["objective"]
                candidate_value = values.get(objective)
                recommended_value = recommendation_values.get(objective)
                if candidate_value != recommended_value:
                    first_difference = (
                        objective,
                        candidate_value,
                        recommended_value,
                    )
                    break
            if first_difference is None:
                reasons[evaluation.candidate_id] = [
                    "on the Pareto front with identical objective values; "
                    "not preferred under the declared order"
                ]
            else:
                objective, candidate_value, recommended_value = first_difference
                reasons[evaluation.candidate_id] = [
                    f"on the Pareto front but worse on {objective} "
                    f"({candidate_value} vs {recommended_value}); objective-level "
                    "comparison, no composite score"
                ]
        elif evaluation.hard_pass:
            reasons[evaluation.candidate_id] = [
                "hard gates pass but it is dominated outside the Pareto front"
            ]
    return {
        "recommendation": recommendation.candidate_id,
        "pareto_front": [item.candidate_id for item in ordered],
        "reasons": reasons,
        "excluded": excluded,
        "preferences": priorities,
        "objectives": {name: dict(OBJECTIVES[name]) for name in OBJECTIVE_ORDER},
        "auxiliary_metrics_not_in_pareto": list(AUXILIARY_METRICS),
        "priority_rationale": (
            DEFAULT_PRIORITY_RATIONALE if preferences is None else None
        ),
        "note": "hard gates first; the eleven single-unit objectives are compared "
        "directly, the Pareto front and every rejection reason are reported, and "
        "no single black-box score is produced",
    }

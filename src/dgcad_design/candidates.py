"""Deterministic multi-candidate design model generator (M4c-3).

Four candidates start from the same design input / basis and differ only in how
the known main-road/building conflicts are resolved:

* ``road_priority`` (A): the main roads keep their raw (unaligned) geometry and
  the conflicting buildings are translated by the minimum distance needed to
  clear the main corridors.
* ``building_priority_diversion`` (B1): buildings stay put and the M4c-2
  diversion around the building cluster is used (the reference design).
* ``building_priority_alternate`` (B2): buildings stay put, but the diversion uses
  a different fold/clearance offset, producing a visibly different road route
  and displacement.
* ``coordinated`` (C): a small building shift plus a medium road adjustment.

Everything is deterministic: the same spec always yields the same models.  Road
ids are preserved, every candidate keeps the 17 declared group access relations
and the noded network at one component without crossing-only connections.
"""
from __future__ import annotations

import math
from dataclasses import dataclass, replace
from pathlib import Path
from typing import Any

from shapely.affinity import translate
from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from .access import RoadAccessLayout, build_road_access
from .basis import DesignBasis
from .buildings import (
    BuildingLayout,
    StandardBuilding,
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from .evaluation import _boundary_metrics
from .green import GreenLayout, build_green_layout
from .input import DesignInput, load_design_input
from .intent import DesignIntent, build_design_intent
from .parking import ParkingLayout, build_parking_layout
from .roads import RoadLayout, build_road_layout
from .topology import topology_violations

STRATEGY_ROAD_PRIORITY = "road_priority"
STRATEGY_BUILDING_PRIORITY_DIVERSION = "building_priority_diversion"
STRATEGY_BUILDING_PRIORITY_ALTERNATE = "building_priority_alternate"
STRATEGY_COORDINATED = "coordinated"


@dataclass(frozen=True)
class CandidateSpec:
    """One candidate recipe: an id, a strategy key and a human description."""

    candidate_id: str
    strategy: str
    description: str


@dataclass(frozen=True)
class CandidateModels:
    """Complete candidate design models plus the recorded change summary."""

    spec: CandidateSpec
    building_layout: BuildingLayout
    road_layout: RoadLayout
    green_layout: GreenLayout
    parking_layout: ParkingLayout
    road_access: RoadAccessLayout
    changes: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "candidate_id": self.spec.candidate_id,
            "strategy": self.spec.strategy,
            "description": self.spec.description,
            "changes": self.changes,
            "metrics": {
                "main_overlap_after_m2": self.changes[
                    "hard_overlap_after_m2"
                ],
                "road_count": len(self.road_layout.roads),
                "building_count": len(self.building_layout.buildings),
                "designed_green_ratio": (
                    self.green_layout.designed_green_ratio
                ),
                "assumed_nominal_capacity_spaces": (
                    self.parking_layout.assumed_nominal_capacity_spaces
                ),
            },
        }


def _build_catalogue() -> tuple[CandidateSpec, ...]:
    return (
        CandidateSpec(
            candidate_id="A",
            strategy=STRATEGY_ROAD_PRIORITY,
            description=(
                "roads keep their raw source alignment; conflicting buildings "
                "are translated by the minimum distance that clears the main "
                "corridors (road priority)"
            ),
        ),
        CandidateSpec(
            candidate_id="B1",
            strategy=STRATEGY_BUILDING_PRIORITY_DIVERSION,
            description=(
                "buildings stay fixed; the M4c-2 diversion (east fold, 0.5 m "
                "clearance offset) resolves MAIN-19, local detour resolves "
                "MAIN-08 (building priority)"
            ),
        ),
        CandidateSpec(
            candidate_id="B2",
            strategy=STRATEGY_BUILDING_PRIORITY_ALTERNATE,
            description=(
                "buildings stay fixed; an alternate diversion fold with a 6 m "
                "clearance offset gives a visibly different MAIN-19 route and "
                "displacement (building priority, alternate)"
            ),
        ),
        CandidateSpec(
            candidate_id="C",
            strategy=STRATEGY_COORDINATED,
            description=(
                "a small SK-BLD-0006 shift (west) plus a medium local main-road "
                "adjustment remove the conflict together (coordinated)"
            ),
        ),
    )


CANDIDATE_SPECS = _build_catalogue()

#: strategy-specific deterministic parameters
COORDINATED_BUILDING_SHIFT_X = -1.5
ALTERNATE_DIVERSION_MARGIN_M = 6.0
MIN_SHIFT_M = 0.02
MAX_SHIFT_M = 30.0
BUILDING_OVERLAP_TOLERANCE_M2 = 0.01


def _building_shift(
    building: StandardBuilding, dx: float, dy: float
) -> StandardBuilding:
    footprint = translate(building.footprint, xoff=dx, yoff=dy)
    unit_lines = tuple(
        translate(line, xoff=dx, yoff=dy)
        for line in building.unit_lines
    )
    design_centroid = (
        building.design_centroid[0] + dx,
        building.design_centroid[1] + dy,
    )
    label_anchor = (
        building.label_anchor[0] + dx,
        building.label_anchor[1] + dy,
    )
    displacement = math.hypot(
        design_centroid[0] - building.source_centroid[0],
        design_centroid[1] - building.source_centroid[1],
    )
    return replace(
        building,
        footprint=footprint,
        unit_lines=unit_lines,
        design_centroid=design_centroid,
        label_anchor=label_anchor,
        displacement_m=displacement,
    )


def _shift_building_layout(
    building_layout: BuildingLayout,
    shifts: dict[str, tuple[float, float]],
) -> BuildingLayout:
    buildings = []
    for item in building_layout.buildings:
        shift = shifts.get(item.building_id)
        buildings.append(
            _building_shift(item, *shift) if shift is not None else item
        )
    focus_ids = {
        item.building_id for item in building_layout.focus_buildings
    }
    focus = [
        item for item in buildings if item.building_id in focus_ids
    ]
    return replace(
        building_layout,
        buildings=tuple(buildings),
        focus_buildings=tuple(focus),
    )


def _main_centerlines(road_layout: RoadLayout) -> dict[str, LineString]:
    return {
        road.edge_id: road.centerline
        for road in road_layout.roads
        if road.class_name == "main"
    }


def _shift_away_from_road(
    building: StandardBuilding,
    road_centerline: LineString,
) -> tuple[float, float]:
    """Unit direction from the nearest road point towards the building."""
    centroid = Point(building.design_centroid)
    nearest = road_centerline.interpolate(
        road_centerline.project(centroid)
    )
    dx = building.design_centroid[0] - nearest.x
    dy = building.design_centroid[1] - nearest.y
    norm = math.hypot(dx, dy)
    if norm < 1e-9:
        return (1.0, 0.0)
    return (dx / norm, dy / norm)


def _conflict_pairs(
    road_layout: RoadLayout,
    building_layout: BuildingLayout,
    *,
    width: float,
    tolerance_m2: float,
) -> dict[str, dict[str, float]]:
    """building id -> {road id: corridor overlap area} for main corridors."""
    main_roads = [
        road for road in road_layout.roads if road.class_name == "main"
    ]
    conflicts: dict[str, dict[str, float]] = {}
    for building in building_layout.buildings:
        per_road: dict[str, float] = {}
        for road in main_roads:
            area = float(
                road.corridor.intersection(building.footprint).area
            )
            if area > tolerance_m2:
                per_road[road.edge_id] = area
        if per_road:
            conflicts[building.building_id] = per_road
    return conflicts


def _plan_road_priority_shifts(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    *,
    initial_raw_layout: RoadLayout | None = None,
    max_rounds: int = 8,
) -> dict[str, tuple[float, float]]:
    """Minimum building translations that clear every main-road corridor."""
    width = basis.road_widths["main_road"]
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    shifts: dict[str, tuple[float, float]] = {}
    current_layout = building_layout
    raw_layout = initial_raw_layout
    if raw_layout is None:
        raw_layout = build_road_layout(
            design_input,
            basis,
            intent,
            current_layout,
            alignment_mode="none",
        )
    for _ in range(max_rounds):
        conflicts = _conflict_pairs(
            raw_layout,
            current_layout,
            width=width,
            tolerance_m2=1e-4,
        )
        if not conflicts:
            break
        for building_id in sorted(conflicts):
            building = next(
                item
                for item in current_layout.buildings
                if item.building_id == building_id
            )
            per_road = conflicts[building_id]
            road_id = min(per_road, key=lambda key: (-per_road[key], key))
            road = next(
                item
                for item in raw_layout.roads
                if item.edge_id == road_id
            )
            direction = _shift_away_from_road(
                building, road.centerline
            )
            low, high = 0.0, MAX_SHIFT_M
            for _ in range(60):
                middle = (low + high) / 2.0
                shifted = _building_shift(
                    building,
                    direction[0] * middle,
                    direction[1] * middle,
                )
                if (
                    road.corridor.intersection(shifted.footprint).area
                    <= 1e-4
                ):
                    high = middle
                else:
                    low = middle
            distance = min(MAX_SHIFT_M, high + MIN_SHIFT_M)
            shift = (direction[0] * distance, direction[1] * distance)
            shifted = _building_shift(building, *shift)
            _validate_shifted_building(
                shifted=shifted,
                others=[
                    item
                    for item in current_layout.buildings
                    if item.building_id != building_id
                ],
                site_inner=site_inner,
            )
            shifts[building_id] = shift
            current_layout = _shift_building_layout(
                current_layout, {building_id: shift}
            )
        raw_layout = build_road_layout(
            design_input,
            basis,
            intent,
            current_layout,
            alignment_mode="none",
        )
    return shifts


def _validate_shifted_building(
    shifted: StandardBuilding,
    others: list[StandardBuilding],
    site_inner,
) -> None:
    if not site_inner.buffer(1e-6).contains(shifted.footprint):
        raise ValueError(
            f"shifted building {shifted.building_id} leaves the buildable site"
        )
    for other in others:
        overlap = shifted.footprint.intersection(
            other.footprint
        ).area
        if overlap > BUILDING_OVERLAP_TOLERANCE_M2:
            raise ValueError(
                f"shifted building {shifted.building_id} overlaps "
                f"{other.building_id} by {overlap} m2"
            )


LENGTH_CHANGE_TOLERANCE_M = 1e-6
VERTEX_DISPLACEMENT_TOLERANCE_M = 0.01


def _road_route_changes(
    candidate_layout: RoadLayout,
    baseline_main: dict[str, LineString],
) -> list[dict[str, Any]]:
    """Main-road edits versus the raw source alignment.

    A record is emitted for a geometric move (>0.01 m vertex displacement) *and*
    for a pure length change (>1e-6 m) such as a trimmed dangling tail, which
    leaves every remaining vertex on the baseline but still changes the road.
    """
    changes: list[dict[str, Any]] = []
    for road in candidate_layout.roads:
        if road.class_name != "main":
            continue
        baseline = baseline_main[road.edge_id]
        max_displacement = max(
            (
                baseline.distance(Point(float(x), float(y)))
                for x, y in road.centerline.coords
            ),
            default=0.0,
        )
        length_delta = road.centerline.length - baseline.length
        geometry_changed = max_displacement > VERTEX_DISPLACEMENT_TOLERANCE_M
        length_changed = abs(length_delta) > LENGTH_CHANGE_TOLERANCE_M
        if not (geometry_changed or length_changed):
            continue
        if geometry_changed and length_changed:
            kind = "length_change"
        elif geometry_changed:
            kind = "route_change"
        elif length_delta < 0.0:
            kind = "trim"
        else:
            kind = "extend"
        changes.append(
            {
                "road_id": road.edge_id,
                "kind": kind,
                "max_displacement_m": float(max_displacement),
                "max_vertex_displacement_m": float(max_displacement),
                "length_delta_m": float(length_delta),
            }
        )
    changes.sort(key=lambda item: (-item["max_displacement_m"], item["road_id"]))
    return changes


def _topology_summary(road_layout: RoadLayout) -> dict[str, Any]:
    topology = road_layout.noded_topology
    violations = [
        item["code"] for item in topology_violations(topology)
    ]
    return {
        "component_count": topology.component_count,
        "node_count": topology.node_count,
        "edge_count": topology.edge_count,
        "cyclomatic": topology.cyclomatic,
        "dead_end_count": topology.dead_end_count,
        "junction_count": topology.junction_count,
        "explicit_junction_count": topology.explicit_junction_count,
        "closed_ring_count": topology.closed_ring_count,
        "max_endpoint_gap_m": topology.max_endpoint_gap_m,
        "violation_codes": violations,
    }


def _declared_access_total(road_layout: RoadLayout) -> int:
    return sum(len(road.serves_group_ids) for road in road_layout.roads)


def _load_models(
    case_dir: str | Path,
    basis: DesignBasis,
) -> tuple[DesignInput, DesignIntent, BuildingLayout]:
    design_input = load_design_input(case_dir, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        design_rect,
    )
    return design_input, intent, building_layout


@dataclass(frozen=True)
class _CandidateContext:
    design_input: DesignInput
    intent: DesignIntent
    building_layout: BuildingLayout
    raw_layout: RoadLayout
    baseline_main: dict[str, LineString]
    road_priority_shifts: dict[str, tuple[float, float]]


_CONTEXT_CACHE: dict[tuple[str, int], _CandidateContext] = {}


def _context(
    case_dir: str | Path, basis: DesignBasis
) -> _CandidateContext:
    """Deterministic per-process cache for the shared input/basis context."""
    key = (str(Path(case_dir).resolve()), id(basis))
    if key in _CONTEXT_CACHE:
        return _CONTEXT_CACHE[key]
    design_input, intent, building_layout = _load_models(case_dir, basis)
    raw_layout = build_road_layout(
        design_input,
        basis,
        intent,
        building_layout,
        alignment_mode="none",
    )
    baseline_main = _main_centerlines(raw_layout)
    road_priority_shifts = _plan_road_priority_shifts(
        design_input,
        basis,
        intent,
        building_layout,
        initial_raw_layout=raw_layout,
    )
    context = _CandidateContext(
        design_input=design_input,
        intent=intent,
        building_layout=building_layout,
        raw_layout=raw_layout,
        baseline_main=baseline_main,
        road_priority_shifts=road_priority_shifts,
    )
    _CONTEXT_CACHE[key] = context
    return context


def build_candidate(
    case_dir: str | Path,
    basis: DesignBasis,
    spec: CandidateSpec,
) -> CandidateModels:
    """Build one candidate design model deterministically.

    All candidates share the same ``design_input`` / ``basis``; road ids and the
    17 declared group access relations are preserved.
    """
    if isinstance(basis, (str, Path)):
        basis = DesignBasis.load(str(basis))
    context = _context(case_dir, basis)
    design_input = context.design_input
    intent = context.intent
    base_building_layout = context.building_layout
    baseline_main = context.baseline_main
    width = basis.road_widths["main_road"]
    building_layout = base_building_layout
    shifts: dict[str, tuple[float, float]] = {}
    road_kwargs: dict[str, Any] = {}
    if spec.strategy == STRATEGY_ROAD_PRIORITY:
        shifts = dict(context.road_priority_shifts)
        building_layout = _shift_building_layout(
            base_building_layout, shifts
        )
        road_kwargs = {"alignment_mode": "none"}
    elif spec.strategy == STRATEGY_BUILDING_PRIORITY_DIVERSION:
        pass
    elif spec.strategy == STRATEGY_BUILDING_PRIORITY_ALTERNATE:
        road_kwargs = {
            "diversion_side": "east",
            "diversion_margin_m": ALTERNATE_DIVERSION_MARGIN_M,
        }
    elif spec.strategy == STRATEGY_COORDINATED:
        shifts = {
            "SK-BLD-0006": (COORDINATED_BUILDING_SHIFT_X, 0.0)
        }
        building_layout = _shift_building_layout(
            base_building_layout, shifts
        )
    else:
        raise ValueError(f"unknown candidate strategy {spec.strategy!r}")

    road_layout = build_road_layout(
        design_input,
        basis,
        intent,
        building_layout,
        **road_kwargs,
    )
    focus_box = box(*intent.focus_bbox)
    green_layout = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        focus_box,
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    road_access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        design_input.site_boundary,
    )

    route_changes = _road_route_changes(road_layout, baseline_main)
    main_length = sum(
        road.centerline.length
        for road in road_layout.roads
        if road.class_name == "main"
    )
    baseline_length = sum(line.length for line in baseline_main.values())
    building_shifts = [
        {
            "building_id": building_id,
            "dx_m": float(dx),
            "dy_m": float(dy),
            "distance_m": float(math.hypot(dx, dy)),
        }
        for building_id, (dx, dy) in sorted(shifts.items())
    ]
    topology = _topology_summary(road_layout)
    overlap_after = float(
        road_layout.road_building_overlap_m2_main_after
    )
    boundary_metrics = _boundary_metrics(
        building_layout, road_layout, design_input.site_boundary
    )
    changes: dict[str, Any] = {
        "spec": {
            "candidate_id": spec.candidate_id,
            "strategy": spec.strategy,
        },
        "boundary": {
            "hard_boundary_ok": bool(boundary_metrics["ok"]),
            "boundary_violation_m": float(
                boundary_metrics["boundary_violation_m"]
            ),
            "boundary_margin_m": float(
                boundary_metrics["boundary_margin_m"]
            ),
            "centerline_violation_m": float(
                boundary_metrics["centerline_violation_m"]
            ),
            "outside_building_ids": list(
                boundary_metrics["outside_building_ids"]
            ),
        },
        "hard_boundary_ok": bool(boundary_metrics["ok"]),
        "building_shifts": building_shifts,
        "displaced_buildings": sorted(shifts),
        "building_shift_total_m": float(
            sum(item["distance_m"] for item in building_shifts)
        ),
        "road_route_changes": route_changes,
        "road_route_change_count": len(route_changes),
        "road_max_displacement_m": float(
            max(
                (item["max_displacement_m"] for item in route_changes),
                default=0.0,
            )
        ),
        "main_length_m": float(main_length),
        "main_length_baseline_m": float(baseline_length),
        "main_length_delta_m": float(main_length - baseline_length),
        "hard_overlap_after_m2": overlap_after,
        "main_overlap_before_m2": float(
            road_layout.road_building_overlap_m2_main
        ),
        "main_overlap_resolved": bool(
            road_layout.main_overlap_resolved
        ),
        "topology": topology,
        "access": {
            "declared_total": _declared_access_total(road_layout),
            "coverage": float(road_access.road_access_coverage),
            "served_groups": sum(
                1 for group in road_access.groups if group.served
            ),
            "group_count": len(road_access.groups),
            "dead_ends_unresolved": int(
                road_access.dead_ends_unresolved
            ),
            "dead_ends_resolved": int(road_access.dead_ends_resolved),
        },
        "building_count": len(building_layout.buildings),
        "unit_count_total": sum(
            item.unit_count for item in building_layout.buildings
        ),
        "household_count_total": sum(
            item.households for item in building_layout.buildings
        ),
        "designed_green_ratio": float(
            green_layout.designed_green_ratio
        ),
        "assumed_nominal_capacity_spaces": int(
            parking_layout.assumed_nominal_capacity_spaces
        ),
    }
    return CandidateModels(
        spec=spec,
        building_layout=building_layout,
        road_layout=road_layout,
        green_layout=green_layout,
        parking_layout=parking_layout,
        road_access=road_access,
        changes=changes,
    )


def candidate_by_id(candidate_id: str) -> CandidateSpec:
    for spec in CANDIDATE_SPECS:
        if spec.candidate_id == candidate_id:
            return spec
    raise KeyError(candidate_id)


def build_all_candidates(
    case_dir: str | Path,
    basis: DesignBasis,
) -> dict[str, CandidateModels]:
    """Build the four standard candidates (deterministic)."""
    return {
        spec.candidate_id: build_candidate(case_dir, basis, spec)
        for spec in CANDIDATE_SPECS
    }

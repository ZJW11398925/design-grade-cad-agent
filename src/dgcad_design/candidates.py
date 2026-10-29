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
from .evaluation import _boundary_metrics, basis_fingerprint
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
    parent_basis_id: str = ""
    basis_fingerprint: str = ""


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
            "parent_basis_id": self.spec.parent_basis_id,
            "basis_fingerprint": self.spec.basis_fingerprint,
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
                "corridors (road priority). The SK-BLD-0006 shift also re-routes "
                "its BR-G-08 access branch by 2.826 m - every affected road, "
                "including branches/access, is recorded in geometry_change"
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
                "adjustment remove the conflict together (coordinated); the "
                "coordinated shift also re-routes the G-08 access branch "
                "(BR-G-08) - every affected road including branches/access is "
                "recorded in geometry_change"
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
AFFECTED_ROAD_TOLERANCE_M = 0.01
GEOMETRY_DIFFERENCE_BUFFER_M = 1e-6


def _road_route_changes(
    candidate_layout: RoadLayout,
    reference_layout: RoadLayout,
) -> list[dict[str, Any]]:
    """All-road edits versus the raw reference layout (compatibility view).

    Includes main, branch and access roads; a record is emitted for a geometric
    move, a re-route, or a pure length change such as a trimmed dangling tail.
    """
    changes, _, _ = _road_geometry_changes(
        reference_layout, candidate_layout
    )
    return changes


def _road_change_kind(
    *,
    length_delta_m: float,
    removed_length_m: float,
    added_length_m: float,
    hausdorff_m: float,
    max_vertex_displacement_m: float,
) -> str:
    geometry_changed = (
        hausdorff_m > AFFECTED_ROAD_TOLERANCE_M
        or max_vertex_displacement_m > AFFECTED_ROAD_TOLERANCE_M
    )
    length_changed = abs(length_delta_m) > LENGTH_CHANGE_TOLERANCE_M
    if (
        added_length_m <= AFFECTED_ROAD_TOLERANCE_M
        and removed_length_m > AFFECTED_ROAD_TOLERANCE_M
        and length_delta_m < 0.0
    ):
        return "trim"
    if (
        removed_length_m <= AFFECTED_ROAD_TOLERANCE_M
        and added_length_m > AFFECTED_ROAD_TOLERANCE_M
        and length_delta_m > 0.0
    ):
        return "extend"
    if geometry_changed and length_changed:
        return "length_change"
    if geometry_changed:
        return "reroute"
    if length_changed and length_delta_m < 0.0:
        return "trim"
    if length_changed and length_delta_m > 0.0:
        return "extend"
    return "length_change"


def _road_geometry_changes(
    reference_layout: RoadLayout,
    candidate_layout: RoadLayout,
) -> tuple[list[dict[str, Any]], dict[str, float], dict[str, int]]:
    """Per-road geometry diff for *all* road classes against the raw reference.

    The reference is the boundary-safe ``alignment_mode="none"`` layout; every
    road id is compared with its candidate counterpart by Hausdorff distance,
    length delta and removed/added length so a pure trim/extension or a
    branch/access re-route cannot be missed.
    """
    reference_by_id = {
        road.edge_id: road for road in reference_layout.roads
    }
    candidate_by_id = {
        road.edge_id: road for road in candidate_layout.roads
    }
    roads: list[dict[str, Any]] = []
    class_max_deviation = {"main": 0.0, "branch": 0.0, "access": 0.0}
    class_affected_count = {"main": 0, "branch": 0, "access": 0}
    for road_id in sorted(candidate_by_id):
        candidate_road = candidate_by_id[road_id]
        class_name = candidate_road.class_name
        reference_road = reference_by_id.get(road_id)
        if reference_road is None:
            removed_length = 0.0
            added_length = float(candidate_road.centerline.length)
            length_delta = added_length
            hausdorff = added_length
            max_vertex = added_length
            kind = "replace"
        else:
            reference_line = reference_road.centerline
            candidate_line = candidate_road.centerline
            length_delta = (
                candidate_line.length - reference_line.length
            )
            hausdorff = float(
                reference_line.hausdorff_distance(candidate_line)
            )
            max_vertex = max(
                max(
                    (
                        reference_line.distance(
                            Point(float(x), float(y))
                        )
                        for x, y in candidate_line.coords
                    ),
                    default=0.0,
                ),
                max(
                    (
                        candidate_line.distance(
                            Point(float(x), float(y))
                        )
                        for x, y in reference_line.coords
                    ),
                    default=0.0,
                ),
            )
            if (
                hausdorff <= AFFECTED_ROAD_TOLERANCE_M
                and max_vertex <= AFFECTED_ROAD_TOLERANCE_M
                and abs(length_delta) <= LENGTH_CHANGE_TOLERANCE_M
            ):
                continue
            removed_length = float(
                reference_line.difference(
                    candidate_line.buffer(
                        GEOMETRY_DIFFERENCE_BUFFER_M
                    )
                ).length
            )
            added_length = float(
                candidate_line.difference(
                    reference_line.buffer(
                        GEOMETRY_DIFFERENCE_BUFFER_M
                    )
                ).length
            )
            kind = _road_change_kind(
                length_delta_m=length_delta,
                removed_length_m=removed_length,
                added_length_m=added_length,
                hausdorff_m=hausdorff,
                max_vertex_displacement_m=max_vertex,
            )
        if class_name in class_max_deviation:
            class_max_deviation[class_name] = max(
                class_max_deviation[class_name], float(hausdorff)
            )
            class_affected_count[class_name] += 1
        roads.append(
            {
                "road_id": road_id,
                "class_name": class_name,
                "kind": kind,
                "length_delta_m": float(length_delta),
                "max_displacement_m": float(hausdorff),
                "max_vertex_displacement_m": float(max_vertex),
                "hausdorff_m": float(hausdorff),
                "removed_length_m": float(removed_length),
                "added_length_m": float(added_length),
            }
        )
    for reference_road in reference_layout.roads:
        if reference_road.edge_id in candidate_by_id:
            continue
        roads.append(
            {
                "road_id": reference_road.edge_id,
                "class_name": reference_road.class_name,
                "kind": "replace",
                "length_delta_m": -float(
                    reference_road.centerline.length
                ),
                "max_displacement_m": float(
                    reference_road.centerline.length
                ),
                "max_vertex_displacement_m": float(
                    reference_road.centerline.length
                ),
                "hausdorff_m": float(
                    reference_road.centerline.length
                ),
                "removed_length_m": float(
                    reference_road.centerline.length
                ),
                "added_length_m": 0.0,
            }
        )
    roads.sort(key=lambda item: (-item["hausdorff_m"], item["road_id"]))
    return roads, class_max_deviation, class_affected_count


def _group_terminal_changes(
    reference_layout: RoadLayout,
    candidate_layout: RoadLayout,
) -> list[dict[str, Any]]:
    """Terminal displacement per access group (17 declared relations)."""

    def serving_roads(layout: RoadLayout) -> dict[str, Any]:
        mapping: dict[str, Any] = {}
        for road in layout.roads:
            for group_id in road.serves_group_ids:
                mapping[group_id] = road
        return mapping

    reference_serving = serving_roads(reference_layout)
    candidate_serving = serving_roads(candidate_layout)
    changes: list[dict[str, Any]] = []
    for group_id in sorted(set(reference_serving) | set(candidate_serving)):
        reference_road = reference_serving.get(group_id)
        candidate_road = candidate_serving.get(group_id)
        terminal_before = (
            list(reference_road.access_terminal_xy)
            if reference_road is not None
            and reference_road.access_terminal_xy is not None
            else None
        )
        terminal_after = (
            list(candidate_road.access_terminal_xy)
            if candidate_road is not None
            and candidate_road.access_terminal_xy is not None
            else None
        )
        delta_m = None
        hausdorff_m = None
        if terminal_before is not None and terminal_after is not None:
            delta_m = float(
                Point(terminal_before).distance(Point(terminal_after))
            )
        if reference_road is not None and candidate_road is not None:
            hausdorff_m = float(
                reference_road.centerline.hausdorff_distance(
                    candidate_road.centerline
                )
            )
        changes.append(
            {
                "group_id": group_id,
                "road_id": (
                    candidate_road.edge_id
                    if candidate_road is not None
                    else (
                        reference_road.edge_id
                        if reference_road is not None
                        else None
                    )
                ),
                "road_id_before": (
                    reference_road.edge_id
                    if reference_road is not None
                    else None
                ),
                "road_id_after": (
                    candidate_road.edge_id
                    if candidate_road is not None
                    else None
                ),
                "terminal_before": terminal_before,
                "terminal_after": terminal_after,
                "delta_m": delta_m,
                "hausdorff_m": hausdorff_m,
            }
        )
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
    parent_basis_id = str(getattr(basis, "basis_id", "") or "")
    basis_fingerprint_value = basis_fingerprint(basis)
    bound_spec = replace(
        spec,
        parent_basis_id=parent_basis_id,
        basis_fingerprint=basis_fingerprint_value,
    )
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

    route_changes = _road_route_changes(
        road_layout, context.raw_layout
    )
    (
        geometry_road_records,
        class_max_deviation,
        class_affected_count,
    ) = _road_geometry_changes(context.raw_layout, road_layout)
    group_terminal_changes = _group_terminal_changes(
        context.raw_layout, road_layout
    )
    road_max_deviation = max(
        (item["hausdorff_m"] for item in geometry_road_records),
        default=0.0,
    )
    main_road_max_deviation = max(
        (
            item["hausdorff_m"]
            for item in geometry_road_records
            if item["class_name"] == "main"
        ),
        default=0.0,
    )
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
            "parent_basis_id": parent_basis_id,
            "basis_fingerprint": basis_fingerprint_value,
        },
        "parent_basis_id": parent_basis_id,
        "basis_fingerprint": basis_fingerprint_value,
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
        "road_max_displacement_m": float(road_max_deviation),
        "main_road_max_displacement_m": float(
            main_road_max_deviation
        ),
        "geometry_change": {
            "reference": (
                "raw source alignment plus boundary repair "
                "(alignment_mode='none' road layout)"
            ),
            "tolerance_m": AFFECTED_ROAD_TOLERANCE_M,
            "affected_road_count": len(geometry_road_records),
            "affected_road_count_by_class": dict(
                class_affected_count
            ),
            "class_max_deviation_m": dict(class_max_deviation),
            "max_route_deviation_main_m": float(
                class_max_deviation["main"]
            ),
            "max_route_deviation_branch_m": float(
                class_max_deviation["branch"]
            ),
            "max_route_deviation_access_m": float(
                class_max_deviation["access"]
            ),
            "roads": geometry_road_records,
            "group_terminal_changes": group_terminal_changes,
        },
        "group_terminal_changes": group_terminal_changes,
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
        spec=bound_spec,
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

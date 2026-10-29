from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import linemerge, nearest_points, unary_union
from shapely.strtree import STRtree

from .basis import DesignBasis
from .buildings import BuildingLayout
from .input import DesignInput, RoadInput
from .intent import DesignIntent
from .topology import NodedRoadTopology, noded_road_topology

#: Focus access loop is offset this far from the included building hull.
LOOP_BUFFER_M = 8.0

#: Access terminal distance from the group footprint: clearance 3.0 m + 0.5 m
#: allowed tolerance.  At 3.5 m the 7 m branch round cap is tangent to the
#: facade, so the branch corridor does not overlap the building.
ACCESS_TERMINAL_DISTANCE_M = 3.5

#: Candidate ring is generated a micron inside the bound so the exact
#: distance check ``<= clearance + 0.5`` cannot fail on float round-up.
_TERMINAL_RING_M = ACCESS_TERMINAL_DISTANCE_M - 1e-6

#: Branch length window for a group access road.
ACCESS_BRANCH_MIN_LENGTH_M = 3.0
ACCESS_BRANCH_MAX_LENGTH_M = 150.0

#: A route may brush a footprint by at most this length (endpoint contact is 0).
ACCESS_ROUTE_FOOTPRINT_CROSS_MAX_M = 0.1

#: A new access branch corridor may overlap any footprint by at most this area.
ACCESS_CORRIDOR_OVERLAP_MAX_M2 = 1.0

#: Group access connectors may be built as branch (7 m) or, when a 7 m
#: cross-section collides with the detailed focus block, as access (4 m).
GROUP_ACCESS_CLASS_OPTIONS = (
    ("branch", "branch_road"),
    ("access", "access_road"),
)

#: Sampling step along the terminal-distance ring around a group footprint.
ACCESS_CANDIDATE_STEP_M = 1.5

#: Safety margin used when choosing the buildings included in the loop hull.
LOOP_HULL_PROBE_MARGIN_M = 0.5

#: Conservative corridor reach used by the loop-hull fixed point
#: (access corridor half width + sidewalk + margin).
LOOP_CORRIDOR_PROBE_M = 5.0


@dataclass(frozen=True)
class RoadDesign:
    edge_id: str
    class_name: str
    width_m: float
    centerline: LineString
    corridor: Polygon
    is_new_connector: bool
    reason: str
    source_edge_ids: tuple[str, ...] = ()
    source_trace_ref: str | None = None
    start_junction_id: str | None = None
    end_junction_id: str | None = None
    serves_group_ids: tuple[str, ...] = ()
    access_terminal_xy: tuple[float, float] | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "class_name": self.class_name,
            "width_m": self.width_m,
            "is_new_connector": self.is_new_connector,
            "reason": self.reason,
            "source_edge_ids": list(self.source_edge_ids),
            "source_trace_ref": self.source_trace_ref,
            "start_junction_id": self.start_junction_id,
            "end_junction_id": self.end_junction_id,
            "serves_group_ids": list(self.serves_group_ids),
            "access_terminal_xy": (
                None
                if self.access_terminal_xy is None
                else [
                    float(self.access_terminal_xy[0]),
                    float(self.access_terminal_xy[1]),
                ]
            ),
            "length_m": self.centerline.length,
            "corridor_area_m2": self.corridor.area,
            "centerline": {
                "type": "LineString",
                "coordinates": [
                    [float(x), float(y)]
                    for x, y in self.centerline.coords
                ],
            },
        }


@dataclass(frozen=True)
class RoadLayout:
    roads: tuple[RoadDesign, ...]
    corridor_union: Polygon | MultiPolygon
    sidewalk_union: Polygon | MultiPolygon
    junction_nodes: tuple[str, ...]
    dead_end_nodes: tuple[str, ...]
    corridor_generator: str
    not_professional_alignment: bool
    corridor_union_pieces: int
    noded_topology: NodedRoadTopology
    explicit_junctions: tuple[dict[str, Any], ...]
    simplification: dict[str, Any]
    road_building_overlap_m2_new_access: float = 0.0
    road_building_overlap_m2_main: float = 0.0
    road_building_overlap_m2_total: float = 0.0
    group_access_unserved: tuple[str, ...] = ()
    main_alignment_records: tuple[dict[str, Any], ...] = ()
    dead_end_resolutions: tuple[dict[str, Any], ...] = ()
    road_building_overlap_m2_main_after: float = 0.0
    main_overlap_resolved: bool = False
    source_segment_map: dict[str, list[dict[str, Any]]] = field(
        default_factory=dict
    )
    main_boundary_repairs: tuple[dict[str, Any], ...] = ()

    @property
    def road_area_m2(self) -> float:
        return float(self.corridor_union.area)

    @property
    def sidewalk_area_m2(self) -> float:
        return float(self.sidewalk_union.area)

    def to_dict(self) -> dict[str, Any]:
        return {
            "road_count": len(self.roads),
            "road_area_m2": self.road_area_m2,
            "sidewalk_area_m2": self.sidewalk_area_m2,
            "corridor_union_pieces": self.corridor_union_pieces,
            "noded_topology": self.noded_topology.to_dict(),
            "explicit_junctions": [dict(item) for item in self.explicit_junctions],
            "junction_nodes": list(self.junction_nodes),
            "dead_end_nodes": list(self.dead_end_nodes),
            "corridor_generator": self.corridor_generator,
            "not_professional_alignment": self.not_professional_alignment,
            "road_building_overlap_m2_new_access": (
                self.road_building_overlap_m2_new_access
            ),
            "road_building_overlap_m2_main": self.road_building_overlap_m2_main,
            "road_building_overlap_m2_main_after": (
                self.road_building_overlap_m2_main_after
            ),
            "road_building_overlap_m2_total": (
                self.road_building_overlap_m2_total
            ),
            "main_overlap_resolved": self.main_overlap_resolved,
            "main_alignment_records": [
                dict(record) for record in self.main_alignment_records
            ],
            "main_boundary_repairs": [
                dict(record) for record in self.main_boundary_repairs
            ],
            "dead_end_resolutions": [
                dict(record) for record in self.dead_end_resolutions
            ],
            "group_access_unserved": list(self.group_access_unserved),
            "source_segment_map": {
                design_road_id: [dict(item) for item in entries]
                for design_road_id, entries in self.source_segment_map.items()
            },
            "simplification": self.simplification,
            "widths": {
                name: sorted(
                    {
                        road.width_m
                        for road in self.roads
                        if road.class_name == name
                    }
                )
                for name in ("main", "branch", "access")
            },
            "roads": [road.to_dict() for road in self.roads],
        }


def _line_list(geometry) -> list[LineString]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        return [geometry]
    if geometry.geom_type == "LinearRing":
        return [LineString(geometry.coords)]
    if geometry.geom_type in {"MultiLineString", "GeometryCollection"}:
        lines: list[LineString] = []
        for item in geometry.geoms:
            lines.extend(_line_list(item))
        return lines
    return []


def _point_list(geometry) -> list[Point]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Point":
        return [geometry]
    if geometry.geom_type in {"MultiPoint", "GeometryCollection"}:
        points: list[Point] = []
        for item in geometry.geoms:
            points.extend(_point_list(item))
        return points
    return []


def _polygon_list(geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type in {"MultiPolygon", "GeometryCollection"}:
        polygons: list[Polygon] = []
        for item in geometry.geoms:
            polygons.extend(_polygon_list(item))
        return polygons
    return []


def _corridor(line: LineString, width: float, *, round_caps: bool) -> Polygon:
    return line.buffer(
        width / 2,
        cap_style="round" if round_caps else "flat",
        join_style="round" if round_caps else "mitre",
    )


def _road(
    edge_id: str,
    class_name: str,
    width: float,
    centerline: LineString,
    *,
    is_new: bool,
    reason: str,
    source_edge_ids: tuple[str, ...] = (),
    source_trace_ref: str | None = None,
    round_caps: bool = False,
    start_junction_id: str | None = None,
    end_junction_id: str | None = None,
    serves_group_ids: tuple[str, ...] = (),
    access_terminal_xy: tuple[float, float] | None = None,
) -> RoadDesign:
    return RoadDesign(
        edge_id=edge_id,
        class_name=class_name,
        width_m=width,
        centerline=centerline,
        corridor=_corridor(centerline, width, round_caps=round_caps),
        is_new_connector=is_new,
        reason=reason,
        source_edge_ids=source_edge_ids,
        source_trace_ref=source_trace_ref,
        start_junction_id=start_junction_id,
        end_junction_id=end_junction_id,
        serves_group_ids=serves_group_ids,
        access_terminal_xy=access_terminal_xy,
    )


def _main_lines(
    design_input: DesignInput,
) -> tuple[list[LineString], tuple[str, ...]]:
    main_roads = [
        road
        for road in design_input.roads
        if road.class_candidate == "main_road"
    ]
    merged = linemerge(
        unary_union([road.centerline for road in main_roads])
    )
    lines = [
        line
        for line in _line_list(merged)
        if line.length >= 8.0
    ]
    source_ids = tuple(road.edge_id for road in main_roads)
    return lines, source_ids


def _insert_vertex(
    line: LineString, target: Point
) -> tuple[LineString, tuple[float, float]]:
    """Insert the projection of ``target`` as an explicit vertex of ``line``.

    Returns ``(new_line, xy)`` where ``xy`` is the *exact float tuple* of a
    vertex of ``new_line``.  Callers must build the connecting road from the
    same tuple, so both lineworks share the coordinate exactly (no tolerance,
    no snap).  If an existing vertex already has exactly the target coordinate,
    it is reused.
    """
    coords = list(line.coords)
    target_xy = (float(target.x), float(target.y))
    vertices = {(float(x), float(y)) for x, y in coords}
    if target_xy in vertices:
        return line, target_xy

    is_ring = len(coords) >= 4 and coords[0] == coords[-1]
    best: tuple[float, int, float, float] | None = None
    for index in range(len(coords) - 1):
        start = coords[index]
        end = coords[index + 1]
        segment = LineString([start, end])
        distance = segment.distance(target)
        if best is None or distance < best[0]:
            best = (distance, index, segment.project(target), segment.length)
    assert best is not None, "line has no segment"
    _, index, projected, length = best
    t = projected / max(length, 1e-12)
    xy = (
        coords[index][0] + t * (coords[index + 1][0] - coords[index][0]),
        coords[index][1] + t * (coords[index + 1][1] - coords[index][1]),
    )
    if is_ring and index == len(coords) - 2:
        # closing segment (last -> first): keep the ring closed
        new_coords = coords[:-1] + [xy, coords[-1]]
    else:
        new_coords = coords[: index + 1] + [xy] + coords[index + 1 :]
    return LineString(new_coords), xy


def _insert_vertex_at(
    line: LineString, xy: tuple[float, float]
) -> LineString:
    """Insert the *given* coordinate as a vertex (the point must be on line).

    Used when two lineworks must share one exact coordinate (loop/x main
    crossings): the same ``xy`` tuple is inserted into both lines.
    """
    coords = list(line.coords)
    target = (float(xy[0]), float(xy[1]))
    if target in {(float(x), float(y)) for x, y in coords}:
        return line
    is_ring = len(coords) >= 4 and coords[0] == coords[-1]
    best_index = 0
    best_distance = float("inf")
    point = Point(target)
    for index in range(len(coords) - 1):
        segment = LineString([coords[index], coords[index + 1]])
        distance = segment.distance(point)
        if distance < best_distance:
            best_distance = distance
            best_index = index
    if is_ring and best_index == len(coords) - 2:
        new_coords = coords[:-1] + [target, coords[-1]]
    else:
        new_coords = coords[: best_index + 1] + [target] + coords[best_index + 1 :]
    return LineString(new_coords)


def _shared_point_only(geometry, attach: Point) -> bool:
    """True when the only intersection with the target line is the attach point."""
    if geometry.is_empty:
        return False
    if geometry.geom_type == "Point":
        return geometry.distance(attach) <= 1e-9
    if geometry.geom_type in {"MultiPoint", "GeometryCollection"}:
        return all(
            item.geom_type == "Point" and item.distance(attach) <= 1e-9
            for item in geometry.geoms
        )
    return False


def _sample_ring(ring: LineString, step: float) -> list[Point]:
    points = [Point(coord) for coord in ring.coords]
    length = ring.length
    distance = step
    while distance < length:
        points.append(ring.interpolate(distance))
        distance += step
    return points


def _add_or_merge_junction(
    junctions: list[dict[str, Any]],
    xy: tuple[float, float],
    road_ids: tuple[str, ...],
) -> str:
    for junction in junctions:
        if (
            float(junction["x"]) == float(xy[0])
            and float(junction["y"]) == float(xy[1])
        ):
            for road_id in road_ids:
                if road_id not in junction["road_ids"]:
                    junction["road_ids"].append(road_id)
            return str(junction["id"])
    junction_id = f"J-{len(junctions) + 1:02d}"
    junctions.append(
        {
            "id": junction_id,
            "x": float(xy[0]),
            "y": float(xy[1]),
            "road_ids": list(road_ids),
        }
    )
    return junction_id


def _loop_hull(
    building_layout: BuildingLayout,
    adjacent_building_ids: set[str] | None = None,
) -> tuple[LineString, tuple[str, ...]]:
    """Fixed-point loop hull: include every building the loop corridor could hit.

    Starts from the focus buildings plus the buildings of groups adjacent to the
    focus block (groups whose bbox intersects the focus bbox), then repeatedly
    adds any building whose footprint is within corridor reach of the current
    loop ring, until the ring no longer touches a building.  This is what
    removes the old G-05 loop/corridor overlap (and any equivalent one) instead
    of hard-coding group ids.
    """
    buildings = list(building_layout.buildings)
    by_id = {item.building_id: item for item in buildings}
    included_ids = {
        item.building_id for item in building_layout.focus_buildings
        if item.building_id in by_id
    }
    included_ids |= {
        building_id
        for building_id in (adjacent_building_ids or set())
        if building_id in by_id
    }
    focus = [by_id[building_id] for building_id in sorted(included_ids)]
    hull_geometry = unary_union([item.footprint for item in focus])
    for _ in range(12):
        ring = LineString(
            hull_geometry.convex_hull.buffer(
                LOOP_BUFFER_M, join_style="mitre"
            ).exterior.coords
        )
        probe = ring.buffer(LOOP_CORRIDOR_PROBE_M)
        new_ids = [
            item.building_id
            for item in buildings
            if item.building_id not in included_ids
            and item.footprint.intersects(probe)
        ]
        if not new_ids:
            break
        included_ids.update(new_ids)
        hull_geometry = unary_union(
            [hull_geometry] + [by_id[building_id].footprint for building_id in new_ids]
        )
    ring = LineString(
        hull_geometry.convex_hull.buffer(
            LOOP_BUFFER_M, join_style="mitre"
        ).exterior.coords
    )
    return ring, tuple(sorted(included_ids))


#: Frozen-terminal access branches may be short frontage connections (the main
#: road can run along the building frontage after a detour).
FROZEN_TERMINAL_MIN_BRANCH_M = 1.0


def _choose_group_access(
    group_union: Polygon,
    network: list[tuple[str, int, LineString]],
    building_footprints: list[Polygon],
    footprint_tree: STRtree,
    existing_connector_lines: list[LineString],
    branch_width: float,
    existing_footprint_overlap: dict[int, float],
    focus_footprint_indices: set[int],
    focus_clearance_footprints: list[Polygon],
    focus_clearance_m: float,
    class_options: tuple[tuple[str, float], ...],
    fixed_terminal: tuple[float, float] | None = None,
    fixed_network: tuple[str, int] | None = None,
) -> dict[str, Any] | None:
    """Pick a clean access branch: group frontage terminal + network attach."""
    if fixed_terminal is not None:
        terminals = [Point(float(fixed_terminal[0]), float(fixed_terminal[1]))]
    else:
        terminals = []
        for polygon in _polygon_list(
            group_union.buffer(_TERMINAL_RING_M)
        ):
            terminals.extend(
                _sample_ring(
                    LineString(polygon.exterior.coords),
                    ACCESS_CANDIDATE_STEP_M,
                )
            )
    if fixed_network is not None:
        network = [
            (kind, index, geom)
            for kind, index, geom in network
            if (kind, index) == fixed_network
        ]
        if not network:
            return None
    minimum_length = (
        FROZEN_TERMINAL_MIN_BRANCH_M
        if fixed_terminal is not None
        else ACCESS_BRANCH_MIN_LENGTH_M
    )
    feasible: list[dict[str, Any]] = []
    for order, terminal in enumerate(terminals):
        hit_indices = footprint_tree.query(terminal)
        if hit_indices.size and any(
            building_footprints[int(index)].intersects(terminal)
            for index in hit_indices
        ):
            continue
        for kind, index, geom in network:
            if geom.distance(terminal) > ACCESS_BRANCH_MAX_LENGTH_M:
                continue
            attach = nearest_points(geom, terminal)[0]
            length = attach.distance(terminal)
            if (
                length < minimum_length
                or length > ACCESS_BRANCH_MAX_LENGTH_M
            ):
                continue
            segment = LineString(
                [(float(attach.x), float(attach.y)),
                 (float(terminal.x), float(terminal.y))]
            )
            hit_indices = footprint_tree.query(segment)
            crossing = sum(
                segment.intersection(building_footprints[int(item)]).length
                for item in hit_indices
            )
            if crossing > ACCESS_ROUTE_FOOTPRINT_CROSS_MAX_M:
                continue
            if not _shared_point_only(segment.intersection(geom), attach):
                continue
            crosses_other_road = any(
                not segment.intersection(other_geom).is_empty
                for other_kind, other_index, other_geom in network
                if (other_kind, other_index) != (kind, index)
            )
            if crosses_other_road:
                continue
            crosses_branch = any(
                not segment.intersection(line).is_empty
                for line in existing_connector_lines
            )
            if crosses_branch:
                continue
            # a 7 m branch where possible; a 4 m access lane when the 7 m
            # cross-section would collide with the detailed focus block
            for class_name, width in class_options:
                corridor = _corridor(segment, width, round_caps=True)
                class_hits = footprint_tree.query(corridor)
                overlap = sum(
                    corridor.intersection(
                        building_footprints[int(item)]
                    ).area
                    for item in class_hits
                )
                if overlap > ACCESS_CORRIDOR_OVERLAP_MAX_M2:
                    continue
                # cumulative per-building budget across all new access roads
                exceeds_budget = False
                for item in class_hits:
                    index_int = int(item)
                    added = corridor.intersection(
                        building_footprints[index_int]
                    ).area
                    if (
                        existing_footprint_overlap.get(index_int, 0.0) + added
                        > ACCESS_CORRIDOR_OVERLAP_MAX_M2 + 1e-12
                    ):
                        exceeds_budget = True
                        break
                    # designed focus buildings are detailed design objects: a
                    # new access road must not cut into them at all
                    if (
                        index_int in focus_footprint_indices
                        and existing_footprint_overlap.get(index_int, 0.0)
                        + added
                        > 1e-9
                    ):
                        exceeds_budget = True
                        break
                if exceeds_budget:
                    continue
                # focus building-road clearance is a hard design check: the
                # corridor (not only the centreline) keeps its distance
                if any(
                    corridor.distance(footprint)
                    < focus_clearance_m - 1e-9
                    for footprint in focus_clearance_footprints
                ):
                    continue
                feasible.append(
                    {
                        "kind": kind,
                        "index": index,
                        "attach": (float(attach.x), float(attach.y)),
                        "terminal": (float(terminal.x), float(terminal.y)),
                        "length": float(length),
                        "overlap": float(overlap),
                        "order": order,
                        "class_name": class_name,
                        "width": float(width),
                    }
                )
    if not feasible:
        return None
    return min(
        feasible,
        key=lambda item: (
            0 if item["class_name"] == "branch" else 1,
            round(item["length"], 9),
            item["order"],
            0 if item["kind"] == "main" else 1,
            item["index"],
        ),
    )


def _align_main_lines(
    main_geoms: list[LineString],
    building_footprints: list[Polygon],
    building_ids: list[str],
    width: float,
    target_distance: float,
    *,
    tolerance_m2: float = 1e-4,
    max_passes: int = 12,
    diversion_side: str = "auto",
    diversion_margin_m: float = 0.5,
) -> tuple[list[LineString], tuple[dict[str, Any], ...]]:
    """Local main-road detours that remove every corridor/building overlap.

    ``target_distance`` is the centreline-to-footprint distance required for a
    corridor edge clearance (half width + building clearance).  Each conflicting
    footprint is handled by a radial push of the affected sub-line away from the
    obstacle; endpoints and existing vertices outside the conflict are kept, so
    the source geometry stays recognisable and road ids do not change.
    """
    originals = [LineString(geom.coords) for geom in main_geoms]
    footprints_union = unary_union(building_footprints)
    adjusted = list(main_geoms)
    records: list[dict[str, Any]] = []
    for index, geom in enumerate(adjusted):
        current = geom
        for _ in range(max_passes):
            corridor = _corridor(current, width, round_caps=False)
            conflicting_index = None
            for footprint_index, footprint in enumerate(building_footprints):
                if corridor.intersection(footprint).area > tolerance_m2:
                    conflicting_index = footprint_index
                    break
            if conflicting_index is None:
                break
            pushed = _push_line_away_from_obstacle(
                current,
                building_footprints[conflicting_index],
                target_distance,
            )
            if pushed.equals(current):
                break
            current = pushed
        final_corridor = _corridor(current, width, round_caps=False)
        after_area = float(
            final_corridor.intersection(footprints_union).area
        )
        before_area = float(
            _corridor(originals[index], width, round_caps=False)
            .intersection(footprints_union)
            .area
        )
        original_corridor = _corridor(
            originals[index], width, round_caps=False
        )
        original_conflict_indices = [
            footprint_index
            for footprint_index, footprint in enumerate(building_footprints)
            if original_corridor.intersection(footprint).area > tolerance_m2
        ]
        original_conflict_ids = [
            building_ids[footprint_index]
            for footprint_index in original_conflict_indices
        ]
        alignment_strategy = "local_detour"
        local_search_exhausted = False
        relevant_conflict_indices = list(original_conflict_indices)
        if after_area > tolerance_m2:
            # a zero-overlap local detour was not reachable: first try the
            # minimum-overlap lateral shift, then a full diversion around the
            # conflict cluster (needed when the buildings are closer together
            # than the corridor is wide)
            fallback_overlap, fallback_line = _minimise_main_overlap(
                originals[index],
                building_footprints,
                width,
                target_distance,
            )
            if fallback_overlap < after_area - 1e-9:
                current = fallback_line
                after_area = fallback_overlap
                final_corridor = _corridor(
                    current, width, round_caps=False
                )
                alignment_strategy = "min_overlap_shift"
            if after_area > tolerance_m2:
                residual_indices = [
                    footprint_index
                    for footprint_index, footprint in enumerate(
                        building_footprints
                    )
                    if final_corridor.intersection(footprint).area
                    > tolerance_m2
                ]
                diversion_indices = sorted(
                    set(original_conflict_indices) | set(residual_indices)
                )
                relevant_conflict_indices = list(diversion_indices)
                diversion = None
                diversion_corridor = None
                for _ in range(3):
                    diversion = _diversion_around_conflict(
                        originals[index],
                        [
                            building_footprints[footprint_index]
                            for footprint_index in diversion_indices
                        ],
                        target_distance,
                        preferred_side=diversion_side,
                        margin_m=diversion_margin_m,
                    )
                    if diversion is None:
                        break
                    diversion_corridor = _corridor(
                        diversion, width, round_caps=False
                    )
                    diversion_overlap = float(
                        diversion_corridor.intersection(
                            footprints_union
                        ).area
                    )
                    if diversion_overlap <= tolerance_m2:
                        break
                    extra_indices = [
                        footprint_index
                        for footprint_index, footprint in enumerate(
                            building_footprints
                        )
                        if diversion_corridor.intersection(
                            footprint
                        ).area
                        > tolerance_m2
                    ]
                    if not extra_indices:
                        break
                    diversion_indices = sorted(
                        set(diversion_indices) | set(extra_indices)
                    )
                    relevant_conflict_indices = list(diversion_indices)
                if (
                    diversion is not None
                    and diversion_corridor is not None
                    and float(
                        diversion_corridor.intersection(
                            footprints_union
                        ).area
                    )
                    <= tolerance_m2
                ):
                    current = diversion
                    after_area = float(
                        diversion_corridor.intersection(
                            footprints_union
                        ).area
                    )
                    final_corridor = diversion_corridor
                    alignment_strategy = "diversion"
                    local_search_exhausted = True
        if current.equals(originals[index]) and before_area <= tolerance_m2:
            adjusted[index] = current
            continue
        final_conflicts = [
            (building_ids[footprint_index], footprint)
            for footprint_index, footprint in enumerate(building_footprints)
            if final_corridor.intersection(footprint).area > tolerance_m2
        ]
        building_gap = None
        gap_footprints = [item[1] for item in final_conflicts]
        if not gap_footprints:
            gap_footprints = [
                building_footprints[footprint_index]
                for footprint_index in relevant_conflict_indices
            ]
        for left in range(len(gap_footprints)):
            for right in range(left + 1, len(gap_footprints)):
                gap = gap_footprints[left].distance(
                    gap_footprints[right]
                )
                if building_gap is None or gap < building_gap:
                    building_gap = float(gap)
        conflict_building_ids = [
            building_ids[footprint_index]
            for footprint_index in sorted(original_conflict_indices)
        ]
        obstacle_building_ids = [
            building_ids[footprint_index]
            for footprint_index in sorted(
                set(relevant_conflict_indices)
                - set(original_conflict_indices)
            )
        ]
        per_building_overlap_before_m2 = {
            building_ids[footprint_index]: float(
                original_corridor.intersection(footprint).area
            )
            for footprint_index, footprint in enumerate(
                building_footprints
            )
            if original_corridor.intersection(footprint).area
            > tolerance_m2
        }
        max_displacement = max(
            (
                originals[index].distance(Point(float(x), float(y)))
                for x, y in current.coords
            ),
            default=0.0,
        )
        original_coords = [
            (float(x), float(y)) for x, y in originals[index].coords
        ]
        adjusted_coords = [
            (float(x), float(y)) for x, y in current.coords
        ]
        constraint_satisfied = after_area <= tolerance_m2
        if constraint_satisfied and alignment_strategy == "diversion":
            gap_text = (
                f"{building_gap if building_gap is not None else 0.0:.2f}"
            )
            reason = (
                "the current local search family (<=30 m displacement, finite "
                "lateral/diversion candidates) found no endpoint-preserving "
                "local solution; the "
                f"{gap_text} m gap between the original conflict footprint and "
                "the diversion obstacle footprint is only "
                f"{gap_text} m (< {width:.1f} m main corridor), which proves "
                "the passage between the two buildings is infeasible but does "
                "not prove that a wider search cannot find another local "
                "route; the recorded diversion "
                f"(max displacement {max_displacement:.2f} m) is a legal "
                "candidate, not an impossibility proof"
            )
        elif constraint_satisfied:
            reason = (
                "local detour keeps the main corridor edge at least 3.0 m "
                "clear of building footprints; endpoints and junctions "
                "outside the conflict are preserved"
            )
        else:
            reason = (
                "unresolved: neither the local detour nor the diversion "
                "around the conflict cluster reached zero overlap; recorded "
                f"the minimum achievable residual {after_area:.4f} m2"
            )
        records.append(
            {
                "road_id": f"MAIN-{index + 1:02d}",
                "source_edge_ids": [],
                "alignment_strategy": alignment_strategy,
                "local_search_exhausted": local_search_exhausted,
                "conflict_building_ids": conflict_building_ids,
                "obstacle_building_ids": obstacle_building_ids,
                "per_building_overlap_before_m2": (
                    per_building_overlap_before_m2
                ),
                "residual_conflict_building_ids": [
                    item[0] for item in final_conflicts
                ],
                "original_centerline": original_coords,
                "adjusted_centerline": adjusted_coords,
                "max_displacement_m": float(max_displacement),
                "overlap_before_m2": before_area,
                "overlap_after_m2": after_area,
                "constraint_satisfied": constraint_satisfied,
                "minimal_residual_overlap_m2": after_area,
                "conflicting_building_gap_m": building_gap,
                "vertices_added": max(
                    0, len(adjusted_coords) - len(original_coords)
                ),
                "vertices_removed": max(
                    0, len(original_coords) - len(adjusted_coords)
                ),
                "reason": reason,
            }
        )
        adjusted[index] = current
    return adjusted, tuple(records)


def _push_line_away_from_obstacle(
    line: LineString,
    obstacle: Polygon,
    target_distance: float,
    *,
    step_m: float = 1.0,
    margin_m: float = 0.3,
) -> LineString:
    """Push the part of ``line`` inside ``obstacle.buffer(target)`` outwards.

    Samples inside the buffered obstacle are projected radially away from the
    obstacle onto a ring at ``target_distance + margin``; the entry/exit
    vertices stay on the original line, so the detour is local and both ends
    keep their position (and junction vertices outside the conflict remain).
    """
    safe = obstacle.buffer(target_distance + margin_m)
    if not safe.intersects(line):
        return line
    length = line.length
    samples: list[tuple[float, Point]] = []
    distance = 0.0
    while distance <= length:
        samples.append((distance, line.interpolate(distance)))
        distance += step_m
    if not samples or samples[-1][0] < length:
        samples.append((length, line.interpolate(length)))
    inside = [
        (sample_distance, point)
        for sample_distance, point in samples
        if safe.intersects(point)
    ]
    if not inside:
        return line
    first_distance = inside[0][0]
    last_distance = inside[-1][0]
    entry_distance = max(0.0, first_distance - step_m)
    exit_distance = min(length, last_distance + step_m)
    while entry_distance > 0 and safe.intersects(
        line.interpolate(entry_distance)
    ):
        entry_distance = max(0.0, entry_distance - step_m)
    while exit_distance < length and safe.intersects(
        line.interpolate(exit_distance)
    ):
        exit_distance = min(length, exit_distance + step_m)
    entry = line.interpolate(entry_distance)
    exit_point = line.interpolate(exit_distance)
    target_radius = target_distance + margin_m
    pushed: list[Point] = [entry]
    sample_distance = first_distance
    while sample_distance <= last_distance + 1e-9:
        point = line.interpolate(min(sample_distance, length))
        nearest = nearest_points(obstacle, point)[0]
        dx = point.x - nearest.x
        dy = point.y - nearest.y
        norm = (dx * dx + dy * dy) ** 0.5
        if norm < 1e-9:
            centroid = obstacle.centroid
            dx = point.x - centroid.x
            dy = point.y - centroid.y
            norm = (dx * dx + dy * dy) ** 0.5
        if norm < 1e-9:
            dx, dy, norm = 1.0, 0.0, 1.0
        pushed.append(
            Point(
                nearest.x + dx / norm * target_radius,
                nearest.y + dy / norm * target_radius,
            )
        )
        sample_distance += 2.0
    pushed.append(exit_point)
    coordinates = list(line.coords)
    vertex_distances: list[float] = [0.0]
    for left, right in zip(coordinates, coordinates[1:]):
        vertex_distances.append(
            vertex_distances[-1]
            + (
                (right[0] - left[0]) ** 2
                + (right[1] - left[1]) ** 2
            )
            ** 0.5
        )
    new_coords: list[tuple[float, float]] = []
    for (x, y), vertex_distance in zip(coordinates, vertex_distances):
        if vertex_distance < entry_distance - 1e-9:
            new_coords.append((float(x), float(y)))
    for point in pushed:
        candidate = (float(point.x), float(point.y))
        if not new_coords or new_coords[-1] != candidate:
            new_coords.append(candidate)
    for (x, y), vertex_distance in zip(coordinates, vertex_distances):
        if vertex_distance > exit_distance + 1e-9:
            candidate = (float(x), float(y))
            if not new_coords or new_coords[-1] != candidate:
                new_coords.append(candidate)
    if len(new_coords) < 2:
        return line
    return LineString(_simplify_detour_coords(new_coords))


def _noded_degree_one_endpoints(
    lines: list[LineString],
) -> list[tuple[tuple[float, float], int, int]]:
    """Exact degree-one endpoints of the noded union of ``lines``.

    Returns ``(xy, line_index, end_index)`` where ``end_index`` is 0 for the
    start of that line and 1 for its end.  No tolerance, no rounding.
    """
    if not lines:
        return []
    merged = unary_union(lines)
    degree: dict[tuple[float, float], int] = {}
    for segment in _line_list(merged):
        coordinates = list(segment.coords)
        if len(coordinates) < 2:
            continue
        start = (float(coordinates[0][0]), float(coordinates[0][1]))
        end = (float(coordinates[-1][0]), float(coordinates[-1][1]))
        if start == end:
            degree[start] = degree.get(start, 0) + 2
        else:
            degree[start] = degree.get(start, 0) + 1
            degree[end] = degree.get(end, 0) + 1
    dead: list[tuple[tuple[float, float], int, int]] = []
    for index, line in enumerate(lines):
        coordinates = list(line.coords)
        if len(coordinates) < 2:
            continue
        for end_index, position in ((0, coordinates[0]), (1, coordinates[-1])):
            xy = (float(position[0]), float(position[1]))
            if degree.get(xy, 0) == 1:
                dead.append((xy, index, end_index))
    return dead


def _find_main_bridge(
    source_id: str,
    source_index: int,
    end_index: int,
    point: Point,
    main_geoms: list[LineString],
    connector_lines: list[LineString],
    access_loop: LineString,
    buildings_union: Polygon,
    width: float,
    focus_clearance_footprints: list[Polygon],
    focus_clearance_m: float,
    *,
    sample_step_m: float = 2.0,
    min_length_m: float = 2.0,
    max_length_m: float = 40.0,
    vertex_gap_m: float = 2.0,
    overlap_tolerance_m2: float = 0.01,
) -> tuple[float, int, tuple[float, float]] | None:
    """Shortest clean bridge from a dangling main endpoint to another main.

    The bridge must be <= 40 m, must not touch a building footprint with its
    main-road corridor, must not cross a third centreline, must attach at least
    2 m away from an existing target vertex (no degenerate micro-edges), and may
    touch the source line only at the dangling endpoint itself.  The *resulting
    extended road corridor* is also validated (this is what rejects a bridge that
    would fold the source road back on itself and spike its mitre corridor into
    a focused building).
    """
    source_line = main_geoms[source_index]
    source_coordinates = list(source_line.coords)
    other_centerlines = list(connector_lines) + [access_loop]
    best: tuple[float, int, tuple[float, float]] | None = None
    for target_index, target_line in enumerate(main_geoms):
        if target_index == source_index:
            continue
        target_vertices = [
            (float(x), float(y)) for x, y in target_line.coords
        ]
        distance = 0.0
        while distance <= target_line.length:
            candidate = target_line.interpolate(distance)
            candidate_xy = (float(candidate.x), float(candidate.y))
            bridge_length = float(candidate.distance(point))
            if min_length_m - 1e-9 <= bridge_length <= max_length_m + 1e-9:
                far_from_vertices = all(
                    (
                        (candidate_xy[0] - vx) ** 2
                        + (candidate_xy[1] - vy) ** 2
                    )
                    ** 0.5
                    > vertex_gap_m
                    for vx, vy in target_vertices
                )
                if far_from_vertices:
                    bridge = LineString(
                        [(float(point.x), float(point.y)), candidate_xy]
                    )
                    corridor = _corridor(
                        bridge, width, round_caps=False
                    )
                    clean = (
                        corridor.intersection(buildings_union).area
                        <= overlap_tolerance_m2
                    )
                    if clean:
                        # the extended source road must also stay clean
                        if end_index == 0:
                            tentative = LineString(
                                [candidate_xy] + source_coordinates
                            )
                        else:
                            tentative = LineString(
                                source_coordinates + [candidate_xy]
                            )
                        tentative_corridor = _corridor(
                            tentative, width, round_caps=False
                        )
                        if (
                            tentative_corridor.intersection(
                                buildings_union
                            ).area
                            > overlap_tolerance_m2
                        ):
                            clean = False
                        elif any(
                            tentative_corridor.distance(footprint)
                            < focus_clearance_m - 1e-9
                            for footprint in focus_clearance_footprints
                        ):
                            clean = False
                    if clean:
                        for other_index, other_line in enumerate(
                            main_geoms
                        ):
                            if other_index in (source_index, target_index):
                                continue
                            if not bridge.intersection(other_line).is_empty:
                                clean = False
                                break
                    if clean:
                        for other_line in other_centerlines:
                            if not bridge.intersection(other_line).is_empty:
                                clean = False
                                break
                    if clean:
                        source_inter = bridge.intersection(source_line)
                        if not (
                            source_inter.geom_type == "Point"
                            and source_inter.distance(point) <= 1e-9
                        ):
                            clean = False
                    if clean:
                        target_inter = bridge.intersection(target_line)
                        if not (
                            target_inter.is_empty
                            or (
                                target_inter.geom_type == "Point"
                                and target_inter.distance(candidate) <= 1e-9
                            )
                        ):
                            clean = False
                    if clean and (
                        best is None or bridge_length < best[0]
                    ):
                        best = (bridge_length, target_index, candidate_xy)
            distance += sample_step_m
    return best


def _trim_main_to_junction(
    source_id: str,
    line_index: int,
    end_index: int,
    line: LineString,
    junctions: list[dict[str, Any]],
) -> tuple[
    LineString, tuple[float, float], float, int
] | None:
    """Trim a dangling tail back to the nearest explicit junction of its road."""
    coordinates = [
        (float(x), float(y)) for x, y in line.coords
    ]
    dead_xy = coordinates[0] if end_index == 0 else coordinates[-1]
    best: tuple[float, tuple[float, float]] | None = None
    for junction in junctions:
        if source_id not in junction.get("road_ids", ()):
            continue
        xy = (float(junction["x"]), float(junction["y"]))
        if xy not in coordinates:
            continue
        distance = (
            (xy[0] - dead_xy[0]) ** 2 + (xy[1] - dead_xy[1]) ** 2
        ) ** 0.5
        if best is None or distance < best[0]:
            best = (distance, xy)
    if best is None:
        return None
    xy = best[1]
    if end_index == 1:
        index = len(coordinates) - 1 - coordinates[::-1].index(xy)
        if index >= len(coordinates) - 1:
            return None
        new_coordinates = coordinates[: index + 1]
    else:
        index = coordinates.index(xy)
        if index <= 0:
            return None
        new_coordinates = coordinates[index:]
    if len(new_coordinates) < 2:
        return None
    new_line = LineString(new_coordinates)
    if new_line.length < 1.0:
        return None
    return (
        new_line,
        xy,
        float(line.length - new_line.length),
        len(coordinates) - len(new_coordinates),
    )


def _extend_to_site_boundary(
    line: LineString,
    end_index: int,
    point: Point,
    site_boundary: Polygon,
    buildings_union: Polygon,
    width: float,
    focus_clearance_footprints: list[Polygon],
    focus_clearance_m: float,
    other_centerlines: list[LineString],
    *,
    max_extension_m: float = 30.0,
    overlap_tolerance_m2: float = 0.01,
) -> tuple[LineString, tuple[float, float], float, float] | None:
    """Extend a dangling main endpoint to the published site boundary.

    Used for MAIN-25: the stub ends 5.64 m inside the published site boundary and
    has no bridge target or junction, so the honest resolution is to extend it
    along the **shortest direction to the boundary** (not a straight continuation
    of the terminal segment; the two directions differ, reported as the
    normalized cross product).  The source network is clipped at the published
    boundary, so the endpoint then lies exactly on that boundary.  The extension
    segment must stay clear of building footprints and focused building
    clearance, and must not cross another road centreline.
    """
    coordinates = list(line.coords)
    if len(coordinates) < 2:
        return None
    if end_index == 1:
        previous = Point(
            float(coordinates[-2][0]), float(coordinates[-2][1])
        )
        tip = Point(float(coordinates[-1][0]), float(coordinates[-1][1]))
    else:
        previous = Point(
            float(coordinates[1][0]), float(coordinates[1][1])
        )
        tip = Point(float(coordinates[0][0]), float(coordinates[0][1]))
    direction = (tip.x - previous.x, tip.y - previous.y)
    norm = (direction[0] ** 2 + direction[1] ** 2) ** 0.5
    if norm < 1e-12:
        return None
    unit = (direction[0] / norm, direction[1] / norm)
    candidates: list[tuple[float, tuple[float, float]]] = []
    nearest_boundary = nearest_points(site_boundary.boundary, tip)[0]
    nearest_xy = (float(nearest_boundary.x), float(nearest_boundary.y))
    nearest_distance = float(tip.distance(nearest_boundary))
    if 1e-6 < nearest_distance <= max_extension_m + 1e-9:
        candidates.append((nearest_distance, nearest_xy))
    far = Point(
        tip.x + unit[0] * max_extension_m,
        tip.y + unit[1] * max_extension_m,
    )
    ray = LineString([(tip.x, tip.y), (far.x, far.y)])
    for candidate in _point_list(ray.intersection(site_boundary.boundary)):
        offset = (
            (candidate.x - tip.x) * unit[0]
            + (candidate.y - tip.y) * unit[1]
        )
        if 1e-6 < offset <= max_extension_m + 1e-9:
            candidates.append(
                (float(offset), (float(candidate.x), float(candidate.y)))
            )
    if not candidates:
        return None
    extension_length, boundary_xy = min(candidates, key=lambda item: item[0])
    extension = LineString(
        [(float(tip.x), float(tip.y)), boundary_xy]
    )
    extension_corridor = _corridor(extension, width, round_caps=False)
    if (
        extension_corridor.intersection(buildings_union).area
        > overlap_tolerance_m2
    ):
        return None
    if any(
        extension_corridor.distance(footprint)
        < focus_clearance_m - 1e-9
        for footprint in focus_clearance_footprints
    ):
        return None
    for other in other_centerlines:
        if not extension.intersection(other).is_empty:
            return None
    if end_index == 1:
        new_coordinates = coordinates + [boundary_xy]
    else:
        new_coordinates = [boundary_xy] + coordinates
    extension_direction = (
        (boundary_xy[0] - tip.x) / extension_length,
        (boundary_xy[1] - tip.y) / extension_length,
    )
    direction_cross = abs(
        unit[0] * extension_direction[1]
        - unit[1] * extension_direction[0]
    )
    return (
        LineString(new_coordinates),
        boundary_xy,
        extension_length,
        float(direction_cross),
    )


def _simplify_detour_coords(
    coordinates: list[tuple[float, float]],
    *,
    deviation_m: float = 0.02,
) -> list[tuple[float, float]]:
    """Drop near-collinear interior vertices from a detour polyline."""
    if len(coordinates) <= 2:
        return coordinates
    simplified = [coordinates[0]]
    for index in range(1, len(coordinates) - 1):
        previous = simplified[-1]
        current = coordinates[index]
        following = coordinates[index + 1]
        segment = LineString([previous, following])
        if segment.length == 0.0:
            continue
        if segment.distance(Point(current)) <= deviation_m:
            continue
        simplified.append(current)
    simplified.append(coordinates[-1])
    return simplified


def _minimise_main_overlap(
    line: LineString,
    building_footprints: list[Polygon],
    width: float,
    required_distance: float,
    *,
    max_shift_m: float = 30.0,
    step_m: float = 0.25,
    tolerance_m2: float = 1e-4,
) -> tuple[float, LineString]:
    """Best-effort lateral shift when a zero-overlap detour is impossible.

    Tries pushing the conflicting part away from each nearby footprint by a
    range of distances (up to the required clearance), keeps the candidate with
    the smallest total corridor/building overlap, and ties break on displacement.
    Used for the documented MAIN-19 building-gap conflict.
    """
    def total_overlap(candidate: LineString) -> float:
        corridor = _corridor(candidate, width, round_caps=False)
        return float(
            sum(
                corridor.intersection(footprint).area
                for footprint in building_footprints
            )
        )

    def displacement(candidate: LineString) -> float:
        return max(
            line.distance(Point(float(x), float(y)))
            for x, y in candidate.coords
        )

    best_overlap = total_overlap(line)
    best_line = line
    best_displacement = 0.0
    for footprint in building_footprints:
        current_distance = line.distance(footprint)
        if current_distance >= required_distance:
            continue
        target = current_distance + step_m
        while target <= required_distance + 1e-9:
            candidate = _push_line_away_from_obstacle(
                line, footprint, target
            )
            if candidate.equals(line):
                target += step_m
                continue
            movement = displacement(candidate)
            if movement > max_shift_m + 1e-9:
                target += step_m
                continue
            overlap = total_overlap(candidate)
            if overlap < best_overlap - 1e-9 or (
                abs(overlap - best_overlap) <= 1e-9
                and movement < best_displacement
            ):
                best_overlap = overlap
                best_line = candidate
                best_displacement = movement
            target += step_m
    return best_overlap, best_line


def _diversion_around_conflict(
    line: LineString,
    conflict_footprints: list[Polygon],
    required_distance: float,
    *,
    step_m: float = 1.0,
    margin_m: float = 0.5,
    deviation_m: float = 0.05,
    preferred_side: str = "auto",
) -> LineString | None:
    """Route around a building cluster when a local detour is impossible.

    Used for MAIN-19: the two buildings beside it are closer together than the
    main corridor is wide, so the only zero-overlap solution is to leave the
    corridor and walk around the combined clearance envelope.  The entry/exit
    vertices stay on the original line; the middle is replaced by the shorter
    side of the envelope boundary at the required clearance.
    """
    if not conflict_footprints:
        return None
    envelope = unary_union(
        [
            footprint.buffer(required_distance + margin_m)
            for footprint in conflict_footprints
        ]
    )
    polygons = _polygon_list(envelope)
    if not polygons:
        return None
    envelope = max(polygons, key=lambda item: item.area)
    length = line.length
    samples: list[tuple[float, Point]] = []
    distance = 0.0
    while distance <= length:
        samples.append((distance, line.interpolate(distance)))
        distance += step_m
    if samples[-1][0] < length:
        samples.append((length, line.interpolate(length)))
    inside = [
        (sample_distance, point)
        for sample_distance, point in samples
        if envelope.intersects(point)
    ]
    if not inside:
        return None
    first_distance = inside[0][0]
    last_distance = inside[-1][0]
    entry_distance = max(0.0, first_distance - step_m)
    exit_distance = min(length, last_distance + step_m)
    while entry_distance > 0 and envelope.intersects(
        line.interpolate(entry_distance)
    ):
        entry_distance = max(0.0, entry_distance - step_m)
    while exit_distance < length and envelope.intersects(
        line.interpolate(exit_distance)
    ):
        exit_distance = min(length, exit_distance + step_m)
    entry = line.interpolate(entry_distance)
    exit_point = line.interpolate(exit_distance)
    boundary = envelope.exterior
    boundary_coords = [
        (float(x), float(y)) for x, y in boundary.coords
    ]
    start_boundary = nearest_points(boundary, entry)[0]
    end_boundary = nearest_points(boundary, exit_point)[0]
    start_index = min(
        range(len(boundary_coords)),
        key=lambda index: (
            (boundary_coords[index][0] - start_boundary.x) ** 2
            + (boundary_coords[index][1] - start_boundary.y) ** 2
        ),
    )
    end_index = min(
        range(len(boundary_coords)),
        key=lambda index: (
            (boundary_coords[index][0] - end_boundary.x) ** 2
            + (boundary_coords[index][1] - end_boundary.y) ** 2
        ),
    )
    forward = (
        boundary_coords[start_index : end_index + 1]
        if end_index >= start_index
        else boundary_coords[start_index:] + boundary_coords[: end_index + 1]
    )
    backward = (
        list(reversed(boundary_coords[: start_index + 1]))
        + list(reversed(boundary_coords[end_index:]))
    )
    arcs = [forward, backward]
    if preferred_side == "auto":
        arc = min(arcs, key=lambda item: LineString(item).length)
    else:
        side_keys = {"east", "west", "north", "south"}
        if preferred_side not in side_keys:
            raise ValueError(
                f"unknown diversion side {preferred_side!r}; "
                f"expected 'auto' or one of {sorted(side_keys)}"
            )

        def _side_score(coordinates: list[tuple[float, float]]) -> float:
            probe = LineString(coordinates).interpolate(0.5)
            if preferred_side == "east":
                return -probe.x
            if preferred_side == "west":
                return probe.x
            if preferred_side == "north":
                return -probe.y
            return probe.y

        arc = min(arcs, key=_side_score)
    prefix = [
        (float(x), float(y))
        for (x, y), vertex_distance in zip(line.coords, _cumulative(line))
        if vertex_distance < entry_distance - 1e-9
    ]
    suffix = [
        (float(x), float(y))
        for (x, y), vertex_distance in zip(line.coords, _cumulative(line))
        if vertex_distance > exit_distance + 1e-9
    ]
    coordinates = (
        prefix
        + [(float(entry.x), float(entry.y))]
        + [(float(x), float(y)) for x, y in arc]
        + [(float(exit_point.x), float(exit_point.y))]
        + suffix
    )
    deduped: list[tuple[float, float]] = []
    for coordinate in coordinates:
        if not deduped or deduped[-1] != coordinate:
            deduped.append(coordinate)
    if len(deduped) < 2:
        return None
    return LineString(_simplify_detour_coords(deduped, deviation_m=deviation_m))


def _cumulative(line: LineString) -> list[float]:
    coordinates = list(line.coords)
    cumulative = [0.0]
    for left, right in zip(coordinates, coordinates[1:]):
        cumulative.append(
            cumulative[-1]
            + (
                (right[0] - left[0]) ** 2
                + (right[1] - left[1]) ** 2
            )
            ** 0.5
        )
    return cumulative


def _segment_heading_deg(line: LineString) -> float:
    coordinates = list(line.coords)
    dx = coordinates[-1][0] - coordinates[0][0]
    dy = coordinates[-1][1] - coordinates[0][1]
    return float(math.degrees(math.atan2(dy, dx)))


def _heading_delta_deg(
    source_line: LineString, design_line: LineString
) -> float:
    """Coarse heading difference between a source edge and a design road."""
    midpoint = source_line.interpolate(source_line.length / 2.0)
    nearest = nearest_points(design_line, midpoint)[0]
    coordinates = list(design_line.coords)
    best: tuple[float, LineString] | None = None
    for start, end in zip(coordinates, coordinates[1:]):
        segment = LineString([start, end])
        distance = segment.distance(nearest)
        if best is None or distance < best[0]:
            best = (distance, segment)
    assert best is not None
    delta = abs(_segment_heading_deg(source_line) - _segment_heading_deg(best[1]))
    delta = delta % 180.0
    if delta > 90.0:
        delta = 180.0 - delta
    return float(delta)


def _source_segment_map(
    main_geoms: list[LineString],
    design_input: DesignInput,
    width: float,
    *,
    endpoint_tolerance_m: float = 2.5,
) -> dict[str, list[dict[str, Any]]]:
    """Coarse source-main-edge -> design-main-road mapping.

    A source main edge counts as covered by a design main road when both of its
    endpoints project onto that design centreline within
    ``endpoint_tolerance_m``; the projected span then gives the overlap length and
    coverage ratio (so crossing edges, whose endpoints lie far from the line, do
    not pollute the mapping).  When no source edge is covered the three nearest
    source main edges are reported with ``distance_m`` instead.  The heading
    difference is measured against the local design segment.  Purely evidence;
    geometry is not modified.
    """
    source_main = [
        road
        for road in design_input.roads
        if road.class_candidate == "main_road"
    ]
    mapping: dict[str, list[dict[str, Any]]] = {}
    for index, line in enumerate(main_geoms, start=1):
        covered: list[dict[str, Any]] = []
        nearest: list[tuple[float, Any]] = []
        for road in source_main:
            source_line = road.centerline
            source_length = float(source_line.length)
            start = Point(
                float(source_line.coords[0][0]),
                float(source_line.coords[0][1]),
            )
            end = Point(
                float(source_line.coords[-1][0]),
                float(source_line.coords[-1][1]),
            )
            start_distance = float(line.distance(start))
            end_distance = float(line.distance(end))
            midpoint_distance = float(
                source_line.interpolate(0.5).distance(line)
            )
            nearest.append((midpoint_distance, road))
            if (
                source_length <= 0.0
                or start_distance > endpoint_tolerance_m
                or end_distance > endpoint_tolerance_m
            ):
                continue
            start_span = float(line.project(start))
            end_span = float(line.project(end))
            overlap_length = min(
                abs(start_span - end_span), source_length
            )
            coverage_ratio = (
                overlap_length / source_length if source_length > 0 else 0.0
            )
            covered.append(
                {
                    "source_edge_id": road.edge_id,
                    "overlap_length_m": float(overlap_length),
                    "distance_m": float(min(start_distance, end_distance)),
                    "coverage_ratio": float(min(1.0, coverage_ratio)),
                    "heading_delta_deg": _heading_delta_deg(
                        source_line, line
                    ),
                }
            )
        if covered:
            covered.sort(
                key=lambda item: (
                    -item["coverage_ratio"],
                    item["distance_m"],
                    item["source_edge_id"],
                )
            )
            entries = covered
        else:
            entries = [
                {
                    "source_edge_id": road.edge_id,
                    "overlap_length_m": 0.0,
                    "distance_m": float(distance),
                    "coverage_ratio": 0.0,
                    "heading_delta_deg": _heading_delta_deg(
                        road.centerline, line
                    ),
                }
                for distance, road in sorted(
                    nearest,
                    key=lambda item: (item[0], item[1].edge_id),
                )[:3]
            ]
        mapping[f"MAIN-{index:02d}"] = entries
    # every source main edge must appear somewhere in the coarse map: edges whose
    # design corridor was re-routed get a nearest-distance entry on the closest
    # design main road (coverage_ratio 0)
    mapped_ids = {
        entry["source_edge_id"]
        for entries in mapping.values()
        for entry in entries
    }
    for road in source_main:
        if road.edge_id in mapped_ids:
            continue
        nearest_index = min(
            range(len(main_geoms)),
            key=lambda index: (
                road.centerline.distance(main_geoms[index]),
                index,
            ),
        )
        key = f"MAIN-{nearest_index + 1:02d}"
        mapping[key].append(
            {
                "source_edge_id": road.edge_id,
                "overlap_length_m": 0.0,
                "distance_m": float(
                    road.centerline.distance(
                        main_geoms[nearest_index]
                    )
                ),
                "coverage_ratio": 0.0,
                "heading_delta_deg": _heading_delta_deg(
                    road.centerline, main_geoms[nearest_index]
                ),
            }
        )
        mapping[key].sort(
            key=lambda item: (
                -item["coverage_ratio"],
                item["distance_m"],
                item["source_edge_id"],
            )
        )
    return mapping


def _project_point_into_region(point: Point, region: Polygon) -> Point:
    if region.covers(point):
        return point
    return nearest_points(region.boundary, point)[0]


def _grid_route_between(
    start: Point,
    end: Point,
    free_region: Polygon | MultiPolygon,
    *,
    cell_size_m: float = 1.5,
    expand_m: float = 25.0,
) -> LineString | None:
    """Deterministic A* grid route between two points inside ``free_region``.

    The region already excludes the site-boundary overhang and the buffered
    building footprints, so the returned centreline keeps the road corridor
    inside the published site boundary and clear of buildings.
    """
    minx = min(start.x, end.x) - expand_m
    maxx = max(start.x, end.x) + expand_m
    miny = min(start.y, end.y) - expand_m
    maxy = max(start.y, end.y) + expand_m
    cols = max(2, int(math.ceil((maxx - minx) / cell_size_m)) + 1)
    rows = max(2, int(math.ceil((maxy - miny) / cell_size_m)) + 1)

    def grid_point(col: int, row: int) -> Point:
        return Point(minx + col * cell_size_m, miny + row * cell_size_m)

    free: dict[tuple[int, int], bool] = {}
    for col in range(cols):
        for row in range(rows):
            point = grid_point(col, row)
            free[(col, row)] = (
                free_region.covers(point)
                or free_region.distance(point) <= 1e-9
            )

    def nearest_cell(point: Point) -> tuple[int, int] | None:
        best: tuple[float, int, int] | None = None
        for col in range(cols):
            for row in range(rows):
                if not free[(col, row)]:
                    continue
                distance = grid_point(col, row).distance(point)
                if best is None or distance < best[0]:
                    best = (distance, col, row)
        if best is None:
            return None
        return (best[1], best[2])

    start_cell = nearest_cell(start)
    end_cell = nearest_cell(end)
    if start_cell is None or end_cell is None:
        return None
    import heapq

    neighbors = (
        (-1, -1), (-1, 0), (-1, 1),
        (0, -1), (0, 1),
        (1, -1), (1, 0), (1, 1),
    )
    queue: list[tuple[float, int, tuple[int, int]]] = [
        (0.0, 0, start_cell)
    ]
    cost: dict[tuple[int, int], float] = {start_cell: 0.0}
    parent: dict[tuple[int, int], tuple[int, int]] = {}
    visited: set[tuple[int, int]] = set()
    serial = 1
    while queue:
        _, _, current = heapq.heappop(queue)
        if current in visited:
            continue
        visited.add(current)
        if current == end_cell:
            break
        col, row = current
        for delta_col, delta_row in neighbors:
            neighbour = (col + delta_col, row + delta_row)
            if not (0 <= neighbour[0] < cols and 0 <= neighbour[1] < rows):
                continue
            if not free[neighbour]:
                continue
            step = cell_size_m * (
                math.sqrt(2) if delta_col and delta_row else 1.0
            )
            candidate_cost = cost[current] + step
            if (
                neighbour not in cost
                or candidate_cost < cost[neighbour] - 1e-12
            ):
                cost[neighbour] = candidate_cost
                parent[neighbour] = current
                heapq.heappush(
                    queue,
                    (
                        candidate_cost
                        + grid_point(*neighbour).distance(end),
                        serial,
                        neighbour,
                    ),
                )
                serial += 1
    if end_cell not in visited and end_cell not in cost:
        return None
    ordered: list[tuple[int, int]] = [end_cell]
    while ordered[-1] != start_cell:
        if ordered[-1] not in parent:
            return None
        ordered.append(parent[ordered[-1]])
    ordered.reverse()
    coordinates = [
        (float(start.x), float(start.y)),
        *[
            (float(grid_point(col, row).x), float(grid_point(col, row).y))
            for col, row in ordered[1:-1]
        ],
        (float(end.x), float(end.y)),
    ]
    return LineString(_simplify_detour_coords(coordinates, deviation_m=0.15))


def _route_line_inside_region(
    line: LineString,
    free_region: Polygon | MultiPolygon,
    *,
    sample_step_m: float = 1.0,
    cell_size_m: float = 1.5,
    merge_gap_m: float = 15.0,
) -> LineString:
    """Keep free stretches of ``line`` and grid-route every blocked stretch.

    Nearby blocked runs are merged into one gap first; routing the outer anchors
    of a merged gap avoids getting trapped in narrow free pockets near buildings
    and the boundary.
    """
    length = line.length
    samples: list[Point] = []
    distance = 0.0
    while distance <= length:
        samples.append(line.interpolate(distance))
        distance += sample_step_m
    if samples[-1].distance(line.interpolate(length)) > 1e-9:
        samples.append(line.interpolate(length))
    flags = [free_region.covers(point) for point in samples]
    if all(flags):
        return line
    raw_runs: list[list[int]] = []
    index = 0
    while index < len(samples):
        if flags[index]:
            index += 1
            continue
        run_start = index
        while index < len(samples) and not flags[index]:
            index += 1
        raw_runs.append([run_start, index - 1])
    merged_runs: list[list[int]] = []
    for run in raw_runs:
        if (
            merged_runs
            and (run[0] - merged_runs[-1][1] - 1) * sample_step_m
            <= merge_gap_m
        ):
            merged_runs[-1][1] = run[1]
        else:
            merged_runs.append(run)
    coordinates: list[tuple[float, float]] = []
    cursor = 0
    for run_start, run_end in merged_runs:
        for free_index in range(cursor, run_start):
            coordinates.append(
                (float(samples[free_index].x), float(samples[free_index].y))
            )
        anchor_before = (
            samples[run_start - 1] if run_start > 0 else None
        )
        anchor_after = (
            samples[run_end + 1] if run_end + 1 < len(samples) else None
        )
        if anchor_before is None:
            anchor_before = _project_point_into_region(
                samples[run_start], free_region
            )
        if anchor_after is None:
            anchor_after = _project_point_into_region(
                samples[run_end], free_region
            )
        routed = _grid_route_between(
            anchor_before,
            anchor_after,
            free_region,
            cell_size_m=cell_size_m,
        )
        if routed is None:
            routed = LineString(
                [
                    (float(anchor_before.x), float(anchor_before.y)),
                    (float(anchor_after.x), float(anchor_after.y)),
                ]
            )
        for x_value, y_value in list(routed.coords):
            coordinates.append((float(x_value), float(y_value)))
        cursor = run_end + 1
    for free_index in range(cursor, len(samples)):
        coordinates.append(
            (float(samples[free_index].x), float(samples[free_index].y))
        )
    simplified = _simplify_detour_coords(coordinates, deviation_m=0.1)
    if len(simplified) < 2:
        return line
    return LineString(simplified)


def _smooth_line_corners(
    line: LineString,
    *,
    radius_m: float = 1.5,
) -> LineString:
    """Chamfer sharp corners so the mitre corridor does not spike outwards."""
    coordinates = list(line.coords)
    if len(coordinates) <= 2:
        return line
    result: list[tuple[float, float]] = [
        (float(coordinates[0][0]), float(coordinates[0][1]))
    ]
    for index in range(1, len(coordinates) - 1):
        previous = result[-1]
        current = coordinates[index]
        following = coordinates[index + 1]
        v1x, v1y = current[0] - previous[0], current[1] - previous[1]
        v2x, v2y = following[0] - current[0], following[1] - current[1]
        l1 = (v1x * v1x + v1y * v1y) ** 0.5
        l2 = (v2x * v2x + v2y * v2y) ** 0.5
        if l1 < 1e-9 or l2 < 1e-9:
            continue
        distance = min(radius_m, l1 * 0.4, l2 * 0.4)
        first = (
            current[0] - v1x / l1 * distance,
            current[1] - v1y / l1 * distance,
        )
        second = (
            current[0] + v2x / l2 * distance,
            current[1] + v2y / l2 * distance,
        )
        for candidate in (first, second):
            if result[-1] != candidate:
                result.append((float(candidate[0]), float(candidate[1])))
    final = (float(coordinates[-1][0]), float(coordinates[-1][1]))
    if result[-1] != final:
        result.append(final)
    return LineString(result)


def _repair_main_lines_for_boundary(
    main_geoms: list[LineString],
    building_footprints: list[Polygon],
    site_boundary: Polygon,
    half_width: float,
    *,
    margin_m: float = 0.5,
    tolerance_m2: float = 0.01,
) -> tuple[list[LineString], tuple[dict[str, Any], ...]]:
    """Make every main-road corridor sit inside the published site boundary.

    Free space = published boundary eroded by ``half_width + margin_m`` minus the
    building footprints buffered by ``half_width + margin_m``.  Main roads whose
    corridor already fits are untouched; otherwise the blocked stretches are
    re-routed on a deterministic grid while free stretches and all endpoints
    (shared main-road vertices) are preserved.  Endpoints that cannot stay
    outside the eroded boundary are pulled inside; they become corridor-edge
    (site-edge) termini resolved later.
    """
    safe = site_boundary.buffer(-(half_width + margin_m))
    width = 2.0 * half_width
    records: list[dict[str, Any]] = []
    repaired: list[LineString] = []
    boundary_with_tolerance = site_boundary.buffer(0.01)
    footprint_union = unary_union(building_footprints)
    for index, line in enumerate(main_geoms, start=1):
        corridor = _corridor(line, width, round_caps=False)
        boundary_ok = boundary_with_tolerance.covers(corridor)
        if boundary_ok:
            # only a boundary overhang triggers this repair; building overlaps
            # are handled later by the alignment / candidate strategies
            repaired.append(line)
            continue
        def _is_valid(candidate_line: LineString) -> bool:
            candidate_corridor = _corridor(
                candidate_line, width, round_caps=False
            )
            return boundary_with_tolerance.covers(
                candidate_corridor
            ) and (
                candidate_corridor.intersection(footprint_union).area
                <= tolerance_m2
            )

        candidate = line
        for extra_clearance in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
            if _is_valid(candidate):
                break
            blocked = unary_union(
                [
                    footprint.buffer(
                        half_width + margin_m + extra_clearance
                    )
                    for footprint in building_footprints
                ]
            )
            free_region = safe.difference(blocked)
            for cell_size in (1.5, 1.0, 0.75):
                trial = _route_line_inside_region(
                    line, free_region, cell_size_m=cell_size
                )
                trial = _smooth_line_corners(trial)
                if _is_valid(trial):
                    candidate = trial
                    break
            if _is_valid(candidate):
                break
        if not _is_valid(candidate):
            # last resort: re-route the whole road between its endpoints; this
            # is also what a "go around the blocked cluster" plan amounts to
            start = Point(
                float(line.coords[0][0]), float(line.coords[0][1])
            )
            end = Point(
                float(line.coords[-1][0]), float(line.coords[-1][1])
            )
            for extra_clearance in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                if _is_valid(candidate):
                    break
                blocked = unary_union(
                    [
                        footprint.buffer(
                            half_width + margin_m + extra_clearance
                        )
                        for footprint in building_footprints
                    ]
                )
                free_region = safe.difference(blocked)
                for snap in (False, True):
                    route_start = (
                        _project_point_into_region(start, free_region)
                        if snap
                        else start
                    )
                    route_end = (
                        _project_point_into_region(end, free_region)
                        if snap
                        else end
                    )
                    for cell_size in (2.0, 1.5, 1.0):
                        trial = _grid_route_between(
                            route_start,
                            route_end,
                            free_region,
                            cell_size_m=cell_size,
                            expand_m=140.0,
                        )
                        if trial is None:
                            continue
                        trial = _smooth_line_corners(trial)
                        if _is_valid(trial):
                            candidate = trial
                            break
                    if _is_valid(candidate):
                        break
                if _is_valid(candidate):
                    break
        if not _is_valid(candidate):
            # waypoint fallback: force the route through a free sample of the
            # original alignment so it stays near the source corridor
            for extra_clearance in (0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0):
                if _is_valid(candidate):
                    break
                blocked = unary_union(
                    [
                        footprint.buffer(
                            half_width + margin_m + extra_clearance
                        )
                        for footprint in building_footprints
                    ]
                )
                free_region = safe.difference(blocked)
                best_route: LineString | None = None
                for fraction in (0.25, 0.4, 0.55, 0.7, 0.85):
                    via = _project_point_into_region(
                        line.interpolate(line.length * fraction),
                        free_region,
                    )
                    start_route = _grid_route_between(
                        _project_point_into_region(start, free_region)
                        if not free_region.covers(start)
                        else start,
                        via,
                        free_region,
                        cell_size_m=1.5,
                        expand_m=140.0,
                    )
                    end_route = _grid_route_between(
                        via,
                        _project_point_into_region(end, free_region)
                        if not free_region.covers(end)
                        else end,
                        free_region,
                        cell_size_m=1.5,
                        expand_m=140.0,
                    )
                    if start_route is None or end_route is None:
                        continue
                    combined = LineString(
                        list(start_route.coords)
                        + list(end_route.coords)[1:]
                    )
                    combined = _smooth_line_corners(combined)
                    if _is_valid(combined):
                        if (
                            best_route is None
                            or combined.length < best_route.length
                        ):
                            best_route = combined
                if best_route is not None:
                    candidate = best_route
                    break
        repaired.append(candidate)
        after_corridor = _corridor(candidate, width, round_caps=False)
        records.append(
            {
                "road_id": f"MAIN-{index:02d}",
                "boundary_ok_before": bool(boundary_ok),
                "boundary_ok_after": bool(
                    boundary_with_tolerance.covers(after_corridor)
                ),
                "outside_area_before_m2": float(
                    corridor.difference(site_boundary).area
                ),
                "outside_area_after_m2": float(
                    after_corridor.difference(site_boundary).area
                ),
                "boundary_margin_after_m": float(
                    site_boundary.exterior.distance(after_corridor)
                ),
                "vertices_before": len(list(line.coords)),
                "vertices_after": len(list(candidate.coords)),
                "max_vertex_displacement_m": float(
                    max(
                        (
                            line.distance(Point(float(x), float(y)))
                            for x, y in candidate.coords
                        ),
                        default=0.0,
                    )
                ),
                "reason": (
                    "the source main-road corridor overhung the published site "
                    "boundary (site-edge terminus / north boundary); the "
                    "blocked stretches were re-routed inside the boundary-safe "
                    "free space, free stretches and endpoints preserved"
                ),
            }
        )
    return repaired, tuple(records)


def _retract_endpoint_clear_of_obstacles(
    line: LineString,
    end_index: int,
    building_footprints: list[Polygon],
    site_boundary: Polygon,
    width: float,
    *,
    step_m: float = 0.5,
    tolerance_m2: float = 0.01,
) -> tuple[LineString, tuple[float, float], float] | None:
    """Pull a dangling endpoint back along its own road until the corridor clears.

    Used when a moved building leaves a fringe road whose corridor now touches a
    footprint: the dead end is retracted instead of crossing the building, which
    is also the precondition for a clean bridge afterwards.
    """
    coordinates = list(line.coords)
    if len(coordinates) < 2:
        return None
    footprint_union = unary_union(building_footprints)
    site_with_tolerance = site_boundary.buffer(0.01)
    if end_index == 1:
        tip = Point(float(coordinates[-1][0]), float(coordinates[-1][1]))
        adjacent = Point(
            float(coordinates[-2][0]), float(coordinates[-2][1])
        )
    else:
        tip = Point(float(coordinates[0][0]), float(coordinates[0][1]))
        adjacent = Point(
            float(coordinates[1][0]), float(coordinates[1][1])
        )
    inward = (adjacent.x - tip.x, adjacent.y - tip.y)
    norm = (inward[0] ** 2 + inward[1] ** 2) ** 0.5
    if norm < 1e-12:
        return None
    unit = (inward[0] / norm, inward[1] / norm)
    distance = step_m
    while distance < line.length - 1.0:
        new_tip = (
            tip.x + unit[0] * distance,
            tip.y + unit[1] * distance,
        )
        if end_index == 1:
            new_coordinates = coordinates[:-1] + [new_tip]
        else:
            new_coordinates = [new_tip] + coordinates[1:]
        candidate = LineString(new_coordinates)
        corridor = _corridor(candidate, width, round_caps=False)
        new_tip_point = Point(float(new_tip[0]), float(new_tip[1]))
        clearance_ok = (
            footprint_union.distance(new_tip_point)
            >= width / 2.0 + 0.25
        )
        if (
            clearance_ok
            and corridor.intersection(footprint_union).area
            <= tolerance_m2
            and site_with_tolerance.covers(corridor)
        ):
            return candidate, new_tip, float(distance)
        distance += step_m
    return None


def build_road_layout(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    *,
    alignment_mode: str = "auto",
    diversion_side: str = "auto",
    diversion_margin_m: float = 0.5,
) -> RoadLayout:
    """Build the complete design road network.

    ``alignment_mode``:
      * ``"auto"`` (default) — repair main-road/building conflicts locally and
        fall back to minimum-overlap shifts and diversions (the M4c-2 design);
      * ``"none"`` — keep the merged source main-road geometry unchanged
        (candidate A: the buildings are moved instead).
    ``diversion_side`` selects the side used when a main road is diverted around
    a conflict cluster: ``"auto"`` (shortest), ``"east"``/``"west"``/
    ``"north"``/``"south"``.  It only affects the fallback diversion.
    """
    if alignment_mode not in {"auto", "none"}:
        raise ValueError(
            f"unknown alignment_mode {alignment_mode!r}; "
            "expected 'auto' or 'none'"
        )
    main_lines, source_main_ids = _main_lines(design_input)
    main_union = unary_union(main_lines) if main_lines else None
    # mutable main geometries: explicit junction vertices are inserted here
    main_geoms = [LineString(line.coords) for line in main_lines]

    road_widths = basis.road_widths
    branch_width = road_widths["branch_road"]
    sidewalks_width = basis.sidewalk_width_m
    all_buildings = list(building_layout.buildings)
    by_id = {item.building_id: item for item in all_buildings}
    building_footprints = [item.footprint for item in all_buildings]
    footprint_tree = STRtree(building_footprints)
    focus_building_ids = {
        item.building_id for item in building_layout.focus_buildings
    }
    focus_footprint_indices = {
        index
        for index, item in enumerate(all_buildings)
        if item.building_id in focus_building_ids
    }
    new_access_corridors: list[Polygon] = []
    footprint_overlap_m2: dict[int, float] = {}

    def accumulate_overlap(corridor: Polygon) -> None:
        for item in footprint_tree.query(corridor):
            footprint_index = int(item)
            footprint_overlap_m2[footprint_index] = (
                footprint_overlap_m2.get(footprint_index, 0.0)
                + corridor.intersection(
                    building_footprints[footprint_index]
                ).area
            )

    # ---- freeze the group access terminals on the pre-alignment network -----
    # M4c-1e evidence requires the terminal coordinates to stay fixed; a main
    # road detour may only move the branch/junction start, never the terminal.
    focus_group = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    focus_box = box(*intent.focus_bbox)
    adjacent_building_ids: set[str] = set()
    for group in intent.groups:
        if group.group_id == intent.focus_group_id:
            continue
        if box(*group.bbox).intersects(focus_box):
            adjacent_building_ids.update(
                building_id
                for building_id in group.building_ids
                if building_id in by_id
            )
    pre_loop_ring, pre_loop_included_ids = _loop_hull(
        building_layout, adjacent_building_ids
    )
    pre_loop = LineString(pre_loop_ring.coords)
    pre_budget: dict[int, float] = {}

    def pre_accumulate(corridor: Polygon) -> None:
        for item in footprint_tree.query(corridor):
            footprint_index = int(item)
            pre_budget[footprint_index] = (
                pre_budget.get(footprint_index, 0.0)
                + corridor.intersection(
                    building_footprints[footprint_index]
                ).area
            )

    focus_clearance_footprints = [
        item.footprint for item in building_layout.focus_buildings
    ]
    focus_clearance_m = basis.building_road_clearance_m
    class_options = tuple(
        (class_name, road_widths[width_key])
        for class_name, width_key in GROUP_ACCESS_CLASS_OPTIONS
    )
    pre_existing: list[LineString] = []
    pre_accumulate(
        _corridor(pre_loop, road_widths["access_road"], round_caps=True)
    )
    if main_union is not None:
        pre_main_point = nearest_points(
            main_union, Point(focus_group.centroid)
        )[0]
        pre_loop_point = nearest_points(pre_loop, pre_main_point)[0]
        if pre_main_point.distance(pre_loop_point) >= 2.0:
            provisional_focus = LineString(
                [
                    (float(pre_main_point.x), float(pre_main_point.y)),
                    (float(pre_loop_point.x), float(pre_loop_point.y)),
                ]
            )
            pre_accumulate(
                _corridor(
                    provisional_focus, branch_width, round_caps=True
                )
            )
            pre_existing.append(provisional_focus)
    fixed_terminals: dict[str, tuple[float, float]] = {}
    fixed_networks: dict[str, tuple[str, int]] = {}
    for group in intent.groups:
        group_buildings = [
            by_id[building_id]
            for building_id in group.building_ids
            if building_id in by_id
        ]
        if not group_buildings:
            continue
        group_union = unary_union(
            [item.footprint for item in group_buildings]
        )
        pre_network = [
            ("main", index, geom)
            for index, geom in enumerate(main_geoms)
        ] + [("loop", -1, pre_loop)]
        pre_choice = _choose_group_access(
            group_union,
            pre_network,
            building_footprints,
            footprint_tree,
            pre_existing,
            branch_width,
            pre_budget,
            focus_footprint_indices,
            focus_clearance_footprints,
            focus_clearance_m,
            class_options,
        )
        if pre_choice is None:
            continue
        terminal = (
            float(pre_choice["terminal"][0]),
            float(pre_choice["terminal"][1]),
        )
        fixed_terminals[group.group_id] = terminal
        fixed_networks[group.group_id] = (
            str(pre_choice["kind"]),
            int(pre_choice["index"]),
        )
        pre_centerline = LineString(
            [
                (
                    float(pre_choice["attach"][0]),
                    float(pre_choice["attach"][1]),
                ),
                terminal,
            ]
        )
        pre_accumulate(
            _corridor(
                pre_centerline,
                float(pre_choice["width"]),
                round_caps=True,
            )
        )
        pre_existing.append(pre_centerline)

    # ---- main-road alignment: local detours remove corridor/building overlap
    main_overlap_before = float(
        unary_union(
            [
                _corridor(line, road_widths["main_road"], round_caps=False)
                for line in main_geoms
            ]
        )
        .intersection(unary_union(building_footprints))
        .area
    )
    main_alignment_records: tuple[dict[str, Any], ...] = ()
    # ---- boundary-safe base geometry: every main corridor must sit inside the
    # ---- published site boundary (arch-core hard gate)
    main_geoms, main_boundary_repairs = _repair_main_lines_for_boundary(
        main_geoms,
        building_footprints,
        design_input.site_boundary,
        road_widths["main_road"] / 2.0,
    )
    if alignment_mode == "auto":
        main_geoms, main_alignment_records = _align_main_lines(
            main_geoms,
            building_footprints,
            [item.building_id for item in all_buildings],
            road_widths["main_road"],
            road_widths["main_road"] / 2
            + basis.building_road_clearance_m,
            diversion_side=diversion_side,
            diversion_margin_m=diversion_margin_m,
        )
        main_alignment_records = tuple(
            {**record, "source_edge_ids": list(source_main_ids)}
            for record in main_alignment_records
        )

    explicit_junctions: list[dict[str, Any]] = []
    connector_specs: list[
        tuple[str, str, LineString, str | None, str | None]
    ] = []

    def attach_to_main(
        edge_id: str, point: Point
    ) -> tuple[tuple[float, float], str]:
        """Insert ``point`` as a shared vertex on the nearest main line."""
        best_index, best_distance = None, float("inf")
        for index, geom in enumerate(main_geoms):
            distance = geom.distance(point)
            if best_index is None or distance < best_distance:
                best_index, best_distance = index, distance
        assert best_index is not None, "no main line to attach to"
        new_line, xy = _insert_vertex(main_geoms[best_index], point)
        main_geoms[best_index] = new_line
        main_edge_id = f"MAIN-{best_index + 1:02d}"
        junction_id = _add_or_merge_junction(
            explicit_junctions, xy, (main_edge_id, edge_id)
        )
        return xy, junction_id

    # ---- focus access loop: fixed-point hull around every building it could
    # ---- hit, so the loop corridor never overlaps a footprint ---------------
    focus_box = box(*intent.focus_bbox)
    adjacent_building_ids: set[str] = set()
    for group in intent.groups:
        if group.group_id == intent.focus_group_id:
            continue
        if box(*group.bbox).intersects(focus_box):
            adjacent_building_ids.update(
                building_id
                for building_id in group.building_ids
                if building_id in by_id
            )
    loop_ring, loop_included_ids = _loop_hull(
        building_layout, adjacent_building_ids
    )
    access_loop = LineString(loop_ring.coords)
    loop_corridor = _corridor(
        access_loop, road_widths["access_road"], round_caps=True
    )
    new_access_corridors.append(loop_corridor)
    accumulate_overlap(loop_corridor)

    # loop/x main crossings become explicit shared-vertex junctions
    for index, main_geom in enumerate(main_geoms):
        for point in _point_list(access_loop.intersection(main_geom)):
            xy = (float(point.x), float(point.y))
            main_geoms[index] = _insert_vertex_at(main_geoms[index], xy)
            access_loop = _insert_vertex_at(access_loop, xy)
            _add_or_merge_junction(
                explicit_junctions,
                xy,
                (f"MAIN-{index + 1:02d}", "ACC-FOCUS-01"),
            )

    focus_group = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    loop_junction_id: str | None = None
    if main_union is not None:
        main_point = nearest_points(
            main_union, Point(focus_group.centroid)
        )[0]
        loop_point = nearest_points(access_loop, main_point)[0]
        if main_point.distance(loop_point) >= 2.0:
            main_xy, main_junction_id = attach_to_main("BR-FOCUS", main_point)
            access_loop, loop_xy = _insert_vertex(access_loop, loop_point)
            loop_junction_id = _add_or_merge_junction(
                explicit_junctions,
                loop_xy,
                ("BR-FOCUS", "ACC-FOCUS-01"),
            )
            connector_specs.append(
                (
                    "BR-FOCUS",
                    "branch",
                    LineString([main_xy, loop_xy]),
                    main_junction_id,
                    loop_junction_id,
                    (),
                    None,
                )
            )
            focus_corridor = _corridor(
                connector_specs[-1][2], branch_width, round_caps=True
            )
            new_access_corridors.append(focus_corridor)
            accumulate_overlap(focus_corridor)

    # ---- design-aware group access: connector roads for every group with buildings ----
    existing_connector_lines = [
        spec[2] for spec in connector_specs
    ]
    focus_clearance_footprints = [
        item.footprint for item in building_layout.focus_buildings
    ]
    focus_clearance_m = basis.building_road_clearance_m
    class_options = tuple(
        (class_name, road_widths[width_key])
        for class_name, width_key in GROUP_ACCESS_CLASS_OPTIONS
    )
    unserved_group_ids: list[str] = []
    terminal_frozen_violations: list[str] = []
    group_access_count = 0
    group_access_branch_count = 0
    group_access_lane_count = 0
    for group in intent.groups:
        group_buildings = [
            by_id[building_id]
            for building_id in group.building_ids
            if building_id in by_id
        ]
        if not group_buildings:
            continue
        group_union = unary_union(
            [item.footprint for item in group_buildings]
        )
        network = [
            ("main", index, geom)
            for index, geom in enumerate(main_geoms)
        ] + [("loop", -1, access_loop)]
        fixed_terminal = fixed_terminals.get(group.group_id)
        fixed_network = fixed_networks.get(group.group_id)
        choice = _choose_group_access(
            group_union,
            network,
            building_footprints,
            footprint_tree,
            existing_connector_lines,
            branch_width,
            footprint_overlap_m2,
            focus_footprint_indices,
            focus_clearance_footprints,
            focus_clearance_m,
            class_options,
            fixed_terminal=fixed_terminal,
            fixed_network=fixed_network,
        )
        if choice is None and fixed_terminal is not None:
            # frozen terminal/attachment not reachable from the adjusted
            # network: retry the same terminal anywhere, then the free ring
            terminal_frozen_violations.append(group.group_id)
            choice = _choose_group_access(
                group_union,
                network,
                building_footprints,
                footprint_tree,
                existing_connector_lines,
                branch_width,
                footprint_overlap_m2,
                focus_footprint_indices,
                focus_clearance_footprints,
                focus_clearance_m,
                class_options,
                fixed_terminal=fixed_terminal,
            )
        if choice is None and fixed_terminal is not None:
            choice = _choose_group_access(
                group_union,
                network,
                building_footprints,
                footprint_tree,
                existing_connector_lines,
                branch_width,
                footprint_overlap_m2,
                focus_footprint_indices,
                focus_clearance_footprints,
                focus_clearance_m,
                class_options,
            )
        if choice is None:
            unserved_group_ids.append(group.group_id)
            continue
        class_name = str(choice["class_name"])
        edge_id = (
            f"BR-{group.group_id}"
            if class_name == "branch"
            else f"ACC-{group.group_id}"
        )
        kind = str(choice["kind"])
        index = int(choice["index"])
        if kind == "main":
            new_line, xy = _insert_vertex(
                main_geoms[index], Point(choice["attach"])
            )
            main_geoms[index] = new_line
            junction_id = _add_or_merge_junction(
                explicit_junctions,
                xy,
                (f"MAIN-{index + 1:02d}", edge_id),
            )
        else:
            access_loop, xy = _insert_vertex(
                access_loop, Point(choice["attach"])
            )
            junction_id = _add_or_merge_junction(
                explicit_junctions,
                xy,
                ("ACC-FOCUS-01", edge_id),
            )
        terminal = (
            float(choice["terminal"][0]),
            float(choice["terminal"][1]),
        )
        centerline = LineString([xy, terminal])
        connector_specs.append(
            (
                edge_id,
                class_name,
                centerline,
                junction_id,
                None,
                (group.group_id,),
                (float(terminal[0]), float(terminal[1])),
            )
        )
        access_corridor = _corridor(
            centerline, float(choice["width"]), round_caps=True
        )
        new_access_corridors.append(access_corridor)
        accumulate_overlap(access_corridor)
        existing_connector_lines.append(centerline)
        group_access_count += 1
        if class_name == "branch":
            group_access_branch_count += 1
        else:
            group_access_lane_count += 1

    # ---- dead-end resolution: no unresolved design dead ends remain ---------
    buildings_union = unary_union(building_footprints)
    connector_lines = [spec[2] for spec in connector_specs]
    all_centerlines = list(main_geoms) + connector_lines + [access_loop]
    site_boundary_line = design_input.site_boundary.boundary
    main_count = len(main_geoms)
    dead_end_resolutions: list[dict[str, Any]] = []
    candidate_dead_ends = [
        (line_index, end_index, xy)
        for xy, line_index, end_index in _noded_degree_one_endpoints(
            all_centerlines
        )
        if line_index < main_count
    ]
    for line_index, end_index, xy in sorted(candidate_dead_ends):
        source_id = f"MAIN-{line_index + 1:02d}"
        point = Point(float(xy[0]), float(xy[1]))
        boundary_distance = float(site_boundary_line.distance(point))
        resolution: dict[str, Any] = {
            "node_id": f"DE-{source_id}",
            "road_id": source_id,
            "original_xy": [float(xy[0]), float(xy[1])],
            "strategy": None,
            "adjusted_xy": None,
            "bridge_road_id": None,
            "junction_id": None,
            "displacement_m": 0.0,
            "boundary_distance_m": boundary_distance,
            "criterion_met": True,
            "boundary_margin_m": None,
            "extended_to_site_boundary": False,
            "extension_length_m": None,
            "extension_direction_cross": None,
            "extension_angle_deg": None,
            "boundary_band_m": None,
            "vertices_added": 0,
            "vertices_removed": 0,
            "reason": "",
        }
        corridor_geometry = _corridor(
            main_geoms[line_index],
            road_widths["main_road"],
            round_caps=False,
        )
        boundary_with_tolerance = design_input.site_boundary.buffer(0.01)
        corridor_inside_boundary = boundary_with_tolerance.covers(
            corridor_geometry
        )
        if corridor_inside_boundary:
            corridor_edge_margin = float(
                design_input.site_boundary.exterior.distance(
                    corridor_geometry
                )
            )
        else:
            penetration = 0.0
            for polygon in _polygon_list(
                corridor_geometry.difference(design_input.site_boundary)
            ):
                for x_value, y_value in polygon.exterior.coords:
                    penetration = max(
                        penetration,
                        float(
                            design_input.site_boundary.exterior.distance(
                                Point(float(x_value), float(y_value))
                            )
                        ),
                    )
            corridor_edge_margin = -float(penetration)
        near_boundary = (
            boundary_distance
            <= road_widths["main_road"] / 2.0 + 2.5
            or (corridor_inside_boundary and corridor_edge_margin <= 2.5)
        )
        if near_boundary:
            # the corridor edge sits at (or just inside) the published
            # boundary: this dangling end is the corridor-edge terminus of a
            # site-clipped road, not a planning dead end
            resolution.update(
                strategy="site_edge_terminus",
                adjusted_xy=[float(xy[0]), float(xy[1])],
                boundary_margin_m=float(corridor_edge_margin),
                reason=(
                    "endpoint is "
                    f"{boundary_distance:.3f} m from the published site "
                    "boundary, so the 12 m main corridor edge is "
                    f"{corridor_edge_margin:+.3f} m from the boundary "
                    "(inside/at the boundary); the source network is clipped "
                    "at the boundary and the road ends at its corridor-safe "
                    "boundary line - a legitimate site-edge terminus, not a "
                    "road continuing outside the site"
                ),
            )
        else:
            bridge = _find_main_bridge(
                source_id,
                line_index,
                end_index,
                point,
                main_geoms,
                connector_lines,
                access_loop,
                buildings_union,
                road_widths["main_road"],
                focus_clearance_footprints,
                focus_clearance_m,
            )
            if bridge is not None:
                (
                    bridge_length,
                    target_index,
                    candidate_xy,
                ) = bridge
                current_line = main_geoms[line_index]
                coordinates = list(current_line.coords)
                if end_index == 0:
                    new_coordinates = [candidate_xy] + coordinates
                else:
                    new_coordinates = coordinates + [candidate_xy]
                main_geoms[line_index] = LineString(new_coordinates)
                target_id = f"MAIN-{target_index + 1:02d}"
                main_geoms[target_index] = _insert_vertex_at(
                    main_geoms[target_index], candidate_xy
                )
                junction_id = _add_or_merge_junction(
                    explicit_junctions,
                    candidate_xy,
                    (source_id, target_id),
                )
                resolution.update(
                    strategy="bridged",
                    adjusted_xy=[
                        float(candidate_xy[0]),
                        float(candidate_xy[1]),
                    ],
                    bridge_road_id=target_id,
                    junction_id=junction_id,
                    displacement_m=float(bridge_length),
                    vertices_added=2,
                    reason=(
                        "dangling main stub bridged "
                        f"{bridge_length:.3f} m to {target_id} with an "
                        "explicit shared-vertex junction (bridge corridor does "
                        "not touch a building footprint)"
                    ),
                )
            else:
                trimmed = _trim_main_to_junction(
                    source_id,
                    line_index,
                    end_index,
                    main_geoms[line_index],
                    explicit_junctions,
                )
                if trimmed is not None:
                    (
                        new_line,
                        junction_xy,
                        displacement,
                        removed_vertices,
                    ) = trimmed
                    main_geoms[line_index] = new_line
                    resolution.update(
                        strategy="trimmed",
                        adjusted_xy=[
                            float(junction_xy[0]),
                            float(junction_xy[1]),
                        ],
                        displacement_m=float(displacement),
                        vertices_removed=int(removed_vertices),
                        reason=(
                            "dangling tail trimmed back to the last explicit "
                            "junction; the road keeps its id and stays "
                            "connected at that junction"
                        ),
                    )
                else:
                    retracted = _retract_endpoint_clear_of_obstacles(
                        main_geoms[line_index],
                        end_index,
                        building_footprints,
                        design_input.site_boundary,
                        road_widths["main_road"],
                    )
                    bridged_after_retract = None
                    if retracted is not None:
                        (
                            retracted_line,
                            retracted_xy,
                            retract_distance,
                        ) = retracted
                        main_geoms[line_index] = retracted_line
                        retracted_point = Point(
                            float(retracted_xy[0]),
                            float(retracted_xy[1]),
                        )
                        bridged_after_retract = _find_main_bridge(
                            source_id,
                            line_index,
                            end_index,
                            retracted_point,
                            main_geoms,
                            connector_lines,
                            access_loop,
                            buildings_union,
                            road_widths["main_road"],
                            focus_clearance_footprints,
                            focus_clearance_m,
                        )
                        if bridged_after_retract is not None:
                            (
                                bridge_length,
                                target_index,
                                candidate_xy,
                            ) = bridged_after_retract
                            source_coordinates = list(
                                main_geoms[line_index].coords
                            )
                            if end_index == 0:
                                main_geoms[line_index] = LineString(
                                    [candidate_xy] + source_coordinates
                                )
                            else:
                                main_geoms[line_index] = LineString(
                                    source_coordinates + [candidate_xy]
                                )
                            target_id = f"MAIN-{target_index + 1:02d}"
                            main_geoms[target_index] = _insert_vertex_at(
                                main_geoms[target_index], candidate_xy
                            )
                            junction_id = _add_or_merge_junction(
                                explicit_junctions,
                                candidate_xy,
                                (source_id, target_id),
                            )
                            resolution.update(
                                strategy="bridged",
                                adjusted_xy=[
                                    float(candidate_xy[0]),
                                    float(candidate_xy[1]),
                                ],
                                bridge_road_id=target_id,
                                junction_id=junction_id,
                                displacement_m=float(
                                    retract_distance + bridge_length
                                ),
                                vertices_added=2,
                                reason=(
                                    "dangling stub first retracted "
                                    f"{retract_distance:.3f} m to clear a "
                                    "building footprint, then bridged "
                                    f"{bridge_length:.3f} m to {target_id} "
                                    "with an explicit shared-vertex junction"
                                ),
                            )
                    if bridged_after_retract is None:
                        resolution.update(
                            strategy="site_edge_terminus",
                            adjusted_xy=[float(xy[0]), float(xy[1])],
                            criterion_met=False,
                            reason=(
                                "unresolved: no bridge target within 40 m, no "
                                "junction to trim to and no clean retraction; "
                                f"the endpoint is {boundary_distance:.3f} m "
                                "from the published boundary"
                            ),
                        )
        dead_end_resolutions.append(resolution)
    main_overlap_after = float(
        unary_union(
            [
                _corridor(line, road_widths["main_road"], round_caps=False)
                for line in main_geoms
            ]
        )
        .intersection(buildings_union)
        .area
    )

    # ---- build road objects -------------------------------------------------
    roads: list[RoadDesign] = []
    for index, line in enumerate(main_geoms, start=1):
        roads.append(
            _road(
                f"MAIN-{index:02d}",
                "main",
                road_widths["main_road"],
                line,
                is_new=False,
                reason=(
                    "merged main-road alignment from the source main edges; "
                    "the skeleton mesh is simplified"
                ),
                source_edge_ids=source_main_ids,
                source_trace_ref=(
                    source_main_ids[0] if source_main_ids else None
                ),
            )
        )
    for (
        edge_id,
        class_name,
        centerline,
        start_j,
        end_j,
        serves_group_ids,
        access_terminal_xy,
    ) in connector_specs:
        if edge_id == "BR-FOCUS":
            reason = (
                "design branch from the main road to the focus-group "
                "access loop"
            )
        else:
            reason = (
                "design group access road "
                f"({class_name} class): terminal is "
                f"{ACCESS_TERMINAL_DISTANCE_M:.1f} m outside the nearest "
                "group building frontage (clearance + 0.5 m), with the "
                "route checked against every building footprint"
            )
        roads.append(
            _road(
                edge_id,
                class_name,
                (
                    branch_width
                    if class_name == "branch"
                    else road_widths["access_road"]
                ),
                centerline,
                is_new=True,
                reason=reason,
                round_caps=True,
                start_junction_id=start_j,
                end_junction_id=end_j,
                serves_group_ids=serves_group_ids,
                access_terminal_xy=access_terminal_xy,
            )
        )
    roads.append(
        _road(
            "ACC-FOCUS-01",
            "access",
            road_widths["access_road"],
            access_loop,
            is_new=True,
            reason=(
                "design access loop around the focus-group rows; the hull is "
                "expanded until no building footprint intersects the loop "
                "corridor"
            ),
            round_caps=True,
            start_junction_id=None,
            end_junction_id=None,
        )
    )

    corridor_union = unary_union([road.corridor for road in roads])
    sidewalk_parts = [
        road.centerline.buffer(
            road.width_m / 2 + sidewalks_width,
            cap_style="round" if road.class_name != "main" else "flat",
            join_style="round",
        )
        for road in roads
    ]
    sidewalk_union = unary_union(sidewalk_parts).difference(
        corridor_union
    )
    if sidewalk_union.geom_type == "GeometryCollection":
        sidewalk_union = unary_union(
            [
                item
                for item in sidewalk_union.geoms
                if item.geom_type in {"Polygon", "MultiPolygon"}
            ]
        )

    if corridor_union.geom_type == "Polygon":
        corridor_union_pieces = 1
    elif corridor_union.geom_type == "MultiPolygon":
        corridor_union_pieces = len(corridor_union.geoms)
    else:
        corridor_union_pieces = 0

    # ---- honest overlap evidence: new access vs the pre-existing main floor
    new_access_roads = [
        road for road in roads if road.class_name in {"branch", "access"}
    ]
    main_roads = [road for road in roads if road.class_name == "main"]
    overlap_new_access = float(
        unary_union([road.corridor for road in new_access_roads])
        .intersection(buildings_union)
        .area
    )
    #: ``road_building_overlap_m2_main`` keeps the *before* value: the source
    #: alignment conflict recorded by M4c-1b (38.19 m2) is now repaired, and
    #: the residual after-alignment overlap is reported separately.
    overlap_main_before = main_overlap_before
    overlap_main_after = main_overlap_after
    overlap_total = float(
        corridor_union.intersection(buildings_union).area
    )

    noded_topology = noded_road_topology(
        tuple(roads), tuple(explicit_junctions)
    )
    #: node labels are positional; the counts are the real noded graph counts
    junction_nodes = tuple(
        f"JN-{index:02d}"
        for index in range(1, noded_topology.junction_count + 1)
    )
    dead_end_nodes = tuple(
        f"DE-{index:02d}"
        for index in range(1, noded_topology.dead_end_count + 1)
    )

    # ---- published-boundary containment (arch-core hard gate) --------------
    boundary_tolerance = design_input.site_boundary.buffer(0.01)
    main_corridor_union = unary_union(
        [road.corridor for road in roads if road.class_name == "main"]
    )
    main_boundary_ok = bool(boundary_tolerance.covers(main_corridor_union))
    if main_boundary_ok:
        main_boundary_margin_m = float(
            design_input.site_boundary.exterior.distance(
                main_corridor_union
            )
        )
    else:
        penetration = 0.0
        for polygon in _polygon_list(
            main_corridor_union.difference(design_input.site_boundary)
        ):
            for x_value, y_value in polygon.exterior.coords:
                penetration = max(
                    penetration,
                    float(
                        design_input.site_boundary.exterior.distance(
                            Point(float(x_value), float(y_value))
                        )
                    ),
                )
        main_boundary_margin_m = -float(penetration)

    simplification = {
        "source_edge_count": len(design_input.roads),
        "source_main_edge_count": len(source_main_ids),
        "source_blue_edge_count": (
            len(design_input.roads) - len(source_main_ids)
        ),
        "design_main_line_count": len(main_geoms),
        "design_branch_count": sum(
            1 for road in roads if road.class_name == "branch"
        ),
        "design_group_access_count": group_access_count,
        "design_group_access_branch_count": group_access_branch_count,
        "design_group_access_lane_count": group_access_lane_count,
        "design_access_count": sum(
            1 for road in roads if road.class_name == "access"
        ),
        "group_access_unserved_ids": list(unserved_group_ids),
        "terminal_frozen_violations": list(terminal_frozen_violations),
        "access_terminal_distance_m": ACCESS_TERMINAL_DISTANCE_M,
        "loop_hull_included_building_ids": list(loop_included_ids),
        "road_building_overlap_m2_new_access": overlap_new_access,
        "road_building_overlap_m2_main": overlap_main_before,
        "road_building_overlap_m2_main_after": overlap_main_after,
        "road_building_overlap_m2_total": overlap_total,
        "main_overlap_resolved": bool(overlap_main_after <= 0.01),
        "main_boundary_ok": bool(main_boundary_ok),
        "main_boundary_margin_m": float(main_boundary_margin_m),
        "main_boundary_repair_count": len(main_boundary_repairs),
        "main_boundary_repairs": [dict(item) for item in main_boundary_repairs],
        "main_alignment_road_count": len(main_alignment_records),
        "main_alignment_vertices_added": sum(
            record["vertices_added"] for record in main_alignment_records
        ),
        "main_alignment_vertices_removed": sum(
            record["vertices_removed"] for record in main_alignment_records
        ),
        "dead_end_resolution_count": len(dead_end_resolutions),
        "dead_end_resolution_strategies": {
            strategy: sum(
                1
                for record in dead_end_resolutions
                if record["strategy"] == strategy
            )
            for strategy in (
                "site_edge_terminus",
                "bridged",
                "trimmed",
            )
        },
        "road_building_overlap_note": (
            "new access = generated branch/access corridors only; main = the "
            "pre-existing source-alignment conflict recorded before M4c-2 "
            "(38.19 m2) - now repaired, with the residual reported as "
            "road_building_overlap_m2_main_after"
        ),
        "source_blue_edges_replaced_by_design": True,
        "note": (
            "the 333-edge skeleton mesh is source evidence, not the design "
            "road network; the design uses merged main roads, one design-aware "
            "access branch per group with buildings and one access loop for "
            "the focus group"
        ),
    }
    return RoadLayout(
        roads=tuple(roads),
        corridor_union=corridor_union,
        sidewalk_union=sidewalk_union,
        junction_nodes=junction_nodes,
        dead_end_nodes=dead_end_nodes,
        corridor_generator="round_buffer_hierarchy_v0.1",
        not_professional_alignment=True,
        corridor_union_pieces=corridor_union_pieces,
        noded_topology=noded_topology,
        explicit_junctions=tuple(explicit_junctions),
        simplification=simplification,
        road_building_overlap_m2_new_access=overlap_new_access,
        road_building_overlap_m2_main=overlap_main_before,
        road_building_overlap_m2_main_after=overlap_main_after,
        road_building_overlap_m2_total=overlap_total,
        main_overlap_resolved=bool(overlap_main_after <= 0.01),
        main_alignment_records=main_alignment_records,
        dead_end_resolutions=tuple(dead_end_resolutions),
        group_access_unserved=tuple(unserved_group_ids),
        source_segment_map=_source_segment_map(
            main_geoms, design_input, road_widths["main_road"]
        ),
        main_boundary_repairs=main_boundary_repairs,
    )

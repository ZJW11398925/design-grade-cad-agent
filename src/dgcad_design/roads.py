from __future__ import annotations

from dataclasses import dataclass
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
            "road_building_overlap_m2_total": (
                self.road_building_overlap_m2_total
            ),
            "group_access_unserved": list(self.group_access_unserved),
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
) -> dict[str, Any] | None:
    """Pick a clean access branch: group frontage terminal + network attach."""
    terminals: list[Point] = []
    for polygon in _polygon_list(
        group_union.buffer(_TERMINAL_RING_M)
    ):
        terminals.extend(
            _sample_ring(
                LineString(polygon.exterior.coords),
                ACCESS_CANDIDATE_STEP_M,
            )
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
                length < ACCESS_BRANCH_MIN_LENGTH_M
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


def build_road_layout(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
) -> RoadLayout:
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
                )
            )
            focus_corridor = _corridor(
                connector_specs[-1][2], branch_width, round_caps=True
            )
            new_access_corridors.append(focus_corridor)
            accumulate_overlap(focus_corridor)

    # ---- design-aware group access: one branch per group with buildings ----
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
            (edge_id, class_name, centerline, junction_id, None)
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
    for edge_id, class_name, centerline, start_j, end_j in connector_specs:
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
    buildings_union = unary_union(building_footprints)
    new_access_roads = [
        road for road in roads if road.class_name in {"branch", "access"}
    ]
    main_roads = [road for road in roads if road.class_name == "main"]
    overlap_new_access = float(
        unary_union([road.corridor for road in new_access_roads])
        .intersection(buildings_union)
        .area
    )
    overlap_main = float(
        unary_union([road.corridor for road in main_roads])
        .intersection(buildings_union)
        .area
    )
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
        "access_terminal_distance_m": ACCESS_TERMINAL_DISTANCE_M,
        "loop_hull_included_building_ids": list(loop_included_ids),
        "road_building_overlap_m2_new_access": overlap_new_access,
        "road_building_overlap_m2_main": overlap_main,
        "road_building_overlap_m2_total": overlap_total,
        "road_building_overlap_note": (
            "new access = generated branch/access corridors only; main = "
            "pre-existing source alignment vs coarse full-site context, not "
            "repaired in M4c-1b (M4c-2/full-site scope)"
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
        road_building_overlap_m2_main=overlap_main,
        road_building_overlap_m2_total=overlap_total,
        group_access_unserved=tuple(unserved_group_ids),
    )

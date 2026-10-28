from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import linemerge, nearest_points, unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .input import DesignInput, RoadInput
from .intent import DesignIntent
from .topology import NodedRoadTopology, noded_road_topology


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

    explicit_junctions: list[dict[str, Any]] = []

    def add_junction(
        xy: tuple[float, float],
        road_ids: tuple[str, ...],
    ) -> str:
        junction_id = f"J-{len(explicit_junctions) + 1:02d}"
        explicit_junctions.append(
            {
                "id": junction_id,
                "x": float(xy[0]),
                "y": float(xy[1]),
                "road_ids": list(road_ids),
            }
        )
        return junction_id

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
        junction_id = add_junction(xy, (main_edge_id, edge_id))
        return xy, junction_id

    # connector road specs: (edge_id, class, centerline, start_j, end_j)
    connector_specs: list[
        tuple[str, str, LineString, str | None, str | None]
    ] = []

    focus_group = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    focus_union = unary_union(
        [item.footprint for item in building_layout.focus_buildings]
    )
    access_loop: LineString | None = None
    loop_junction_id: str | None = None
    if main_union is not None:
        loop_ring = focus_union.convex_hull.buffer(
            8.0, join_style="mitre"
        ).exterior
        access_loop = LineString(loop_ring.coords)
        main_point = nearest_points(
            main_union, Point(focus_group.centroid)
        )[0]
        loop_point = nearest_points(access_loop, main_point)[0]
        if main_point.distance(loop_point) >= 2.0:
            main_xy, main_junction_id = attach_to_main("BR-FOCUS", main_point)
            access_loop, loop_xy = _insert_vertex(access_loop, loop_point)
            loop_junction_id = add_junction(
                loop_xy, ("BR-FOCUS", "ACC-FOCUS-01")
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

    focus_box = box(*intent.focus_bbox)
    for group in intent.groups:
        if group.group_id == intent.focus_group_id:
            continue
        if box(*group.bbox).intersects(focus_box):
            continue
        if main_union is None:
            break
        group_box = box(*group.bbox)
        main_point = nearest_points(
            main_union, Point(group.centroid)
        )[0]
        group_point = nearest_points(group_box.boundary, main_point)[0]
        if main_point.distance(group_point) < 2.0:
            continue
        edge_id = f"BR-{group.group_id}"
        main_xy, main_junction_id = attach_to_main(edge_id, main_point)
        connector_specs.append(
            (
                edge_id,
                "branch",
                LineString([main_xy, group_point]),
                main_junction_id,
                None,
            )
        )

    sidewalks_width = basis.sidewalk_width_m
    roads: list[RoadDesign] = []
    for index, line in enumerate(main_geoms, start=1):
        roads.append(
            _road(
                f"MAIN-{index:02d}",
                "main",
                basis.road_widths["main_road"],
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
        roads.append(
            _road(
                edge_id,
                class_name,
                basis.road_widths["branch_road"],
                centerline,
                is_new=True,
                reason=(
                    "design branch from the main road to the focus-group "
                    "access loop"
                    if edge_id == "BR-FOCUS"
                    else (
                        "design branch connecting the group to the main road; "
                        "the source blue-edge mesh is not used as the design "
                        "road network"
                    )
                ),
                round_caps=True,
                start_junction_id=start_j,
                end_junction_id=end_j,
            )
        )
    if access_loop is not None:
        roads.append(
            _road(
                "ACC-FOCUS-01",
                "access",
                basis.road_widths["access_road"],
                access_loop,
                is_new=True,
                reason=(
                    "design access loop around the focus-group rows; it uses "
                    "the side and north-south gaps"
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
        "design_access_count": sum(
            1 for road in roads if road.class_name == "access"
        ),
        "source_blue_edges_replaced_by_design": True,
        "note": (
            "the 333-edge skeleton mesh is source evidence, not the design "
            "road network; the design uses merged main roads, one branch per "
            "group and one access loop for the focus group"
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
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import LineString, MultiPolygon, Point, Polygon, box
from shapely.ops import linemerge, nearest_points, unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .input import DesignInput, RoadInput
from .intent import DesignIntent


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "edge_id": self.edge_id,
            "class_name": self.class_name,
            "width_m": self.width_m,
            "is_new_connector": self.is_new_connector,
            "reason": self.reason,
            "source_edge_ids": list(self.source_edge_ids),
            "source_trace_ref": self.source_trace_ref,
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
    component_count: int
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
            "component_count": self.component_count,
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


def _main_connectors(
    lines: list[LineString],
) -> list[LineString]:
    if len(lines) <= 1:
        return []
    connectors: list[LineString] = []
    remaining = list(lines)
    connected = [remaining.pop(0)]
    while remaining:
        best = None
        for index, line in enumerate(remaining):
            for existing in connected:
                a, b = nearest_points(existing, line)
                distance = a.distance(b)
                if best is None or distance < best[0]:
                    best = (distance, index, a, b)
        if best is None:
            break
        _, index, a, b = best
        if a.distance(b) >= 0.5:
            connectors.append(LineString([a, b]))
        connected.append(remaining.pop(index))
    return connectors


def build_road_layout(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
) -> RoadLayout:
    main_lines, source_main_ids = _main_lines(design_input)
    main_union = unary_union(main_lines) if main_lines else None
    roads: list[RoadDesign] = []
    for index, line in enumerate(main_lines, start=1):
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
    for index, connector in enumerate(
        _main_connectors(main_lines), start=1
    ):
        roads.append(
            _road(
                f"MAIN-CONNECTOR-{index:02d}",
                "main",
                basis.road_widths["main_road"],
                connector,
                is_new=True,
                reason="design connector between main-road components",
            )
        )

    focus_group = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    focus_union = unary_union(
        [item.footprint for item in building_layout.focus_buildings]
    )
    access_loop = None
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
            roads.append(
                _road(
                    "BR-FOCUS",
                    "branch",
                    basis.road_widths["branch_road"],
                    LineString([main_point, loop_point]),
                    is_new=True,
                    reason=(
                        "design branch from the main road to the focus-group "
                        "access loop"
                    ),
                    round_caps=True,
                )
            )
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
        roads.append(
            _road(
                f"BR-{group.group_id}",
                "branch",
                basis.road_widths["branch_road"],
                LineString([main_point, group_point]),
                is_new=True,
                reason=(
                    "design branch connecting the group to the main road; "
                    "the source blue-edge mesh is not used as the design "
                    "road network"
                ),
                round_caps=True,
            )
        )

    corridor_union = unary_union([road.corridor for road in roads])
    sidewalk_parts = [
        road.centerline.buffer(
            road.width_m / 2 + basis.sidewalk_width_m,
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
        components = 1
    elif corridor_union.geom_type == "MultiPolygon":
        components = len(corridor_union.geoms)
    else:
        components = 0

    endpoints: dict[tuple[float, float], int] = {}
    for road in roads:
        if road.class_name == "access" and road.centerline.is_ring:
            continue
        coords = list(road.centerline.coords)
        for point in (coords[0], coords[-1]):
            key = (round(point[0], 3), round(point[1], 3))
            endpoints[key] = endpoints.get(key, 0) + 1
    dead_ends = tuple(
        f"DE-{index:02d}"
        for index, count in enumerate(endpoints.values(), start=1)
        if count == 1
    )
    junction_nodes = tuple(
        f"J-{index:02d}"
        for index in range(
            1,
            sum(
                1
                for road in roads
                if road.is_new_connector
            )
            + 1,
        )
    )
    simplification = {
        "source_edge_count": len(design_input.roads),
        "source_main_edge_count": len(source_main_ids),
        "source_blue_edge_count": (
            len(design_input.roads) - len(source_main_ids)
        ),
        "design_main_line_count": len(main_lines),
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
        dead_end_nodes=dead_ends,
        corridor_generator="round_buffer_hierarchy_v0.1",
        not_professional_alignment=True,
        component_count=components,
        simplification=simplification,
    )

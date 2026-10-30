from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import LineString, Point, box
from shapely.ops import unary_union

from .input import DesignInput


@dataclass(frozen=True)
class BuildingGroup:
    group_id: str
    building_ids: tuple[str, ...]
    unit_count: int
    households: int
    centroid: tuple[float, float]
    bbox: tuple[float, float, float, float]
    green_ids: tuple[str, ...]
    main_road_distance_m: float | None

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "building_ids": list(self.building_ids),
            "unit_count": self.unit_count,
            "households": self.households,
            "centroid": list(self.centroid),
            "bbox": list(self.bbox),
            "green_ids": list(self.green_ids),
            "main_road_distance_m": self.main_road_distance_m,
        }


@dataclass(frozen=True)
class DesignIntent:
    groups: tuple[BuildingGroup, ...]
    road_hierarchy: dict[str, Any]
    principles: tuple[str, ...]
    focus_group_id: str
    focus_bbox: tuple[float, float, float, float]
    focus_building_ids: tuple[str, ...]
    focus_green_ids: tuple[str, ...]
    focus_road_ids: tuple[str, ...]
    focus_subgroups: dict[str, tuple[str, ...]]
    #: The 17 groups are *inferred* by the Agent from proximity and the main
    #: road buffer; they are not designer-confirmed groups.  The provenance
    #: records the assumptions so consumers cannot silently upgrade them.
    grouping_provenance: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": "dgcad.design-intent.v0.1",
            "groups": [group.to_dict() for group in self.groups],
            "road_hierarchy": self.road_hierarchy,
            "principles": list(self.principles),
            "focus_group_id": self.focus_group_id,
            "focus_bbox": list(self.focus_bbox),
            "focus_building_ids": list(self.focus_building_ids),
            "focus_green_ids": list(self.focus_green_ids),
            "focus_road_ids": list(self.focus_road_ids),
            "focus_subgroups": {
                key: list(value)
                for key, value in self.focus_subgroups.items()
            },
            "grouping_provenance": dict(self.grouping_provenance),
        }


class _UnionFind:
    def __init__(self) -> None:
        self.parent: dict[str, str] = {}

    def find(self, item: str) -> str:
        self.parent.setdefault(item, item)
        while self.parent[item] != item:
            self.parent[item] = self.parent[self.parent[item]]
            item = self.parent[item]
        return item

    def union(self, first: str, second: str) -> None:
        root_a = self.find(first)
        root_b = self.find(second)
        if root_a != root_b:
            self.parent[root_b] = root_a


def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def build_design_intent(
    design_input: DesignInput, basis
) -> DesignIntent:
    buildings = {item.trace_id: item for item in design_input.buildings}
    union_find = _UnionFind()
    for trace_id in buildings:
        union_find.find(trace_id)
    main_lines = [
        road.centerline
        for road in design_input.roads
        if road.class_candidate == "main_road"
    ]
    main_network = unary_union(main_lines) if main_lines else None
    main_barrier = (
        main_network.buffer(8.0) if main_network is not None else None
    )
    ids = sorted(buildings)
    for index, first in enumerate(ids):
        for second in ids[index + 1 :]:
            if (
                _distance(
                    buildings[first].centroid,
                    buildings[second].centroid,
                )
                > basis.group_distance_m
            ):
                continue
            if main_barrier is not None and LineString(
                [
                    buildings[first].centroid,
                    buildings[second].centroid,
                ]
            ).intersects(main_barrier):
                continue
            union_find.union(first, second)

    clusters: dict[str, list[str]] = {}
    for trace_id in ids:
        clusters.setdefault(union_find.find(trace_id), []).append(trace_id)

    greens = {item.trace_id: item for item in design_input.greens}

    groups: list[BuildingGroup] = []
    for index, (root, building_ids) in enumerate(
        sorted(clusters.items(), key=lambda item: -len(item[1])),
        start=1,
    ):
        group_buildings = [buildings[trace_id] for trace_id in building_ids]
        unit_count = sum(
            item.unit_count or 0
            for item in group_buildings
            if not item.is_facility
        )
        households = basis.households(unit_count)
        minx = min(item.geometry.bounds[0] for item in group_buildings)
        miny = min(item.geometry.bounds[1] for item in group_buildings)
        maxx = max(item.geometry.bounds[2] for item in group_buildings)
        maxy = max(item.geometry.bounds[3] for item in group_buildings)
        centroid = (
            sum(item.centroid[0] for item in group_buildings)
            / len(group_buildings),
            sum(item.centroid[1] for item in group_buildings)
            / len(group_buildings),
        )
        group_box = box(minx, miny, maxx, maxy)
        group_greens = tuple(
            sorted(
                green.trace_id
                for green in greens.values()
                if green.geometry.intersects(group_box)
            )
        )
        main_distance = (
            None
            if main_network is None
            else float(
                main_network.distance(Point(centroid))
            )
        )
        groups.append(
            BuildingGroup(
                group_id=f"G-{index:02d}",
                building_ids=tuple(sorted(building_ids)),
                unit_count=unit_count,
                households=households,
                centroid=centroid,
                bbox=(minx, miny, maxx, maxy),
                green_ids=group_greens,
                main_road_distance_m=main_distance,
            )
        )

    focus_group = max(
        groups,
        key=lambda group: (
            group.unit_count,
            -abs(group.main_road_distance_m or 0.0),
        ),
    )
    margin = 25.0
    focus_bbox = (
        focus_group.bbox[0] - margin,
        focus_group.bbox[1] - margin,
        focus_group.bbox[2] + margin,
        focus_group.bbox[3] + margin,
    )
    focus_box = box(*focus_bbox)
    focus_buildings = [
        buildings[trace_id] for trace_id in focus_group.building_ids
    ]
    ordered = sorted(focus_buildings, key=lambda item: item.centroid[1])
    chunk = max(1, math.ceil(len(ordered) / 3))
    focus_subgroups = {
        f"FOCUS-{index}": tuple(
            item.trace_id for item in ordered[start : start + chunk]
        )
        for index, start in enumerate(
            range(0, len(ordered), chunk), start=1
        )
    }
    focus_roads = tuple(
        sorted(
            road.edge_id
            for road in design_input.roads
            if road.centerline.intersects(focus_box)
        )
    )
    focus_greens = tuple(
        sorted(
            green.trace_id
            for green in greens.values()
            if green.geometry.intersects(focus_box)
        )
    )
    hierarchy = {
        "main_edges": sum(
            1
            for road in design_input.roads
            if road.class_candidate == "main_road"
        ),
        "branch_or_access_edges": sum(
            1
            for road in design_input.roads
            if road.class_candidate != "main_road"
        ),
        "node_count": len(design_input.road_graph.nodes),
        "edge_count": len(design_input.road_graph.edges),
        "main_class_state": "inferred_from_colour_majority",
        "branch_access_combined": True,
    }
    principles = (
        "the main road forms the organization spine; residential groups sit "
        "along it",
        "each building keeps its unit count and building ID; the footprint is "
        "standardized to the declared staircase module",
        "the focus group is reorganized into rows with at least 20 m "
        "north-south spacing and internal green strips",
        "branch/access roads connect the groups to the main road; the blue "
        "class still combines branch and access road",
        "garage entrances are placed on the main road; parking is "
        "underground and its layout is not designed",
    )
    return DesignIntent(
        groups=tuple(groups),
        road_hierarchy=hierarchy,
        principles=principles,
        focus_group_id=focus_group.group_id,
        focus_bbox=focus_bbox,
        focus_building_ids=focus_group.building_ids,
        focus_green_ids=focus_greens,
        focus_road_ids=focus_roads,
        focus_subgroups=focus_subgroups,
        grouping_provenance={
            "schema_id": "dgcad.inferred-groups.v0.1",
            "kind": "inferred_groups",
            "not_designer_confirmed": True,
            "method": "union_find_single_linkage",
            "group_distance_m": float(basis.group_distance_m),
            "main_road_buffer_m": 8.0,
            "main_road_filter": "class_candidate == main_road",
            "transitive_merge": True,
            "note": (
                "the 17 groups are inferred by the Agent from building "
                "centroid distance, the main-road 8 m buffer and transitive "
                "Union-Find merging; they must not be described as "
                "designer-confirmed spatial groups"
            ),
        },
    )

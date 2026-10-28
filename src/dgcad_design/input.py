from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from shapely.geometry import LineString, Point, Polygon, shape
from shapely.ops import unary_union
from shapely.validation import make_valid

from dgcad_domain import RoadEdge, RoadGraph, RoadNode

from .basis import DesignBasis


@dataclass(frozen=True)
class BuildingInput:
    trace_id: str
    geometry: Polygon
    unit_count: int | None
    unit_count_state: str
    is_facility: bool
    area_m2: float
    orientation_deg: float
    centroid: tuple[float, float]
    parent_ids: tuple[str, ...]


@dataclass(frozen=True)
class GreenInput:
    trace_id: str
    geometry: Polygon
    area_m2: float


@dataclass(frozen=True)
class EntranceInput:
    trace_id: str
    point: Point


@dataclass(frozen=True)
class RoadInput:
    edge_id: str
    class_candidate: str
    centerline: LineString
    node_a: str
    node_b: str
    length_m: float


@dataclass(frozen=True)
class DesignInput:
    case_id: str
    site_boundary: Polygon
    site_area_m2: float
    buildings: tuple[BuildingInput, ...]
    greens: tuple[GreenInput, ...]
    entrances: tuple[EntranceInput, ...]
    roads: tuple[RoadInput, ...]
    road_graph: RoadGraph
    source_manifest: dict[str, Any]
    coordinate_handoff: dict[str, Any]

    @property
    def staircase_count(self) -> int:
        return sum(
            building.unit_count or 0
            for building in self.buildings
            if not building.is_facility
        )

    @property
    def facility_count(self) -> int:
        return sum(1 for building in self.buildings if building.is_facility)

    @property
    def unit_count_total(self) -> int:
        return sum(
            building.unit_count or 0
            for building in self.buildings
            if not building.is_facility
        )


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _key(x: float, y: float) -> tuple[float, float]:
    return (round(float(x), 3), round(float(y), 3))


def _orientation(geometry: Polygon) -> float:
    rectangle = geometry.minimum_rotated_rectangle
    if rectangle.geom_type != "Polygon":
        return 0.0
    coords = list(rectangle.exterior.coords)
    edges = []
    for start, end in zip(coords, coords[1:]):
        dx = end[0] - start[0]
        dy = end[1] - start[1]
        edges.append((math.hypot(dx, dy), math.degrees(math.atan2(dy, dx))))
    _, angle = max(edges, key=lambda item: item[0])
    while angle > 90:
        angle -= 180
    while angle <= -90:
        angle += 180
    return angle


def _valid_polygon(geometry):
    if geometry.is_valid and geometry.geom_type in {
        "Polygon",
        "MultiPolygon",
    }:
        return geometry
    fixed = make_valid(geometry)
    if fixed.geom_type in {"Polygon", "MultiPolygon"}:
        return fixed
    polygons = [
        item
        for item in getattr(fixed, "geoms", [])
        if item.geom_type == "Polygon"
    ]
    if not polygons:
        raise ValueError("geometry has no valid polygonal part")
    merged = unary_union(polygons)
    if merged.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(
            f"geometry has no valid polygonal part: {merged.geom_type}"
        )
    return merged


def load_design_input(
    case_dir: str | Path, basis: DesignBasis
) -> DesignInput:
    case_dir = Path(case_dir)
    trace_path = case_dir / "trace-raw.geojson"
    network_path = case_dir / "road-network-proposed.geojson"
    nodes_path = case_dir / "road-nodes-proposed.geojson"
    summary_path = case_dir / "case-summary.json"
    sketch_path = case_dir / "source" / "sketch.png"

    summary = json.loads(summary_path.read_text(encoding="utf-8"))
    trace = json.loads(trace_path.read_text(encoding="utf-8"))
    network = json.loads(network_path.read_text(encoding="utf-8"))
    nodes = json.loads(nodes_path.read_text(encoding="utf-8"))

    scale = basis.scale_px_per_m
    origin_x, origin_y = basis.origin_px

    def transform_coords(coords):
        return [
            (
                round((float(x) - origin_x) / scale, 6),
                round((origin_y - float(y)) / scale, 6),
            )
            for x, y in coords
        ]

    def transform(geometry: dict[str, Any]):
        kind = geometry["type"]
        if kind == "Polygon":
            polygon = Polygon(
                transform_coords(geometry["coordinates"][0]),
                [
                    transform_coords(ring)
                    for ring in geometry["coordinates"][1:]
                ],
            )
            return _valid_polygon(polygon)
        if kind == "MultiPolygon":
            polygons = [
                Polygon(
                    transform_coords(polygon[0]),
                    [
                        transform_coords(ring)
                        for ring in polygon[1:]
                    ],
                )
                for polygon in geometry["coordinates"]
            ]
            merged = unary_union(
                [_valid_polygon(item) for item in polygons]
            )
            return _valid_polygon(merged)
        if kind == "LineString":
            return LineString(transform_coords(geometry["coordinates"]))
        if kind == "Point":
            x, y = geometry["coordinates"]
            return Point(
                (float(x) - origin_x) / scale,
                (origin_y - float(y)) / scale,
            )
        raise ValueError(f"unsupported geometry: {kind}")

    site_boundary = None
    buildings: list[BuildingInput] = []
    greens: list[GreenInput] = []
    entrances: list[EntranceInput] = []
    for feature in trace["features"]:
        properties = feature["properties"]
        role = properties["semantic_role"]
        geometry = transform(feature["geometry"])
        if role == "site_boundary_candidate":
            site_boundary = geometry
        elif role == "building_candidate":
            unit_count = properties.get("unit_count")
            unit_count = None if unit_count is None else int(unit_count)
            centroid = geometry.centroid
            buildings.append(
                BuildingInput(
                    trace_id=str(properties["trace_id"]),
                    geometry=geometry,
                    unit_count=unit_count,
                    unit_count_state=str(
                        properties.get("unit_count_state", "unknown")
                    ),
                    is_facility=unit_count is None,
                    area_m2=float(geometry.area),
                    orientation_deg=_orientation(geometry),
                    centroid=(float(centroid.x), float(centroid.y)),
                    parent_ids=tuple(
                        str(item)
                        for item in properties.get("provenance", {}).get(
                            "parent_ids", []
                        )
                    ),
                )
            )
        elif role == "cluster_green_space_candidate":
            greens.append(
                GreenInput(
                    trace_id=str(properties["trace_id"]),
                    geometry=geometry,
                    area_m2=float(geometry.area),
                )
            )
        elif role == "garage_entrance_candidate":
            entrances.append(
                EntranceInput(
                    trace_id=str(properties["trace_id"]),
                    point=geometry,
                )
            )

    if site_boundary is None:
        raise ValueError("site_boundary_candidate is missing")
    if site_boundary.geom_type != "Polygon":
        raise ValueError(
            f"site boundary must be a Polygon, got {site_boundary.geom_type}"
        )

    node_by_xy = {}
    node_junction = {}
    node_local_by_id: dict[str, tuple[float, float]] = {}
    for feature in nodes["features"]:
        properties = feature["properties"]
        point = feature["geometry"]["coordinates"]
        node_id = str(properties["node_id"])
        node_by_xy[_key(*point)] = node_id
        node_junction[node_id] = bool(
            properties.get("junction", False)
        )
        node_local_by_id[node_id] = (
            (float(point[0]) - origin_x) / scale,
            (origin_y - float(point[1])) / scale,
        )

    roads: list[RoadInput] = []
    graph_nodes: dict[str, RoadNode] = {}
    graph_edges: dict[str, RoadEdge] = {}
    for feature in network["features"]:
        properties = feature["properties"]
        centerline = transform(feature["geometry"])
        a = _key(*properties["from_node"])
        b = _key(*properties["to_node"])
        if a not in node_by_xy or b not in node_by_xy:
            raise ValueError(
                f"road edge {properties['trace_id']} references an unknown node"
            )
        node_a = node_by_xy[a]
        node_b = node_by_xy[b]
        for node_id in (node_a, node_b):
            x_local, y_local = node_local_by_id[node_id]
            graph_nodes[node_id] = RoadNode(
                node_id=node_id,
                x=x_local,
                y=y_local,
                junction=node_junction.get(node_id, False),
            )
        coords = list(centerline.coords)
        coords[0] = node_local_by_id[node_a]
        coords[-1] = node_local_by_id[node_b]
        centerline = LineString(coords)
        edge_id = str(properties["trace_id"])
        graph_edges[edge_id] = RoadEdge(
            edge_id=edge_id,
            corridor_id=edge_id,
            node_a=node_a,
            node_b=node_b,
            centerline=centerline,
        )
        roads.append(
            RoadInput(
                edge_id=edge_id,
                class_candidate=str(
                    properties["road_class_candidate"]
                ),
                centerline=centerline,
                node_a=node_a,
                node_b=node_b,
                length_m=float(centerline.length),
            )
        )

    road_graph = RoadGraph(nodes=graph_nodes, edges=graph_edges)
    source_manifest = {
        "case_id": str(summary["case_id"]),
        "source_sketch_sha256": _sha256(sketch_path),
        "files": [
            {
                "path": str(trace_path.relative_to(case_dir.parent.parent.parent)),
                "sha256": _sha256(trace_path),
                "role": "trace_geojson",
            },
            {
                "path": str(network_path.relative_to(case_dir.parent.parent.parent)),
                "sha256": _sha256(network_path),
                "role": "road_network_geojson",
            },
            {
                "path": str(nodes_path.relative_to(case_dir.parent.parent.parent)),
                "sha256": _sha256(nodes_path),
                "role": "road_nodes_geojson",
            },
            {
                "path": str(sketch_path.relative_to(case_dir.parent.parent.parent)),
                "sha256": _sha256(sketch_path),
                "role": "sketch_raster",
            },
        ],
    }
    return DesignInput(
        case_id=str(summary["case_id"]),
        site_boundary=site_boundary,
        site_area_m2=float(site_boundary.area),
        buildings=tuple(buildings),
        greens=tuple(greens),
        entrances=tuple(entrances),
        roads=tuple(roads),
        road_graph=road_graph,
        source_manifest=source_manifest,
        coordinate_handoff={
            "source_frame": "image_space_unscaled",
            "target_frame": basis.target_frame,
            "coordinate_state": "local_metric_scaled",
            "scale_px_per_m": scale,
            "origin_px": [origin_x, origin_y],
            "y_axis": "flipped",
            "project_coordinates": False,
            "accuracy": "approximate",
            "not_survey_grade": True,
        },
    )

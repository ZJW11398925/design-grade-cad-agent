"""Noded design-road topology: exact-coordinate MultiGraph check.

This module is the dependency-free topology truth for the design road network
(M4c-1a).  It deliberately contains **no rounding, no buffering, no tolerance
and no snapping**: nodes are the exact endpoint coordinate tuples produced by
``shapely.ops.unary_union`` (GEOS exact noding), parallel edges are preserved in
a multigraph, and connectivity is what the exact coordinate identity gives.

Two predicates matter and are intentionally different:

* ``component_count`` / connectivity is exact-coordinate noding;
* ``max_endpoint_gap_m`` uses the *endpoint-on-line* exact predicate for the
  junctions a connector declares (a point that is 1e-15 m off the target line is
  not on it, even though a float distance reports a tiny number);
* ``crossing_only`` flags a connector that is connected to another road only by
  a line crossing at a point that is not a vertex of both roads.  Such a node
  exists topologically but not by construction ("float luck"), which is a defect
  for a design network that must have explicit junctions.

``topology_violations`` turns the measurements into fail-closed codes.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Protocol, Sequence

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

SCHEMA_ID = "dgcad.design-road-topology.v0.1"

REQUIRED_FIELDS = (
    "road_count",
    "noded_segment_count",
    "node_count",
    "edge_count",
    "component_count",
    "cyclomatic",
    "degree_histogram",
    "dead_end_count",
    "junction_count",
    "explicit_junction_count",
    "max_endpoint_gap_m",
    "closed_ring_count",
    "components",
    "connector_states",
)

CONNECTOR_STATES = (
    "shared_vertex",
    "crossing_only",
    "detached",
    "dead_end",
    "isolated_ring",
)

#: maximum tolerated endpoint-on-line residual for a declared junction
ENDPOINT_GAP_TOLERANCE_M = 1e-9

#: violation codes emitted by :func:`topology_violations`
VIOLATION_COMPONENT_COUNT = "TOPOLOGY_COMPONENT_COUNT"
VIOLATION_ENDPOINT_GAP = "TOPOLOGY_ENDPOINT_GAP"
VIOLATION_CROSSING_ONLY = "TOPOLOGY_CROSSING_ONLY"
VIOLATION_UNDECLARED_RING = "TOPOLOGY_UNDECLARED_CLOSED_RING"


class RoadLike(Protocol):
    """Duck-typed design road: topology must not import ``roads.py``."""

    edge_id: str
    class_name: str
    centerline: LineString
    start_junction_id: str | None
    end_junction_id: str | None


@dataclass(frozen=True)
class NodedRoadTopology:
    road_count: int
    noded_segment_count: int
    node_count: int
    edge_count: int
    component_count: int
    cyclomatic: int
    degree_histogram: dict[int, int]
    dead_end_count: int
    junction_count: int
    explicit_junction_count: int
    max_endpoint_gap_m: float
    closed_ring_count: int
    components: tuple[dict[str, Any], ...]
    connector_states: tuple[dict[str, Any], ...]

    def to_dict(self) -> dict[str, Any]:
        payload: dict[str, Any] = {"schema_id": SCHEMA_ID}
        for field_name in REQUIRED_FIELDS:
            value = getattr(self, field_name)
            if field_name in {"components", "connector_states"}:
                value = [dict(item) for item in value]
            elif field_name == "degree_histogram":
                value = {
                    int(degree): count for degree, count in value.items()
                }
            payload[field_name] = value
        return payload


# --------------------------------------------------------------------- helpers
class _DSU:
    def __init__(self) -> None:
        self._parent: dict[int, int] = {}

    def find(self, item: int) -> int:
        self._parent.setdefault(item, item)
        root = item
        while self._parent[root] != root:
            root = self._parent[root]
        while self._parent[item] != root:
            self._parent[item], item = root, self._parent[item]
        return root

    def union(self, first: int, second: int) -> None:
        root_a = self.find(first)
        root_b = self.find(second)
        if root_a != root_b:
            self._parent[root_b] = root_a


def _lines_of(geometry: Any) -> list[LineString]:
    """Flatten a shapely geometry into noded LineStrings (rings kept closed)."""
    lines: list[LineString] = []

    def collect(item: Any) -> None:
        if item.is_empty:
            return
        if item.geom_type in {"LineString", "LinearRing"}:
            lines.append(LineString(item.coords))
        elif item.geom_type in {"MultiLineString", "GeometryCollection"}:
            for part in item.geoms:
                collect(part)

    collect(geometry)
    return lines


def _points_of(geometry: Any) -> list[Point]:
    points: list[Point] = []
    if geometry.is_empty:
        return points
    if geometry.geom_type == "Point":
        points.append(geometry)
    elif geometry.geom_type in {"MultiPoint", "GeometryCollection"}:
        for part in geometry.geoms:
            points.extend(_points_of(part))
    return points


def _vertices(line: LineString) -> set[tuple[float, float]]:
    return {(float(x), float(y)) for x, y in line.coords}


def _line_vertices(line: LineString) -> set[tuple[float, float]]:
    return _vertices(line)


def _road_attr(road: Any, name: str, default: Any = None) -> Any:
    return getattr(road, name, default)


def _nearest_finite(values: Iterable[float]) -> float:
    return min(values) if values else 0.0


# ---------------------------------------------------------------- public API
def noded_road_topology(
    roads: Sequence[Any],
    junctions: Sequence[dict[str, Any]] = (),
) -> NodedRoadTopology:
    """Build the exact-coordinate noded topology of a design road network.

    ``roads`` is any sequence of objects with ``edge_id``, ``class_name`` and
    ``centerline`` attributes (``RoadDesign`` or a test double).  ``junctions``
    are explicit junction records ``{"id", "x", "y", "road_ids"}`` produced by
    the road builder; each declared junction endpoint must be exactly on the
    other member road's centreline.
    """
    road_list = list(roads)
    junction_list = list(junctions or ())
    merged = unary_union([road.centerline for road in road_list])

    segments = _lines_of(merged)

    # ---- exact-coordinate multigraph: node = endpoint tuple ---------------
    node_index: dict[tuple[float, float], int] = {}
    segment_edges: list[tuple[int, int]] = []
    for segment in segments:
        coords = list(segment.coords)
        start = (float(coords[0][0]), float(coords[0][1]))
        end = (float(coords[-1][0]), float(coords[-1][1]))
        start_index = node_index.setdefault(start, len(node_index))
        end_index = node_index.setdefault(end, len(node_index))
        segment_edges.append((start_index, end_index))

    dsu = _DSU()
    for index in node_index.values():
        dsu.find(index)
    for start_index, end_index in segment_edges:
        dsu.union(start_index, end_index)

    # ---- component bookkeeping -------------------------------------------
    component_nodes: dict[int, set[int]] = {}
    for index in node_index.values():
        component_nodes.setdefault(dsu.find(index), set()).add(index)
    component_edges: dict[int, int] = {}
    segment_component: list[int] = []
    for start_index, end_index in segment_edges:
        root = dsu.find(start_index)
        component_edges[root] = component_edges.get(root, 0) + 1
        segment_component.append(root)

    # ---- road -> component (by covered noded length) ----------------------
    road_component: dict[str, int] = {}
    component_road_ids: dict[int, set[str]] = {}
    for road in road_list:
        best_root = None
        best_covered = -1.0
        for segment, root in zip(segments, segment_component):
            covered = road.centerline.intersection(segment).length
            if covered > best_covered:
                best_covered = covered
                best_root = root
        if best_root is None:  # degenerate road, fall back to nearest node
            nearest = min(
                node_index.values(),
                key=lambda idx: Point(
                    list(node_index.keys())[idx]
                ).distance(road.centerline),
            )
            best_root = dsu.find(nearest)
        road_component[road.edge_id] = best_root
        component_road_ids.setdefault(best_root, set()).add(road.edge_id)

    # ---- degree histogram on the multigraph (self-loop counts 2) ----------
    degree: dict[int, int] = {}
    for start_index, end_index in segment_edges:
        if start_index == end_index:
            degree[start_index] = degree.get(start_index, 0) + 2
        else:
            degree[start_index] = degree.get(start_index, 0) + 1
            degree[end_index] = degree.get(end_index, 0) + 1
    degree_histogram: dict[int, int] = {}
    for value in degree.values():
        degree_histogram[value] = degree_histogram.get(value, 0) + 1
    dead_end_count = sum(1 for value in degree.values() if value == 1)
    junction_count = sum(1 for value in degree.values() if value >= 3)

    component_count = len(component_nodes)
    node_count = len(node_index)
    edge_count = len(segments)
    cyclomatic = edge_count - node_count + component_count

    # ---- crossing-only detection -----------------------------------------
    crossing_road_ids: set[str] = set()
    for first_index, first in enumerate(road_list):
        first_vertices = _line_vertices(first.centerline)
        for second in road_list[first_index + 1:]:
            second_vertices = _line_vertices(second.centerline)
            intersection = first.centerline.intersection(second.centerline)
            for point in _points_of(intersection):
                key = (float(point.x), float(point.y))
                shared = key in first_vertices and key in second_vertices
                if shared:
                    continue
                crossing_road_ids.add(first.edge_id)
                crossing_road_ids.add(second.edge_id)

    # ---- endpoint gaps (exact endpoint-on-line predicate) -----------------
    junction_by_id = {
        str(item["id"]): item for item in junction_list if "id" in item
    }
    road_by_id = {road.edge_id: road for road in road_list}
    gaps: list[float] = []
    for road in road_list:
        for attribute, end_index in (
            ("start_junction_id", 0),
            ("end_junction_id", -1),
        ):
            junction_id = _road_attr(road, attribute)
            coords = list(road.centerline.coords)
            endpoint = Point(float(coords[end_index][0]), float(coords[end_index][1]))
            if junction_id is not None and str(junction_id) in junction_by_id:
                members = [
                    road_by_id[member_id]
                    for member_id in junction_by_id[str(junction_id)].get(
                        "road_ids", ()
                    )
                    if member_id in road_by_id and member_id != road.edge_id
                ]
            else:
                # no declared junction: the endpoint claims no attachment, so
                # there is no endpoint-on-line claim to test.  A network that
                # forgets its junctions still fails the component-count check.
                members = []
            if not members:
                continue
            exact = any(member.centerline.intersects(endpoint) for member in members)
            if exact:
                gaps.append(0.0)
            else:
                gaps.append(
                    min(endpoint.distance(member.centerline) for member in members)
                )
    max_endpoint_gap_m = max(gaps) if gaps else 0.0

    # ---- closed rings -----------------------------------------------------
    closed_ring_road_ids = [
        road.edge_id
        for road in road_list
        if list(road.centerline.coords)[0] == list(road.centerline.coords)[-1]
        and len(list(road.centerline.coords)) >= 4
    ]

    # ---- main component (for detached classification) ---------------------
    main_component_ids = {
        road_component[road.edge_id]
        for road in road_list
        if road.class_name == "main"
    }
    if not main_component_ids:
        main_component_ids = set(component_nodes)

    # ---- connector states -------------------------------------------------
    connector_states: list[dict[str, Any]] = []
    for road in road_list:
        if road.class_name == "main":
            continue
        root = road_component[road.edge_id]
        coords = list(road.centerline.coords)
        endpoints = (
            Point(float(coords[0][0]), float(coords[0][1])),
            Point(float(coords[-1][0]), float(coords[-1][1])),
        )
        node_degrees = [
            degree.get(node_index.get((float(point.x), float(point.y))), 0)
            for point in endpoints
        ]
        is_closed = coords[0] == coords[-1] and len(coords) >= 4
        if is_closed and len(component_road_ids.get(root, ())) == 1:
            state = "isolated_ring"
        elif road.edge_id in crossing_road_ids:
            state = "crossing_only"
        elif root not in main_component_ids:
            state = "detached"
        elif any(value == 1 for value in node_degrees):
            state = "dead_end"
        else:
            state = "shared_vertex"
        connector_states.append(
            {
                "road_id": road.edge_id,
                "class_name": road.class_name,
                "state": state,
            }
        )

    # ---- components detail -------------------------------------------------
    components: list[dict[str, Any]] = []
    for root, node_ids in component_nodes.items():
        components.append(
            {
                "node_count": len(node_ids),
                "edge_count": component_edges.get(root, 0),
                "road_ids": sorted(component_road_ids.get(root, set())),
            }
        )
    components.sort(
        key=lambda item: (-int(item["node_count"]), item["road_ids"])
    )

    return NodedRoadTopology(
        road_count=len(road_list),
        noded_segment_count=len(segments),
        node_count=node_count,
        edge_count=edge_count,
        component_count=component_count,
        cyclomatic=cyclomatic,
        degree_histogram=dict(sorted(degree_histogram.items())),
        dead_end_count=dead_end_count,
        junction_count=junction_count,
        explicit_junction_count=len(junction_list),
        max_endpoint_gap_m=float(max_endpoint_gap_m),
        closed_ring_count=len(closed_ring_road_ids),
        components=tuple(components),
        connector_states=tuple(connector_states),
    )


def topology_violations(
    topology: NodedRoadTopology,
) -> tuple[dict[str, Any], ...]:
    """Fail-closed violation records for a noded design-road topology."""
    violations: list[dict[str, Any]] = []

    if topology.component_count != 1:
        violations.append(
            {
                "code": VIOLATION_COMPONENT_COUNT,
                "severity": "error",
                "message": (
                    "the noded design-road graph must be one connected "
                    f"component, got {topology.component_count}"
                ),
                "detail": {
                    "component_count": topology.component_count,
                    "components": [
                        list(item["road_ids"])
                        for item in topology.components
                    ],
                },
            }
        )

    if topology.max_endpoint_gap_m > ENDPOINT_GAP_TOLERANCE_M:
        violations.append(
            {
                "code": VIOLATION_ENDPOINT_GAP,
                "severity": "error",
                "message": (
                    "a connector endpoint is not exactly on the centreline it "
                    f"claims to join (gap {topology.max_endpoint_gap_m} m)"
                ),
                "detail": {
                    "max_endpoint_gap_m": topology.max_endpoint_gap_m,
                    "tolerance_m": ENDPOINT_GAP_TOLERANCE_M,
                },
            }
        )

    crossing_only = [
        item for item in topology.connector_states
        if item.get("state") == "crossing_only"
    ]
    if crossing_only:
        violations.append(
            {
                "code": VIOLATION_CROSSING_ONLY,
                "severity": "error",
                "message": (
                    "connector(s) are connected only by a centreline crossing "
                    "at a point that is not a shared vertex"
                ),
                "detail": {
                    "road_ids": [item["road_id"] for item in crossing_only]
                },
            }
        )

    isolated_rings = [
        item for item in topology.connector_states
        if item.get("state") == "isolated_ring"
    ]
    if isolated_rings:
        violations.append(
            {
                "code": VIOLATION_UNDECLARED_RING,
                "severity": "error",
                "message": (
                    "closed ring(s) are not declared or not joined to the "
                    "design network at an explicit junction"
                ),
                "detail": {
                    "road_ids": [item["road_id"] for item in isolated_rings]
                },
            }
        )

    return tuple(violations)


__all__ = [
    "SCHEMA_ID",
    "REQUIRED_FIELDS",
    "CONNECTOR_STATES",
    "ENDPOINT_GAP_TOLERANCE_M",
    "VIOLATION_COMPONENT_COUNT",
    "VIOLATION_ENDPOINT_GAP",
    "VIOLATION_CROSSING_ONLY",
    "VIOLATION_UNDECLARED_RING",
    "NodedRoadTopology",
    "noded_road_topology",
    "topology_violations",
]

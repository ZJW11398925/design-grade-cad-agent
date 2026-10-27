from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from .building import BuildingIntent
from .common import parse_geometry
from .road import RoadCorridorIntent, RoadGraph


TRACE_SCHEMA_ID = "dgcad.domain.fixture.confirmed-trace.v0.1"
SEMANTIC_ROLES = frozenset(
    {"site_boundary", "building", "road", "green", "unknown"}
)


class TraceNotConfirmed(RuntimeError):
    pass


@dataclass(frozen=True)
class TraceObject:
    trace_id: str
    semantic_role: str
    geometry: Any
    review_state: str
    locked: bool
    source_refs: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.semantic_role not in SEMANTIC_ROLES:
            raise ValueError(f"unknown semantic role: {self.semantic_role}")
        if self.review_state != "confirmed":
            raise ValueError(
                f"trace {self.trace_id} is not confirmed: {self.review_state}"
            )
        if not self.locked:
            raise ValueError(f"trace {self.trace_id} must be locked")


@dataclass(frozen=True)
class ConfirmedTraceScene:
    fixture_id: str
    scene_id: str
    synthetic_only: bool
    human_confirmed_trace: bool
    coordinate_frame: str
    units: str
    site_boundary_ref: str
    trace_objects: dict[str, TraceObject]
    buildings: dict[str, BuildingIntent]
    roads: dict[str, RoadCorridorIntent]
    road_graph: RoadGraph

    def trace(self, trace_id: str) -> TraceObject:
        try:
            return self.trace_objects[trace_id]
        except KeyError as exc:
            raise ValueError(f"unknown trace object: {trace_id}") from exc

    def building(self, object_id: str) -> BuildingIntent:
        try:
            return self.buildings[object_id]
        except KeyError as exc:
            raise ValueError(f"unknown building intent: {object_id}") from exc

    def road(self, corridor_id: str) -> RoadCorridorIntent:
        try:
            return self.roads[corridor_id]
        except KeyError as exc:
            raise ValueError(f"unknown road intent: {corridor_id}") from exc

    @property
    def site_boundary(self) -> TraceObject:
        return self.trace(self.site_boundary_ref)


def _require_mapping(data: Any, name: str) -> dict[str, Any]:
    if not isinstance(data, dict):
        raise ValueError(f"{name} must be a mapping")
    return data


def load_confirmed_trace_fixture(path: str | Path) -> ConfirmedTraceScene:
    payload = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    data = _require_mapping(payload, "fixture")
    if data.get("schema_id") != TRACE_SCHEMA_ID:
        raise ValueError(f"unexpected fixture schema: {data.get('schema_id')}")
    if data.get("human_confirmed_trace") is not True:
        raise TraceNotConfirmed(
            "domain slice requires human_confirmed_trace: true"
        )
    synthetic_only = data.get("synthetic_only")
    if not isinstance(synthetic_only, bool):
        raise ValueError("synthetic_only must be an explicit boolean")

    trace_objects: dict[str, TraceObject] = {}
    for item in data.get("trace_objects", []):
        record = _require_mapping(item, "trace object")
        trace_id = str(record["trace_id"])
        if trace_id in trace_objects:
            raise ValueError(f"duplicate trace id: {trace_id}")
        trace_objects[trace_id] = TraceObject(
            trace_id=trace_id,
            semantic_role=str(record["semantic_role"]),
            geometry=parse_geometry(record["geometry"]),
            review_state=str(record.get("review_state", "confirmed")),
            locked=bool(record.get("locked", True)),
            source_refs=tuple(str(ref) for ref in record.get("source_refs", [])),
        )

    site_boundary_ref = str(data["site_boundary_ref"])
    if site_boundary_ref not in trace_objects:
        raise ValueError("site_boundary_ref does not resolve")
    if trace_objects[site_boundary_ref].semantic_role != "site_boundary":
        raise ValueError("site_boundary_ref must reference a site_boundary trace")

    buildings = {
        str(item["object_id"]): BuildingIntent.from_dict(item)
        for item in data.get("buildings", [])
    }
    for intent in buildings.values():
        trace = trace_objects.get(intent.trace_ref)
        if trace is None:
            raise ValueError(
                f"building {intent.object_id} references unknown trace"
            )
        if trace.semantic_role != "building":
            raise ValueError(
                f"building {intent.object_id} trace role is {trace.semantic_role}"
            )

    roads = {
        str(item["corridor_id"]): RoadCorridorIntent.from_dict(item)
        for item in data.get("roads", [])
    }
    road_graph = RoadGraph.from_dict(data.get("road_graph", {}))
    for intent in roads.values():
        for edge_id in intent.edge_refs:
            edge = road_graph.edge(edge_id)
            if edge.corridor_id != intent.corridor_id:
                raise ValueError(
                    f"edge {edge_id} belongs to {edge.corridor_id}, not {intent.corridor_id}"
                )
        if not any(
            trace.semantic_role == "road" for trace in trace_objects.values()
        ):
            raise ValueError("road corridor requires at least one road trace")

    return ConfirmedTraceScene(
        fixture_id=str(data["fixture_id"]),
        scene_id=str(data["scene_id"]),
        synthetic_only=synthetic_only,
        human_confirmed_trace=True,
        coordinate_frame=str(data["coordinate_frame"]),
        units=str(data["units"]),
        site_boundary_ref=site_boundary_ref,
        trace_objects=trace_objects,
        buildings=buildings,
        roads=roads,
        road_graph=road_graph,
    )

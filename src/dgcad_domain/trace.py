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
TRACE_REVIEW_STATES = frozenset({"confirmed", "confirmed_for_pilot"})
CONFIRMATION_SCOPES = frozenset({"synthetic", "pilot_subset", "full_case"})
GEOMETRY_QUALITIES = frozenset(
    {"synthetic_exact", "confirmed_for_pilot", "confirmed"}
)
REVIEW_KINDS = frozenset(
    {"synthetic_fixture", "human_object_review", "test_double"}
)
SITE_BOUNDARY_AUTHORITIES = frozenset(
    {
        "synthetic_reference",
        "authoritative_site_reference",
        "published_sketch_boundary",
    }
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
    confirmation_scope: str = "synthetic"
    geometry_quality: str = "synthetic_exact"
    review_kind: str = "synthetic_fixture"

    def __post_init__(self) -> None:
        if self.semantic_role not in SEMANTIC_ROLES:
            raise ValueError(f"unknown semantic role: {self.semantic_role}")
        if self.review_state not in TRACE_REVIEW_STATES:
            raise ValueError(
                f"trace {self.trace_id} has unknown review state: "
                f"{self.review_state}"
            )
        if self.confirmation_scope not in CONFIRMATION_SCOPES:
            raise ValueError(
                f"trace {self.trace_id} has unknown confirmation scope: "
                f"{self.confirmation_scope}"
            )
        if self.geometry_quality not in GEOMETRY_QUALITIES:
            raise ValueError(
                f"trace {self.trace_id} has unknown geometry quality: "
                f"{self.geometry_quality}"
            )
        if self.review_kind not in REVIEW_KINDS:
            raise ValueError(
                f"trace {self.trace_id} has unknown review kind: "
                f"{self.review_kind}"
            )
        if self.review_state == "confirmed_for_pilot":
            if self.confirmation_scope != "pilot_subset":
                raise ValueError(
                    f"trace {self.trace_id} is confirmed_for_pilot but scope is "
                    f"{self.confirmation_scope}"
                )
            if self.geometry_quality != "confirmed_for_pilot":
                raise ValueError(
                    f"trace {self.trace_id} is confirmed_for_pilot but quality is "
                    f"{self.geometry_quality}"
                )
        if self.review_state == "confirmed" and (
            self.confirmation_scope == "pilot_subset"
        ):
            raise ValueError(
                f"trace {self.trace_id} is fully confirmed inside a pilot scope"
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
    confirmation_scope: str = "synthetic"
    review_kind: str = "synthetic_fixture"
    geometry_quality: str = "synthetic_exact"
    site_boundary_authority: str = "synthetic_reference"
    site_canonical_id: str = "SITE-001"
    review_ref: str | None = None
    review_packet_sha256: str | None = None
    source_handoff_id: str | None = None
    test_only: bool = False

    def __post_init__(self) -> None:
        if self.confirmation_scope not in CONFIRMATION_SCOPES:
            raise ValueError(
                f"unknown confirmation scope: {self.confirmation_scope}"
            )
        if self.review_kind not in REVIEW_KINDS:
            raise ValueError(f"unknown review kind: {self.review_kind}")
        if self.geometry_quality not in GEOMETRY_QUALITIES:
            raise ValueError(
                f"unknown geometry quality: {self.geometry_quality}"
            )
        if self.site_boundary_authority not in SITE_BOUNDARY_AUTHORITIES:
            raise ValueError(
                "unknown site boundary authority: "
                f"{self.site_boundary_authority}"
            )
        if self.site_boundary_authority in {
            "synthetic_reference",
            "authoritative_site_reference",
        }:
            if self.site_canonical_id != "SITE-001":
                raise ValueError(
                    "an authoritative boundary must use canonical SITE-001"
                )
        elif self.site_canonical_id == "SITE-001":
            raise ValueError(
                "a published sketch boundary may not use canonical SITE-001"
            )

        if self.review_kind == "synthetic_fixture":
            if not self.synthetic_only:
                raise ValueError(
                    "synthetic_fixture review requires synthetic_only: true"
                )
            if not self.human_confirmed_trace:
                raise ValueError(
                    "a confirmed trace fixture must declare "
                    "human_confirmed_trace: true"
                )
        elif self.review_kind == "human_object_review":
            if not self.human_confirmed_trace:
                raise ValueError(
                    "human_object_review requires human_confirmed_trace: true"
                )
            if self.test_only:
                raise ValueError("human_object_review cannot be test_only")
            if self.confirmation_scope not in {"pilot_subset", "full_case"}:
                raise ValueError(
                    "human_object_review requires a pilot_subset or full_case "
                    "scope"
                )
            if not self.review_ref or not self.review_packet_sha256:
                raise ValueError(
                    "human_object_review requires review_ref and "
                    "review_packet_sha256"
                )
        else:
            if not self.test_only:
                raise ValueError(
                    "test_double review requires test_only: true"
                )
            if not self.human_confirmed_trace:
                raise ValueError(
                    "test_double requires a simulated human confirmation"
                )

        if self.confirmation_scope == "full_case":
            for trace in self.trace_objects.values():
                if trace.review_state != "confirmed":
                    raise ValueError(
                        f"full_case trace {trace.trace_id} is not fully confirmed"
                    )
                if trace.confirmation_scope != "full_case":
                    raise ValueError(
                        f"full_case trace {trace.trace_id} lost its scope"
                    )
        elif self.confirmation_scope == "pilot_subset":
            for trace in self.trace_objects.values():
                if trace.review_state != "confirmed_for_pilot":
                    raise ValueError(
                        f"pilot trace {trace.trace_id} is not "
                        "confirmed_for_pilot"
                    )
                if trace.confirmation_scope != "pilot_subset":
                    raise ValueError(
                        f"pilot trace {trace.trace_id} lost its scope"
                    )

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

    if synthetic_only:
        confirmation_scope = str(data.get("confirmation_scope", "synthetic"))
        review_kind = str(data.get("review_kind", "synthetic_fixture"))
        geometry_quality = str(data.get("geometry_quality", "synthetic_exact"))
        site_boundary_authority = str(
            data.get("site_boundary_authority", "synthetic_reference")
        )
    else:
        missing = [
            key
            for key in (
                "confirmation_scope",
                "review_kind",
                "geometry_quality",
                "site_boundary_authority",
            )
            if key not in data
        ]
        if missing:
            raise TraceNotConfirmed(
                "a real confirmed trace must declare "
                f"{', '.join(missing)}"
            )
        confirmation_scope = str(data["confirmation_scope"])
        review_kind = str(data["review_kind"])
        geometry_quality = str(data["geometry_quality"])
        site_boundary_authority = str(data["site_boundary_authority"])

    trace_objects: dict[str, TraceObject] = {}
    for item in data.get("trace_objects", []):
        record = _require_mapping(item, "trace object")
        trace_id = str(record["trace_id"])
        if trace_id in trace_objects:
            raise ValueError(f"duplicate trace id: {trace_id}")
        if synthetic_only:
            object_scope = str(
                record.get("confirmation_scope", confirmation_scope)
            )
            object_quality = str(
                record.get("geometry_quality", geometry_quality)
            )
            object_review_kind = str(
                record.get("review_kind", review_kind)
            )
        else:
            for key in (
                "confirmation_scope",
                "geometry_quality",
                "review_kind",
            ):
                if key not in record:
                    raise TraceNotConfirmed(
                        f"real trace {trace_id} must declare {key}"
                    )
            object_scope = str(record["confirmation_scope"])
            object_quality = str(record["geometry_quality"])
            object_review_kind = str(record["review_kind"])
        trace_objects[trace_id] = TraceObject(
            trace_id=trace_id,
            semantic_role=str(record["semantic_role"]),
            geometry=parse_geometry(record["geometry"]),
            review_state=str(record.get("review_state", "confirmed")),
            locked=bool(record.get("locked", True)),
            source_refs=tuple(str(ref) for ref in record.get("source_refs", [])),
            confirmation_scope=object_scope,
            geometry_quality=object_quality,
            review_kind=object_review_kind,
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
        for trace_ref in intent.trace_refs:
            trace = trace_objects.get(trace_ref)
            if trace is None:
                raise ValueError(
                    f"road {intent.corridor_id} references unknown trace {trace_ref}"
                )
            if trace.semantic_role != "road":
                raise ValueError(
                    f"road {intent.corridor_id} trace {trace_ref} has role {trace.semantic_role}"
                )
        for edge_id in intent.edge_refs:
            edge = road_graph.edge(edge_id)
            if edge.corridor_id != intent.corridor_id:
                raise ValueError(
                    f"edge {edge_id} belongs to {edge.corridor_id}, not {intent.corridor_id}"
                )

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
        confirmation_scope=confirmation_scope,
        review_kind=review_kind,
        geometry_quality=geometry_quality,
        site_boundary_authority=site_boundary_authority,
        site_canonical_id=str(data.get("site_canonical_id", "SITE-001")),
        review_ref=(
            None if data.get("review_ref") is None else str(data["review_ref"])
        ),
        review_packet_sha256=(
            None
            if data.get("review_packet_sha256") is None
            else str(data["review_packet_sha256"])
        ),
        source_handoff_id=(
            None
            if data.get("source_handoff_id") is None
            else str(data["source_handoff_id"])
        ),
        test_only=bool(data.get("test_only", False)),
    )

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import TYPE_CHECKING, Any

from shapely.geometry import MultiLineString
from shapely.ops import linemerge

from dgcad_foundation import DerivedArtifact, World

from .common import geometry_to_geojson, parse_geometry

if TYPE_CHECKING:
    from .trace import ConfirmedTraceScene


CLASSIFICATION_STATES = frozenset(
    {"unknown", "proposed", "confirmed", "needs_review", "disputed"}
)
COMPONENT_TYPES = frozenset(
    {
        "traffic_lane",
        "sidewalk",
        "cycle_lane",
        "parking_lane",
        "bus_lane",
        "median",
        "buffer",
        "planting_strip",
        "verge",
        "other",
    }
)
WIDTH_STATUSES = frozenset(
    {"sourced", "user_specified", "derived", "proposed", "unknown"}
)


@dataclass(frozen=True)
class CrossSectionComponent:
    component_type: str
    width_m: float | None
    width_status: str
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if self.component_type not in COMPONENT_TYPES:
            raise ValueError(f"unknown cross-section component: {self.component_type}")
        if self.width_status not in WIDTH_STATUSES:
            raise ValueError(f"unknown width status: {self.width_status}")
        if self.width_status == "unknown":
            if self.width_m is not None:
                raise ValueError("unknown width must not carry a numeric value")
            return
        if self.width_m is None:
            raise ValueError(f"{self.width_status} width requires a numeric value")
        if isinstance(self.width_m, bool) or not isfinite(float(self.width_m)):
            raise ValueError("width must be a finite number")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CrossSectionComponent":
        return cls(
            component_type=str(data["component_type"]),
            width_m=data.get("width_m"),
            width_status=str(data.get("width_status", "unknown")),
            source_ref=data.get("source_ref"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_type": self.component_type,
            "width_m": self.width_m,
            "width_status": self.width_status,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class CrossSectionProfile:
    profile_id: str
    components: tuple[CrossSectionComponent, ...]
    total_width_m: float | None
    status: str

    def __post_init__(self) -> None:
        if self.status not in {"draft", "needs_review", "validated_for_scope"}:
            raise ValueError(f"unknown profile status: {self.status}")
        if self.total_width_m is not None:
            if isinstance(self.total_width_m, bool) or not isfinite(
                float(self.total_width_m)
            ):
                raise ValueError("total width must be a finite number")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "CrossSectionProfile | None":
        if data is None:
            return None
        components = tuple(
            CrossSectionComponent.from_dict(item)
            for item in data.get("components", [])
        )
        return cls(
            profile_id=str(data.get("profile_id", "XS-UNNAMED")),
            components=components,
            total_width_m=data.get("total_width_m"),
            status=str(data.get("status", "draft")),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "profile_id": self.profile_id,
            "components": [component.to_dict() for component in self.components],
            "total_width_m": self.total_width_m,
            "status": self.status,
        }


@dataclass(frozen=True)
class ProfileResolution:
    outcome: str
    code: str
    hierarchy: str | None
    components: tuple[CrossSectionComponent, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "outcome": self.outcome,
            "code": self.code,
            "hierarchy": self.hierarchy,
            "components": [component.to_dict() for component in self.components],
            "message": self.message,
        }


@dataclass(frozen=True)
class RoadNode:
    node_id: str
    x: float
    y: float
    junction: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoadNode":
        x = float(data["x"])
        y = float(data["y"])
        if isinstance(data["x"], bool) or isinstance(data["y"], bool):
            raise ValueError("node coordinates must be numeric")
        if not isfinite(x) or not isfinite(y):
            raise ValueError("node coordinates must be finite")
        return cls(
            node_id=str(data["node_id"]),
            x=x,
            y=y,
            junction=bool(data.get("junction", False)),
        )


@dataclass(frozen=True)
class RoadEdge:
    edge_id: str
    corridor_id: str
    node_a: str
    node_b: str
    centerline: Any

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoadEdge":
        centerline = parse_geometry(data["centerline"])
        if centerline.geom_type not in {"LineString", "MultiLineString"}:
            raise ValueError("edge centerline must be a line geometry")
        return cls(
            edge_id=str(data["edge_id"]),
            corridor_id=str(data["corridor_id"]),
            node_a=str(data["node_a"]),
            node_b=str(data["node_b"]),
            centerline=centerline,
        )


@dataclass(frozen=True)
class RoadGraph:
    nodes: dict[str, RoadNode]
    edges: dict[str, RoadEdge]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoadGraph":
        nodes = {
            str(item["node_id"]): RoadNode.from_dict(item)
            for item in data.get("nodes", [])
        }
        edges = {
            str(item["edge_id"]): RoadEdge.from_dict(item)
            for item in data.get("edges", [])
        }
        for edge in edges.values():
            if edge.node_a not in nodes or edge.node_b not in nodes:
                raise ValueError(f"edge {edge.edge_id} references unknown node")
        return cls(nodes=nodes, edges=edges)

    def edge(self, edge_id: str) -> RoadEdge:
        try:
            return self.edges[edge_id]
        except KeyError as exc:
            raise ValueError(f"unknown road edge: {edge_id}") from exc

    def incident_edges(self, node_id: str) -> tuple[RoadEdge, ...]:
        return tuple(
            edge
            for edge in self.edges.values()
            if edge.node_a == node_id or edge.node_b == node_id
        )


@dataclass(frozen=True)
class RoadCorridorIntent:
    corridor_id: str
    trace_refs: tuple[str, ...]
    edge_refs: tuple[str, ...]
    hierarchy: str | None
    hierarchy_state: str
    primary_function: str
    permitted_modes: tuple[str, ...]
    special_designations: tuple[str, ...]
    cross_section: CrossSectionProfile | None

    def __post_init__(self) -> None:
        if not self.trace_refs:
            raise ValueError(f"corridor {self.corridor_id} has no trace refs")
        if not self.edge_refs:
            raise ValueError(f"corridor {self.corridor_id} has no edges")
        if self.hierarchy_state not in CLASSIFICATION_STATES:
            raise ValueError(f"unknown hierarchy state: {self.hierarchy_state}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RoadCorridorIntent":
        return cls(
            corridor_id=str(data["corridor_id"]),
            trace_refs=tuple(str(item) for item in data.get("trace_refs", [])),
            edge_refs=tuple(str(item) for item in data.get("edge_refs", [])),
            hierarchy=data.get("hierarchy"),
            hierarchy_state=str(data.get("hierarchy_state", "unknown")),
            primary_function=str(data.get("primary_function", "unknown")),
            permitted_modes=tuple(
                str(item) for item in data.get("permitted_modes", [])
            ),
            special_designations=tuple(
                str(item) for item in data.get("special_designations", [])
            ),
            cross_section=CrossSectionProfile.from_dict(data.get("cross_section")),
        )


@dataclass(frozen=True)
class RoadCandidate:
    corridor_id: str
    edge_refs: tuple[str, ...]
    centerline: Any
    centerline_state: str
    hierarchy: str | None
    hierarchy_state: str
    primary_function: str
    permitted_modes: tuple[str, ...]
    special_designations: tuple[str, ...]
    cross_section: CrossSectionProfile | None
    profile_resolution: ProfileResolution

    def to_changes(self) -> dict[str, Any]:
        return {
            "centerline": geometry_to_geojson(self.centerline),
            "centerline_state": self.centerline_state,
            "hierarchy": self.hierarchy,
            "hierarchy_state": self.hierarchy_state,
            "primary_function": self.primary_function,
            "permitted_modes": list(self.permitted_modes),
            "special_designations": list(self.special_designations),
            "cross_section": (
                None
                if self.cross_section is None
                else self.cross_section.to_dict()
            ),
            "profile_resolution": self.profile_resolution.to_dict(),
        }


class RoadSurfaceBlocked(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


def _explicit_widths_are_resolved(
    profile: CrossSectionProfile,
) -> bool:
    return all(
        component.width_m is not None
        and component.width_status in {"sourced", "user_specified"}
        for component in profile.components
    )


def resolve_profile_for_class(
    hierarchy: str | None,
    hierarchy_state: str,
    explicit_profile: CrossSectionProfile | None,
) -> ProfileResolution:
    if not hierarchy or hierarchy_state != "confirmed":
        if explicit_profile is not None and _explicit_widths_are_resolved(
            explicit_profile
        ):
            return ProfileResolution(
                outcome="needs_review",
                code="ROAD_CLASS_UNCONFIRMED",
                hierarchy=hierarchy,
                components=explicit_profile.components,
                message=(
                    "explicit user-specified widths retained, but road class "
                    "remains unconfirmed and no derived width is allowed"
                ),
            )
        return ProfileResolution(
            outcome="blocked",
            code="ROAD_CLASS_UNCONFIRMED",
            hierarchy=hierarchy,
            components=(),
            message="road hierarchy is unknown or unconfirmed",
        )

    if explicit_profile is None:
        return ProfileResolution(
            outcome="blocked",
            code="NO_PROFILE_FOR_CLASS",
            hierarchy=hierarchy,
            components=(),
            message="no authorized design profile is bound to this class",
        )

    if not _explicit_widths_are_resolved(explicit_profile):
        return ProfileResolution(
            outcome="blocked",
            code="NO_PROFILE_FOR_CLASS",
            hierarchy=hierarchy,
            components=(),
            message=(
                "explicit profile contains unresolved or derived widths; "
                "no authorized profile registry is available"
            ),
        )

    return ProfileResolution(
        outcome="resolved",
        code="OK",
        hierarchy=hierarchy,
        components=explicit_profile.components,
        message="explicit user-specified profile resolved",
    )


def road_corridor_candidate(
    trace_scene: "ConfirmedTraceScene",
    intent: RoadCorridorIntent,
) -> RoadCandidate:
    edges = [trace_scene.road_graph.edge(edge_id) for edge_id in intent.edge_refs]
    geometries = [edge.centerline for edge in edges]
    if len(geometries) == 1:
        centerline = geometries[0]
    else:
        centerline = linemerge(MultiLineString(geometries))
    if centerline.is_empty:
        raise ValueError(f"ROAD_GEOMETRY_INVALID: {intent.corridor_id}")

    resolution = resolve_profile_for_class(
        intent.hierarchy, intent.hierarchy_state, intent.cross_section
    )
    return RoadCandidate(
        corridor_id=intent.corridor_id,
        edge_refs=intent.edge_refs,
        centerline=centerline,
        centerline_state="confirmed",
        hierarchy=intent.hierarchy,
        hierarchy_state=intent.hierarchy_state,
        primary_function=intent.primary_function,
        permitted_modes=intent.permitted_modes,
        special_designations=intent.special_designations,
        cross_section=intent.cross_section,
        profile_resolution=resolution,
    )


def road_surface_artifact(scene, corridor_id: str) -> DerivedArtifact:
    obj = scene.objects.get(corridor_id)
    if obj is None:
        raise RoadSurfaceBlocked("CORRIDOR_NOT_FOUND", corridor_id)
    if obj.values.get("centerline_state") != "confirmed":
        raise RoadSurfaceBlocked(
            "ROAD_CENTERLINE_NOT_CONFIRMED", corridor_id
        )
    resolution = obj.values.get("profile_resolution") or {}
    if resolution.get("outcome") != "resolved":
        raise RoadSurfaceBlocked(
            "ROAD_PROFILE_BLOCKED",
            f"{corridor_id} profile outcome is {resolution.get('outcome')}",
        )
    edge_refs = obj.values.get("edge_refs", [])
    dependency_keys = {f"{edge_id}.geometry" for edge_id in edge_refs}
    dependency_keys.add(f"{corridor_id}.parameter")
    return DerivedArtifact(
        artifact_id=f"SURFACE-{corridor_id}",
        artifact_type="road_surface",
        world=World.CANONICAL_CURRENT,
        dependency_keys=frozenset(dependency_keys),
    )

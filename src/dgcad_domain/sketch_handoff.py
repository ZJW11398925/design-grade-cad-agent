from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from .building import BuildingIntent
from .common import geometry_to_geojson, parse_geometry
from .road import RoadCorridorIntent, RoadEdge, RoadGraph, RoadNode
from .trace import (
    TRACE_SCHEMA_ID,
    ConfirmedTraceScene,
    TraceNotConfirmed,
    TraceObject,
)

HANDOFF_SCHEMA_ID = "dgcad.sketch-domain-handoff.v0.1"
REVIEW_SCHEMA_ID = "dgcad.sketch-handoff-review.v0.1"
HANDOFF_SEMANTIC_ROLES = frozenset(
    {"site_boundary", "building", "green", "road"}
)
REVIEWER_ROLES = frozenset({"designer", "human_reviewer"})
REVIEW_SCOPES = frozenset({"pilot_subset", "full_case"})
GEOMETRY_STATES = frozenset({"confirmed_for_pilot", "confirmed"})


class SketchHandoffError(ValueError):
    pass


class SketchHandoffNotConfirmed(SketchHandoffError):
    pass


class SketchHandoffInvalid(SketchHandoffError):
    pass


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SketchHandoffInvalid(f"{name} must be a mapping")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise SketchHandoffInvalid(f"{name} must be a list")
    return value


def _transform_coordinates(coordinates: Any, scale: float, origin_x: float, origin_y: float):
    if not isinstance(coordinates, (list, tuple)):
        raise SketchHandoffInvalid("geometry coordinates must be lists")
    if coordinates and isinstance(coordinates[0], (int, float)):
        if len(coordinates) < 2:
            raise SketchHandoffInvalid("point must have x and y")
        x, y = float(coordinates[0]), float(coordinates[1])
        return [
            round((x - origin_x) / scale, 9),
            round((origin_y - y) / scale, 9),
        ]
    return [
        _transform_coordinates(item, scale, origin_x, origin_y)
        for item in coordinates
    ]


@dataclass(frozen=True)
class CoordinateHandoff:
    source_frame: str
    target_frame: str
    coordinate_state: str
    scale_px_per_m: float
    scale_range_px_per_m: tuple[float, float]
    origin_px: tuple[float, float]
    y_axis: str
    project_coordinates: bool
    calibration_ref: str
    review_state: str
    accuracy: str
    not_survey_grade: bool

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CoordinateHandoff":
        data = _mapping(data, "coordinate_handoff")
        scale = float(data["scale_px_per_m"])
        low, high = (float(item) for item in data["scale_range_px_per_m"])
        origin_x, origin_y = (float(item) for item in data["origin_px"])
        handoff = cls(
            source_frame=str(data["source_frame"]),
            target_frame=str(data["target_frame"]),
            coordinate_state=str(data["coordinate_state"]),
            scale_px_per_m=scale,
            scale_range_px_per_m=(low, high),
            origin_px=(origin_x, origin_y),
            y_axis=str(data["y_axis"]),
            project_coordinates=bool(data["project_coordinates"]),
            calibration_ref=str(data["calibration_ref"]),
            review_state=str(data["review_state"]),
            accuracy=str(data["accuracy"]),
            not_survey_grade=bool(data["not_survey_grade"]),
        )
        handoff.validate()
        return handoff

    def validate(self) -> None:
        if self.source_frame != "image_space_unscaled":
            raise SketchHandoffInvalid(
                "source_frame must be image_space_unscaled"
            )
        if self.target_frame != "LOCAL-ENU-XY-ZUP":
            raise SketchHandoffInvalid("target_frame must be LOCAL-ENU-XY-ZUP")
        if self.coordinate_state != "local_metric_scaled":
            raise SketchHandoffInvalid(
                "coordinate_state must be local_metric_scaled"
            )
        if self.project_coordinates:
            raise SketchHandoffInvalid(
                "project_coordinates must be false for the pilot"
            )
        if not isfinite(self.scale_px_per_m) or self.scale_px_per_m <= 0:
            raise SketchHandoffInvalid("scale must be positive and finite")
        if not all(isfinite(value) for value in self.scale_range_px_per_m):
            raise SketchHandoffInvalid("scale range must be finite")
        if not (
            self.scale_range_px_per_m[0]
            <= self.scale_px_per_m
            <= self.scale_range_px_per_m[1]
        ):
            raise SketchHandoffInvalid("scale must lie inside the declared range")
        if not all(isfinite(value) for value in self.origin_px):
            raise SketchHandoffInvalid("origin must be finite")
        if self.y_axis != "flipped":
            raise SketchHandoffInvalid("y_axis must be flipped")
        if self.review_state != "reviewed":
            raise SketchHandoffInvalid("coordinate review_state must be reviewed")
        if self.accuracy != "approximate":
            raise SketchHandoffInvalid("pilot coordinate accuracy must be approximate")
        if not self.not_survey_grade:
            raise SketchHandoffInvalid(
                "pilot coordinate handoff must declare not_survey_grade"
            )
        if not self.calibration_ref:
            raise SketchHandoffInvalid("calibration_ref is required")

    def transform_geometry(self, payload: dict[str, Any]) -> dict[str, Any]:
        geometry = _mapping(payload, "geometry")
        geometry_type = str(geometry.get("type"))
        if geometry_type not in {
            "Point",
            "LineString",
            "Polygon",
            "MultiPolygon",
        }:
            raise SketchHandoffInvalid(
                f"unsupported handoff geometry: {geometry_type}"
            )
        transformed = {
            "type": geometry_type,
            "coordinates": _transform_coordinates(
                geometry["coordinates"],
                self.scale_px_per_m,
                self.origin_px[0],
                self.origin_px[1],
            ),
        }
        parsed = parse_geometry(transformed)
        if parsed.geom_type in {"Polygon", "MultiPolygon"} and not parsed.is_valid:
            raise SketchHandoffInvalid("transformed polygon is invalid")
        return geometry_to_geojson(parsed)

    def transform_point(self, x: float, y: float) -> tuple[float, float]:
        return (
            (float(x) - self.origin_px[0]) / self.scale_px_per_m,
            (self.origin_px[1] - float(y)) / self.scale_px_per_m,
        )


@dataclass(frozen=True)
class HandoffReview:
    handoff_id: str
    reviewer: str
    reviewer_role: str
    review_scope: str
    human_confirmed_trace: bool
    reviewed_at: str
    basis: str
    decisions: dict[str, dict[str, Any]]
    limitations: tuple[str, ...] = ()
    non_claims: tuple[str, ...] = ()

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffReview":
        data = _mapping(data, "review")
        if data.get("schema_id") != REVIEW_SCHEMA_ID:
            raise SketchHandoffInvalid(
                f"unexpected review schema: {data.get('schema_id')}"
            )
        decisions = {}
        for item in _list(data.get("decisions", []), "review.decisions"):
            record = _mapping(item, "review decision")
            source_id = str(record["source_id"])
            if source_id in decisions:
                raise SketchHandoffInvalid(f"duplicate review decision: {source_id}")
            decisions[source_id] = {
                "semantic": str(record.get("semantic")),
                "geometry": str(record.get("geometry")),
                "coordinate": str(record.get("coordinate")),
            }
        review = cls(
            handoff_id=str(data["handoff_id"]),
            reviewer=str(data["reviewer"]),
            reviewer_role=str(data["reviewer_role"]),
            review_scope=str(data["review_scope"]),
            human_confirmed_trace=bool(data.get("human_confirmed_trace")),
            reviewed_at=str(data["reviewed_at"]),
            basis=str(data["basis"]),
            decisions=decisions,
            limitations=tuple(str(item) for item in data.get("limitations", [])),
            non_claims=tuple(str(item) for item in data.get("non_claims", [])),
        )
        review.validate()
        return review

    def validate(self) -> None:
        if self.reviewer_role not in REVIEWER_ROLES:
            raise SketchHandoffNotConfirmed(
                "handoff review must be by a designer or human reviewer"
            )
        if not self.reviewer:
            raise SketchHandoffInvalid("reviewer is required")
        if self.review_scope not in REVIEW_SCOPES:
            raise SketchHandoffInvalid(f"unknown review scope: {self.review_scope}")
        if not self.human_confirmed_trace:
            raise SketchHandoffNotConfirmed(
                "human_confirmed_trace must be true"
            )
        if not self.reviewed_at or not self.basis:
            raise SketchHandoffInvalid("reviewed_at and basis are required")

    def decision(self, source_id: str) -> dict[str, Any]:
        try:
            return self.decisions[source_id]
        except KeyError as exc:
            raise SketchHandoffNotConfirmed(
                f"no human review decision for {source_id}"
            ) from exc


@dataclass(frozen=True)
class HandoffObject:
    source_id: str
    trace_id: str
    canonical_id: str
    semantic_role: str
    geometry: dict[str, Any]
    semantic_state: str
    geometry_state: str
    provenance: dict[str, Any]
    attributes: dict[str, Any]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HandoffObject":
        data = _mapping(data, "handoff object")
        role = str(data["semantic_role"])
        if role not in HANDOFF_SEMANTIC_ROLES:
            raise SketchHandoffInvalid(f"unknown semantic role: {role}")
        geometry = _mapping(data["geometry"], "object.geometry")
        parse_geometry(geometry)
        provenance = _mapping(data.get("provenance", {}), "object.provenance")
        if not provenance.get("source_ref") or not provenance.get("source_hash"):
            raise SketchHandoffInvalid(
                f"{data.get('source_id')} provenance needs source_ref and source_hash"
            )
        return cls(
            source_id=str(data["source_id"]),
            trace_id=str(data["trace_id"]),
            canonical_id=str(data["canonical_id"]),
            semantic_role=role,
            geometry=geometry,
            semantic_state=str(data["semantic_state"]),
            geometry_state=str(data["geometry_state"]),
            provenance=provenance,
            attributes=dict(data.get("attributes", {})),
        )


@dataclass(frozen=True)
class SketchHandoff:
    handoff_id: str
    case_id: str
    source_sketch_sha256: str
    synthetic_only: bool
    coordinate: CoordinateHandoff
    review: HandoffReview
    objects: dict[str, HandoffObject]
    buildings: tuple[BuildingIntent, ...]
    roads: tuple[RoadCorridorIntent, ...]
    road_graph: RoadGraph
    source_edge_ids_by_corridor: dict[str, tuple[str, ...]]
    non_claims: tuple[str, ...]

    @classmethod
    def from_dicts(
        cls, handoff_data: dict[str, Any], review_data: dict[str, Any]
    ) -> "SketchHandoff":
        handoff_data = _mapping(handoff_data, "handoff")
        if handoff_data.get("schema_id") != HANDOFF_SCHEMA_ID:
            raise SketchHandoffInvalid(
                f"unexpected handoff schema: {handoff_data.get('schema_id')}"
            )
        handoff_id = str(handoff_data["handoff_id"])
        review = HandoffReview.from_dict(review_data)
        if review.handoff_id != handoff_id:
            raise SketchHandoffInvalid("review handoff_id mismatch")
        if handoff_data.get("synthetic_only") is not False:
            raise SketchHandoffInvalid(
                "a real sketch handoff must declare synthetic_only: false"
            )
        source_hash = str(handoff_data.get("source_sketch_sha256", ""))
        if not source_hash:
            raise SketchHandoffInvalid("source_sketch_sha256 is required")

        coordinate = CoordinateHandoff.from_dict(handoff_data["coordinate_handoff"])
        objects: dict[str, HandoffObject] = {}
        trace_ids: set[str] = set()
        canonical_ids: set[str] = set()
        for item in _list(handoff_data.get("objects", []), "objects"):
            obj = HandoffObject.from_dict(item)
            if obj.source_id in objects:
                raise SketchHandoffInvalid(f"duplicate source_id: {obj.source_id}")
            if obj.trace_id in trace_ids:
                raise SketchHandoffInvalid(f"duplicate trace_id: {obj.trace_id}")
            if obj.canonical_id in canonical_ids:
                raise SketchHandoffInvalid(
                    f"duplicate canonical_id: {obj.canonical_id}"
                )
            if obj.semantic_state != "confirmed":
                raise SketchHandoffNotConfirmed(
                    f"{obj.source_id} semantic state is {obj.semantic_state}"
                )
            if obj.geometry_state not in GEOMETRY_STATES:
                raise SketchHandoffNotConfirmed(
                    f"{obj.source_id} geometry state is {obj.geometry_state}"
                )
            decision = review.decision(obj.source_id)
            if decision["semantic"] != "confirmed":
                raise SketchHandoffNotConfirmed(
                    f"{obj.source_id} has no confirmed semantic decision"
                )
            if decision["geometry"] != obj.geometry_state:
                raise SketchHandoffNotConfirmed(
                    f"{obj.source_id} review/geometry state mismatch"
                )
            if decision["coordinate"] not in {
                "local_metric_approximate",
                "reviewed",
            }:
                raise SketchHandoffInvalid(
                    f"{obj.source_id} has no coordinate review decision"
                )
            objects[obj.source_id] = obj
            trace_ids.add(obj.trace_id)
            canonical_ids.add(obj.canonical_id)

        if set(review.decisions) != set(objects):
            missing = sorted(set(objects) - set(review.decisions))
            extra = sorted(set(review.decisions) - set(objects))
            raise SketchHandoffNotConfirmed(
                f"review decisions do not match objects; missing={missing}, extra={extra}"
            )

        site_objects = [
            obj for obj in objects.values() if obj.semantic_role == "site_boundary"
        ]
        if len(site_objects) != 1:
            raise SketchHandoffInvalid(
                "exactly one site_boundary object is required"
            )
        site = site_objects[0]
        if site.canonical_id != "SITE-001":
            raise SketchHandoffInvalid("site boundary canonical_id must be SITE-001")

        buildings: list[BuildingIntent] = []
        for item in _list(handoff_data.get("buildings", []), "buildings"):
            intent = BuildingIntent.from_dict(item)
            if intent.trace_ref not in {obj.trace_id for obj in objects.values()}:
                raise SketchHandoffInvalid(
                    f"building {intent.object_id} has unknown trace_ref"
                )
            trace_obj = next(
                obj for obj in objects.values() if obj.trace_id == intent.trace_ref
            )
            if trace_obj.semantic_role != "building":
                raise SketchHandoffInvalid(
                    f"building {intent.object_id} trace role is not building"
                )
            if trace_obj.canonical_id != intent.object_id:
                raise SketchHandoffInvalid(
                    f"building {intent.object_id} canonical mapping mismatch"
                )
            if intent.height.state == "unknown" and intent.height.value is not None:
                raise SketchHandoffInvalid("unknown height must be null")
            buildings.append(intent)

        road_graph = RoadGraph.from_dict(handoff_data.get("road_graph", {}))
        roads: list[RoadCorridorIntent] = []
        source_edge_ids_by_corridor: dict[str, tuple[str, ...]] = {}
        for item in _list(handoff_data.get("roads", []), "roads"):
            intent = RoadCorridorIntent.from_dict(item)
            for trace_ref in intent.trace_refs:
                trace_obj = next(
                    (obj for obj in objects.values() if obj.trace_id == trace_ref),
                    None,
                )
                if trace_obj is None or trace_obj.semantic_role != "road":
                    raise SketchHandoffInvalid(
                        f"road {intent.corridor_id} trace {trace_ref} is not a road trace"
                    )
            for edge_id in intent.edge_refs:
                edge = road_graph.edge(edge_id)
                if edge.corridor_id != intent.corridor_id:
                    raise SketchHandoffInvalid(
                        f"edge {edge_id} belongs to {edge.corridor_id}"
                    )
            source_edge_ids_by_corridor[intent.corridor_id] = tuple(
                str(item) for item in item.get("source_edge_ids", [])
            )
            roads.append(intent)

        return cls(
            handoff_id=handoff_id,
            case_id=str(handoff_data["case_id"]),
            source_sketch_sha256=source_hash,
            synthetic_only=False,
            coordinate=coordinate,
            review=review,
            objects=objects,
            buildings=tuple(buildings),
            roads=tuple(roads),
            road_graph=road_graph,
            source_edge_ids_by_corridor=source_edge_ids_by_corridor,
            non_claims=tuple(
                str(item) for item in handoff_data.get("non_claims", [])
            ),
        )

    @classmethod
    def load(
        cls, handoff_path: str | Path, review_path: str | Path
    ) -> "SketchHandoff":
        handoff_data = yaml.safe_load(
            Path(handoff_path).read_text(encoding="utf-8")
        )
        review_data = yaml.safe_load(
            Path(review_path).read_text(encoding="utf-8")
        )
        return cls.from_dicts(handoff_data, review_data)

    def _trace_objects(self) -> dict[str, TraceObject]:
        trace_objects = {}
        for obj in self.objects.values():
            local_geometry = self.coordinate.transform_geometry(obj.geometry)
            trace_objects[obj.trace_id] = TraceObject(
                trace_id=obj.trace_id,
                semantic_role=obj.semantic_role,
                geometry=parse_geometry(local_geometry),
                review_state="confirmed",
                locked=True,
                source_refs=(obj.source_id,),
            )
        return trace_objects

    def _road_graph_local(self) -> RoadGraph:
        nodes = {}
        for node in self.road_graph.nodes.values():
            x, y = self.coordinate.transform_point(node.x, node.y)
            nodes[node.node_id] = RoadNode(
                node_id=node.node_id,
                x=x,
                y=y,
                junction=node.junction,
            )
        edges = {}
        for edge in self.road_graph.edges.values():
            local_centerline = self.coordinate.transform_geometry(
                geometry_to_geojson(edge.centerline)
            )
            edges[edge.edge_id] = RoadEdge(
                edge_id=edge.edge_id,
                corridor_id=edge.corridor_id,
                node_a=edge.node_a,
                node_b=edge.node_b,
                centerline=parse_geometry(local_centerline),
            )
        return RoadGraph(nodes=nodes, edges=edges)

    def to_confirmed_trace_scene(self) -> ConfirmedTraceScene:
        site = next(
            obj for obj in self.objects.values() if obj.semantic_role == "site_boundary"
        )
        return ConfirmedTraceScene(
            fixture_id=self.handoff_id,
            scene_id=f"scene-{self.handoff_id}",
            synthetic_only=False,
            human_confirmed_trace=True,
            coordinate_frame=self.coordinate.target_frame,
            units="metre",
            site_boundary_ref=site.trace_id,
            trace_objects=self._trace_objects(),
            buildings={intent.object_id: intent for intent in self.buildings},
            roads={intent.corridor_id: intent for intent in self.roads},
            road_graph=self._road_graph_local(),
        )

    def to_domain_fixture(self) -> dict[str, Any]:
        site = next(
            obj for obj in self.objects.values() if obj.semantic_role == "site_boundary"
        )
        trace_objects = []
        for obj in self.objects.values():
            trace_objects.append(
                {
                    "trace_id": obj.trace_id,
                    "semantic_role": obj.semantic_role,
                    "review_state": "confirmed",
                    "locked": True,
                    "source_refs": [obj.source_id],
                    "geometry": self.coordinate.transform_geometry(obj.geometry),
                }
            )
        road_graph = self._road_graph_local()
        return {
            "schema_id": TRACE_SCHEMA_ID,
            "fixture_id": self.handoff_id,
            "scene_id": f"scene-{self.handoff_id}",
            "synthetic_only": False,
            "human_confirmed_trace": True,
            "coordinate_frame": self.coordinate.target_frame,
            "units": "metre",
            "site_boundary_ref": site.trace_id,
            "trace_objects": trace_objects,
            "buildings": [
                {
                    "object_id": intent.object_id,
                    "trace_ref": intent.trace_ref,
                    "height": intent.height.to_dict(),
                    "base_elevation": intent.base_elevation.to_dict(),
                    "typology": intent.typology,
                    "typology_state": intent.typology_state,
                    "regularization_request": intent.regularization_request,
                }
                for intent in self.buildings
            ],
            "roads": [
                {
                    "corridor_id": intent.corridor_id,
                    "trace_refs": list(intent.trace_refs),
                    "edge_refs": list(intent.edge_refs),
                    "hierarchy": intent.hierarchy,
                    "hierarchy_state": intent.hierarchy_state,
                    "primary_function": intent.primary_function,
                    "permitted_modes": list(intent.permitted_modes),
                    "special_designations": list(intent.special_designations),
                    "cross_section": (
                        None
                        if intent.cross_section is None
                        else intent.cross_section.to_dict()
                    ),
                }
                for intent in self.roads
            ],
            "road_graph": {
                "nodes": [
                    {
                        "node_id": node.node_id,
                        "x": node.x,
                        "y": node.y,
                        "junction": node.junction,
                    }
                    for node in road_graph.nodes.values()
                ],
                "edges": [
                    {
                        "edge_id": edge.edge_id,
                        "corridor_id": edge.corridor_id,
                        "node_a": edge.node_a,
                        "node_b": edge.node_b,
                        "centerline": geometry_to_geojson(edge.centerline),
                    }
                    for edge in road_graph.edges.values()
                ],
            },
            "handoff": {
                "handoff_id": self.handoff_id,
                "case_id": self.case_id,
                "source_sketch_sha256": self.source_sketch_sha256,
                "review_scope": self.review.review_scope,
                "reviewer_role": self.review.reviewer_role,
                "review_basis": self.review.basis,
                "coordinate_handoff": {
                    "source_frame": self.coordinate.source_frame,
                    "target_frame": self.coordinate.target_frame,
                    "coordinate_state": self.coordinate.coordinate_state,
                    "scale_px_per_m": self.coordinate.scale_px_per_m,
                    "scale_range_px_per_m": list(
                        self.coordinate.scale_range_px_per_m
                    ),
                    "origin_px": list(self.coordinate.origin_px),
                    "y_axis": self.coordinate.y_axis,
                    "project_coordinates": self.coordinate.project_coordinates,
                    "calibration_ref": self.coordinate.calibration_ref,
                    "accuracy": self.coordinate.accuracy,
                    "not_survey_grade": self.coordinate.not_survey_grade,
                },
                "mapping": self.mapping(),
                "source_edge_ids_by_corridor": {
                    key: list(value)
                    for key, value in self.source_edge_ids_by_corridor.items()
                },
                "non_claims": list(self.non_claims),
            },
        }

    def mapping(self) -> list[dict[str, str]]:
        return [
            {
                "source_id": obj.source_id,
                "trace_id": obj.trace_id,
                "canonical_id": obj.canonical_id,
                "semantic_role": obj.semantic_role,
            }
            for obj in self.objects.values()
        ]

    def write_domain_fixture(self, path: str | Path) -> None:
        Path(path).write_text(
            yaml.safe_dump(self.to_domain_fixture(), sort_keys=False),
            encoding="utf-8",
        )

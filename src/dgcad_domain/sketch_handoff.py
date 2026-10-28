from __future__ import annotations

import hashlib
import json
import math
from collections import Counter, defaultdict
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
    TraceObject,
)


HANDOFF_SCHEMA_ID = "dgcad.sketch-domain-handoff.v0.2"
REVIEW_SCHEMA_ID = "dgcad.sketch-handoff-review.v0.2"
HANDOFF_SEMANTIC_ROLES = frozenset(
    {"site_boundary", "building", "green", "road"}
)
REVIEWER_ROLES = frozenset({"designer", "human_reviewer"})
REVIEW_SCOPES = frozenset({"pilot_subset", "full_case"})
REVIEW_KINDS = frozenset(
    {"human_object_review", "designer_authorized_pilot", "test_double"}
)
OBJECT_GEOMETRY_STATES = frozenset(
    {"proposed", "not_reviewed", "confirmed_for_pilot", "confirmed"}
)
CONFIRMED_GEOMETRY_STATES = frozenset({"confirmed_for_pilot", "confirmed"})
COORDINATE_DECISIONS = frozenset(
    {"not_reviewed", "local_metric_approximate", "reviewed"}
)
SITE_BOUNDARY_AUTHORITIES = frozenset(
    {"authoritative_site_reference", "published_sketch_boundary"}
)
SOURCE_GEOMETRY_ALGORITHMS = frozenset(
    {"canonical_geojson_sha256_round9"}
)
TRANSFORM_KINDS = frozenset({"uniform_scale_translation_yflip"})
AXIS_ORIENTATIONS = frozenset({"unknown", "east_north_defined"})
PUBLICATION_CLASSIFICATIONS = frozenset(
    {"pilot_local_metric", "image_space_only"}
)
REQUIRED_EXCLUDED_ASSETS = frozenset(
    {"dwg", "redline", "project_coordinates", "calibration_matrix"}
)


class SketchHandoffError(ValueError):
    code = "SKETCH_HANDOFF_ERROR"

    def __init__(self, message: str, *, code: str | None = None) -> None:
        super().__init__(message)
        if code is not None:
            self.code = code


class SketchHandoffNotConfirmed(SketchHandoffError):
    code = "HANDOFF_NOT_CONFIRMED"


class SketchHandoffInvalid(SketchHandoffError):
    code = "HANDOFF_INVALID"


def _mapping(value: Any, name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise SketchHandoffInvalid(f"{name} must be a mapping")
    return value


def _list(value: Any, name: str) -> list[Any]:
    if not isinstance(value, list):
        raise SketchHandoffInvalid(f"{name} must be a list")
    return value


def _sha256_text(value: Any, name: str) -> str:
    text = str(value or "")
    if len(text) != 64 or any(char not in "0123456789abcdef" for char in text):
        raise SketchHandoffInvalid(
            f"{name} must be 64 lowercase hex characters"
        )
    return text


def _round_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return round(float(value), 9)
    if isinstance(value, (list, tuple)):
        return [_round_value(item) for item in value]
    if isinstance(value, dict):
        return {
            str(key): _round_value(item)
            for key, item in sorted(value.items())
        }
    return value


def normalized_geometry(payload: dict[str, Any]) -> dict[str, Any]:
    geometry = parse_geometry(payload)
    return _round_value(geometry_to_geojson(geometry))


def geometry_sha256(payload: dict[str, Any]) -> str:
    canonical = json.dumps(
        normalized_geometry(payload),
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def _find_geojson_feature(
    data: Any, object_id: str
) -> dict[str, Any] | None:
    if not isinstance(data, dict):
        return None
    features = data.get("features")
    if isinstance(features, list):
        for feature in features:
            if not isinstance(feature, dict):
                continue
            properties = feature.get("properties") or {}
            for key in ("trace_id", "edge_id", "node_id", "source_id", "id"):
                if str(properties.get(key)) == object_id:
                    return feature
            if str(feature.get("id")) == object_id:
                return feature
    if str(data.get("id")) == object_id:
        return data
    return None


def _load_json_source(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def _transform_coordinates(
    coordinates: Any, scale: float, origin_x: float, origin_y: float
):
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


def _geometry_metrics(geometry) -> dict[str, float]:
    if geometry.geom_type in {"Polygon", "MultiPolygon"}:
        return {
            "area": float(geometry.area),
            "perimeter": float(geometry.length),
            "centroid_x": float(geometry.centroid.x),
            "centroid_y": float(geometry.centroid.y),
        }
    if geometry.geom_type in {"LineString", "MultiLineString"}:
        return {
            "area": 0.0,
            "perimeter": float(geometry.length),
            "centroid_x": float(geometry.centroid.x),
            "centroid_y": float(geometry.centroid.y),
        }
    if geometry.geom_type == "Point":
        return {
            "area": 0.0,
            "perimeter": 0.0,
            "centroid_x": float(geometry.x),
            "centroid_y": float(geometry.y),
        }
    raise SketchHandoffInvalid(
        f"unsupported handoff geometry: {geometry.geom_type}"
    )


@dataclass(frozen=True)
class CoordinateHandoff:
    source_frame: str
    target_frame: str
    coordinate_state: str
    transform_kind: str
    homography_applied: bool
    shape_correction: str
    axis_orientation: str
    scale_px_per_m: float
    scale_range_px_per_m: tuple[float, float]
    scale_source: str
    origin_px: tuple[float, float]
    origin_source: str
    y_axis: str
    project_coordinates: bool
    calibration_ref: str
    review_state: str
    accuracy: str
    not_survey_grade: bool
    uncertainty_method: str

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
            transform_kind=str(data["transform_kind"]),
            homography_applied=bool(data["homography_applied"]),
            shape_correction=str(data["shape_correction"]),
            axis_orientation=str(data["axis_orientation"]),
            scale_px_per_m=scale,
            scale_range_px_per_m=(low, high),
            scale_source=str(data["scale_source"]),
            origin_px=(origin_x, origin_y),
            origin_source=str(data["origin_source"]),
            y_axis=str(data["y_axis"]),
            project_coordinates=bool(data["project_coordinates"]),
            calibration_ref=str(data["calibration_ref"]),
            review_state=str(data["review_state"]),
            accuracy=str(data["accuracy"]),
            not_survey_grade=bool(data["not_survey_grade"]),
            uncertainty_method=str(data["uncertainty_method"]),
        )
        handoff.validate()
        return handoff

    def validate(self) -> None:
        if self.source_frame != "image_space_unscaled":
            raise SketchHandoffInvalid(
                "source_frame must be image_space_unscaled"
            )
        if self.target_frame != "LOCAL-XY-ZUP":
            raise SketchHandoffInvalid(
                "target_frame must be LOCAL-XY-ZUP; the sketch does not "
                "establish east or north"
            )
        if self.coordinate_state != "local_metric_scaled":
            raise SketchHandoffInvalid(
                "coordinate_state must be local_metric_scaled"
            )
        if self.transform_kind not in TRANSFORM_KINDS:
            raise SketchHandoffInvalid(
                f"unknown transform kind: {self.transform_kind}"
            )
        if self.homography_applied:
            raise SketchHandoffInvalid(
                "the pilot transform is not a homography"
            )
        if self.shape_correction != "none":
            raise SketchHandoffInvalid(
                "the pilot transform corrects no local distortion"
            )
        if self.axis_orientation not in AXIS_ORIENTATIONS:
            raise SketchHandoffInvalid(
                f"unknown axis orientation: {self.axis_orientation}"
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
        if not self.scale_source:
            raise SketchHandoffInvalid("scale_source is required")
        if not all(isfinite(value) for value in self.origin_px):
            raise SketchHandoffInvalid("origin must be finite")
        if not self.origin_source:
            raise SketchHandoffInvalid("origin_source is required")
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
        if self.uncertainty_method != "scale_range_sensitivity":
            raise SketchHandoffInvalid(
                "uncertainty_method must be scale_range_sensitivity"
            )

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

    def transform_with_scale(
        self, payload: dict[str, Any], scale: float
    ) -> dict[str, Any]:
        geometry = _mapping(payload, "geometry")
        transformed = {
            "type": str(geometry["type"]),
            "coordinates": _transform_coordinates(
                geometry["coordinates"],
                scale,
                self.origin_px[0],
                self.origin_px[1],
            ),
        }
        return geometry_to_geojson(parse_geometry(transformed))

    def scale_sensitivity(self, payload: dict[str, Any]) -> dict[str, Any]:
        nominal = _geometry_metrics(
            parse_geometry(self.transform_geometry(payload))
        )
        low = _geometry_metrics(
            parse_geometry(
                self.transform_with_scale(payload, self.scale_range_px_per_m[0])
            )
        )
        high = _geometry_metrics(
            parse_geometry(
                self.transform_with_scale(payload, self.scale_range_px_per_m[1])
            )
        )
        areas = sorted([low["area"], nominal["area"], high["area"]])
        perimeters = sorted(
            [low["perimeter"], nominal["perimeter"], high["perimeter"]]
        )
        shift = max(
            math.hypot(
                low["centroid_x"] - nominal["centroid_x"],
                low["centroid_y"] - nominal["centroid_y"],
            ),
            math.hypot(
                high["centroid_x"] - nominal["centroid_x"],
                high["centroid_y"] - nominal["centroid_y"],
            ),
        )
        return {
            "nominal_scale_px_per_m": self.scale_px_per_m,
            "scale_range_px_per_m": list(self.scale_range_px_per_m),
            "area_m2": nominal["area"],
            "area_range_m2": [areas[0], areas[-1]],
            "perimeter_m": nominal["perimeter"],
            "perimeter_range_m": [perimeters[0], perimeters[-1]],
            "centroid_m": [nominal["centroid_x"], nominal["centroid_y"]],
            "centroid_shift_m": shift,
        }


@dataclass(frozen=True)
class HandoffReview:
    handoff_id: str
    review_kind: str
    object_geometry_review: bool
    reviewer: str
    reviewer_role: str
    review_scope: str
    human_confirmed_trace: bool
    basis: str
    decisions: dict[str, dict[str, Any]]
    reviewed_at: str | None = None
    evidence_refs: tuple[str, ...] = ()
    review_packet_sha256: str | None = None
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
                "evidence_ref": (
                    None
                    if record.get("evidence_ref") is None
                    else str(record["evidence_ref"])
                ),
            }
        review = cls(
            handoff_id=str(data["handoff_id"]),
            review_kind=str(data["review_kind"]),
            object_geometry_review=bool(data.get("object_geometry_review")),
            reviewer=str(data["reviewer"]),
            reviewer_role=str(data["reviewer_role"]),
            review_scope=str(data["review_scope"]),
            human_confirmed_trace=bool(data.get("human_confirmed_trace")),
            basis=str(data["basis"]),
            decisions=decisions,
            reviewed_at=(
                None
                if data.get("reviewed_at") is None
                else str(data["reviewed_at"])
            ),
            evidence_refs=tuple(
                str(item) for item in data.get("evidence_refs", [])
            ),
            review_packet_sha256=(
                None
                if data.get("review_packet_sha256") is None
                else str(data["review_packet_sha256"])
            ),
            limitations=tuple(str(item) for item in data.get("limitations", [])),
            non_claims=tuple(str(item) for item in data.get("non_claims", [])),
        )
        review.validate()
        return review

    def validate(self) -> None:
        if self.review_kind not in REVIEW_KINDS:
            raise SketchHandoffInvalid(
                f"unknown review kind: {self.review_kind}"
            )
        if self.reviewer_role not in REVIEWER_ROLES:
            raise SketchHandoffNotConfirmed(
                "handoff review must be by a designer or human reviewer",
                code="AGENT_CANNOT_CONFIRM_HANDOFF",
            )
        if not self.reviewer:
            raise SketchHandoffInvalid("reviewer is required")
        if self.review_scope not in REVIEW_SCOPES:
            raise SketchHandoffInvalid(f"unknown review scope: {self.review_scope}")
        if not self.basis:
            raise SketchHandoffInvalid("review basis is required")
        if not self.decisions:
            raise SketchHandoffInvalid("review decisions are required")

        if self.review_kind == "human_object_review":
            if not self.object_geometry_review:
                raise SketchHandoffNotConfirmed(
                    "human_object_review requires object_geometry_review: true",
                    code="OBJECT_GEOMETRY_REVIEW_REQUIRED",
                )
            if not self.human_confirmed_trace:
                raise SketchHandoffNotConfirmed(
                    "human_confirmed_trace must be true",
                    code="HUMAN_CONFIRMATION_REQUIRED",
                )
            if not self.reviewed_at:
                raise SketchHandoffInvalid(
                    "human_object_review requires reviewed_at"
                )
            if not self.evidence_refs:
                raise SketchHandoffInvalid(
                    "human_object_review requires evidence_refs"
                )
            _sha256_text(
                self.review_packet_sha256, "review_packet_sha256"
            )
            for source_id, decision in self.decisions.items():
                if decision["geometry"] not in CONFIRMED_GEOMETRY_STATES:
                    raise SketchHandoffNotConfirmed(
                        f"{source_id} has no confirmed geometry decision",
                        code="OBJECT_GEOMETRY_REVIEW_REQUIRED",
                    )
                if decision["coordinate"] == "not_reviewed":
                    raise SketchHandoffNotConfirmed(
                        f"{source_id} has no coordinate review decision",
                        code="COORDINATE_REVIEW_REQUIRED",
                    )
        elif self.review_kind == "designer_authorized_pilot":
            if self.object_geometry_review:
                raise SketchHandoffInvalid(
                    "designer_authorized_pilot cannot claim object_geometry_review"
                )
            if self.human_confirmed_trace:
                raise SketchHandoffInvalid(
                    "designer_authorized_pilot cannot claim human_confirmed_trace"
                )
            for source_id, decision in self.decisions.items():
                if decision["geometry"] != "not_reviewed":
                    raise SketchHandoffInvalid(
                        f"{source_id} claims geometry review inside an "
                        "authorization-only record"
                    )
                if decision["coordinate"] != "not_reviewed":
                    raise SketchHandoffInvalid(
                        f"{source_id} claims coordinate review inside an "
                        "authorization-only record"
                    )
        else:
            if not self.object_geometry_review:
                raise SketchHandoffNotConfirmed(
                    "test_double requires object_geometry_review: true",
                    code="OBJECT_GEOMETRY_REVIEW_REQUIRED",
                )
            if not self.human_confirmed_trace:
                raise SketchHandoffNotConfirmed(
                    "test_double requires a simulated human confirmation"
                )
            if not self.evidence_refs:
                raise SketchHandoffInvalid(
                    "test_double requires evidence_refs"
                )
            _sha256_text(
                self.review_packet_sha256, "review_packet_sha256"
            )

        for source_id, decision in self.decisions.items():
            if decision["semantic"] != "confirmed":
                raise SketchHandoffNotConfirmed(
                    f"{source_id} has no confirmed semantic decision"
                )
            if decision["coordinate"] not in COORDINATE_DECISIONS:
                raise SketchHandoffInvalid(
                    f"{source_id} has no valid coordinate decision"
                )

    def decision(self, source_id: str) -> dict[str, Any]:
        try:
            return self.decisions[source_id]
        except KeyError as exc:
            raise SketchHandoffNotConfirmed(
                f"no human review decision for {source_id}",
                code="MISSING_REVIEW_DECISION",
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
        for key in (
            "source_file",
            "source_object_id",
            "source_geometry_algorithm",
        ):
            if not provenance.get(key):
                raise SketchHandoffInvalid(
                    f"{data.get('source_id')} provenance needs {key}"
                )
        _sha256_text(
            provenance.get("source_file_sha256"),
            f"{data.get('source_id')} source_file_sha256",
        )
        _sha256_text(
            provenance.get("source_geometry_sha256"),
            f"{data.get('source_id')} source_geometry_sha256",
        )
        algorithm = str(provenance["source_geometry_algorithm"])
        if algorithm not in SOURCE_GEOMETRY_ALGORITHMS:
            raise SketchHandoffInvalid(
                f"unsupported source geometry algorithm: {algorithm}"
            )
        geometry_state = str(data["geometry_state"])
        if geometry_state not in OBJECT_GEOMETRY_STATES:
            raise SketchHandoffInvalid(
                f"{data.get('source_id')} has unknown geometry state: "
                f"{geometry_state}"
            )
        return cls(
            source_id=str(data["source_id"]),
            trace_id=str(data["trace_id"]),
            canonical_id=str(data["canonical_id"]),
            semantic_role=role,
            geometry=geometry,
            semantic_state=str(data["semantic_state"]),
            geometry_state=geometry_state,
            provenance=provenance,
            attributes=dict(data.get("attributes", {})),
        )


@dataclass(frozen=True)
class SketchHandoff:
    handoff_id: str
    case_id: str
    source_sketch_sha256: str
    source_files: tuple[dict[str, str], ...]
    synthetic_only: bool
    publication: dict[str, Any]
    coordinate: CoordinateHandoff
    review: HandoffReview
    site_boundary_authority: str
    objects: dict[str, HandoffObject]
    buildings: tuple[BuildingIntent, ...]
    roads: tuple[RoadCorridorIntent, ...]
    road_graph: RoadGraph
    road_topology_expected: dict[str, Any]
    source_edge_ids_by_corridor: dict[str, tuple[str, ...]]
    non_claims: tuple[str, ...]
    allow_test_double: bool = False

    @classmethod
    def from_dicts(
        cls,
        handoff_data: dict[str, Any],
        review_data: dict[str, Any],
        *,
        require_confirmation: bool = True,
        allow_test_double: bool = False,
        verify_sources: bool = False,
        root: str | Path | None = None,
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
        source_hash = _sha256_text(
            handoff_data.get("source_sketch_sha256"),
            "source_sketch_sha256",
        )

        source_files: list[dict[str, str]] = []
        seen_paths: set[str] = set()
        for item in _list(handoff_data.get("source_files", []), "source_files"):
            record = _mapping(item, "source file")
            path = str(record["path"])
            if path in seen_paths:
                raise SketchHandoffInvalid(f"duplicate source file: {path}")
            seen_paths.add(path)
            role = str(record["role"])
            if role not in {
                "sketch_raster",
                "trace_geojson",
                "road_network_geojson",
            }:
                raise SketchHandoffInvalid(f"unknown source file role: {role}")
            source_files.append(
                {
                    "path": path,
                    "sha256": _sha256_text(
                        record.get("sha256"), f"source file {path} sha256"
                    ),
                    "role": role,
                }
            )
        if not source_files:
            raise SketchHandoffInvalid("source_files must not be empty")

        publication = _mapping(
            handoff_data.get("publication", {}), "publication"
        )
        classification = str(publication.get("classification"))
        if classification not in PUBLICATION_CLASSIFICATIONS:
            raise SketchHandoffInvalid(
                f"unknown publication classification: {classification}"
            )
        if publication.get("authorized") is not True:
            raise SketchHandoffInvalid(
                "publication.authorized must be true for published evidence"
            )
        excluded = {
            str(item) for item in publication.get("excluded", [])
        }
        missing_excluded = sorted(REQUIRED_EXCLUDED_ASSETS - excluded)
        if missing_excluded:
            raise SketchHandoffInvalid(
                "publication.excluded is missing private assets: "
                f"{missing_excluded}"
            )

        coordinate = CoordinateHandoff.from_dict(
            handoff_data["coordinate_handoff"]
        )
        site_boundary_authority = str(
            handoff_data["site_boundary_authority"]
        )
        if site_boundary_authority not in SITE_BOUNDARY_AUTHORITIES:
            raise SketchHandoffInvalid(
                f"unknown site boundary authority: {site_boundary_authority}"
            )

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
            if obj.geometry_state not in OBJECT_GEOMETRY_STATES:
                raise SketchHandoffNotConfirmed(
                    f"{obj.source_id} geometry state is {obj.geometry_state}"
                )
            file_entry = next(
                (
                    entry
                    for entry in source_files
                    if entry["path"] == obj.provenance["source_file"]
                ),
                None,
            )
            if file_entry is None:
                raise SketchHandoffInvalid(
                    f"{obj.source_id} references an undeclared source file"
                )
            if (
                file_entry["sha256"]
                != obj.provenance["source_file_sha256"]
            ):
                raise SketchHandoffInvalid(
                    f"{obj.source_id} source_file_sha256 does not match "
                    "source_files"
                )
            decision = review.decision(obj.source_id)
            if review.review_kind == "designer_authorized_pilot":
                if obj.geometry_state not in {"proposed", "not_reviewed"}:
                    raise SketchHandoffNotConfirmed(
                        f"{obj.source_id} cannot claim "
                        f"{obj.geometry_state} inside an authorization-only "
                        "record",
                        code="AUTHORIZATION_CANNOT_CONFIRM_GEOMETRY",
                    )
                if decision["geometry"] != "not_reviewed":
                    raise SketchHandoffInvalid(
                        f"{obj.source_id} review decision claims geometry review"
                    )
            else:
                if obj.geometry_state not in CONFIRMED_GEOMETRY_STATES:
                    raise SketchHandoffNotConfirmed(
                        f"{obj.source_id} geometry state is {obj.geometry_state}",
                        code="OBJECT_GEOMETRY_REVIEW_REQUIRED",
                    )
                if decision["geometry"] != obj.geometry_state:
                    raise SketchHandoffNotConfirmed(
                        f"{obj.source_id} review/geometry state mismatch",
                        code="REVIEW_GEOMETRY_MISMATCH",
                    )
            if decision["coordinate"] not in COORDINATE_DECISIONS:
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
                "review decisions do not match objects; "
                f"missing={missing}, extra={extra}",
                code="REVIEW_DECISIONS_MISMATCH",
            )

        site_objects = [
            obj for obj in objects.values() if obj.semantic_role == "site_boundary"
        ]
        if len(site_objects) != 1:
            raise SketchHandoffInvalid(
                "exactly one site_boundary object is required"
            )
        site = site_objects[0]
        if site_boundary_authority == "published_sketch_boundary":
            if site.canonical_id != "SITE-SKETCH-001":
                raise SketchHandoffInvalid(
                    "a published sketch boundary must map to SITE-SKETCH-001",
                    code="SITE_BOUNDARY_AUTHORITY_MISMATCH",
                )
            if site.attributes.get("canonical_site_identity") is True:
                raise SketchHandoffInvalid(
                    "a published sketch boundary cannot claim canonical "
                    "site identity",
                    code="SITE_BOUNDARY_AUTHORITY_MISMATCH",
                )
        else:
            if site.canonical_id != "SITE-001":
                raise SketchHandoffInvalid(
                    "an authoritative boundary must map to SITE-001",
                    code="SITE_BOUNDARY_AUTHORITY_MISMATCH",
                )

        geometry_states = {obj.geometry_state for obj in objects.values()}
        if len(geometry_states) != 1:
            raise SketchHandoffNotConfirmed(
                "all objects in one handoff must share one geometry state",
                code="MIXED_GEOMETRY_STATES",
            )
        state = next(iter(geometry_states))
        if (
            review.review_kind == "designer_authorized_pilot"
            and require_confirmation
        ):
            raise SketchHandoffNotConfirmed(
                "the designer authorized a pilot but did not review object "
                "geometry; run the review packet first",
                code="HUMAN_OBJECT_REVIEW_REQUIRED",
            )
        if review.review_kind != "designer_authorized_pilot":
            if review.review_scope == "full_case" and state != "confirmed":
                raise SketchHandoffNotConfirmed(
                    "a full_case review rejects confirmed_for_pilot geometry",
                    code="FULL_CASE_REQUIRES_CONFIRMED_GEOMETRY",
                )
            if (
                review.review_scope == "pilot_subset"
                and state != "confirmed_for_pilot"
            ):
                raise SketchHandoffNotConfirmed(
                    "a pilot_subset review requires confirmed_for_pilot geometry",
                    code="PILOT_SCOPE_MISMATCH",
                )

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
            source_edge_ids = tuple(
                str(value)
                for value in item.get("source_edge_ids", [])
            )
            if set(source_edge_ids) != set(intent.edge_refs):
                raise SketchHandoffInvalid(
                    f"corridor {intent.corridor_id} source_edge_ids do not "
                    "match edge_refs",
                    code="ROAD_CORRIDOR_EDGE_MISMATCH",
                )
            source_edge_ids_by_corridor[intent.corridor_id] = source_edge_ids
            roads.append(intent)

        road_topology = _mapping(
            handoff_data.get("road_topology", {}), "road_topology"
        )
        for key in (
            "expected_component_count",
            "expected_node_count",
            "expected_edge_count",
            "expected_junction_node_ids",
            "expected_endpoint_node_ids",
            "endpoint_tolerance_px",
        ):
            if key not in road_topology:
                raise SketchHandoffInvalid(
                    f"road_topology requires {key}"
                )
        endpoint_tolerance = float(road_topology["endpoint_tolerance_px"])
        if not isfinite(endpoint_tolerance) or endpoint_tolerance <= 0:
            raise SketchHandoffInvalid(
                "road_topology.endpoint_tolerance_px must be positive"
            )
        road_topology_expected = {
            "expected_component_count": int(
                road_topology["expected_component_count"]
            ),
            "expected_node_count": int(road_topology["expected_node_count"]),
            "expected_edge_count": int(road_topology["expected_edge_count"]),
            "expected_junction_node_ids": tuple(
                str(item)
                for item in road_topology["expected_junction_node_ids"]
            ),
            "expected_endpoint_node_ids": tuple(
                str(item)
                for item in road_topology["expected_endpoint_node_ids"]
            ),
            "endpoint_tolerance_px": endpoint_tolerance,
        }

        if review.review_kind == "test_double" and not allow_test_double:
            raise SketchHandoffNotConfirmed(
                "test_double review is only accepted by an explicit test caller",
                code="TEST_DOUBLE_NOT_ALLOWED",
            )
        if review.review_kind != "designer_authorized_pilot" and review.review_scope == "full_case":
            if any(
                obj.geometry_state == "confirmed_for_pilot"
                for obj in objects.values()
            ):
                raise SketchHandoffNotConfirmed(
                    "a full_case review rejects confirmed_for_pilot geometry",
                    code="FULL_CASE_REQUIRES_CONFIRMED_GEOMETRY",
                )

        handoff = cls(
            handoff_id=handoff_id,
            case_id=str(handoff_data["case_id"]),
            source_sketch_sha256=source_hash,
            source_files=tuple(source_files),
            synthetic_only=False,
            publication=publication,
            coordinate=coordinate,
            review=review,
            site_boundary_authority=site_boundary_authority,
            objects=objects,
            buildings=tuple(buildings),
            roads=tuple(roads),
            road_graph=road_graph,
            road_topology_expected=road_topology_expected,
            source_edge_ids_by_corridor=source_edge_ids_by_corridor,
            non_claims=tuple(
                str(item) for item in handoff_data.get("non_claims", [])
            ),
            allow_test_double=allow_test_double,
        )
        handoff.validate_road_topology()
        if verify_sources:
            if root is None:
                raise SketchHandoffInvalid(
                    "root is required when verify_sources is true"
                )
            handoff.verify_sources(root)
        return handoff

    @classmethod
    def load(
        cls,
        handoff_path: str | Path,
        review_path: str | Path,
        *,
        require_confirmation: bool = True,
        allow_test_double: bool = False,
        verify_sources: bool = False,
        root: str | Path | None = None,
    ) -> "SketchHandoff":
        handoff_data = yaml.safe_load(
            Path(handoff_path).read_text(encoding="utf-8")
        )
        review_data = yaml.safe_load(
            Path(review_path).read_text(encoding="utf-8")
        )
        return cls.from_dicts(
            handoff_data,
            review_data,
            require_confirmation=require_confirmation,
            allow_test_double=allow_test_double,
            verify_sources=verify_sources,
            root=root,
        )

    def _trace_objects(self) -> dict[str, TraceObject]:
        trace_objects = {}
        for obj in self.objects.values():
            local_geometry = self.coordinate.transform_geometry(obj.geometry)
            trace_objects[obj.trace_id] = TraceObject(
                trace_id=obj.trace_id,
                semantic_role=obj.semantic_role,
                geometry=parse_geometry(local_geometry),
                review_state=obj.geometry_state,
                locked=True,
                source_refs=(obj.source_id,),
                confirmation_scope=self.review.review_scope,
                geometry_quality=obj.geometry_state,
                review_kind=self.review.review_kind,
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
        if self.review.review_kind == "designer_authorized_pilot":
            raise SketchHandoffNotConfirmed(
                "designer_authorized_pilot cannot enter ConfirmedTraceScene",
                code="HUMAN_OBJECT_REVIEW_REQUIRED",
            )
        if self.review.review_kind == "test_double" and not self.allow_test_double:
            raise SketchHandoffNotConfirmed(
                "test_double review is only accepted by an explicit test caller",
                code="TEST_DOUBLE_NOT_ALLOWED",
            )
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
            confirmation_scope=self.review.review_scope,
            review_kind=self.review.review_kind,
            geometry_quality=site.geometry_state,
            site_boundary_authority=self.site_boundary_authority,
            site_canonical_id=site.canonical_id,
            review_ref=f"{self.handoff_id}:review",
            review_packet_sha256=self.review.review_packet_sha256,
            source_handoff_id=self.handoff_id,
            test_only=self.review.review_kind == "test_double",
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
                    "review_state": obj.geometry_state,
                    "locked": True,
                    "source_refs": [obj.source_id],
                    "geometry": self.coordinate.transform_geometry(obj.geometry),
                    "confirmation_scope": self.review.review_scope,
                    "geometry_quality": obj.geometry_state,
                    "review_kind": self.review.review_kind,
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
            "site_canonical_id": site.canonical_id,
            "site_boundary_authority": self.site_boundary_authority,
            "confirmation_scope": self.review.review_scope,
            "review_kind": self.review.review_kind,
            "geometry_quality": site.geometry_state,
            "review_ref": f"{self.handoff_id}:review",
            "review_packet_sha256": self.review.review_packet_sha256,
            "source_handoff_id": self.handoff_id,
            "test_only": self.review.review_kind == "test_double",
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
                "source_files": [dict(item) for item in self.source_files],
                "site_boundary_authority": self.site_boundary_authority,
                "review_kind": self.review.review_kind,
                "object_geometry_review": self.review.object_geometry_review,
                "review_scope": self.review.review_scope,
                "reviewer_role": self.review.reviewer_role,
                "review_basis": self.review.basis,
                "review_packet_sha256": self.review.review_packet_sha256,
                "coordinate_handoff": {
                    "source_frame": self.coordinate.source_frame,
                    "target_frame": self.coordinate.target_frame,
                    "coordinate_state": self.coordinate.coordinate_state,
                    "transform_kind": self.coordinate.transform_kind,
                    "homography_applied": self.coordinate.homography_applied,
                    "shape_correction": self.coordinate.shape_correction,
                    "axis_orientation": self.coordinate.axis_orientation,
                    "scale_px_per_m": self.coordinate.scale_px_per_m,
                    "scale_range_px_per_m": list(
                        self.coordinate.scale_range_px_per_m
                    ),
                    "scale_source": self.coordinate.scale_source,
                    "origin_px": list(self.coordinate.origin_px),
                    "origin_source": self.coordinate.origin_source,
                    "y_axis": self.coordinate.y_axis,
                    "project_coordinates": self.coordinate.project_coordinates,
                    "calibration_ref": self.coordinate.calibration_ref,
                    "accuracy": self.coordinate.accuracy,
                    "not_survey_grade": self.coordinate.not_survey_grade,
                    "uncertainty_method": self.coordinate.uncertainty_method,
                },
                "mapping": self.mapping(),
                "source_edge_ids_by_corridor": {
                    key: list(value)
                    for key, value in self.source_edge_ids_by_corridor.items()
                },
                "road_topology": {
                    key: list(value) if isinstance(value, tuple) else value
                    for key, value in self.road_topology_expected.items()
                },
                "publication": dict(self.publication),
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
                "source_file": obj.provenance["source_file"],
                "source_object_id": obj.provenance["source_object_id"],
                "source_geometry_sha256": obj.provenance[
                    "source_geometry_sha256"
                ],
            }
            for obj in self.objects.values()
        ]

    def road_topology_report(self) -> dict[str, Any]:
        nodes = self.road_graph.nodes
        edges = self.road_graph.edges
        errors: list[dict[str, str]] = []
        tolerance = float(
            self.road_topology_expected["endpoint_tolerance_px"]
        )
        edge_offsets: list[dict[str, Any]] = []

        coords_seen: dict[tuple[float, float], str] = {}
        for node in nodes.values():
            key = (round(node.x, 6), round(node.y, 6))
            if key in coords_seen:
                errors.append(
                    {
                        "code": "ROAD_NODE_COORDINATES_DUPLICATE",
                        "message": (
                            f"{node.node_id} duplicates {coords_seen[key]}"
                        ),
                    }
                )
            coords_seen[key] = node.node_id

        degree: Counter[str] = Counter()
        adjacency: dict[str, set[str]] = defaultdict(set)
        for edge in edges.values():
            node_a = nodes.get(edge.node_a)
            node_b = nodes.get(edge.node_b)
            if node_a is None or node_b is None:
                errors.append(
                    {
                        "code": "ROAD_EDGE_NODE_MISSING",
                        "message": f"edge {edge.edge_id} references an unknown node",
                    }
                )
                continue
            coords = list(edge.centerline.coords)
            if len(coords) < 2:
                errors.append(
                    {
                        "code": "ROAD_EDGE_ENDPOINT_MISMATCH",
                        "message": f"edge {edge.edge_id} has too few vertices",
                    }
                )
                continue
            first = (float(coords[0][0]), float(coords[0][1]))
            last = (float(coords[-1][0]), float(coords[-1][1]))
            start_offset = math.hypot(
                first[0] - node_a.x, first[1] - node_a.y
            )
            end_offset = math.hypot(
                last[0] - node_b.x, last[1] - node_b.y
            )
            edge_offsets.append(
                {
                    "edge_id": edge.edge_id,
                    "start_node": node_a.node_id,
                    "end_node": node_b.node_id,
                    "start_offset_px": start_offset,
                    "end_offset_px": end_offset,
                }
            )
            if start_offset > tolerance:
                errors.append(
                    {
                        "code": "ROAD_EDGE_ENDPOINT_MISMATCH",
                        "message": (
                            f"edge {edge.edge_id} start is "
                            f"{start_offset:.3f} px from {node_a.node_id} "
                            f"(tolerance {tolerance})"
                        ),
                    }
                )
            if end_offset > tolerance:
                errors.append(
                    {
                        "code": "ROAD_EDGE_ENDPOINT_MISMATCH",
                        "message": (
                            f"edge {edge.edge_id} end is "
                            f"{end_offset:.3f} px from {node_b.node_id} "
                            f"(tolerance {tolerance})"
                        ),
                    }
                )
            degree[edge.node_a] += 1
            degree[edge.node_b] += 1
            adjacency[edge.node_a].add(edge.node_b)
            adjacency[edge.node_b].add(edge.node_a)

        isolated = sorted(
            node_id for node_id in nodes if degree[node_id] == 0
        )
        if isolated:
            errors.append(
                {
                    "code": "ROAD_GRAPH_DISCONNECTED",
                    "message": f"isolated nodes: {isolated}",
                }
            )

        junction_nodes = sorted(
            node_id for node_id in nodes if degree[node_id] >= 3
        )
        flagged_junctions = sorted(
            node_id for node_id in nodes if nodes[node_id].junction
        )
        if junction_nodes != flagged_junctions:
            errors.append(
                {
                    "code": "ROAD_JUNCTION_FLAG_MISMATCH",
                    "message": (
                        "junction flags do not match degree; "
                        f"degree={junction_nodes}, flagged={flagged_junctions}"
                    ),
                }
            )
        endpoint_nodes = sorted(
            node_id for node_id in nodes if degree[node_id] == 1
        )

        components = 0
        seen: set[str] = set()
        for start in nodes:
            if start in seen:
                continue
            components += 1
            stack = [start]
            seen.add(start)
            while stack:
                current = stack.pop()
                for neighbour in adjacency[current]:
                    if neighbour not in seen:
                        seen.add(neighbour)
                        stack.append(neighbour)

        for intent in self.roads:
            assigned = {
                edge.edge_id
                for edge in edges.values()
                if edge.corridor_id == intent.corridor_id
            }
            if set(intent.edge_refs) != assigned:
                errors.append(
                    {
                        "code": "ROAD_CORRIDOR_EDGE_MISMATCH",
                        "message": (
                            f"corridor {intent.corridor_id} edge_refs do not "
                            f"match its edges: {sorted(assigned)}"
                        ),
                    }
                )
            declared_sources = set(
                self.source_edge_ids_by_corridor.get(intent.corridor_id, ())
            )
            if declared_sources != set(intent.edge_refs):
                errors.append(
                    {
                        "code": "ROAD_CORRIDOR_EDGE_MISMATCH",
                        "message": (
                            f"corridor {intent.corridor_id} source_edge_ids "
                            "do not match edge_refs"
                        ),
                    }
                )

        expected = self.road_topology_expected
        checks = {
            "expected_component_count": components,
            "expected_node_count": len(nodes),
            "expected_edge_count": len(edges),
            "expected_junction_node_ids": tuple(junction_nodes),
            "expected_endpoint_node_ids": tuple(endpoint_nodes),
        }
        for key, actual in checks.items():
            if actual != expected[key]:
                errors.append(
                    {
                        "code": "ROAD_TOPOLOGY_EXPECTATION_MISMATCH",
                        "message": (
                            f"{key}: expected {expected[key]}, got {actual}"
                        ),
                    }
                )

        return {
            "ok": not errors,
            "errors": errors,
            "component_count": components,
            "node_count": len(nodes),
            "edge_count": len(edges),
            "junction_node_ids": junction_nodes,
            "endpoint_node_ids": endpoint_nodes,
            "endpoint_tolerance_px": tolerance,
            "max_endpoint_offset_px": max(
                (
                    max(
                        item["start_offset_px"],
                        item["end_offset_px"],
                    )
                    for item in edge_offsets
                ),
                default=0.0,
            ),
            "edge_offsets": edge_offsets,
            "degrees": {
                node_id: degree[node_id] for node_id in sorted(nodes)
            },
            "corridors": {
                intent.corridor_id: list(intent.edge_refs)
                for intent in self.roads
            },
            "expected": expected,
        }

    def validate_road_topology(self) -> None:
        report = self.road_topology_report()
        if report["ok"]:
            return
        first = report["errors"][0]
        raise SketchHandoffInvalid(
            "; ".join(error["message"] for error in report["errors"]),
            code=first["code"],
        )

    def source_integrity_report(self, root: str | Path) -> dict[str, Any]:
        root = Path(root)
        errors: list[dict[str, str]] = []
        file_reports: list[dict[str, Any]] = []
        loaded: dict[str, Any] = {}
        file_by_path = {entry["path"]: entry for entry in self.source_files}

        for entry in self.source_files:
            path = root / entry["path"]
            report: dict[str, Any] = {
                "path": entry["path"],
                "role": entry["role"],
                "declared_sha256": entry["sha256"],
                "exists": path.is_file(),
            }
            if not path.is_file():
                errors.append(
                    {
                        "code": "SOURCE_FILE_MISSING",
                        "message": f"source file missing: {entry['path']}",
                    }
                )
                file_reports.append(report)
                continue
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            report["actual_sha256"] = actual
            report["hash_matches"] = actual == entry["sha256"]
            if actual != entry["sha256"]:
                errors.append(
                    {
                        "code": "SOURCE_FILE_HASH_MISMATCH",
                        "message": (
                            f"source file hash changed: {entry['path']}"
                        ),
                    }
                )
            if entry["role"] in {"trace_geojson", "road_network_geojson"}:
                try:
                    loaded[entry["path"]] = _load_json_source(path)
                except (json.JSONDecodeError, UnicodeDecodeError) as exc:
                    errors.append(
                        {
                            "code": "SOURCE_FILE_UNREADABLE",
                            "message": f"source file unreadable: {entry['path']}: {exc}",
                        }
                    )
            file_reports.append(report)

        sketch_entries = [
            entry
            for entry in self.source_files
            if entry["role"] == "sketch_raster"
        ]
        if not sketch_entries:
            errors.append(
                {
                    "code": "SOURCE_FILE_MISSING",
                    "message": "no sketch_raster source file declared",
                }
            )
        else:
            sketch_entry = sketch_entries[0]
            if sketch_entry["sha256"] != self.source_sketch_sha256:
                errors.append(
                    {
                        "code": "SOURCE_SKETCH_HASH_MISMATCH",
                        "message": (
                            "source_sketch_sha256 does not match the declared "
                            "sketch raster hash"
                        ),
                    }
                )

        object_reports: list[dict[str, Any]] = []
        for obj in self.objects.values():
            provenance = obj.provenance
            entry = file_by_path.get(provenance["source_file"])
            report = {
                "source_id": obj.source_id,
                "source_file": provenance["source_file"],
                "source_object_id": provenance["source_object_id"],
                "declared_geometry_sha256": provenance[
                    "source_geometry_sha256"
                ],
            }
            data = loaded.get(provenance["source_file"])
            if entry is None or data is None:
                errors.append(
                    {
                        "code": "SOURCE_OBJECT_UNVERIFIABLE",
                        "message": (
                            f"{obj.source_id} source file is not a readable "
                            "GeoJSON source"
                        ),
                    }
                )
                object_reports.append(report)
                continue
            feature = _find_geojson_feature(
                data, provenance["source_object_id"]
            )
            if feature is None:
                errors.append(
                    {
                        "code": "SOURCE_OBJECT_MISSING",
                        "message": (
                            f"{obj.source_id} source object "
                            f"{provenance['source_object_id']} is missing"
                        ),
                    }
                )
                object_reports.append(report)
                continue
            actual_hash = geometry_sha256(feature["geometry"])
            report["actual_geometry_sha256"] = actual_hash
            report["geometry_hash_matches"] = (
                actual_hash == provenance["source_geometry_sha256"]
            )
            report["handoff_geometry_matches"] = (
                geometry_sha256(obj.geometry) == actual_hash
            )
            if not report["geometry_hash_matches"]:
                errors.append(
                    {
                        "code": "SOURCE_OBJECT_HASH_MISMATCH",
                        "message": (
                            f"{obj.source_id} source geometry hash changed"
                        ),
                    }
                )
            if not report["handoff_geometry_matches"]:
                errors.append(
                    {
                        "code": "HANDOFF_GEOMETRY_MISMATCH",
                        "message": (
                            f"{obj.source_id} handoff geometry does not equal "
                            "the source object geometry"
                        ),
                    }
                )
            object_reports.append(report)

        return {
            "ok": not errors,
            "errors": errors,
            "source_sketch_sha256": self.source_sketch_sha256,
            "files": file_reports,
            "objects": object_reports,
        }

    def verify_sources(self, root: str | Path) -> None:
        report = self.source_integrity_report(root)
        if report["ok"]:
            return
        first = report["errors"][0]
        raise SketchHandoffInvalid(
            "; ".join(error["message"] for error in report["errors"]),
            code=first["code"],
        )

    def coordinate_sensitivity_report(self) -> list[dict[str, Any]]:
        return [
            {
                "source_id": obj.source_id,
                "semantic_role": obj.semantic_role,
                **self.coordinate.scale_sensitivity(obj.geometry),
            }
            for obj in self.objects.values()
        ]

    def write_domain_fixture(self, path: str | Path) -> None:
        Path(path).write_text(
            yaml.safe_dump(self.to_domain_fixture(), sort_keys=False),
            encoding="utf-8",
        )

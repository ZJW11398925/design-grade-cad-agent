from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from dgcad_foundation import DerivedArtifact, World

from .common import (
    GeometryDiff,
    ParameterValue,
    axis_aligned_envelope,
    geometry_diff,
    geometry_to_geojson,
    polygon_from_geojson,
)

if TYPE_CHECKING:
    from .trace import ConfirmedTraceScene


REGULARIZATION_REQUESTS = frozenset({"preserve_trace", "regularize_axis_aligned"})
TYPOLOGY_STATES = frozenset({"unknown", "proposed", "confirmed", "disputed"})
REGULARIZATION_STATES = frozenset(
    {"not_run", "preserve_trace", "regularized_candidate", "needs_review", "confirmed"}
)


@dataclass(frozen=True)
class BuildingIntent:
    object_id: str
    trace_ref: str
    height: ParameterValue
    base_elevation: ParameterValue
    typology: str | None
    typology_state: str
    regularization_request: str

    def __post_init__(self) -> None:
        if self.regularization_request not in REGULARIZATION_REQUESTS:
            raise ValueError(
                f"unknown regularization request: {self.regularization_request}"
            )
        if self.typology_state not in TYPOLOGY_STATES:
            raise ValueError(f"unknown typology state: {self.typology_state}")

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "BuildingIntent":
        return cls(
            object_id=str(data["object_id"]),
            trace_ref=str(data["trace_ref"]),
            height=ParameterValue.from_dict(data.get("height")),
            base_elevation=ParameterValue.from_dict(data.get("base_elevation")),
            typology=data.get("typology"),
            typology_state=str(data.get("typology_state", "unknown")),
            regularization_request=str(
                data.get("regularization_request", "preserve_trace")
            ),
        )


@dataclass(frozen=True)
class BuildingCandidate:
    object_id: str
    trace_ref: str
    trace_footprint: Any
    professional_footprint: Any
    regularization_state: str
    diff: GeometryDiff | None
    height: ParameterValue
    base_elevation: ParameterValue
    typology: str | None
    typology_state: str

    def __post_init__(self) -> None:
        if self.regularization_state not in REGULARIZATION_STATES:
            raise ValueError(
                f"unknown regularization state: {self.regularization_state}"
            )

    def to_changes(self) -> dict[str, Any]:
        return {
            "professional_footprint": geometry_to_geojson(
                self.professional_footprint
            ),
            "regularization_state": self.regularization_state,
            "regularization_diff": (
                None if self.diff is None else self.diff.to_dict()
            ),
            "height": self.height.to_dict(),
            "base_elevation": self.base_elevation.to_dict(),
            "typology": self.typology,
            "typology_state": self.typology_state,
        }


class MassingBlocked(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


def building_candidate(
    trace_scene: "ConfirmedTraceScene",
    intent: BuildingIntent,
    *,
    regularize: bool = False,
) -> BuildingCandidate:
    trace = trace_scene.trace(intent.trace_ref)
    if trace.semantic_role != "building":
        raise ValueError(
            f"{intent.trace_ref} is not a building trace object"
        )

    source = trace.geometry
    if not source.is_valid or source.is_empty:
        raise ValueError("INVALID_FOOTPRINT: trace geometry is invalid")

    regularize_requested = regularize or (
        intent.regularization_request == "regularize_axis_aligned"
    )
    if regularize_requested:
        professional = axis_aligned_envelope(source)
        diff = geometry_diff(source, professional)
        state = "regularized_candidate"
    else:
        professional = source
        diff = None
        state = "preserve_trace"

    if not professional.is_valid or professional.is_empty:
        raise ValueError("INVALID_FOOTPRINT: professional geometry is invalid")

    return BuildingCandidate(
        object_id=intent.object_id,
        trace_ref=intent.trace_ref,
        trace_footprint=source,
        professional_footprint=professional,
        regularization_state=state,
        diff=diff,
        height=intent.height,
        base_elevation=intent.base_elevation,
        typology=intent.typology,
        typology_state=intent.typology_state,
    )


def building_massing(scene, building_id: str) -> DerivedArtifact:
    obj = scene.objects.get(building_id)
    if obj is None:
        raise MassingBlocked("BUILDING_NOT_FOUND", building_id)
    height = ParameterValue.from_dict(obj.values.get("height"))
    if height.state != "confirmed":
        raise MassingBlocked(
            "MASSING_BLOCKED_UNKNOWN_HEIGHT",
            f"{building_id} height state is {height.state}",
        )
    footprint_payload = obj.values.get("professional_footprint")
    if footprint_payload is None:
        raise MassingBlocked(
            "MASSING_BLOCKED_MISSING_FOOTPRINT",
            f"{building_id} has no professional footprint",
        )
    try:
        footprint = polygon_from_geojson(footprint_payload)
    except ValueError as exc:
        raise MassingBlocked(
            "MASSING_BLOCKED_INVALID_FOOTPRINT",
            f"{building_id} footprint is invalid: {exc}",
        ) from exc
    if not footprint.is_valid:
        raise MassingBlocked(
            "MASSING_BLOCKED_INVALID_FOOTPRINT",
            f"{building_id} footprint is not a valid polygon",
        )
    return DerivedArtifact(
        artifact_id=f"MASS-{building_id}",
        artifact_type="massing",
        world=World.CANONICAL_CURRENT,
        dependency_keys=frozenset(
            {f"{building_id}.geometry", f"{building_id}.parameter"}
        ),
    )

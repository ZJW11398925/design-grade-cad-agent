from __future__ import annotations

from dataclasses import dataclass
from math import atan2, degrees, hypot, isfinite
from typing import Any

from shapely.geometry import box, mapping, shape
from shapely.geometry.base import BaseGeometry


PARAMETER_STATES = frozenset({"unknown", "estimated", "proposed", "confirmed"})


def finite_number(value: Any, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a finite number, got {type(value).__name__}")
    number = float(value)
    if not isfinite(number):
        raise ValueError(f"{name} must be finite")
    return number


@dataclass(frozen=True)
class ParameterValue:
    value: float | None
    unit: str
    state: str
    source_ref: str | None = None

    def __post_init__(self) -> None:
        if self.state not in PARAMETER_STATES:
            raise ValueError(f"invalid parameter state: {self.state}")
        if self.state == "unknown":
            if self.value is not None:
                raise ValueError("unknown parameter must not carry a numeric value")
            return
        if self.value is None:
            raise ValueError(f"{self.state} parameter requires a numeric value")
        finite_number(self.value, "parameter value")

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> "ParameterValue":
        if not isinstance(data, dict):
            raise ValueError("parameter payload must be a mapping")
        return cls(
            value=data.get("value"),
            unit=str(data.get("unit", "metre")),
            state=str(data.get("state", "unknown")),
            source_ref=data.get("source_ref"),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "value": self.value,
            "unit": self.unit,
            "state": self.state,
            "source_ref": self.source_ref,
        }


@dataclass(frozen=True)
class DomainIssue:
    code: str
    severity: str
    object_id: str | None
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "object_id": self.object_id,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class DomainValidationResult:
    validator_id: str
    validator_version: str
    scope: str
    verdict: str
    issues: tuple[DomainIssue, ...] = ()
    coverage_limits: tuple[str, ...] = ()

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)

    def has_code(self, code: str) -> bool:
        return code in self.codes

    def to_dict(self) -> dict[str, Any]:
        return {
            "validator_id": self.validator_id,
            "validator_version": self.validator_version,
            "scope": self.scope,
            "verdict": self.verdict,
            "issues": [issue.to_dict() for issue in self.issues],
            "coverage_limits": list(self.coverage_limits),
        }


@dataclass(frozen=True)
class GeometryDiff:
    area_change_ratio: float
    hausdorff_distance_m: float
    centroid_shift_m: float
    orientation_change_deg: float
    iou: float

    def to_dict(self) -> dict[str, float]:
        return {
            "area_change_ratio": self.area_change_ratio,
            "hausdorff_distance_m": self.hausdorff_distance_m,
            "centroid_shift_m": self.centroid_shift_m,
            "orientation_change_deg": self.orientation_change_deg,
            "iou": self.iou,
        }


def _to_lists(value: Any) -> Any:
    if isinstance(value, tuple):
        return [_to_lists(item) for item in value]
    if isinstance(value, list):
        return [_to_lists(item) for item in value]
    if isinstance(value, dict):
        return {key: _to_lists(item) for key, item in value.items()}
    return value


def parse_geometry(payload: dict[str, Any]) -> BaseGeometry:
    if not isinstance(payload, dict) or "type" not in payload:
        raise ValueError("geometry payload must be a GeoJSON mapping")
    try:
        geometry = shape(payload)
    except Exception as exc:  # noqa: BLE001 - normalize shapely parse errors
        raise ValueError(f"invalid GeoJSON geometry: {exc}") from exc
    if geometry.is_empty:
        raise ValueError("geometry must not be empty")
    return geometry


def polygon_from_geojson(payload: dict[str, Any]) -> BaseGeometry:
    geometry = parse_geometry(payload)
    if geometry.geom_type not in {"Polygon", "MultiPolygon"}:
        raise ValueError(f"expected polygon geometry, got {geometry.geom_type}")
    return geometry


def geometry_to_geojson(geometry: BaseGeometry) -> dict[str, Any]:
    return _to_lists(mapping(geometry))


def axis_aligned_envelope(polygon: BaseGeometry) -> BaseGeometry:
    min_x, min_y, max_x, max_y = polygon.bounds
    return box(min_x, min_y, max_x, max_y)


def dominant_orientation_deg(polygon: BaseGeometry) -> float:
    rectangle = polygon.minimum_rotated_rectangle
    coords = list(rectangle.exterior.coords)[:-1]
    if len(coords) < 2:
        raise ValueError("cannot determine orientation of degenerate geometry")
    edges = [
        (coords[index], coords[(index + 1) % len(coords)])
        for index in range(len(coords))
    ]
    first, second = max(
        edges,
        key=lambda edge: hypot(
            edge[1][0] - edge[0][0], edge[1][1] - edge[0][1]
        ),
    )
    angle = degrees(atan2(second[1] - first[1], second[0] - first[0])) % 180.0
    if angle >= 90.0:
        angle -= 90.0
    return angle


def _orientation_change(first: BaseGeometry, second: BaseGeometry) -> float:
    a = dominant_orientation_deg(first)
    b = dominant_orientation_deg(second)
    delta = abs(a - b)
    return min(delta, 90.0 - delta)


def geometry_diff(source: BaseGeometry, candidate: BaseGeometry) -> GeometryDiff:
    if not source.is_valid or source.is_empty:
        raise ValueError("source geometry is invalid")
    if not candidate.is_valid or candidate.is_empty:
        raise ValueError("candidate geometry is invalid")
    union = source.union(candidate)
    intersection = source.intersection(candidate)
    iou = 0.0 if union.area == 0 else intersection.area / union.area
    area_change_ratio = (
        0.0 if source.area == 0 else abs(candidate.area - source.area) / source.area
    )
    return GeometryDiff(
        area_change_ratio=area_change_ratio,
        hausdorff_distance_m=float(source.hausdorff_distance(candidate)),
        centroid_shift_m=float(source.centroid.distance(candidate.centroid)),
        orientation_change_deg=_orientation_change(source, candidate),
        iou=iou,
    )

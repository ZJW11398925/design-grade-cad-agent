from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import acos, atan2, cos, degrees, hypot, isfinite, pi, radians, sin, tan
from typing import Any

from shapely.geometry import LineString, Point
from shapely.geometry.base import BaseGeometry

from dgcad_domain import ParameterValue, geometry_to_geojson, polygon_from_geojson
from dgcad_foundation import canonical_hash


METHOD_ID = "dgcad.analysis.shadow.raycast.v0.1"
METHOD_VERSION = "0.1"
COVERAGE_LIMITS = (
    "synthetic flat-ground fixture only",
    "vertical prism blockers with constant footprint",
    "no terrain, reflection, refraction or weather weighting",
    "not a legal daylight or standards conclusion",
)


@dataclass(frozen=True)
class SolarPosition:
    elevation_deg: float
    azimuth_deg: float

    def to_dict(self) -> dict[str, float]:
        return {
            "elevation_deg": self.elevation_deg,
            "azimuth_deg": self.azimuth_deg,
        }


@dataclass(frozen=True)
class ShadowBlocker:
    object_id: str
    footprint: BaseGeometry
    base_elevation_m: float
    height_m: float | None
    height_state: str
    geometry_revision: int
    parameter_revision: int

    def __post_init__(self) -> None:
        if self.height_state not in {"unknown", "estimated", "confirmed"}:
            raise ValueError(f"unknown height state: {self.height_state}")
        if not isfinite(self.base_elevation_m):
            raise ValueError("base elevation must be finite")
        if self.height_state == "unknown":
            if self.height_m is not None:
                raise ValueError("unknown blocker height must be null")
            return
        if self.height_m is None or not isfinite(self.height_m) or self.height_m <= 0:
            raise ValueError("known blocker height must be positive and finite")


@dataclass(frozen=True)
class ShadowSample:
    sample_id: str
    x: float
    y: float

    def __post_init__(self) -> None:
        if not isfinite(self.x) or not isfinite(self.y):
            raise ValueError("sample coordinates must be finite")


@dataclass(frozen=True)
class ShadowSampleResult:
    sample_id: str
    x: float
    y: float
    status: str
    blocker_ids: tuple[str, ...]
    message: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "sample_id": self.sample_id,
            "x": self.x,
            "y": self.y,
            "status": self.status,
            "blocker_ids": list(self.blocker_ids),
            "message": self.message,
        }


@dataclass(frozen=True)
class ShadowConfig:
    latitude_deg: float
    longitude_deg: float
    local_datetime: datetime
    north_bearing_deg: float
    sensor_height_m: float
    context_complete: bool
    samples: tuple[ShadowSample, ...]

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ShadowConfig":
        if data.get("local_datetime") is None:
            raise ValueError("analysis.local_datetime is required")
        local_datetime = datetime.fromisoformat(str(data["local_datetime"]))
        return cls(
            latitude_deg=float(data["latitude_deg"]),
            longitude_deg=float(data["longitude_deg"]),
            local_datetime=local_datetime,
            north_bearing_deg=float(
                data["project_y_axis_true_north_bearing_deg"]
            ),
            sensor_height_m=float(data.get("sensor_height_m", 1.5)),
            context_complete=bool(data.get("context_complete", True)),
            samples=tuple(
                ShadowSample(
                    sample_id=str(item["sample_id"]),
                    x=float(item["x"]),
                    y=float(item["y"]),
                )
                for item in data.get("sample_points", [])
            ),
        )

    def __post_init__(self) -> None:
        if self.local_datetime.tzinfo is None:
            raise ValueError("local_datetime must be timezone-aware")
        if not -90.0 <= self.latitude_deg <= 90.0:
            raise ValueError("latitude out of range")
        if not -180.0 <= self.longitude_deg <= 180.0:
            raise ValueError("longitude out of range")
        if not isfinite(self.north_bearing_deg):
            raise ValueError("north bearing must be finite")
        if not isfinite(self.sensor_height_m) or self.sensor_height_m < 0:
            raise ValueError("sensor height must be finite and non-negative")
        if not self.samples:
            raise ValueError("at least one sample point is required")


@dataclass(frozen=True)
class ShadowAnalysisResult:
    analysis_id: str
    status: str
    solar_position: SolarPosition
    samples: tuple[ShadowSampleResult, ...]
    dependency_fingerprint: str
    method_id: str = METHOD_ID
    method_version: str = METHOD_VERSION
    coverage_limits: tuple[str, ...] = COVERAGE_LIMITS

    def to_dict(self) -> dict[str, Any]:
        return {
            "analysis_id": self.analysis_id,
            "status": self.status,
            "method_id": self.method_id,
            "method_version": self.method_version,
            "solar_position": self.solar_position.to_dict(),
            "samples": [sample.to_dict() for sample in self.samples],
            "dependency_fingerprint": self.dependency_fingerprint,
            "coverage_limits": list(self.coverage_limits),
        }


def solar_position_noaa(
    latitude_deg: float, longitude_deg: float, local_datetime: datetime
) -> SolarPosition:
    if local_datetime.tzinfo is None:
        raise ValueError("timezone-aware datetime required")
    if not -90.0 <= latitude_deg <= 90.0:
        raise ValueError("latitude out of range")
    if not -180.0 <= longitude_deg <= 180.0:
        raise ValueError("longitude out of range")

    latitude = radians(latitude_deg)
    day_of_year = local_datetime.timetuple().tm_yday
    hour = (
        local_datetime.hour
        + local_datetime.minute / 60.0
        + local_datetime.second / 3600.0
    )
    timezone_hours = local_datetime.utcoffset().total_seconds() / 3600.0
    gamma = 2.0 * pi / 365.0 * (day_of_year - 1 + (hour - 12.0) / 24.0)

    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * cos(gamma)
        - 0.032077 * sin(gamma)
        - 0.014615 * cos(2 * gamma)
        - 0.040849 * sin(2 * gamma)
    )
    declination = (
        0.006918
        - 0.399912 * cos(gamma)
        + 0.070257 * sin(gamma)
        - 0.006758 * cos(2 * gamma)
        + 0.000907 * sin(2 * gamma)
        - 0.002697 * cos(3 * gamma)
        + 0.001480 * sin(3 * gamma)
    )
    time_offset = equation_of_time + 4.0 * longitude_deg - 60.0 * timezone_hours
    true_solar_minutes = (hour * 60.0 + time_offset) % 1440.0
    hour_angle = radians(true_solar_minutes / 4.0 - 180.0)

    cos_zenith = sin(latitude) * sin(declination) + cos(latitude) * cos(
        declination
    ) * cos(hour_angle)
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    elevation = 90.0 - degrees(acos(cos_zenith))
    azimuth = (
        degrees(
            atan2(
                sin(hour_angle),
                cos(hour_angle) * sin(latitude)
                - tan(declination) * cos(latitude),
            )
        )
        + 180.0
    ) % 360.0
    return SolarPosition(elevation_deg=elevation, azimuth_deg=azimuth)


def sun_vector_project(
    azimuth_deg: float,
    elevation_deg: float,
    north_bearing_deg: float,
) -> tuple[float, float, float]:
    if not isfinite(north_bearing_deg):
        raise ValueError("project north bearing is required")
    local_azimuth = radians(azimuth_deg - north_bearing_deg)
    elevation = radians(elevation_deg)
    x = sin(local_azimuth) * cos(elevation)
    y = cos(local_azimuth) * cos(elevation)
    z = sin(elevation)
    norm = (x * x + y * y + z * z) ** 0.5
    if norm == 0.0:
        raise ValueError("invalid solar vector")
    return (x / norm, y / norm, z / norm)


def _ray_intersections(
    origin: tuple[float, float],
    direction: tuple[float, float],
    footprint: BaseGeometry,
    max_distance_m: float,
) -> list[float]:
    end = (
        origin[0] + direction[0] * max_distance_m,
        origin[1] + direction[1] * max_distance_m,
    )
    segment = LineString([origin, end])
    intersection = segment.intersection(footprint)
    if intersection.is_empty:
        return []
    points: list[Point] = []
    if intersection.geom_type == "Point":
        points = [intersection]
    elif intersection.geom_type in {"LineString", "LinearRing"}:
        points = [Point(intersection.coords[0]), Point(intersection.coords[-1])]
    elif intersection.geom_type == "MultiLineString":
        for line in intersection.geoms:
            points.append(Point(line.coords[0]))
            points.append(Point(line.coords[-1]))
    elif intersection.geom_type == "GeometryCollection":
        for item in intersection.geoms:
            if item.geom_type == "Point":
                points.append(item)
            elif item.geom_type in {"LineString", "LinearRing"}:
                points.append(Point(item.coords[0]))
                points.append(Point(item.coords[-1]))
    distances = []
    for point in points:
        distance = hypot(point.x - origin[0], point.y - origin[1])
        if distance > 0:
            distances.append(distance)
    return sorted(set(distances))


def _ray_hits_footprint(
    origin: tuple[float, float],
    direction: tuple[float, float],
    footprint: BaseGeometry,
    max_distance_m: float,
) -> bool:
    if footprint.is_empty:
        return False
    return bool(_ray_intersections(origin, direction, footprint, max_distance_m))


def evaluate_sample(
    sample: ShadowSample,
    blockers: tuple[ShadowBlocker, ...],
    sun_vector: tuple[float, float, float],
    *,
    sensor_height_m: float,
    context_complete: bool,
    max_distance_m: float = 200.0,
) -> ShadowSampleResult:
    sx, sy, sz = sun_vector
    if sz <= 0.0:
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "night_or_sun_below_horizon",
            (),
            "sun is at or below the horizon",
        )

    horizontal = hypot(sx, sy)
    if horizontal < 1e-12:
        if not context_complete:
            return ShadowSampleResult(
                sample.sample_id,
                sample.x,
                sample.y,
                "incomplete_surrounding_context",
                (),
                "sun at zenith with incomplete surrounding context",
            )
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "confirmed_sunlit_given_declared_context",
            (),
            "sun at zenith; no horizontal shadow",
        )

    direction = (sx / horizontal, sy / horizontal)
    origin = (sample.x, sample.y)
    shaded: list[str] = []
    unknown: list[str] = []
    estimated: list[str] = []

    for blocker in blockers:
        if blocker.height_state == "unknown":
            if _ray_hits_footprint(origin, direction, blocker.footprint, max_distance_m):
                unknown.append(blocker.object_id)
            continue
        if blocker.height_state == "estimated":
            if _ray_hits_footprint(origin, direction, blocker.footprint, max_distance_m):
                estimated.append(blocker.object_id)
            continue

        distances = _ray_intersections(
            origin, direction, blocker.footprint, max_distance_m
        )
        if not distances:
            continue
        base = blocker.base_elevation_m
        top = base + (blocker.height_m or 0.0)
        heights = [
            sensor_height_m + distance * (sz / horizontal)
            for distance in distances
        ]
        if max(heights) >= base and min(heights) <= top:
            shaded.append(blocker.object_id)

    if shaded:
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "confirmed_shaded",
            tuple(sorted(shaded)),
            "ray intersects a confirmed vertical prism",
        )
    if unknown:
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "unknown_obstruction_height",
            tuple(sorted(unknown)),
            "ray intersects a blocker with unknown height",
        )
    if estimated:
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "estimated_height_affects_result",
            tuple(sorted(estimated)),
            "ray intersects a blocker with estimated height",
        )
    if not context_complete:
        return ShadowSampleResult(
            sample.sample_id,
            sample.x,
            sample.y,
            "incomplete_surrounding_context",
            (),
            "surrounding context is declared incomplete",
        )
    return ShadowSampleResult(
        sample.sample_id,
        sample.x,
        sample.y,
        "confirmed_sunlit_given_declared_context",
        (),
        "no blocker intersects the solar ray",
    )


def blockers_from_scene(scene) -> tuple[ShadowBlocker, ...]:
    blockers: list[ShadowBlocker] = []
    for obj in scene.objects.values():
        if obj.object_class != "building":
            continue
        footprint_payload = obj.values.get("professional_footprint")
        if footprint_payload is None:
            continue
        height = ParameterValue.from_dict(obj.values.get("height"))
        base = ParameterValue.from_dict(obj.values.get("base_elevation"))
        if base.state != "confirmed":
            raise ValueError(
                f"BASE_ELEVATION_UNCONFIRMED: {obj.object_id} base is {base.state}"
            )
        blockers.append(
            ShadowBlocker(
                object_id=obj.object_id,
                footprint=polygon_from_geojson(footprint_payload),
                base_elevation_m=base.value,
                height_m=height.value,
                height_state=height.state,
                geometry_revision=obj.revisions.geometry,
                parameter_revision=obj.revisions.parameter,
            )
        )
    return tuple(sorted(blockers, key=lambda blocker: blocker.object_id))


def run_shadow_baseline(
    scene, config: ShadowConfig, *, analysis_id: str = "SHADOW-E2E-001"
) -> ShadowAnalysisResult:
    position = solar_position_noaa(
        config.latitude_deg, config.longitude_deg, config.local_datetime
    )
    vector = sun_vector_project(
        position.azimuth_deg, position.elevation_deg, config.north_bearing_deg
    )
    blockers = blockers_from_scene(scene)
    results = tuple(
        evaluate_sample(
            sample,
            blockers,
            vector,
            sensor_height_m=config.sensor_height_m,
            context_complete=config.context_complete,
        )
        for sample in config.samples
    )
    statuses = {sample.status for sample in results}
    if statuses & {
        "unknown_obstruction_height",
        "estimated_height_affects_result",
        "incomplete_surrounding_context",
        "night_or_sun_below_horizon",
    }:
        status = "bounded_or_unknown"
    else:
        status = "confirmed_for_declared_context"

    payload = {
        "analysis_id": analysis_id,
        "method_id": METHOD_ID,
        "method_version": METHOD_VERSION,
        "latitude_deg": config.latitude_deg,
        "longitude_deg": config.longitude_deg,
        "local_datetime": config.local_datetime.isoformat(),
        "north_bearing_deg": config.north_bearing_deg,
        "sensor_height_m": config.sensor_height_m,
        "context_complete": config.context_complete,
        "samples": [
            {"sample_id": sample.sample_id, "x": sample.x, "y": sample.y}
            for sample in config.samples
        ],
        "blockers": [
            {
                "object_id": blocker.object_id,
                "geometry_revision": blocker.geometry_revision,
                "parameter_revision": blocker.parameter_revision,
                "footprint": geometry_to_geojson(blocker.footprint),
                "base_elevation_m": blocker.base_elevation_m,
                "height_m": blocker.height_m,
                "height_state": blocker.height_state,
            }
            for blocker in blockers
        ],
    }
    return ShadowAnalysisResult(
        analysis_id=analysis_id,
        status=status,
        solar_position=position,
        samples=results,
        dependency_fingerprint=canonical_hash(payload),
    )

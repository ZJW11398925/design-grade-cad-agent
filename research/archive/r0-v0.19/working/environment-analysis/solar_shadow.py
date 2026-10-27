"""Deterministic low-dependency solar/shadow probe for BATCH-005.

Scope: low-precision NOAA fractional-year sun position + geometric ray/vertical-prism
occlusion on a local metric XY plane. This is a benchmark/reference implementation,
not a validated professional solar simulation engine or a regulatory compliance tool.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict
from datetime import datetime, timezone
import hashlib
import json
import math
from typing import Any, Iterable

from shapely.geometry import LineString, Point, Polygon, MultiPolygon

Geometry = Polygon | MultiPolygon


@dataclass(frozen=True)
class SolarPosition:
    elevation_deg: float
    azimuth_deg_from_true_north_clockwise: float
    declination_deg: float
    equation_of_time_min: float
    algorithm: str = "NOAA fractional-year approximation (benchmark only)"


def solar_position_noaa(local_datetime: datetime, latitude_deg: float, longitude_deg: float) -> SolarPosition:
    """Return approximate solar elevation and azimuth for an offset-aware local datetime.

    Azimuth is clockwise from true north. The timestamp must include a UTC offset;
    this function does not infer location, timezone, or daylight-saving rules.
    """
    if local_datetime.tzinfo is None or local_datetime.utcoffset() is None:
        raise ValueError("local_datetime must be timezone-aware and include a UTC offset")
    if not -90 <= latitude_deg <= 90:
        raise ValueError("latitude_deg must be in [-90, 90]")
    if not -180 <= longitude_deg <= 180:
        raise ValueError("longitude_deg must be in [-180, 180]")

    day_of_year = local_datetime.timetuple().tm_yday
    hour = (
        local_datetime.hour
        + local_datetime.minute / 60.0
        + local_datetime.second / 3600.0
        + local_datetime.microsecond / 3_600_000_000.0
    )
    gamma = 2.0 * math.pi / 365.0 * (day_of_year - 1 + (hour - 12.0) / 24.0)
    equation_of_time = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2.0 * gamma)
        - 0.040849 * math.sin(2.0 * gamma)
    )
    declination = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2.0 * gamma)
        + 0.000907 * math.sin(2.0 * gamma)
        - 0.002697 * math.cos(3.0 * gamma)
        + 0.001480 * math.sin(3.0 * gamma)
    )

    utc_offset = local_datetime.utcoffset()
    assert utc_offset is not None
    timezone_hours = utc_offset.total_seconds() / 3600.0
    time_offset = equation_of_time + 4.0 * longitude_deg - 60.0 * timezone_hours
    true_solar_minutes = (hour * 60.0 + time_offset) % 1440.0
    hour_angle = math.radians(true_solar_minutes / 4.0 - 180.0)
    latitude = math.radians(latitude_deg)

    cos_zenith = (
        math.sin(latitude) * math.sin(declination)
        + math.cos(latitude) * math.cos(declination) * math.cos(hour_angle)
    )
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    elevation = 90.0 - math.degrees(math.acos(cos_zenith))
    azimuth = (
        math.degrees(
            math.atan2(
                math.sin(hour_angle),
                math.cos(hour_angle) * math.sin(latitude)
                - math.tan(declination) * math.cos(latitude),
            )
        )
        + 180.0
    ) % 360.0

    return SolarPosition(
        elevation_deg=elevation,
        azimuth_deg_from_true_north_clockwise=azimuth,
        declination_deg=math.degrees(declination),
        equation_of_time_min=equation_of_time,
    )


def sun_vector_in_project_frame(
    solar: SolarPosition, project_y_axis_bearing_deg: float | None = None
) -> tuple[float, float, float]:
    """Unit vector from site toward the sun in local project coordinates.

    Coordinate convention: x=east, y=north, z=up when bearing=0. The supplied
    bearing is the clockwise true-north bearing of the project's positive Y axis.
    Thus local azimuth = true-north azimuth - project-Y bearing.
    """
    if project_y_axis_bearing_deg is None:
        raise ValueError("project_y_axis_bearing_deg is required; do not assume true north")
    if not -360.0 <= project_y_axis_bearing_deg <= 360.0:
        raise ValueError("project_y_axis_bearing_deg must be in [-360, 360]")
    elevation = math.radians(solar.elevation_deg)
    local_azimuth = math.radians(
        (solar.azimuth_deg_from_true_north_clockwise - project_y_axis_bearing_deg) % 360.0
    )
    horizontal = math.cos(elevation)
    return (
        horizontal * math.sin(local_azimuth),
        horizontal * math.cos(local_azimuth),
        math.sin(elevation),
    )


@dataclass(frozen=True)
class Blocker:
    blocker_id: str
    footprint: Geometry
    base_elevation_m: float = 0.0
    height_m: float | None = None
    height_status: str = "confirmed"  # confirmed | estimated | unknown
    revision: str = "r1"

    def validate(self) -> None:
        if not isinstance(self.footprint, (Polygon, MultiPolygon)):
            raise ValueError(f"blocker {self.blocker_id} footprint must be Polygon or MultiPolygon")
        if not math.isfinite(self.base_elevation_m):
            raise ValueError(f"blocker {self.blocker_id} base_elevation_m must be finite")
        if self.height_status not in {"confirmed", "estimated", "unknown"}:
            raise ValueError(f"unsupported height_status: {self.height_status}")
        if not self.footprint.is_valid or self.footprint.is_empty:
            raise ValueError(f"blocker {self.blocker_id} has invalid/empty footprint")
        if self.height_status == "unknown" and self.height_m is not None:
            raise ValueError("unknown height must not carry a numeric height_m")
        if self.height_status != "unknown" and (self.height_m is None or not math.isfinite(self.height_m) or self.height_m <= 0):
            raise ValueError("confirmed/estimated height requires finite height_m > 0")


def _ray_intersects_unknown_height(sensor: Point, direction_xy: tuple[float, float], footprint: Geometry) -> bool:
    """Conservatively test whether an unbounded sun ray could meet an unknown-height footprint."""
    minx, miny, maxx, maxy = footprint.bounds
    sx, sy = sensor.x, sensor.y
    corners = ((minx, miny), (minx, maxy), (maxx, miny), (maxx, maxy))
    max_distance = max(math.hypot(x - sx, y - sy) for x, y in corners) + 1.0
    dx, dy = direction_xy
    ray = LineString([(sx, sy), (sx + dx * max_distance, sy + dy * max_distance)])
    # Ignore an intersection solely at the sensor origin; sensors inside/on a blocker are invalid separately.
    intersection = ray.intersection(footprint)
    return not intersection.is_empty


def assess_sensor_direct_sun(
    sensor_xy: tuple[float, float],
    sensor_elevation_m: float,
    solar: SolarPosition,
    blockers: Iterable[Blocker],
    *,
    project_y_axis_bearing_deg: float | None = None,
    context_complete: bool = True,
) -> dict[str, Any]:
    """Classify a horizontal ground sensor as sunlit, shaded, or unknown.

    Known-height vertical prisms are tested using a geometric ray segment from the
    sensor to the prism's top elevation. Unknown-height blockers only make the
    result unknown when their footprint intersects the ray in the sunward direction.
    """
    if len(sensor_xy) != 2 or not all(math.isfinite(v) for v in sensor_xy) or not math.isfinite(sensor_elevation_m):
        raise ValueError("sensor coordinates and elevation must be finite")
    if not math.isfinite(solar.elevation_deg) or not math.isfinite(solar.azimuth_deg_from_true_north_clockwise):
        return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "invalid_solar_position", "blocker_ids": []}
    sensor = Point(sensor_xy)
    if solar.elevation_deg <= 0.0:
        return {"sensor_xy": list(sensor_xy), "sunlit": False, "status": "night_or_sun_below_horizon", "blocker_ids": []}

    sx, sy, sz = sun_vector_in_project_frame(solar, project_y_axis_bearing_deg)
    horizontal_norm = math.hypot(sx, sy)
    if horizontal_norm < 1e-12:
        return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "invalid_solar_vector", "blocker_ids": []}
    direction_xy = (sx / horizontal_norm, sy / horizontal_norm)
    tan_elevation = math.tan(math.radians(solar.elevation_deg))
    unknown_hits: list[str] = []
    estimated_hits: list[str] = []

    for blocker in blockers:
        blocker.validate()
        if blocker.footprint.covers(sensor):
            return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "sensor_inside_or_on_blocker", "blocker_ids": [blocker.blocker_id]}

        if blocker.height_status == "unknown":
            if _ray_intersects_unknown_height(sensor, direction_xy, blocker.footprint):
                unknown_hits.append(blocker.blocker_id)
            continue
        if blocker.height_status == "estimated":
            # An estimated height cannot support a confirmed sunlit result if the
            # footprint lies on the sunward ray, even when the estimate is too short.
            if _ray_intersects_unknown_height(sensor, direction_xy, blocker.footprint):
                estimated_hits.append(blocker.blocker_id)
            continue

        assert blocker.height_m is not None
        top_z = blocker.base_elevation_m + blocker.height_m
        if top_z <= sensor_elevation_m:
            continue
        d_start = max(0.0, (blocker.base_elevation_m - sensor_elevation_m) / tan_elevation)
        d_end = (top_z - sensor_elevation_m) / tan_elevation
        if d_end <= d_start:
            continue
        dx, dy = direction_xy
        ray = LineString([
            (sensor.x + dx * d_start, sensor.y + dy * d_start),
            (sensor.x + dx * d_end, sensor.y + dy * d_end),
        ])
        if ray.intersects(blocker.footprint):
            return {"sensor_xy": list(sensor_xy), "sunlit": False, "status": "confirmed_shaded", "blocker_ids": [blocker.blocker_id]}

    if estimated_hits:
        return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "estimated_height_affects_result", "blocker_ids": estimated_hits}
    if unknown_hits:
        return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "unknown_obstruction_height", "blocker_ids": unknown_hits}
    if not context_complete:
        return {"sensor_xy": list(sensor_xy), "sunlit": None, "status": "incomplete_surrounding_context", "blocker_ids": []}
    return {"sensor_xy": list(sensor_xy), "sunlit": True, "status": "confirmed_sunlit_given_declared_context", "blocker_ids": []}


def dependency_fingerprint(manifest: dict[str, Any]) -> str:
    """Hash all declared analysis dependencies using stable JSON canonicalization."""
    canonical = json.dumps(manifest, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


def result_is_stale(stored_dependency_hash: str, current_manifest: dict[str, Any]) -> bool:
    return stored_dependency_hash != dependency_fingerprint(current_manifest)


def sampled_direct_sun_hours(
    sensor_xy: tuple[float, float],
    sensor_elevation_m: float,
    times: list[datetime],
    latitude_deg: float,
    longitude_deg: float,
    blockers: Iterable[Blocker],
    *,
    timestep_hours: float,
    project_y_axis_bearing_deg: float | None = None,
    context_complete: bool = True,
) -> dict[str, Any]:
    """Sum sampled direct-sun intervals; unknown intervals yield lower/upper bounds.

    This is a geometry-only, discrete-time clear-sun probe. It is not weather-weighted,
    annual climate simulation, indoor daylight analysis, or a legal sunlight-hours test.
    """
    if timestep_hours <= 0 or not math.isfinite(timestep_hours):
        raise ValueError("timestep_hours must be finite and > 0")
    if not times:
        raise ValueError("times must not be empty")
    if any(dt.tzinfo is None or dt.utcoffset() is None for dt in times):
        raise ValueError("all sample times must be timezone-aware")
    utc_times = [dt.astimezone(timezone.utc) for dt in times]
    for left, right in zip(utc_times, utc_times[1:]):
        interval = (right - left).total_seconds() / 3600.0
        if interval <= 0:
            raise ValueError("sample times must be strictly increasing")
        if not math.isclose(interval, timestep_hours, rel_tol=0.0, abs_tol=1e-9):
            raise ValueError("sample times must be evenly spaced at timestep_hours")
    blockers = tuple(blockers)
    samples = []
    sunlit_count = 0
    unknown_count = 0
    for dt in times:
        solar = solar_position_noaa(dt, latitude_deg, longitude_deg)
        result = assess_sensor_direct_sun(
            sensor_xy, sensor_elevation_m, solar, blockers,
            project_y_axis_bearing_deg=project_y_axis_bearing_deg,
            context_complete=context_complete,
        )
        samples.append({"time": dt.isoformat(), "solar": asdict(solar), "assessment": result})
        if result["sunlit"] is True:
            sunlit_count += 1
        elif result["sunlit"] is None:
            unknown_count += 1
    lower = sunlit_count * timestep_hours
    upper = (sunlit_count + unknown_count) * timestep_hours
    return {
        "metric": "sampled_direct_sun_hours_geometry_only",
        "lower_bound_hours": lower,
        "upper_bound_hours": upper,
        "timestep_hours": timestep_hours,
        "sample_count": len(times),
        "unknown_sample_count": unknown_count,
        "status": "confirmed_for_declared_context" if unknown_count == 0 else "bounded_or_unknown",
        "samples": samples,
    }

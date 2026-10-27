from datetime import datetime, timezone, timedelta
import math

import pytest
from shapely.geometry import box

from solar_shadow_v0_3 import (
    Blocker,
    SolarPosition,
    assess_sensor_direct_sun,
    dependency_fingerprint,
    result_is_stale,
    sampled_direct_sun_hours,
    solar_position_noaa,
    sun_vector_in_project_frame,
)


def fixed_sun(altitude=45.0, azimuth=90.0):
    return SolarPosition(altitude, azimuth, 0.0, 0.0)


def test_published_ladybug_sydney_example_is_within_low_precision_tolerance():
    # Ladybug's official README/test gives Sydney 15 Nov, 11:00 local as 72.26° / 32.37°.
    # This is a cross-implementation sanity check, not a high-precision certification.
    dt = datetime(2025, 11, 15, 11, 0, tzinfo=timezone(timedelta(hours=10)))
    solar = solar_position_noaa(dt, -33.87, 151.22)
    assert abs(solar.elevation_deg - 72.26) < 0.5
    assert abs(solar.azimuth_deg_from_true_north_clockwise - 32.37) < 0.5


def test_naive_datetime_is_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        solar_position_noaa(datetime(2025, 6, 21, 12), 40.0, 116.0)


def test_latitude_out_of_range_is_rejected():
    with pytest.raises(ValueError, match="latitude"):
        solar_position_noaa(datetime(2025, 6, 21, 12, tzinfo=timezone.utc), 91, 0)


def test_sun_vector_is_unit_length():
    vec = sun_vector_in_project_frame(fixed_sun(30, 90), project_y_axis_bearing_deg=0)
    assert math.isclose(math.sqrt(sum(v * v for v in vec)), 1.0, rel_tol=1e-12)


def test_east_blocker_shades_sensor_when_sun_is_east():
    blocker = Blocker("B-EAST", box(4, -1, 5, 1), height_m=6, height_status="confirmed")
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=0)
    assert result["sunlit"] is False
    assert result["status"] == "confirmed_shaded"
    assert result["blocker_ids"] == ["B-EAST"]


def test_shorter_blocker_does_not_reach_sensor_ray():
    blocker = Blocker("B-SHORT", box(4, -1, 5, 1), height_m=2, height_status="confirmed")
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=0)
    assert result["sunlit"] is True


def test_unknown_height_that_intersects_ray_blocks_confirmation():
    blocker = Blocker("B-UNKNOWN", box(4, -1, 5, 1), height_m=None, height_status="unknown")
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=0)
    assert result["sunlit"] is None
    assert result["status"] == "unknown_obstruction_height"


def test_incomplete_context_does_not_confirm_sunlit_result():
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [], project_y_axis_bearing_deg=0, context_complete=False)
    assert result["sunlit"] is None
    assert result["status"] == "incomplete_surrounding_context"


def test_north_rotation_changes_project_frame_shadow_direction():
    # With +Y pointing east, a true-east sun is in project +Y direction.
    vec = sun_vector_in_project_frame(fixed_sun(45, 90), project_y_axis_bearing_deg=90)
    assert abs(vec[0]) < 1e-12
    assert vec[1] > 0
    blocker = Blocker("B-NORTH", box(-1, 4, 1, 5), height_m=6, height_status="confirmed")
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=90)
    assert result["status"] == "confirmed_shaded"


def test_height_revision_changes_dependency_fingerprint_and_marks_stale():
    old = {
        "footprint_revision": "fp-r1", "height_revision": "h-r1", "placement_revision": "p-r1",
        "terrain_revision": "t-r1", "north_bearing_deg": 0,
        "site_latitude": -33.87, "site_longitude": 151.22,
        "timestamp_local_iso": "2025-11-15T11:00:00+10:00", "analysis_method": "NOAA-low-precision+ray-prism",
        "analysis_method_version": "0.1.0", "context_complete": True,
    }
    old_hash = dependency_fingerprint(old)
    assert not result_is_stale(old_hash, old)
    new = dict(old, height_revision="h-r2")
    assert result_is_stale(old_hash, new)


def test_sampled_hours_produce_bounds_when_context_is_unknown():
    times = [
        datetime(2025, 11, 15, 10, 0, tzinfo=timezone(timedelta(hours=10))),
        datetime(2025, 11, 15, 11, 0, tzinfo=timezone(timedelta(hours=10))),
    ]
    blocker = Blocker("B-UNKNOWN", box(2, 2, 5, 8), height_m=None, height_status="unknown")
    result = sampled_direct_sun_hours(
        (0, 0), 0, times, -33.87, 151.22, [blocker], timestep_hours=1, interval_convention="timestamp_starts_interval", project_y_axis_bearing_deg=0,
    )
    assert result["sample_count"] == 2
    assert result["upper_bound_hours"] >= result["lower_bound_hours"]
    assert result["status"] == "bounded_or_unknown"


def test_same_manifest_is_deterministic():
    manifest = {"footprint_revision": "fp-r1", "height_revision": "h-r1", "north_bearing_deg": 0}
    assert dependency_fingerprint(manifest) == dependency_fingerprint(manifest)


def test_missing_north_is_rejected_for_daytime_geometry():
    with pytest.raises(ValueError, match="required; do not assume true north"):
        sun_vector_in_project_frame(fixed_sun(45, 90))
    with pytest.raises(ValueError, match="required; do not assume true north"):
        assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [])


def test_estimated_height_cannot_confirm_sunlit_when_ray_meets_footprint():
    blocker = Blocker("B-ESTIMATED", box(4, -1, 5, 1), height_m=2, height_status="estimated")
    result = assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=0)
    assert result["sunlit"] is None
    assert result["status"] == "estimated_height_affects_result"



def test_irregular_sample_times_are_rejected():
    times = [
        datetime(2025, 11, 15, 10, 0, tzinfo=timezone(timedelta(hours=10))),
        datetime(2025, 11, 15, 11, 30, tzinfo=timezone(timedelta(hours=10))),
    ]
    with pytest.raises(ValueError, match="evenly spaced"):
        sampled_direct_sun_hours((0, 0), 0, times, -33.87, 151.22, [], timestep_hours=1, interval_convention="timestamp_starts_interval", project_y_axis_bearing_deg=0)



def test_empty_time_samples_are_rejected():
    with pytest.raises(ValueError, match="must not be empty"):
        sampled_direct_sun_hours((0, 0), 0, [], -33.87, 151.22, [], timestep_hours=1, interval_convention="timestamp_starts_interval", project_y_axis_bearing_deg=0)


def test_nonfinite_confirmed_height_is_rejected():
    blocker = Blocker("B-NAN", box(4, -1, 5, 1), height_m=float("nan"), height_status="confirmed")
    with pytest.raises(ValueError, match="finite real height_m"):
        assess_sensor_direct_sun((0, 0), 0, fixed_sun(45, 90), [blocker], project_y_axis_bearing_deg=0)


def test_exact_solar_zenith_is_not_misclassified_as_invalid_vector():
    result = assess_sensor_direct_sun(
        (0.0, 0.0), 0.0, SolarPosition(90.0, 180.0, 23.4, 0.0), [],
        project_y_axis_bearing_deg=0.0, context_complete=True,
    )
    assert result["sunlit"] is True
    assert result["status"] == "confirmed_sunlit_given_declared_context"


def test_zenith_preserves_incomplete_context_as_unknown():
    result = assess_sensor_direct_sun(
        (0.0, 0.0), 0.0, SolarPosition(90.0, 180.0, 23.4, 0.0), [],
        project_y_axis_bearing_deg=0.0, context_complete=False,
    )
    assert result["sunlit"] is None
    assert result["status"] == "incomplete_surrounding_context"


def test_boolean_height_is_rejected():
    blocker = Blocker("BOOL-HEIGHT", box(1, 1, 2, 2), height_m=True, height_status="confirmed")
    with pytest.raises(ValueError, match="finite real height_m"):
        blocker.validate()


def test_boolean_sensor_coordinate_is_rejected():
    with pytest.raises(ValueError, match="finite real numbers"):
        assess_sensor_direct_sun((True, 0.0), 0.0, fixed_sun(), [], project_y_axis_bearing_deg=0.0)


def test_boolean_latitude_is_rejected():
    with pytest.raises(ValueError, match="finite real number"):
        solar_position_noaa(datetime(2025, 6, 21, 12, tzinfo=timezone.utc), True, 0.0)


def test_timestamp_starts_interval_counts_each_timestamp_and_reports_coverage():
    t0 = datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc)
    result = sampled_direct_sun_hours(
        (0.0, 0.0), 0.0, [t0], 0.0, 0.0, [], timestep_hours=1.0,
        interval_convention="timestamp_starts_interval", project_y_axis_bearing_deg=0.0,
    )
    assert result["interval_count"] == 1
    assert result["lower_bound_hours"] == 1.0
    assert result["coverage_start"] == t0.isoformat()
    assert result["coverage_end"] == (t0 + timedelta(hours=1)).isoformat()


def test_timestamp_is_instant_counts_only_intervals_between_samples():
    t0 = datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc)
    times = [t0, t0 + timedelta(hours=1), t0 + timedelta(hours=2)]
    result = sampled_direct_sun_hours(
        (0.0, 0.0), 0.0, times, 0.0, 0.0, [], timestep_hours=1.0,
        interval_convention="timestamp_is_instant", project_y_axis_bearing_deg=0.0,
    )
    assert result["sample_count"] == 3
    assert result["interval_count"] == 2
    assert result["lower_bound_hours"] == 2.0
    assert result["coverage_end"] == times[-1].isoformat()


def test_timestamp_is_instant_requires_two_samples():
    t0 = datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="at least two timestamps"):
        sampled_direct_sun_hours(
            (0.0, 0.0), 0.0, [t0], 0.0, 0.0, [], timestep_hours=1.0,
            interval_convention="timestamp_is_instant", project_y_axis_bearing_deg=0.0,
        )


def test_interval_convention_must_be_explicit_and_supported():
    t0 = datetime(2025, 6, 21, 12, 0, tzinfo=timezone.utc)
    with pytest.raises(ValueError, match="interval_convention must be"):
        sampled_direct_sun_hours(
            (0.0, 0.0), 0.0, [t0], 0.0, 0.0, [], timestep_hours=1.0,
            interval_convention="ambiguous", project_y_axis_bearing_deg=0.0,
        )


def test_zenith_sensor_inside_blocker_is_not_confirmed_sunlit():
    blocker = Blocker("OVERHEAD", box(-1, -1, 1, 1), height_m=5.0, height_status="confirmed")
    result = assess_sensor_direct_sun(
        (0.0, 0.0), 0.0, SolarPosition(90.0, 0.0, 23.4, 0.0), [blocker],
        project_y_axis_bearing_deg=0.0, context_complete=True,
    )
    assert result["sunlit"] is None
    assert result["status"] == "sensor_inside_or_on_blocker"

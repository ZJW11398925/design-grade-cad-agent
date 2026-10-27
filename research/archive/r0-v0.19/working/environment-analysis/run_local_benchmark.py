"""Run the bounded BATCH-005 solar/shadow probe and write a JSON result report.

Requires Python 3.10+ and Shapely 2.x. This benchmark is not a professional
solar simulation or a regulatory compliance test.
"""
from __future__ import annotations

from datetime import datetime, timezone, timedelta
from pathlib import Path
import importlib.util
import json
import hashlib
import sys
import shapely

from shapely.geometry import box

from solar_shadow import (
    Blocker,
    SolarPosition,
    assess_sensor_direct_sun,
    dependency_fingerprint,
    result_is_stale,
    sampled_direct_sun_hours,
    solar_position_noaa,
)

ROOT = Path(__file__).resolve().parent


def run_assertion_functions() -> dict:
    """Invoke the pytest-style test functions directly for sandbox diagnostics."""
    spec = importlib.util.spec_from_file_location("test_solar_shadow", ROOT / "test_solar_shadow.py")
    if spec is None or spec.loader is None:
        raise RuntimeError("could not load test_solar_shadow.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    names = sorted(name for name in dir(module) if name.startswith("test_"))
    passed, failed = [], []
    for name in names:
        try:
            getattr(module, name)()
            passed.append(name)
        except Exception as exc:  # include the failure in a durable report
            failed.append({"test": name, "error": repr(exc)})
    return {"runner": "direct_invocation_of_pytest_style_functions", "passed": len(passed), "failed": failed, "passed_tests": passed}


def main() -> int:
    local_dt = datetime(2025, 11, 15, 11, 0, tzinfo=timezone(timedelta(hours=10)))
    solar = solar_position_noaa(local_dt, latitude_deg=-33.87, longitude_deg=151.22)
    official_ladybug_reference = {"elevation_deg": 72.26, "azimuth_deg": 32.37, "source": "Ladybug official README/tests Sydney example; year is abstracted in example"}

    fixed_sun = SolarPosition(45.0, 90.0, 0.0, 0.0)
    tall_blocker = Blocker("B-EAST", box(4, -1, 5, 1), height_m=6.0, height_status="confirmed", revision="r1")
    short_blocker = Blocker("B-SHORT", box(4, -1, 5, 1), height_m=2.0, height_status="confirmed", revision="r1")
    unknown_blocker = Blocker("B-UNKNOWN", box(4, -1, 5, 1), height_m=None, height_status="unknown", revision="r1")

    shade_tall = assess_sensor_direct_sun((0, 0), 0, fixed_sun, [tall_blocker], project_y_axis_bearing_deg=0)
    shade_short = assess_sensor_direct_sun((0, 0), 0, fixed_sun, [short_blocker], project_y_axis_bearing_deg=0)
    shade_unknown = assess_sensor_direct_sun((0, 0), 0, fixed_sun, [unknown_blocker], project_y_axis_bearing_deg=0)
    estimated_blocker = Blocker("B-ESTIMATED", box(4, -1, 5, 1), height_m=2.0, height_status="estimated", revision="r1")
    shade_estimated = assess_sensor_direct_sun((0, 0), 0, fixed_sun, [estimated_blocker], project_y_axis_bearing_deg=0)
    incomplete_context = assess_sensor_direct_sun((0, 0), 0, fixed_sun, [], project_y_axis_bearing_deg=0, context_complete=False)

    manifest = {
        "site_model_id": "SYNTHETIC-ENV-SITE-001",
        "site_model_revision": "site-r1",
        "footprint_revision": "fp-r1",
        "body_revision": "body-r1",
        "height_revision": "height-r1",
        "placement_revision": "placement-r1",
        "terrain_revision": "terrain-r1",
        "coordinate_frame_id": "LOCAL-ENU-XY-ZUP",
        "coordinate_units": "metre",
        "project_y_axis_true_north_bearing_deg": 0.0,
        "latitude_deg": -33.87,
        "longitude_deg": 151.22,
        "local_datetime_iso_with_utc_offset": local_dt.isoformat(),
        "timezone_identifier_or_explicit_offset": "+10:00 (explicit offset; no DST rule inferred)",
        "solar_position_method": "NOAA fractional-year approximation",
        "solar_position_method_version": "local-probe-0.1.0",
        "shadow_method": "2D ray segment against vertical prism footprint",
        "shadow_method_version": "local-probe-0.1.0",
        "blocker_object_ids_and_revisions": ["B-EAST:r1"],
        "blocker_height_source_statuses": ["confirmed"],
        "sensor_grid_revision": "sensor-grid-r1",
        "timestep_hours": 1.0,
        "analysis_period": "single synthetic timestamp for solar-position check",
        "context_coverage_status": "declared-complete-for-synthetic-case",
        "terrain_coverage_status": "flat-ground-assumption",
        "weather_or_sky_source_and_revision": "none; geometric direct-sun only",
        "result_metric_definition": "pointwise direct-sun visibility under declared vertical-prism blockers",
    }
    manifest_hash = dependency_fingerprint(manifest)
    manifest_changed_height = dict(manifest, height_revision="height-r2")

    sample_times = [
        datetime(2025, 11, 15, 10, 0, tzinfo=timezone(timedelta(hours=10))),
        datetime(2025, 11, 15, 11, 0, tzinfo=timezone(timedelta(hours=10))),
    ]
    hour_bounds = sampled_direct_sun_hours(
        (0, 0), 0, sample_times, -33.87, 151.22,
        [Blocker("B-UNKNOWN-NE", box(2, 2, 5, 8), height_m=None, height_status="unknown")],
        timestep_hours=1.0, project_y_axis_bearing_deg=0.0,
    )

    tests = run_assertion_functions()
    result = {
        "run_id": "RUN-005-01",
        "benchmark_id": "LOCAL-ENV-001",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "environment": {"python_version": sys.version.split()[0], "shapely_version": shapely.__version__},
        "source_sha256": {"solar_shadow.py": hashlib.sha256((ROOT / "solar_shadow.py").read_bytes()).hexdigest(), "test_solar_shadow.py": hashlib.sha256((ROOT / "test_solar_shadow.py").read_bytes()).hexdigest()},
        "status": "passed_with_scope_limits" if tests["passed"] == 17 and not tests["failed"] else "failed",
        "local_tests": tests,
        "solar_position_reference_check": {
            "input": {"datetime": local_dt.isoformat(), "latitude_deg": -33.87, "longitude_deg": 151.22},
            "local_result": {"elevation_deg": solar.elevation_deg, "azimuth_deg": solar.azimuth_deg_from_true_north_clockwise, "algorithm": solar.algorithm},
            "published_reference": official_ladybug_reference,
            "absolute_delta_deg": {"elevation": abs(solar.elevation_deg - official_ladybug_reference["elevation_deg"]), "azimuth": abs(solar.azimuth_deg_from_true_north_clockwise - official_ladybug_reference["azimuth_deg"])},
            "tolerance_deg": 0.5,
            "pass": abs(solar.elevation_deg - 72.26) < 0.5 and abs(solar.azimuth_deg_from_true_north_clockwise - 32.37) < 0.5,
        },
        "geometric_occlusion_cases": {
            "tall_confirmed_blocker": shade_tall,
            "short_confirmed_blocker": shade_short,
            "unknown_height_blocker": shade_unknown,
            "estimated_height_blocker": shade_estimated,
            "incomplete_surrounding_context": incomplete_context,
        },
        "revision_staleness": {
            "current_fingerprint_sha256": manifest_hash,
            "same_manifest_is_stale": result_is_stale(manifest_hash, manifest),
            "height_revision_changed_is_stale": result_is_stale(manifest_hash, manifest_changed_height),
            "required_dependencies": manifest,
        },
        "sampled_direct_sun_hours": hour_bounds,
        "limits": [
            "The NOAA fractional-year formula is low-precision and is only cross-checked against a published example within 0.5 degrees.",
            "The shadow probe uses vertical prism footprints on a local metric plane; it does not model facade apertures, sloped terrain, transparent materials, refraction, weather, diffuse sky, or complex 3D mesh intersection.",
            "The sampled-hours output is discrete-time, geometry-only direct sun, not annual climate-based daylight or regulatory compliance.",
            "No Ladybug, pvlib, Honeybee-Radiance, Radiance, or momepy runtime was available in this sandbox.",
        ],
    }
    output = ROOT / "local-benchmark-001-solar-shadow.json"
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(output), "status": result["status"], "passed_tests": tests["passed"], "failed_tests": len(tests["failed"]), "solar_reference_check": result["solar_position_reference_check"]["pass"], "unknown_height_status": shade_unknown["status"], "height_revision_stale": result["revision_staleness"]["height_revision_changed_is_stale"]}, ensure_ascii=False, indent=2))
    return 0 if result["status"] == "passed_with_scope_limits" and result["solar_position_reference_check"]["pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())

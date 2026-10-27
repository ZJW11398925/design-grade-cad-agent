"""Run the shared synthetic site fixture through the environment-analysis slice."""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import json
import hashlib
import sys

from shapely.geometry import shape

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "environment-analysis"))
from solar_shadow import Blocker, assess_sensor_direct_sun, dependency_fingerprint, result_is_stale, solar_position_noaa  # noqa: E402

ROOT = Path(__file__).resolve().parent
fixture_path = ROOT / "site-fixture-v0.1.json"
fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
assert fixture["synthetic_only"] is True
site = fixture["site"]
location = site["location_for_solar_test_only"]
local_dt = datetime.fromisoformat(site["local_datetime_iso_with_utc_offset"])
solar = solar_position_noaa(local_dt, location["latitude_deg"], location["longitude_deg"])

blockers = []
for obj in fixture["objects"]:
    if obj["object_class"] != "building":
        continue
    massing = obj["massing"]
    height_state = massing["height_state"]
    if height_state == "unknown":
        status = "unknown"
        height = None
    elif height_state == "estimated":
        status = "estimated"
        height = massing["height_m"]
    else:
        status = "confirmed"
        height = massing["height_m"]
    blockers.append(Blocker(
        blocker_id=obj["object_id"],
        footprint=shape({"type": obj["geometry_type"], "coordinates": obj["coordinates"]}),
        base_elevation_m=massing["base_elevation_m"],
        height_m=height,
        height_status=status,
        revision=f'{obj["geometry_revision"]}|{massing["height_revision"]}|{obj["placement_revision"]}',
    ))

bearing = site["coordinate_frame"]["project_y_axis_true_north_bearing_deg"]
context_complete = site["context_coverage_status"] == "complete_for_declared_synthetic_fixture"
results = []
for sensor in fixture["sensors"]:
    assessment = assess_sensor_direct_sun(
        (sensor["x_m"], sensor["y_m"]), sensor["z_m"], solar, blockers,
        project_y_axis_bearing_deg=bearing,
        context_complete=context_complete,
    )
    results.append({
        "sensor_id": sensor["sensor_id"],
        "expected_status": sensor["expected_status"],
        "actual": assessment,
        "passed": assessment["status"] == sensor["expected_status"] and assessment["blocker_ids"] == sensor["expected_blocker_ids"],
    })

# Synthetic Footprint -> Massing identity checks. This is extrusion metadata/projection
# validation, not an IFC or CAD solid-kernel round-trip.
body_projection_checks = []
for obj in fixture["objects"]:
    if obj["object_class"] != "building":
        continue
    massing = obj["massing"]
    reps = obj.get("representations", {})
    footprint = shape({"type": obj["geometry_type"], "coordinates": obj["coordinates"]})
    if massing["height_state"] == "unknown":
        passed = reps.get("body_3d", {}).get("state") == "missing" and obj.get("body_revision") is None
        body_projection_checks.append({"object_id": obj["object_id"], "status": "blocked_missing_height", "body_not_generated": passed, "passed": passed})
    else:
        body_rep = reps.get("body_3d", {})
        # For a vertical extrusion, XY projection is the same footprint by construction.
        projected_footprint = footprint
        symmetric_difference_area = footprint.symmetric_difference(projected_footprint).area
        passed = (body_rep.get("state") == "current" and body_rep.get("ref") == f'{obj["object_id"]}/body-r1'
                  and obj.get("body_revision") is not None and symmetric_difference_area == 0.0
                  and massing["height_m"] > 0)
        body_projection_checks.append({"object_id": obj["object_id"], "status": "synthetic_body_projection_matches_footprint", "xy_symmetric_difference_area_m2": symmetric_difference_area, "base_elevation_m": massing["base_elevation_m"], "top_elevation_m": massing["base_elevation_m"] + massing["height_m"], "passed": passed})

manifest = {
    "fixture_id": fixture["fixture_id"],
    "fixture_revision": fixture["fixture_revision"],
    "site_model_revision": site["site_model_revision"],
    "coordinate_frame_id": site["coordinate_frame"]["coordinate_frame_id"],
    "coordinate_units": site["coordinate_frame"]["units"],
    "project_y_axis_true_north_bearing_deg": bearing,
    "site_latitude_deg": location["latitude_deg"],
    "site_longitude_deg": location["longitude_deg"],
    "local_datetime_iso_with_utc_offset": site["local_datetime_iso_with_utc_offset"],
    "terrain_revision": site["terrain"]["revision"],
    "context_coverage_status": site["context_coverage_status"],
    "sensor_grid_revision": fixture["sensors"][0]["sensor_grid_revision"],
    "solar_position_method": solar.algorithm,
    "solar_position_method_version": "local-probe-0.1.0",
    "shadow_method": "2D ray segment against vertical-prism footprints",
    "shadow_method_version": "local-probe-0.1.0",
    "sensor_grid_content_hash_sha256": hashlib.sha256(json.dumps([{k: s[k] for k in ("sensor_id", "sensor_grid_revision", "x_m", "y_m", "z_m")} for s in fixture["sensors"]], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
    "terrain_content_hash_sha256": hashlib.sha256(json.dumps(site["terrain"], sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
    "object_revisions": [
        {
            "object_id": o["object_id"],
            "geometry_revision": o["geometry_revision"],
            "geometry_content_hash_sha256": hashlib.sha256(json.dumps({"type": o["geometry_type"], "coordinates": o["coordinates"]}, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
            "placement_revision": o.get("placement_revision"),
            "body_revision": o.get("body_revision"),
            "height_revision": o.get("massing", {}).get("height_revision"),
        }
        for o in fixture["objects"] if o["object_class"] == "building"
    ],
}
fingerprint = dependency_fingerprint(manifest)
height_mutation = deepcopy(manifest)
height_mutation["object_revisions"][0]["height_revision"] = "height-r2"
geometry_mutation = deepcopy(manifest)
geometry_mutation["object_revisions"][0]["geometry_content_hash_sha256"] = "mutated-without-revision-bump"
north_mutation = deepcopy(manifest)
north_mutation["project_y_axis_true_north_bearing_deg"] = 90.0

rotated_results = []
for sensor in fixture["sensors"]:
    assessment = assess_sensor_direct_sun(
        (sensor["x_m"], sensor["y_m"]), sensor["z_m"], solar, blockers,
        project_y_axis_bearing_deg=90.0,
        context_complete=context_complete,
    )
    rotated_results.append({"sensor_id": sensor["sensor_id"], "status": assessment["status"], "sunlit": assessment["sunlit"]})

result = {
    "run_id": "RUN-E2E-001",
    "benchmark_id": "LOCAL-E2E-ENV-001",
    "fixture_id": fixture["fixture_id"],
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed_with_scope_limits" if all(r["passed"] for r in results) and all(c["passed"] for c in body_projection_checks) and result_is_stale(fingerprint, height_mutation) and result_is_stale(fingerprint, geometry_mutation) and result_is_stale(fingerprint, north_mutation) else "failed",
    "solar_position": {
        "elevation_deg": solar.elevation_deg,
        "azimuth_deg_from_true_north_clockwise": solar.azimuth_deg_from_true_north_clockwise,
        "algorithm": solar.algorithm,
    },
    "dependency_fingerprint_sha256": fingerprint,
    "sensor_results": results,
    "synthetic_footprint_body_identity_checks": body_projection_checks,
    "revision_checks": {
        "same_manifest_stale": result_is_stale(fingerprint, manifest),
        "height_revision_change_stale": result_is_stale(fingerprint, height_mutation),
        "geometry_content_change_without_revision_bump_stale": result_is_stale(fingerprint, geometry_mutation),
        "north_bearing_change_stale": result_is_stale(fingerprint, north_mutation),
    },
    "north_rotation_probe": {
        "changed_bearing_deg": 90.0,
        "dependency_stale": result_is_stale(fingerprint, north_mutation),
        "sensor_results": rotated_results,
    },
    "limits": [
        "This is a synthetic vertical slice through the shared fixture into the environment-analysis module only.",
        "It does not run road generation, building regularization, IFC export, DXF compilation, or an independent solar/shadow engine.",
        "The location is a solar-position reference only and does not georeference the local site geometry.",
        "Passing results prove fixture/interface invariants only, not real-site quality, professional design correctness, or regulatory compliance.",
    ],
}
output = ROOT / "local-e2e-fixture-env-001.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps({"output": str(output), "status": result["status"], "sensor_passes": sum(r["passed"] for r in results), "sensor_total": len(results), "body_identity_passes": sum(c["passed"] for c in body_projection_checks), "body_identity_total": len(body_projection_checks), "height_revision_stale": result["revision_checks"]["height_revision_change_stale"], "geometry_content_without_revision_stale": result["revision_checks"]["geometry_content_change_without_revision_bump_stale"], "north_bearing_stale": result["revision_checks"]["north_bearing_change_stale"], "rotated_statuses": {r["sensor_id"]: r["status"] for r in rotated_results}}, ensure_ascii=False, indent=2))
raise SystemExit(0 if result["status"] == "passed_with_scope_limits" else 1)

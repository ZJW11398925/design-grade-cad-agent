"""Run E2E-FIXTURE-001 through the bounded environment-analysis probe.

This is a synthetic contract test, not a validated solar simulation engine.
"""
from __future__ import annotations
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, math, sys
from shapely.geometry import shape, Polygon, MultiPolygon

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "environment-analysis"))
from solar_shadow import Blocker, assess_sensor_direct_sun, dependency_fingerprint, result_is_stale, solar_position_noaa  # noqa: E402


def canonical_hash(value) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def body_checks_for(obj: dict, frame_id: str) -> dict:
    massing = obj["massing"]
    reps = obj.get("representations", {})
    body = reps.get("body_3d", {})
    footprint = shape({"type": obj["geometry_type"], "coordinates": obj["coordinates"]})
    if massing["height_state"] == "unknown":
        passed = body.get("state") == "missing" and obj.get("body_revision") is None and "geometry" not in body
        return {"object_id": obj["object_id"], "status": "blocked_missing_height", "body_not_generated": passed, "passed": passed}

    geometry = body.get("geometry")
    if body.get("state") != "current" or not obj.get("body_revision") or not isinstance(geometry, dict):
        return {"object_id": obj["object_id"], "status": "failed_missing_body_geometry", "passed": False}
    if geometry.get("coordinate_frame_id") != frame_id or geometry.get("units") != "metre" or geometry.get("geometry_type") != "vertical_prism_mesh":
        return {"object_id": obj["object_id"], "status": "failed_body_frame_or_type", "passed": False}

    vertices = geometry.get("vertices", [])
    faces = geometry.get("faces", [])
    if not vertices or not faces or any(len(v) != 3 or not all(isinstance(x, (int, float)) and math.isfinite(x) for x in v) for v in vertices):
        return {"object_id": obj["object_id"], "status": "failed_invalid_vertices", "passed": False}
    if any(len(face) < 3 or any(not isinstance(i, int) or i < 0 or i >= len(vertices) for i in face) for face in faces):
        return {"object_id": obj["object_id"], "status": "failed_invalid_faces", "passed": False}

    base_z = float(massing["base_elevation_m"])
    top_z = base_z + float(massing["height_m"])
    top_faces = [face for face in faces if all(math.isclose(vertices[i][2], top_z, abs_tol=1e-9) for i in face)]
    bottom_faces = [face for face in faces if all(math.isclose(vertices[i][2], base_z, abs_tol=1e-9) for i in face)]
    if len(top_faces) != 1 or len(bottom_faces) != 1:
        return {"object_id": obj["object_id"], "status": "failed_top_bottom_faces", "top_face_count": len(top_faces), "bottom_face_count": len(bottom_faces), "passed": False}

    # Critically, derive this projection from the stored body's actual top-face vertices;
    # do not reuse the footprint object as the projected result.
    top_xy = [(vertices[i][0], vertices[i][1]) for i in top_faces[0]]
    bottom_xy = [(vertices[i][0], vertices[i][1]) for i in bottom_faces[0]]
    projected_top = Polygon(top_xy)
    projected_bottom = Polygon(bottom_xy)
    if not projected_top.is_valid or projected_top.is_empty or not projected_bottom.is_valid or projected_bottom.is_empty:
        return {"object_id": obj["object_id"], "status": "failed_projected_body_polygon", "passed": False}
    top_diff = footprint.symmetric_difference(projected_top).area
    bottom_diff = footprint.symmetric_difference(projected_bottom).area
    top_z_valid = all(math.isclose(vertices[i][2], top_z, abs_tol=1e-9) for i in top_faces[0])
    bottom_z_valid = all(math.isclose(vertices[i][2], base_z, abs_tol=1e-9) for i in bottom_faces[0])
    all_vertex_z_valid = all(math.isclose(v[2], base_z, abs_tol=1e-9) or math.isclose(v[2], top_z, abs_tol=1e-9) for v in vertices)
    top_xy_set = sorted((round(x, 9), round(y, 9)) for x, y in top_xy)
    bottom_xy_set = sorted((round(x, 9), round(y, 9)) for x, y in bottom_xy)
    same_top_bottom_xy = top_xy_set == bottom_xy_set
    # A closed prism shell has each undirected mesh edge used by exactly two faces.
    edge_counts = {}
    for face in faces:
        for a, b in zip(face, face[1:] + face[:1]):
            edge = tuple(sorted((a, b)))
            edge_counts[edge] = edge_counts.get(edge, 0) + 1
    closed_shell = bool(edge_counts) and all(count == 2 for count in edge_counts.values())
    passed = (top_diff <= 1e-9 and bottom_diff <= 1e-9 and top_z_valid and bottom_z_valid
              and all_vertex_z_valid and same_top_bottom_xy and closed_shell)
    return {
        "object_id": obj["object_id"],
        "status": "stored_body_mesh_projection_matches_footprint" if passed else "failed_body_projection_or_mesh_mismatch",
        "top_xy_symmetric_difference_area_m2": top_diff,
        "bottom_xy_symmetric_difference_area_m2": bottom_diff,
        "base_elevation_m": base_z,
        "top_elevation_m": top_z,
        "top_z_valid": top_z_valid,
        "bottom_z_valid": bottom_z_valid,
        "all_vertex_z_valid": all_vertex_z_valid,
        "same_top_bottom_xy": same_top_bottom_xy,
        "closed_shell_edge_check": closed_shell,
        "body_geometry_content_hash_sha256": canonical_hash(geometry),
        "projected_top_face_coordinates": top_xy,
        "passed": passed,
    }


def run() -> dict:
    fixture_path = ROOT / "site-fixture-v0.2.json"
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
    if fixture.get("synthetic_only") is not True:
        raise ValueError("E2E-FIXTURE-001 must remain explicitly synthetic_only")
    site = fixture["site"]
    location = site["location_for_solar_test_only"]
    local_dt = datetime.fromisoformat(site["local_datetime_iso_with_utc_offset"])
    solar = solar_position_noaa(local_dt, location["latitude_deg"], location["longitude_deg"])
    frame = site["coordinate_frame"]

    height_state_map = {
        "confirmed_within_synthetic_fixture": "confirmed",
        "confirmed": "confirmed",
        "estimated": "estimated",
        "unknown": "unknown",
    }
    blockers = []
    body_checks = []
    building_dependencies = []
    for obj in fixture["objects"]:
        if obj["object_class"] != "building":
            continue
        massing = obj["massing"]
        state = massing.get("height_state")
        if state not in height_state_map:
            raise ValueError(f"Unsupported height_state {state!r} for {obj['object_id']}; refusing implicit promotion")
        status = height_state_map[state]
        height = massing.get("height_m")
        if status == "unknown" and height is not None:
            raise ValueError(f"Unknown height must not carry numeric height_m: {obj['object_id']}")
        if status != "unknown" and (not isinstance(height, (int, float)) or not math.isfinite(height) or height <= 0):
            raise ValueError(f"Known/estimated height must be finite and > 0: {obj['object_id']}")
        blockers.append(Blocker(
            blocker_id=obj["object_id"],
            footprint=shape({"type": obj["geometry_type"], "coordinates": obj["coordinates"]}),
            base_elevation_m=massing["base_elevation_m"], height_m=height,
            height_status=status,
            revision=f'{obj["geometry_revision"]}|{massing["height_revision"]}|{obj["placement_revision"]}|{obj.get("body_revision")}',
        ))
        body_checks.append(body_checks_for(obj, frame["coordinate_frame_id"]))
        body = obj.get("representations", {}).get("body_3d", {})
        body_geometry = body.get("geometry")
        footprint_geometry = {"type": obj["geometry_type"], "coordinates": obj["coordinates"]}
        building_dependencies.append({
            "object_id": obj["object_id"],
            "geometry_revision": obj["geometry_revision"],
            "geometry_content_hash_sha256": canonical_hash(footprint_geometry),
            "placement_revision": obj.get("placement_revision"),
            "body_revision": obj.get("body_revision"),
            "body_ref": body.get("ref"),
            "body_state": body.get("state"),
            "body_representation_kind": body.get("representation_kind"),
            "body_geometry_content_hash_sha256": canonical_hash(body_geometry) if body_geometry is not None else None,
            "height_revision": massing.get("height_revision"),
            "height_state": state,
            "height_value_m": height,
            "base_elevation_m": massing.get("base_elevation_m"),
            "base_elevation_state": massing.get("base_elevation_state"),
        })

    bearing = frame["project_y_axis_true_north_bearing_deg"]
    context_complete = site["context_coverage_status"] == "complete_for_declared_synthetic_fixture"
    sensor_hash_payload = [{k: s[k] for k in ("sensor_id", "sensor_grid_revision", "x_m", "y_m", "z_m")} for s in fixture["sensors"]]
    terrain = site["terrain"]
    manifest = {
        "site_model_id": site["site_model_id"],
        "site_model_revision": site["site_model_revision"],
        "fixture_id": fixture["fixture_id"],
        "fixture_revision": fixture["fixture_revision"],
        "coordinate_frame_id": frame["coordinate_frame_id"],
        "coordinate_state": frame["coordinate_state"],
        "coordinate_units": frame["units"],
        "project_y_axis_true_north_bearing_deg": bearing,
        "north_bearing_state": frame["north_bearing_state"],
        "site_latitude_deg": location["latitude_deg"],
        "site_longitude_deg": location["longitude_deg"],
        "local_datetime_iso_with_utc_offset": site["local_datetime_iso_with_utc_offset"],
        "terrain_revision": terrain["revision"],
        "terrain_content_hash_sha256": canonical_hash(terrain),
        "context_coverage_status": site["context_coverage_status"],
        "sensor_grid_revisions": sorted({s["sensor_grid_revision"] for s in fixture["sensors"]}),
        "sensor_grid_content_hash_sha256": canonical_hash(sensor_hash_payload),
        "solar_position_method": solar.algorithm,
        "solar_position_method_version": "local-probe-0.2.1",
        "shadow_method": "2D ray segment against stored vertical-prism mesh/footprint contract",
        "shadow_method_version": "local-probe-0.2.1",
        "metric_definition": fixture["metric_definition"],
        "blockers": building_dependencies,
    }
    fingerprint = dependency_fingerprint(manifest)

    results = []
    for sensor in fixture["sensors"]:
        assessment = assess_sensor_direct_sun(
            (sensor["x_m"], sensor["y_m"]), sensor["z_m"], solar, blockers,
            project_y_axis_bearing_deg=bearing, context_complete=context_complete,
        )
        results.append({
            "sensor_id": sensor["sensor_id"],
            "expected_status": sensor["expected_status"],
            "actual": assessment,
            "passed": assessment["status"] == sensor["expected_status"] and assessment["blocker_ids"] == sensor["expected_blocker_ids"],
        })

    def fingerprint_with(mutator):
        mutated = deepcopy(manifest)
        mutator(mutated)
        return result_is_stale(fingerprint, mutated)

    stale_checks = {
        "same_manifest_not_stale": not result_is_stale(fingerprint, manifest),
        "height_revision_change_stale": fingerprint_with(lambda m: m["blockers"][0].update(height_revision="height-r2")),
        "height_value_change_without_revision_bump_stale": fingerprint_with(lambda m: m["blockers"][0].update(height_value_m=5.0)),
        "height_state_change_without_revision_bump_stale": fingerprint_with(lambda m: m["blockers"][0].update(height_state="estimated")),
        "base_elevation_change_without_revision_bump_stale": fingerprint_with(lambda m: m["blockers"][0].update(base_elevation_m=1.0)),
        "body_geometry_change_without_revision_bump_stale": fingerprint_with(lambda m: m["blockers"][0].update(body_geometry_content_hash_sha256="mutated-body-hash")),
        "footprint_geometry_change_without_revision_bump_stale": fingerprint_with(lambda m: m["blockers"][0].update(geometry_content_hash_sha256="mutated-footprint-hash")),
        "north_bearing_change_stale": fingerprint_with(lambda m: m.update(project_y_axis_true_north_bearing_deg=90.0)),
        "timestamp_change_stale": fingerprint_with(lambda m: m.update(local_datetime_iso_with_utc_offset="2025-11-15T12:00:00+10:00")),
        "solar_method_version_change_stale": fingerprint_with(lambda m: m.update(solar_position_method_version="local-probe-0.2.2")),
        "shadow_method_version_change_stale": fingerprint_with(lambda m: m.update(shadow_method_version="local-probe-0.2.2")),
        "sensor_grid_content_change_stale": fingerprint_with(lambda m: m.update(sensor_grid_content_hash_sha256="mutated-sensor-grid-hash")),
        "terrain_content_change_stale": fingerprint_with(lambda m: m.update(terrain_content_hash_sha256="mutated-terrain-hash")),
        "context_coverage_change_stale": fingerprint_with(lambda m: m.update(context_coverage_status="incomplete")),
    }

    rotated_results = []
    for sensor in fixture["sensors"]:
        assessment = assess_sensor_direct_sun(
            (sensor["x_m"], sensor["y_m"]), sensor["z_m"], solar, blockers,
            project_y_axis_bearing_deg=90.0, context_complete=context_complete,
        )
        rotated_results.append({"sensor_id": sensor["sensor_id"], "status": assessment["status"], "sunlit": assessment["sunlit"], "blocker_ids": assessment["blocker_ids"]})
    original_signature = [(r["sensor_id"], r["actual"]["status"], r["actual"]["blocker_ids"]) for r in results]
    rotated_signature = [(r["sensor_id"], r["status"], r["blocker_ids"]) for r in rotated_results]
    rotation_results_changed = original_signature != rotated_signature

    all_passed = (
        all(r["passed"] for r in results)
        and all(c["passed"] for c in body_checks)
        and all(stale_checks.values())
        and rotation_results_changed
    )
    result = {
        "run_id": "RUN-E2E-003",
        "benchmark_id": "LOCAL-E2E-ENV-002",
        "fixture_id": fixture["fixture_id"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": "passed_with_scope_limits" if all_passed else "failed",
        "solar_position": {"elevation_deg": solar.elevation_deg, "azimuth_deg_from_true_north_clockwise": solar.azimuth_deg_from_true_north_clockwise, "algorithm": solar.algorithm},
        "dependency_manifest": manifest,
        "dependency_fingerprint_sha256": fingerprint,
        "sensor_results": results,
        "stored_body_mesh_checks": body_checks,
        "revision_checks": stale_checks,
        "north_rotation_probe": {"changed_bearing_deg": 90.0, "dependency_stale": stale_checks["north_bearing_change_stale"], "results_changed": rotation_results_changed, "sensor_results": rotated_results},
        "limits": [
            "Synthetic fixture only; the body mesh is a simple synthetic vertical-prism mesh, not IFC or a validated solid-kernel result.",
            "The sun/shadow algorithm is a low-precision benchmark probe, not a validated professional solar simulation engine.",
            "No real raster-to-Trace, road generation, building regularization, IFC export, or independent solar engine was run.",
            "The location is a solar-position reference only; local site geometry is not georeferenced.",
            "Passing proves declared fixture/interface invariants only, not real-site quality, professional design correctness, or regulatory compliance.",
        ],
    }
    out = ROOT / "local-e2e-fixture-env-002.json"
    out.write_text(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output": str(out), "status": result["status"], "sensor_passes": sum(r["passed"] for r in results), "sensor_total": len(results), "body_mesh_passes": sum(c["passed"] for c in body_checks), "body_mesh_total": len(body_checks), "revision_checks": stale_checks, "north_rotation_results_changed": rotation_results_changed}, ensure_ascii=False, indent=2))
    return result


if __name__ == "__main__":
    result = run()
    raise SystemExit(0 if result["status"] == "passed_with_scope_limits" else 1)

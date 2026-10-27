"""Translate the shared synthetic fixture into a provisional CAD-IR JSON instance."""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json

ROOT = Path(__file__).resolve().parent
fixture = json.loads((ROOT / "site-fixture-v0.2.json").read_text(encoding="utf-8"))
site = fixture["site"]
frame = site["coordinate_frame"]
objects = []


def make_object(object_id, object_class, geometry_revision, geometry_data, layer_key, *, locked=False,
                source_trace_ref=None, source_trace_revision=None, semantic_properties=None,
                massing_parameters=None, placement_ref=None, provenance=None):
    return {
        "object_id": object_id,
        "object_class": object_class,
        "geometry_ref": f'fixture://{fixture["fixture_id"]}/{object_id}/{geometry_revision}',
        "geometry_revision": geometry_revision,
        "geometry_data": geometry_data,
        "geometry_content_hash_sha256": hashlib.sha256(json.dumps(geometry_data, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest(),
        "semantic_properties": semantic_properties or {},
        "source_trace_ref": source_trace_ref,
        "source_trace_revision": source_trace_revision,
        "locked": locked,
        "layer_key": layer_key,
        "style_key": None,
        "block_key": None,
        "placement_ref": placement_ref,
        "massing_parameters": massing_parameters or {
            "height": {"value": None, "unit": "m", "state": "unknown", "source_ref": None},
            "floors": {"value": None, "state": "unknown", "source_ref": None},
            "floor_height": {"value": None, "unit": "m", "state": "unknown", "source_ref": None},
        },
        "representations": {
            "dxf": {"state": "not_compiled", "output_entity_refs": []},
            "ifc_footprint": {"state": "missing", "representation_ref": None},
            "ifc_body": {"state": "missing", "representation_ref": None},
        },
        "dependencies": {"derived_from": [source_trace_ref] if source_trace_ref else [], "stale_reasons": [], "rebuild_required": []},
        "validation": {
            "geometry": {"state": "not_run", "findings": []},
            "topology": {"state": "not_run", "findings": []},
            "profile": {"state": "not_run", "findings": []},
            "file_integrity": {"state": "not_run", "findings": []},
            "roundtrip": {"state": "not_run", "findings": []},
            "independent_application": {"state": "not_run", "findings": []},
        },
        "provenance": {
            "created_by": "fixture_to_cad_ir.py",
            "source_version": fixture["fixture_revision"],
            "algorithm_and_version": "fixture adapter 0.2.0",
            "parameters": {},
            "change_proposal_ref": None,
            "reviewer_decision_ref": None,
            "source_provenance": provenance or {},
        },
    }

boundary = site["site_boundary"]
objects.append(make_object(
    boundary["object_id"], "site_boundary", boundary["geometry_revision"],
    {"type": boundary["geometry_type"], "coordinates": boundary["coordinates"]},
    "A-SITE-BOUNDARY", locked=boundary["locked"], provenance=boundary["provenance"],
))

layer_for_class = {
    "road_corridor": "C-ROAD-CENTER",
    "green_space": "L-GREEN",
    "building": "A-BUILDING-OUTLINE",
}
ir_class_for = {"road_corridor": "road_centerline", "green_space": "green_space", "building": "building_footprint"}
for obj in fixture["objects"]:
    if obj["geometry_type"] == "LineString":
        geometry_data = {"type": "LineString", "coordinates": obj["coordinates"]}
    elif obj["geometry_type"] == "Polygon":
        geometry_data = {"type": "Polygon", "coordinates": obj["coordinates"]}
    else:
        raise ValueError(f'unsupported fixture geometry type: {obj["geometry_type"]}')
    semantic = {"fixture_evidence_state": obj.get("evidence_state"), "fixture_review_state": obj.get("review_state")}
    massing = {"height": {"value": None, "unit": "m", "state": "unknown", "source_ref": None},
               "floors": {"value": None, "state": "unknown", "source_ref": None},
               "floor_height": {"value": None, "unit": "m", "state": "unknown", "source_ref": None}}
    placement_ref = None
    if obj["object_class"] == "building":
        m = obj["massing"]
        semantic.update({"height_state": m["height_state"], "height_revision": m["height_revision"], "base_elevation_state": m["base_elevation_state"], "body_fixture_state": obj.get("representations", {}).get("body_3d", {}).get("state", "not_declared")})
        massing = {
            "height": {"value": m["height_m"], "unit": "m", "state": "proposed" if m["height_state"] == "confirmed_within_synthetic_fixture" else m["height_state"], "source_ref": f'fixture://{fixture["fixture_id"]}/{obj["object_id"]}/massing'},
            "floors": {"value": m["floors"], "state": m["floors_state"], "source_ref": None},
            "floor_height": {"value": None, "unit": "m", "state": "unknown", "source_ref": None},
        }
        placement_ref = f'{obj["object_id"]}/{obj["placement_revision"]}'
    objects.append(make_object(
        obj["object_id"], ir_class_for[obj["object_class"]], obj["geometry_revision"], geometry_data,
        layer_for_class[obj["object_class"]], source_trace_ref=obj.get("source_trace_stub", {}).get("trace_id"),
        source_trace_revision=obj.get("source_trace_stub", {}).get("revision"), semantic_properties=semantic,
        massing_parameters=massing, placement_ref=placement_ref, provenance=obj["provenance"],
    ))

for sensor in fixture["sensors"]:
    geometry_data = {"type": "Point", "coordinates": [sensor["x_m"], sensor["y_m"], sensor["z_m"]]}
    objects.append(make_object(
        sensor["sensor_id"], "other", sensor["sensor_grid_revision"], geometry_data, "A-ENV-SENSOR",
        semantic_properties={"subclass": "environment_sensor", "expected_status": sensor["expected_status"], "expected_blocker_ids": sensor["expected_blocker_ids"]},
        provenance={"operation": "synthetic_fixture_creation", "reason": "Environment test sensor; not a surveyed location."},
    ))

cad_ir = {
    "schema": "cad_ir_contract_r0_v0.1",
    "instance_version": "0.2.0",
    "status": "synthetic_fixture_instance",
    "source_fixture_id": fixture["fixture_id"],
    "source_fixture_revision": fixture["fixture_revision"],
    "project": {
        "project_id": site["site_model_id"],
        "coordinate_frame_ref": frame["coordinate_frame_id"],
        "coordinate_state": frame["coordinate_state"],
        "units": frame["units"],
        "profile_ref": "SYNTHETIC-SITE-DXF-PROFILE-001",
        "profile_version": "0.1.0",
        "design_stage": "synthetic integration fixture; not for design approval",
        "source_refs": [f'fixture://{fixture["fixture_id"]}'],
        "north_bearing_deg": frame["project_y_axis_true_north_bearing_deg"],
        "site_location_for_solar_test_only": site["location_for_solar_test_only"],
        "local_datetime_iso_with_utc_offset": site["local_datetime_iso_with_utc_offset"],
        "terrain_revision": site["terrain"]["revision"],
        "context_coverage_status": site["context_coverage_status"],
    },
    "objects": objects,
    "export_targets": {
        "dxf": {"version": "R2010", "profile_ref": "SYNTHETIC-SITE-DXF-PROFILE-001", "unit_policy": "metre / INSUNITS=6"},
        "ifc": {"schema_version": "IFC4", "profile_ref": "UNSELECTED-NOT-EXECUTED", "representation_policy": "not generated in this benchmark"},
    },
    "validation_policy": {
        "source_trace_is_immutable": True,
        "unknown_values_must_not_be_silently_promoted": True,
        "never_collapse_scopes": ["geometry", "topology", "profile", "file_integrity", "roundtrip", "independent_application", "domain_compliance"],
    },
    "created_at_utc": datetime.now(timezone.utc).isoformat(),
}
out = ROOT / "site-fixture-cad-ir-v0.2.json"
out.write_text(json.dumps(cad_ir, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps({"output": str(out), "objects": len(objects), "building_objects": sum(o["object_class"] == "building_footprint" for o in objects), "status": cad_ir["status"]}, ensure_ascii=False, indent=2))

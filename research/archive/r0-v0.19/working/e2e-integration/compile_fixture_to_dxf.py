"""Compile provisional CAD-IR from E2E-FIXTURE-001 to editable DXF and re-read it.

Synthetic Profile only. Same-library round-trip only; not third-party CAD QA.
"""
from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import hashlib
import json
import sys

import ezdxf

ROOT = Path(__file__).resolve().parent
cad_ir = json.loads((ROOT / "site-fixture-cad-ir-v0.1.json").read_text(encoding="utf-8"))
env_result = json.loads((ROOT / "local-e2e-fixture-env-001.json").read_text(encoding="utf-8"))
assert cad_ir["source_fixture_id"] == env_result["fixture_id"]

out_path = ROOT / "site-fixture-v0.1.dxf"
manifest_path = ROOT / "site-fixture-v0.1-dxf-manifest.json"
doc = ezdxf.new(cad_ir["export_targets"]["dxf"]["version"])
doc.header["$INSUNITS"] = ezdxf.units.M

layer_specs = {
    "A-SITE-BOUNDARY": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 50},
    "C-ROAD-CENTER": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 18},
    "L-GREEN": {"color": 94, "linetype": "CONTINUOUS", "lineweight": 13},
    "A-BUILDING-OUTLINE": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 35},
    "A-ENV-SENSOR": {"color": 2, "linetype": "CONTINUOUS", "lineweight": 13},
}
for name, attrs in layer_specs.items():
    doc.layers.new(name, dxfattribs=attrs)
doc.appids.add("DESIGN_GRADE")
msp = doc.modelspace()
expected_objects: dict[str, dict] = {}


def xdata(entity, obj: dict, geometry_payload: dict) -> str:
    geometry_hash = hashlib.sha256(json.dumps(geometry_payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")).hexdigest()
    entity.set_xdata("DESIGN_GRADE", [
        (1000, obj["object_id"]), (1000, obj["object_class"]), (1000, obj["geometry_revision"]), (1000, geometry_hash),
    ])
    return geometry_hash


for obj in cad_ir["objects"]:
    object_id = obj["object_id"]
    geometry = obj["geometry_data"]
    geometry_type = geometry["type"]
    layer = obj["layer_key"]
    if layer not in layer_specs:
        raise ValueError(f"No synthetic DXF layer mapping for {object_id}: {layer}")

    if geometry_type in {"Polygon", "LineString"}:
        closed = geometry_type == "Polygon"
        coords = geometry["coordinates"][0] if closed else geometry["coordinates"]
        vertices = [tuple(xy[:2]) for xy in coords]
        if closed and len(vertices) > 1 and vertices[-1] == vertices[0]:
            vertices = vertices[:-1]
        entity = msp.add_lwpolyline(vertices, close=closed, dxfattribs={"layer": layer})
        geom_hash = xdata(entity, obj, geometry)
        if obj.get("geometry_content_hash_sha256") != geom_hash:
            raise ValueError(f"CAD-IR geometry content hash mismatch for {object_id}")
        expected_objects[object_id] = {
            "object_class": obj["object_class"], "geometry_revision": obj["geometry_revision"],
            "geometry_hash": geom_hash, "entity_type": "LWPOLYLINE", "expected_entity_count": 1,
            "expected_vertices": vertices, "closed": closed, "layer": layer,
            "semantic_properties": obj["semantic_properties"], "massing_parameters": obj["massing_parameters"],
        }
    elif geometry_type == "Point":
        point = geometry["coordinates"]
        circle = msp.add_circle((point[0], point[1]), radius=0.25, dxfattribs={"layer": layer})
        geom_hash = xdata(circle, obj, geometry)
        if obj.get("geometry_content_hash_sha256") != geom_hash:
            raise ValueError(f"CAD-IR geometry content hash mismatch for {object_id}")
        label = msp.add_text(object_id, height=0.35, dxfattribs={"layer": layer})
        label.set_placement((point[0] + 0.3, point[1] + 0.3))
        xdata(label, obj, geometry)
        expected_objects[object_id] = {
            "object_class": obj["object_class"], "geometry_revision": obj["geometry_revision"],
            "geometry_hash": geom_hash, "entity_type": "CIRCLE+TEXT", "expected_entity_count": 2,
            "point": point, "layer": layer, "semantic_properties": obj["semantic_properties"],
        }
    else:
        raise ValueError(f"Unsupported CAD-IR geometry type for {object_id}: {geometry_type}")

doc.saveas(out_path)
readback = ezdxf.readfile(out_path)
auditor = readback.audit()
actual_map: dict[str, list[dict]] = {}
for entity in readback.modelspace():
    if not entity.has_xdata("DESIGN_GRADE"):
        continue
    tags = entity.get_xdata("DESIGN_GRADE")
    values = [tag.value for tag in tags if tag.code == 1000]
    if len(values) < 4:
        continue
    object_id, object_class, revision, geometry_hash = values[:4]
    actual_map.setdefault(object_id, []).append({
        "handle": entity.dxf.handle, "type": entity.dxftype(), "layer": entity.dxf.layer,
        "object_class": object_class, "geometry_revision": revision, "geometry_hash": geometry_hash,
    })

mapping_checks = {}
for object_id, expected in expected_objects.items():
    actual = actual_map.get(object_id, [])
    check = {
        "expected_entity_count": expected["expected_entity_count"],
        "actual_entity_count": len(actual),
        "identity_count_pass": len(actual) == expected["expected_entity_count"],
        "class_pass": bool(actual) and all(e["object_class"] == expected["object_class"] for e in actual),
        "revision_pass": bool(actual) and all(e["geometry_revision"] == expected["geometry_revision"] for e in actual),
        "geometry_hash_pass": bool(actual) and all(e["geometry_hash"] == expected["geometry_hash"] for e in actual),
        "layer_pass": bool(actual) and all(e["layer"] == expected["layer"] for e in actual),
        "entities": actual,
    }
    if expected["entity_type"] == "LWPOLYLINE" and actual:
        entity = readback.entitydb[actual[0]["handle"]]
        read_vertices = [tuple(point[:2]) for point in entity.get_points("xy")]
        check["vertex_coordinates_pass"] = read_vertices == [tuple(p) for p in expected["expected_vertices"]]
        check["closed_pass"] = bool(entity.closed) == expected["closed"]
    if expected["entity_type"] == "CIRCLE+TEXT" and actual:
        circle_entity = next((readback.entitydb[e["handle"]] for e in actual if e["type"] == "CIRCLE"), None)
        check["sensor_xy_pass"] = circle_entity is not None and [round(circle_entity.dxf.center.x, 9), round(circle_entity.dxf.center.y, 9)] == expected["point"][:2]
    mapping_checks[object_id] = check

all_checks = all(
    c["identity_count_pass"] and c["class_pass"] and c["revision_pass"] and c["geometry_hash_pass"] and c["layer_pass"]
    and c.get("vertex_coordinates_pass", True) and c.get("closed_pass", True) and c.get("sensor_xy_pass", True)
    for c in mapping_checks.values()
)
manifest = {
    "benchmark_id": "LOCAL-E2E-CAD-001",
    "run_id": "RUN-E2E-002",
    "fixture_id": cad_ir["source_fixture_id"],
    "fixture_revision": cad_ir["source_fixture_revision"],
    "cad_ir_instance": "site-fixture-cad-ir-v0.1.json",
    "cad_ir_schema": cad_ir["schema"],
    "generated_at_utc": datetime.now(timezone.utc).isoformat(),
    "status": "passed_with_scope_limits" if all_checks and not auditor.errors else "failed",
    "environment": {"python_version": sys.version.split()[0], "ezdxf_version": ezdxf.__version__},
    "output_dxf": out_path.name,
    "dxf_version": readback.dxfversion,
    "insunits": readback.header.get("$INSUNITS"),
    "entity_count": len(list(readback.modelspace())),
    "audit_error_count": len(auditor.errors),
    "audit_fix_count": len(auditor.fixes),
    "environment_result_ref": "local-e2e-fixture-env-001.json",
    "environment_dependency_fingerprint_sha256": env_result["dependency_fingerprint_sha256"],
    "object_mapping_checks": mapping_checks,
    "all_identity_revision_geometry_checks_pass": all_checks,
    "limits": [
        "Synthetic Profile only; no design-office or national standard compliance claim.",
        "Same-library ezdxf write/read only; no LibreCAD/AutoCAD/FreeCAD third-party round-trip.",
        "The DXF contains editable 2D entities; building height/massing semantics remain in CAD-IR and the sidecar manifest, not a 3D solid or IFC model.",
        "Passing this adapter does not prove the road, building, or site design is professionally correct.",
    ],
}
manifest_path = ROOT / "site-fixture-v0.1-dxf-manifest.json"
manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
print(json.dumps({"output_dxf": str(out_path), "manifest": str(manifest_path), "status": manifest["status"], "object_ids": len(mapping_checks), "entity_count": manifest["entity_count"], "audit_errors": manifest["audit_error_count"], "identity_geometry_checks_pass": all_checks}, ensure_ascii=False, indent=2))
raise SystemExit(0 if manifest["status"] == "passed_with_scope_limits" else 1)

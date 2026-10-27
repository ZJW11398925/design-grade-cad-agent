"""Compile provisional CAD-IR to a tagged, editable 2D DXF representation.

Synthetic Profile only. Geometry features that cannot be represented safely are
rejected rather than silently dropped. This is not third-party CAD QA.
"""
from __future__ import annotations
from datetime import datetime, timezone
from pathlib import Path
import hashlib, json, math, sys
import ezdxf
from shapely.geometry import shape
from dxf_validator import LAYER_SPECS, validate_dxf_file, canonical_hash

ROOT = Path(__file__).resolve().parent
CAD_IR_PATH = ROOT / "site-fixture-cad-ir-v0.2.json"
ENV_PATH = ROOT / "local-e2e-fixture-env-002.json"
OUT_PATH = ROOT / "site-fixture-v0.2.dxf"
MANIFEST_PATH = ROOT / "site-fixture-v0.2-dxf-manifest.json"
APPID = "DESIGN_GRADE"


def finite_coordinates(value):
    if isinstance(value, (list, tuple)):
        if value and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in value):
            return all(math.isfinite(float(v)) for v in value)
        return all(finite_coordinates(v) for v in value)
    return True


def xdata(entity, obj: dict, source_hash: str, rep_hash: str, entity_role: str, part_index: int, ring_index: int, ring_role: str) -> None:
    entity.set_xdata(APPID, [
        (1000, obj["object_id"]), (1000, obj["object_class"]), (1000, obj["geometry_revision"]),
        (1000, source_hash), (1000, rep_hash), (1000, entity_role), (1000, str(part_index)),
        (1000, str(ring_index)), (1000, ring_role),
    ])


def _add_polyline(msp, obj, source_hash, layer, coords, closed, entity_role, part_index, ring_index, ring_role):
    vertices = [tuple(p[:2]) for p in coords]
    if closed and len(vertices) > 1 and vertices[-1] == vertices[0]:
        vertices = vertices[:-1]
    rep = {"kind": "LWPOLYLINE", "coordinates": [list(p) for p in vertices], "closed": closed, "ring_role": ring_role}
    rep_hash = canonical_hash(rep)
    entity = msp.add_lwpolyline(vertices, close=closed, dxfattribs={"layer": layer})
    xdata(entity, obj, source_hash, rep_hash, entity_role, part_index, ring_index, ring_role)


def compile_fixture_to_dxf(cad_ir_path=CAD_IR_PATH, env_path=ENV_PATH, out_path=OUT_PATH, manifest_path=MANIFEST_PATH):
    cad_ir = json.loads(Path(cad_ir_path).read_text(encoding="utf-8"))
    env_result = json.loads(Path(env_path).read_text(encoding="utf-8"))
    if cad_ir.get("source_fixture_id") != env_result.get("fixture_id"):
        raise ValueError("CAD-IR and environment result do not reference the same fixture")
    if not env_result.get("dependency_fingerprint_sha256"):
        raise ValueError("Environment result is missing dependency fingerprint")

    doc = ezdxf.new(cad_ir["export_targets"]["dxf"]["version"])
    doc.header["$INSUNITS"] = ezdxf.units.M
    for name, attrs in LAYER_SPECS.items():
        doc.layers.new(name, dxfattribs=attrs)
    doc.appids.add(APPID)
    msp = doc.modelspace()
    object_ids = set()

    for obj in cad_ir["objects"]:
        oid = obj["object_id"]
        if oid in object_ids:
            raise ValueError(f"Duplicate object_id in CAD-IR: {oid}")
        object_ids.add(oid)
        geometry = obj["geometry_data"]
        gtype = geometry.get("type")
        coords = geometry.get("coordinates")
        layer = obj["layer_key"]
        if layer not in LAYER_SPECS:
            raise ValueError(f"No synthetic DXF layer mapping for {oid}: {layer}")
        if not finite_coordinates(coords):
            raise ValueError(f"Non-finite geometry coordinate: {oid}")
        geom = shape(geometry)
        if geom.is_empty or not geom.is_valid:
            raise ValueError(f"Invalid/empty CAD-IR geometry: {oid}")
        source_hash = canonical_hash(geometry)
        if obj.get("geometry_content_hash_sha256") != source_hash:
            raise ValueError(f"CAD-IR geometry content hash mismatch for {oid}")

        if gtype == "Polygon":
            if not coords:
                raise ValueError(f"Polygon has no rings: {oid}")
            for ring_index, ring in enumerate(coords):
                if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                    raise ValueError(f"Polygon ring must be closed and have >=4 coordinates: {oid}/{ring_index}")
                role = "outer" if ring_index == 0 else "hole"
                _add_polyline(msp, obj, source_hash, layer, ring, True, "ring", 0, ring_index, role)
        elif gtype == "MultiPolygon":
            for part_index, polygon_rings in enumerate(coords):
                if not polygon_rings:
                    raise ValueError(f"MultiPolygon part has no rings: {oid}/{part_index}")
                for ring_index, ring in enumerate(polygon_rings):
                    if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                        raise ValueError(f"MultiPolygon ring must be closed: {oid}/{part_index}/{ring_index}")
                    role = "outer" if ring_index == 0 else "hole"
                    _add_polyline(msp, obj, source_hash, layer, ring, True, "ring", part_index, ring_index, role)
        elif gtype == "LineString":
            if len(coords) < 2:
                raise ValueError(f"LineString needs at least two coordinates: {oid}")
            _add_polyline(msp, obj, source_hash, layer, coords, False, "line", 0, 0, "line")
        elif gtype == "Point":
            if len(coords) < 2:
                raise ValueError(f"Point needs x/y coordinates: {oid}")
            x, y = float(coords[0]), float(coords[1])
            circle_rep = {"kind": "CIRCLE", "center_xy": [x, y], "radius": 0.25}
            circle = msp.add_circle((x, y), radius=0.25, dxfattribs={"layer": layer})
            xdata(circle, obj, source_hash, canonical_hash(circle_rep), "point_marker", 0, 0, "marker")
            text_rep = {"kind": "TEXT", "text": oid, "insert_xy": [x + 0.3, y + 0.3], "height": 0.35}
            label = msp.add_text(oid, height=0.35, dxfattribs={"layer": layer})
            label.set_placement((x + 0.3, y + 0.3))
            xdata(label, obj, source_hash, canonical_hash(text_rep), "point_label", 0, 0, "label")
        else:
            raise ValueError(f"Unsupported geometry type in DXF adapter: {gtype}")

    out_path = Path(out_path)
    manifest_path = Path(manifest_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    doc.saveas(out_path)
    validation = validate_dxf_file(out_path, cad_ir, LAYER_SPECS)
    manifest = {
        "benchmark_id": "LOCAL-E2E-CAD-002", "run_id": "RUN-E2E-004",
        "fixture_id": cad_ir["source_fixture_id"], "fixture_revision": cad_ir["source_fixture_revision"],
        "cad_ir_instance": Path(cad_ir_path).name, "cad_ir_schema": cad_ir["schema"],
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "status": validation["status"], "environment": {"python_version": sys.version.split()[0], "ezdxf_version": ezdxf.__version__},
        "output_dxf": out_path.name, "dxf_validation": validation,
        "environment_result_ref": Path(env_path).name,
        "environment_dependency_fingerprint_sha256": env_result["dependency_fingerprint_sha256"],
        "limits": [
            "Synthetic Profile only; no design-office or national standard compliance claim.",
            "The validator is a separate code path but still uses ezdxf; no LibreCAD/AutoCAD/FreeCAD third-party round-trip.",
            "The DXF is 2D plan linework. Building height/massing semantics remain in CAD-IR and the sidecar manifest, not a 3D solid or IFC model.",
            "Polygon/MultiPolygon rings are separate tagged polylines; ring roles are metadata, not filled DXF region semantics.",
            "Passing this adapter does not prove the road, building, or site design is professionally correct.",
        ],
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps({"output_dxf": str(out_path), "manifest": str(manifest_path), "status": validation["status"], "objects": len(cad_ir["objects"]), "entity_count": validation["entity_count"], "expected_entity_count": validation["expected_entity_count"], "audit_errors": validation["audit_error_count"], "audit_fixes": validation["audit_fix_count"], "layers_pass": validation["layers_pass"], "units_pass": validation["units_pass"], "all_object_checks_pass": validation["all_object_checks_pass"]}, ensure_ascii=False, indent=2))
    return manifest


if __name__ == "__main__":
    result = compile_fixture_to_dxf()
    raise SystemExit(0 if result["status"] == "passed_with_scope_limits" else 1)

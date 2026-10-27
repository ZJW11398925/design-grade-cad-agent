"""Independent DXF artifact validator for the synthetic CAD-IR adapter.

This validates the declared synthetic profile and representation mapping only. It is
not an independent CAD application, professional-design, or legal-compliance check.
"""
from __future__ import annotations
import hashlib, json, math
from pathlib import Path
from typing import Any
import ezdxf
from shapely.geometry import shape, Polygon

LAYER_SPECS = {
    "A-SITE-BOUNDARY": {"color": 1, "linetype": "CONTINUOUS", "lineweight": 50},
    "C-ROAD-CENTER": {"color": 3, "linetype": "CONTINUOUS", "lineweight": 18},
    "L-GREEN": {"color": 94, "linetype": "CONTINUOUS", "lineweight": 13},
    "A-BUILDING-OUTLINE": {"color": 7, "linetype": "CONTINUOUS", "lineweight": 35},
    "A-ENV-SENSOR": {"color": 2, "linetype": "CONTINUOUS", "lineweight": 13},
}
APPID = "DESIGN_GRADE"


def canonical_hash(value: Any) -> str:
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode("utf-8")).hexdigest()


def _finite_coords(coords: Any) -> bool:
    if isinstance(coords, (list, tuple)):
        if coords and all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in coords):
            return all(math.isfinite(float(v)) for v in coords)
        return all(_finite_coords(v) for v in coords)
    return True


def _expected_entities(obj: dict) -> list[dict]:
    geometry = obj["geometry_data"]
    gtype, coords = geometry["type"], geometry["coordinates"]
    layer = obj["layer_key"]
    source_hash = canonical_hash(geometry)
    if obj.get("geometry_content_hash_sha256") != source_hash:
        raise ValueError(f"CAD-IR geometry hash mismatch: {obj['object_id']}")
    if not _finite_coords(coords):
        raise ValueError(f"Non-finite geometry coordinate: {obj['object_id']}")
    geom = shape(geometry)
    if geom.is_empty or not geom.is_valid:
        raise ValueError(f"Invalid/empty geometry in CAD-IR: {obj['object_id']}")

    expected = []
    if gtype == "Polygon":
        rings = coords
        if not rings:
            raise ValueError(f"Polygon has no rings: {obj['object_id']}")
        for ring_index, ring in enumerate(rings):
            if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                raise ValueError(f"Polygon ring must be closed and have >=4 coordinates: {obj['object_id']}/{ring_index}")
            vertices = [list(p[:2]) for p in ring[:-1]]
            role = "outer" if ring_index == 0 else "hole"
            rep = {"kind": "LWPOLYLINE", "coordinates": vertices, "closed": True, "ring_role": role}
            expected.append({"entity_role": "ring", "part_index": 0, "ring_index": ring_index, "ring_role": role, "entity_type": "LWPOLYLINE", "layer": layer, "source_hash": source_hash, "representation_hash": canonical_hash(rep), "vertices": vertices, "closed": True})
    elif gtype == "MultiPolygon":
        for part_index, polygon_rings in enumerate(coords):
            if not polygon_rings:
                raise ValueError(f"MultiPolygon part has no rings: {obj['object_id']}/{part_index}")
            for ring_index, ring in enumerate(polygon_rings):
                if len(ring) < 4 or ring[0][:2] != ring[-1][:2]:
                    raise ValueError(f"MultiPolygon ring must be closed: {obj['object_id']}/{part_index}/{ring_index}")
                vertices = [list(p[:2]) for p in ring[:-1]]
                role = "outer" if ring_index == 0 else "hole"
                rep = {"kind": "LWPOLYLINE", "coordinates": vertices, "closed": True, "ring_role": role}
                expected.append({"entity_role": "ring", "part_index": part_index, "ring_index": ring_index, "ring_role": role, "entity_type": "LWPOLYLINE", "layer": layer, "source_hash": source_hash, "representation_hash": canonical_hash(rep), "vertices": vertices, "closed": True})
    elif gtype == "LineString":
        if len(coords) < 2:
            raise ValueError(f"LineString needs at least two coordinates: {obj['object_id']}")
        vertices = [list(p[:2]) for p in coords]
        rep = {"kind": "LWPOLYLINE", "coordinates": vertices, "closed": False, "ring_role": "line"}
        expected.append({"entity_role": "line", "part_index": 0, "ring_index": 0, "ring_role": "line", "entity_type": "LWPOLYLINE", "layer": layer, "source_hash": source_hash, "representation_hash": canonical_hash(rep), "vertices": vertices, "closed": False})
    elif gtype == "Point":
        if len(coords) < 2:
            raise ValueError(f"Point needs x/y coordinates: {obj['object_id']}")
        x, y = float(coords[0]), float(coords[1])
        circle_rep = {"kind": "CIRCLE", "center_xy": [x, y], "radius": 0.25}
        text_rep = {"kind": "TEXT", "text": obj["object_id"], "insert_xy": [x + 0.3, y + 0.3], "height": 0.35}
        expected.extend([
            {"entity_role": "point_marker", "part_index": 0, "ring_index": 0, "ring_role": "marker", "entity_type": "CIRCLE", "layer": layer, "source_hash": source_hash, "representation_hash": canonical_hash(circle_rep), "center_xy": [x, y], "radius": 0.25},
            {"entity_role": "point_label", "part_index": 0, "ring_index": 0, "ring_role": "label", "entity_type": "TEXT", "layer": layer, "source_hash": source_hash, "representation_hash": canonical_hash(text_rep), "text": obj["object_id"], "insert_xy": [x + 0.3, y + 0.3], "height": 0.35},
        ])
    else:
        raise ValueError(f"Unsupported geometry type in DXF adapter: {gtype}")
    return expected


def validate_dxf_file(dxf_path: str | Path, cad_ir: dict, layer_specs: dict | None = None) -> dict:
    layer_specs = layer_specs or LAYER_SPECS
    doc = ezdxf.readfile(str(dxf_path))
    auditor = doc.audit()
    expected_version = cad_ir["export_targets"]["dxf"]["version"]
    expected_insunits = ezdxf.units.M
    version_pass = doc.dxfversion == acad_release_to_dxf(expected_version)
    units_pass = doc.header.get("$INSUNITS") == expected_insunits

    layer_checks = {}
    for name, spec in layer_specs.items():
        layer = doc.layers.get(name) if name in doc.layers else None
        layer_checks[name] = {
            "exists": layer is not None,
            "color_pass": layer is not None and layer.dxf.color == spec["color"],
            "linetype_pass": layer is not None and layer.dxf.linetype == spec["linetype"],
            "lineweight_pass": layer is not None and layer.dxf.lineweight == spec["lineweight"],
        }
        layer_checks[name]["passed"] = all(layer_checks[name][k] for k in ("exists", "color_pass", "linetype_pass", "lineweight_pass"))

    expected_by_object = {}
    for obj in cad_ir["objects"]:
        oid = obj["object_id"]
        if oid in expected_by_object:
            raise ValueError(f"Duplicate CAD-IR object_id: {oid}")
        if obj["layer_key"] not in layer_specs:
            raise ValueError(f"No profile layer mapping for {oid}: {obj['layer_key']}")
        expected_by_object[oid] = _expected_entities(obj)

    actual_by_object: dict[str, list[dict]] = {}
    entity_count = 0
    entities_without_xdata = []
    malformed_xdata = []
    for entity in doc.modelspace():
        entity_count += 1
        if not entity.has_xdata(APPID):
            entities_without_xdata.append({"handle": entity.dxf.handle, "type": entity.dxftype(), "layer": entity.dxf.layer})
            continue
        values = [tag.value for tag in entity.get_xdata(APPID) if tag.code == 1000]
        if len(values) != 9:
            malformed_xdata.append({"handle": entity.dxf.handle, "field_count": len(values)})
            continue
        oid, obj_class, revision, source_hash, rep_hash, role, part_s, ring_s, ring_role = values
        try:
            part_index, ring_index = int(part_s), int(ring_s)
        except ValueError:
            malformed_xdata.append({"handle": entity.dxf.handle, "reason": "non-integer part/ring index"})
            continue
        actual_by_object.setdefault(oid, []).append({
            "handle": entity.dxf.handle, "entity_type": entity.dxftype(), "layer": entity.dxf.layer,
            "object_class": obj_class, "geometry_revision": revision, "source_hash": source_hash,
            "representation_hash": rep_hash, "entity_role": role, "part_index": part_index,
            "ring_index": ring_index, "ring_role": ring_role, "entity": entity,
        })

    object_checks = {}
    expected_total = sum(len(items) for items in expected_by_object.values())
    for oid, expected_entities in expected_by_object.items():
        actual_entities = actual_by_object.get(oid, [])
        check_items = []
        for exp in expected_entities:
            match = [a for a in actual_entities if (a["entity_role"], a["part_index"], a["ring_index"], a["ring_role"]) == (exp["entity_role"], exp["part_index"], exp["ring_index"], exp["ring_role"])]
            item = {
                "entity_role": exp["entity_role"], "part_index": exp["part_index"], "ring_index": exp["ring_index"],
                "exactly_one_match": len(match) == 1,
            }
            if len(match) == 1:
                act = match[0]
                entity = act["entity"]
                item["type_pass"] = act["entity_type"] == exp["entity_type"]
                item["class_pass"] = act["object_class"] == next(o["object_class"] for o in cad_ir["objects"] if o["object_id"] == oid)
                item["revision_pass"] = act["geometry_revision"] == next(o["geometry_revision"] for o in cad_ir["objects"] if o["object_id"] == oid)
                item["source_hash_pass"] = act["source_hash"] == exp["source_hash"]
                item["representation_hash_pass"] = act["representation_hash"] == exp["representation_hash"]
                item["layer_pass"] = act["layer"] == exp["layer"]
                if exp["entity_type"] == "LWPOLYLINE":
                    got = [list(p[:2]) for p in entity.get_points("xy")]
                    item["coordinates_pass"] = len(got) == len(exp["vertices"]) and all(all(math.isclose(float(a), float(b), rel_tol=0, abs_tol=1e-9) for a, b in zip(g, e)) for g, e in zip(got, exp["vertices"]))
                    item["closed_pass"] = bool(entity.closed) == exp["closed"]
                elif exp["entity_type"] == "CIRCLE":
                    center = [float(entity.dxf.center.x), float(entity.dxf.center.y)]
                    item["center_pass"] = all(math.isclose(a, b, rel_tol=0, abs_tol=1e-9) for a, b in zip(center, exp["center_xy"]))
                    item["radius_pass"] = math.isclose(float(entity.dxf.radius), exp["radius"], rel_tol=0, abs_tol=1e-9)
                elif exp["entity_type"] == "TEXT":
                    insert = [float(entity.dxf.insert.x), float(entity.dxf.insert.y)]
                    item["text_pass"] = entity.dxf.text == exp["text"]
                    item["insert_pass"] = all(math.isclose(a, b, rel_tol=0, abs_tol=1e-9) for a, b in zip(insert, exp["insert_xy"]))
                    item["height_pass"] = math.isclose(float(entity.dxf.height), exp["height"], rel_tol=0, abs_tol=1e-9)
            else:
                item["type_pass"] = item["class_pass"] = item["revision_pass"] = item["source_hash_pass"] = item["representation_hash_pass"] = item["layer_pass"] = False
            item["passed"] = all(v for k, v in item.items() if k.endswith("_pass") or k == "exactly_one_match")
            check_items.append(item)
        unexpected_roles = [
            {k: a[k] for k in ("entity_role", "part_index", "ring_index", "ring_role", "handle")}
            for a in actual_entities
            if not any((a["entity_role"], a["part_index"], a["ring_index"], a["ring_role"]) == (e["entity_role"], e["part_index"], e["ring_index"], e["ring_role"]) for e in expected_entities)
        ]
        object_checks[oid] = {
            "expected_entity_count": len(expected_entities), "actual_entity_count": len(actual_entities),
            "entity_checks": check_items, "unexpected_entities": unexpected_roles,
            "passed": len(actual_entities) == len(expected_entities) and all(i["passed"] for i in check_items) and not unexpected_roles,
        }

    unknown_object_ids = sorted(set(actual_by_object) - set(expected_by_object))
    all_entities_checked = entity_count == expected_total and not entities_without_xdata and not malformed_xdata and not unknown_object_ids
    all_object_checks = all(x["passed"] for x in object_checks.values())
    layers_pass = all(x["passed"] for x in layer_checks.values())
    audit_pass = len(auditor.errors) == 0 and len(auditor.fixes) == 0
    passed = version_pass and units_pass and layers_pass and audit_pass and all_entities_checked and all_object_checks
    return {
        "status": "passed_with_scope_limits" if passed else "failed",
        "dxf_path": str(dxf_path), "dxf_version": doc.dxfversion, "expected_dxf_version": expected_version,
        "version_pass": version_pass, "insunits": doc.header.get("$INSUNITS"), "expected_insunits": expected_insunits,
        "units_pass": units_pass, "entity_count": entity_count, "expected_entity_count": expected_total,
        "all_entities_checked": all_entities_checked, "entities_without_xdata": entities_without_xdata,
        "malformed_xdata": malformed_xdata, "unknown_object_ids": unknown_object_ids,
        "layer_checks": layer_checks, "layers_pass": layers_pass,
        "audit_error_count": len(auditor.errors), "audit_fix_count": len(auditor.fixes), "audit_pass": audit_pass,
        "object_checks": {oid: {k: v for k, v in check.items() if k != "entity_checks"} | {"entity_checks": check["entity_checks"]} for oid, check in object_checks.items()},
        "all_object_checks_pass": all_object_checks, "passed": passed,
        "limits": ["This is a separate code-path DXF artifact validator, but it still uses ezdxf and is not an independent CAD application.", "DXF plan output projects 3D Point coordinates to XY for marker display; original source geometry hash remains in XDATA and z remains in CAD-IR/sidecar.", "Polygon holes and MultiPolygon parts are emitted as separately tagged outline rings; this preserves ring roles as metadata but does not create a filled DXF region object."],
    }


def acad_release_to_dxf(version: str) -> str:
    mapping = {"R12": "AC1009", "R2000": "AC1015", "R2004": "AC1018", "R2007": "AC1021", "R2010": "AC1024", "R2013": "AC1027", "R2018": "AC1032"}
    if version not in mapping:
        raise ValueError(f"Unsupported declared DXF version: {version}")
    return mapping[version]

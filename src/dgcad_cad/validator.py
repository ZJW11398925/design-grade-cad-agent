from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ezdxf

from dgcad_domain import parse_geometry

from .dxf import XDATA_APPID, _insunits, _polygon_rings, _ring_coords, _source_hash, _rep_hash
from .ir import CadIR, DeliveryProfile


DXF_VERSION_MAP = {"R2010": "AC1024", "R2013": "AC1027", "R2018": "AC1032"}
TOLERANCE = 1e-9
SYSTEM_LAYERS = frozenset({"0", "Defpoints"})
COVERAGE_LIMITS = (
    "modelspace-only synthetic E2E output",
    "no third-party CAD round-trip",
    "no IFC",
    "bulge, width and full LWPOLYLINE semantics deferred to DEV-CAD-003",
)


@dataclass(frozen=True)
class DxfIssue:
    code: str
    severity: str
    object_id: str | None
    message: str
    expected: Any = None
    actual: Any = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "severity": self.severity,
            "object_id": self.object_id,
            "message": self.message,
            "expected": self.expected,
            "actual": self.actual,
        }


@dataclass(frozen=True)
class DxfReadbackResult:
    verdict: str
    issues: tuple[DxfIssue, ...]
    manifest: dict[str, Any]
    coverage_limits: tuple[str, ...] = COVERAGE_LIMITS

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "issues": [issue.to_dict() for issue in self.issues],
            "manifest": self.manifest,
            "coverage_limits": list(self.coverage_limits),
        }


def _expected_entities(cad_ir: CadIR) -> dict[tuple[str, str, int, int], dict[str, Any]]:
    expected: dict[tuple[str, str, int, int], dict[str, Any]] = {}
    for obj in cad_ir.objects:
        geometry = parse_geometry(obj.geometry)
        if obj.representation_kind == "polygon_ring":
            ring_index = 0
            for part_index, ring_role, ring in _polygon_rings(geometry):
                key = (obj.object_id, "polygon_ring", part_index, ring_index)
                expected[key] = {
                    "object_id": obj.object_id,
                    "object_class": obj.object_class,
                    "dxftype": "LWPOLYLINE",
                    "layer": obj.layer_key,
                    "closed": True,
                    "coords": _ring_coords(ring),
                    "ring_role": ring_role,
                    "geometry_revision": obj.geometry_revision,
                    "source_hash": _source_hash(obj),
                    "rep_hash": _rep_hash(obj),
                }
                ring_index += 1
        elif obj.representation_kind == "centerline":
            if geometry.geom_type == "LineString":
                lines = [geometry]
            elif geometry.geom_type == "MultiLineString":
                lines = list(geometry.geoms)
            else:
                raise ValueError(f"unsupported centerline: {geometry.geom_type}")
            for part_index, line in enumerate(lines):
                key = (obj.object_id, "centerline", part_index, 0)
                expected[key] = {
                    "object_id": obj.object_id,
                    "object_class": obj.object_class,
                    "dxftype": "LWPOLYLINE",
                    "layer": obj.layer_key,
                    "closed": False,
                    "coords": [(float(x), float(y)) for x, y in line.coords],
                    "ring_role": "none",
                    "geometry_revision": obj.geometry_revision,
                    "source_hash": _source_hash(obj),
                    "rep_hash": _rep_hash(obj),
                }
        elif obj.representation_kind == "point_marker":
            if geometry.geom_type != "Point":
                raise ValueError(f"unsupported point marker: {geometry.geom_type}")
            x, y = float(geometry.x), float(geometry.y)
            expected[(obj.object_id, "point_marker", 0, 0)] = {
                "object_id": obj.object_id,
                "object_class": obj.object_class,
                "dxftype": "CIRCLE",
                "layer": obj.layer_key,
                "center": (x, y),
                "radius": 0.25,
                "ring_role": "none",
                "geometry_revision": obj.geometry_revision,
                "source_hash": _source_hash(obj),
                "rep_hash": _rep_hash(obj),
            }
            expected[(obj.object_id, "point_marker_label", 0, 0)] = {
                "object_id": obj.object_id,
                "object_class": obj.object_class,
                "dxftype": "TEXT",
                "layer": "ANNO-DIM",
                "text": obj.object_id,
                "height": 0.35,
                "ring_role": "none",
                "geometry_revision": obj.geometry_revision,
                "source_hash": _source_hash(obj),
                "rep_hash": _rep_hash(obj),
            }
    return expected


def _read_xdata(entity) -> tuple[dict[str, Any] | None, str | None]:
    if not entity.has_xdata(XDATA_APPID):
        return None, "MISSING_XDATA"
    values = list(entity.get_xdata(XDATA_APPID))
    if len(values) != 9:
        return None, "MISSING_XDATA"
    try:
        return (
            {
                "object_id": str(values[0][1]),
                "object_class": str(values[1][1]),
                "geometry_revision": int(values[2][1]),
                "source_hash": str(values[3][1]),
                "rep_hash": str(values[4][1]),
                "entity_role": str(values[5][1]),
                "part_index": int(values[6][1]),
                "ring_index": int(values[7][1]),
                "ring_role": str(values[8][1]),
            },
            None,
        )
    except (TypeError, ValueError):
        return None, "MISSING_XDATA"


def _coords_equal(actual, expected) -> bool:
    if len(actual) != len(expected):
        return False
    return all(
        abs(float(a[0]) - float(e[0])) <= TOLERANCE
        and abs(float(a[1]) - float(e[1])) <= TOLERANCE
        for a, e in zip(actual, expected)
    )


def validate_dxf(
    dxf_path: str | Path, cad_ir: CadIR, profile: DeliveryProfile
) -> DxfReadbackResult:
    dxf_path = Path(dxf_path)
    doc = ezdxf.readfile(dxf_path)
    issues: list[DxfIssue] = []
    expected = _expected_entities(cad_ir)

    expected_version = DXF_VERSION_MAP.get(profile.dxf_version)
    if expected_version and doc.dxfversion != expected_version:
        issues.append(
            DxfIssue(
                "DXF_VERSION_MISMATCH",
                "error",
                None,
                "DXF version does not match the delivery profile",
                expected_version,
                doc.dxfversion,
            )
        )
    expected_units = _insunits(profile.units)
    if doc.header.get("$INSUNITS") != expected_units:
        issues.append(
            DxfIssue(
                "UNITS_MISMATCH",
                "error",
                None,
                "INSUNITS does not match the delivery profile",
                expected_units,
                doc.header.get("$INSUNITS"),
            )
        )

    layer_names = {layer.dxf.name for layer in doc.layers}
    allowed_layers = set(profile.layers) | set(SYSTEM_LAYERS)
    for name in sorted(allowed_layers - layer_names):
        issues.append(
            DxfIssue(
                "LAYER_MISSING",
                "error",
                None,
                f"required layer {name} is missing",
            )
        )
    for name in sorted(layer_names - allowed_layers):
        issues.append(
            DxfIssue(
                "UNEXPECTED_LAYER",
                "error",
                None,
                f"unexpected layer {name}",
            )
        )
    for name, spec in profile.layers.items():
        layer = doc.layers.get(name) if name in layer_names else None
        if layer is None:
            continue
        if int(layer.dxf.color) != int(spec.get("color", 7)):
            issues.append(
                DxfIssue(
                    "LAYER_PROPERTY_MISMATCH",
                    "error",
                    None,
                    f"layer {name} color mismatch",
                    spec.get("color"),
                    layer.dxf.color,
                )
            )
        if str(layer.dxf.linetype).upper() != str(
            spec.get("linetype", "CONTINUOUS")
        ).upper():
            issues.append(
                DxfIssue(
                    "LAYER_PROPERTY_MISMATCH",
                    "error",
                    None,
                    f"layer {name} linetype mismatch",
                    spec.get("linetype"),
                    layer.dxf.linetype,
                )
            )
        if int(layer.dxf.lineweight) != int(spec.get("lineweight", -1)):
            issues.append(
                DxfIssue(
                    "LAYER_PROPERTY_MISMATCH",
                    "error",
                    None,
                    f"layer {name} lineweight mismatch",
                    spec.get("lineweight"),
                    layer.dxf.lineweight,
                )
            )

    msp = doc.modelspace()
    seen: set[tuple[str, str, int, int]] = set()
    entities_manifest: list[dict[str, Any]] = []
    for entity in msp:
        xdata, error = _read_xdata(entity)
        if error:
            issues.append(
                DxfIssue(
                    error,
                    "error",
                    None,
                    f"{entity.dxftype()} entity has no complete {XDATA_APPID} XDATA",
                )
            )
            continue
        key = (
            xdata["object_id"],
            xdata["entity_role"],
            xdata["part_index"],
            xdata["ring_index"],
        )
        seen.add(key)
        spec = expected.get(key)
        if spec is None:
            issues.append(
                DxfIssue(
                    "UNEXPECTED_ENTITY",
                    "error",
                    xdata["object_id"],
                    f"entity {key} is not present in CAD-IR",
                )
            )
            continue

        if entity.dxftype() != spec["dxftype"]:
            issues.append(
                DxfIssue(
                    "ENTITY_TYPE_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "entity type does not match CAD-IR",
                    spec["dxftype"],
                    entity.dxftype(),
                )
            )
            continue
        if entity.dxf.layer != spec["layer"]:
            issues.append(
                DxfIssue(
                    "LAYER_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "entity layer does not match CAD-IR",
                    spec["layer"],
                    entity.dxf.layer,
                )
            )
        if xdata["object_class"] != spec["object_class"]:
            issues.append(
                DxfIssue(
                    "OBJECT_CLASS_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA object class does not match CAD-IR",
                    spec["object_class"],
                    xdata["object_class"],
                )
            )
        if xdata["geometry_revision"] != spec["geometry_revision"]:
            issues.append(
                DxfIssue(
                    "REVISION_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA geometry revision does not match CAD-IR",
                    spec["geometry_revision"],
                    xdata["geometry_revision"],
                )
            )
        if xdata["source_hash"] != spec["source_hash"]:
            issues.append(
                DxfIssue(
                    "SOURCE_HASH_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA source hash does not match CAD-IR",
                )
            )
        if xdata["rep_hash"] != spec["rep_hash"]:
            issues.append(
                DxfIssue(
                    "REP_HASH_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA representation hash does not match CAD-IR",
                )
            )
        if xdata["ring_role"] != spec["ring_role"]:
            issues.append(
                DxfIssue(
                    "RING_ROLE_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA ring role does not match CAD-IR",
                    spec["ring_role"],
                    xdata["ring_role"],
                )
            )

        if entity.dxftype() == "LWPOLYLINE":
            actual_coords = [
                (float(point[0]), float(point[1]))
                for point in entity.get_points("xy")
            ]
            if not _coords_equal(actual_coords, spec["coords"]):
                issues.append(
                    DxfIssue(
                        "COORDINATE_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE coordinates do not match CAD-IR",
                        spec["coords"],
                        actual_coords,
                    )
                )
            if bool(entity.closed) != bool(spec["closed"]):
                issues.append(
                    DxfIssue(
                        "CLOSED_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE closed flag does not match CAD-IR",
                        spec["closed"],
                        entity.closed,
                    )
                )
            if abs(float(entity.dxf.elevation)) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "NONZERO_Z",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE elevation is not zero",
                        0.0,
                        entity.dxf.elevation,
                    )
                )
        elif entity.dxftype() == "CIRCLE":
            center = (float(entity.dxf.center.x), float(entity.dxf.center.y))
            if not _coords_equal([center], [spec["center"]]):
                issues.append(
                    DxfIssue(
                        "CIRCLE_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "CIRCLE center does not match CAD-IR",
                        spec["center"],
                        center,
                    )
                )
            if abs(float(entity.dxf.radius) - float(spec["radius"])) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "CIRCLE_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "CIRCLE radius does not match CAD-IR",
                        spec["radius"],
                        entity.dxf.radius,
                    )
                )
        elif entity.dxftype() == "TEXT":
            if entity.dxf.text != spec["text"]:
                issues.append(
                    DxfIssue(
                        "TEXT_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT content does not match CAD-IR",
                        spec["text"],
                        entity.dxf.text,
                    )
                )
            if abs(float(entity.dxf.height) - float(spec["height"])) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "TEXT_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT height does not match CAD-IR",
                        spec["height"],
                        entity.dxf.height,
                    )
                )

        entities_manifest.append(
            {
                "object_id": xdata["object_id"],
                "object_class": xdata["object_class"],
                "entity_role": xdata["entity_role"],
                "part_index": xdata["part_index"],
                "ring_index": xdata["ring_index"],
                "ring_role": xdata["ring_role"],
                "dxftype": entity.dxftype(),
                "layer": entity.dxf.layer,
            }
        )

    for key in sorted(set(expected) - seen):
        issues.append(
            DxfIssue(
                "MISSING_ENTITY",
                "error",
                key[0],
                f"expected entity {key} is missing",
            )
        )

    audit = doc.audit()
    if audit.errors:
        issues.append(
            DxfIssue(
                "AUDIT_ERROR",
                "error",
                None,
                f"ezdxf audit reported {len(audit.errors)} errors",
            )
        )
    if audit.fixes:
        issues.append(
            DxfIssue(
                "AUDIT_FIX",
                "warning",
                None,
                f"ezdxf audit applied {len(audit.fixes)} fixes",
            )
        )

    severities = {issue.severity for issue in issues}
    if "error" in severities:
        verdict = "fail"
    elif "warning" in severities:
        verdict = "pass_with_scope_limits"
    else:
        verdict = "pass"

    manifest = {
        "file": dxf_path.name,
        "sha256": hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
        "dxf_version": doc.dxfversion,
        "insunits": doc.header.get("$INSUNITS"),
        "layer_names": sorted(layer_names),
        "entity_count": len(msp),
        "expected_entity_count": len(expected),
        "object_ids": sorted({obj.object_id for obj in cad_ir.objects}),
        "entities": sorted(
            entities_manifest,
            key=lambda item: (
                item["object_id"],
                item["entity_role"],
                item["part_index"],
                item["ring_index"],
            ),
        ),
        "audit_errors": len(audit.errors),
        "audit_fixes": len(audit.fixes),
        "cad_ir_dependency_fingerprint": cad_ir.dependency_fingerprint,
        "profile_id": profile.profile_id,
        "profile_version": profile.profile_version,
    }
    return DxfReadbackResult(
        verdict=verdict,
        issues=tuple(issues),
        manifest=manifest,
    )

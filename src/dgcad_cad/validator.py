from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import ezdxf

from dgcad_domain import parse_geometry

from .dxf import XDATA_APPID, _insunits, _polygon_rings, _ring_coords, _ring_key, _source_hash, _rep_hash
from .ir import CadIR, DeliveryProfile


DXF_VERSION_MAP = {"R2010": "AC1024", "R2013": "AC1027", "R2018": "AC1032"}
TOLERANCE = 1e-9
SYSTEM_LAYERS = frozenset({"0", "Defpoints"})
COVERAGE_LIMITS = (
    "modelspace-only output",
    "no third-party CAD round-trip",
    "no IFC",
    "full LWPOLYLINE semantics currently expect compiler defaults (zero bulge/width/thickness, +Z extrusion)",
)


ISSUE_CATEGORIES = {
    "DXF_VERSION_MISMATCH": "cad_format_semantics",
    "UNITS_MISMATCH": "cad_format_semantics",
    "LAYER_MISSING": "profile_violation",
    "UNEXPECTED_LAYER": "profile_violation",
    "LAYER_PROPERTY_MISMATCH": "profile_violation",
    "LAYER_MISMATCH": "profile_violation",
    "MISSING_XDATA": "interoperability",
    "UNEXPECTED_ENTITY": "interoperability",
    "MISSING_ENTITY": "interoperability",
    "ENTITY_TYPE_MISMATCH": "cad_format_semantics",
    "OBJECT_CLASS_MISMATCH": "interoperability",
    "REVISION_MISMATCH": "interoperability",
    "SOURCE_HASH_MISMATCH": "interoperability",
    "REP_HASH_MISMATCH": "interoperability",
    "RING_ROLE_MISMATCH": "interoperability",
    "RING_KEY_MISMATCH": "interoperability",
    "COORDINATE_MISMATCH": "cad_format_semantics",
    "CLOSED_MISMATCH": "cad_format_semantics",
    "NONZERO_Z": "cad_format_semantics",
    "CIRCLE_NONZERO_Z": "cad_format_semantics",
    "TEXT_NONZERO_Z": "cad_format_semantics",
    "TEXT_ROTATION_MISMATCH": "profile_violation",
    "TEXT_WIDTH_MISMATCH": "profile_violation",
    "TEXT_ALIGNMENT_MISMATCH": "profile_violation",
    "TEXT_STYLE_MISMATCH": "profile_violation",
    "BLOCK_MISSING": "profile_violation",
    "DIMSTYLE_MISSING": "profile_violation",
    "TEXT_STYLE_MISSING": "profile_violation",
    "ENTITY_COLOR_OVERRIDE": "profile_violation",
    "ENTITY_LINETYPE_OVERRIDE": "profile_violation",
    "ENTITY_LINEWEIGHT_OVERRIDE": "profile_violation",
    "ENTITY_TRUE_COLOR_OVERRIDE": "profile_violation",
    "ENTITY_TRANSPARENCY_OVERRIDE": "profile_violation",
    "BULGE_MISMATCH": "cad_format_semantics",
    "VERTEX_WIDTH_MISMATCH": "cad_format_semantics",
    "CONST_WIDTH_MISMATCH": "cad_format_semantics",
    "THICKNESS_MISMATCH": "cad_format_semantics",
    "EXTRUSION_MISMATCH": "cad_format_semantics",
    "CIRCLE_MISMATCH": "cad_format_semantics",
    "TEXT_MISMATCH": "cad_format_semantics",
    "AUDIT_ERROR": "cad_format_semantics",
    "AUDIT_FIX": "serialization_difference",
    "VALIDATOR_ERROR": "validator_error",
}
DEFAULT_CATEGORY = "unclassified"


@dataclass(frozen=True)
class DxfIssue:
    code: str
    severity: str
    object_id: str | None
    message: str
    expected: Any = None
    actual: Any = None

    @property
    def category(self) -> str:
        return ISSUE_CATEGORIES.get(self.code, DEFAULT_CATEGORY)

    def to_dict(self) -> dict[str, Any]:
        return {
            "code": self.code,
            "category": self.category,
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


def symbol_name_equal(
    first: str, second: str, policy: str = "case_insensitive"
) -> bool:
    if policy == "exact":
        return first == second
    return first.casefold() == second.casefold()


def _expected_entities(
    cad_ir: CadIR, profile: DeliveryProfile
) -> dict[tuple[str, str, int, int], dict[str, Any]]:
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
                    "ring_key": _ring_key(
                        obj, "polygon_ring", ring_role, _ring_coords(ring)
                    ),
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
                    "ring_key": "",
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
                "ring_key": "",
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
                "style": profile.text_style_policy["style"],
                "ring_role": "none",
                "ring_key": "",
                "geometry_revision": obj.geometry_revision,
                "source_hash": _source_hash(obj),
                "rep_hash": _rep_hash(obj),
            }
    return expected


def _read_xdata(entity) -> tuple[dict[str, Any] | None, str | None]:
    if not entity.has_xdata(XDATA_APPID):
        return None, "MISSING_XDATA"
    values = list(entity.get_xdata(XDATA_APPID))
    if len(values) != 10:
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
                "ring_key": str(values[9][1]),
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


def _style_issues(entity, object_id: str) -> list[DxfIssue]:
    issues: list[DxfIssue] = []
    if int(getattr(entity.dxf, "color", 256)) != 256:
        issues.append(
            DxfIssue(
                "ENTITY_COLOR_OVERRIDE",
                "error",
                object_id,
                "entity color override is not allowed (BYLAYER policy)",
                256,
                entity.dxf.color,
            )
        )
    linetype = str(getattr(entity.dxf, "linetype", "BYLAYER"))
    if linetype.upper() != "BYLAYER":
        issues.append(
            DxfIssue(
                "ENTITY_LINETYPE_OVERRIDE",
                "error",
                object_id,
                "entity linetype override is not allowed (BYLAYER policy)",
                "BYLAYER",
                linetype,
            )
        )
    if int(getattr(entity.dxf, "lineweight", -1)) != -1:
        issues.append(
            DxfIssue(
                "ENTITY_LINEWEIGHT_OVERRIDE",
                "error",
                object_id,
                "entity lineweight override is not allowed (BYLAYER policy)",
                -1,
                entity.dxf.lineweight,
            )
        )
    if entity.dxf.hasattr("true_color"):
        issues.append(
            DxfIssue(
                "ENTITY_TRUE_COLOR_OVERRIDE",
                "error",
                object_id,
                "entity true color override is not allowed (BYLAYER policy)",
                None,
                entity.dxf.true_color,
            )
        )
    if entity.dxf.hasattr("transparency"):
        issues.append(
            DxfIssue(
                "ENTITY_TRANSPARENCY_OVERRIDE",
                "error",
                object_id,
                "entity transparency override is not allowed (BYLAYER policy)",
                None,
                entity.dxf.transparency,
            )
        )
    return issues


def _validate_dxf_impl(
    dxf_path: str | Path, cad_ir: CadIR, profile: DeliveryProfile
) -> DxfReadbackResult:
    dxf_path = Path(dxf_path)
    doc = ezdxf.readfile(dxf_path)
    issues: list[DxfIssue] = []
    expected = _expected_entities(cad_ir, profile)
    name_policy = profile.symbol_name_policy

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
    actual_layer_names = [layer.dxf.name for layer in doc.layers]

    def _layer_key(name: str) -> str:
        return name if name_policy == "exact" else name.casefold()

    def _find_layer(name: str):
        for layer in doc.layers:
            if symbol_name_equal(layer.dxf.name, name, name_policy):
                return layer
        return None

    profile_layer_keys = {_layer_key(name) for name in profile.layers}
    system_layer_keys = {_layer_key(name) for name in SYSTEM_LAYERS}
    actual_layer_keys = {_layer_key(name) for name in actual_layer_names}
    for name in profile.layers:
        if _layer_key(name) not in actual_layer_keys:
            issues.append(
                DxfIssue(
                    "LAYER_MISSING",
                    "error",
                    None,
                    f"required layer {name} is missing",
                    name,
                    sorted(actual_layer_names),
                )
            )
    for name in actual_layer_names:
        if _layer_key(name) not in profile_layer_keys | system_layer_keys:
            issues.append(
                DxfIssue(
                    "UNEXPECTED_LAYER",
                    "error",
                    None,
                    f"unexpected layer {name}",
                    None,
                    name,
                )
            )
    for name, spec in profile.layers.items():
        layer = _find_layer(name)
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
        if not symbol_name_equal(
            str(layer.dxf.linetype),
            str(spec.get("linetype", "CONTINUOUS")),
            name_policy,
        ):
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

    def _collection_has_name(collection, expected: str) -> bool:
        for item in collection:
            name = getattr(item, "name", None)
            if name is None:
                name = item.dxf.name
            if symbol_name_equal(str(name), expected, name_policy):
                return True
        return False

    for name in profile.required_blocks:
        if not _collection_has_name(doc.blocks, name):
            issues.append(
                DxfIssue(
                    "BLOCK_MISSING",
                    "error",
                    None,
                    f"required block {name} is missing",
                    name,
                    None,
                )
            )
    for name in profile.required_dimstyles:
        if not _collection_has_name(doc.dimstyles, name):
            issues.append(
                DxfIssue(
                    "DIMSTYLE_MISSING",
                    "error",
                    None,
                    f"required dimstyle {name} is missing",
                    name,
                    None,
                )
            )
    for name in profile.required_text_styles:
        if not _collection_has_name(doc.styles, name):
            issues.append(
                DxfIssue(
                    "TEXT_STYLE_MISSING",
                    "error",
                    None,
                    f"required text style {name} is missing",
                    name,
                    None,
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
        if not symbol_name_equal(
            entity.dxf.layer, spec["layer"], name_policy
        ):
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
        issues.extend(_style_issues(entity, xdata["object_id"]))
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
        if xdata["ring_key"] != spec.get("ring_key", ""):
            issues.append(
                DxfIssue(
                    "RING_KEY_MISMATCH",
                    "error",
                    xdata["object_id"],
                    "XDATA ring key does not match CAD-IR",
                    spec["ring_key"],
                    xdata["ring_key"],
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
            points = list(entity.get_points("xyseb"))
            if any(abs(float(point[4])) > TOLERANCE for point in points):
                issues.append(
                    DxfIssue(
                        "BULGE_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE bulge is not zero",
                        0.0,
                        [point[4] for point in points],
                    )
                )
            if any(
                abs(float(point[2])) > TOLERANCE
                or abs(float(point[3])) > TOLERANCE
                for point in points
            ):
                issues.append(
                    DxfIssue(
                        "VERTEX_WIDTH_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE start/end width is not zero",
                        0.0,
                        [(point[2], point[3]) for point in points],
                    )
                )
            if abs(float(getattr(entity.dxf, "const_width", 0.0))) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "CONST_WIDTH_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE constant width is not zero",
                        0.0,
                        entity.dxf.const_width,
                    )
                )
            if abs(float(getattr(entity.dxf, "thickness", 0.0))) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "THICKNESS_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE thickness is not zero",
                        0.0,
                        entity.dxf.thickness,
                    )
                )
            extrusion = entity.dxf.extrusion
            if (
                abs(float(extrusion.x)) > TOLERANCE
                or abs(float(extrusion.y)) > TOLERANCE
                or abs(float(extrusion.z) - 1.0) > TOLERANCE
            ):
                issues.append(
                    DxfIssue(
                        "EXTRUSION_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "LWPOLYLINE extrusion is not +Z",
                        (0.0, 0.0, 1.0),
                        (extrusion.x, extrusion.y, extrusion.z),
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
            if abs(float(entity.dxf.center.z)) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "CIRCLE_NONZERO_Z",
                        "error",
                        xdata["object_id"],
                        "CIRCLE center Z is not zero",
                        0.0,
                        entity.dxf.center.z,
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
            if not symbol_name_equal(
                str(entity.dxf.style), spec["style"], name_policy
            ):
                issues.append(
                    DxfIssue(
                        "TEXT_STYLE_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT style does not match the delivery profile",
                        spec["style"],
                        entity.dxf.style,
                    )
                )
            if abs(float(entity.dxf.insert.z)) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "TEXT_NONZERO_Z",
                        "error",
                        xdata["object_id"],
                        "TEXT insertion Z is not zero",
                        0.0,
                        entity.dxf.insert.z,
                    )
                )
            text_policy = profile.text_style_policy
            if abs(
                float(entity.dxf.rotation)
                - float(text_policy["rotation"])
            ) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "TEXT_ROTATION_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT rotation does not match the delivery profile",
                        text_policy["rotation"],
                        entity.dxf.rotation,
                    )
                )
            if abs(
                float(entity.dxf.width)
                - float(text_policy["width_factor"])
            ) > TOLERANCE:
                issues.append(
                    DxfIssue(
                        "TEXT_WIDTH_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT width factor does not match the delivery profile",
                        text_policy["width_factor"],
                        entity.dxf.width,
                    )
                )
            if int(entity.dxf.halign) != int(
                text_policy["halign"]
            ) or int(entity.dxf.valign) != int(text_policy["valign"]):
                issues.append(
                    DxfIssue(
                        "TEXT_ALIGNMENT_MISMATCH",
                        "error",
                        xdata["object_id"],
                        "TEXT alignment does not match the delivery profile",
                        (text_policy["halign"], text_policy["valign"]),
                        (entity.dxf.halign, entity.dxf.valign),
                    )
                )

        if entity.dxftype() == "LWPOLYLINE":
            raw_points = list(entity.get_points("xyseb"))
            raw_semantics = {
                "closed": bool(entity.closed),
                "elevation": float(entity.dxf.elevation),
                "bulge": [float(point[4]) for point in raw_points],
                "start_width": [float(point[2]) for point in raw_points],
                "end_width": [float(point[3]) for point in raw_points],
                "const_width": float(
                    getattr(entity.dxf, "const_width", 0.0)
                ),
                "thickness": float(
                    getattr(entity.dxf, "thickness", 0.0)
                ),
                "extrusion": [
                    float(entity.dxf.extrusion.x),
                    float(entity.dxf.extrusion.y),
                    float(entity.dxf.extrusion.z),
                ],
            }
            canonical_target = {
                "coords": spec.get("coords"),
                "closed": spec.get("closed"),
            }
        elif entity.dxftype() == "CIRCLE":
            raw_semantics = {
                "center": [
                    float(entity.dxf.center.x),
                    float(entity.dxf.center.y),
                    float(entity.dxf.center.z),
                ],
                "radius": float(entity.dxf.radius),
            }
            canonical_target = {
                "center": spec.get("center"),
                "radius": spec.get("radius"),
            }
        elif entity.dxftype() == "TEXT":
            raw_semantics = {
                "insert": [
                    float(entity.dxf.insert.x),
                    float(entity.dxf.insert.y),
                    float(entity.dxf.insert.z),
                ],
                "height": float(entity.dxf.height),
                "rotation": float(entity.dxf.rotation),
                "width": float(entity.dxf.width),
                "halign": int(entity.dxf.halign),
                "valign": int(entity.dxf.valign),
                "style": str(entity.dxf.style),
                "text": str(entity.dxf.text),
            }
            canonical_target = {
                "text": spec.get("text"),
                "height": spec.get("height"),
                "style": spec.get("style"),
            }
        else:
            raw_semantics = {}
            canonical_target = {}

        entities_manifest.append(
            {
                "object_id": xdata["object_id"],
                "object_class": xdata["object_class"],
                "entity_role": xdata["entity_role"],
                "part_index": xdata["part_index"],
                "ring_index": xdata["ring_index"],
                "ring_role": xdata["ring_role"],
                "ring_key": xdata["ring_key"],
                "dxftype": entity.dxftype(),
                "layer": entity.dxf.layer,
                "canonical_target": canonical_target,
                "raw_dxf_semantics": raw_semantics,
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
        "dxf_sha256": hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
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


def validate_dxf(
    dxf_path: str | Path, cad_ir: CadIR, profile: DeliveryProfile
) -> DxfReadbackResult:
    """Validate a DXF; validator-internal errors are structured, never a pass."""
    try:
        return _validate_dxf_impl(dxf_path, cad_ir, profile)
    except Exception as exc:  # noqa: BLE001 - validator boundary
        path = Path(dxf_path)
        message = f"{type(exc).__name__}: {exc}"
        return DxfReadbackResult(
            verdict="fail",
            issues=(
                DxfIssue(
                    "VALIDATOR_ERROR",
                    "error",
                    None,
                    message,
                ),
            ),
            manifest={
                "file": path.name,
                "validator_error": message,
            },
            coverage_limits=COVERAGE_LIMITS,
        )

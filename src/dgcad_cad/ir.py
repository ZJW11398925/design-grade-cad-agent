from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Point

from dgcad_analysis import ShadowAnalysisResult, ShadowSample
from dgcad_domain import (
    ParameterValue,
    geometry_to_geojson,
    parse_geometry,
)
from dgcad_foundation import World, canonical_hash


CAD_IR_SCHEMA_ID = "design-grade-cad-agent.cad-ir.v0.1"


@dataclass(frozen=True)
class DeliveryProfile:
    profile_id: str
    profile_version: str
    dxf_version: str
    units: str
    coordinate_state: str
    coordinate_frame_ref: str
    layers: dict[str, dict[str, Any]]
    entity_style_policy: str
    layer_set_policy: str
    symbol_name_policy: str = "case_insensitive"
    required_blocks: tuple[str, ...] = ()
    required_dimstyles: tuple[str, ...] = ()
    required_text_styles: tuple[str, ...] = ()
    text_style_policy: dict[str, Any] = field(
        default_factory=lambda: {
            "style": "Standard",
            "rotation": 0.0,
            "width_factor": 1.0,
            "halign": 0,
            "valign": 0,
        }
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DeliveryProfile":
        layers = data.get("layers")
        if not isinstance(layers, dict) or not layers:
            raise ValueError("delivery.layers must be a non-empty mapping")
        text_policy = data.get("text_style_policy", {})
        if not isinstance(text_policy, dict):
            raise ValueError("delivery.text_style_policy must be a mapping")
        symbol_policy = str(
            data.get("symbol_name_policy", "case_insensitive")
        )
        if symbol_policy not in {"case_insensitive", "exact"}:
            raise ValueError(
                f"unsupported symbol_name_policy: {symbol_policy}"
            )
        return cls(
            profile_id=str(data["profile_id"]),
            profile_version=str(data["profile_version"]),
            dxf_version=str(data.get("dxf_version", "R2010")),
            units=str(data.get("units", "metre")),
            coordinate_state=str(data.get("coordinate_state", "local_metric_scaled")),
            coordinate_frame_ref=str(
                data.get("coordinate_frame_ref", "LOCAL-ENU-XY-ZUP")
            ),
            layers={str(name): dict(spec) for name, spec in layers.items()},
            entity_style_policy=str(data.get("entity_style_policy", "BYLAYER")),
            layer_set_policy=str(data.get("layer_set_policy", "exact_allowlist")),
            symbol_name_policy=symbol_policy,
            required_blocks=tuple(
                str(item) for item in data.get("required_blocks", [])
            ),
            required_dimstyles=tuple(
                str(item) for item in data.get("required_dimstyles", [])
            ),
            required_text_styles=tuple(
                str(item) for item in data.get("required_text_styles", [])
            ),
            text_style_policy={
                "style": str(text_policy.get("style", "Standard")),
                "rotation": float(text_policy.get("rotation", 0.0)),
                "width_factor": float(text_policy.get("width_factor", 1.0)),
                "halign": int(text_policy.get("halign", 0)),
                "valign": int(text_policy.get("valign", 0)),
            },
        )


@dataclass(frozen=True)
class CadObject:
    object_id: str
    object_class: str
    geometry: dict[str, Any]
    geometry_revision: int
    layer_key: str
    representation_kind: str
    source_world: str
    provenance: dict[str, Any]
    massing: dict[str, Any] | None = None

    def to_dict(self) -> dict[str, Any]:
        payload = {
            "object_id": self.object_id,
            "object_class": self.object_class,
            "geometry": self.geometry,
            "geometry_revision": self.geometry_revision,
            "layer_key": self.layer_key,
            "representation_kind": self.representation_kind,
            "source_world": self.source_world,
            "provenance": self.provenance,
        }
        if self.massing is not None:
            payload["massing"] = self.massing
        return payload


@dataclass(frozen=True)
class CadIR:
    project: dict[str, Any]
    objects: tuple[CadObject, ...]
    dependency_fingerprint: str
    schema_id: str = CAD_IR_SCHEMA_ID

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "project": self.project,
            "objects": [obj.to_dict() for obj in self.objects],
            "dependency_fingerprint": self.dependency_fingerprint,
        }


@dataclass(frozen=True)
class CadIssue:
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
class CadValidationResult:
    verdict: str
    issues: tuple[CadIssue, ...]
    coverage_limits: tuple[str, ...]

    @property
    def codes(self) -> tuple[str, ...]:
        return tuple(issue.code for issue in self.issues)

    def to_dict(self) -> dict[str, Any]:
        return {
            "verdict": self.verdict,
            "issues": [issue.to_dict() for issue in self.issues],
            "coverage_limits": list(self.coverage_limits),
        }


CAD_COVERAGE_LIMITS = (
    "current delivery profile and entity set only (LWPOLYLINE/CIRCLE/TEXT)",
    "no standards or design-office profile compliance",
    "no IFC",
    "no third-party CAD round-trip in this pipeline",
    "no arcs/splines; modelspace only",
)


def _revisions(obj) -> dict[str, int]:
    return {
        "semantic": obj.revisions.semantic,
        "geometry": obj.revisions.geometry,
        "parameter": obj.revisions.parameter,
    }


CONFIRMATION_PROVENANCE_KEYS = (
    "confirmation_scope",
    "geometry_quality",
    "review_kind",
    "site_boundary_authority",
    "canonical_site_identity",
)


def _canonical_provenance(obj, trace_ref: str | None) -> dict[str, Any]:
    provenance = {
        "source_trace_ref": trace_ref,
        "canonical_object_id": obj.object_id,
        "canonical_revisions": _revisions(obj),
        "confirmation_scope": obj.values.get("confirmation_scope", "synthetic"),
    }
    for key in CONFIRMATION_PROVENANCE_KEYS:
        if key in obj.values:
            provenance[key] = obj.values[key]
    return provenance


def _building_massing(obj) -> dict[str, Any]:
    height = ParameterValue.from_dict(obj.values.get("height"))
    base = ParameterValue.from_dict(obj.values.get("base_elevation"))
    return {
        "height_m": height.value,
        "height_state": height.state,
        "base_elevation_m": base.value,
        "height_source": height.source_ref,
    }


def build_cad_ir(
    scene,
    profile: DeliveryProfile,
    shadow_result: ShadowAnalysisResult,
    *,
    sample_points: tuple[ShadowSample, ...],
) -> CadIR:
    objects: list[CadObject] = []
    for obj in sorted(scene.objects.values(), key=lambda item: item.object_id):
        if obj.object_class == "site_boundary":
            geometry = obj.values.get("geometry")
            if geometry is None:
                raise ValueError(f"MISSING_GEOMETRY: {obj.object_id}")
            objects.append(
                CadObject(
                    object_id=obj.object_id,
                    object_class="site_boundary",
                    geometry=geometry,
                    geometry_revision=obj.revisions.geometry,
                    layer_key="A-SITE-BOUNDARY",
                    representation_kind="polygon_ring",
                    source_world=World.CANONICAL_CURRENT.value,
                    provenance=_canonical_provenance(
                        obj, obj.values.get("trace_ref")
                    ),
                )
            )
        elif obj.object_class == "green_space":
            geometry = obj.values.get("geometry")
            if geometry is None:
                raise ValueError(f"MISSING_GEOMETRY: {obj.object_id}")
            objects.append(
                CadObject(
                    object_id=obj.object_id,
                    object_class="green_space",
                    geometry=geometry,
                    geometry_revision=obj.revisions.geometry,
                    layer_key="L-GREEN",
                    representation_kind="polygon_ring",
                    source_world=World.CANONICAL_CURRENT.value,
                    provenance=_canonical_provenance(
                        obj, obj.values.get("trace_ref")
                    ),
                )
            )
        elif obj.object_class == "building":
            footprint = obj.values.get("professional_footprint")
            if footprint is None:
                raise ValueError(
                    f"MISSING_PROFESSIONAL_FOOTPRINT: {obj.object_id}"
                )
            objects.append(
                CadObject(
                    object_id=obj.object_id,
                    object_class="building_footprint",
                    geometry=footprint,
                    geometry_revision=obj.revisions.geometry,
                    layer_key="A-BUILDING-OUTLINE",
                    representation_kind="polygon_ring",
                    source_world=World.CANONICAL_CURRENT.value,
                    provenance=_canonical_provenance(
                        obj, obj.values.get("trace_ref")
                    ),
                    massing=_building_massing(obj),
                )
            )
        elif obj.object_class == "road_corridor":
            centerline = obj.values.get("centerline")
            if centerline is None:
                raise ValueError(f"ROAD_CENTERLINE_MISSING: {obj.object_id}")
            objects.append(
                CadObject(
                    object_id=obj.object_id,
                    object_class="road_centerline",
                    geometry=centerline,
                    geometry_revision=obj.revisions.geometry,
                    layer_key="C-ROAD-CENTER",
                    representation_kind="centerline",
                    source_world=World.CANONICAL_CURRENT.value,
                    provenance={
                        "source_trace_ref": obj.values.get("trace_ref"),
                        "canonical_object_id": obj.object_id,
                        "canonical_revisions": _revisions(obj),
                        "confirmation_scope": obj.values.get(
                            "confirmation_scope", "synthetic"
                        ),
                        **{
                            key: obj.values[key]
                            for key in CONFIRMATION_PROVENANCE_KEYS
                            if key in obj.values
                            and key != "confirmation_scope"
                        },
                        "edge_refs": list(obj.values.get("edge_refs", [])),
                    },
                )
            )

    for sample in sample_points:
        objects.append(
            CadObject(
                object_id=sample.sample_id,
                object_class="environment_sensor",
                geometry=geometry_to_geojson(Point(sample.x, sample.y)),
                geometry_revision=0,
                layer_key="A-ENV-SENSOR",
                representation_kind="point_marker",
                source_world="analysis",
                provenance={
                    "source_trace_ref": None,
                    "canonical_object_id": None,
                    "canonical_revisions": {
                        "semantic": 0,
                        "geometry": 0,
                        "parameter": 0,
                    },
                    "analysis_dependency_fingerprint": (
                        shadow_result.dependency_fingerprint
                    ),
                },
            )
        )

    project = {
        "project_id": scene.scene_id,
        "built_from_scene_revision": scene.scene_revision,
        "units": profile.units,
        "coordinate_frame_ref": profile.coordinate_frame_ref,
        "coordinate_state": profile.coordinate_state,
        "profile_ref": profile.profile_id,
        "profile_version": profile.profile_version,
    }
    # The global scene revision is build metadata, not a semantic dependency.
    # Otherwise an unrelated commit would change the fingerprint while the
    # CAD-IR artifact is still correctly marked current.
    fingerprint_project = {
        key: value
        for key, value in project.items()
        if key != "built_from_scene_revision"
    }
    fingerprint_payload = {
        "schema_id": CAD_IR_SCHEMA_ID,
        "project": fingerprint_project,
        "objects": [obj.to_dict() for obj in objects],
        "shadow_dependency_fingerprint": shadow_result.dependency_fingerprint,
    }
    return CadIR(
        project=project,
        objects=tuple(objects),
        dependency_fingerprint=canonical_hash(fingerprint_payload),
    )


def validate_cad_ir(cad_ir: CadIR, profile: DeliveryProfile) -> CadValidationResult:
    issues: list[CadIssue] = []
    seen: set[str] = set()
    for obj in cad_ir.objects:
        if obj.object_id in seen:
            issues.append(
                CadIssue(
                    "DUPLICATE_OBJECT_ID",
                    "error",
                    obj.object_id,
                    "duplicate object id in CAD-IR",
                )
            )
        seen.add(obj.object_id)

        try:
            geometry = parse_geometry(obj.geometry)
        except ValueError as exc:
            issues.append(
                CadIssue(
                    "INVALID_GEOMETRY",
                    "error",
                    obj.object_id,
                    str(exc),
                )
            )
            continue
        if geometry.is_empty or not geometry.is_valid:
            issues.append(
                CadIssue(
                    "INVALID_GEOMETRY",
                    "error",
                    obj.object_id,
                    "geometry is empty or invalid",
                )
            )
        if obj.representation_kind == "polygon_ring" and geometry.geom_type not in {
            "Polygon",
            "MultiPolygon",
        }:
            issues.append(
                CadIssue(
                    "INVALID_GEOMETRY",
                    "error",
                    obj.object_id,
                    f"polygon object has {geometry.geom_type}",
                )
            )
        if obj.representation_kind == "centerline" and geometry.geom_type not in {
            "LineString",
            "MultiLineString",
        }:
            issues.append(
                CadIssue(
                    "INVALID_GEOMETRY",
                    "error",
                    obj.object_id,
                    f"centerline object has {geometry.geom_type}",
                )
            )
        if obj.layer_key not in profile.layers:
            issues.append(
                CadIssue(
                    "UNKNOWN_LAYER",
                    "error",
                    obj.object_id,
                    f"layer {obj.layer_key} is not in the delivery profile",
                )
            )
        for key in (
            "source_trace_ref",
            "canonical_object_id",
            "canonical_revisions",
        ):
            if key not in obj.provenance:
                issues.append(
                    CadIssue(
                        "PROVENANCE_INCOMPLETE",
                        "error",
                        obj.object_id,
                        f"provenance missing {key}",
                    )
                )
        review_kind = obj.provenance.get("review_kind")
        if review_kind is not None:
            for key in ("confirmation_scope", "geometry_quality"):
                if key not in obj.provenance:
                    issues.append(
                        CadIssue(
                            "PROVENANCE_INCOMPLETE",
                            "error",
                            obj.object_id,
                            f"review provenance missing {key}",
                        )
                    )
            scope = obj.provenance.get("confirmation_scope")
            quality = obj.provenance.get("geometry_quality")
            if scope == "pilot_subset" and quality != "confirmed_for_pilot":
                issues.append(
                    CadIssue(
                        "SCOPE_QUALITY_MISMATCH",
                        "error",
                        obj.object_id,
                        "pilot_subset requires confirmed_for_pilot geometry",
                    )
                )
            if scope == "full_case" and quality != "confirmed":
                issues.append(
                    CadIssue(
                        "SCOPE_QUALITY_MISMATCH",
                        "error",
                        obj.object_id,
                        "full_case requires confirmed geometry",
                    )
                )
        if (
            obj.provenance.get("site_boundary_authority")
            == "published_sketch_boundary"
            and obj.provenance.get("canonical_site_identity") is True
        ):
            issues.append(
                CadIssue(
                    "SITE_AUTHORITY_CONFLICT",
                    "error",
                    obj.object_id,
                    "a published sketch boundary cannot claim canonical site "
                    "identity",
                )
            )
        if obj.object_class == "building_footprint":
            massing = obj.massing or {}
            if massing.get("height_state") != "confirmed":
                issues.append(
                    CadIssue(
                        "UNKNOWN_HEIGHT_ALLOWED",
                        "warning",
                        obj.object_id,
                        "building height is not confirmed; exported as metadata only",
                    )
                )

    if not cad_ir.dependency_fingerprint:
        issues.append(
            CadIssue(
                "DEPENDENCY_FINGERPRINT_MISSING",
                "error",
                None,
                "CAD-IR has no dependency fingerprint",
            )
        )

    severities = {issue.severity for issue in issues}
    if "error" in severities:
        verdict = "fail"
    elif "warning" in severities:
        verdict = "pass_with_scope_limits"
    else:
        verdict = "pass"
    return CadValidationResult(
        verdict=verdict,
        issues=tuple(issues),
        coverage_limits=CAD_COVERAGE_LIMITS,
    )

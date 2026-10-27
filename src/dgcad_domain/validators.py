from __future__ import annotations

from typing import Any

from dgcad_foundation import AuthorityState

from .common import (
    DomainIssue,
    DomainValidationResult,
    ParameterValue,
    geometry_to_geojson,
    parse_geometry,
    polygon_from_geojson,
)
from .trace import ConfirmedTraceScene


COVERAGE_LIMITS = (
    "synthetic fixture only; not real-world evidence",
    "massing geometry and volume are not computed",
    "road surface continuity and junction turn geometry are not checked",
    "no standards, profile compliance or regulatory conclusion",
)


def _verdict(issues: tuple[DomainIssue, ...]) -> str:
    severities = {issue.severity for issue in issues}
    if "error" in severities:
        return "fail"
    if "blocked" in severities:
        return "blocked"
    if "review_required" in severities or "warning" in severities:
        return "conditional"
    return "pass"


def _result(
    validator_id: str, scope: str, issues: list[DomainIssue]
) -> DomainValidationResult:
    issue_tuple = tuple(issues)
    return DomainValidationResult(
        validator_id=validator_id,
        validator_version="0.1",
        scope=scope,
        verdict=_verdict(issue_tuple),
        issues=issue_tuple,
        coverage_limits=COVERAGE_LIMITS,
    )


def _site_geometry(scene) -> Any | None:
    for obj in scene.objects.values():
        if obj.object_class == "site_boundary":
            geometry = obj.values.get("geometry")
            if geometry is not None:
                try:
                    return polygon_from_geojson(geometry)
                except ValueError:
                    return None
    return None


def validate_building(scene, building_id: str) -> DomainValidationResult:
    issues: list[DomainIssue] = []
    obj = scene.objects.get(building_id)
    if obj is None:
        issues.append(
            DomainIssue(
                code="BUILDING_NOT_FOUND",
                severity="error",
                object_id=building_id,
                message=f"building {building_id} does not exist",
            )
        )
        return _result("dgcad.domain.building.v0.1", f"building:{building_id}", issues)

    professional_payload = obj.values.get("professional_footprint")
    if professional_payload is None:
        issues.append(
            DomainIssue(
                code="BUILDING_PROFESSIONAL_FOOTPRINT_MISSING",
                severity="warning",
                object_id=building_id,
                message="professional footprint has not been committed",
            )
        )
    else:
        try:
            professional = polygon_from_geojson(professional_payload)
        except ValueError as exc:
            issues.append(
                DomainIssue(
                    code="INVALID_FOOTPRINT",
                    severity="error",
                    object_id=building_id,
                    message=str(exc),
                    actual=professional_payload,
                )
            )
        else:
            if not professional.is_valid:
                issues.append(
                    DomainIssue(
                        code="INVALID_FOOTPRINT",
                        severity="error",
                        object_id=building_id,
                        message="professional footprint is not a valid polygon",
                    )
                )
            else:
                site = _site_geometry(scene)
                if site is not None and not site.covers(professional):
                    issues.append(
                        DomainIssue(
                            code="FOOTPRINT_OUTSIDE_SITE",
                            severity="error",
                            object_id=building_id,
                            message="professional footprint is not contained by site boundary",
                        )
                    )

    if obj.values.get("regularization_state") == "regularized_candidate":
        if obj.values.get("regularization_diff") is None:
            issues.append(
                DomainIssue(
                    code="MISSING_REGULARIZATION_DIFF",
                    severity="error",
                    object_id=building_id,
                    message="regularized candidate has no diff metrics",
                )
            )
        issues.append(
            DomainIssue(
                code="REGULARIZATION_REQUIRES_REVIEW",
                severity="review_required",
                object_id=building_id,
                message="regularized candidate must be reviewed against the trace",
            )
        )

    height = ParameterValue.from_dict(obj.values.get("height"))
    if height.state != "confirmed":
        issues.append(
            DomainIssue(
                code="UNKNOWN_HEIGHT_BLOCKS_MASSING",
                severity="warning",
                object_id=building_id,
                message=f"height state is {height.state}; massing is blocked",
            )
        )

    return _result(
        "dgcad.domain.building.v0.1", f"building:{building_id}", issues
    )


def validate_road(scene, corridor_id: str) -> DomainValidationResult:
    issues: list[DomainIssue] = []
    obj = scene.objects.get(corridor_id)
    if obj is None:
        issues.append(
            DomainIssue(
                code="CORRIDOR_NOT_FOUND",
                severity="error",
                object_id=corridor_id,
                message=f"road corridor {corridor_id} does not exist",
            )
        )
        return _result("dgcad.domain.road.v0.1", f"road:{corridor_id}", issues)

    centerline = obj.values.get("centerline")
    if centerline is None or obj.values.get("centerline_state") != "confirmed":
        issues.append(
            DomainIssue(
                code="ROAD_CENTERLINE_NOT_CONFIRMED",
                severity="blocked",
                object_id=corridor_id,
                message="road surface requires a confirmed, current centerline",
            )
        )
    else:
        try:
            geometry = parse_geometry(centerline)
        except ValueError as exc:
            issues.append(
                DomainIssue(
                    code="ROAD_GEOMETRY_INVALID",
                    severity="error",
                    object_id=corridor_id,
                    message=str(exc),
                )
            )
        else:
            if geometry.is_empty or not geometry.is_valid:
                issues.append(
                    DomainIssue(
                        code="ROAD_GEOMETRY_INVALID",
                        severity="error",
                        object_id=corridor_id,
                        message="centerline geometry is empty or invalid",
                    )
                )

    hierarchy = obj.values.get("hierarchy")
    hierarchy_state = obj.values.get("hierarchy_state")
    if not hierarchy or hierarchy_state != "confirmed":
        issues.append(
            DomainIssue(
                code="ROAD_CLASS_UNCONFIRMED",
                severity="blocked",
                object_id=corridor_id,
                message="road class is unknown or unconfirmed; no derived width is allowed",
            )
        )
    else:
        resolution = obj.values.get("profile_resolution") or {}
        if resolution.get("outcome") != "resolved":
            issues.append(
                DomainIssue(
                    code="NO_PROFILE_FOR_CLASS",
                    severity="blocked",
                    object_id=corridor_id,
                    message="no authorized profile resolves this road class",
                )
            )

    cross_section = obj.values.get("cross_section") or {}
    if hierarchy_state != "confirmed":
        for component in cross_section.get("components", []):
            if component.get("width_status") == "derived":
                issues.append(
                    DomainIssue(
                        code="DERIVED_WIDTH_WITHOUT_CLASS",
                        severity="error",
                        object_id=corridor_id,
                        message="derived width exists while road class is unconfirmed",
                    )
                )

    return _result("dgcad.domain.road.v0.1", f"road:{corridor_id}", issues)


def validate_scene(
    scene, trace_scene: ConfirmedTraceScene
) -> DomainValidationResult:
    issues: list[DomainIssue] = []

    for trace in trace_scene.trace_objects.values():
        evidence = scene.objects.get(trace.trace_id)
        if evidence is None:
            issues.append(
                DomainIssue(
                    code="TRACE_EVIDENCE_MODIFIED",
                    severity="error",
                    object_id=trace.trace_id,
                    message="trace evidence object is missing",
                )
            )
            continue
        if evidence.authority_state != AuthorityState.EVIDENCE_ONLY:
            issues.append(
                DomainIssue(
                    code="TRACE_EVIDENCE_MODIFIED",
                    severity="error",
                    object_id=trace.trace_id,
                    message="trace evidence object no longer has evidence_only authority",
                )
            )
        expected = geometry_to_geojson(trace.geometry)
        if evidence.values.get("geometry") != expected:
            issues.append(
                DomainIssue(
                    code="TRACE_EVIDENCE_MODIFIED",
                    severity="error",
                    object_id=trace.trace_id,
                    message="trace evidence geometry no longer matches the fixture",
                )
            )

    for object_id, obj in scene.objects.items():
        if obj.object_class in {
            "building",
            "road_corridor",
            "site_boundary",
            "green_space",
        }:
            trace_ref = obj.values.get("trace_ref")
            if trace_ref is None:
                issues.append(
                    DomainIssue(
                        code="TRACE_REF_MISSING",
                        severity="error",
                        object_id=object_id,
                        message="design object has no trace_ref",
                    )
                )
            elif trace_ref not in trace_scene.trace_objects:
                issues.append(
                    DomainIssue(
                        code="TRACE_REF_UNKNOWN",
                        severity="error",
                        object_id=object_id,
                        message=f"trace_ref {trace_ref} does not exist",
                    )
                )

    for building_id in trace_scene.buildings:
        issues.extend(validate_building(scene, building_id).issues)
    for corridor_id in trace_scene.roads:
        issues.extend(validate_road(scene, corridor_id).issues)

    return _result("dgcad.domain.scene.v0.1", "scene", issues)

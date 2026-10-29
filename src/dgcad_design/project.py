from __future__ import annotations

import hashlib
import inspect
import json
import shutil
from dataclasses import replace
from pathlib import Path
from typing import Any

import yaml
from shapely.geometry import box

from dgcad_cad import (
    CadIR,
    CadObject,
    DeliveryProfile,
    compile_to_dxf,
    validate_cad_ir,
    validate_dxf,
)
from dgcad_e2e import scan_dxf_privacy
from dgcad_foundation import World, canonical_hash

from .basis import DesignBasis
from . import buildings as buildings_module
from .buildings import (
    BuildingLayout,
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from .access import RoadAccessLayout, build_road_access
from .consistency import check_design
from .drawing import (
    build_drawing_elements,
    build_full_site_drawing_elements,
)
from .green import (
    OPEN_SPACE_FILTERS,
    GreenLayout,
    build_green_layout,
    design_full_site_green,
)
from .input import DesignInput, load_design_input
from .intent import DesignIntent, build_design_intent
from .parking import ParkingLayout, build_parking_layout
from .roads import RoadLayout, build_road_layout
from .scene import design_scene, scene_objects_for_export


class DesignSynthesisBlocked(RuntimeError):
    pass


def _provenance(obj, basis: DesignBasis) -> dict[str, Any]:
    values = obj.values
    return {
        "source_trace_ref": values.get("source_trace_ref"),
        "canonical_object_id": obj.object_id,
        "canonical_revisions": {
            "semantic": obj.revisions.semantic,
            "geometry": obj.revisions.geometry,
            "parameter": obj.revisions.parameter,
        },
        "confirmation_scope": "design_draft",
        "geometry_quality": "rule_derived",
        "review_kind": "autonomous_design_draft",
        "design_basis_id": basis.basis_id,
        "design_authority": basis.design_authority,
        "human_confirmed": False,
        "annotation_role": values.get("annotation_role"),
    }


def _cad_object(obj, profile: DeliveryProfile, basis: DesignBasis) -> CadObject:
    values = obj.values
    layer = str(values["layer_key"])
    if obj.object_class == "building":
        geometry = values["professional_footprint"]
        object_class = "building_footprint"
        representation = "polygon_ring"
        height = values["height"]
        massing = {
            "height_m": height["value"],
            "height_state": height["state"],
            "base_elevation_m": values["base_elevation"]["value"],
            "height_source": height["source_ref"],
        }
    elif obj.object_class in {
        "green_space",
        "road_corridor",
        "road_sidewalk",
        "entrance",
    }:
        geometry = values["geometry"]
        object_class = obj.object_class
        representation = "polygon_ring"
        massing = None
    elif obj.object_class == "road_centerline":
        geometry = values["geometry"]
        object_class = "road_centerline"
        representation = "centerline"
        massing = None
    elif obj.object_class == "annotation_polyline":
        geometry = values["geometry"]
        object_class = "annotation_polyline"
        representation = "polyline"
        massing = None
    elif obj.object_class == "annotation_text":
        geometry = values["geometry"]
        object_class = "annotation_text"
        representation = "text"
        massing = None
    else:
        raise ValueError(f"unsupported design object class: {obj.object_class}")
    return CadObject(
        object_id=obj.object_id,
        object_class=object_class,
        geometry=geometry,
        geometry_revision=obj.revisions.geometry,
        layer_key=layer,
        representation_kind=representation,
        source_world=World.PROPOSAL_PREVIEW.value,
        provenance=_provenance(obj, basis),
        massing=massing,
        text=(
            str(values["text"])
            if obj.object_class == "annotation_text"
            else None
        ),
        text_height=(
            float(values.get("text_height", 2.0))
            if obj.object_class == "annotation_text"
            else 0.0
        ),
        text_style=(
            str(profile.text_style_policy["style"])
            if obj.object_class == "annotation_text"
            else None
        ),
        rotation=(
            float(values.get("rotation", 0.0))
            if obj.object_class == "annotation_text"
            else 0.0
        ),
    )


def build_design_cad_ir(
    scene,
    profile: DeliveryProfile,
    basis: DesignBasis,
    metrics: dict[str, Any],
    *,
    project_id: str = "DESIGN-CASE-SKETCH-001",
) -> CadIR:
    objects = tuple(
        _cad_object(obj, profile, basis)
        for obj in sorted(
            scene.objects.values(), key=lambda item: item.object_id
        )
    )
    object_dicts = [obj.to_dict() for obj in objects]
    fingerprint = canonical_hash(
        {
            "design_basis": basis.to_dict(),
            "objects": object_dicts,
            "metrics": {
                "far": metrics["far"],
                "households": metrics["households"],
                "parking_spaces": metrics["parking_spaces"],
            },
        }
    )
    project = {
        "project_id": project_id,
        "built_from_scene_revision": scene.scene_revision,
        "units": profile.units,
        "coordinate_frame_ref": profile.coordinate_frame_ref,
        "coordinate_state": profile.coordinate_state,
        "profile_ref": profile.profile_id,
        "profile_version": profile.profile_version,
        "design_basis_id": basis.basis_id,
        "design_authority": basis.design_authority,
        "human_confirmed": False,
        "drawing_standard": basis.drawing_standard,
        "claim_scope": basis.claim_scope,
        "scope_limits": [
            "schematic design proposal, not a construction or permit drawing",
            "no code-compliance claim",
            "road corridors are schematic offsets, not professional alignment",
            "garage layout is not designed",
            "the published sketch boundary is not the authoritative private redline",
            "the unit module is a provisional design assumption",
        ],
    }
    return CadIR(
        project=project,
        objects=objects,
        dependency_fingerprint=fingerprint,
    )


def _design_diff(
    design_input: DesignInput,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    green_layout: GreenLayout,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
) -> dict[str, Any]:
    buildings = []
    for building in building_layout.focus_buildings:
        width = (
            30.0
            if building.is_facility
            else basis.building_width(building.unit_count)
        )
        buildings.append(
            {
                "building_id": building.building_id,
                "subgroup_id": building.subgroup_id,
                "row": building.row_index,
                "unit_count": building.unit_count,
                "households": building.households,
                "gfa_m2": building.gfa_m2,
                "source_area_m2": building.source_area_m2,
                "design_area_m2": building.footprint.area,
                "area_change_m2": (
                    building.footprint.area - building.source_area_m2
                ),
                "source_centroid": list(building.source_centroid),
                "design_centroid": list(building.design_centroid),
                "displacement_m": building.displacement_m,
                "source_orientation_deg": building.source_orientation_deg,
                "design_orientation_deg": building.design_orientation_deg,
                "design_dimensions_m": [
                    width,
                    basis.staircase_depth_m,
                ],
                "reason": (
                    "standardized to the declared staircase module and placed "
                    "in a 20 m north-south row layout"
                ),
            }
        )
    road_classes: dict[str, dict[str, Any]] = {}
    for road in road_layout.roads:
        entry = road_classes.setdefault(
            road.class_name,
            {"count": 0, "width_m": road.width_m},
        )
        entry["count"] += 1
    return {
        "schema_id": "dgcad.design-diff.v0.1",
        "design_basis_id": basis.basis_id,
        "focus_group_id": intent.focus_group_id,
        "buildings": buildings,
        "rows": list(building_layout.rows),
        "dropped_focus_building_ids": list(
            building_layout.dropped_focus_building_ids
        ),
        "dropped": [
            {
                "building_id": trace_id,
                "unit_count": next(
                    (
                        item.unit_count
                        for item in design_input.buildings
                        if item.trace_id == trace_id
                    ),
                    None,
                ),
                "reason": (
                    "does not fit the buildable focus block at the declared "
                    "north-south spacing, setback and road clearance"
                ),
            }
            for trace_id in building_layout.dropped_focus_building_ids
        ],
        "roads": {
            "classes": road_classes,
            "corridor_generator": road_layout.corridor_generator,
            "not_professional_alignment": True,
            "main_road_count": intent.road_hierarchy["main_edges"],
            "branch_or_access_count": intent.road_hierarchy[
                "branch_or_access_edges"
            ],
        },
        "green": {
            "cluster_area_m2": green_layout.cluster_area_m2,
            "strip_area_m2": green_layout.strip_area_m2,
            "supplementary_area_m2": green_layout.supplementary_area_m2,
            "candidate_open_space_area_m2": (
                green_layout.candidate_open_space_area_m2
            ),
            "candidate_open_space_ratio": (
                green_layout.candidate_open_space_ratio
            ),
            "unbuilt_area_m2": green_layout.unbuilt_area_m2,
            "unbuilt_ratio": green_layout.unbuilt_ratio,
            "open_space_filters": dict(OPEN_SPACE_FILTERS),
            "designed_green_area_m2": green_layout.designed_green_area_m2,
            "designed_green_ratio": green_layout.designed_green_ratio,
            "green_target_ratio": green_layout.target_ratio,
            "dropped_cluster_ids": list(green_layout.dropped_cluster_ids),
        },
        "parking": {
            "households": parking_layout.households,
            "spaces_required": parking_layout.spaces_required,
            "entrances_required": parking_layout.entrances_required,
            "existing_entrances": sum(
                1
                for item in parking_layout.entrances
                if item.status == "existing"
            ),
            "proposed_entrances": sum(
                1
                for item in parking_layout.entrances
                if item.status == "proposed"
            ),
            "assumed_nominal_capacity_spaces": (
                parking_layout.assumed_nominal_capacity_spaces
            ),
            "capacity_basis": "spaces_per_entrance assumption (not verified)",
            "garage_layout": parking_layout.garage_layout,
        },
        "road_alignment": {
            "records": [
                dict(record)
                for record in road_layout.main_alignment_records
            ],
            "boundary_repairs": [
                dict(item) for item in road_layout.main_boundary_repairs
            ],
            "main_boundary_ok": road_layout.simplification.get(
                "main_boundary_ok"
            ),
            "main_boundary_margin_m": road_layout.simplification.get(
                "main_boundary_margin_m"
            ),
            "source_segment_map": {
                road_id: [dict(item) for item in segments]
                for road_id, segments in road_layout.source_segment_map.items()
            },
        },
        "dead_end_resolutions": [
            dict(item) for item in road_layout.dead_end_resolutions
        ],
        "changed": [
            "building footprints replaced by standardized staircase modules",
            "focus-group buildings reorganized into rows",
            "20 m north-south spacing inserted between rows",
            "green strips inserted between building rows",
            "road widths assigned from the declared class",
            "garage entrances added to meet the parking requirement",
            "main roads adjusted to remove the known road/building overlap "
            "(MAIN-19 diversion, MAIN-08 local detour) and repaired for site "
            "boundary containment (MAIN-08/16/18 corridor overhangs)",
            "seven previously unresolved dead ends resolved: 2 trimmed, "
            "3 bridged and 2 site-edge termini",
        ],
        "preserved": [
            "building IDs and inferred staircase counts",
            "the focus group's location and its relation to the main road",
            "the main road as the organization spine",
            "cluster green spaces that remain clear of buildings and roads",
            "all 44 road ids, class widths and the 17 declared group-access "
            "relations",
        ],
        "why": [
            "the declared design basis fixes the unit module, floor count, "
            "road widths, FAR range, parking ratio and 20 m north-south gap",
            "a regular row layout makes the 20 m gap verifiable and gives each "
            "group a clear internal green strip",
            "the main-road geometry change is recorded per road (source edges, "
            "alignment strategy, displacement, overlap before/after) and by "
            "boundary repair, and every dead-end resolution is recorded with "
            "its strategy and verification",
            "the schema is a proposal: no human confirmation or code-compliance "
            "claim is made",
        ],
    }


def _evidence_files(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)


def _design_roads_geojson(
    road_layout: RoadLayout,
    road_access: RoadAccessLayout | None = None,
) -> dict[str, Any]:
    """Publish the design centre lines so topology is checkable from evidence.

    This is the M4c-1a artefact: before it, only the focus-area centre lines
    reached the DXF/CAD-IR and the full design network's topology could not be
    recomputed from committed files. M4c-1b adds the per-group access terminals
    and the dead-end justification records.
    """
    payload: dict[str, Any] = {
        "type": "FeatureCollection",
        "schema_id": "dgcad.design-roads.v0.1",
        "road_count": len(road_layout.roads),
        "coordinate_frame": "design-local-metric",
        "junction_count": len(road_layout.explicit_junctions),
        "road_class_counts": {
            name: sum(
                1 for road in road_layout.roads if road.class_name == name
            )
            for name in ("main", "branch", "access")
        },
        "road_building_overlap_m2_new_access": (
            road_layout.road_building_overlap_m2_new_access
        ),
        "road_building_overlap_m2_main_before": (
            road_layout.road_building_overlap_m2_main
        ),
        "road_building_overlap_m2_alignment_records_before": sum(
            record.get("overlap_before_m2") or 0.0
            for record in road_layout.main_alignment_records
        ),
        "road_building_overlap_m2_boundary_replaced_before": max(
            0.0,
            road_layout.road_building_overlap_m2_main
            - sum(
                record.get("overlap_before_m2") or 0.0
                for record in road_layout.main_alignment_records
            ),
        ),
        "road_building_overlap_m2_main_after": (
            road_layout.road_building_overlap_m2_main_after
        ),
        "road_building_overlap_m2_total_after": (
            road_layout.road_building_overlap_m2_total
        ),
        "main_boundary_ok": road_layout.simplification.get(
            "main_boundary_ok"
        ),
        "main_boundary_margin_m": road_layout.simplification.get(
            "main_boundary_margin_m"
        ),
        "main_boundary_repairs": [
            dict(item) for item in road_layout.main_boundary_repairs
        ],
        "source_segment_map": {
            road_id: [dict(item) for item in segments]
            for road_id, segments in road_layout.source_segment_map.items()
        },
        "junctions": [
            dict(junction)
            for junction in road_layout.explicit_junctions
        ],
        "features": [
            {
                "type": "Feature",
                "id": road.edge_id,
                "properties": {
                    "edge_id": road.edge_id,
                    "class_name": road.class_name,
                    "width_m": road.width_m,
                    "is_new_connector": road.is_new_connector,
                    "start_junction_id": road.start_junction_id,
                    "end_junction_id": road.end_junction_id,
                    "source_edge_ids": list(road.source_edge_ids),
                    "serves_group_ids": list(road.serves_group_ids),
                    "access_terminal_xy": (
                        None
                        if road.access_terminal_xy is None
                        else [
                            float(road.access_terminal_xy[0]),
                            float(road.access_terminal_xy[1]),
                        ]
                    ),
                },
                "geometry": {
                    "type": "LineString",
                    "coordinates": [
                        [float(x), float(y)]
                        for x, y in road.centerline.coords
                    ],
                },
            }
            for road in road_layout.roads
        ],
    }
    if road_access is not None:
        payload["road_access_coverage"] = road_access.road_access_coverage
        payload["road_access_relation_error_count"] = len(
            road_access.relation_errors
        )
        payload["main_road_building_overlap"] = dict(
            road_access.main_road_overlap
        )
        payload["main_alignment_records"] = [
            dict(record)
            for record in road_access.main_alignment_records
        ]
        payload["dead_end_resolution_records"] = [
            dict(record)
            for record in road_access.dead_end_resolutions
        ]
        payload["group_access"] = [
            item.to_dict() for item in road_access.groups
        ]
        payload["dead_end_justification"] = [
            item.to_dict() for item in road_access.dead_ends
        ]
    return payload


def run_design_synthesis(
    case_dir: str | Path,
    basis_path: str | Path,
    profile_path: str | Path,
    output_dir: str | Path,
) -> dict[str, Any]:
    case_dir = Path(case_dir).resolve()
    basis_path = Path(basis_path).resolve()
    profile_path = Path(profile_path).resolve()
    output_dir = Path(output_dir).resolve()
    _evidence_files(output_dir)

    basis = DesignBasis.from_dict(
        yaml.safe_load(basis_path.read_text(encoding="utf-8"))
    )
    profile = DeliveryProfile.from_dict(
        yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    )
    design_input = load_design_input(case_dir, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        design_rect,
    )
    road_layout = build_road_layout(
        design_input, basis, intent, building_layout
    )
    focus_box = box(*intent.focus_bbox)
    green_layout = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        focus_box,
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    road_access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=design_input.site_boundary,
    )
    consistency = check_design(
        design_input,
        basis,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        road_access,
    )
    if design_rect is not None:
        consistency.metrics["focus_design_rect"] = list(design_rect)
    diff = _design_diff(
        design_input,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        basis,
    )
    if design_rect is not None:
        diff["focus_design_rect"] = list(design_rect)

    roads_path = output_dir / "design-roads.geojson"
    roads_path.write_text(
        json.dumps(
            _design_roads_geojson(road_layout, road_access),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
        newline="\n",
    )
    roads_sha256 = hashlib.sha256(roads_path.read_bytes()).hexdigest()

    authority_counts: dict[str, int] = {}
    for entry in basis.parameter_sources.values():
        authority = str(entry["authority"])
        authority_counts[authority] = authority_counts.get(authority, 0) + 1

    summary: dict[str, Any] = {
        "schema_id": "dgcad.design-synthesis.v0.1",
        "case_id": design_input.case_id,
        "draft_id": "DRAFT-CASE-SKETCH-001-A-R1",
        "revision": 1,
        "status": (
            "autonomous_design_draft"
            if consistency.hard_checks_ok
            else "design_incomplete"
        ),
        "design_authority": basis.design_authority,
        "human_confirmed": False,
        "design_basis_id": basis.basis_id,
        "design_basis": {
            "basis_id": basis.basis_id,
            "version": basis.version,
            "design_authority": basis.design_authority,
            "human_confirmed": basis.human_confirmed,
            "provenance_authentication": basis.provenance()[
                "provenance_authentication"
            ],
            "parameter_sources": basis.parameter_sources,
            "authority_counts": dict(sorted(authority_counts.items())),
        },
        "drawing_standard": basis.drawing_standard,
        "claim_scope": basis.claim_scope,
        "focus_group_id": intent.focus_group_id,
        "focus_bbox": list(intent.focus_bbox),
        "focus_design_rect": (
            None if design_rect is None else list(design_rect)
        ),
        "source_manifest": design_input.source_manifest,
        "coordinate_handoff": design_input.coordinate_handoff,
        "metrics": consistency.metrics,
        "consistency": consistency.to_dict(),
        "intent": intent.to_dict(),
        "road_topology": road_layout.noded_topology.to_dict(),
        "road_access": road_access.to_dict(),
        "road_alignment": {
            "records": [
                dict(record)
                for record in road_access.main_alignment_records
            ],
            "dead_end_resolutions": [
                dict(record)
                for record in road_access.dead_end_resolutions
            ],
            "main_overlap_before_m2": (
                road_layout.road_building_overlap_m2_main
            ),
            "alignment_records_overlap_before_m2": sum(
                record.get("overlap_before_m2") or 0.0
                for record in road_access.main_alignment_records
            ),
            "boundary_replaced_overlap_before_m2": max(
                0.0,
                road_layout.road_building_overlap_m2_main
                - sum(
                    record.get("overlap_before_m2") or 0.0
                    for record in road_access.main_alignment_records
                ),
            ),
            "main_overlap_after_m2": (
                road_access.main_road_overlap.get("area_m2")
            ),
            "main_overlap_status": (
                road_access.main_road_overlap.get("status")
            ),
            "main_boundary_ok": road_layout.simplification.get(
                "main_boundary_ok"
            ),
            "main_boundary_margin_m": road_layout.simplification.get(
                "main_boundary_margin_m"
            ),
            "boundary_repairs": [
                dict(item) for item in road_layout.main_boundary_repairs
            ],
            "source_segment_map": {
                road_id: [dict(item) for item in segments]
                for road_id, segments in road_layout.source_segment_map.items()
            },
        },
        "road_boundary": {
            "ok": road_layout.simplification.get("main_boundary_ok"),
            "margin_m": road_layout.simplification.get(
                "main_boundary_margin_m"
            ),
            "repair_count": road_layout.simplification.get(
                "main_boundary_repair_count"
            ),
            "definition": (
                "main-road corridor edge (centreline +/- width/2) inside the "
                "published site boundary, tolerance 0.01 m"
            ),
        },
        "main_road_building_overlap": dict(road_access.main_road_overlap),
        "full_site_road_clearance": {
            "status": "deferred",
            "value": None,
            "required": "full-site road/building clearance design",
            "message": (
                "the known main-road overlap is resolved, but a full-site "
                "road-building clearance design and check are still deferred"
            ),
        },
        "design_roads": {
            "path": roads_path.name,
            "road_count": len(road_layout.roads),
            "sha256": roads_sha256,
        },
        "diff": diff,
        "non_claims": [
            "this is a schematic design proposal, not a construction or permit drawing",
            "no Chinese code, fire-access, daylight or accessibility compliance is claimed",
            "the unit module is a provisional design assumption, not the designer's unit library",
            "the published sketch boundary is used; the private redline remains authoritative",
            "road corridors are schematic offsets, not professional alignment or junction design",
            "the garage layout is not designed; only the entrance requirement is checked",
            "the full-site north-south spacing is not yet enforced; the focus group is",
            "the noded-topology check proves connectivity only; it is not road design, alignment or junction engineering",
        ],
    }

    (output_dir / "design-intent.json").write_text(
        json.dumps(intent.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "design-consistency.json").write_text(
        json.dumps(consistency.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "design-diff.json").write_text(
        json.dumps(diff, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    shutil.copyfile(basis_path, output_dir / "design-basis.yaml")
    shutil.copyfile(profile_path, output_dir / "design-profile.yaml")

    if not consistency.hard_checks_ok:
        (output_dir / "design-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        failed = [
            check["id"]
            for check in consistency.checks
            if check["status"] == "fail"
        ]
        raise DesignSynthesisBlocked(
            "design constraints failed: " + ", ".join(failed)
        )

    elements = build_drawing_elements(
        design_input,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        basis,
        consistency.metrics,
    )
    scene_id = "scene-CASE-SKETCH-001-AUTONOMOUS-DRAFT-R1"
    scene = design_scene(elements, basis, scene_id=scene_id)
    cad_ir = build_design_cad_ir(
        scene, profile, basis, consistency.metrics
    )
    cad_validation = validate_cad_ir(cad_ir, profile)
    dxf_path = output_dir / "design-proposal.dxf"
    compile_result = compile_to_dxf(cad_ir, profile, dxf_path)
    readback = validate_dxf(dxf_path, cad_ir, profile)
    privacy = scan_dxf_privacy(dxf_path)

    summary.update(
        {
            "scene_id": scene_id,
            "scene_object_count": len(scene.objects),
            "dxf": {
                "path": dxf_path.name,
                "sha256": hashlib.sha256(
                    dxf_path.read_bytes()
                ).hexdigest(),
                "entity_count": compile_result.entity_count,
                "audit_errors": compile_result.audit_errors,
                "audit_fixes": compile_result.audit_fixes,
            },
            "readback": {
                "verdict": readback.verdict,
                "codes": list(readback.codes),
                "entity_count": readback.manifest.get("entity_count"),
                "expected_entity_count": readback.manifest.get(
                    "expected_entity_count"
                ),
                "confirmation_scopes": readback.manifest.get(
                    "confirmation_scopes"
                ),
                "manifest_sha256": canonical_hash(readback.manifest),
            },
            "cad_ir_validation": cad_validation.to_dict(),
            "privacy": privacy,
        }
    )
    if readback.verdict == "fail":
        raise DesignSynthesisBlocked(
            "DXF readback failed: " + ", ".join(readback.codes)
        )
    if not privacy["ok"]:
        raise DesignSynthesisBlocked("DXF privacy scan failed")

    (output_dir / "design-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "draft-manifest.json").write_text(
        json.dumps(
            {
                "draft_id": summary["draft_id"],
                "revision": summary["revision"],
                "status": "autonomous_draft",
                "parent_revision": None,
                "created_by": "agent",
                "design_authority": basis.design_authority,
                "human_confirmed": False,
                "design_basis_id": basis.basis_id,
                "scene_id": scene_id,
                "scene_object_count": len(scene.objects),
                "metrics": consistency.metrics,
                "consistency_ok": consistency.hard_checks_ok,
                "basis_ref": "design-basis.yaml",
                "diff_ref": "design-diff.json",
                "dxf_ref": "design-proposal.dxf",
                "note": (
                    "The agent may revise this draft without human approval. "
                    "The draft is not canonical design truth and is not "
                    "human-confirmed."
                ),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "scene-snapshot.json").write_text(
        json.dumps(
            {
                "scene_id": scene.scene_id,
                "world": scene.world.value,
                "objects": scene_objects_for_export(scene),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "cad-ir.json").write_text(
        json.dumps(cad_ir.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "readback-manifest.json").write_text(
        json.dumps(readback.manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "validation.json").write_text(
        json.dumps(
            {
                "cad_ir": cad_validation.to_dict(),
                "dxf_readback": readback.to_dict(),
                "privacy": privacy,
                "verdicts": {
                    "cad_ir": cad_validation.verdict,
                    "dxf_readback": readback.verdict,
                    "privacy": "pass" if privacy["ok"] else "fail",
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "privacy.json").write_text(
        json.dumps(privacy, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return summary


FULL_SITE_SCHEMA_ID = "dgcad.full-site-evidence.v0.1"
FULL_SITE_PROJECT_ID = "DESIGN-CASE-SKETCH-001-FULL-SITE"
FULL_SITE_SCENE_ID = "scene-CASE-SKETCH-001-FULL-SITE-R1"


def _full_site_metrics(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    green_layout: GreenLayout,
    parking_layout: ParkingLayout,
    road_access: RoadAccessLayout,
) -> dict[str, Any]:
    """Metrics for the full-site sheet, measured from the layouts themselves.

    Deliberately does not read ``consistency.metrics``: the sheet must be
    generatable while the full-site checks are still being integrated, and a
    failing full-site check must not block the drawing.  The measured clearance
    and row-spacing values do reuse the public consistency reports when they are
    available, so the drawing title block and the checks quote the same numbers.
    """
    site_area = float(design_input.site_area_m2)
    total_gfa = sum(item.gfa_m2 for item in building_layout.buildings)
    households = sum(item.households for item in building_layout.buildings)
    unit_count = sum(item.unit_count for item in building_layout.buildings)
    metrics: dict[str, Any] = {
        "site_area_m2": site_area,
        "building_count": len(building_layout.buildings),
        "unit_count": unit_count,
        "staircase_count": unit_count,
        "households": households,
        "total_gfa_m2": total_gfa,
        "far": (total_gfa / site_area) if site_area else 0.0,
        "parking_spaces": parking_layout.spaces_required,
        "parking_entrances": len(parking_layout.entrances),
        "road_access_coverage": road_access.road_access_coverage,
        "road_groups_served": road_access.groups_served,
        "road_groups_total": road_access.groups_total,
        "road_access_relation_error_count": len(road_access.relation_errors),
        "dead_ends_unresolved": road_access.dead_ends_unresolved,
        "unbuilt_ratio": green_layout.unbuilt_ratio,
        "candidate_open_space_ratio": (
            green_layout.candidate_open_space_ratio
        ),
        "designed_green_ratio": green_layout.designed_green_ratio,
        "focus_group_id": intent.focus_group_id,
        "focus_building_count": len(building_layout.focus_buildings),
        "focus_unit_count": sum(
            item.unit_count for item in building_layout.focus_buildings
        ),
    }
    full_site_green = getattr(green_layout, "full_site_green", None)
    if full_site_green is not None:
        metrics.update(
            {
                "full_site_green_parcel_count": len(green_layout.greens),
                "full_site_designed_green_area_m2": (
                    green_layout.designed_green_area_m2
                ),
                "full_site_designed_green_ratio": (
                    green_layout.designed_green_ratio
                ),
                "full_site_green_target_ratio": green_layout.target_ratio,
                "full_site_green_gap_m2": max(
                    0.0,
                    green_layout.target_ratio
                    * (
                        green_layout.designed_green_area_m2
                        / green_layout.designed_green_ratio
                    )
                    - green_layout.designed_green_area_m2,
                )
                if green_layout.designed_green_ratio
                else None,
                "full_site_green_account_kind": (
                    "open_space_tiling_auxiliary_not_designed_green"
                ),
                "full_site_open_space_account_area_m2": (
                    full_site_green.area_m2
                ),
                "full_site_open_space_account_ratio": full_site_green.ratio,
                "full_site_open_space_account_target_ratio": (
                    full_site_green.target_ratio
                ),
                "full_site_open_space_account_gap_m2": (
                    full_site_green.gap_m2
                ),
                "full_site_open_space_account_parcel_count": len(
                    full_site_green.parcels
                ),
            }
        )
    required_clearance = float(basis.building_road_clearance_m)
    metrics["road_clearance_required_m"] = required_clearance
    try:
        from .consistency import (  # noqa: PLC0415 - optional coupling
            full_site_ns_spacing_report,
            full_site_road_clearance_report,
        )

        clearance = full_site_road_clearance_report(
            basis, building_layout, road_layout
        )
        spacing = full_site_ns_spacing_report(building_layout, basis)
        metrics.update(
            {
                "min_road_clearance_m": clearance["min_clearance_m"],
                "road_clearance_violation_count": clearance[
                    "violation_count"
                ],
                "min_ns_spacing_m": spacing["value"],
                "ns_spacing_violation_count": spacing["violation_count"],
            }
        )
    except Exception:  # noqa: BLE001 - consistency coupling is optional
        pass
    if road_access.road_access_coverage < 1.0:
        metrics["road_access_note"] = (
            "the declared group-access relations (serves_group_ids and access "
            "terminals) were generated for the focus layout; relocating the "
            "other 48 buildings leaves "
            f"{len(road_access.relation_errors)} relation errors and "
            f"{road_access.groups_total - road_access.groups_served} unserved "
            "groups.  This is a known M4d integration gap, reported, not hidden."
        )
    return metrics


def try_full_site_layout(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    standardized: dict[str, Any],
    *,
    road_corridor=None,
) -> tuple[BuildingLayout | None, str | None]:
    """Use ``buildings.layout_full_site`` when it is available and valid.

    ``road_corridor`` (the fixed committed road corridor) is passed when the
    engine supports the keyword, which both pins the placement to the design
    road network and avoids rebuilding the corridor inside the engine.
    Returns ``(layout, None)`` on success and ``(None, reason)`` otherwise so
    callers can fall back to the current pipeline layout *and say so* in their
    evidence instead of silently pretending the site is laid out.
    """
    engine = getattr(buildings_module, "layout_full_site", None)
    if engine is None:
        return None, "dgcad_design.buildings.layout_full_site is not available"
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)
    kwargs: dict[str, Any] = {}
    if road_corridor is not None:
        try:
            if "road_corridor" in inspect.signature(engine).parameters:
                kwargs["road_corridor"] = road_corridor
        except (TypeError, ValueError):
            pass
    try:
        layout = engine(
            design_input, basis, intent, standardized, site_inner, **kwargs
        )
    except Exception as exc:  # noqa: BLE001 - report the reason, then fall back
        return None, f"layout_full_site failed: {type(exc).__name__}: {exc}"
    if not isinstance(layout, BuildingLayout):
        return None, "layout_full_site did not return a BuildingLayout"
    expected = {item.trace_id for item in design_input.buildings}
    actual = {item.building_id for item in layout.buildings}
    if actual != expected:
        return None, (
            "layout_full_site building set does not match the case "
            f"({len(actual)} vs {len(expected)} ids)"
        )
    return layout, None


def build_full_site_models(
    case_dir: str | Path,
    basis_path: str | Path,
    profile_path: str | Path,
    *,
    building_layout: BuildingLayout | None = None,
    use_full_site_layout: bool = True,
) -> dict[str, Any]:
    """Rebuild every layout the full-site sheet needs, once.

    The road network is the committed design network: it is built on the focus
    layout (exactly as ``run_design_synthesis`` does), which makes the 44 roads
    identical to the published ``design-roads.geojson``.  The full-site layout
    is then packed against that fixed corridor, so the sheet's buildings and
    roads are mutually consistent (0 clearance violations).  Returns a dict
    with ``basis``, ``profile``, ``design_input``, ``intent``, ``standardized``,
    ``building_layout``, ``layout_source``, ``layout_note``, ``road_layout``,
    ``green_layout``, ``parking_layout``, ``road_access`` and ``metrics``.
    """
    case_dir = Path(case_dir).resolve()
    basis_path = Path(basis_path).resolve()
    profile_path = Path(profile_path).resolve()
    basis = DesignBasis.from_dict(
        yaml.safe_load(basis_path.read_text(encoding="utf-8"))
    )
    profile = DeliveryProfile.from_dict(
        yaml.safe_load(profile_path.read_text(encoding="utf-8"))
    )
    design_input = load_design_input(case_dir, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    design_rect = find_focus_design_rect(design_input, intent, basis)
    baseline = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        design_rect,
    )
    road_layout = build_road_layout(
        design_input, basis, intent, baseline
    )
    layout_source = "supplied"
    layout_note: str | None = None
    if building_layout is None:
        if use_full_site_layout:
            building_layout, layout_note = try_full_site_layout(
                design_input,
                basis,
                intent,
                standardized,
                road_corridor=road_layout.corridor_union,
            )
        if building_layout is not None:
            layout_source = "full_site_layout"
        else:
            building_layout = baseline
            layout_source = "focus_region_fallback"

    focus_box = box(*intent.focus_bbox)
    green_layout = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        focus_box,
    )
    try:
        full_site_green = design_full_site_green(
            design_input, building_layout, road_layout, basis
        )
        if hasattr(green_layout, "full_site_green"):
            green_layout = replace(
                green_layout, full_site_green=full_site_green
            )
    except Exception:  # noqa: BLE001 - full-site green is optional
        pass
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    road_access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=design_input.site_boundary,
    )
    metrics = _full_site_metrics(
        design_input,
        basis,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        road_access,
    )
    return {
        "basis": basis,
        "profile": profile,
        "design_input": design_input,
        "intent": intent,
        "standardized": standardized,
        "building_layout": building_layout,
        "layout_source": layout_source,
        "layout_note": layout_note,
        "road_layout": road_layout,
        "green_layout": green_layout,
        "parking_layout": parking_layout,
        "road_access": road_access,
        "metrics": metrics,
    }


def _full_site_non_claims(
    layout_source: str, metrics: dict[str, Any] | None = None
) -> list[str]:
    claims = [
        "this is a schematic design proposal, not a construction or permit drawing",
        "no Chinese code, fire-access, daylight or accessibility compliance is claimed",
        "the full-site building placement is not a designer-confirmed layout",
        "road corridors are schematic offsets, not professional alignment or junction design",
        "the garage layout is not designed; only the entrance requirement is checked",
    ]
    if layout_source == "full_site_layout":
        claims.insert(
            2,
            "the full-site row placement is rule-derived from the declared basis "
            "and fixed roads, not a designer-confirmed site plan",
        )
    else:
        claims.insert(
            2,
            "context buildings are drawn at their standardized source positions "
            "because the full-site layout engine is not available or did not fit",
        )
    if metrics:
        if metrics.get("full_site_open_space_account_ratio") is not None:
            claims.append(
                "the full-site potential-open-space account is an open-space "
                "allocation candidate outside buildings and roads, not designed "
                "green and not a landscape design; the designed-green ratio is "
                "reported separately and is below the declared target"
            )
        if metrics.get("road_access_coverage", 1.0) < 1.0:
            claims.append(
                "the declared group-access relations were generated for the "
                "focus layout; the full-site relocation invalidates them, so "
                "access coverage is reported as a known M4d gap, not designed"
            )
    return claims


def run_full_site_evidence(
    case_dir: str | Path,
    basis_path: str | Path,
    profile_path: str | Path,
    output_dir: str | Path,
    *,
    building_layout: BuildingLayout | None = None,
    models: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Generate the full-site sheet (A-102) DXF plus readback/privacy evidence.

    The output directory is explicit: callers write into scratch during checks
    and the Lead decides when (and where) to publish the artefacts.  When
    ``building_layout`` is not supplied the current pipeline layout is rebuilt
    (focus group placed in rows, the other 48 buildings at their standardized
    source positions); that is the honest state until the full-site layout
    engine lands.  ``models`` lets callers reuse an already-built model dict.
    """
    output_dir = Path(output_dir).resolve()
    _evidence_files(output_dir)
    if models is None:
        models = build_full_site_models(
            case_dir,
            basis_path,
            profile_path,
            building_layout=building_layout,
        )
    basis = models["basis"]
    profile = models["profile"]
    design_input = models["design_input"]
    intent = models["intent"]
    building_layout = models["building_layout"]
    layout_source = models["layout_source"]
    layout_note = models.get("layout_note")
    road_layout = models["road_layout"]
    green_layout = models["green_layout"]
    parking_layout = models["parking_layout"]
    metrics = models["metrics"]

    elements = build_full_site_drawing_elements(
        design_input,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        basis,
        metrics,
    )
    scene = design_scene(elements, basis, scene_id=FULL_SITE_SCENE_ID)
    cad_ir = build_design_cad_ir(
        scene, profile, basis, metrics, project_id=FULL_SITE_PROJECT_ID
    )
    cad_validation = validate_cad_ir(cad_ir, profile)
    dxf_path = output_dir / "full-site-proposal.dxf"
    compile_result = compile_to_dxf(cad_ir, profile, dxf_path)
    readback = validate_dxf(dxf_path, cad_ir, profile)
    privacy = scan_dxf_privacy(dxf_path)

    summary: dict[str, Any] = {
        "schema_id": FULL_SITE_SCHEMA_ID,
        "case_id": design_input.case_id,
        "draft_id": "DRAFT-CASE-SKETCH-001-FULL-SITE-R1",
        "revision": 1,
        "status": "autonomous_full_site_draft",
        "design_authority": basis.design_authority,
        "human_confirmed": False,
        "design_basis_id": basis.basis_id,
        "sheet_id": "A-102",
        "plan_scale": "1:2000",
        "layout_source": layout_source,
        "layout_note": layout_note,
        "building_count": metrics["building_count"],
        "focus_building_count": metrics["focus_building_count"],
        "unit_count": metrics["unit_count"],
        "households": metrics["households"],
        "site_area_m2": metrics["site_area_m2"],
        "metrics": metrics,
        "road_access": {
            "coverage": metrics["road_access_coverage"],
            "groups_served": metrics["road_groups_served"],
            "groups_total": metrics["road_groups_total"],
            "relation_error_count": metrics[
                "road_access_relation_error_count"
            ],
            "note": metrics.get("road_access_note"),
        },
        "road_clearance": {
            "required_m": metrics.get("road_clearance_required_m"),
            "min_m": metrics.get("min_road_clearance_m"),
            "violation_count": metrics.get(
                "road_clearance_violation_count"
            ),
        },
        "north_south_spacing": {
            "min_m": metrics.get("min_ns_spacing_m"),
            "violation_count": metrics.get("ns_spacing_violation_count"),
        },
        "full_site_green": (
            None
            if metrics.get("full_site_designed_green_ratio") is None
            else {
                "parcel_count": metrics.get(
                    "full_site_green_parcel_count"
                ),
                "area_m2": metrics.get(
                    "full_site_designed_green_area_m2"
                ),
                "ratio": metrics.get("full_site_designed_green_ratio"),
                "target_ratio": metrics.get(
                    "full_site_green_target_ratio"
                ),
                "gap_m2": metrics.get("full_site_green_gap_m2"),
                "account_kind": "designed_green",
                "open_space_account": {
                    "account_kind": "potential_open_space",
                    "area_m2": metrics.get(
                        "full_site_open_space_account_area_m2"
                    ),
                    "ratio": metrics.get(
                        "full_site_open_space_account_ratio"
                    ),
                    "target_ratio": metrics.get(
                        "full_site_open_space_account_target_ratio"
                    ),
                    "gap_m2": metrics.get(
                        "full_site_open_space_account_gap_m2"
                    ),
                    "parcel_count": metrics.get(
                        "full_site_open_space_account_parcel_count"
                    ),
                },
                "note": (
                    "this block is an open-space tiling account (parcels "
                    "outside buildings/roads/sidewalks); it is NOT designed "
                    "green and is not used to pass DESIGNED_GREEN_RATIO"
                ),
            }
        ),
        "non_claims": _full_site_non_claims(layout_source, metrics),
        "scene_id": scene.scene_id,
        "scene_object_count": len(scene.objects),
        "dxf": {
            "path": dxf_path.name,
            "sha256": hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
            "entity_count": compile_result.entity_count,
            "audit_errors": compile_result.audit_errors,
            "audit_fixes": compile_result.audit_fixes,
        },
        "readback": {
            "verdict": readback.verdict,
            "codes": list(readback.codes),
            "entity_count": readback.manifest.get("entity_count"),
            "expected_entity_count": readback.manifest.get(
                "expected_entity_count"
            ),
            "confirmation_scopes": readback.manifest.get(
                "confirmation_scopes"
            ),
            "manifest_sha256": canonical_hash(readback.manifest),
        },
        "cad_ir_validation": cad_validation.to_dict(),
        "privacy": privacy,
    }
    (output_dir / "full-site-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "full-site-scene-snapshot.json").write_text(
        json.dumps(
            {
                "scene_id": scene.scene_id,
                "world": scene.world.value,
                "objects": scene_objects_for_export(scene),
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "full-site-cad-ir.json").write_text(
        json.dumps(cad_ir.to_dict(), indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "full-site-readback-manifest.json").write_text(
        json.dumps(readback.manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    (output_dir / "full-site-validation.json").write_text(
        json.dumps(
            {
                "cad_ir": cad_validation.to_dict(),
                "dxf_readback": readback.to_dict(),
                "privacy": privacy,
                "verdicts": {
                    "cad_ir": cad_validation.verdict,
                    "dxf_readback": readback.verdict,
                    "privacy": "pass" if privacy["ok"] else "fail",
                },
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "full-site-privacy.json").write_text(
        json.dumps(privacy, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    if readback.verdict == "fail":
        raise DesignSynthesisBlocked(
            "full-site DXF readback failed: " + ", ".join(readback.codes)
        )
    if not privacy["ok"]:
        raise DesignSynthesisBlocked("full-site DXF privacy scan failed")
    return summary

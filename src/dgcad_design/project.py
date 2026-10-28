from __future__ import annotations

import hashlib
import json
import shutil
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
from .buildings import (
    BuildingLayout,
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from .consistency import check_design
from .drawing import build_drawing_elements
from .green import GreenLayout, build_green_layout
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
        "project_id": "DESIGN-CASE-SKETCH-001",
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
            "green_ratio": green_layout.green_ratio,
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
        },
        "changed": [
            "building footprints replaced by standardized staircase modules",
            "focus-group buildings reorganized into rows",
            "20 m north-south spacing inserted between rows",
            "green strips inserted between building rows",
            "road widths assigned from the declared class",
            "garage entrances added to meet the parking requirement",
        ],
        "preserved": [
            "building IDs and inferred staircase counts",
            "the focus group's location and its relation to the main road",
            "the main road as the organization spine",
            "cluster green spaces that remain clear of buildings and roads",
        ],
        "why": [
            "the declared design basis fixes the unit module, floor count, "
            "road widths, FAR range, parking ratio and 20 m north-south gap",
            "a regular row layout makes the 20 m gap verifiable and gives each "
            "group a clear internal green strip",
            "the schema is a proposal: no human confirmation or code-compliance "
            "claim is made",
        ],
    }


def _evidence_files(out: Path) -> None:
    out.mkdir(parents=True, exist_ok=True)


def _design_roads_geojson(road_layout: RoadLayout) -> dict[str, Any]:
    """Publish the 41 design centre lines so topology is checkable from evidence.

    This is the M4c-1a artefact: before it, only the 10 focus-area centre lines
    reached the DXF/CAD-IR and the full design network's topology could not be
    recomputed from committed files.
    """
    return {
        "type": "FeatureCollection",
        "schema_id": "dgcad.design-roads.v0.1",
        "road_count": len(road_layout.roads),
        "coordinate_frame": "design-local-metric",
        "junction_count": len(road_layout.explicit_junctions),
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
    consistency = check_design(
        design_input,
        basis,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
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
            _design_roads_geojson(road_layout),
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    roads_sha256 = hashlib.sha256(roads_path.read_bytes()).hexdigest()

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

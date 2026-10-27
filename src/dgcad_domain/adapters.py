from __future__ import annotations

from typing import Any

from dgcad_foundation import (
    AtomicChangeSet,
    AuthorityState,
    CanonicalObject,
    ChangeProposal,
    RequiredAuthority,
    RevisionStamp,
    SceneState,
    World,
    canonical_hash,
)

from .building import building_candidate
from .common import ParameterValue, finite_number, geometry_to_geojson, polygon_from_geojson
from .road import road_corridor_candidate
from .trace import ConfirmedTraceScene


SEMANTIC_KEYS = frozenset(
    {
        "typology",
        "typology_state",
        "hierarchy",
        "hierarchy_state",
        "primary_function",
        "permitted_modes",
        "special_designations",
    }
)
GEOMETRY_KEYS = frozenset(
    {
        "professional_footprint",
        "regularization_state",
        "regularization_diff",
        "centerline",
        "centerline_state",
        "x",
        "y",
    }
)
PARAMETER_KEYS = frozenset(
    {"height", "base_elevation", "cross_section", "profile_resolution"}
)


def _changed_axes(current: dict[str, Any], changes: dict[str, Any]) -> set[str]:
    axes: set[str] = set()
    for key, value in changes.items():
        if current.get(key) == value:
            continue
        if key in SEMANTIC_KEYS:
            axes.add("semantic")
        elif key in GEOMETRY_KEYS:
            axes.add("geometry")
        elif key in PARAMETER_KEYS:
            axes.add("parameter")
        else:
            raise ValueError(f"unmapped change key: {key}")
    if not axes:
        raise ValueError("proposal makes no change")
    return axes


def _proposal(
    obj: CanonicalObject,
    *,
    proposal_id: str,
    changes: dict[str, Any],
    bump: set[str],
    reason: str,
    confirm: bool,
    source_world: World = World.CANONICAL_CURRENT,
) -> ChangeProposal:
    return ChangeProposal(
        proposal_id=proposal_id,
        target_object_id=obj.object_id,
        before_revisions=obj.revisions,
        changes=changes,
        bump=frozenset(bump),
        required_authority=RequiredAuthority.HUMAN_CONFIRM,
        reason=reason,
        source_world=source_world,
        confirmed=confirm,
        before_values={key: obj.values.get(key) for key in changes},
    )


def _evidence_object(trace) -> CanonicalObject:
    return CanonicalObject(
        object_id=trace.trace_id,
        object_class=f"trace_{trace.semantic_role}",
        revisions=RevisionStamp(1, 1, 1),
        authority_state=AuthorityState.EVIDENCE_ONLY,
        values={
            "semantic_role": trace.semantic_role,
            "geometry": geometry_to_geojson(trace.geometry),
            "review_state": trace.review_state,
            "locked": trace.locked,
        },
        locks=frozenset({"all"}),
    )


def build_initial_scene(trace_scene: ConfirmedTraceScene) -> SceneState:
    objects: dict[str, CanonicalObject] = {}

    for trace in trace_scene.trace_objects.values():
        objects[trace.trace_id] = _evidence_object(trace)

    site = trace_scene.site_boundary
    objects["SITE-001"] = CanonicalObject(
        object_id="SITE-001",
        object_class="site_boundary",
        revisions=RevisionStamp(1, 1, 0),
        authority_state=AuthorityState.HUMAN_CONFIRMED,
        values={
            "trace_ref": site.trace_id,
            "geometry": geometry_to_geojson(site.geometry),
            "semantic_role": "site_boundary",
        },
    )

    green_traces = [
        trace
        for trace in trace_scene.trace_objects.values()
        if trace.semantic_role == "green"
    ]
    for index, trace in enumerate(green_traces, start=1):
        object_id = f"G-{index:03d}"
        objects[object_id] = CanonicalObject(
            object_id=object_id,
            object_class="green_space",
            revisions=RevisionStamp(1, 1, 0),
            authority_state=AuthorityState.HUMAN_CONFIRMED,
            values={
                "trace_ref": trace.trace_id,
                "geometry": geometry_to_geojson(trace.geometry),
                "semantic_role": "green",
            },
        )

    for intent in trace_scene.buildings.values():
        trace = trace_scene.trace(intent.trace_ref)
        objects[intent.object_id] = CanonicalObject(
            object_id=intent.object_id,
            object_class="building",
            revisions=RevisionStamp(0, 0, 0),
            authority_state=AuthorityState.CANDIDATE,
            values={
                "trace_ref": intent.trace_ref,
                "trace_footprint": geometry_to_geojson(trace.geometry),
                "professional_footprint": None,
                "regularization_state": "not_run",
                "regularization_diff": None,
                "height": intent.height.to_dict(),
                "base_elevation": intent.base_elevation.to_dict(),
                "typology": intent.typology,
                "typology_state": intent.typology_state,
            },
        )

    for intent in trace_scene.roads.values():
        objects[intent.corridor_id] = CanonicalObject(
            object_id=intent.corridor_id,
            object_class="road_corridor",
            revisions=RevisionStamp(0, 0, 0),
            authority_state=AuthorityState.CANDIDATE,
            values={
                "edge_refs": list(intent.edge_refs),
                "hierarchy": intent.hierarchy,
                "hierarchy_state": intent.hierarchy_state,
                "primary_function": intent.primary_function,
                "permitted_modes": list(intent.permitted_modes),
                "special_designations": list(intent.special_designations),
                "cross_section": (
                    None
                    if intent.cross_section is None
                    else intent.cross_section.to_dict()
                ),
                "profile_resolution": None,
                "centerline": None,
                "centerline_state": "trace_only",
            },
        )

    for node in trace_scene.road_graph.nodes.values():
        objects[node.node_id] = CanonicalObject(
            object_id=node.node_id,
            object_class="road_node",
            revisions=RevisionStamp(0, 0, 0),
            authority_state=AuthorityState.CANDIDATE,
            values={"x": node.x, "y": node.y, "junction": node.junction},
        )

    for edge in trace_scene.road_graph.edges.values():
        objects[edge.edge_id] = CanonicalObject(
            object_id=edge.edge_id,
            object_class="road_edge",
            revisions=RevisionStamp(0, 0, 0),
            authority_state=AuthorityState.CANDIDATE,
            values={
                "corridor_id": edge.corridor_id,
                "node_a": edge.node_a,
                "node_b": edge.node_b,
                "centerline": geometry_to_geojson(edge.centerline),
                "centerline_state": "confirmed",
            },
        )

    return SceneState(
        scene_id=trace_scene.scene_id,
        scene_revision=1,
        objects=objects,
        world=World.CANONICAL_CURRENT,
    )


def building_proposal(
    scene: SceneState,
    trace_scene: ConfirmedTraceScene,
    building_id: str,
    *,
    proposal_id: str,
    regularize: bool = False,
    confirm: bool = False,
) -> ChangeProposal:
    obj = scene.objects[building_id]
    intent = trace_scene.building(building_id)
    candidate = building_candidate(trace_scene, intent, regularize=regularize)
    changes = candidate.to_changes()
    return _proposal(
        obj,
        proposal_id=proposal_id,
        changes=changes,
        bump=_changed_axes(obj.values, changes),
        reason=(
            "professional building footprint from confirmed trace"
            if not regularize
            else "axis-aligned regularization candidate; requires review"
        ),
        confirm=confirm,
    )


def height_change_proposal(
    scene: SceneState,
    building_id: str,
    value: float,
    *,
    proposal_id: str,
    confirm: bool = False,
) -> ChangeProposal:
    obj = scene.objects[building_id]
    current = ParameterValue.from_dict(obj.values["height"])
    new_height = ParameterValue(
        value=value,
        unit=current.unit,
        state="confirmed",
        source_ref="design_change",
    )
    changes = {"height": new_height.to_dict()}
    return _proposal(
        obj,
        proposal_id=proposal_id,
        changes=changes,
        bump={"parameter"},
        reason="confirmed building height change",
        confirm=confirm,
    )


def road_corridor_proposal(
    scene: SceneState,
    trace_scene: ConfirmedTraceScene,
    corridor_id: str,
    *,
    proposal_id: str,
    confirm: bool = False,
) -> ChangeProposal:
    obj = scene.objects[corridor_id]
    intent = trace_scene.road(corridor_id)
    candidate = road_corridor_candidate(trace_scene, intent)
    changes = candidate.to_changes()
    return _proposal(
        obj,
        proposal_id=proposal_id,
        changes=changes,
        bump=_changed_axes(obj.values, changes),
        reason="road corridor from confirmed trace and explicit profile state",
        confirm=confirm,
    )


def confirm_road_class_proposal(
    scene: SceneState,
    corridor_id: str,
    hierarchy: str,
    *,
    proposal_id: str,
    confirm: bool = False,
) -> ChangeProposal:
    obj = scene.objects[corridor_id]
    changes = {"hierarchy": hierarchy, "hierarchy_state": "confirmed"}
    return _proposal(
        obj,
        proposal_id=proposal_id,
        changes=changes,
        bump={"semantic"},
        reason="human confirmation of road hierarchy; no width is derived here",
        confirm=confirm,
    )


def move_road_node_changeset(
    scene: SceneState,
    node_id: str,
    new_x: float,
    new_y: float,
    *,
    change_set_id: str,
    confirm: bool = False,
) -> AtomicChangeSet:
    node = scene.objects[node_id]
    if node.object_class != "road_node":
        raise ValueError(f"{node_id} is not a road node")
    new_x = finite_number(new_x, "node x")
    new_y = finite_number(new_y, "node y")
    incident_edges = [
        obj
        for obj in scene.objects.values()
        if obj.object_class == "road_edge"
        and node_id in {obj.values.get("node_a"), obj.values.get("node_b")}
    ]
    if len(incident_edges) < 3:
        raise ValueError("T_JUNCTION_TOPOLOGY_INVALID: at least three edges required")

    proposals: list[ChangeProposal] = [
        _proposal(
            node,
            proposal_id=f"{change_set_id}-NODE",
            changes={"x": float(new_x), "y": float(new_y)},
            bump={"geometry"},
            reason="T-junction node move",
            confirm=confirm,
        )
    ]

    affected_corridors: set[str] = set()
    for edge in incident_edges:
        centerline = edge.values["centerline"]
        if centerline.get("type") != "LineString":
            raise ValueError(
                "T_JUNCTION_TOPOLOGY_INVALID: only LineString edges are supported"
            )
        coordinates = [list(point) for point in centerline["coordinates"]]
        if edge.values["node_a"] == node_id:
            coordinates[0] = [float(new_x), float(new_y)]
        if edge.values["node_b"] == node_id:
            coordinates[-1] = [float(new_x), float(new_y)]
        proposals.append(
            _proposal(
                edge,
                proposal_id=f"{change_set_id}-{edge.object_id}",
                changes={
                    "centerline": {
                        "type": "LineString",
                        "coordinates": coordinates,
                    },
                    "centerline_state": "confirmed",
                },
                bump={"geometry"},
                reason="edge centerline follows moved T-junction node",
                confirm=confirm,
            )
        )
        affected_corridors.add(str(edge.values["corridor_id"]))

    for corridor_id in sorted(affected_corridors):
        corridor = scene.objects[corridor_id]
        proposals.append(
            _proposal(
                corridor,
                proposal_id=f"{change_set_id}-{corridor_id}",
                changes={"centerline": None, "centerline_state": "stale"},
                bump={"geometry"},
                reason="corridor centerline must be rebuilt after node move",
                confirm=confirm,
            )
        )

    return AtomicChangeSet(
        change_set_id=change_set_id, proposals=tuple(proposals)
    )


def external_geometry_proposal(
    scene: SceneState,
    object_id: str,
    external_geometry: dict[str, Any],
    *,
    proposal_id: str,
    as_external: bool,
    confirm: bool = False,
) -> ChangeProposal:
    obj = scene.objects[object_id]
    if obj.object_class != "building":
        raise ValueError("external geometry reconcile is only implemented for buildings")
    external = polygon_from_geojson(external_geometry)
    if not external.is_valid:
        raise ValueError("INVALID_FOOTPRINT: external geometry is invalid")
    changes = {
        "professional_footprint": external_geometry,
        "regularization_state": "needs_review",
    }
    return _proposal(
        obj,
        proposal_id=proposal_id,
        changes=changes,
        bump={"geometry"},
        reason=(
            "external geometry direct write attempt"
            if as_external
            else "external geometry reconciled into a human-confirm proposal"
        ),
        confirm=confirm,
        source_world=World.EXTERNAL if as_external else World.CANONICAL_CURRENT,
    )


def scene_fingerprint(scene: SceneState) -> str:
    payload = {
        object_id: {
            "revisions": [
                obj.revisions.semantic,
                obj.revisions.geometry,
                obj.revisions.parameter,
            ],
            "content_hash": obj.content_hash,
        }
        for object_id, obj in sorted(scene.objects.items())
    }
    return canonical_hash(payload)

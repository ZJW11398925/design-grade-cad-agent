from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest
import yaml
from shapely.geometry import Polygon

from dgcad_foundation import (
    ActorContext,
    AtomicChangeSet,
    CanonicalStore,
    CommitError,
    DependencyGraph,
    DerivedArtifact,
    RequiredAuthority,
    World,
)
from dgcad_runtime import (
    HumanControlPlane,
    RuntimeContractError,
    RuntimeSession,
    StatefulRuntime,
)
from dgcad_domain import (
    MassingBlocked,
    RoadSurfaceBlocked,
    TraceNotConfirmed,
    building_candidate,
    building_massing,
    building_proposal,
    build_initial_scene,
    confirm_road_class_proposal,
    external_geometry_proposal,
    geometry_to_geojson,
    height_change_proposal,
    load_confirmed_trace_fixture,
    move_road_node_changeset,
    polygon_from_geojson,
    resolve_profile_for_class,
    road_corridor_proposal,
    road_surface_artifact,
    scene_fingerprint,
    validate_building,
    validate_road,
    validate_scene,
)

FIXTURE = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "domain"
    / "domain-slice-001.yaml"
)
AGENT = ActorContext("agent-1")
HUMAN = ActorContext("designer-1", is_human=True, can_unlock=True)


@pytest.fixture(scope="module")
def trace_scene():
    return load_confirmed_trace_fixture(FIXTURE)


@pytest.fixture()
def scene(trace_scene):
    return build_initial_scene(trace_scene)


@pytest.fixture()
def store(scene):
    return CanonicalStore(scene)


def _commit(store: CanonicalStore, proposals, change_set_id: str = "CS"):
    return store.commit(AtomicChangeSet(change_set_id, tuple(proposals)), HUMAN)


def _with_value(scene, object_id: str, key: str, value):
    obj = scene.objects[object_id]
    new_obj = replace(obj, values={**obj.values, key: value})
    return replace(scene, objects={**scene.objects, object_id: new_obj})


# ---------------------------------------------------------------------------
# Fixture / trace integrity
# ---------------------------------------------------------------------------


def test_domain_fixture_is_marked_synthetic_and_confirmed(trace_scene):
    assert trace_scene.synthetic_only is True
    assert trace_scene.human_confirmed_trace is True
    assert trace_scene.site_boundary_ref in trace_scene.trace_objects
    assert all(t.review_state == "confirmed" for t in trace_scene.trace_objects.values())
    assert all(t.locked for t in trace_scene.trace_objects.values())


def test_trace_fixture_requires_confirmed_human_trace(tmp_path):
    data = yaml.safe_load(FIXTURE.read_text(encoding="utf-8"))
    data["human_confirmed_trace"] = False
    bad = tmp_path / "unconfirmed.yaml"
    bad.write_text(yaml.safe_dump(data), encoding="utf-8")
    with pytest.raises(TraceNotConfirmed):
        load_confirmed_trace_fixture(bad)


def test_trace_is_not_overwritten_by_professional_candidate(store, scene, trace_scene):
    trace_before = scene.objects["TRACE-B-001"].values["geometry"]
    proposal = building_proposal(
        scene, trace_scene, "B-001", proposal_id="P-B001", confirm=True
    )
    committed = _commit(store, [proposal], "CS-B001")
    assert committed.objects["TRACE-B-001"].values["geometry"] == trace_before
    assert committed.objects["B-001"].values["trace_footprint"] == trace_before
    assert committed.objects["B-001"].values["professional_footprint"] is not None
    assert (
        committed.objects["B-001"].values["professional_footprint"]
        == trace_before
    )


# ---------------------------------------------------------------------------
# Building
# ---------------------------------------------------------------------------


def test_unknown_height_remains_unknown(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-002", proposal_id="P-B002", confirm=True
    )
    committed = _commit(store, [proposal], "CS-B002")
    height = committed.objects["B-002"].values["height"]
    assert height["state"] == "unknown"
    assert height["value"] is None
    assert height["source_ref"] is None


def test_building_regularization_requires_confirmation(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-003", proposal_id="P-B003", regularize=True
    )
    assert proposal.required_authority == RequiredAuthority.HUMAN_CONFIRM
    with pytest.raises(CommitError) as exc:
        store.commit(AtomicChangeSet("CS-B003", (proposal,)), AGENT)
    assert exc.value.code == "HUMAN_CONFIRMATION_REQUIRED"

    preview = store.preview(AtomicChangeSet("CS-PRE", (proposal,)), AGENT, "SNAP-1")
    assert (
        preview.scene.objects["B-003"].values["regularization_state"]
        == "regularized_candidate"
    )
    assert store.current.objects["B-003"].values["professional_footprint"] is None

    confirmed = building_proposal(
        store.current,
        trace_scene,
        "B-003",
        proposal_id="P-B003-H",
        regularize=True,
        confirm=True,
    )
    committed = _commit(store, [confirmed], "CS-B003-H")
    assert (
        committed.objects["B-003"].values["regularization_state"]
        == "regularized_candidate"
    )
    result = validate_building(committed, "B-003")
    assert "REGULARIZATION_REQUIRES_REVIEW" in result.codes


def test_intentional_rotation_is_not_silently_axis_aligned(trace_scene):
    intent = trace_scene.building("B-003")
    preserved = building_candidate(trace_scene, intent, regularize=False)
    assert preserved.regularization_state == "preserve_trace"
    assert preserved.professional_footprint.equals(
        trace_scene.trace("TRACE-B-003").geometry
    )

    regularized = building_candidate(trace_scene, intent, regularize=True)
    assert regularized.regularization_state == "regularized_candidate"
    assert regularized.diff is not None
    assert regularized.diff.orientation_change_deg > 1.0
    assert not regularized.professional_footprint.equals(
        trace_scene.trace("TRACE-B-003").geometry
    )


def test_building_without_height_cannot_generate_massing(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-002", proposal_id="P-MASS-B002", confirm=True
    )
    committed = _commit(store, [proposal], "CS-MASS-B002")
    with pytest.raises(MassingBlocked) as exc:
        building_massing(committed, "B-002")
    assert exc.value.code == "MASSING_BLOCKED_UNKNOWN_HEIGHT"


def test_confirmed_height_generates_massing_with_dependency_keys(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-001", proposal_id="P-MASS-B001", confirm=True
    )
    committed = _commit(store, [proposal], "CS-MASS-B001")
    artifact = building_massing(committed, "B-001")
    assert isinstance(artifact, DerivedArtifact)
    assert artifact.artifact_type == "massing"
    assert artifact.world == World.CANONICAL_CURRENT
    assert artifact.dependency_keys == frozenset(
        {"B-001.geometry", "B-001.parameter"}
    )


def test_footprint_geometry_change_bumps_only_geometry_revision(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-001", proposal_id="P-REV-G", confirm=True
    )
    committed = _commit(store, [proposal], "CS-REV-G")
    obj = committed.objects["B-001"]
    assert obj.revisions.geometry == 1
    assert obj.revisions.parameter == 0
    assert obj.revisions.semantic == 0

    tall = height_change_proposal(
        committed, "B-001", 24.0, proposal_id="P-REV-P", confirm=True
    )
    committed_2 = _commit(store, [tall], "CS-REV-P")
    obj_2 = committed_2.objects["B-001"]
    assert obj_2.revisions.geometry == 1
    assert obj_2.revisions.parameter == 1
    assert obj_2.revisions.semantic == 0


def test_height_change_invalidates_massing_but_not_footprint():
    graph = DependencyGraph()
    graph.register(
        DerivedArtifact(
            "MASS-B-001",
            "massing",
            World.CANONICAL_CURRENT,
            frozenset({"B-001.geometry", "B-001.parameter"}),
        )
    )
    graph.register(
        DerivedArtifact(
            "PLAN-B-001",
            "professional_2d",
            World.CANONICAL_CURRENT,
            frozenset({"B-001.geometry"}),
        )
    )
    graph.invalidate({"B-001.parameter"})
    assert graph.state("MASS-B-001") == "stale"
    assert graph.state("PLAN-B-001") == "current"


def test_preview_building_does_not_mutate_canonical(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-003", proposal_id="P-PRE", regularize=True
    )
    preview = store.preview(AtomicChangeSet("CS-PRE", (proposal,)), AGENT, "SNAP-PRE")
    assert preview.scene.world == World.PROPOSAL_PREVIEW
    assert preview.scene.objects["B-003"].values["professional_footprint"] is not None
    assert store.current.objects["B-003"].values["professional_footprint"] is None


# ---------------------------------------------------------------------------
# Road
# ---------------------------------------------------------------------------


def test_road_class_unknown_blocks_profile_derived_width(store, trace_scene):
    intent = trace_scene.road("R-001")
    resolution = resolve_profile_for_class(
        intent.hierarchy, intent.hierarchy_state, intent.cross_section
    )
    assert resolution.outcome == "blocked"
    assert resolution.code == "ROAD_CLASS_UNCONFIRMED"
    assert resolution.components == ()

    proposal = road_corridor_proposal(
        store.current, trace_scene, "R-001", proposal_id="P-R001", confirm=True
    )
    committed = _commit(store, [proposal], "CS-R001")
    values = committed.objects["R-001"].values
    assert values["hierarchy_state"] == "unknown"
    assert values["profile_resolution"]["outcome"] == "blocked"
    assert values["cross_section"] is None

    result = validate_road(committed, "R-001")
    assert result.verdict == "blocked"
    assert "ROAD_CLASS_UNCONFIRMED" in result.codes


def test_agent_cannot_confirm_road_class(store):
    proposal = confirm_road_class_proposal(
        store.current, "R-001", "site_primary", proposal_id="P-CLASS"
    )
    with pytest.raises(CommitError) as exc:
        store.commit(AtomicChangeSet("CS-CLASS", (proposal,)), AGENT)
    assert exc.value.code == "HUMAN_CONFIRMATION_REQUIRED"

    confirmed = confirm_road_class_proposal(
        store.current,
        "R-001",
        "site_primary",
        proposal_id="P-CLASS-H",
        confirm=True,
    )
    committed = _commit(store, [confirmed], "CS-CLASS-H")
    assert committed.objects["R-001"].values["hierarchy_state"] == "confirmed"

    resolution = resolve_profile_for_class("site_primary", "confirmed", None)
    assert resolution.outcome == "blocked"
    assert resolution.code == "NO_PROFILE_FOR_CLASS"
    assert resolution.components == ()


def test_semantic_reclassification_bumps_semantic_revision(store):
    proposal = confirm_road_class_proposal(
        store.current, "R-001", "site_primary", proposal_id="P-SEM", confirm=True
    )
    committed = _commit(store, [proposal], "CS-SEM")
    obj = committed.objects["R-001"]
    assert obj.revisions.semantic == 1
    assert obj.revisions.geometry == 0
    assert obj.revisions.parameter == 0


def test_t_junction_change_uses_atomic_changeset(store):
    changeset = move_road_node_changeset(
        store.current, "RN-003", 21.0, 12.0, change_set_id="CS-T1", confirm=True
    )
    targets = {p.target_object_id for p in changeset.proposals}
    assert {
        "RN-003",
        "RE-001",
        "RE-002",
        "RE-003",
        "R-001",
        "R-002",
    } <= targets
    committed = store.commit(changeset, HUMAN)
    assert committed.objects["RN-003"].values["x"] == 21.0
    assert committed.objects["RN-003"].values["y"] == 12.0
    for edge_id in ("RE-001", "RE-002", "RE-003"):
        coords = committed.objects[edge_id].values["centerline"]["coordinates"]
        assert [21.0, 12.0] in coords
    assert committed.objects["R-001"].values["centerline_state"] == "stale"


def test_multi_object_atomic_changeset_rolls_back_on_stale_member(store):
    stale = move_road_node_changeset(
        store.current, "RN-003", 21.0, 12.0, change_set_id="CS-A", confirm=True
    )
    winner = move_road_node_changeset(
        store.current, "RN-003", 20.5, 11.5, change_set_id="CS-B", confirm=True
    )
    after_winner = store.commit(winner, HUMAN)
    fingerprint = scene_fingerprint(after_winner)

    with pytest.raises(CommitError) as exc:
        store.commit(stale, HUMAN)
    assert exc.value.code == "STALE_PROPOSAL"
    assert scene_fingerprint(store.current) == fingerprint


def test_road_geometry_change_invalidates_surface():
    graph = DependencyGraph()
    graph.register(
        DerivedArtifact(
            "SURFACE-R-001",
            "road_surface",
            World.CANONICAL_CURRENT,
            frozenset({"RE-001.geometry", "RE-002.geometry", "R-001.parameter"}),
        )
    )
    affected = graph.invalidate({"RE-001.geometry"})
    assert affected == {"SURFACE-R-001"}
    assert graph.state("SURFACE-R-001") == "stale"


def test_road_surface_requires_confirmed_centerline_and_profile(store, trace_scene):
    blocked = road_corridor_proposal(
        store.current, trace_scene, "R-001", proposal_id="P-SURF", confirm=True
    )
    committed = _commit(store, [blocked], "CS-SURF")
    with pytest.raises(RoadSurfaceBlocked) as exc:
        road_surface_artifact(committed, "R-001")
    assert exc.value.code == "ROAD_PROFILE_BLOCKED"

    resolved = road_corridor_proposal(
        committed, trace_scene, "R-002", proposal_id="P-SURF2", confirm=True
    )
    committed_2 = _commit(store, [resolved], "CS-SURF2")
    artifact = road_surface_artifact(committed_2, "R-002")
    assert artifact.dependency_keys == frozenset(
        {"RE-003.geometry", "R-002.parameter"}
    )


# ---------------------------------------------------------------------------
# Validation / reconcile
# ---------------------------------------------------------------------------


def test_domain_validation_returns_structured_issue(store, trace_scene):
    proposal = building_proposal(
        store.current, trace_scene, "B-002", proposal_id="P-VAL", confirm=True
    )
    committed = _commit(store, [proposal], "CS-VAL")
    result = validate_building(committed, "B-002")
    assert result.verdict == "conditional"
    issue = next(i for i in result.issues if i.code == "UNKNOWN_HEIGHT_BLOCKS_MASSING")
    assert issue.object_id == "B-002"
    assert issue.message

    bowtie = Polygon([(0.0, 0.0), (2.0, 2.0), (2.0, 0.0), (0.0, 2.0), (0.0, 0.0)])
    bad = _with_value(
        committed, "B-001", "professional_footprint", geometry_to_geojson(bowtie)
    )
    bad_result = validate_building(bad, "B-001")
    assert bad_result.verdict == "fail"
    assert "INVALID_FOOTPRINT" in bad_result.codes


def test_site_boundary_contains_building_footprints(store, trace_scene):
    first = building_proposal(
        store.current, trace_scene, "B-001", proposal_id="P-SITE-1", confirm=True
    )
    scene_1 = _commit(store, [first], "CS-SITE-1")
    third = building_proposal(
        scene_1, trace_scene, "B-003", proposal_id="P-SITE-3", confirm=True
    )
    scene_2 = _commit(store, [third], "CS-SITE-3")
    result = validate_scene(scene_2, trace_scene)
    assert "FOOTPRINT_OUTSIDE_SITE" not in result.codes

    outside = Polygon(
        [(100.0, 100.0), (104.0, 100.0), (104.0, 104.0), (100.0, 104.0)]
    )
    bad = _with_value(
        scene_2, "B-001", "professional_footprint", geometry_to_geojson(outside)
    )
    bad_result = validate_scene(bad, trace_scene)
    assert "FOOTPRINT_OUTSIDE_SITE" in bad_result.codes


def test_domain_proposal_through_stateful_runtime(tmp_path, scene, trace_scene):
    runtime = StatefulRuntime(
        tmp_path / "runtime", project_id="P-DOMAIN", initial_scene=scene
    )
    runtime.register_artifact(
        artifact_id="MASS-B-001",
        artifact_type="massing",
        dependency_keys={"B-001.geometry", "B-001.parameter"},
    )
    agent = RuntimeSession(
        "S-AGENT",
        "agent-1",
        frozenset(
            {
                "read",
                "propose",
                "preview",
                "request_commit",
                "cancel",
                "rebuild",
                "inspect_jobs",
            }
        ),
    )
    human = RuntimeSession(
        "S-HUMAN",
        "designer-1",
        frozenset({"read", "approve", "unlock", "review", "conflict_resolve"}),
        is_human=True,
        can_unlock=True,
    )

    domain_proposal = building_proposal(
        scene, trace_scene, "B-001", proposal_id="P-DOMAIN", confirm=True
    )
    proposed = runtime.propose_change(
        agent,
        object_id="B-001",
        changes=domain_proposal.changes,
        bump=set(domain_proposal.bump),
        required_authority="human_confirm",
        reason="domain building proposal",
        idempotency_key="idem-propose",
    )
    proposal_id = proposed["proposal_id"]
    preview = runtime.preview_change(
        agent, proposal_id=proposal_id, idempotency_key="idem-preview"
    )
    assert preview["world"] == "proposal_preview"

    with pytest.raises(RuntimeContractError) as exc:
        runtime.request_commit(
            agent, proposal_id=proposal_id, idempotency_key="idem-commit-1"
        )
    assert exc.value.code == "HUMAN_APPROVAL_REQUIRED"

    HumanControlPlane(runtime, human).approve(
        proposal_id, idempotency_key="idem-approve"
    )
    committed = runtime.request_commit(
        agent, proposal_id=proposal_id, idempotency_key="idem-commit-2"
    )
    assert committed["status"] == "committed"
    assert "MASS-B-001" in committed["stale_artifacts"]
    assert (
        runtime.store.current.objects["B-001"].values["professional_footprint"]
        is not None
    )

    rebuild = runtime.rebuild_stale(agent, idempotency_key="idem-rebuild")
    assert rebuild["status"] == "queued"
    assert rebuild["rebuild_order"] == ["MASS-B-001"]
    assert len(rebuild["job_ids"]) == 1


def test_move_node_rejects_non_finite_coordinates(store):
    with pytest.raises(ValueError):
        move_road_node_changeset(
            store.current,
            "RN-003",
            float("nan"),
            12.0,
            change_set_id="CS-NAN",
            confirm=True,
        )


def test_external_invalid_geometry_is_rejected(store):
    bowtie = Polygon(
        [(0.0, 0.0), (2.0, 2.0), (2.0, 0.0), (0.0, 2.0), (0.0, 0.0)]
    )
    with pytest.raises(ValueError):
        external_geometry_proposal(
            store.current,
            "B-001",
            geometry_to_geojson(bowtie),
            proposal_id="P-BAD-EXT",
            as_external=False,
            confirm=True,
        )


def test_design_object_without_trace_ref_is_rejected(store, trace_scene):
    bad = _with_value(store.current, "B-001", "trace_ref", None)
    result = validate_scene(bad, trace_scene)
    assert "TRACE_REF_MISSING" in result.codes


def test_node_move_stales_corridor_surface(store, trace_scene):
    resolved = road_corridor_proposal(
        store.current, trace_scene, "R-002", proposal_id="P-SURF-R2", confirm=True
    )
    committed = _commit(store, [resolved], "CS-SURF-R2")
    assert road_surface_artifact(committed, "R-002").artifact_id == "SURFACE-R-002"

    changeset = move_road_node_changeset(
        committed, "RN-003", 21.0, 12.0, change_set_id="CS-MOVE-R2", confirm=True
    )
    moved = store.commit(changeset, HUMAN)
    with pytest.raises(RoadSurfaceBlocked) as exc:
        road_surface_artifact(moved, "R-002")
    assert exc.value.code == "ROAD_CENTERLINE_NOT_CONFIRMED"


def test_external_geometry_enters_via_reconcile(store):
    external_geometry = geometry_to_geojson(
        Polygon([(12.0, 14.0), (17.0, 14.0), (17.0, 18.0), (12.0, 18.0)])
    )
    direct = external_geometry_proposal(
        store.current,
        "B-001",
        external_geometry,
        proposal_id="P-EXT",
        as_external=True,
    )
    assert direct.source_world == World.EXTERNAL
    with pytest.raises(CommitError) as exc:
        store.preview(AtomicChangeSet("CS-EXT", (direct,)), AGENT, "SNAP-EXT")
    assert exc.value.code == "EXTERNAL_DIRECT_WRITE_FORBIDDEN"

    reconciled = external_geometry_proposal(
        store.current,
        "B-001",
        external_geometry,
        proposal_id="P-REC",
        as_external=False,
        confirm=True,
    )
    assert reconciled.source_world == World.CANONICAL_CURRENT
    committed = _commit(store, [reconciled], "CS-REC")
    footprint = polygon_from_geojson(
        committed.objects["B-001"].values["professional_footprint"]
    )
    assert footprint.area == pytest.approx(20.0)

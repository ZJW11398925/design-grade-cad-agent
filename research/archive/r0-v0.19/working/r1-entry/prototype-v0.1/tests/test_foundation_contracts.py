import pathlib
import yaml
import pytest

from dgcad_foundation import (
    ActorContext, AtomicChangeSet, AuthorityState, CanonicalObject, CanonicalStore,
    ChangeProposal, CommitError, DependencyGraph, DerivedArtifact, RequiredAuthority,
    RevisionStamp, SceneState, ValidationIssue, ValidationResult, World,
)


def make_scene(*, locked=False):
    obj = CanonicalObject(
        object_id="B-001",
        object_class="building",
        revisions=RevisionStamp(1, 1, 1),
        authority_state=AuthorityState.LOCKED if locked else AuthorityState.HUMAN_CONFIRMED,
        values={"height_m": 18.0},
        locks=frozenset({"geometry"}) if locked else frozenset(),
    )
    return SceneState("scene-001", 3, {obj.object_id: obj})


def proposal(**overrides):
    data = dict(
        proposal_id="P-001",
        target_object_id="B-001",
        before_revisions=RevisionStamp(1, 1, 1),
        changes={"height_m": 21.0},
        bump=frozenset({"parameter"}),
        required_authority=RequiredAuthority.HUMAN_CONFIRM,
        reason="test height change",
        confirmed=True,
    )
    data.update(overrides)
    return ChangeProposal(**data)


def test_stable_identity_revision_changes_only_selected_axis():
    store = CanonicalStore(make_scene())
    result = store.commit(AtomicChangeSet("CS-1", (proposal(),)), ActorContext("human", is_human=True))
    obj = result.objects["B-001"]
    assert obj.object_id == "B-001"
    assert obj.revisions == RevisionStamp(1, 1, 2)
    assert result.scene_revision == 4


def test_preview_is_isolated_from_canonical_current():
    store = CanonicalStore(make_scene())
    before = store.current
    snap = store.preview(AtomicChangeSet("CS-1", (proposal(),)), ActorContext("human", is_human=True), "S-1")
    assert snap.scene.world == World.PROPOSAL_PREVIEW
    assert snap.scene.objects["B-001"].values["height_m"] == 21.0
    assert store.current.objects["B-001"].values["height_m"] == 18.0
    assert store.current == before


def test_atomic_changeset_rolls_back_all_when_one_proposal_is_stale():
    scene = make_scene()
    second = CanonicalObject("B-002", "building", RevisionStamp(1,1,1), AuthorityState.HUMAN_CONFIRMED, values={"height_m":12.0})
    scene = SceneState(scene.scene_id, scene.scene_revision, {**scene.objects, "B-002": second})
    store = CanonicalStore(scene)
    p1 = proposal()
    p2 = ChangeProposal("P-002", "B-002", RevisionStamp(9,9,9), {"height_m":15.0}, frozenset({"parameter"}), RequiredAuthority.HUMAN_CONFIRM, "stale test", confirmed=True)
    with pytest.raises(CommitError) as ex:
        store.commit(AtomicChangeSet("CS-2", (p1,p2)), ActorContext("human", is_human=True))
    assert ex.value.code == "STALE_PROPOSAL"
    assert store.current.objects["B-001"].values["height_m"] == 18.0
    assert store.current.objects["B-002"].values["height_m"] == 12.0


def test_locked_object_requires_explicit_human_unlock():
    store = CanonicalStore(make_scene(locked=True))
    p = proposal(required_authority=RequiredAuthority.HUMAN_UNLOCK, unlock_confirmed=False)
    with pytest.raises(CommitError) as ex:
        store.commit(AtomicChangeSet("CS-3", (p,)), ActorContext("human", is_human=True, can_unlock=True))
    assert ex.value.code == "LOCK_REQUIRES_EXPLICIT_HUMAN_UNLOCK"


def test_external_world_can_never_write_canonical_directly():
    store = CanonicalStore(make_scene())
    p = proposal(source_world=World.EXTERNAL)
    with pytest.raises(CommitError) as ex:
        store.commit(AtomicChangeSet("CS-4", (p,)), ActorContext("human", is_human=True))
    assert ex.value.code == "EXTERNAL_DIRECT_WRITE_FORBIDDEN"
    with pytest.raises(CommitError) as ex2:
        store.direct_external_write({"object_id":"B-001"})
    assert ex2.value.code == "EXTERNAL_DIRECT_WRITE_FORBIDDEN"


def test_dependency_invalidation_is_local_not_global():
    graph = DependencyGraph()
    graph.register(DerivedArtifact("MASS-B001", "massing", World.CANONICAL_CURRENT, frozenset({"B-001.parameter"})))
    graph.register(DerivedArtifact("DXF-001", "dxf", World.CANONICAL_CURRENT, frozenset({"B-001.geometry", "R-001.geometry"})))
    affected = graph.invalidate({"B-001.parameter"})
    assert affected == {"MASS-B001"}
    assert graph.state("MASS-B001") == "stale"
    assert graph.state("DXF-001") == "current"


def test_validation_failure_is_structured_not_exception_text():
    result = ValidationResult(
        validator_id="foundation.contract",
        validator_version="0.1",
        scope="external reconcile",
        world=World.EXTERNAL,
        verdict="fail",
        issues=(ValidationIssue("ENTITY_TYPE_MISMATCH", "error", "B-001", "LWPOLYLINE", "CIRCLE", "entity#17", "manual_or_recompile"),),
    )
    assert result.verdict == "fail"
    assert result.issues[0].code == "ENTITY_TYPE_MISMATCH"
    assert result.issues[0].actual == "CIRCLE"


def test_fixture_contracts_are_parseable_and_have_schema_ids():
    fixture_dir = pathlib.Path(__file__).parents[1] / "fixtures"
    for path in fixture_dir.glob("*.yaml"):
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert data["schema_id"].startswith("dgcad.foundation.fixture.")


def test_preview_of_human_confirm_proposal_does_not_require_prior_confirmation():
    store = CanonicalStore(make_scene())
    p = proposal(confirmed=False)
    snap = store.preview(AtomicChangeSet("CS-PREVIEW", (p,)), ActorContext("agent", is_human=False), "S-PREVIEW")
    assert snap.scene.objects["B-001"].values["height_m"] == 21.0
    assert store.current.objects["B-001"].values["height_m"] == 18.0
    with pytest.raises(CommitError) as ex:
        store.commit(AtomicChangeSet("CS-PREVIEW", (p,)), ActorContext("agent", is_human=False))
    assert ex.value.code == "HUMAN_CONFIRMATION_REQUIRED"


def test_field_scoped_geometry_lock_does_not_block_parameter_only_change():
    scene = make_scene(locked=False)
    obj = scene.objects["B-001"]
    scoped = CanonicalObject(
        obj.object_id, obj.object_class, obj.revisions, AuthorityState.HUMAN_CONFIRMED,
        obj.lifecycle_state, obj.values, frozenset({"geometry"})
    )
    store = CanonicalStore(SceneState(scene.scene_id, scene.scene_revision, {"B-001": scoped}))
    result = store.commit(AtomicChangeSet("CS-PARAM", (proposal(),)), ActorContext("human", is_human=True))
    assert result.objects["B-001"].values["height_m"] == 21.0


def test_field_scoped_geometry_lock_blocks_geometry_change_without_unlock():
    scene = make_scene(locked=False)
    obj = scene.objects["B-001"]
    scoped = CanonicalObject(
        obj.object_id, obj.object_class, obj.revisions, AuthorityState.HUMAN_CONFIRMED,
        obj.lifecycle_state, obj.values, frozenset({"geometry"})
    )
    store = CanonicalStore(SceneState(scene.scene_id, scene.scene_revision, {"B-001": scoped}))
    p = proposal(changes={"footprint_ref":"GEO-B-002"}, bump=frozenset({"geometry"}), required_authority=RequiredAuthority.HUMAN_CONFIRM)
    with pytest.raises(CommitError) as ex:
        store.preview(AtomicChangeSet("CS-GEO", (p,)), ActorContext("human", is_human=True), "S-GEO")
    assert ex.value.code == "LOCK_REQUIRES_EXPLICIT_HUMAN_UNLOCK"


def test_dependency_invalidation_propagates_transitively_across_derived_artifacts():
    graph = DependencyGraph()
    graph.register(DerivedArtifact("MASS-B001", "massing", World.CANONICAL_CURRENT, frozenset({"B-001.parameter"})))
    graph.register(DerivedArtifact("SHADOW-001", "shadow", World.CANONICAL_CURRENT, frozenset({"MASS-B001", "context.north"})))
    graph.register(DerivedArtifact("DXF-001", "dxf", World.CANONICAL_CURRENT, frozenset({"B-001.geometry"})))
    affected = graph.invalidate({"B-001.parameter"})
    assert affected == {"MASS-B001", "SHADOW-001"}
    assert graph.state("SHADOW-001") == "stale"
    assert graph.state("DXF-001") == "current"

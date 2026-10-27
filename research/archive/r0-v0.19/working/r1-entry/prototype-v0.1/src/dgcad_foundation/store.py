from __future__ import annotations
from copy import deepcopy
from dataclasses import replace
from .authority import ActorContext, authority_allows
from .model import AtomicChangeSet, ProposalSnapshot, SceneState, World


class CommitError(RuntimeError):
    def __init__(self, code: str, message: str):
        self.code = code
        super().__init__(f"{code}: {message}")


class CanonicalStore:
    def __init__(self, scene: SceneState):
        if scene.world != World.CANONICAL_CURRENT:
            raise ValueError("CanonicalStore requires canonical_current scene")
        self._scene = deepcopy(scene)

    @property
    def current(self) -> SceneState:
        return deepcopy(self._scene)

    def _validate_changeset(self, changeset: AtomicChangeSet, actor: ActorContext, *, for_preview: bool = False) -> None:
        if changeset.commit_policy != "all_or_nothing":
            raise CommitError("UNSUPPORTED_COMMIT_POLICY", changeset.commit_policy)
        for proposal in changeset.proposals:
            if proposal.target_object_id not in self._scene.objects:
                raise CommitError("OBJECT_NOT_FOUND", proposal.target_object_id)
            obj = self._scene.objects[proposal.target_object_id]
            if obj.revisions != proposal.before_revisions:
                raise CommitError("STALE_PROPOSAL", proposal.target_object_id)
            allowed, code = authority_allows(obj, proposal, actor, for_preview=for_preview)
            if not allowed:
                raise CommitError(code, proposal.target_object_id)

    @staticmethod
    def _apply(scene: SceneState, changeset: AtomicChangeSet, world: World) -> SceneState:
        objects = deepcopy(scene.objects)
        for proposal in changeset.proposals:
            obj = objects[proposal.target_object_id]
            objects[proposal.target_object_id] = obj.with_changes(proposal.changes, set(proposal.bump))
        return SceneState(scene.scene_id, scene.scene_revision, objects, world=world)

    def preview(self, changeset: AtomicChangeSet, actor: ActorContext, snapshot_id: str) -> ProposalSnapshot:
        self._validate_changeset(changeset, actor, for_preview=True)
        preview_scene = self._apply(self._scene, changeset, World.PROPOSAL_PREVIEW)
        return ProposalSnapshot(snapshot_id, self._scene.scene_revision, changeset.change_set_id, preview_scene)

    def commit(self, changeset: AtomicChangeSet, actor: ActorContext) -> SceneState:
        self._validate_changeset(changeset, actor)
        candidate = self._apply(self._scene, changeset, World.CANONICAL_CURRENT)
        self._scene = replace(candidate, scene_revision=self._scene.scene_revision + 1)
        return self.current

    def direct_external_write(self, *_args, **_kwargs):
        raise CommitError("EXTERNAL_DIRECT_WRITE_FORBIDDEN", "external artifacts require reconcile -> proposal")

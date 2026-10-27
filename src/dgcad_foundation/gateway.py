from __future__ import annotations
from dataclasses import asdict
from typing import Any

from .authority import ActorContext
from .model import AtomicChangeSet, ChangeProposal, RequiredAuthority, RevisionStamp, World
from .store import CanonicalStore, CommitError


class AgentGateway:
    """Transport-agnostic, capability-limited facade intended for MCP/HTTP adapters.

    The ActorContext is injected by the host/server and is never accepted from tool input.
    The facade intentionally exposes no raw canonical write or arbitrary code execution.
    """

    def __init__(self, store: CanonicalStore, actor: ActorContext):
        self.store = store
        self.actor = actor

    def scene_summary(self) -> dict[str, Any]:
        scene = self.store.current
        return {
            "scene_id": scene.scene_id,
            "scene_revision": scene.scene_revision,
            "world": scene.world.value,
            "object_ids": sorted(scene.objects),
        }

    def object_view(self, object_id: str) -> dict[str, Any]:
        obj = self.store.current.objects[object_id]
        data = asdict(obj)
        data["authority_state"] = obj.authority_state.value
        data["lifecycle_state"] = obj.lifecycle_state.value
        data["locks"] = sorted(obj.locks)
        data["locked_paths"] = sorted(obj.locked_paths)
        data["content_hash"] = obj.content_hash
        return data

    def propose_change(self, *, proposal_id: str, object_id: str, changes: dict[str, Any],
                       bump: set[str], required_authority: str, reason: str) -> ChangeProposal:
        obj = self.store.current.objects[object_id]
        return ChangeProposal(
            proposal_id=proposal_id,
            target_object_id=object_id,
            before_revisions=obj.revisions,
            changes=changes,
            bump=frozenset(bump),
            required_authority=RequiredAuthority(required_authority),
            reason=reason,
            source_world=World.CANONICAL_CURRENT,
            before_values={key: obj.values.get(key) for key in changes},
        )

    def preview_change(self, change_set: AtomicChangeSet, snapshot_id: str) -> dict[str, Any]:
        try:
            snap = self.store.preview(change_set, self.actor, snapshot_id)
            return {"status": "ok", "snapshot_id": snap.snapshot_id, "state": snap.state,
                    "base_scene_revision": snap.base_scene_revision}
        except CommitError as exc:
            return {"status": "blocked", "code": exc.code, "message": str(exc)}

    def request_commit(self, change_set: AtomicChangeSet) -> dict[str, Any]:
        """Agent-facing commit request.

        This never fabricates human approval. If approval/unlock is required, the structured
        block is returned to the host UI/control plane, which must create a separately
        authorized changeset or call the privileged human control path.
        """
        try:
            scene = self.store.commit(change_set, self.actor)
            return {"status": "committed", "scene_revision": scene.scene_revision}
        except CommitError as exc:
            return {"status": "blocked", "code": exc.code, "message": str(exc)}

    def direct_set_object(self, *_args, **_kwargs):
        raise PermissionError("raw canonical mutation is not part of the agent tool surface")

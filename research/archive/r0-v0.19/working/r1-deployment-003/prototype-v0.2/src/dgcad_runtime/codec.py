from __future__ import annotations
from dataclasses import asdict
from typing import Any

from dgcad_foundation.audit import AuditEvent
from dgcad_foundation.model import (
    AtomicChangeSet, AuthorityState, CanonicalObject, ChangeProposal, LifecycleState,
    RequiredAuthority, RevisionStamp, SceneState, World,
)
from .model import (
    ApprovalGrant, ArtifactRecord, ArtifactStatus, IdempotencyRecord, JobRecord,
    JobStatus, ProposalRecord, ProposalStatus, RuntimeState,
)


def revision_to_dict(r: RevisionStamp) -> dict[str, int]:
    return {"semantic": r.semantic, "geometry": r.geometry, "parameter": r.parameter}


def revision_from_dict(d: dict[str, Any]) -> RevisionStamp:
    return RevisionStamp(int(d.get("semantic", 0)), int(d.get("geometry", 0)), int(d.get("parameter", 0)))


def object_to_dict(o: CanonicalObject) -> dict[str, Any]:
    return {
        "object_id": o.object_id,
        "object_class": o.object_class,
        "revisions": revision_to_dict(o.revisions),
        "authority_state": o.authority_state.value,
        "lifecycle_state": o.lifecycle_state.value,
        "values": o.values,
        "locks": sorted(o.locks),
        "locked_paths": sorted(o.locked_paths),
    }


def object_from_dict(d: dict[str, Any]) -> CanonicalObject:
    return CanonicalObject(
        object_id=d["object_id"],
        object_class=d["object_class"],
        revisions=revision_from_dict(d.get("revisions", {})),
        authority_state=AuthorityState(d.get("authority_state", AuthorityState.CANDIDATE.value)),
        lifecycle_state=LifecycleState(d.get("lifecycle_state", LifecycleState.CURRENT.value)),
        values=dict(d.get("values", {})),
        locks=frozenset(d.get("locks", [])),
        locked_paths=frozenset(d.get("locked_paths", [])),
    )


def scene_to_dict(scene: SceneState) -> dict[str, Any]:
    return {
        "scene_id": scene.scene_id,
        "scene_revision": scene.scene_revision,
        "world": scene.world.value,
        "objects": {k: object_to_dict(v) for k, v in sorted(scene.objects.items())},
    }


def scene_from_dict(d: dict[str, Any]) -> SceneState:
    return SceneState(
        scene_id=d["scene_id"],
        scene_revision=int(d["scene_revision"]),
        objects={k: object_from_dict(v) for k, v in d.get("objects", {}).items()},
        world=World(d.get("world", World.CANONICAL_CURRENT.value)),
    )


def proposal_to_dict(p: ChangeProposal) -> dict[str, Any]:
    return {
        "proposal_id": p.proposal_id,
        "target_object_id": p.target_object_id,
        "before_revisions": revision_to_dict(p.before_revisions),
        "changes": p.changes,
        "bump": sorted(p.bump),
        "required_authority": p.required_authority.value,
        "reason": p.reason,
        "source_world": p.source_world.value,
        "confirmed": p.confirmed,
        "unlock_confirmed": p.unlock_confirmed,
        "before_values": p.before_values,
    }


def proposal_from_dict(d: dict[str, Any]) -> ChangeProposal:
    return ChangeProposal(
        proposal_id=d["proposal_id"],
        target_object_id=d["target_object_id"],
        before_revisions=revision_from_dict(d["before_revisions"]),
        changes=dict(d.get("changes", {})),
        bump=frozenset(d.get("bump", [])),
        required_authority=RequiredAuthority(d["required_authority"]),
        reason=d.get("reason", ""),
        source_world=World(d.get("source_world", World.CANONICAL_CURRENT.value)),
        confirmed=bool(d.get("confirmed", False)),
        unlock_confirmed=bool(d.get("unlock_confirmed", False)),
        before_values=dict(d.get("before_values", {})),
    )


def changeset_to_dict(cs: AtomicChangeSet) -> dict[str, Any]:
    return {
        "change_set_id": cs.change_set_id,
        "commit_policy": cs.commit_policy,
        "proposals": [proposal_to_dict(p) for p in cs.proposals],
    }


def changeset_from_dict(d: dict[str, Any]) -> AtomicChangeSet:
    return AtomicChangeSet(
        change_set_id=d["change_set_id"],
        proposals=tuple(proposal_from_dict(x) for x in d.get("proposals", [])),
        commit_policy=d.get("commit_policy", "all_or_nothing"),
    )


def proposal_record_to_dict(r: ProposalRecord) -> dict[str, Any]:
    return {
        "proposal_id": r.proposal_id,
        "change_set": changeset_to_dict(r.change_set),
        "created_by": r.created_by,
        "created_at": r.created_at,
        "base_scene_revision": r.base_scene_revision,
        "expires_at": r.expires_at,
        "status": r.status.value,
        "snapshot_id": r.snapshot_id,
        "committed_scene_revision": r.committed_scene_revision,
        "block_code": r.block_code,
    }


def proposal_record_from_dict(d: dict[str, Any]) -> ProposalRecord:
    return ProposalRecord(
        proposal_id=d["proposal_id"],
        change_set=changeset_from_dict(d["change_set"]),
        created_by=d["created_by"],
        created_at=int(d["created_at"]),
        base_scene_revision=int(d.get("base_scene_revision", 0)),
        expires_at=d.get("expires_at"),
        status=ProposalStatus(d.get("status", ProposalStatus.PROPOSED.value)),
        snapshot_id=d.get("snapshot_id"),
        committed_scene_revision=d.get("committed_scene_revision"),
        block_code=d.get("block_code"),
    )


def artifact_to_dict(a: ArtifactRecord) -> dict[str, Any]:
    return {
        "artifact_id": a.artifact_id,
        "artifact_type": a.artifact_type,
        "world": a.world.value,
        "dependency_keys": sorted(a.dependency_keys),
        "status": a.status.value,
        "content_hash": a.content_hash,
        "payload_ref": a.payload_ref,
        "source_scene_revision": a.source_scene_revision,
    }


def artifact_from_dict(d: dict[str, Any]) -> ArtifactRecord:
    return ArtifactRecord(
        artifact_id=d["artifact_id"], artifact_type=d["artifact_type"],
        world=World(d["world"]), dependency_keys=frozenset(d.get("dependency_keys", [])),
        status=ArtifactStatus(d.get("status", ArtifactStatus.CURRENT.value)),
        content_hash=d.get("content_hash"), payload_ref=d.get("payload_ref"),
        source_scene_revision=d.get("source_scene_revision"),
    )


def state_to_payload(state: RuntimeState, scene: SceneState, audit_events: tuple[AuditEvent, ...]) -> dict[str, Any]:
    return {
        "schema_id": state.schema_id,
        "project_id": state.project_id,
        "counters": dict(state.counters),
        "scene": scene_to_dict(scene),
        "audit_events": [asdict(e) for e in audit_events],
        "proposals": {k: proposal_record_to_dict(v) for k, v in sorted(state.proposals.items())},
        "approvals": {k: asdict(v) for k, v in sorted(state.approvals.items())},
        "artifacts": {k: artifact_to_dict(v) for k, v in sorted(state.artifacts.items())},
        "jobs": {k: {**asdict(v), "status": v.status.value} for k, v in sorted(state.jobs.items())},
        "idempotency": {k: asdict(v) for k, v in sorted(state.idempotency.items())},
    }


def payload_to_state(payload: dict[str, Any]) -> tuple[RuntimeState, SceneState, list[AuditEvent]]:
    state = RuntimeState(
        schema_id=payload["schema_id"], project_id=payload["project_id"],
        counters={k: int(v) for k, v in payload.get("counters", {}).items()},
        proposals={k: proposal_record_from_dict(v) for k, v in payload.get("proposals", {}).items()},
        approvals={k: ApprovalGrant(**v) for k, v in payload.get("approvals", {}).items()},
        artifacts={k: artifact_from_dict(v) for k, v in payload.get("artifacts", {}).items()},
        jobs={k: JobRecord(**{**v, "status": JobStatus(v["status"]), "predecessor_job_ids": tuple(v.get("predecessor_job_ids", []))}) for k, v in payload.get("jobs", {}).items()},
        idempotency={k: IdempotencyRecord(**v) for k, v in payload.get("idempotency", {}).items()},
    )
    scene = scene_from_dict(payload["scene"])
    audit = [AuditEvent(**e) for e in payload.get("audit_events", [])]
    return state, scene, audit

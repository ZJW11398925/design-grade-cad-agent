from __future__ import annotations
from dataclasses import replace
from pathlib import Path
from typing import Any

from dgcad_foundation import (
    ActorContext, AtomicChangeSet, AuditLog, CanonicalStore, ChangeProposal,
    CommitError, DependencyGraph, DerivedArtifact, RequiredAuthority, RebuildScheduler,
    SceneState, World, canonical_hash,
)
from .clock import SystemClock
from .codec import changeset_to_dict
from .errors import RuntimeContractError
from .model import (
    ApprovalGrant, ArtifactRecord, ArtifactStatus, IdempotencyRecord, JobRecord,
    JobStatus, ProposalRecord, ProposalStatus, RuntimeSession, RuntimeState,
)
from .persistence import AtomicProjectFile


TERMINAL_PROPOSAL = {ProposalStatus.COMMITTED, ProposalStatus.CANCELLED, ProposalStatus.EXPIRED}


class StatefulRuntime:
    SCHEMA_ID = "dgcad.runtime.state.v0.1"

    def __init__(self, root: str | Path, *, project_id: str | None = None,
                 initial_scene: SceneState | None = None, clock=None):
        self.persistence = AtomicProjectFile(root)
        self.clock = clock or SystemClock()
        self.recovered_running_jobs: list[str] = []
        if self.persistence.exists():
            state, scene, audit_events, persisted_hash = self.persistence.load()
            self.state = state
            self.store = CanonicalStore(scene, audit_log=AuditLog(audit_events))
            self._persisted_hash = persisted_hash
            self._recover_interrupted_jobs()
        else:
            if project_id is None or initial_scene is None:
                raise ValueError("project_id and initial_scene are required for a new runtime")
            self.state = RuntimeState(self.SCHEMA_ID, project_id)
            self.store = CanonicalStore(initial_scene)
            self._persisted_hash = None
            self._save()
        self._rebuild_dependency_graph()

    def _save(self) -> None:
        self._persisted_hash = self.persistence.save(
            self.state, self.store.current, self.store.audit_log.events, expected_hash=self._persisted_hash
        )

    def _recover_interrupted_jobs(self) -> None:
        changed = False
        for job in self.state.jobs.values():
            if job.status == JobStatus.RUNNING:
                job.status = JobStatus.QUEUED
                job.worker_id = None
                if job.artifact_id in self.state.artifacts:
                    self.state.artifacts[job.artifact_id].status = ArtifactStatus.STALE
                self.recovered_running_jobs.append(job.job_id)
                changed = True
        if self.recovered_running_jobs:
            recovered = set(self.recovered_running_jobs)
            for key, record in list(self.state.idempotency.items()):
                if record.operation == "claim_next_job" and record.response.get("job_id") in recovered:
                    del self.state.idempotency[key]
                    changed = True
        if changed:
            self._save()

    def _rebuild_dependency_graph(self) -> None:
        self.graph = DependencyGraph()
        for record in self.state.artifacts.values():
            state = "stale" if record.status != ArtifactStatus.CURRENT else "current"
            self.graph.register(DerivedArtifact(
                record.artifact_id, record.artifact_type, record.world,
                record.dependency_keys, state,
            ))

    def _next_id(self, kind: str, prefix: str) -> str:
        value = self.state.counters.get(kind, 0) + 1
        self.state.counters[kind] = value
        return f"{prefix}-{value:06d}"

    @staticmethod
    def _require(session: RuntimeSession, capability: str) -> None:
        if capability not in session.capabilities:
            raise RuntimeContractError("CAPABILITY_DENIED", f"session lacks capability: {capability}")

    def _idem_lookup(self, operation: str, key: str | None, request: dict[str, Any]) -> dict[str, Any] | None:
        if not key:
            raise RuntimeContractError("IDEMPOTENCY_KEY_REQUIRED", f"{operation} requires an idempotency key")
        req_hash = canonical_hash(request)
        existing = self.state.idempotency.get(key)
        if existing is None:
            return None
        if existing.operation != operation or existing.request_hash != req_hash:
            raise RuntimeContractError(
                "IDEMPOTENCY_KEY_REUSE_MISMATCH",
                "idempotency key was already used for a different operation or payload",
                details={"key": key, "existing_operation": existing.operation},
            )
        return dict(existing.response)

    def _idem_store(self, operation: str, key: str, request: dict[str, Any], response: dict[str, Any]) -> None:
        self.state.idempotency[key] = IdempotencyRecord(key, operation, canonical_hash(request), dict(response))

    def scene_summary(self, session: RuntimeSession) -> dict[str, Any]:
        self._require(session, "read")
        scene = self.store.current
        return {
            "status": "ok", "project_id": self.state.project_id,
            "scene_id": scene.scene_id, "scene_revision": scene.scene_revision,
            "world": scene.world.value, "object_ids": sorted(scene.objects),
        }

    def propose_change(self, session: RuntimeSession, *, object_id: str, changes: dict[str, Any],
                       bump: set[str], required_authority: str, reason: str,
                       idempotency_key: str, ttl_seconds: int | None = None) -> dict[str, Any]:
        self._require(session, "propose")
        request = {
            "object_id": object_id, "changes": changes, "bump": sorted(bump),
            "required_authority": required_authority, "reason": reason,
            "ttl_seconds": ttl_seconds,
        }
        replay = self._idem_lookup("propose_change", idempotency_key, request)
        if replay is not None:
            return replay
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise RuntimeContractError("INVALID_TTL", "ttl_seconds must be positive")
        scene = self.store.current
        if object_id not in scene.objects:
            raise RuntimeContractError("OBJECT_NOT_FOUND", object_id)
        obj = scene.objects[object_id]
        proposal_id = self._next_id("proposal", "P")
        change_set_id = self._next_id("changeset", "CS")
        p = ChangeProposal(
            proposal_id=proposal_id,
            target_object_id=object_id,
            before_revisions=obj.revisions,
            changes=dict(changes),
            bump=frozenset(bump),
            required_authority=RequiredAuthority(required_authority),
            reason=reason,
            source_world=World.CANONICAL_CURRENT,
            before_values={key: obj.values.get(key) for key in changes},
        )
        cs = AtomicChangeSet(change_set_id, (p,))
        now = self.clock.now()
        rec = ProposalRecord(
            proposal_id=proposal_id, change_set=cs, created_by=session.actor_id,
            created_at=now, base_scene_revision=scene.scene_revision,
            expires_at=(now + ttl_seconds) if ttl_seconds is not None else None,
        )
        self.state.proposals[proposal_id] = rec
        response = {
            "status": "proposed", "proposal_id": proposal_id,
            "change_set_id": change_set_id, "base_scene_revision": scene.scene_revision,
            "expires_at": rec.expires_at,
        }
        self._idem_store("propose_change", idempotency_key, request, response)
        self._save()
        return response

    def propose_changeset(self, session: RuntimeSession, *, operations: list[dict[str, Any]],
                          reason: str, idempotency_key: str, ttl_seconds: int | None = None) -> dict[str, Any]:
        self._require(session, "propose")
        normalized_ops = []
        for op in operations:
            normalized_ops.append({
                "object_id": op["object_id"], "changes": dict(op["changes"]),
                "bump": sorted(set(op["bump"])),
                "required_authority": op["required_authority"],
            })
        request = {"operations": normalized_ops, "reason": reason, "ttl_seconds": ttl_seconds}
        replay = self._idem_lookup("propose_changeset", idempotency_key, request)
        if replay is not None:
            return replay
        if not operations:
            raise RuntimeContractError("EMPTY_CHANGESET", "at least one operation is required")
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise RuntimeContractError("INVALID_TTL", "ttl_seconds must be positive")
        scene = self.store.current
        top_proposal_id = self._next_id("proposal", "P")
        change_set_id = self._next_id("changeset", "CS")
        proposals = []
        seen = set()
        for idx, op in enumerate(operations, start=1):
            object_id = op["object_id"]
            if object_id in seen:
                raise RuntimeContractError("DUPLICATE_TARGET_IN_CHANGESET", object_id)
            seen.add(object_id)
            if object_id not in scene.objects:
                raise RuntimeContractError("OBJECT_NOT_FOUND", object_id)
            obj = scene.objects[object_id]
            proposals.append(ChangeProposal(
                proposal_id=f"{top_proposal_id}-{idx:02d}", target_object_id=object_id,
                before_revisions=obj.revisions, changes=dict(op["changes"]),
                bump=frozenset(op["bump"]), required_authority=RequiredAuthority(op["required_authority"]),
                reason=reason, source_world=World.CANONICAL_CURRENT,
                before_values={key: obj.values.get(key) for key in op["changes"]},
            ))
        cs = AtomicChangeSet(change_set_id, tuple(proposals))
        now = self.clock.now()
        rec = ProposalRecord(
            proposal_id=top_proposal_id, change_set=cs, created_by=session.actor_id, created_at=now,
            base_scene_revision=scene.scene_revision,
            expires_at=(now + ttl_seconds) if ttl_seconds is not None else None,
        )
        self.state.proposals[top_proposal_id] = rec
        response = {
            "status": "proposed", "proposal_id": top_proposal_id, "change_set_id": change_set_id,
            "operation_count": len(proposals), "base_scene_revision": scene.scene_revision,
            "expires_at": rec.expires_at,
        }
        self._idem_store("propose_changeset", idempotency_key, request, response)
        self._save()
        return response

    def _proposal_record(self, proposal_id: str) -> ProposalRecord:
        rec = self.state.proposals.get(proposal_id)
        if rec is None:
            raise RuntimeContractError("PROPOSAL_NOT_FOUND", proposal_id)
        if rec.status not in TERMINAL_PROPOSAL and rec.expires_at is not None and self.clock.now() >= rec.expires_at:
            rec.status = ProposalStatus.EXPIRED
            self._save()
        return rec

    def preview_change(self, session: RuntimeSession, *, proposal_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "preview")
        request = {"proposal_id": proposal_id}
        replay = self._idem_lookup("preview_change", idempotency_key, request)
        if replay is not None:
            return replay
        rec = self._proposal_record(proposal_id)
        if rec.status == ProposalStatus.EXPIRED:
            raise RuntimeContractError("PROPOSAL_EXPIRED", proposal_id)
        if rec.status in {ProposalStatus.CANCELLED, ProposalStatus.COMMITTED}:
            raise RuntimeContractError("PROPOSAL_NOT_PREVIEWABLE", rec.status.value)
        snapshot_id = rec.snapshot_id or self._next_id("snapshot", "SN")
        try:
            snap = self.store.preview(
                rec.change_set,
                ActorContext(session.actor_id, is_human=session.is_human, can_unlock=session.can_unlock),
                snapshot_id,
            )
        except CommitError as exc:
            rec.status = ProposalStatus.BLOCKED
            rec.block_code = exc.code
            self._save()
            raise RuntimeContractError(exc.code, str(exc)) from exc
        rec.snapshot_id = snapshot_id
        rec.status = ProposalStatus.PREVIEWED
        response = {
            "status": "previewed", "proposal_id": proposal_id, "snapshot_id": snap.snapshot_id,
            "base_scene_revision": snap.base_scene_revision, "world": snap.scene.world.value,
        }
        self._idem_store("preview_change", idempotency_key, request, response)
        self._save()
        return response

    def cancel_proposal(self, session: RuntimeSession, *, proposal_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "cancel")
        request = {"proposal_id": proposal_id}
        replay = self._idem_lookup("cancel_proposal", idempotency_key, request)
        if replay is not None:
            return replay
        rec = self._proposal_record(proposal_id)
        if rec.status == ProposalStatus.COMMITTED:
            raise RuntimeContractError("COMMITTED_PROPOSAL_CANNOT_CANCEL", proposal_id)
        if rec.status == ProposalStatus.EXPIRED:
            raise RuntimeContractError("PROPOSAL_EXPIRED", proposal_id)
        rec.status = ProposalStatus.CANCELLED
        response = {"status": "cancelled", "proposal_id": proposal_id}
        self._idem_store("cancel_proposal", idempotency_key, request, response)
        self._save()
        return response

    def approve_proposal(self, session: RuntimeSession, *, proposal_id: str, grant_kind: str,
                         idempotency_key: str, ttl_seconds: int | None = 300) -> dict[str, Any]:
        """Privileged human-control-plane action. This is intentionally not on AgentToolSurface."""
        capability = "unlock" if grant_kind == "unlock" else "approve"
        self._require(session, capability)
        if not session.is_human:
            raise RuntimeContractError("HUMAN_ACTOR_REQUIRED", "approval grants require a human session")
        if grant_kind == "unlock" and not session.can_unlock:
            raise RuntimeContractError("UNLOCK_CAPABILITY_REQUIRED", session.actor_id)
        if grant_kind not in {"confirm", "unlock"}:
            raise RuntimeContractError("INVALID_GRANT_KIND", grant_kind)
        request = {"proposal_id": proposal_id, "grant_kind": grant_kind, "ttl_seconds": ttl_seconds}
        replay = self._idem_lookup("approve_proposal", idempotency_key, request)
        if replay is not None:
            return replay
        rec = self._proposal_record(proposal_id)
        if rec.status in TERMINAL_PROPOSAL:
            raise RuntimeContractError("PROPOSAL_NOT_APPROVABLE", rec.status.value)
        if ttl_seconds is not None and ttl_seconds <= 0:
            raise RuntimeContractError("INVALID_TTL", "ttl_seconds must be positive")
        grant_id = self._next_id("grant", "G")
        now = self.clock.now()
        grant = ApprovalGrant(
            grant_id=grant_id, proposal_id=proposal_id, grant_kind=grant_kind,
            actor_id=session.actor_id, scene_revision=self.store.current.scene_revision,
            change_set_hash=canonical_hash(changeset_to_dict(rec.change_set)),
            issued_at=now, expires_at=(now + ttl_seconds) if ttl_seconds is not None else None,
        )
        self.state.approvals[grant_id] = grant
        rec.status = ProposalStatus.APPROVED
        response = {"status": "approved", "proposal_id": proposal_id, "grant_id": grant_id, "grant_kind": grant_kind}
        self._idem_store("approve_proposal", idempotency_key, request, response)
        self._save()
        return response

    def _valid_grant(self, rec: ProposalRecord, kind: str) -> ApprovalGrant | None:
        cs_hash = canonical_hash(changeset_to_dict(rec.change_set))
        for grant in sorted(self.state.approvals.values(), key=lambda g: g.issued_at, reverse=True):
            if grant.proposal_id != rec.proposal_id or grant.grant_kind != kind or grant.consumed:
                continue
            if grant.expires_at is not None and self.clock.now() >= grant.expires_at:
                continue
            if grant.scene_revision != self.store.current.scene_revision:
                continue
            if grant.change_set_hash != cs_hash:
                continue
            return grant
        return None

    @staticmethod
    def _required_grant_kind(cs: AtomicChangeSet) -> str | None:
        reqs = {p.required_authority for p in cs.proposals}
        if RequiredAuthority.HUMAN_UNLOCK in reqs:
            return "unlock"
        if RequiredAuthority.HUMAN_CONFIRM in reqs:
            return "confirm"
        return None

    def request_commit(self, session: RuntimeSession, *, proposal_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "request_commit")
        request = {"proposal_id": proposal_id}
        replay = self._idem_lookup("request_commit", idempotency_key, request)
        if replay is not None:
            return replay
        rec = self._proposal_record(proposal_id)
        if rec.status == ProposalStatus.EXPIRED:
            raise RuntimeContractError("PROPOSAL_EXPIRED", proposal_id)
        if rec.status == ProposalStatus.CANCELLED:
            raise RuntimeContractError("PROPOSAL_CANCELLED", proposal_id)
        if rec.status == ProposalStatus.COMMITTED:
            raise RuntimeContractError("PROPOSAL_ALREADY_COMMITTED", proposal_id)
        grant_kind = self._required_grant_kind(rec.change_set)
        grant = self._valid_grant(rec, grant_kind) if grant_kind else None
        if grant_kind and grant is None:
            raise RuntimeContractError(
                "HUMAN_APPROVAL_REQUIRED" if grant_kind == "confirm" else "HUMAN_UNLOCK_REQUIRED",
                f"no valid {grant_kind} grant for proposal {proposal_id}",
            )
        if grant is None:
            commit_actor = ActorContext("runtime-deterministic", is_human=False, can_unlock=False)
            committed_cs = rec.change_set
        else:
            commit_actor = ActorContext(grant.actor_id, is_human=True, can_unlock=grant.grant_kind == "unlock")
            committed_cs = AtomicChangeSet(
                rec.change_set.change_set_id,
                tuple(replace(
                    p,
                    confirmed=(grant.grant_kind in {"confirm", "unlock"}) or p.confirmed,
                    unlock_confirmed=(grant.grant_kind == "unlock") or p.unlock_confirmed,
                ) for p in rec.change_set.proposals),
                rec.change_set.commit_policy,
            )
        try:
            scene = self.store.commit(committed_cs, commit_actor)
        except CommitError as exc:
            rec.status = ProposalStatus.BLOCKED
            rec.block_code = exc.code
            self._save()
            raise RuntimeContractError(exc.code, str(exc)) from exc
        if grant is not None:
            grant.consumed = True
        rec.status = ProposalStatus.COMMITTED
        rec.committed_scene_revision = scene.scene_revision
        changed_keys: set[str] = set()
        for p in committed_cs.proposals:
            for axis in p.bump:
                changed_keys.add(f"{p.target_object_id}.{axis}")
        affected = self.graph.invalidate(changed_keys) if changed_keys else set()
        for aid in affected:
            if aid in self.state.artifacts:
                self.state.artifacts[aid].status = ArtifactStatus.STALE
        self.store.audit_log.append(
            event_type="runtime_commit_requested",
            actor_id=session.actor_id,
            scene_revision_before=scene.scene_revision,
            scene_revision_after=scene.scene_revision,
            change_set_id=committed_cs.change_set_id,
            payload={"proposal_id": proposal_id, "approval_actor": grant.actor_id if grant else None},
        )
        response = {
            "status": "committed", "proposal_id": proposal_id,
            "scene_revision": scene.scene_revision, "stale_artifacts": sorted(affected),
        }
        self._idem_store("request_commit", idempotency_key, request, response)
        self._save()
        return response

    def register_artifact(self, *, artifact_id: str, artifact_type: str, dependency_keys: set[str],
                          world: World = World.CANONICAL_CURRENT, content_hash: str | None = None,
                          payload_ref: str | None = None) -> None:
        record = ArtifactRecord(
            artifact_id=artifact_id, artifact_type=artifact_type, world=world,
            dependency_keys=frozenset(dependency_keys), status=ArtifactStatus.CURRENT,
            content_hash=content_hash, payload_ref=payload_ref,
            source_scene_revision=self.store.current.scene_revision,
        )
        self.state.artifacts[artifact_id] = record
        self._rebuild_dependency_graph()
        self._save()

    def rebuild_stale(self, session: RuntimeSession, *, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "rebuild")
        request = {"stale_artifacts": sorted(aid for aid, a in self.state.artifacts.items() if a.status == ArtifactStatus.STALE)}
        replay = self._idem_lookup("rebuild_stale", idempotency_key, request)
        if replay is not None:
            return replay
        stale = set(request["stale_artifacts"])
        order = RebuildScheduler(self.graph).plan(stale)
        existing_active = {j.artifact_id: j for j in self.state.jobs.values() if j.status in {JobStatus.QUEUED, JobStatus.RUNNING}}
        artifact_to_job: dict[str, str] = {a: j.job_id for a, j in existing_active.items()}
        created: list[str] = []
        for artifact_id in order:
            if artifact_id in artifact_to_job:
                continue
            preds = [dep for dep in self.state.artifacts[artifact_id].dependency_keys if dep in stale]
            predecessor_job_ids = tuple(artifact_to_job[d] for d in preds if d in artifact_to_job)
            job_id = self._next_id("job", "J")
            job = JobRecord(job_id, "rebuild_artifact", artifact_id, JobStatus.QUEUED,
                            self.clock.now(), predecessor_job_ids=predecessor_job_ids,
                            idempotency_key=f"rebuild:{artifact_id}:{self.store.current.scene_revision}")
            self.state.jobs[job_id] = job
            artifact_to_job[artifact_id] = job_id
            created.append(job_id)
        response = {"status": "queued", "job_ids": created, "rebuild_order": order}
        self._idem_store("rebuild_stale", idempotency_key, request, response)
        self._save()
        return response

    def claim_next_job(self, session: RuntimeSession, *, worker_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "claim_job")
        request = {"worker_id": worker_id}
        replay = self._idem_lookup("claim_next_job", idempotency_key, request)
        if replay is not None:
            return replay
        succeeded = {jid for jid, j in self.state.jobs.items() if j.status == JobStatus.SUCCEEDED}
        candidates = [j for j in self.state.jobs.values() if j.status == JobStatus.QUEUED and set(j.predecessor_job_ids) <= succeeded]
        candidates.sort(key=lambda j: (j.created_at, j.job_id))
        if not candidates:
            # An empty queue is transient. Caching it would make the same retry key
            # return "empty" even after a predecessor completes and work becomes claimable.
            return {"status": "empty"}
        job = candidates[0]
        job.status = JobStatus.RUNNING
        job.worker_id = worker_id
        job.attempt += 1
        if job.artifact_id in self.state.artifacts:
            self.state.artifacts[job.artifact_id].status = ArtifactStatus.BUILDING
        response = {"status": "claimed", "job_id": job.job_id, "artifact_id": job.artifact_id,
                    "attempt": job.attempt, "worker_id": worker_id}
        self._idem_store("claim_next_job", idempotency_key, request, response)
        self._save()
        return response

    def complete_job(self, session: RuntimeSession, *, job_id: str, success: bool,
                     worker_id: str, attempt: int, idempotency_key: str,
                     content_hash: str | None = None, payload_ref: str | None = None,
                     error: str | None = None) -> dict[str, Any]:
        self._require(session, "complete_job")
        request = {"job_id": job_id, "success": success, "worker_id": worker_id, "attempt": attempt,
                   "content_hash": content_hash, "payload_ref": payload_ref, "error": error}
        replay = self._idem_lookup("complete_job", idempotency_key, request)
        if replay is not None:
            return replay
        job = self.state.jobs.get(job_id)
        if job is None:
            raise RuntimeContractError("JOB_NOT_FOUND", job_id)
        if job.status != JobStatus.RUNNING:
            raise RuntimeContractError("JOB_NOT_RUNNING", job.status.value)
        if job.worker_id != worker_id or job.attempt != attempt:
            raise RuntimeContractError(
                "STALE_JOB_CLAIM",
                "job completion does not match the current worker claim generation",
                details={"current_worker": job.worker_id, "current_attempt": job.attempt},
            )
        artifact = self.state.artifacts[job.artifact_id]
        if success:
            if not content_hash:
                raise RuntimeContractError("ARTIFACT_HASH_REQUIRED", job.artifact_id)
            job.status = JobStatus.SUCCEEDED
            artifact.status = ArtifactStatus.CURRENT
            artifact.content_hash = content_hash
            artifact.payload_ref = payload_ref
            artifact.source_scene_revision = self.store.current.scene_revision
            if job.artifact_id in self.graph._artifacts:
                self.graph._artifacts[job.artifact_id].state = "current"
            response = {"status": "succeeded", "job_id": job_id, "artifact_id": job.artifact_id}
        else:
            job.status = JobStatus.FAILED
            job.last_error = error or "unknown"
            artifact.status = ArtifactStatus.FAILED
            if job.artifact_id in self.graph._artifacts:
                self.graph._artifacts[job.artifact_id].state = "stale"
            response = {"status": "failed", "job_id": job_id, "artifact_id": job.artifact_id, "error": job.last_error}
        self._idem_store("complete_job", idempotency_key, request, response)
        self._save()
        return response

    def retry_job(self, session: RuntimeSession, *, job_id: str, idempotency_key: str) -> dict[str, Any]:
        self._require(session, "retry_job")
        request = {"job_id": job_id}
        replay = self._idem_lookup("retry_job", idempotency_key, request)
        if replay is not None:
            return replay
        job = self.state.jobs.get(job_id)
        if job is None:
            raise RuntimeContractError("JOB_NOT_FOUND", job_id)
        if job.status != JobStatus.FAILED:
            raise RuntimeContractError("JOB_NOT_FAILED", job.status.value)
        job.status = JobStatus.QUEUED
        job.worker_id = None
        self.state.artifacts[job.artifact_id].status = ArtifactStatus.STALE
        response = {"status": "queued", "job_id": job_id}
        self._idem_store("retry_job", idempotency_key, request, response)
        self._save()
        return response

    def job_status(self, session: RuntimeSession) -> dict[str, Any]:
        self._require(session, "inspect_jobs")
        return {
            "status": "ok",
            "jobs": [
                {"job_id": j.job_id, "artifact_id": j.artifact_id, "state": j.status.value,
                 "attempt": j.attempt, "worker_id": j.worker_id}
                for j in sorted(self.state.jobs.values(), key=lambda x: x.job_id)
            ],
        }

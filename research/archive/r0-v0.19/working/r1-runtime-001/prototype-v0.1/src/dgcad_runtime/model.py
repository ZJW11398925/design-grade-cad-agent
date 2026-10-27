from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from dgcad_foundation.model import AtomicChangeSet, World


class ProposalStatus(str, Enum):
    PROPOSED = "proposed"
    PREVIEWED = "previewed"
    APPROVED = "approved"
    COMMITTED = "committed"
    CANCELLED = "cancelled"
    EXPIRED = "expired"
    BLOCKED = "blocked"


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class ArtifactStatus(str, Enum):
    CURRENT = "current"
    STALE = "stale"
    BUILDING = "building"
    FAILED = "failed"


@dataclass(frozen=True)
class RuntimeSession:
    session_id: str
    actor_id: str
    capabilities: frozenset[str]
    is_human: bool = False
    can_unlock: bool = False


@dataclass
class ProposalRecord:
    proposal_id: str
    change_set: AtomicChangeSet
    created_by: str
    created_at: int
    base_scene_revision: int
    expires_at: int | None = None
    status: ProposalStatus = ProposalStatus.PROPOSED
    snapshot_id: str | None = None
    committed_scene_revision: int | None = None
    block_code: str | None = None


@dataclass
class ApprovalGrant:
    grant_id: str
    proposal_id: str
    grant_kind: str
    actor_id: str
    scene_revision: int
    change_set_hash: str
    issued_at: int
    expires_at: int | None = None
    consumed: bool = False


@dataclass
class ArtifactRecord:
    artifact_id: str
    artifact_type: str
    world: World
    dependency_keys: frozenset[str]
    status: ArtifactStatus = ArtifactStatus.CURRENT
    content_hash: str | None = None
    payload_ref: str | None = None
    source_scene_revision: int | None = None


@dataclass
class JobRecord:
    job_id: str
    job_type: str
    artifact_id: str
    status: JobStatus
    created_at: int
    predecessor_job_ids: tuple[str, ...] = ()
    attempt: int = 0
    worker_id: str | None = None
    last_error: str | None = None
    idempotency_key: str | None = None


@dataclass
class IdempotencyRecord:
    key: str
    operation: str
    request_hash: str
    response: dict[str, Any]


@dataclass
class RuntimeState:
    schema_id: str
    project_id: str
    counters: dict[str, int] = field(default_factory=dict)
    proposals: dict[str, ProposalRecord] = field(default_factory=dict)
    approvals: dict[str, ApprovalGrant] = field(default_factory=dict)
    artifacts: dict[str, ArtifactRecord] = field(default_factory=dict)
    jobs: dict[str, JobRecord] = field(default_factory=dict)
    idempotency: dict[str, IdempotencyRecord] = field(default_factory=dict)

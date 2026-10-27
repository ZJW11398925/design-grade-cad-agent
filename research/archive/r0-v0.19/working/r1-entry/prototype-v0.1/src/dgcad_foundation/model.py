from __future__ import annotations
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any


class AuthorityState(str, Enum):
    EVIDENCE_ONLY = "evidence_only"
    CANDIDATE = "candidate"
    RULE_DERIVED = "rule_derived"
    HUMAN_CONFIRMED = "human_confirmed"
    LOCKED = "locked"


class LifecycleState(str, Enum):
    CURRENT = "current"
    REJECTED = "rejected"
    BLOCKED = "blocked"


class RequiredAuthority(str, Enum):
    DETERMINISTIC_AUTO = "deterministic_auto"
    HUMAN_CONFIRM = "human_confirm"
    HUMAN_UNLOCK = "human_unlock"
    BLOCKED = "blocked"


class World(str, Enum):
    CANONICAL_CURRENT = "canonical_current"
    PROPOSAL_PREVIEW = "proposal_preview"
    EXTERNAL = "external"


@dataclass(frozen=True)
class RevisionStamp:
    semantic: int = 0
    geometry: int = 0
    parameter: int = 0

    def bumped(self, *, semantic: bool = False, geometry: bool = False, parameter: bool = False) -> "RevisionStamp":
        return RevisionStamp(
            self.semantic + int(semantic),
            self.geometry + int(geometry),
            self.parameter + int(parameter),
        )


@dataclass(frozen=True)
class CanonicalObject:
    object_id: str
    object_class: str
    revisions: RevisionStamp = field(default_factory=RevisionStamp)
    authority_state: AuthorityState = AuthorityState.CANDIDATE
    lifecycle_state: LifecycleState = LifecycleState.CURRENT
    values: dict[str, Any] = field(default_factory=dict)
    locks: frozenset[str] = field(default_factory=frozenset)

    def with_changes(self, changes: dict[str, Any], bump: set[str]) -> "CanonicalObject":
        new_values = dict(self.values)
        new_values.update(changes)
        new_rev = self.revisions.bumped(
            semantic="semantic" in bump,
            geometry="geometry" in bump,
            parameter="parameter" in bump,
        )
        return replace(self, values=new_values, revisions=new_rev)


@dataclass(frozen=True)
class SceneState:
    scene_id: str
    scene_revision: int
    objects: dict[str, CanonicalObject]
    world: World = World.CANONICAL_CURRENT


@dataclass(frozen=True)
class ChangeProposal:
    proposal_id: str
    target_object_id: str
    before_revisions: RevisionStamp
    changes: dict[str, Any]
    bump: frozenset[str]
    required_authority: RequiredAuthority
    reason: str
    source_world: World = World.CANONICAL_CURRENT
    confirmed: bool = False
    unlock_confirmed: bool = False


@dataclass(frozen=True)
class AtomicChangeSet:
    change_set_id: str
    proposals: tuple[ChangeProposal, ...]
    commit_policy: str = "all_or_nothing"


@dataclass(frozen=True)
class ProposalSnapshot:
    snapshot_id: str
    base_scene_revision: int
    change_set_id: str
    scene: SceneState
    state: str = "preview_only"


@dataclass
class DerivedArtifact:
    artifact_id: str
    artifact_type: str
    world: World
    dependency_keys: frozenset[str]
    state: str = "current"


@dataclass(frozen=True)
class ValidationIssue:
    code: str
    severity: str
    object_id: str | None = None
    expected: Any = None
    actual: Any = None
    evidence_locator: str | None = None
    fixability: str | None = None


@dataclass(frozen=True)
class ValidationResult:
    validator_id: str
    validator_version: str
    scope: str
    world: World
    verdict: str
    issues: tuple[ValidationIssue, ...] = ()
    coverage_limits: tuple[str, ...] = ()

"""Research-only Foundation contracts. Not production CAD software."""
from .model import (
    AuthorityState, LifecycleState, RequiredAuthority, World, RevisionStamp,
    CanonicalObject, SceneState, ChangeProposal, AtomicChangeSet, ProposalSnapshot,
    DerivedArtifact, ValidationIssue, ValidationResult,
)
from .store import CanonicalStore, CommitError
from .dependency import DependencyGraph, DependencyCycleError
from .authority import ActorContext, authority_allows
from .serialization import canonical_json, canonical_hash
from .audit import AuditEvent, AuditLog
from .migration import MigrationError, MigrationRegistry
from .scheduler import RebuildScheduler
from .gateway import AgentGateway

__all__ = [
    "AuthorityState", "LifecycleState", "RequiredAuthority", "World",
    "RevisionStamp", "CanonicalObject", "SceneState", "ChangeProposal",
    "AtomicChangeSet", "ProposalSnapshot", "DerivedArtifact",
    "ValidationIssue", "ValidationResult", "CanonicalStore", "CommitError",
    "DependencyGraph", "DependencyCycleError", "ActorContext", "authority_allows",
    "canonical_json", "canonical_hash", "AuditEvent", "AuditLog",
    "MigrationError", "MigrationRegistry", "RebuildScheduler", "AgentGateway",
]

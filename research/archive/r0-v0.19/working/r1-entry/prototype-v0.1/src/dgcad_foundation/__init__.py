"""Research-only Foundation contracts. Not production CAD software."""
from .model import (
    AuthorityState,
    LifecycleState,
    RequiredAuthority,
    World,
    RevisionStamp,
    CanonicalObject,
    SceneState,
    ChangeProposal,
    AtomicChangeSet,
    ProposalSnapshot,
    DerivedArtifact,
    ValidationIssue,
    ValidationResult,
)
from .store import CanonicalStore, CommitError
from .dependency import DependencyGraph
from .authority import ActorContext, authority_allows

__all__ = [
    "AuthorityState", "LifecycleState", "RequiredAuthority", "World",
    "RevisionStamp", "CanonicalObject", "SceneState", "ChangeProposal",
    "AtomicChangeSet", "ProposalSnapshot", "DerivedArtifact",
    "ValidationIssue", "ValidationResult", "CanonicalStore", "CommitError",
    "DependencyGraph", "ActorContext", "authority_allows",
]

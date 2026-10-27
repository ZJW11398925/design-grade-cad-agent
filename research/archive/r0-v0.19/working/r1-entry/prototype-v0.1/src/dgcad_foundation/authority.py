from dataclasses import dataclass
from .model import AuthorityState, CanonicalObject, ChangeProposal, RequiredAuthority, World


@dataclass(frozen=True)
class ActorContext:
    actor_id: str
    is_human: bool = False
    can_unlock: bool = False


def _touches_locked_scope(obj: CanonicalObject, proposal: ChangeProposal) -> bool:
    if obj.authority_state == AuthorityState.LOCKED:
        return True
    if "all" in obj.locks:
        return True
    return bool(set(proposal.bump) & set(obj.locks))


def authority_allows(
    obj: CanonicalObject,
    proposal: ChangeProposal,
    actor: ActorContext,
    *,
    for_preview: bool = False,
) -> tuple[bool, str]:
    if proposal.source_world == World.EXTERNAL:
        return False, "EXTERNAL_DIRECT_WRITE_FORBIDDEN"
    if proposal.required_authority == RequiredAuthority.BLOCKED:
        return False, "PROPOSAL_BLOCKED"

    if _touches_locked_scope(obj, proposal):
        unlocked = (
            proposal.required_authority == RequiredAuthority.HUMAN_UNLOCK
            and actor.is_human
            and actor.can_unlock
            and proposal.unlock_confirmed
        )
        if not unlocked:
            return False, "LOCK_REQUIRES_EXPLICIT_HUMAN_UNLOCK"

    # A design-intent proposal is allowed to exist and be previewed before confirmation.
    # Confirmation is required only at canonical commit.
    if proposal.required_authority == RequiredAuthority.HUMAN_CONFIRM and not for_preview:
        if not (actor.is_human and proposal.confirmed):
            return False, "HUMAN_CONFIRMATION_REQUIRED"

    if proposal.required_authority == RequiredAuthority.HUMAN_UNLOCK:
        if not (actor.is_human and actor.can_unlock and proposal.unlock_confirmed):
            return False, "HUMAN_UNLOCK_REQUIRED"

    return True, "OK"

from __future__ import annotations
from .model import RuntimeSession
from .runtime import StatefulRuntime


class HumanControlPlane:
    """Privileged control surface kept separate from the agent tool surface."""

    def __init__(self, runtime: StatefulRuntime, session: RuntimeSession):
        self.runtime = runtime
        self.session = session

    def approve(self, proposal_id: str, *, idempotency_key: str, ttl_seconds: int | None = 300):
        return self.runtime.approve_proposal(
            self.session, proposal_id=proposal_id, grant_kind="confirm",
            idempotency_key=idempotency_key, ttl_seconds=ttl_seconds,
        )

    def unlock(self, proposal_id: str, *, idempotency_key: str, ttl_seconds: int | None = 300):
        return self.runtime.approve_proposal(
            self.session, proposal_id=proposal_id, grant_kind="unlock",
            idempotency_key=idempotency_key, ttl_seconds=ttl_seconds,
        )

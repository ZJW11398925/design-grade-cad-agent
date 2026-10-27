from __future__ import annotations
from typing import Any

from .errors import RuntimeContractError
from .model import RuntimeSession
from .runtime import StatefulRuntime


class AgentToolSurface:
    """Protocol-neutral agent surface. No approve/unlock method exists here."""

    def __init__(self, runtime: StatefulRuntime, session: RuntimeSession):
        self.runtime = runtime
        self.session = session

    def invoke(self, tool: str, args: dict[str, Any] | None = None, *, idempotency_key: str | None = None) -> dict[str, Any]:
        args = dict(args or {})
        try:
            if tool == "scene_summary":
                return self.runtime.scene_summary(self.session)
            if tool == "propose_change":
                return self.runtime.propose_change(self.session, idempotency_key=idempotency_key, **args)
            if tool == "propose_changeset":
                return self.runtime.propose_changeset(self.session, idempotency_key=idempotency_key, **args)
            if tool == "preview_change":
                return self.runtime.preview_change(self.session, idempotency_key=idempotency_key, **args)
            if tool == "request_commit":
                return self.runtime.request_commit(self.session, idempotency_key=idempotency_key, **args)
            if tool == "cancel_proposal":
                return self.runtime.cancel_proposal(self.session, idempotency_key=idempotency_key, **args)
            if tool == "rebuild_stale":
                return self.runtime.rebuild_stale(self.session, idempotency_key=idempotency_key)
            if tool == "job_status":
                return self.runtime.job_status(self.session)
            raise RuntimeContractError("UNKNOWN_TOOL", tool)
        except RuntimeContractError as exc:
            return exc.as_result()


class CliAdapter:
    def __init__(self, surface: AgentToolSurface):
        self.surface = surface

    def invoke(self, tool: str, args: dict[str, Any] | None = None, *, idempotency_key: str | None = None) -> dict[str, Any]:
        return self.surface.invoke(tool, args, idempotency_key=idempotency_key)


class McpAdapter:
    """Research MCP binding shim. It proves parity, not wire-level MCP conformance."""

    def __init__(self, surface: AgentToolSurface):
        self.surface = surface

    def invoke(self, tool: str, args: dict[str, Any] | None = None, *, idempotency_key: str | None = None) -> dict[str, Any]:
        return self.surface.invoke(tool, args, idempotency_key=idempotency_key)

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from dgcad_runtime.surface import AgentToolSurface


@dataclass
class DeploymentService:
    """One semantic entry point used by CLI and future MCP adapters."""
    surface: AgentToolSurface

    def invoke(self, tool: str, args: dict[str, Any] | None = None, *, idempotency_key: str | None = None) -> dict[str, Any]:
        return self.surface.invoke(tool, args or {}, idempotency_key=idempotency_key)

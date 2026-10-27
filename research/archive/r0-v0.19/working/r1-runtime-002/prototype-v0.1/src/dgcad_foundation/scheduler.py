from __future__ import annotations
from .dependency import DependencyGraph


class RebuildScheduler:
    """Produces a dependency-safe rebuild order for stale artifacts.

    This is a research scheduler only. It does not execute geometry or analysis jobs.
    """

    def __init__(self, graph: DependencyGraph):
        self.graph = graph

    def plan(self, artifact_ids: set[str] | None = None) -> list[str]:
        stale = set(artifact_ids or self.graph.stale_artifacts())
        return [aid for aid in self.graph.topological_artifacts() if aid in stale]

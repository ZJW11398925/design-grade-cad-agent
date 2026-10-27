from __future__ import annotations
from collections import defaultdict, deque
from .model import DerivedArtifact


class DependencyCycleError(RuntimeError):
    pass


class DependencyGraph:
    def __init__(self) -> None:
        self._artifacts: dict[str, DerivedArtifact] = {}
        self._by_key: dict[str, set[str]] = defaultdict(set)

    def register(self, artifact: DerivedArtifact) -> None:
        old = self._artifacts.get(artifact.artifact_id)
        if old is not None:
            for key in old.dependency_keys:
                self._by_key[key].discard(artifact.artifact_id)
        self._artifacts[artifact.artifact_id] = artifact
        for key in artifact.dependency_keys:
            self._by_key[key].add(artifact.artifact_id)
        self._assert_acyclic()

    def _artifact_dependencies(self, artifact_id: str) -> set[str]:
        return {key for key in self._artifacts[artifact_id].dependency_keys if key in self._artifacts}

    def _assert_acyclic(self) -> None:
        temporary: set[str] = set()
        permanent: set[str] = set()

        def visit(node: str) -> None:
            if node in permanent:
                return
            if node in temporary:
                raise DependencyCycleError(f"cycle detected at {node}")
            temporary.add(node)
            for dep in self._artifact_dependencies(node):
                visit(dep)
            temporary.remove(node)
            permanent.add(node)

        for node in self._artifacts:
            visit(node)

    def invalidate(self, changed_keys: set[str]) -> set[str]:
        """Mark direct and transitive downstream artifacts stale.

        Artifact IDs are valid dependency keys, so MASS-B001 can feed SHADOW-001.
        """
        affected: set[str] = set()
        queue = deque(changed_keys)
        seen_keys = set(changed_keys)
        while queue:
            key = queue.popleft()
            for artifact_id in self._by_key.get(key, set()):
                if artifact_id in affected:
                    continue
                affected.add(artifact_id)
                self._artifacts[artifact_id].state = "stale"
                if artifact_id not in seen_keys:
                    seen_keys.add(artifact_id)
                    queue.append(artifact_id)
        return affected

    def state(self, artifact_id: str) -> str:
        return self._artifacts[artifact_id].state

    def stale_artifacts(self) -> set[str]:
        return {aid for aid, artifact in self._artifacts.items() if artifact.state == "stale"}

    def topological_artifacts(self) -> list[str]:
        """Dependencies appear before the artifacts that depend on them."""
        indegree = {aid: 0 for aid in self._artifacts}
        downstream: dict[str, set[str]] = defaultdict(set)
        for aid in self._artifacts:
            for dep in self._artifact_dependencies(aid):
                indegree[aid] += 1
                downstream[dep].add(aid)
        queue = deque(sorted(aid for aid, deg in indegree.items() if deg == 0))
        order: list[str] = []
        while queue:
            node = queue.popleft()
            order.append(node)
            for nxt in sorted(downstream.get(node, set())):
                indegree[nxt] -= 1
                if indegree[nxt] == 0:
                    queue.append(nxt)
        if len(order) != len(self._artifacts):
            raise DependencyCycleError("cycle detected during topological sort")
        return order

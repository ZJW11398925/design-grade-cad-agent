from collections import defaultdict, deque
from .model import DerivedArtifact


class DependencyGraph:
    def __init__(self) -> None:
        self._artifacts: dict[str, DerivedArtifact] = {}
        self._by_key: dict[str, set[str]] = defaultdict(set)

    def register(self, artifact: DerivedArtifact) -> None:
        self._artifacts[artifact.artifact_id] = artifact
        for key in artifact.dependency_keys:
            self._by_key[key].add(artifact.artifact_id)

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

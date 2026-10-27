from __future__ import annotations
from collections.abc import Callable
from copy import deepcopy
from typing import Any


class MigrationError(RuntimeError):
    pass


class MigrationRegistry:
    def __init__(self) -> None:
        self._steps: dict[tuple[str, str], Callable[[dict[str, Any]], dict[str, Any]]] = {}

    def register(self, from_schema: str, to_schema: str, fn: Callable[[dict[str, Any]], dict[str, Any]]) -> None:
        self._steps[(from_schema, to_schema)] = fn

    def migrate(self, document: dict[str, Any], target_schema: str) -> dict[str, Any]:
        doc = deepcopy(document)
        current = doc.get("schema_id")
        if current == target_schema:
            return doc
        visited: set[str] = set()
        while current != target_schema:
            if current in visited:
                raise MigrationError("migration cycle detected")
            visited.add(current)
            candidates = [(to, fn) for (frm, to), fn in self._steps.items() if frm == current]
            if len(candidates) != 1:
                raise MigrationError(f"no unique migration path from {current} to {target_schema}")
            nxt, fn = candidates[0]
            doc = fn(doc)
            doc["schema_id"] = nxt
            current = nxt
        return doc

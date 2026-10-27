from __future__ import annotations
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class AuditEvent:
    sequence: int
    event_type: str
    actor_id: str
    scene_revision_before: int
    scene_revision_after: int
    change_set_id: str | None = None
    payload: dict[str, Any] | None = None


class AuditLog:
    def __init__(self, events: list[AuditEvent] | None = None) -> None:
        self._events: list[AuditEvent] = list(events or [])
        for idx, event in enumerate(self._events, start=1):
            if event.sequence != idx:
                raise ValueError("audit sequence must be contiguous and start at 1")

    def append(self, *, event_type: str, actor_id: str, scene_revision_before: int,
               scene_revision_after: int, change_set_id: str | None = None,
               payload: dict[str, Any] | None = None) -> AuditEvent:
        event = AuditEvent(
            sequence=len(self._events) + 1,
            event_type=event_type,
            actor_id=actor_id,
            scene_revision_before=scene_revision_before,
            scene_revision_after=scene_revision_after,
            change_set_id=change_set_id,
            payload=payload,
        )
        self._events.append(event)
        return event

    @property
    def events(self) -> tuple[AuditEvent, ...]:
        return tuple(self._events)

    def write_jsonl(self, path: str | Path) -> None:
        p = Path(path)
        with p.open("w", encoding="utf-8", newline="\n") as f:
            for event in self._events:
                f.write(json.dumps(asdict(event), ensure_ascii=False, sort_keys=True, separators=(",", ":")) + "\n")

    @classmethod
    def read_jsonl(cls, path: str | Path) -> "AuditLog":
        events: list[AuditEvent] = []
        with Path(path).open("r", encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    events.append(AuditEvent(**json.loads(line)))
        return cls(events)

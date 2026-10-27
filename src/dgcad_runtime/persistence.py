from __future__ import annotations
import json
import os
from pathlib import Path

from dgcad_foundation.serialization import canonical_hash, canonical_json
from .codec import payload_to_state, state_to_payload
from .errors import RuntimeContractError


class AtomicProjectFile:
    """Single-file research persistence boundary.

    One atomic envelope keeps canonical scene + registries + audit consistent for the
    research prototype. It is not a production database or distributed transaction layer.
    """

    FILE_NAME = "runtime-state.json"

    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.path = self.root / self.FILE_NAME

    def exists(self) -> bool:
        return self.path.exists()

    def save(self, state, scene, audit_events, *, expected_hash: str | None = None) -> str:
        if self.path.exists() and expected_hash is not None:
            try:
                current = json.loads(self.path.read_text(encoding="utf-8"))
                current_hash = current.get("payload_hash")
                actual_current_hash = canonical_hash(current.get("payload"))
            except Exception as exc:
                raise RuntimeContractError("PROJECT_STATE_UNREADABLE", str(exc)) from exc
            if current_hash != actual_current_hash:
                raise RuntimeContractError("PROJECT_STATE_HASH_MISMATCH", "disk payload changed without a matching envelope hash")
            if current_hash != expected_hash:
                raise RuntimeContractError(
                    "PROJECT_STATE_CONCURRENT_MODIFICATION",
                    "project state changed since this runtime instance loaded it",
                )
        payload = state_to_payload(state, scene, audit_events)
        payload_hash = canonical_hash(payload)
        envelope = {
            "envelope_schema": "dgcad.runtime.envelope.v0.1",
            "payload_hash": payload_hash,
            "payload": payload,
        }
        tmp = self.path.with_suffix(".json.tmp")
        data = canonical_json(envelope) + "\n"
        with tmp.open("w", encoding="utf-8", newline="\n") as f:
            f.write(data)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp, self.path)
        return payload_hash

    def load(self):
        try:
            envelope = json.loads(self.path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise RuntimeContractError("PROJECT_STATE_UNREADABLE", str(exc)) from exc
        if envelope.get("envelope_schema") != "dgcad.runtime.envelope.v0.1":
            raise RuntimeContractError("PROJECT_STATE_SCHEMA_UNSUPPORTED", str(envelope.get("envelope_schema")))
        payload = envelope.get("payload")
        expected = envelope.get("payload_hash")
        actual = canonical_hash(payload)
        if expected != actual:
            raise RuntimeContractError("PROJECT_STATE_HASH_MISMATCH", "runtime-state payload hash mismatch")
        state, scene, audit = payload_to_state(payload)
        return state, scene, audit, actual

from __future__ import annotations

import hashlib
import os
from pathlib import Path


class ContentAddressedArtifactStore:
    def __init__(self, root: str | Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def put_bytes(self, data: bytes) -> tuple[str, Path]:
        digest = hashlib.sha256(data).hexdigest()
        target = self.root / digest[:2] / digest[2:]
        target.parent.mkdir(parents=True, exist_ok=True)
        if not target.exists():
            tmp = target.with_suffix(".tmp")
            tmp.write_bytes(data)
            os.replace(tmp, target)
        elif target.read_bytes() != data:
            raise RuntimeError("ARTIFACT_HASH_COLLISION_OR_CORRUPTION")
        return digest, target

    def read_bytes(self, digest: str) -> bytes:
        target = self.root / digest[:2] / digest[2:]
        data = target.read_bytes()
        if hashlib.sha256(data).hexdigest() != digest:
            raise RuntimeError("ARTIFACT_CONTENT_HASH_MISMATCH")
        return data

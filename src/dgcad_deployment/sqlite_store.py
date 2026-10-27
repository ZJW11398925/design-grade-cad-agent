from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Any


def _canonical_bytes(value: Any) -> bytes:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode("utf-8")


def _hash(value: Any) -> str:
    return hashlib.sha256(_canonical_bytes(value)).hexdigest()


class ProjectStoreError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class Snapshot:
    project_id: str
    state_revision: int
    payload_hash: str
    payload: dict[str, Any]


class SqliteProjectStore:
    """Deployment-boundary spike: single-project SQLite store with CAS semantics.

    It is intentionally small. It proves transaction and restart semantics, not a final schema.
    """

    SCHEMA_VERSION = 1

    def __init__(self, db_path: str | Path):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA foreign_keys=ON")
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA synchronous=FULL")
        self._migrate()

    def close(self) -> None:
        self.conn.close()

    def _migrate(self) -> None:
        self.conn.execute("CREATE TABLE IF NOT EXISTS schema_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL)")
        row = self.conn.execute("SELECT value FROM schema_meta WHERE key='schema_version'").fetchone()
        if row is None:
            self.conn.execute("INSERT INTO schema_meta(key,value) VALUES('schema_version',?)", (str(self.SCHEMA_VERSION),))
        elif int(row["value"]) != self.SCHEMA_VERSION:
            raise ProjectStoreError("SQLITE_SCHEMA_VERSION_UNSUPPORTED", f"found schema version {row['value']}")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS project_state (
                project_id TEXT PRIMARY KEY,
                state_revision INTEGER NOT NULL,
                payload_json TEXT NOT NULL,
                payload_hash TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
        """)
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS artifact_meta (
                project_id TEXT NOT NULL,
                artifact_id TEXT NOT NULL,
                content_hash TEXT NOT NULL,
                relative_path TEXT NOT NULL,
                media_type TEXT,
                byte_size INTEGER NOT NULL,
                source_scene_revision INTEGER,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY(project_id, artifact_id)
            )
        """)

    def journal_mode(self) -> str:
        return str(self.conn.execute("PRAGMA journal_mode").fetchone()[0]).lower()

    def create_project(self, project_id: str, payload: dict[str, Any]) -> Snapshot:
        encoded = _canonical_bytes(payload).decode("utf-8")
        digest = _hash(payload)
        try:
            self.conn.execute(
                "INSERT INTO project_state(project_id,state_revision,payload_json,payload_hash) VALUES(?,?,?,?)",
                (project_id, 1, encoded, digest),
            )
        except sqlite3.IntegrityError as exc:
            raise ProjectStoreError("PROJECT_ALREADY_EXISTS", project_id) from exc
        return Snapshot(project_id, 1, digest, json.loads(encoded))

    def load(self, project_id: str) -> Snapshot:
        row = self.conn.execute(
            "SELECT project_id,state_revision,payload_json,payload_hash FROM project_state WHERE project_id=?",
            (project_id,),
        ).fetchone()
        if row is None:
            raise ProjectStoreError("PROJECT_NOT_FOUND", project_id)
        payload = json.loads(row["payload_json"])
        actual = _hash(payload)
        if actual != row["payload_hash"]:
            raise ProjectStoreError("PROJECT_STATE_HASH_MISMATCH", project_id)
        return Snapshot(row["project_id"], int(row["state_revision"]), row["payload_hash"], payload)

    def compare_and_swap(self, project_id: str, *, expected_revision: int, expected_hash: str,
                         payload: dict[str, Any]) -> Snapshot:
        encoded = _canonical_bytes(payload).decode("utf-8")
        digest = _hash(payload)
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute(
                "SELECT state_revision,payload_json,payload_hash FROM project_state WHERE project_id=?",
                (project_id,),
            ).fetchone()
            if row is None:
                raise ProjectStoreError("PROJECT_NOT_FOUND", project_id)
            actual_payload = json.loads(row["payload_json"])
            actual_hash = _hash(actual_payload)
            if actual_hash != row["payload_hash"]:
                raise ProjectStoreError("PROJECT_STATE_HASH_MISMATCH", project_id)
            if int(row["state_revision"]) != expected_revision or row["payload_hash"] != expected_hash:
                raise ProjectStoreError("PROJECT_STATE_CONCURRENT_MODIFICATION", project_id)
            new_revision = expected_revision + 1
            self.conn.execute(
                "UPDATE project_state SET state_revision=?,payload_json=?,payload_hash=?,updated_at=CURRENT_TIMESTAMP WHERE project_id=?",
                (new_revision, encoded, digest, project_id),
            )
            self.conn.execute("COMMIT")
            return Snapshot(project_id, new_revision, digest, json.loads(encoded))
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def register_artifact(self, project_id: str, *, artifact_id: str, content_hash: str,
                          relative_path: str, media_type: str | None, byte_size: int,
                          source_scene_revision: int | None) -> None:
        self.conn.execute(
            """INSERT INTO artifact_meta(project_id,artifact_id,content_hash,relative_path,media_type,byte_size,source_scene_revision)
               VALUES(?,?,?,?,?,?,?)
               ON CONFLICT(project_id,artifact_id) DO UPDATE SET
                 content_hash=excluded.content_hash,
                 relative_path=excluded.relative_path,
                 media_type=excluded.media_type,
                 byte_size=excluded.byte_size,
                 source_scene_revision=excluded.source_scene_revision,
                 created_at=CURRENT_TIMESTAMP""",
            (project_id, artifact_id, content_hash, relative_path, media_type, byte_size, source_scene_revision),
        )

    def artifact_record(self, project_id: str, artifact_id: str) -> dict[str, Any]:
        row = self.conn.execute(
            "SELECT * FROM artifact_meta WHERE project_id=? AND artifact_id=?", (project_id, artifact_id)
        ).fetchone()
        if row is None:
            raise ProjectStoreError("ARTIFACT_NOT_FOUND", artifact_id)
        return dict(row)

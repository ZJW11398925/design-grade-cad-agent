from __future__ import annotations

import hashlib
import json
import os
import secrets
import sqlite3
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


class LifecycleError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class InstanceDescriptor:
    schema_id: str
    instance_id: str
    pid: int
    host: str
    port: int
    protocol: str
    started_at: int
    generation: int

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"


class EndpointRegistry:
    """Local discovery record. It contains no bearer/session token."""

    SCHEMA_ID = "dgcad.sidecar.discovery.v0.1"
    LOOPBACK_HOSTS = {"127.0.0.1", "localhost", "::1"}

    def __init__(self, path: str | Path):
        self.path = Path(path)

    def write(self, *, instance_id: str, host: str, port: int, generation: int = 1,
              pid: int | None = None, protocol: str = "http") -> InstanceDescriptor:
        if host not in self.LOOPBACK_HOSTS:
            raise LifecycleError("NON_LOOPBACK_BIND_REJECTED", host)
        if not (1 <= int(port) <= 65535):
            raise LifecycleError("INVALID_PORT", str(port))
        desc = InstanceDescriptor(
            self.SCHEMA_ID, instance_id, int(pid or os.getpid()), host, int(port), protocol,
            int(time.time()), int(generation),
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(self.path.suffix + ".tmp")
        tmp.write_text(json.dumps(asdict(desc), sort_keys=True, separators=(",", ":")), encoding="utf-8")
        try:
            os.chmod(tmp, 0o600)
        except OSError:
            pass
        os.replace(tmp, self.path)
        try:
            os.chmod(self.path, 0o600)
        except OSError:
            pass
        return desc

    def read(self) -> InstanceDescriptor:
        data = json.loads(self.path.read_text(encoding="utf-8"))
        if data.get("schema_id") != self.SCHEMA_ID:
            raise LifecycleError("DISCOVERY_SCHEMA_UNSUPPORTED", str(data.get("schema_id")))
        if data.get("host") not in self.LOOPBACK_HOSTS:
            raise LifecycleError("DISCOVERY_NON_LOOPBACK_REJECTED", str(data.get("host")))
        return InstanceDescriptor(**data)

    def clear_if_owned(self, instance_id: str) -> bool:
        if not self.path.exists():
            return False
        try:
            current = self.read()
        except Exception:
            return False
        if current.instance_id != instance_id:
            return False
        self.path.unlink(missing_ok=True)
        return True


@dataclass(frozen=True)
class SessionPrincipal:
    session_id: str
    actor_id: str
    role: str
    capabilities: frozenset[str]
    issued_at: int
    expires_at: int


class CapabilityAuthority:
    """Issues role-scoped local bearer tokens. Raw tokens are never persisted here."""

    ROLE_CAPABILITIES = {
        "agent": frozenset({"read", "propose", "preview", "request_commit", "cancel", "rebuild", "inspect_jobs"}),
        "human_review": frozenset({"read", "approve", "unlock", "review", "conflict_resolve"}),
        "cad_bridge": frozenset({"bridge_read", "bridge_write_external", "bridge_select", "bridge_view_sync"}),
        "cli_admin": frozenset({"read", "propose", "preview", "request_commit", "cancel", "rebuild", "inspect_jobs"}),
    }

    def __init__(self, now_fn=None):
        self._now = now_fn or (lambda: int(time.time()))
        self._sessions: dict[str, tuple[str, SessionPrincipal]] = {}

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def issue(self, *, role: str, actor_id: str, ttl_seconds: int = 900) -> tuple[str, SessionPrincipal]:
        if role not in self.ROLE_CAPABILITIES:
            raise LifecycleError("UNKNOWN_SESSION_ROLE", role)
        if ttl_seconds <= 0:
            raise LifecycleError("INVALID_SESSION_TTL", str(ttl_seconds))
        now = int(self._now())
        token = secrets.token_urlsafe(32)
        principal = SessionPrincipal(
            session_id=f"SES-{secrets.token_hex(8)}", actor_id=actor_id, role=role,
            capabilities=self.ROLE_CAPABILITIES[role], issued_at=now, expires_at=now + ttl_seconds,
        )
        self._sessions[self._digest(token)] = (token[:0], principal)  # store no raw token
        return token, principal

    def authenticate(self, token: str, *, required: Iterable[str] = ()) -> SessionPrincipal:
        rec = self._sessions.get(self._digest(token))
        if rec is None:
            raise LifecycleError("SESSION_TOKEN_INVALID", "unknown bearer token")
        principal = rec[1]
        if int(self._now()) >= principal.expires_at:
            raise LifecycleError("SESSION_TOKEN_EXPIRED", principal.session_id)
        missing = set(required) - set(principal.capabilities)
        if missing:
            raise LifecycleError("SESSION_CAPABILITY_DENIED", ",".join(sorted(missing)))
        return principal

    def revoke(self, token: str) -> None:
        self._sessions.pop(self._digest(token), None)


@dataclass(frozen=True)
class PairingGrant:
    pairing_id: str
    role: str
    actor_id: str
    issued_at: int
    expires_at: int
    consumed: bool = False


class PairingBroker:
    """Trusted launcher/control-plane mints role-bound one-time pairing grants.

    The exchange call accepts no requested role; therefore a component cannot
    turn an agent pairing grant into a human-review session.
    """

    def __init__(self, authority: CapabilityAuthority, now_fn=None):
        self.authority = authority
        self._now = now_fn or (lambda: int(time.time()))
        self._grants: dict[str, tuple[PairingGrant, str]] = {}

    @staticmethod
    def _digest(token: str) -> str:
        return hashlib.sha256(token.encode("utf-8")).hexdigest()

    def mint(self, *, role: str, actor_id: str, ttl_seconds: int = 60) -> tuple[str, PairingGrant]:
        if role not in self.authority.ROLE_CAPABILITIES:
            raise LifecycleError("UNKNOWN_SESSION_ROLE", role)
        if ttl_seconds <= 0:
            raise LifecycleError("INVALID_PAIRING_TTL", str(ttl_seconds))
        now = int(self._now())
        raw = secrets.token_urlsafe(24)
        grant = PairingGrant(
            pairing_id=f"PAIR-{secrets.token_hex(6)}", role=role, actor_id=actor_id,
            issued_at=now, expires_at=now + ttl_seconds, consumed=False,
        )
        self._grants[self._digest(raw)] = (grant, raw[:0])
        return raw, grant

    def exchange(self, pairing_token: str, *, session_ttl_seconds: int = 900) -> tuple[str, SessionPrincipal]:
        key = self._digest(pairing_token)
        rec = self._grants.get(key)
        if rec is None:
            raise LifecycleError("PAIRING_TOKEN_INVALID", "unknown pairing grant")
        grant = rec[0]
        now = int(self._now())
        if now >= grant.expires_at:
            del self._grants[key]
            raise LifecycleError("PAIRING_TOKEN_EXPIRED", grant.pairing_id)
        del self._grants[key]
        return self.authority.issue(role=grant.role, actor_id=grant.actor_id, ttl_seconds=session_ttl_seconds)


class ProjectLeaseStore:
    """SQLite-backed single-active-runtime lease for one project."""

    def __init__(self, db_path: str | Path, now_fn=None):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(self.db_path, timeout=5.0, isolation_level=None)
        self.conn.row_factory = sqlite3.Row
        self._now = now_fn or (lambda: int(time.time()))
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS runtime_lease (
              project_id TEXT PRIMARY KEY,
              instance_id TEXT NOT NULL,
              generation INTEGER NOT NULL,
              lease_expires_at INTEGER NOT NULL,
              updated_at INTEGER NOT NULL
            )
        """)

    def close(self):
        self.conn.close()

    def acquire(self, project_id: str, instance_id: str, *, ttl_seconds: int = 15) -> dict:
        if ttl_seconds <= 0:
            raise LifecycleError("INVALID_LEASE_TTL", str(ttl_seconds))
        now = int(self._now())
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT * FROM runtime_lease WHERE project_id=?", (project_id,)).fetchone()
            if row is None:
                generation = 1
                self.conn.execute(
                    "INSERT INTO runtime_lease(project_id,instance_id,generation,lease_expires_at,updated_at) VALUES(?,?,?,?,?)",
                    (project_id, instance_id, generation, now + ttl_seconds, now),
                )
            elif row["instance_id"] == instance_id:
                generation = int(row["generation"])
                self.conn.execute(
                    "UPDATE runtime_lease SET lease_expires_at=?,updated_at=? WHERE project_id=?",
                    (now + ttl_seconds, now, project_id),
                )
            elif int(row["lease_expires_at"]) <= now:
                generation = int(row["generation"]) + 1
                self.conn.execute(
                    "UPDATE runtime_lease SET instance_id=?,generation=?,lease_expires_at=?,updated_at=? WHERE project_id=?",
                    (instance_id, generation, now + ttl_seconds, now, project_id),
                )
            else:
                raise LifecycleError("PROJECT_RUNTIME_LEASE_HELD", f"project {project_id} is owned by {row['instance_id']}")
            self.conn.execute("COMMIT")
            return {"project_id": project_id, "instance_id": instance_id, "generation": generation, "lease_expires_at": now + ttl_seconds}
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def heartbeat(self, project_id: str, instance_id: str, *, generation: int, ttl_seconds: int = 15) -> dict:
        now = int(self._now())
        self.conn.execute("BEGIN IMMEDIATE")
        try:
            row = self.conn.execute("SELECT * FROM runtime_lease WHERE project_id=?", (project_id,)).fetchone()
            if row is None or row["instance_id"] != instance_id or int(row["generation"]) != int(generation):
                raise LifecycleError("PROJECT_RUNTIME_LEASE_LOST", project_id)
            if int(row["lease_expires_at"]) <= now:
                raise LifecycleError("PROJECT_RUNTIME_LEASE_EXPIRED", project_id)
            self.conn.execute(
                "UPDATE runtime_lease SET lease_expires_at=?,updated_at=? WHERE project_id=?",
                (now + ttl_seconds, now, project_id),
            )
            self.conn.execute("COMMIT")
            return {"project_id": project_id, "instance_id": instance_id, "generation": generation, "lease_expires_at": now + ttl_seconds}
        except Exception:
            self.conn.execute("ROLLBACK")
            raise

    def release(self, project_id: str, instance_id: str, *, generation: int) -> bool:
        cur = self.conn.execute(
            "DELETE FROM runtime_lease WHERE project_id=? AND instance_id=? AND generation=?",
            (project_id, instance_id, generation),
        )
        return cur.rowcount == 1


@dataclass
class BridgeSession:
    bridge_id: str
    bridge_type: str
    actor_id: str
    host_pid: int
    document_key: str | None
    registered_at: int
    last_seen_at: int
    expires_at: int


class BridgeRegistry:
    def __init__(self, now_fn=None):
        self._now = now_fn or (lambda: int(time.time()))
        self._bridges: dict[str, BridgeSession] = {}

    def register(self, principal: SessionPrincipal, *, bridge_type: str, host_pid: int,
                 document_key: str | None = None, ttl_seconds: int = 15) -> BridgeSession:
        if "bridge_read" not in principal.capabilities:
            raise LifecycleError("BRIDGE_CAPABILITY_REQUIRED", principal.session_id)
        if bridge_type not in {"autocad", "freecad", "bonsai", "generic"}:
            raise LifecycleError("UNSUPPORTED_BRIDGE_TYPE", bridge_type)
        now = int(self._now())
        bridge = BridgeSession(
            bridge_id=f"BR-{secrets.token_hex(6)}", bridge_type=bridge_type,
            actor_id=principal.actor_id, host_pid=int(host_pid), document_key=document_key,
            registered_at=now, last_seen_at=now, expires_at=now + ttl_seconds,
        )
        self._bridges[bridge.bridge_id] = bridge
        return bridge

    def heartbeat(self, bridge_id: str, principal: SessionPrincipal, *, ttl_seconds: int = 15) -> BridgeSession:
        bridge = self._bridges.get(bridge_id)
        if bridge is None:
            raise LifecycleError("BRIDGE_NOT_FOUND", bridge_id)
        if bridge.actor_id != principal.actor_id:
            raise LifecycleError("BRIDGE_SESSION_OWNERSHIP_MISMATCH", bridge_id)
        now = int(self._now())
        if now >= bridge.expires_at:
            raise LifecycleError("BRIDGE_SESSION_EXPIRED", bridge_id)
        bridge.last_seen_at = now
        bridge.expires_at = now + ttl_seconds
        return bridge

    def active(self) -> list[BridgeSession]:
        now = int(self._now())
        return [b for b in self._bridges.values() if now < b.expires_at]

class SidecarLifecycleHost:
    """Trusted local launcher for the research sidecar lifecycle.

    It acquires the project lease before publishing discovery. Pairing grants are
    minted explicitly for components and are never written to the discovery file.
    """

    def __init__(self, *, project_id: str, instance_id: str, lease_store: ProjectLeaseStore,
                 discovery: EndpointRegistry, authority: CapabilityAuthority,
                 pairing: PairingBroker, bridges: BridgeRegistry, runtime=None,
                 lease_ttl_seconds: int = 15):
        self.project_id = project_id
        self.instance_id = instance_id
        self.lease_store = lease_store
        self.discovery = discovery
        self.authority = authority
        self.pairing = pairing
        self.bridges = bridges
        self.runtime = runtime
        self.lease_ttl_seconds = lease_ttl_seconds
        self.server = None
        self.lease = None
        self.descriptor = None

    def start(self):
        if self.server is not None:
            raise LifecycleError("SIDECAR_ALREADY_STARTED", self.instance_id)
        lease = self.lease_store.acquire(
            self.project_id, self.instance_id, ttl_seconds=self.lease_ttl_seconds
        )
        from .local_http import LocalControlServer
        server = LocalControlServer(
            instance_id=self.instance_id, authority=self.authority, bridges=self.bridges,
            runtime=self.runtime, pairing=self.pairing,
        )
        try:
            server.start()
            desc = self.discovery.write(
                instance_id=self.instance_id, host=server.host, port=server.port,
                generation=lease["generation"],
            )
        except Exception:
            server.stop()
            self.lease_store.release(
                self.project_id, self.instance_id, generation=lease["generation"]
            )
            raise
        self.server, self.lease, self.descriptor = server, lease, desc
        return desc

    def heartbeat(self):
        if self.lease is None:
            raise LifecycleError("SIDECAR_NOT_STARTED", self.instance_id)
        self.lease = self.lease_store.heartbeat(
            self.project_id, self.instance_id, generation=self.lease["generation"],
            ttl_seconds=self.lease_ttl_seconds,
        )
        return self.lease

    def mint_pairing(self, *, role: str, actor_id: str, ttl_seconds: int = 60):
        if self.server is None:
            raise LifecycleError("SIDECAR_NOT_STARTED", self.instance_id)
        return self.pairing.mint(role=role, actor_id=actor_id, ttl_seconds=ttl_seconds)

    def stop(self):
        if self.server is not None:
            self.server.stop()
        released = False
        if self.lease is not None:
            released = self.lease_store.release(
                self.project_id, self.instance_id, generation=self.lease["generation"]
            )
        self.discovery.clear_if_owned(self.instance_id)
        self.server = None
        self.lease = None
        self.descriptor = None
        return released

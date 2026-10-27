from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from typing import Any

from dgcad_runtime import HumanControlPlane, RuntimeSession

from .lifecycle import BridgeRegistry, CapabilityAuthority, LifecycleError, PairingBroker


class _Handler(BaseHTTPRequestHandler):
    server_version = "DGCADLocalControl/0.1"

    def log_message(self, format: str, *args: Any) -> None:
        return

    def _json(self, code: int, payload: dict[str, Any]) -> None:
        raw = json.dumps(payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def _read_json(self) -> dict[str, Any]:
        n = int(self.headers.get("Content-Length", "0"))
        if n > 1024 * 1024:
            raise LifecycleError("REQUEST_TOO_LARGE", str(n))
        if n == 0:
            return {}
        return json.loads(self.rfile.read(n).decode("utf-8"))

    def _validate_host_origin(self) -> None:
        port = self.server.server_address[1]  # type: ignore[attr-defined]
        allowed_hosts = {f"127.0.0.1:{port}", f"localhost:{port}", f"[::1]:{port}"}
        host = self.headers.get("Host", "")
        if host not in allowed_hosts:
            raise LifecycleError("LOCAL_HOST_HEADER_REJECTED", host)
        origin = self.headers.get("Origin")
        if origin is not None:
            allowed_origins = {f"http://{h}" for h in allowed_hosts}
            if origin not in allowed_origins:
                raise LifecycleError("LOCAL_ORIGIN_REJECTED", origin)

    def _principal(self, required=()):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            raise LifecycleError("AUTH_REQUIRED", "bearer token required")
        return self.server.authority.authenticate(auth[7:], required=required)  # type: ignore[attr-defined]

    def do_GET(self) -> None:
        try:
            self._validate_host_origin()
            if self.path == "/health":
                return self._json(200, {"status": "ok", "instance_id": self.server.instance_id})  # type: ignore[attr-defined]
            if self.path == "/whoami":
                p = self._principal()
                return self._json(200, {
                    "status": "ok", "session_id": p.session_id, "actor_id": p.actor_id,
                    "role": p.role, "capabilities": sorted(p.capabilities),
                })
            return self._json(404, {"status": "error", "code": "NOT_FOUND"})
        except LifecycleError as exc:
            return self._json(403 if exc.code == "SESSION_CAPABILITY_DENIED" else 401, {"status": "error", "code": exc.code})

    def do_POST(self) -> None:
        try:
            self._validate_host_origin()
            body = self._read_json()
            if self.path == "/session/exchange":
                if self.server.pairing is None:  # type: ignore[attr-defined]
                    raise LifecycleError("PAIRING_DISABLED", "no pairing broker")
                token, principal = self.server.pairing.exchange(  # type: ignore[attr-defined]
                    body["pairing_token"], session_ttl_seconds=int(body.get("session_ttl_seconds", 900))
                )
                return self._json(200, {
                    "status": "paired", "bearer_token": token, "session_id": principal.session_id,
                    "actor_id": principal.actor_id, "role": principal.role,
                    "capabilities": sorted(principal.capabilities),
                })
            if self.path == "/bridge/register":
                p = self._principal(required={"bridge_read"})
                bridge = self.server.bridges.register(  # type: ignore[attr-defined]
                    p, bridge_type=body["bridge_type"], host_pid=int(body["host_pid"]),
                    document_key=body.get("document_key"), ttl_seconds=int(body.get("ttl_seconds", 15)),
                )
                return self._json(200, {"status": "registered", "bridge_id": bridge.bridge_id, "expires_at": bridge.expires_at})
            if self.path == "/bridge/heartbeat":
                p = self._principal(required={"bridge_read"})
                bridge = self.server.bridges.heartbeat(  # type: ignore[attr-defined]
                    body["bridge_id"], p, ttl_seconds=int(body.get("ttl_seconds", 15)),
                )
                return self._json(200, {"status": "ok", "bridge_id": bridge.bridge_id, "expires_at": bridge.expires_at})
            if self.path in {"/human/approve", "/human/unlock"}:
                p = self._principal(required={"approve" if self.path.endswith("approve") else "unlock"})
                if p.role != "human_review":
                    raise LifecycleError("HUMAN_CONTROL_SESSION_REQUIRED", p.role)
                runtime = self.server.runtime  # type: ignore[attr-defined]
                if runtime is None:
                    raise LifecycleError("RUNTIME_NOT_ATTACHED", "human control plane requires runtime")
                session = RuntimeSession(
                    p.session_id, p.actor_id, p.capabilities, is_human=True,
                    can_unlock=("unlock" in p.capabilities),
                )
                control = HumanControlPlane(runtime, session)
                fn = control.approve if self.path.endswith("approve") else control.unlock
                result = fn(
                    body["proposal_id"], idempotency_key=body["idempotency_key"],
                    ttl_seconds=body.get("ttl_seconds", 300),
                )
                return self._json(200, result)
            return self._json(404, {"status": "error", "code": "NOT_FOUND"})
        except KeyError as exc:
            return self._json(400, {"status": "error", "code": "MISSING_FIELD", "field": str(exc)})
        except LifecycleError as exc:
            status = 403 if exc.code in {"SESSION_CAPABILITY_DENIED", "HUMAN_CONTROL_SESSION_REQUIRED"} else 401
            return self._json(status, {"status": "error", "code": exc.code})
        except Exception as exc:
            code = getattr(exc, "code", "CONTROL_PLANE_ERROR")
            return self._json(409, {"status": "error", "code": code, "message": str(exc)})


class LocalControlServer:
    """Loopback-only research HTTP control plane. This is NOT an MCP implementation."""

    def __init__(self, *, instance_id: str, authority: CapabilityAuthority,
                 bridges: BridgeRegistry, runtime=None, pairing: PairingBroker | None = None,
                 host: str = "127.0.0.1", port: int = 0):
        if host not in {"127.0.0.1", "::1"}:
            raise LifecycleError("NON_LOOPBACK_BIND_REJECTED", host)
        self.httpd = ThreadingHTTPServer((host, port), _Handler)
        self.httpd.instance_id = instance_id
        self.httpd.authority = authority
        self.httpd.bridges = bridges
        self.httpd.runtime = runtime
        self.httpd.pairing = pairing
        self.thread: threading.Thread | None = None

    @property
    def host(self) -> str:
        return str(self.httpd.server_address[0])

    @property
    def port(self) -> int:
        return int(self.httpd.server_address[1])

    def start(self) -> None:
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self) -> None:
        self.httpd.shutdown()
        self.httpd.server_close()
        if self.thread:
            self.thread.join(timeout=2)

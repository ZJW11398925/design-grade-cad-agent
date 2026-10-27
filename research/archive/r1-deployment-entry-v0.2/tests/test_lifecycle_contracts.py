from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from dgcad_deployment import (
    BridgeRegistry, CapabilityAuthority, DeploymentService, EndpointRegistry,
    LifecycleError, LocalControlServer, ProjectLeaseStore,
)
from dgcad_foundation import AuthorityState, CanonicalObject, RevisionStamp, SceneState
from dgcad_runtime import AgentToolSurface, RuntimeSession, StatefulRuntime


class FakeNow:
    def __init__(self, value=1000): self.value = value
    def __call__(self): return self.value
    def advance(self, seconds): self.value += seconds


def _request(url, *, token=None, method="GET", payload=None):
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, method=method, data=data)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        return exc.code, json.loads(exc.read().decode("utf-8"))


def _runtime_service(tmp_path):
    obj = CanonicalObject("B-001", "building", RevisionStamp(1,1,1), AuthorityState.HUMAN_CONFIRMED, values={"height_m": 18.0})
    scene = SceneState("S-1", 1, {"B-001": obj})
    rt = StatefulRuntime(tmp_path / "runtime", project_id="P-1", initial_scene=scene)
    agent = RuntimeSession("agent-direct", "agent-1", frozenset({"read", "propose", "preview", "request_commit", "cancel", "rebuild", "inspect_jobs"}))
    return rt, DeploymentService(AgentToolSurface(rt, agent))


def test_endpoint_registry_is_loopback_token_free_and_private(tmp_path):
    registry = EndpointRegistry(tmp_path / "runtime.json")
    desc = registry.write(instance_id="I-1", host="127.0.0.1", port=8765, generation=2, pid=123)
    restored = registry.read()
    assert restored == desc
    raw = json.loads((tmp_path / "runtime.json").read_text())
    assert not any("token" in key or "secret" in key for key in raw)
    if os.name == "posix":
        assert ((tmp_path / "runtime.json").stat().st_mode & 0o777) == 0o600
    with pytest.raises(LifecycleError) as ex:
        registry.write(instance_id="I-2", host="0.0.0.0", port=8765)
    assert ex.value.code == "NON_LOOPBACK_BIND_REJECTED"


def test_capability_authority_keeps_agent_human_and_bridge_roles_separate():
    clock = FakeNow()
    auth = CapabilityAuthority(now_fn=clock)
    agent_token, agent = auth.issue(role="agent", actor_id="agent-1")
    human_token, human = auth.issue(role="human_review", actor_id="user-1")
    bridge_token, bridge = auth.issue(role="cad_bridge", actor_id="autocad-101")
    assert "approve" not in agent.capabilities and "unlock" not in agent.capabilities
    assert {"approve", "unlock"}.issubset(human.capabilities)
    assert "bridge_read" in bridge.capabilities and "approve" not in bridge.capabilities
    with pytest.raises(LifecycleError) as ex:
        auth.authenticate(agent_token, required={"approve"})
    assert ex.value.code == "SESSION_CAPABILITY_DENIED"
    assert auth.authenticate(human_token, required={"approve"}).actor_id == "user-1"
    assert auth.authenticate(bridge_token, required={"bridge_read"}).actor_id == "autocad-101"


def test_session_token_expires_and_revoke_is_fail_closed():
    clock = FakeNow()
    auth = CapabilityAuthority(now_fn=clock)
    token, _ = auth.issue(role="agent", actor_id="a", ttl_seconds=5)
    assert auth.authenticate(token).actor_id == "a"
    clock.advance(5)
    with pytest.raises(LifecycleError) as ex:
        auth.authenticate(token)
    assert ex.value.code == "SESSION_TOKEN_EXPIRED"
    token2, _ = auth.issue(role="agent", actor_id="a", ttl_seconds=5)
    auth.revoke(token2)
    with pytest.raises(LifecycleError) as ex2:
        auth.authenticate(token2)
    assert ex2.value.code == "SESSION_TOKEN_INVALID"


def test_project_lease_prevents_split_brain_and_allows_expired_takeover(tmp_path):
    clock = FakeNow()
    leases = ProjectLeaseStore(tmp_path / "project.db", now_fn=clock)
    a = leases.acquire("P-1", "I-A", ttl_seconds=10)
    assert a["generation"] == 1
    with pytest.raises(LifecycleError) as ex:
        leases.acquire("P-1", "I-B", ttl_seconds=10)
    assert ex.value.code == "PROJECT_RUNTIME_LEASE_HELD"
    clock.advance(11)
    b = leases.acquire("P-1", "I-B", ttl_seconds=10)
    assert b["generation"] == 2
    with pytest.raises(LifecycleError) as lost:
        leases.heartbeat("P-1", "I-A", generation=1, ttl_seconds=10)
    assert lost.value.code == "PROJECT_RUNTIME_LEASE_LOST"
    leases.close()


def test_project_lease_requires_matching_generation_on_release(tmp_path):
    leases = ProjectLeaseStore(tmp_path / "project.db", now_fn=FakeNow())
    a = leases.acquire("P-1", "I-A")
    assert leases.release("P-1", "I-A", generation=a["generation"] + 1) is False
    assert leases.release("P-1", "I-A", generation=a["generation"]) is True
    leases.close()


def test_bridge_registry_enforces_role_ownership_and_expiry():
    clock = FakeNow()
    auth = CapabilityAuthority(now_fn=clock)
    t1, p1 = auth.issue(role="cad_bridge", actor_id="acad-A", ttl_seconds=100)
    _, p2 = auth.issue(role="cad_bridge", actor_id="acad-B", ttl_seconds=100)
    _, agent = auth.issue(role="agent", actor_id="agent", ttl_seconds=100)
    bridges = BridgeRegistry(now_fn=clock)
    bridge = bridges.register(p1, bridge_type="autocad", host_pid=555, document_key="dwg:abc", ttl_seconds=5)
    assert bridge in bridges.active()
    with pytest.raises(LifecycleError) as denied:
        bridges.register(agent, bridge_type="autocad", host_pid=1)
    assert denied.value.code == "BRIDGE_CAPABILITY_REQUIRED"
    with pytest.raises(LifecycleError) as owner:
        bridges.heartbeat(bridge.bridge_id, p2)
    assert owner.value.code == "BRIDGE_SESSION_OWNERSHIP_MISMATCH"
    clock.advance(5)
    assert bridges.active() == []
    with pytest.raises(LifecycleError) as expired:
        bridges.heartbeat(bridge.bridge_id, p1)
    assert expired.value.code == "BRIDGE_SESSION_EXPIRED"


def test_loopback_control_server_health_and_auth(tmp_path):
    auth = CapabilityAuthority()
    token, _ = auth.issue(role="agent", actor_id="agent-1")
    server = LocalControlServer(instance_id="I-1", authority=auth, bridges=BridgeRegistry())
    server.start()
    try:
        base = f"http://{server.host}:{server.port}"
        status, health = _request(base + "/health")
        assert status == 200 and health["instance_id"] == "I-1"
        status2, body2 = _request(base + "/whoami")
        assert status2 == 401 and body2["code"] == "AUTH_REQUIRED"
        status3, who = _request(base + "/whoami", token=token)
        assert status3 == 200 and who["role"] == "agent"
    finally:
        server.stop()


def test_agent_cannot_use_human_control_endpoint_but_human_can(tmp_path):
    rt, service = _runtime_service(tmp_path)
    proposed = service.invoke("propose_change", {
        "object_id": "B-001", "changes": {"height_m": 21.0}, "bump": ["parameter"],
        "required_authority": "human_confirm", "reason": "lifecycle test",
    }, idempotency_key="p1")
    auth = CapabilityAuthority()
    agent_token, _ = auth.issue(role="agent", actor_id="agent-1")
    human_token, _ = auth.issue(role="human_review", actor_id="user-1")
    server = LocalControlServer(instance_id="I-1", authority=auth, bridges=BridgeRegistry(), runtime=rt)
    server.start()
    try:
        base = f"http://{server.host}:{server.port}"
        payload = {"proposal_id": proposed["proposal_id"], "idempotency_key": "approve-1"}
        s1, b1 = _request(base + "/human/approve", token=agent_token, method="POST", payload=payload)
        assert s1 == 403 and b1["code"] == "SESSION_CAPABILITY_DENIED"
        s2, b2 = _request(base + "/human/approve", token=human_token, method="POST", payload=payload)
        assert s2 == 200 and b2["status"] == "approved"
        committed = service.invoke("request_commit", {"proposal_id": proposed["proposal_id"]}, idempotency_key="commit-1")
        assert committed["status"] == "committed"
    finally:
        server.stop()


def test_bridge_register_http_rejects_agent_and_accepts_bridge_token():
    auth = CapabilityAuthority()
    agent_token, _ = auth.issue(role="agent", actor_id="agent-1")
    bridge_token, _ = auth.issue(role="cad_bridge", actor_id="acad-1")
    bridges = BridgeRegistry()
    server = LocalControlServer(instance_id="I-1", authority=auth, bridges=bridges)
    server.start()
    try:
        base = f"http://{server.host}:{server.port}"
        payload = {"bridge_type": "autocad", "host_pid": 777, "document_key": "dwg:demo"}
        s1, b1 = _request(base + "/bridge/register", token=agent_token, method="POST", payload=payload)
        assert s1 == 403 and b1["code"] == "SESSION_CAPABILITY_DENIED"
        s2, b2 = _request(base + "/bridge/register", token=bridge_token, method="POST", payload=payload)
        assert s2 == 200 and b2["status"] == "registered"
        assert len(bridges.active()) == 1
    finally:
        server.stop()


def test_local_control_server_refuses_non_loopback_bind():
    with pytest.raises(LifecycleError) as ex:
        LocalControlServer(instance_id="I-1", authority=CapabilityAuthority(), bridges=BridgeRegistry(), host="0.0.0.0")
    assert ex.value.code == "NON_LOOPBACK_BIND_REJECTED"


def test_pairing_grant_is_one_time_role_bound_and_has_no_role_request_parameter():
    clock = FakeNow()
    auth = CapabilityAuthority(now_fn=clock)
    broker = __import__('dgcad_deployment').PairingBroker(auth, now_fn=clock)
    raw, grant = broker.mint(role="agent", actor_id="agent-1", ttl_seconds=10)
    token, principal = broker.exchange(raw, session_ttl_seconds=20)
    assert grant.role == "agent"
    assert principal.role == "agent"
    assert "approve" not in principal.capabilities
    assert auth.authenticate(token).role == "agent"
    with pytest.raises(LifecycleError) as ex:
        broker.exchange(raw)
    assert ex.value.code == "PAIRING_TOKEN_INVALID"


def test_http_pairing_exchange_cannot_escalate_role_and_is_one_time():
    from dgcad_deployment import PairingBroker
    auth = CapabilityAuthority()
    broker = PairingBroker(auth)
    pairing_token, _ = broker.mint(role="agent", actor_id="agent-1")
    server = LocalControlServer(instance_id="I-1", authority=auth, bridges=BridgeRegistry(), pairing=broker)
    server.start()
    try:
        base = f"http://{server.host}:{server.port}"
        # Extra 'role' input is ignored; server-side grant owns the role.
        s1, b1 = _request(base + "/session/exchange", method="POST", payload={
            "pairing_token": pairing_token, "role": "human_review"
        })
        assert s1 == 200 and b1["role"] == "agent" and "approve" not in b1["capabilities"]
        s2, b2 = _request(base + "/session/exchange", method="POST", payload={"pairing_token": pairing_token})
        assert s2 == 401 and b2["code"] == "PAIRING_TOKEN_INVALID"
    finally:
        server.stop()


def test_local_http_rejects_dns_rebinding_style_host_and_cross_origin():
    auth = CapabilityAuthority()
    server = LocalControlServer(instance_id="I-1", authority=auth, bridges=BridgeRegistry())
    server.start()
    try:
        url = f"http://{server.host}:{server.port}/health"
        bad_host = urllib.request.Request(url)
        bad_host.add_header("Host", "evil.example")
        with pytest.raises(urllib.error.HTTPError) as ex1:
            urllib.request.urlopen(bad_host, timeout=3)
        assert ex1.value.code == 401
        body1 = json.loads(ex1.value.read().decode())
        assert body1["code"] == "LOCAL_HOST_HEADER_REJECTED"

        bad_origin = urllib.request.Request(url)
        bad_origin.add_header("Origin", "https://evil.example")
        with pytest.raises(urllib.error.HTTPError) as ex2:
            urllib.request.urlopen(bad_origin, timeout=3)
        assert ex2.value.code == 401
        body2 = json.loads(ex2.value.read().decode())
        assert body2["code"] == "LOCAL_ORIGIN_REJECTED"
    finally:
        server.stop()


def test_sidecar_host_publishes_only_after_lease_and_cleans_discovery(tmp_path):
    from dgcad_deployment import PairingBroker, SidecarLifecycleHost
    clock = FakeNow()
    lease_a = ProjectLeaseStore(tmp_path / "project.db", now_fn=clock)
    lease_b = ProjectLeaseStore(tmp_path / "project.db", now_fn=clock)
    discovery = EndpointRegistry(tmp_path / "runtime.json")

    auth_a = CapabilityAuthority(now_fn=clock)
    host_a = SidecarLifecycleHost(
        project_id="P-1", instance_id="I-A", lease_store=lease_a, discovery=discovery,
        authority=auth_a, pairing=PairingBroker(auth_a, now_fn=clock), bridges=BridgeRegistry(now_fn=clock),
    )
    desc = host_a.start()
    assert discovery.read().instance_id == "I-A"
    assert desc.host == "127.0.0.1"

    auth_b = CapabilityAuthority(now_fn=clock)
    host_b = SidecarLifecycleHost(
        project_id="P-1", instance_id="I-B", lease_store=lease_b, discovery=discovery,
        authority=auth_b, pairing=PairingBroker(auth_b, now_fn=clock), bridges=BridgeRegistry(now_fn=clock),
    )
    with pytest.raises(LifecycleError) as ex:
        host_b.start()
    assert ex.value.code == "PROJECT_RUNTIME_LEASE_HELD"
    assert discovery.read().instance_id == "I-A"

    assert host_a.stop() is True
    assert not discovery.path.exists()
    desc_b = host_b.start()
    assert desc_b.instance_id == "I-B"
    host_b.stop()
    lease_a.close(); lease_b.close()

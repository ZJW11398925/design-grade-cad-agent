from __future__ import annotations

import json
from pathlib import Path

import pytest
import yaml

from dgcad_deployment import ContentAddressedArtifactStore, DeploymentService, ProjectStoreError, SqliteProjectStore
from dgcad_deployment.cli import run_cli
from dgcad_foundation import AuthorityState, CanonicalObject, RevisionStamp, SceneState
from dgcad_runtime import AgentToolSurface, RuntimeSession, StatefulRuntime


def test_sqlite_uses_wal_and_reopens_snapshot(tmp_path):
    db = tmp_path / "project.db"
    a = SqliteProjectStore(db)
    assert a.journal_mode() == "wal"
    snap = a.create_project("P-1", {"scene_revision": 1, "objects": {"B-1": {"height": 18}}})
    a.close()
    b = SqliteProjectStore(db)
    restored = b.load("P-1")
    assert restored == snap
    b.close()


def test_sqlite_compare_and_swap_rejects_stale_writer(tmp_path):
    db = tmp_path / "project.db"
    a = SqliteProjectStore(db)
    s0 = a.create_project("P-1", {"value": 1})
    b = SqliteProjectStore(db)
    s1 = a.compare_and_swap("P-1", expected_revision=s0.state_revision, expected_hash=s0.payload_hash, payload={"value": 2})
    assert s1.state_revision == 2
    with pytest.raises(ProjectStoreError) as ex:
        b.compare_and_swap("P-1", expected_revision=s0.state_revision, expected_hash=s0.payload_hash, payload={"value": 3})
    assert ex.value.code == "PROJECT_STATE_CONCURRENT_MODIFICATION"
    a.close(); b.close()


def test_sqlite_detects_declared_hash_corruption(tmp_path):
    db = tmp_path / "project.db"
    store = SqliteProjectStore(db)
    store.create_project("P-1", {"value": 1})
    store.conn.execute("UPDATE project_state SET payload_json=? WHERE project_id='P-1'", ('{"value":999}',))
    with pytest.raises(ProjectStoreError) as ex:
        store.load("P-1")
    assert ex.value.code == "PROJECT_STATE_HASH_MISMATCH"
    store.close()


def test_artifact_store_is_content_addressed_and_deduplicated(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path / "artifacts")
    h1, p1 = store.put_bytes(b"DXF bytes")
    h2, p2 = store.put_bytes(b"DXF bytes")
    assert h1 == h2
    assert p1 == p2
    assert store.read_bytes(h1) == b"DXF bytes"


def test_artifact_store_detects_tampering(tmp_path):
    store = ContentAddressedArtifactStore(tmp_path / "artifacts")
    digest, path = store.put_bytes(b"IFC bytes")
    path.write_bytes(b"tampered")
    with pytest.raises(RuntimeError, match="ARTIFACT_CONTENT_HASH_MISMATCH"):
        store.read_bytes(digest)


def test_artifact_metadata_is_transactionally_reopenable(tmp_path):
    db = tmp_path / "project.db"
    store = SqliteProjectStore(db)
    store.create_project("P-1", {"value": 1})
    store.register_artifact("P-1", artifact_id="DXF-1", content_hash="abc", relative_path="ab/c", media_type="application/dxf", byte_size=99, source_scene_revision=4)
    store.close()
    reopened = SqliteProjectStore(db)
    rec = reopened.artifact_record("P-1", "DXF-1")
    assert rec["content_hash"] == "abc"
    assert rec["source_scene_revision"] == 4
    reopened.close()


def _runtime_service(tmp_path):
    obj = CanonicalObject("B-001", "building", RevisionStamp(1,1,1), AuthorityState.HUMAN_CONFIRMED, values={"height_m": 18.0})
    scene = SceneState("S-1", 1, {"B-001": obj})
    rt = StatefulRuntime(tmp_path / "runtime", project_id="P-1", initial_scene=scene)
    session = RuntimeSession("s1", "agent", frozenset({"read", "propose", "preview", "request_commit", "cancel", "rebuild", "inspect_jobs"}))
    return rt, DeploymentService(AgentToolSurface(rt, session))


def test_cli_and_direct_service_share_identical_semantics(tmp_path):
    rt, service = _runtime_service(tmp_path)
    args = {
        "object_id": "B-001", "changes": {"height_m": 21.0}, "bump": ["parameter"],
        "required_authority": "human_confirm", "reason": "deployment parity"
    }
    direct = service.invoke("propose_change", args, idempotency_key="same-key")
    cli = run_cli(service, ["propose_change", "--args-json", json.dumps(args), "--idempotency-key", "same-key"])
    assert cli == direct
    assert len(rt.state.proposals) == 1


def test_agent_deployment_contract_has_no_approval_tool_and_marks_mcp_unverified():
    path = Path(__file__).parents[1] / "contracts" / "deployment-boundary-contract-v0.1.yaml"
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert data["recommended_mode"] == "local_sidecar_hybrid"
    assert data["adapters"]["mcp"]["wire_level_verified_in_this_environment"] is False
    assert data["adapters"]["human_control_plane"]["exposed_as_agent_tool"] is False
    assert data["security"]["do_not_expose_store_or_database_to_agent"] is True

from __future__ import annotations
import json
from pathlib import Path

import pytest

from dgcad_foundation import AuthorityState, CanonicalObject, RevisionStamp, SceneState, World
from dgcad_runtime import (
    AgentToolSurface, ArtifactStatus, CliAdapter, HumanControlPlane, ManualClock,
    McpAdapter, RuntimeContractError, RuntimeSession, StatefulRuntime,
)


def make_scene():
    b1 = CanonicalObject(
        "B-001", "building", RevisionStamp(1, 1, 1), AuthorityState.HUMAN_CONFIRMED,
        values={"height_m": 18.0, "name": "A"},
    )
    b2 = CanonicalObject(
        "B-002", "building", RevisionStamp(1, 1, 1), AuthorityState.HUMAN_CONFIRMED,
        values={"height_m": 12.0, "name": "B"},
    )
    return SceneState("scene-001", 3, {"B-001": b1, "B-002": b2})


def sessions():
    agent = RuntimeSession(
        "agent-session", "agent-01",
        frozenset({"read", "propose", "preview", "request_commit", "cancel", "rebuild", "inspect_jobs"}),
    )
    human = RuntimeSession(
        "human-session", "human-01", frozenset({"read", "approve", "unlock", "cancel"}),
        is_human=True, can_unlock=True,
    )
    worker = RuntimeSession(
        "worker-session", "worker-control", frozenset({"claim_job", "complete_job", "retry_job"}),
    )
    return agent, human, worker


def new_runtime(tmp_path, clock=None):
    return StatefulRuntime(tmp_path / "project", project_id="PJT-001", initial_scene=make_scene(), clock=clock)


def propose_height(rt, agent, idem="idem-propose", object_id="B-001", value=21.0, ttl=None):
    return rt.propose_change(
        agent, object_id=object_id, changes={"height_m": value}, bump={"parameter"},
        required_authority="human_confirm", reason="height study",
        idempotency_key=idem, ttl_seconds=ttl,
    )


def approve_and_commit(rt, agent, human, proposal_id, *, approve_key="idem-approve", commit_key="idem-commit"):
    HumanControlPlane(rt, human).approve(proposal_id, idempotency_key=approve_key)
    return rt.request_commit(agent, proposal_id=proposal_id, idempotency_key=commit_key)


def test_state_file_roundtrip_restores_scene_proposals_and_audit(tmp_path):
    clock = ManualClock(100)
    rt = new_runtime(tmp_path, clock)
    agent, human, _ = sessions()
    p = propose_height(rt, agent)
    rt.preview_change(agent, proposal_id=p["proposal_id"], idempotency_key="idem-preview")
    approve_and_commit(rt, agent, human, p["proposal_id"])

    restored = StatefulRuntime(tmp_path / "project", clock=clock)
    assert restored.store.current.scene_revision == 4
    assert restored.store.current.objects["B-001"].values["height_m"] == 21.0
    assert restored.state.proposals[p["proposal_id"]].status.value == "committed"
    assert [e.event_type for e in restored.store.audit_log.events][-1] == "runtime_commit_requested"


def test_state_envelope_detects_payload_corruption(tmp_path):
    rt = new_runtime(tmp_path)
    path = tmp_path / "project" / "runtime-state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["payload"]["scene"]["scene_revision"] = 999
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeContractError) as ex:
        StatefulRuntime(tmp_path / "project")
    assert ex.value.code == "PROJECT_STATE_HASH_MISMATCH"


def test_idempotent_propose_returns_same_proposal_across_cli_and_mcp(tmp_path):
    rt = new_runtime(tmp_path)
    agent, _, _ = sessions()
    surface = AgentToolSurface(rt, agent)
    cli, mcp = CliAdapter(surface), McpAdapter(surface)
    args = {
        "object_id": "B-001", "changes": {"height_m": 22.0}, "bump": {"parameter"},
        "required_authority": "human_confirm", "reason": "transport parity",
    }
    a = cli.invoke("propose_change", args, idempotency_key="shared-key")
    b = mcp.invoke("propose_change", args, idempotency_key="shared-key")
    assert a == b
    assert len(rt.state.proposals) == 1


def test_idempotency_key_reuse_with_different_payload_is_rejected(tmp_path):
    rt = new_runtime(tmp_path)
    agent, _, _ = sessions()
    propose_height(rt, agent, idem="same", value=21.0)
    with pytest.raises(RuntimeContractError) as ex:
        propose_height(rt, agent, idem="same", value=22.0)
    assert ex.value.code == "IDEMPOTENCY_KEY_REUSE_MISMATCH"


def test_agent_surface_has_no_approval_tool_and_agent_cannot_mint_grant(tmp_path):
    rt = new_runtime(tmp_path)
    agent, _, _ = sessions()
    surface = AgentToolSurface(rt, agent)
    p = propose_height(rt, agent)
    res = surface.invoke("approve_proposal", {"proposal_id": p["proposal_id"]}, idempotency_key="fake")
    assert res["status"] == "blocked"
    assert res["code"] == "UNKNOWN_TOOL"
    with pytest.raises(RuntimeContractError) as ex:
        rt.approve_proposal(agent, proposal_id=p["proposal_id"], grant_kind="confirm", idempotency_key="fake-direct")
    assert ex.value.code == "CAPABILITY_DENIED"


def test_commit_blocks_without_human_grant_then_succeeds_after_server_side_approval(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, _ = sessions()
    p = propose_height(rt, agent)
    with pytest.raises(RuntimeContractError) as ex:
        rt.request_commit(agent, proposal_id=p["proposal_id"], idempotency_key="commit-before")
    assert ex.value.code == "HUMAN_APPROVAL_REQUIRED"
    HumanControlPlane(rt, human).approve(p["proposal_id"], idempotency_key="approve")
    result = rt.request_commit(agent, proposal_id=p["proposal_id"], idempotency_key="commit-after")
    assert result["status"] == "committed"
    assert rt.store.current.objects["B-001"].values["height_m"] == 21.0


def test_approval_grant_is_bound_to_scene_revision(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, _ = sessions()
    p1 = propose_height(rt, agent, idem="p1", object_id="B-001", value=21.0)
    HumanControlPlane(rt, human).approve(p1["proposal_id"], idempotency_key="approve-p1")
    p2 = propose_height(rt, agent, idem="p2", object_id="B-002", value=13.0)
    approve_and_commit(rt, agent, human, p2["proposal_id"], approve_key="approve-p2", commit_key="commit-p2")
    with pytest.raises(RuntimeContractError) as ex:
        rt.request_commit(agent, proposal_id=p1["proposal_id"], idempotency_key="commit-p1")
    assert ex.value.code == "HUMAN_APPROVAL_REQUIRED"


def test_approval_grant_expires(tmp_path):
    clock = ManualClock(100)
    rt = new_runtime(tmp_path, clock)
    agent, human, _ = sessions()
    p = propose_height(rt, agent)
    HumanControlPlane(rt, human).approve(p["proposal_id"], idempotency_key="approve", ttl_seconds=5)
    clock.advance(5)
    with pytest.raises(RuntimeContractError) as ex:
        rt.request_commit(agent, proposal_id=p["proposal_id"], idempotency_key="commit")
    assert ex.value.code == "HUMAN_APPROVAL_REQUIRED"


def test_proposal_expiry_and_cancel_are_terminal(tmp_path):
    clock = ManualClock(10)
    rt = new_runtime(tmp_path, clock)
    agent, _, _ = sessions()
    p = propose_height(rt, agent, ttl=3)
    clock.advance(3)
    with pytest.raises(RuntimeContractError) as ex:
        rt.preview_change(agent, proposal_id=p["proposal_id"], idempotency_key="preview-expired")
    assert ex.value.code == "PROPOSAL_EXPIRED"

    p2 = propose_height(rt, agent, idem="p2", value=22.0)
    rt.cancel_proposal(agent, proposal_id=p2["proposal_id"], idempotency_key="cancel")
    with pytest.raises(RuntimeContractError) as ex2:
        rt.request_commit(agent, proposal_id=p2["proposal_id"], idempotency_key="commit-cancelled")
    assert ex2.value.code == "PROPOSAL_CANCELLED"


def test_commit_invalidates_only_transitive_dependent_artifacts(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, _ = sessions()
    rt.register_artifact(artifact_id="MASS-B001", artifact_type="massing", dependency_keys={"B-001.parameter"})
    rt.register_artifact(artifact_id="SHADOW-001", artifact_type="shadow", dependency_keys={"MASS-B001"})
    rt.register_artifact(artifact_id="DXF-001", artifact_type="dxf", dependency_keys={"B-001.geometry"})
    p = propose_height(rt, agent)
    result = approve_and_commit(rt, agent, human, p["proposal_id"])
    assert result["stale_artifacts"] == ["MASS-B001", "SHADOW-001"]
    assert rt.state.artifacts["MASS-B001"].status == ArtifactStatus.STALE
    assert rt.state.artifacts["SHADOW-001"].status == ArtifactStatus.STALE
    assert rt.state.artifacts["DXF-001"].status == ArtifactStatus.CURRENT


def test_rebuild_jobs_respect_dependency_order(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    rt.register_artifact(artifact_id="SHADOW", artifact_type="shadow", dependency_keys={"MASS"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    queued = rt.rebuild_stale(agent, idempotency_key="rebuild")
    assert queued["rebuild_order"] == ["MASS", "SHADOW"]

    first = rt.claim_next_job(worker, worker_id="W-1", idempotency_key="claim-1")
    assert first["artifact_id"] == "MASS"
    empty = rt.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-blocked")
    assert empty["status"] == "empty"
    rt.complete_job(worker, job_id=first["job_id"], success=True, worker_id=first["worker_id"], attempt=first["attempt"], content_hash="h-mass", idempotency_key="done-1")
    second = rt.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-2")
    assert second["artifact_id"] == "SHADOW"


def test_running_job_is_requeued_after_restart_and_claim_idempotency_is_invalidated(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    rt.rebuild_stale(agent, idempotency_key="rebuild")
    claimed = rt.claim_next_job(worker, worker_id="W-1", idempotency_key="claim-once")
    assert claimed["status"] == "claimed"

    restored = StatefulRuntime(tmp_path / "project")
    assert restored.recovered_running_jobs == [claimed["job_id"]]
    assert restored.state.jobs[claimed["job_id"]].status.value == "queued"
    reclaimed = restored.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-once")
    assert reclaimed["job_id"] == claimed["job_id"]
    assert reclaimed["attempt"] == 2


def test_completed_job_is_idempotent_and_survives_restart(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    rt.rebuild_stale(agent, idempotency_key="rebuild")
    job = rt.claim_next_job(worker, worker_id="W-1", idempotency_key="claim")
    a = rt.complete_job(worker, job_id=job["job_id"], success=True, worker_id=job["worker_id"], attempt=job["attempt"], content_hash="abc", payload_ref="artifact://mass", idempotency_key="done")
    b = rt.complete_job(worker, job_id=job["job_id"], success=True, worker_id=job["worker_id"], attempt=job["attempt"], content_hash="abc", payload_ref="artifact://mass", idempotency_key="done")
    assert a == b
    restored = StatefulRuntime(tmp_path / "project")
    assert restored.state.jobs[job["job_id"]].status.value == "succeeded"
    assert restored.state.artifacts["MASS"].content_hash == "abc"


def test_failed_job_can_be_retried(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    rt.rebuild_stale(agent, idempotency_key="rebuild")
    job = rt.claim_next_job(worker, worker_id="W-1", idempotency_key="claim")
    rt.complete_job(worker, job_id=job["job_id"], success=False, worker_id=job["worker_id"], attempt=job["attempt"], error="worker crashed", idempotency_key="fail")
    retried = rt.retry_job(worker, job_id=job["job_id"], idempotency_key="retry")
    assert retried["status"] == "queued"
    claimed = rt.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-2")
    assert claimed["job_id"] == job["job_id"]
    assert claimed["attempt"] == 2


def test_read_only_session_cannot_propose_and_surface_returns_structured_block(tmp_path):
    rt = new_runtime(tmp_path)
    readonly = RuntimeSession("ro", "viewer", frozenset({"read"}))
    surface = AgentToolSurface(rt, readonly)
    res = surface.invoke("propose_change", {
        "object_id": "B-001", "changes": {"height_m": 30.0}, "bump": {"parameter"},
        "required_authority": "human_confirm", "reason": "nope",
    }, idempotency_key="ro")
    assert res["status"] == "blocked"
    assert res["code"] == "CAPABILITY_DENIED"


def test_cli_and_mcp_share_authority_behavior_not_just_data_shape(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, _ = sessions()
    surface = AgentToolSurface(rt, agent)
    cli, mcp = CliAdapter(surface), McpAdapter(surface)
    args = {
        "object_id": "B-001", "changes": {"height_m": 25.0}, "bump": {"parameter"},
        "required_authority": "human_confirm", "reason": "same runtime",
    }
    p = cli.invoke("propose_change", args, idempotency_key="p")
    block_cli = cli.invoke("request_commit", {"proposal_id": p["proposal_id"]}, idempotency_key="c-before-cli")
    block_mcp = mcp.invoke("request_commit", {"proposal_id": p["proposal_id"]}, idempotency_key="c-before-mcp")
    assert block_cli["code"] == block_mcp["code"] == "HUMAN_APPROVAL_REQUIRED"
    HumanControlPlane(rt, human).approve(p["proposal_id"], idempotency_key="approve")
    committed = mcp.invoke("request_commit", {"proposal_id": p["proposal_id"]}, idempotency_key="c-after")
    assert committed["status"] == "committed"


def test_transient_empty_claim_is_not_cached_after_predecessor_completes(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    rt.register_artifact(artifact_id="SHADOW", artifact_type="shadow", dependency_keys={"MASS"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    rt.rebuild_stale(agent, idempotency_key="rebuild")
    first = rt.claim_next_job(worker, worker_id="W-1", idempotency_key="claim-first")
    empty = rt.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-later")
    assert empty["status"] == "empty"
    rt.complete_job(worker, job_id=first["job_id"], success=True, worker_id=first["worker_id"],
                    attempt=first["attempt"], content_hash="mass-hash", idempotency_key="done-mass")
    later = rt.claim_next_job(worker, worker_id="W-2", idempotency_key="claim-later")
    assert later["status"] == "claimed"
    assert later["artifact_id"] == "SHADOW"


def test_old_worker_cannot_complete_reclaimed_job_after_restart(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, worker = sessions()
    rt.register_artifact(artifact_id="MASS", artifact_type="massing", dependency_keys={"B-001.parameter"})
    p = propose_height(rt, agent)
    approve_and_commit(rt, agent, human, p["proposal_id"])
    rt.rebuild_stale(agent, idempotency_key="rebuild")
    old_claim = rt.claim_next_job(worker, worker_id="W-OLD", idempotency_key="claim-old")

    restored = StatefulRuntime(tmp_path / "project")
    assert restored.state.artifacts["MASS"].status == ArtifactStatus.STALE
    new_claim = restored.claim_next_job(worker, worker_id="W-NEW", idempotency_key="claim-new")
    assert new_claim["attempt"] == old_claim["attempt"] + 1
    with pytest.raises(RuntimeContractError) as ex:
        restored.complete_job(worker, job_id=old_claim["job_id"], success=True,
                              worker_id=old_claim["worker_id"], attempt=old_claim["attempt"],
                              content_hash="old-output", idempotency_key="old-complete")
    assert ex.value.code == "STALE_JOB_CLAIM"
    ok = restored.complete_job(worker, job_id=new_claim["job_id"], success=True,
                               worker_id=new_claim["worker_id"], attempt=new_claim["attempt"],
                               content_hash="new-output", idempotency_key="new-complete")
    assert ok["status"] == "succeeded"


def test_two_runtime_instances_detect_lost_update_instead_of_overwriting(tmp_path):
    clock = ManualClock(100)
    rt1 = new_runtime(tmp_path, clock)
    rt2 = StatefulRuntime(tmp_path / "project", clock=clock)
    agent, _, _ = sessions()
    p1 = propose_height(rt1, agent, idem="rt1", object_id="B-001", value=21.0)
    assert p1["status"] == "proposed"
    with pytest.raises(RuntimeContractError) as ex:
        propose_height(rt2, agent, idem="rt2", object_id="B-002", value=13.0)
    assert ex.value.code == "PROJECT_STATE_CONCURRENT_MODIFICATION"
    authoritative = StatefulRuntime(tmp_path / "project", clock=clock)
    assert len(authoritative.state.proposals) == 1
    assert p1["proposal_id"] in authoritative.state.proposals


def test_multi_object_changeset_is_registered_previewed_and_committed_atomically(tmp_path):
    rt = new_runtime(tmp_path)
    agent, human, _ = sessions()
    p = rt.propose_changeset(
        agent,
        operations=[
            {"object_id": "B-001", "changes": {"height_m": 20.0}, "bump": {"parameter"}, "required_authority": "human_confirm"},
            {"object_id": "B-002", "changes": {"height_m": 14.0}, "bump": {"parameter"}, "required_authority": "human_confirm"},
        ],
        reason="paired massing change", idempotency_key="multi-propose",
    )
    preview = rt.preview_change(agent, proposal_id=p["proposal_id"], idempotency_key="multi-preview")
    assert preview["status"] == "previewed"
    HumanControlPlane(rt, human).approve(p["proposal_id"], idempotency_key="multi-approve")
    result = rt.request_commit(agent, proposal_id=p["proposal_id"], idempotency_key="multi-commit")
    assert result["status"] == "committed"
    assert rt.store.current.objects["B-001"].values["height_m"] == 20.0
    assert rt.store.current.objects["B-002"].values["height_m"] == 14.0
    assert rt.store.current.scene_revision == 4


def test_unlock_grant_can_authorize_mixed_atomic_set_without_losing_human_confirmation(tmp_path):
    scene = make_scene()
    b1 = scene.objects["B-001"]
    locked_b1 = CanonicalObject(
        b1.object_id, b1.object_class, b1.revisions, b1.authority_state, b1.lifecycle_state,
        b1.values, locks=frozenset({"geometry"}),
    )
    scene = SceneState(scene.scene_id, scene.scene_revision, {"B-001": locked_b1, "B-002": scene.objects["B-002"]})
    rt = StatefulRuntime(tmp_path / "project", project_id="PJT-001", initial_scene=scene)
    agent, human, _ = sessions()
    p = rt.propose_changeset(
        agent,
        operations=[
            {"object_id": "B-001", "changes": {"footprint_ref": "GEO-2"}, "bump": {"geometry"}, "required_authority": "human_unlock"},
            {"object_id": "B-002", "changes": {"height_m": 14.0}, "bump": {"parameter"}, "required_authority": "human_confirm"},
        ],
        reason="junction-like atomic test", idempotency_key="mix-propose",
    )
    HumanControlPlane(rt, human).unlock(p["proposal_id"], idempotency_key="mix-unlock")
    result = rt.request_commit(agent, proposal_id=p["proposal_id"], idempotency_key="mix-commit")
    assert result["status"] == "committed"
    assert rt.store.current.objects["B-001"].values["footprint_ref"] == "GEO-2"
    assert rt.store.current.objects["B-002"].values["height_m"] == 14.0


def test_loaded_runtime_refuses_to_overwrite_external_state_corruption(tmp_path):
    rt = new_runtime(tmp_path)
    agent, _, _ = sessions()
    path = tmp_path / "project" / "runtime-state.json"
    data = json.loads(path.read_text(encoding="utf-8"))
    data["payload"]["scene"]["scene_revision"] = 777
    # Deliberately keep the old declared payload_hash.
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RuntimeContractError) as ex:
        propose_height(rt, agent, idem="after-corruption", value=23.0)
    assert ex.value.code == "PROJECT_STATE_HASH_MISMATCH"

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dgcad_analysis import (
    ShadowAnalysisResult,
    ShadowConfig,
    run_shadow_baseline,
)
from dgcad_cad import (
    CadIR,
    CadValidationResult,
    DeliveryProfile,
    DxfCompileResult,
    DxfReadbackResult,
    build_cad_ir,
    compile_to_dxf,
    validate_cad_ir,
    validate_dxf,
)
from dgcad_domain import (
    MassingBlocked,
    build_initial_scene,
    building_massing,
    building_proposal,
    load_confirmed_trace_fixture,
    road_corridor_proposal,
    validate_scene,
)
from dgcad_foundation import DerivedArtifact
from dgcad_runtime import HumanControlPlane, RuntimeSession, StatefulRuntime


AGENT_CAPABILITIES = frozenset(
    {
        "read",
        "propose",
        "preview",
        "request_commit",
        "cancel",
        "rebuild",
        "inspect_jobs",
    }
)
HUMAN_CAPABILITIES = frozenset(
    {"read", "approve", "unlock", "review", "conflict_resolve"}
)


@dataclass(frozen=True)
class PipelineResult:
    fixture_id: str
    synthetic_only: bool
    runtime: StatefulRuntime
    trace_scene: Any
    massing: dict[str, DerivedArtifact]
    massing_blocked: dict[str, str]
    rebuild: dict[str, Any]
    commit_responses: dict[str, dict[str, Any]]
    shadow: ShadowAnalysisResult
    cad_ir: CadIR
    cad_ir_validation: CadValidationResult
    dxf_path: Path
    dxf_compile: DxfCompileResult
    dxf_readback: DxfReadbackResult
    domain_validation: Any
    output_dir: Path

    @property
    def canonical_scene(self):
        return self.runtime.store.current

    def to_dict(self) -> dict[str, Any]:
        return {
            "fixture_id": self.fixture_id,
            "synthetic_only": self.synthetic_only,
            "canonical_scene_revision": self.canonical_scene.scene_revision,
            "commit_responses": self.commit_responses,
            "massing": {
                artifact_id: {
                    "artifact_type": artifact.artifact_type,
                    "dependency_keys": sorted(artifact.dependency_keys),
                    "state": artifact.state,
                }
                for artifact_id, artifact in self.massing.items()
            },
            "massing_blocked": self.massing_blocked,
            "rebuild": self.rebuild,
            "shadow": self.shadow.to_dict(),
            "cad_ir": {
                "object_count": len(self.cad_ir.objects),
                "object_ids": [obj.object_id for obj in self.cad_ir.objects],
                "dependency_fingerprint": self.cad_ir.dependency_fingerprint,
            },
            "cad_ir_validation": self.cad_ir_validation.to_dict(),
            "dxf": self.dxf_compile.to_dict(),
            "dxf_readback": self.dxf_readback.to_dict(),
            "domain_validation": self.domain_validation.to_dict(),
            "output_dir": str(self.output_dir),
        }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(
        json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
        encoding="utf-8",
    )


def _commit_proposal(
    runtime: StatefulRuntime,
    agent: RuntimeSession,
    human: RuntimeSession,
    proposal,
    *,
    prefix: str,
) -> dict[str, Any]:
    proposed = runtime.propose_change(
        agent,
        object_id=proposal.target_object_id,
        changes=proposal.changes,
        bump=set(proposal.bump),
        required_authority="human_confirm",
        reason=proposal.reason,
        idempotency_key=f"{prefix}-propose",
    )
    proposal_id = proposed["proposal_id"]
    runtime.preview_change(
        agent,
        proposal_id=proposal_id,
        idempotency_key=f"{prefix}-preview",
    )
    HumanControlPlane(runtime, human).approve(
        proposal_id, idempotency_key=f"{prefix}-approve"
    )
    return runtime.request_commit(
        agent,
        proposal_id=proposal_id,
        idempotency_key=f"{prefix}-commit",
    )


def run_living_pipeline(
    e2e_fixture_path: str | Path, output_dir: str | Path
) -> PipelineResult:
    e2e_fixture_path = Path(e2e_fixture_path).resolve()
    output_dir = Path(output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    e2e_data = yaml.safe_load(e2e_fixture_path.read_text(encoding="utf-8"))
    if e2e_data.get("schema_id") != "dgcad.e2e.fixture.living-pipeline.v0.1":
        raise ValueError(
            f"unexpected E2E fixture schema: {e2e_data.get('schema_id')}"
        )
    domain_fixture_path = (
        e2e_fixture_path.parent / str(e2e_data["domain_fixture"])
    ).resolve()
    trace_scene = load_confirmed_trace_fixture(domain_fixture_path)
    initial_scene = build_initial_scene(trace_scene)

    runtime = StatefulRuntime(
        output_dir / "runtime",
        project_id=str(e2e_data["fixture_id"]),
        initial_scene=initial_scene,
    )
    for building_id in ("B-001", "B-003"):
        runtime.register_artifact(
            artifact_id=f"MASS-{building_id}",
            artifact_type="massing",
            dependency_keys={
                f"{building_id}.geometry",
                f"{building_id}.parameter",
            },
        )
    runtime.register_artifact(
        artifact_id="SURFACE-R-002",
        artifact_type="road_surface",
        dependency_keys={"RE-003.geometry", "R-002.parameter"},
    )

    agent = RuntimeSession(
        "E2E-AGENT", "agent-e2e", AGENT_CAPABILITIES
    )
    human = RuntimeSession(
        "E2E-HUMAN",
        "designer-e2e",
        HUMAN_CAPABILITIES,
        is_human=True,
        can_unlock=True,
    )

    commit_responses: dict[str, dict[str, Any]] = {}
    for building_id in ("B-001", "B-002", "B-003"):
        proposal = building_proposal(
            runtime.store.current,
            trace_scene,
            building_id,
            proposal_id=f"E2E-{building_id}",
            confirm=True,
        )
        commit_responses[building_id] = _commit_proposal(
            runtime, agent, human, proposal, prefix=building_id
        )
    for corridor_id in ("R-001", "R-002"):
        proposal = road_corridor_proposal(
            runtime.store.current,
            trace_scene,
            corridor_id,
            proposal_id=f"E2E-{corridor_id}",
            confirm=True,
        )
        commit_responses[corridor_id] = _commit_proposal(
            runtime, agent, human, proposal, prefix=corridor_id
        )

    scene = runtime.store.current
    massing: dict[str, DerivedArtifact] = {}
    massing_blocked: dict[str, str] = {}
    for building_id in ("B-001", "B-002", "B-003"):
        try:
            massing[building_id] = building_massing(scene, building_id)
        except MassingBlocked as exc:
            massing_blocked[building_id] = exc.code

    rebuild = runtime.rebuild_stale(agent, idempotency_key="e2e-rebuild")

    shadow_config = ShadowConfig.from_dict(e2e_data["analysis"])
    shadow = run_shadow_baseline(scene, shadow_config)

    profile = DeliveryProfile.from_dict(e2e_data["delivery"])
    cad_ir = build_cad_ir(
        scene, profile, shadow, sample_points=shadow_config.samples
    )
    cad_ir_validation = validate_cad_ir(cad_ir, profile)

    dxf_path = output_dir / "living-pipeline-001.dxf"
    dxf_compile = compile_to_dxf(cad_ir, profile, dxf_path)
    dxf_readback = validate_dxf(dxf_path, cad_ir, profile)
    domain_validation = validate_scene(scene, trace_scene)

    result = PipelineResult(
        fixture_id=str(e2e_data["fixture_id"]),
        synthetic_only=bool(e2e_data.get("synthetic_only", False)),
        runtime=runtime,
        trace_scene=trace_scene,
        massing=massing,
        massing_blocked=massing_blocked,
        rebuild=rebuild,
        commit_responses=commit_responses,
        shadow=shadow,
        cad_ir=cad_ir,
        cad_ir_validation=cad_ir_validation,
        dxf_path=dxf_path,
        dxf_compile=dxf_compile,
        dxf_readback=dxf_readback,
        domain_validation=domain_validation,
        output_dir=output_dir,
    )

    _write_json(output_dir / "cad-ir.json", cad_ir.to_dict())
    _write_json(output_dir / "shadow-result.json", shadow.to_dict())
    _write_json(output_dir / "readback-manifest.json", dxf_readback.manifest)
    _write_json(
        output_dir / "cad-ir-validation.json",
        cad_ir_validation.to_dict(),
    )
    _write_json(
        output_dir / "domain-validation.json",
        domain_validation.to_dict(),
    )
    _write_json(output_dir / "pipeline-summary.json", result.to_dict())
    return result

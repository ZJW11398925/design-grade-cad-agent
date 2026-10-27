from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, replace
from datetime import datetime
from math import isfinite
from pathlib import Path
from typing import Any

import yaml

from dgcad_analysis import ShadowAnalysisResult, ShadowConfig, run_shadow_baseline
from dgcad_cad import (
    CadIR,
    DeliveryProfile,
    build_cad_ir,
    compile_to_dxf,
    validate_cad_ir,
    validate_dxf,
)
from dgcad_domain import (
    ParameterValue,
    build_initial_scene,
    building_massing,
    building_proposal,
    height_change_proposal,
    load_confirmed_trace_fixture,
    move_road_node_changeset,
    polygon_from_geojson,
    rebuild_road_corridor_proposal,
    road_corridor_proposal,
)
from dgcad_foundation import (
    AuthorityState,
    CanonicalObject,
    ChangeProposal,
    RequiredAuthority,
    RevisionStamp,
    SceneState,
    canonical_hash,
)
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
WORKER_CAPABILITIES = frozenset({"claim_job", "complete_job"})
PROJECT_CONTEXT_ID = "PROJECT-CONTEXT-001"
ROAD_SURFACE_STATUS = "deferred_no_geometry_generator"

ARTIFACT_REGISTRATIONS = (
    ("MASS-B-001", "massing", {"B-001.geometry", "B-001.parameter"}),
    ("MASS-B-003", "massing", {"B-003.geometry", "B-003.parameter"}),
    ("PLAN-B-001", "professional_2d", {"B-001.geometry"}),
    (
        "SHADOW-E2E-002",
        "analysis",
        {
            "PROJECT-CONTEXT-001.parameter",
            "B-001.geometry",
            "B-001.parameter",
            "B-002.geometry",
            "B-002.parameter",
            "B-003.geometry",
            "B-003.parameter",
        },
    ),
    (
        "CAD-IR-E2E-002",
        "cad_ir",
        {
            "SHADOW-E2E-002",
            "SITE-001.geometry",
            "G-001.geometry",
            "B-001.geometry",
            "B-001.parameter",
            "B-002.geometry",
            "B-002.parameter",
            "B-003.geometry",
            "B-003.parameter",
            "R-001.geometry",
            "R-002.geometry",
        },
    ),
    ("DXF-E2E-002", "cad_dxf", {"CAD-IR-E2E-002"}),
)


class RebuildError(RuntimeError):
    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(f"{code}: {message}" if message else code)


@dataclass(frozen=True)
class RebuildOutput:
    artifact_id: str
    payload_ref: str
    content_hash: str
    payload: dict[str, Any]


@dataclass(frozen=True)
class RebuildReport:
    queued: dict[str, Any]
    jobs: tuple[dict[str, Any], ...]
    artifact_states: dict[str, str]
    written: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "queued": self.queued,
            "jobs": list(self.jobs),
            "artifact_states": self.artifact_states,
            "written": list(self.written),
        }


@dataclass
class LivingProject:
    e2e_fixture_path: Path
    output_dir: Path
    data: dict[str, Any]
    trace_scene: Any
    profile: DeliveryProfile
    base_shadow_config: ShadowConfig
    runtime: StatefulRuntime
    agent: RuntimeSession
    human: RuntimeSession
    worker: RuntimeSession
    latest_shadow: ShadowAnalysisResult | None = None
    latest_cad_ir: CadIR | None = None
    latest_manifest: dict[str, Any] | None = None
    road_surface_status: str = ROAD_SURFACE_STATUS
    _seq: int = 0

    @classmethod
    def create(
        cls, e2e_fixture_path: str | Path, output_dir: str | Path
    ) -> "LivingProject":
        e2e_fixture_path = Path(e2e_fixture_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        data = yaml.safe_load(e2e_fixture_path.read_text(encoding="utf-8"))
        if data.get("schema_id") != "dgcad.e2e.fixture.living-pipeline.v0.1":
            raise ValueError(
                f"unexpected E2E fixture schema: {data.get('schema_id')}"
            )
        domain_fixture_path = (
            e2e_fixture_path.parent / str(data["domain_fixture"])
        ).resolve()
        trace_scene = load_confirmed_trace_fixture(domain_fixture_path)
        scene = build_initial_scene(trace_scene)
        scene = _inject_project_context(scene, data["analysis"])
        runtime = StatefulRuntime(
            output_dir / "runtime",
            project_id=str(data["fixture_id"]),
            initial_scene=scene,
        )
        profile = DeliveryProfile.from_dict(data["delivery"])
        base_shadow_config = ShadowConfig.from_dict(data["analysis"])
        for artifact_id, artifact_type, dependency_keys in ARTIFACT_REGISTRATIONS:
            runtime.register_artifact(
                artifact_id=artifact_id,
                artifact_type=artifact_type,
                dependency_keys=set(dependency_keys),
            )
        project = cls(
            e2e_fixture_path=e2e_fixture_path,
            output_dir=output_dir,
            data=data,
            trace_scene=trace_scene,
            profile=profile,
            base_shadow_config=base_shadow_config,
            runtime=runtime,
            agent=RuntimeSession("E2E-AGENT", "agent-e2e", AGENT_CAPABILITIES),
            human=RuntimeSession(
                "E2E-HUMAN",
                "designer-e2e",
                HUMAN_CAPABILITIES,
                is_human=True,
                can_unlock=True,
            ),
            worker=RuntimeSession(
                "E2E-WORKER", "rebuild-worker", WORKER_CAPABILITIES
            ),
        )
        return project

    @property
    def scene(self) -> SceneState:
        return self.runtime.store.current

    @property
    def project_context(self) -> CanonicalObject:
        return self.scene.objects[PROJECT_CONTEXT_ID]

    @property
    def artifact_states(self) -> dict[str, str]:
        return {
            artifact_id: record.status.value
            for artifact_id, record in self.runtime.state.artifacts.items()
        }

    @property
    def stale_artifacts(self) -> set[str]:
        return {
            artifact_id
            for artifact_id, state in self.artifact_states.items()
            if state == "stale"
        }

    def artifact_state(self, artifact_id: str) -> str:
        return self.artifact_states[artifact_id]

    def shadow_config_from_scene(self) -> ShadowConfig:
        values = self.project_context.values
        return replace(
            self.base_shadow_config,
            latitude_deg=float(values["latitude_deg"]),
            longitude_deg=float(values["longitude_deg"]),
            local_datetime=datetime.fromisoformat(values["local_datetime"]),
            north_bearing_deg=float(values["north_bearing_deg"]),
            sensor_height_m=float(values["sensor_height_m"]),
            context_complete=bool(values["context_complete"]),
        )

    def _next_label(self, label: str) -> str:
        self._seq += 1
        return f"{label}-{self._seq:03d}"

    def _commit_single(self, proposal: ChangeProposal, *, prefix: str) -> dict[str, Any]:
        proposed = self.runtime.propose_change(
            self.agent,
            object_id=proposal.target_object_id,
            changes=proposal.changes,
            bump=set(proposal.bump),
            required_authority=proposal.required_authority.value,
            reason=proposal.reason,
            idempotency_key=f"{prefix}-propose",
        )
        proposal_id = proposed["proposal_id"]
        self.runtime.preview_change(
            self.agent,
            proposal_id=proposal_id,
            idempotency_key=f"{prefix}-preview",
        )
        if proposal.required_authority != RequiredAuthority.DETERMINISTIC_AUTO:
            HumanControlPlane(self.runtime, self.human).approve(
                proposal_id, idempotency_key=f"{prefix}-approve"
            )
        return self.runtime.request_commit(
            self.agent,
            proposal_id=proposal_id,
            idempotency_key=f"{prefix}-commit",
        )

    def _commit_changeset(
        self, proposals, *, reason: str, prefix: str
    ) -> dict[str, Any]:
        operations = [
            {
                "object_id": proposal.target_object_id,
                "changes": proposal.changes,
                "bump": sorted(proposal.bump),
                "required_authority": proposal.required_authority.value,
            }
            for proposal in proposals
        ]
        proposed = self.runtime.propose_changeset(
            self.agent,
            operations=operations,
            reason=reason,
            idempotency_key=f"{prefix}-propose",
        )
        proposal_id = proposed["proposal_id"]
        self.runtime.preview_change(
            self.agent,
            proposal_id=proposal_id,
            idempotency_key=f"{prefix}-preview",
        )
        HumanControlPlane(self.runtime, self.human).approve(
            proposal_id, idempotency_key=f"{prefix}-approve"
        )
        return self.runtime.request_commit(
            self.agent,
            proposal_id=proposal_id,
            idempotency_key=f"{prefix}-commit",
        )

    def bootstrap(self) -> RebuildReport:
        for building_id in ("B-001", "B-002", "B-003"):
            proposal = building_proposal(
                self.scene,
                self.trace_scene,
                building_id,
                proposal_id=self._next_label(f"BOOT-{building_id}"),
                confirm=True,
            )
            self._commit_single(
                proposal, prefix=self._next_label(f"BOOT-{building_id}")
            )
        for corridor_id in ("R-001", "R-002"):
            proposal = road_corridor_proposal(
                self.scene,
                self.trace_scene,
                corridor_id,
                proposal_id=self._next_label(f"BOOT-{corridor_id}"),
                confirm=True,
            )
            self._commit_single(
                proposal, prefix=self._next_label(f"BOOT-{corridor_id}")
            )
        return self.rebuild_all()

    def mutate_building_height(
        self, building_id: str, new_height_m: float
    ) -> dict[str, Any]:
        proposal = height_change_proposal(
            self.scene,
            building_id,
            new_height_m,
            proposal_id=self._next_label(f"HEIGHT-{building_id}"),
            confirm=True,
        )
        return self._commit_single(
            proposal, prefix=self._next_label(f"HEIGHT-{building_id}")
        )

    def mutate_road_node(
        self, node_id: str, x: float, y: float
    ) -> dict[str, Any]:
        changeset = move_road_node_changeset(
            self.scene,
            node_id,
            x,
            y,
            change_set_id=self._next_label(f"MOVE-{node_id}"),
            confirm=True,
        )
        affected_corridors = sorted(
            proposal.target_object_id
            for proposal in changeset.proposals
            if self.scene.objects[proposal.target_object_id].object_class
            == "road_corridor"
        )
        node_move = self._commit_changeset(
            changeset.proposals,
            reason=f"human-approved move of T-junction node {node_id}",
            prefix=self._next_label(f"MOVE-{node_id}"),
        )
        corridor_rebuilds: dict[str, dict[str, Any]] = {}
        for corridor_id in affected_corridors:
            proposal = rebuild_road_corridor_proposal(
                self.scene,
                corridor_id,
                proposal_id=self._next_label(f"CORRIDOR-{corridor_id}"),
                confirm=False,
            )
            corridor_rebuilds[corridor_id] = self._commit_single(
                proposal,
                prefix=self._next_label(f"CORRIDOR-{corridor_id}"),
            )
        return {
            "node_move": node_move,
            "corridor_rebuilds": corridor_rebuilds,
            "affected_corridors": affected_corridors,
        }

    def mutate_north_bearing(
        self, new_bearing_deg: float, *, source: str = "human_override"
    ) -> dict[str, Any]:
        if not isfinite(new_bearing_deg):
            raise ValueError("north bearing must be finite")
        normalized = float(new_bearing_deg) % 360.0
        context = self.project_context
        changes = {
            "north_bearing_deg": normalized,
            "north_bearing_source": source,
        }
        proposal = ChangeProposal(
            proposal_id=self._next_label("NORTH"),
            target_object_id=PROJECT_CONTEXT_ID,
            before_revisions=context.revisions,
            changes=changes,
            bump=frozenset({"parameter"}),
            required_authority=RequiredAuthority.HUMAN_CONFIRM,
            reason="human-confirmed project north bearing change",
            confirmed=True,
            before_values={
                key: context.values.get(key) for key in changes
            },
        )
        return self._commit_single(
            proposal, prefix=self._next_label("NORTH")
        )

    def rebuild_all(self) -> RebuildReport:
        self._seq += 1
        seq = self._seq
        queued = self.runtime.rebuild_stale(
            self.agent, idempotency_key=f"rebuild-{seq:03d}"
        )
        jobs: list[dict[str, Any]] = []
        written: list[str] = []
        for index in range(100):
            claimed = self.runtime.claim_next_job(
                self.worker,
                worker_id="rebuild-worker",
                idempotency_key=f"claim-{seq:03d}-{index:03d}",
            )
            if claimed["status"] == "empty":
                break
            artifact_id = claimed["artifact_id"]
            try:
                output = self._rebuild_artifact(artifact_id)
                completion = self.runtime.complete_job(
                    self.worker,
                    job_id=claimed["job_id"],
                    success=True,
                    worker_id=claimed["worker_id"],
                    attempt=claimed["attempt"],
                    idempotency_key=f"complete-{seq:03d}-{claimed['job_id']}",
                    content_hash=output.content_hash,
                    payload_ref=output.payload_ref,
                )
                written.append(output.payload_ref)
                jobs.append(
                    {
                        "job": claimed,
                        "completion": completion,
                        "payload_ref": output.payload_ref,
                        "content_hash": output.content_hash,
                        "payload": output.payload,
                    }
                )
            except Exception as exc:  # noqa: BLE001 - convert to failed job
                completion = self.runtime.complete_job(
                    self.worker,
                    job_id=claimed["job_id"],
                    success=False,
                    worker_id=claimed["worker_id"],
                    attempt=claimed["attempt"],
                    idempotency_key=f"failed-{seq:03d}-{claimed['job_id']}",
                    error=str(exc),
                )
                jobs.append(
                    {
                        "job": claimed,
                        "completion": completion,
                        "error": str(exc),
                    }
                )
                raise RebuildError(
                    "REBUILD_FAILED", f"{artifact_id}: {exc}"
                ) from exc
        else:
            raise RebuildError(
                "REBUILD_LOOP_LIMIT", "too many rebuild jobs"
            )
        return RebuildReport(
            queued=queued,
            jobs=tuple(jobs),
            artifact_states=self.artifact_states,
            written=tuple(written),
        )

    def _write_json_artifact(
        self, artifact_id: str, payload: dict[str, Any]
    ) -> RebuildOutput:
        path = self.output_dir / "artifacts" / f"{artifact_id}.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps(payload, indent=2, sort_keys=True, ensure_ascii=False),
            encoding="utf-8",
        )
        return RebuildOutput(
            artifact_id=artifact_id,
            payload_ref=path.relative_to(self.output_dir).as_posix(),
            content_hash=canonical_hash(payload),
            payload=payload,
        )

    def _massing_payload(self, artifact_id: str) -> dict[str, Any]:
        building_id = artifact_id.split("-", 1)[1]
        building = self.scene.objects[building_id]
        height = ParameterValue.from_dict(building.values["height"])
        if height.state != "confirmed":
            raise RebuildError(
                "MASSING_BLOCKED_UNKNOWN_HEIGHT",
                f"{building_id} height state is {height.state}",
            )
        footprint = polygon_from_geojson(
            building.values["professional_footprint"]
        )
        if not footprint.is_valid or footprint.area <= 0:
            raise RebuildError(
                "INVALID_FOOTPRINT", f"{building_id} footprint is invalid"
            )
        return {
            "artifact_id": artifact_id,
            "artifact_type": "massing",
            "method_id": "dgcad.massing.extrusion_summary.v0.1",
            "method_version": "0.1",
            "building_id": building_id,
            "height_m": height.value,
            "height_state": height.state,
            "height_source": height.source_ref,
            "footprint_area_m2": footprint.area,
            "volume_m3": footprint.area * height.value,
            "dependency_keys": ["B-001.geometry", "B-001.parameter"]
            if building_id == "B-001"
            else [f"{building_id}.geometry", f"{building_id}.parameter"],
            "canonical_scene_revision": self.scene.scene_revision,
            "scope": "synthetic extrusion summary; not a professional massing model",
        }

    def _plan_payload(self, artifact_id: str) -> dict[str, Any]:
        building = self.scene.objects["B-001"]
        footprint = polygon_from_geojson(
            building.values["professional_footprint"]
        )
        if not footprint.is_valid:
            raise RebuildError("INVALID_FOOTPRINT", "B-001 footprint is invalid")
        return {
            "artifact_id": artifact_id,
            "artifact_type": "professional_2d",
            "method_id": "dgcad.plan.footprint_snapshot.v0.1",
            "method_version": "0.1",
            "building_id": "B-001",
            "geometry": building.values["professional_footprint"],
            "footprint_area_m2": footprint.area,
            "geometry_revision": building.revisions.geometry,
            "dependency_keys": ["B-001.geometry"],
            "canonical_scene_revision": self.scene.scene_revision,
        }

    def _rebuild_artifact(self, artifact_id: str) -> RebuildOutput:
        if artifact_id in {"MASS-B-001", "MASS-B-003"}:
            return self._write_json_artifact(
                artifact_id, self._massing_payload(artifact_id)
            )
        if artifact_id == "PLAN-B-001":
            return self._write_json_artifact(
                artifact_id, self._plan_payload(artifact_id)
            )
        if artifact_id == "SHADOW-E2E-002":
            result = run_shadow_baseline(
                self.scene,
                self.shadow_config_from_scene(),
                analysis_id="SHADOW-E2E-002",
            )
            self.latest_shadow = result
            return self._write_json_artifact(artifact_id, result.to_dict())
        if artifact_id == "CAD-IR-E2E-002":
            if self.latest_shadow is None:
                raise RebuildError(
                    "SHADOW_RESULT_REQUIRED",
                    "CAD-IR rebuild requires a current shadow result",
                )
            cad_ir = build_cad_ir(
                self.scene,
                self.profile,
                self.latest_shadow,
                sample_points=self.base_shadow_config.samples,
            )
            validation = validate_cad_ir(cad_ir, self.profile)
            if validation.verdict == "fail":
                raise RebuildError(
                    "CAD_IR_VALIDATION_FAILED", str(validation.codes)
                )
            self.latest_cad_ir = cad_ir
            return self._write_json_artifact(
                artifact_id,
                {
                    "cad_ir": cad_ir.to_dict(),
                    "validation": validation.to_dict(),
                },
            )
        if artifact_id == "DXF-E2E-002":
            if self.latest_cad_ir is None:
                raise RebuildError(
                    "CAD_IR_REQUIRED",
                    "DXF rebuild requires a current CAD-IR",
                )
            dxf_path = self.output_dir / "living-mutations-002.dxf"
            compile_result = compile_to_dxf(
                self.latest_cad_ir, self.profile, dxf_path
            )
            readback = validate_dxf(
                dxf_path, self.latest_cad_ir, self.profile
            )
            if readback.verdict != "pass":
                raise RebuildError(
                    "DXF_READBACK_FAILED", str(readback.codes)
                )
            self.latest_manifest = readback.manifest
            manifest_path = self.output_dir / "readback-manifest-002.json"
            manifest_path.write_text(
                json.dumps(
                    readback.manifest,
                    indent=2,
                    sort_keys=True,
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            content_hash = hashlib.sha256(
                dxf_path.read_bytes()
            ).hexdigest()
            return RebuildOutput(
                artifact_id=artifact_id,
                payload_ref=dxf_path.relative_to(self.output_dir).as_posix(),
                content_hash=content_hash,
                payload={
                    "dxf": compile_result.to_dict(),
                    "readback": readback.to_dict(),
                    "manifest_ref": manifest_path.relative_to(
                        self.output_dir
                    ).as_posix(),
                },
            )
        raise RebuildError("NO_REBUILD_EXECUTOR", artifact_id)

    def summary(self) -> dict[str, Any]:
        return {
            "fixture_id": self.data["fixture_id"],
            "canonical_scene_revision": self.scene.scene_revision,
            "artifact_states": self.artifact_states,
            "road_surface_status": self.road_surface_status,
            "north_bearing_deg": self.project_context.values[
                "north_bearing_deg"
            ],
            "north_bearing_source": self.project_context.values[
                "north_bearing_source"
            ],
            "north_bearing_parameter_revision": (
                self.project_context.revisions.parameter
            ),
            "shadow_dependency_fingerprint": (
                None
                if self.latest_shadow is None
                else self.latest_shadow.dependency_fingerprint
            ),
            "cad_ir_dependency_fingerprint": (
                None
                if self.latest_cad_ir is None
                else self.latest_cad_ir.dependency_fingerprint
            ),
            "manifest": self.latest_manifest,
        }


def _inject_project_context(
    scene: SceneState, analysis: dict[str, Any]
) -> SceneState:
    context = CanonicalObject(
        object_id=PROJECT_CONTEXT_ID,
        object_class="project_context",
        revisions=RevisionStamp(1, 0, 1),
        authority_state=AuthorityState.HUMAN_CONFIRMED,
        values={
            "north_bearing_deg": float(
                analysis["project_y_axis_true_north_bearing_deg"]
            ),
            "north_bearing_source": "e2e_fixture_declared",
            "latitude_deg": float(analysis["latitude_deg"]),
            "longitude_deg": float(analysis["longitude_deg"]),
            "local_datetime": str(analysis["local_datetime"]),
            "sensor_height_m": float(analysis.get("sensor_height_m", 1.5)),
            "context_complete": bool(
                analysis.get("context_complete", True)
            ),
            "synthetic_only": True,
        },
    )
    return replace(
        scene, objects={**scene.objects, PROJECT_CONTEXT_ID: context}
    )

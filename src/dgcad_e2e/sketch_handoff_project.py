from __future__ import annotations

import hashlib
import json
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from dgcad_analysis import ShadowAnalysisResult, SolarPosition
from dgcad_cad import (
    CadIR,
    DeliveryProfile,
    build_cad_ir,
    compile_to_dxf,
    validate_cad_ir,
    validate_dxf,
)
from dgcad_domain import (
    MassingBlocked,
    SketchHandoff,
    building_massing,
    building_proposal,
    build_initial_scene,
    road_corridor_proposal,
)
from dgcad_foundation import (
    AuthorityState,
    CanonicalObject,
    RevisionStamp,
    SceneState,
    canonical_hash,
)
from dgcad_runtime import HumanControlPlane, RuntimeSession, StatefulRuntime

from .privacy import scan_dxf_privacy


ROOT = Path(__file__).resolve().parents[2]
E2E_FIXTURE = ROOT / "fixtures" / "e2e" / "living-pipeline-001.yaml"

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


def _json(value: Any) -> Any:
    if isinstance(value, dict):
        return {str(key): _json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json(item) for item in value]
    if hasattr(value, "value"):
        return value.value
    return value


def _object_snapshot(obj: CanonicalObject) -> dict[str, Any]:
    return {
        "object_id": obj.object_id,
        "object_class": obj.object_class,
        "authority_state": obj.authority_state.value,
        "lifecycle_state": obj.lifecycle_state.value,
        "revisions": {
            "semantic": obj.revisions.semantic,
            "geometry": obj.revisions.geometry,
            "parameter": obj.revisions.parameter,
        },
        "values": _json(obj.values),
        "locks": sorted(obj.locks),
        "locked_paths": sorted(obj.locked_paths),
    }


def _not_run_shadow(handoff_id: str, scene_id: str) -> ShadowAnalysisResult:
    fingerprint = canonical_hash(
        {
            "analysis": "not_run",
            "handoff_id": handoff_id,
            "scene_id": scene_id,
            "reason": (
                "no site location/time was provided for the handoff pilot; "
                "environment analysis is intentionally not executed"
            ),
        }
    )
    return ShadowAnalysisResult(
        analysis_id="SHADOW-HANDOFF-A-NOT-RUN",
        status="not_run",
        solar_position=SolarPosition(elevation_deg=0.0, azimuth_deg=0.0),
        samples=(),
        dependency_fingerprint=fingerprint,
    )


def _handoff_audit_object(
    handoff: SketchHandoff, review_ref: str
) -> CanonicalObject:
    review = handoff.review
    human_confirmation = review.review_kind == "human_object_review"
    return CanonicalObject(
        object_id=f"HANDOFF-{handoff.handoff_id}",
        object_class="sketch_handoff",
        revisions=RevisionStamp(1, 0, 0),
        authority_state=(
            AuthorityState.HUMAN_CONFIRMED
            if human_confirmation
            else AuthorityState.CANDIDATE
        ),
        values={
            "handoff_id": handoff.handoff_id,
            "case_id": handoff.case_id,
            "review_ref": review_ref,
            "review_kind": review.review_kind,
            "object_geometry_review": review.object_geometry_review,
            "human_confirmation_claimed": human_confirmation,
            "source_sketch_sha256": handoff.source_sketch_sha256,
            "source_files": [dict(item) for item in handoff.source_files],
            "site_boundary_authority": handoff.site_boundary_authority,
            "confirmation_scope": review.review_scope,
            "geometry_quality": next(iter(handoff.objects.values())).geometry_state,
            "review_scope": review.review_scope,
            "reviewer_role": review.reviewer_role,
            "review_basis": review.basis,
            "review_packet_sha256": review.review_packet_sha256,
            "coordinate_handoff": {
                "source_frame": handoff.coordinate.source_frame,
                "target_frame": handoff.coordinate.target_frame,
                "coordinate_state": handoff.coordinate.coordinate_state,
                "transform_kind": handoff.coordinate.transform_kind,
                "homography_applied": handoff.coordinate.homography_applied,
                "shape_correction": handoff.coordinate.shape_correction,
                "axis_orientation": handoff.coordinate.axis_orientation,
                "scale_px_per_m": handoff.coordinate.scale_px_per_m,
                "scale_range_px_per_m": list(
                    handoff.coordinate.scale_range_px_per_m
                ),
                "scale_source": handoff.coordinate.scale_source,
                "origin_px": list(handoff.coordinate.origin_px),
                "origin_source": handoff.coordinate.origin_source,
                "project_coordinates": handoff.coordinate.project_coordinates,
                "calibration_ref": handoff.coordinate.calibration_ref,
                "accuracy": handoff.coordinate.accuracy,
                "not_survey_grade": handoff.coordinate.not_survey_grade,
                "uncertainty_method": handoff.coordinate.uncertainty_method,
            },
            "mapping": handoff.mapping(),
            "source_edge_ids_by_corridor": {
                key: list(value)
                for key, value in handoff.source_edge_ids_by_corridor.items()
            },
            "road_topology": handoff.road_topology_report(),
            "non_claims": list(handoff.non_claims),
        },
    )


@dataclass
class SketchHandoffProject:
    handoff_path: Path
    review_path: Path
    output_dir: Path
    handoff: SketchHandoff
    trace_scene: Any
    scene: SceneState
    profile: DeliveryProfile
    runtime: StatefulRuntime
    agent: RuntimeSession
    human: RuntimeSession
    source_root: Path | None = None
    latest_cad_ir: CadIR | None = None
    latest_readback: Any = None

    @classmethod
    def create(
        cls,
        handoff_path: str | Path,
        review_path: str | Path,
        output_dir: str | Path,
        *,
        allow_test_double: bool = False,
        verify_sources: bool = True,
        root: str | Path | None = None,
    ) -> "SketchHandoffProject":
        handoff_path = Path(handoff_path).resolve()
        review_path = Path(review_path).resolve()
        output_dir = Path(output_dir).resolve()
        output_dir.mkdir(parents=True, exist_ok=True)
        source_root = (
            Path(root).resolve() if root is not None else ROOT
        )
        handoff = SketchHandoff.load(
            handoff_path,
            review_path,
            require_confirmation=True,
            allow_test_double=allow_test_double,
            verify_sources=verify_sources,
            root=source_root,
        )
        trace_scene = handoff.to_confirmed_trace_scene()
        scene = build_initial_scene(trace_scene)
        audit = _handoff_audit_object(handoff, review_path.name)
        scene = SceneState(
            scene_id=scene.scene_id,
            scene_revision=scene.scene_revision,
            objects={**scene.objects, audit.object_id: audit},
            world=scene.world,
        )
        profile_data = yaml.safe_load(E2E_FIXTURE.read_text(encoding="utf-8"))[
            "delivery"
        ]
        profile_data = dict(profile_data)
        profile_data["coordinate_frame_ref"] = handoff.coordinate.target_frame
        profile_data["coordinate_state"] = handoff.coordinate.coordinate_state
        profile = DeliveryProfile.from_dict(profile_data)
        runtime = StatefulRuntime(
            output_dir / "runtime",
            project_id=handoff.handoff_id,
            initial_scene=scene,
        )
        return cls(
            handoff_path=handoff_path,
            review_path=review_path,
            output_dir=output_dir,
            handoff=handoff,
            trace_scene=trace_scene,
            scene=scene,
            profile=profile,
            runtime=runtime,
            agent=RuntimeSession(
                "HANDOFF-AGENT", "agent-handoff", AGENT_CAPABILITIES
            ),
            human=RuntimeSession(
                "HANDOFF-HUMAN",
                "designer-handoff",
                HUMAN_CAPABILITIES,
                is_human=True,
                can_unlock=True,
            ),
            source_root=source_root,
        )

    @property
    def scene_current(self) -> SceneState:
        return self.runtime.store.current

    def _commit_single(self, proposal, *, prefix: str) -> dict[str, Any]:
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
        HumanControlPlane(self.runtime, self.human).approve(
            proposal_id, idempotency_key=f"{prefix}-approve"
        )
        return self.runtime.request_commit(
            self.agent,
            proposal_id=proposal_id,
            idempotency_key=f"{prefix}-commit",
        )

    def run_pilot(self) -> dict[str, Any]:
        trace_before = {
            trace_id: self.scene_current.objects[trace_id].values["geometry"]
            for trace_id in self.trace_scene.trace_objects
        }
        building_results = []
        for intent in self.handoff.buildings:
            proposal = building_proposal(
                self.scene_current,
                self.trace_scene,
                intent.object_id,
                proposal_id=f"HANDOFF-{intent.object_id}-PROP",
                confirm=True,
            )
            building_results.append(
                self._commit_single(
                    proposal, prefix=f"HANDOFF-{intent.object_id}"
                )
            )
        road_results = []
        for intent in self.handoff.roads:
            proposal = road_corridor_proposal(
                self.scene_current,
                self.trace_scene,
                intent.corridor_id,
                proposal_id=f"HANDOFF-{intent.corridor_id}-PROP",
                confirm=True,
            )
            road_results.append(
                self._commit_single(
                    proposal, prefix=f"HANDOFF-{intent.corridor_id}"
                )
            )

        scene = self.scene_current
        trace_after = {
            trace_id: self.scene_current.objects[trace_id].values["geometry"]
            for trace_id in trace_before
        }
        trace_unchanged = {
            trace_id: trace_before[trace_id] == trace_after[trace_id]
            for trace_id in trace_before
        }

        massing = {}
        for intent in self.handoff.buildings:
            try:
                artifact = building_massing(scene, intent.object_id)
                massing[intent.object_id] = {
                    "state": "generated",
                    "artifact_id": artifact.artifact_id,
                }
            except MassingBlocked as exc:
                massing[intent.object_id] = {
                    "state": "blocked",
                    "code": exc.code,
                }

        road_profiles = {}
        for intent in self.handoff.roads:
            obj = scene.objects[intent.corridor_id]
            road_profiles[intent.corridor_id] = {
                "centerline_state": obj.values.get("centerline_state"),
                "hierarchy": obj.values.get("hierarchy"),
                "hierarchy_state": obj.values.get("hierarchy_state"),
                "cross_section": obj.values.get("cross_section"),
                "profile_resolution": obj.values.get("profile_resolution"),
                "width_claim": "none",
            }

        shadow = _not_run_shadow(
            self.handoff.handoff_id, scene.scene_id
        )
        cad_ir = build_cad_ir(
            scene, self.profile, shadow, sample_points=()
        )
        cad_validation = validate_cad_ir(cad_ir, self.profile)
        dxf_path = self.output_dir / "pilot.dxf"
        compile_result = compile_to_dxf(cad_ir, self.profile, dxf_path)
        readback = validate_dxf(dxf_path, cad_ir, self.profile)
        privacy = scan_dxf_privacy(dxf_path)
        integrity = (
            self.handoff.source_integrity_report(self.source_root)
            if self.source_root is not None
            else {"ok": False, "errors": [{"code": "SOURCE_ROOT_MISSING"}]}
        )
        road_topology = self.handoff.road_topology_report()
        sensitivity = self.handoff.coordinate_sensitivity_report()

        self.latest_cad_ir = cad_ir
        self.latest_readback = readback

        cad_objects = {obj.object_id: obj for obj in cad_ir.objects}
        entities = readback.manifest.get("entities", [])
        entities_by_id: dict[str, list[dict[str, Any]]] = {}
        for entity in entities:
            entities_by_id.setdefault(entity["object_id"], []).append(entity)

        provenance = []
        for item in self.handoff.mapping():
            canonical_id = item["canonical_id"]
            canonical = scene.objects.get(canonical_id)
            cad = cad_objects.get(canonical_id)
            corridor_for_edge = next(
                (
                    intent.corridor_id
                    for intent in self.handoff.roads
                    if canonical_id in intent.edge_refs
                ),
                None,
            )
            provenance.append(
                {
                    **item,
                    "canonical_object_found": canonical is not None,
                    "canonical_class": (
                        None if canonical is None else canonical.object_class
                    ),
                    "canonical_authority_state": (
                        None
                        if canonical is None
                        else canonical.authority_state.value
                    ),
                    "canonical_confirmation_scope": (
                        None
                        if canonical is None
                        else canonical.values.get("confirmation_scope")
                    ),
                    "cad_ir_object_found": cad is not None,
                    "source_trace_ref_in_cad_ir": (
                        None
                        if cad is None
                        else cad.provenance.get("source_trace_ref")
                    ),
                    "edge_exported_as_corridor": corridor_for_edge,
                    "readback_entity_count": len(
                        entities_by_id.get(
                            canonical_id if cad is not None else corridor_for_edge,
                            [],
                        )
                    ),
                    "xdata_object_ids": sorted(
                        {
                            entity["object_id"]
                            for entity in entities_by_id.get(
                                canonical_id if cad is not None else corridor_for_edge,
                                [],
                            )
                        }
                    ),
                }
            )

        corridor_provenance = []
        for intent in self.handoff.roads:
            canonical = scene.objects[intent.corridor_id]
            cad = cad_objects.get(intent.corridor_id)
            corridor_provenance.append(
                {
                    "corridor_id": intent.corridor_id,
                    "trace_refs": list(intent.trace_refs),
                    "edge_refs": list(intent.edge_refs),
                    "source_edge_ids": list(
                        self.handoff.source_edge_ids_by_corridor.get(
                            intent.corridor_id, ()
                        )
                    ),
                    "canonical_object_found": canonical is not None,
                    "canonical_centerline_state": canonical.values.get(
                        "centerline_state"
                    ),
                    "canonical_confirmation_scope": canonical.values.get(
                        "confirmation_scope"
                    ),
                    "cad_ir_object_found": cad is not None,
                    "source_trace_ref_in_cad_ir": (
                        None
                        if cad is None
                        else cad.provenance.get("source_trace_ref")
                    ),
                    "readback_entity_count": len(
                        entities_by_id.get(intent.corridor_id, [])
                    ),
                }
            )

        node_provenance = [
            {
                "node_id": node_id,
                "canonical_object_found": node_id in scene.objects,
                "canonical_confirmation_scope": (
                    scene.objects[node_id].values.get("confirmation_scope")
                    if node_id in scene.objects
                    else None
                ),
                "exported_to_dxf": False,
                "reason": "road graph node; exported through corridor edges",
            }
            for node_id in self.handoff.road_graph.nodes
        ]

        human_confirmation = (
            self.handoff.review.review_kind == "human_object_review"
        )
        summary = {
            "schema_id": "dgcad.e2e.sketch-handoff-a.v0.2",
            "handoff_id": self.handoff.handoff_id,
            "case_id": self.handoff.case_id,
            "status": "executed",
            "synthetic_only": False,
            "pilot_scope": True,
            "ep_r1_sketch_complete": False,
            "review_kind": self.handoff.review.review_kind,
            "object_geometry_review": (
                self.handoff.review.object_geometry_review
            ),
            "human_confirmation_claimed": human_confirmation,
            "human_confirmed_trace": human_confirmation,
            "runtime_approval_kind": "simulated_human_session",
            "test_only": self.handoff.review.review_kind == "test_double",
            "review_scope": self.handoff.review.review_scope,
            "confirmation_scope": self.handoff.review.review_scope,
            "geometry_quality": self.trace_scene.geometry_quality,
            "reviewer_role": self.handoff.review.reviewer_role,
            "review_basis": self.handoff.review.basis,
            "review_packet_sha256": (
                self.handoff.review.review_packet_sha256
            ),
            "source_sketch_sha256": self.handoff.source_sketch_sha256,
            "source_files": [dict(item) for item in self.handoff.source_files],
            "site_boundary_authority": self.handoff.site_boundary_authority,
            "site_canonical_id": self.trace_scene.site_canonical_id,
            "selected_objects": self.handoff.mapping(),
            "coordinate_handoff": {
                "source_frame": self.handoff.coordinate.source_frame,
                "target_frame": self.handoff.coordinate.target_frame,
                "coordinate_state": self.handoff.coordinate.coordinate_state,
                "transform_kind": self.handoff.coordinate.transform_kind,
                "homography_applied": self.handoff.coordinate.homography_applied,
                "shape_correction": self.handoff.coordinate.shape_correction,
                "axis_orientation": self.handoff.coordinate.axis_orientation,
                "scale_px_per_m": self.handoff.coordinate.scale_px_per_m,
                "scale_range_px_per_m": list(
                    self.handoff.coordinate.scale_range_px_per_m
                ),
                "scale_source": self.handoff.coordinate.scale_source,
                "origin_px": list(self.handoff.coordinate.origin_px),
                "origin_source": self.handoff.coordinate.origin_source,
                "project_coordinates": self.handoff.coordinate.project_coordinates,
                "accuracy": self.handoff.coordinate.accuracy,
                "not_survey_grade": self.handoff.coordinate.not_survey_grade,
                "uncertainty_method": self.handoff.coordinate.uncertainty_method,
            },
            "coordinate_sensitivity": sensitivity,
            "buildings": [
                {
                    "object_id": intent.object_id,
                    "trace_ref": intent.trace_ref,
                    "height": intent.height.to_dict(),
                    "base_elevation": intent.base_elevation.to_dict(),
                    "massing": massing[intent.object_id],
                }
                for intent in self.handoff.buildings
            ],
            "roads": [
                {
                    "corridor_id": intent.corridor_id,
                    "hierarchy": intent.hierarchy,
                    "hierarchy_state": intent.hierarchy_state,
                    "cross_section": None,
                    "profile": road_profiles[intent.corridor_id],
                }
                for intent in self.handoff.roads
            ],
            "trace_immutable": trace_unchanged,
            "handoff_audit_object": f"HANDOFF-{self.handoff.handoff_id}",
            "canonical_scene_revision": scene.scene_revision,
            "cad_ir_dependency_fingerprint": cad_ir.dependency_fingerprint,
            "cad_ir_validation": cad_validation.to_dict(),
            "dxf": {
                "path": dxf_path.name,
                "sha256": hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
                "entity_count": compile_result.entity_count,
                "audit_errors": compile_result.audit_errors,
                "audit_fixes": compile_result.audit_fixes,
            },
            "readback": {
                "verdict": readback.verdict,
                "codes": list(readback.codes),
                "entity_count": readback.manifest.get("entity_count"),
                "expected_entity_count": readback.manifest.get(
                    "expected_entity_count"
                ),
                "confirmation_scopes": readback.manifest.get(
                    "confirmation_scopes"
                ),
                "manifest_sha256": canonical_hash(readback.manifest),
            },
            "privacy": privacy,
            "integrity": integrity,
            "road_topology": road_topology,
            "provenance": provenance,
            "corridor_provenance": corridor_provenance,
            "road_node_provenance": node_provenance,
            "shadow_analysis": {
                "status": shadow.status,
                "samples": 0,
                "note": "environment analysis intentionally not run; no site location/time",
            },
            "delivery_profile": {
                "profile_id": self.profile.profile_id,
                "profile_version": self.profile.profile_version,
                "state": "synthetic_e2e_profile_not_design_office",
            },
            "non_claims": list(self.handoff.non_claims)
            + [
                "same-library ezdxf readback; not third-party CAD evidence",
                "pilot subset only; EP-R1-SKETCH-001 is not complete",
                "unknown height, base elevation, road hierarchy and cross-section remain unknown",
                "the runtime approval is a simulated human session in the test, not the design review",
            ],
        }
        self._write_evidence(summary, cad_ir, readback, shadow)
        return summary

    def _write_evidence(
        self,
        summary: dict[str, Any],
        cad_ir: CadIR,
        readback,
        shadow: ShadowAnalysisResult,
    ) -> None:
        out = self.output_dir
        out.mkdir(parents=True, exist_ok=True)
        (out / "handoff-summary.json").write_text(
            json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        (out / "canonical-snapshot.json").write_text(
            json.dumps(
                {
                    "scene_id": self.scene_current.scene_id,
                    "scene_revision": self.scene_current.scene_revision,
                    "objects": {
                        object_id: _object_snapshot(obj)
                        for object_id, obj in sorted(
                            self.scene_current.objects.items()
                        )
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out / "cad-ir.json").write_text(
            json.dumps(cad_ir.to_dict(), indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out / "readback-manifest.json").write_text(
            json.dumps(readback.manifest, indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out / "validation.json").write_text(
            json.dumps(
                {
                    "cad_ir": summary["cad_ir_validation"],
                    "dxf_readback": readback.to_dict(),
                    "privacy": summary["privacy"],
                    "integrity": summary["integrity"],
                    "road_topology": summary["road_topology"],
                    "verdicts": {
                        "cad_ir": summary["cad_ir_validation"]["verdict"],
                        "dxf_readback": readback.verdict,
                        "privacy": (
                            "pass" if summary["privacy"]["ok"] else "fail"
                        ),
                        "integrity": (
                            "pass" if summary["integrity"]["ok"] else "fail"
                        ),
                    },
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out / "provenance-map.json").write_text(
            json.dumps(
                {
                    "handoff_id": self.handoff.handoff_id,
                    "review_kind": summary["review_kind"],
                    "confirmation_scope": summary["confirmation_scope"],
                    "human_confirmation_claimed": summary[
                        "human_confirmation_claimed"
                    ],
                    "mapping": summary["provenance"],
                    "selected_objects": summary["selected_objects"],
                    "corridors": summary["corridor_provenance"],
                    "road_nodes": summary["road_node_provenance"],
                    "handoff_audit_object": summary["handoff_audit_object"],
                    "integrity": summary["integrity"],
                    "road_topology": summary["road_topology"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out / "coordinate-sensitivity.json").write_text(
            json.dumps(
                {
                    "transform_kind": summary["coordinate_handoff"][
                        "transform_kind"
                    ],
                    "homography_applied": summary["coordinate_handoff"][
                        "homography_applied"
                    ],
                    "shape_correction": summary["coordinate_handoff"][
                        "shape_correction"
                    ],
                    "axis_orientation": summary["coordinate_handoff"][
                        "axis_orientation"
                    ],
                    "objects": summary["coordinate_sensitivity"],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        (out / "integrity.json").write_text(
            json.dumps(summary["integrity"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out / "road-topology.json").write_text(
            json.dumps(
                summary["road_topology"], indent=2, ensure_ascii=False
            ),
            encoding="utf-8",
        )
        (out / "privacy.json").write_text(
            json.dumps(summary["privacy"], indent=2, ensure_ascii=False),
            encoding="utf-8",
        )
        (out / "shadow-not-run.json").write_text(
            json.dumps(
                {
                    "analysis_id": shadow.analysis_id,
                    "status": shadow.status,
                    "dependency_fingerprint": shadow.dependency_fingerprint,
                    "samples": 0,
                    "note": summary["shadow_analysis"]["note"],
                    "non_claims": [
                        "no solar/daylight result is computed or claimed",
                    ],
                },
                indent=2,
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        shutil.copyfile(self.handoff_path, out / "handoff.yaml")
        shutil.copyfile(self.review_path, out / "review-record.yaml")
        self.handoff.write_domain_fixture(out / "domain-fixture.yaml")


def write_blocked_evidence(
    handoff: SketchHandoff,
    output_dir: str | Path,
    *,
    handoff_path: str | Path,
    review_path: str | Path,
    code: str,
    message: str,
    packet: dict[str, Any] | None = None,
    root: str | Path | None = None,
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    source_root = Path(root).resolve() if root is not None else ROOT
    integrity = handoff.source_integrity_report(source_root)
    road_topology = handoff.road_topology_report()
    sensitivity = handoff.coordinate_sensitivity_report()
    object_checks = {
        item["source_id"]: item for item in integrity.get("objects", [])
    }
    mapping = []
    for item in handoff.mapping():
        check = object_checks.get(item["source_id"], {})
        mapping.append(
            {
                **item,
                "source_geometry_verified": bool(
                    check.get("geometry_hash_matches")
                    and check.get("handoff_geometry_matches")
                ),
                "canonical_object_found": False,
                "canonical_object_created": False,
            }
        )
    summary = {
        "schema_id": "dgcad.e2e.sketch-handoff-a.v0.2",
        "handoff_id": handoff.handoff_id,
        "case_id": handoff.case_id,
        "status": "blocked",
        "pipeline_executed": False,
        "blocked": {"code": code, "message": message},
        "synthetic_only": False,
        "pilot_scope": True,
        "ep_r1_sketch_complete": False,
        "review_kind": handoff.review.review_kind,
        "object_geometry_review": handoff.review.object_geometry_review,
        "human_confirmation_claimed": False,
        "human_confirmed_trace": False,
        "review_scope": handoff.review.review_scope,
        "confirmation_scope": handoff.review.review_scope,
        "geometry_quality": next(iter(handoff.objects.values())).geometry_state,
        "reviewer_role": handoff.review.reviewer_role,
        "review_basis": handoff.review.basis,
        "review_packet_sha256": (
            None if packet is None else packet.get("packet_sha256")
        ),
        "source_sketch_sha256": handoff.source_sketch_sha256,
        "source_files": [dict(item) for item in handoff.source_files],
        "site_boundary_authority": handoff.site_boundary_authority,
        "site_canonical_id": next(
            obj.canonical_id
            for obj in handoff.objects.values()
            if obj.semantic_role == "site_boundary"
        ),
        "selected_objects": handoff.mapping(),
        "coordinate_handoff": {
            "source_frame": handoff.coordinate.source_frame,
            "target_frame": handoff.coordinate.target_frame,
            "coordinate_state": handoff.coordinate.coordinate_state,
            "transform_kind": handoff.coordinate.transform_kind,
            "homography_applied": handoff.coordinate.homography_applied,
            "shape_correction": handoff.coordinate.shape_correction,
            "axis_orientation": handoff.coordinate.axis_orientation,
            "scale_px_per_m": handoff.coordinate.scale_px_per_m,
            "scale_range_px_per_m": list(
                handoff.coordinate.scale_range_px_per_m
            ),
            "scale_source": handoff.coordinate.scale_source,
            "origin_px": list(handoff.coordinate.origin_px),
            "origin_source": handoff.coordinate.origin_source,
            "project_coordinates": handoff.coordinate.project_coordinates,
            "accuracy": handoff.coordinate.accuracy,
            "not_survey_grade": handoff.coordinate.not_survey_grade,
            "uncertainty_method": handoff.coordinate.uncertainty_method,
        },
        "coordinate_sensitivity": sensitivity,
        "canonical": None,
        "cad_ir": None,
        "dxf": None,
        "readback": None,
        "privacy": None,
        "integrity": integrity,
        "road_topology": road_topology,
        "provenance": mapping,
        "required_actions": [
            "inspect review-packet.html and every object overlay",
            "fill review-confirmation-template.yaml with per-object geometry and coordinate decisions",
            "set human_confirmed_trace: true only after the inspection",
            "record the review packet hash and reviewed_at date",
            "re-run the pilot after the review record is signed",
        ],
        "non_claims": list(handoff.non_claims)
        + [
            "authorization to run a pilot is not an object-level geometry review",
            "no canonical object, CAD-IR or DXF was produced in this blocked run",
        ],
    }
    (output_dir / "handoff-summary.json").write_text(
        json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "blocked.json").write_text(
        json.dumps(
            {
                "status": "blocked",
                "code": code,
                "message": message,
                "handoff_id": handoff.handoff_id,
                "review_kind": handoff.review.review_kind,
                "object_geometry_review": handoff.review.object_geometry_review,
                "human_confirmation_claimed": False,
                "required_actions": summary["required_actions"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "integrity.json").write_text(
        json.dumps(integrity, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "road-topology.json").write_text(
        json.dumps(road_topology, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    (output_dir / "coordinate-sensitivity.json").write_text(
        json.dumps(
            {
                "transform_kind": handoff.coordinate.transform_kind,
                "homography_applied": handoff.coordinate.homography_applied,
                "shape_correction": handoff.coordinate.shape_correction,
                "axis_orientation": handoff.coordinate.axis_orientation,
                "objects": sensitivity,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    (output_dir / "provenance-map.json").write_text(
        json.dumps(
            {
                "handoff_id": handoff.handoff_id,
                "review_kind": handoff.review.review_kind,
                "confirmation_scope": handoff.review.review_scope,
                "human_confirmation_claimed": False,
                "mapping": mapping,
                "selected_objects": handoff.mapping(),
                "corridors": [
                    {
                        "corridor_id": intent.corridor_id,
                        "trace_refs": list(intent.trace_refs),
                        "edge_refs": list(intent.edge_refs),
                        "source_edge_ids": list(
                            handoff.source_edge_ids_by_corridor.get(
                                intent.corridor_id, ()
                            )
                        ),
                        "canonical_object_found": False,
                    }
                    for intent in handoff.roads
                ],
                "road_nodes": [
                    {
                        "node_id": node_id,
                        "canonical_object_found": False,
                        "exported_to_dxf": False,
                        "reason": "blocked before canonical binding",
                    }
                    for node_id in handoff.road_graph.nodes
                ],
                "handoff_audit_object": None,
                "integrity": integrity,
                "road_topology": road_topology,
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    shutil.copyfile(handoff_path, output_dir / "handoff.yaml")
    shutil.copyfile(review_path, output_dir / "review-record.yaml")
    return summary

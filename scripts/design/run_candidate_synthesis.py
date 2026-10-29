#!/usr/bin/env python3
"""Synthesise one M4c-3 design candidate and write its CAD/visual evidence.

The multi-candidate engine lives in ``src/dgcad_design/candidates.py``
(implemented in parallel by design-topology). This script is the stable CLI
around it:

    python scripts/design/run_candidate_synthesis.py \
        --candidate-id C1 --output-root docs/e2e/design-candidates-001

Expected interface (``dgcad_design.candidates``)::

    build_candidate(
        candidate_id: str,
        *,
        case_dir: Path,
        basis_path: Path,
        profile_path: Path,
    ) -> CandidateModels

where ``CandidateModels`` exposes:

    building_layout : BuildingLayout
    road_layout     : RoadLayout
    green_layout    : GreenLayout
    parking_layout  : ParkingLayout
    changes         : dict        # strategy / parameters actually applied
    metrics         : dict        # hard_pass, max_displacement_m, main_length_m,
                                  # road_building_overlap_m2_total, ...
    design_elements : optional tuple  # if present, an editable DXF is written
    scene           : optional SceneState  # alternative to design_elements

If the module is not available yet the script reports
``status: waiting_for_candidates_interface`` with the interface it expects and
(save for ``--dry-run``) exits non-zero. The skeleton is importable and
side-effect free, so the Lead can integrate it before the engine lands.

An editable DXF is produced when the model exposes ``design_elements`` or
``scene`` (then the normal Cad-IR -> DXF path is used); otherwise the summary
records ``dxf: pending_interface`` so the gap is explicit, never silent.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

DEFAULT_CASE = ROOT / "docs/e2e/sketch-001"
DEFAULT_BASIS = ROOT / "fixtures/design/design-basis-001.yaml"
DEFAULT_PROFILE = ROOT / "fixtures/design/design-profile-001.yaml"
DEFAULT_OUTPUT_ROOT = ROOT / "docs/e2e/design-candidates-001"

CANDIDATE_INTERFACE = {
    "module": "dgcad_design.candidates",
    "callable": "build_candidate(candidate_id, *, case_dir, basis_path, profile_path)",
    "returns": "CandidateModels",
    "required_attributes": [
        "building_layout", "road_layout", "green_layout", "parking_layout",
        "changes", "metrics",
    ],
    "optional_attributes": ["design_elements", "scene", "site_boundary", "focus_bbox"],
}


def _load_engine():
    try:
        from dgcad_design import candidates  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return None, f"{type(exc).__name__}: {exc}"
    if not hasattr(candidates, "build_candidate"):
        return None, "module dgcad_design.candidates has no build_candidate()"
    return candidates, None


def _write_json(path: Path, payload: object) -> None:
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def _render_plan_if_possible(models, candidate_dir: Path, title: str) -> dict:
    try:
        from dgcad_design.visuals import render_plan_svg  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"visuals import: {exc}"}
    try:
        artifact = render_plan_svg(
            models.building_layout,
            models.road_layout,
            green_layout=getattr(models, "green_layout", None),
            site_boundary=getattr(models, "site_boundary", None),
            focus_bbox=getattr(models, "focus_bbox", None),
            path=candidate_dir / "plan.svg",
            title=title,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}
    return {"status": "rendered", **artifact}


def _write_dxf(models, candidate_dir: Path, basis_path: Path,
               profile_path: Path, candidate_id: str) -> dict:
    elements = getattr(models, "design_elements", None)
    scene = getattr(models, "scene", None)
    if elements is None and scene is None:
        return {"status": "pending_interface",
                "reason": "models expose neither design_elements nor scene"}
    try:
        import yaml  # noqa: PLC0415
        from dgcad_design.basis import DesignBasis  # noqa: PLC0415
        from dgcad_design.project import build_design_cad_ir  # noqa: PLC0415
        from dgcad_design.scene import design_scene  # noqa: PLC0415
        from dgcad_cad import (  # noqa: PLC0415
            DeliveryProfile,
            compile_to_dxf,
            validate_cad_ir,
            validate_dxf,
        )
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"cad import: {exc}"}
    try:
        basis = DesignBasis.from_dict(
            yaml.safe_load(Path(basis_path).read_text(encoding="utf-8")))
        profile = DeliveryProfile.from_dict(
            yaml.safe_load(Path(profile_path).read_text(encoding="utf-8")))
        if scene is None:
            scene = design_scene(elements, basis,
                                 scene_id=f"scene-CANDIDATE-{candidate_id}")
        metrics = getattr(models, "metrics", {}) or {}
        cad_ir = build_design_cad_ir(scene, profile, basis, metrics)
        validation = validate_cad_ir(cad_ir, profile)
        dxf_path = candidate_dir / "design-proposal.dxf"
        compile_result = compile_to_dxf(cad_ir, profile, dxf_path)
        readback = validate_dxf(dxf_path, cad_ir, profile)
        return {
            "status": "written",
            "path": dxf_path.name,
            "entity_count": compile_result.entity_count,
            "audit_errors": compile_result.audit_errors,
            "audit_fixes": compile_result.audit_fixes,
            "readback_verdict": readback.verdict,
            "cad_ir_verdict": validation.verdict,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}


def _summary(models, candidate_id: str) -> dict:
    def count(name: str, attr: str) -> int | None:
        layout = getattr(models, name, None)
        if layout is None:
            return None
        return len(getattr(layout, attr, ()) or ())

    return {
        "candidate_id": candidate_id,
        "changes": getattr(models, "changes", {}) or {},
        "metrics": getattr(models, "metrics", {}) or {},
        "counts": {
            "buildings": count("building_layout", "buildings"),
            "roads": count("road_layout", "roads"),
            "greens": count("green_layout", "greens"),
            "entrances": count("parking_layout", "entrances"),
        },
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate-id", required=True,
                        help="candidate identifier, e.g. C1 (used for the directory)")
    parser.add_argument("--output-root", type=Path, default=DEFAULT_OUTPUT_ROOT)
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--basis", type=Path, default=DEFAULT_BASIS)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument("--dry-run", action="store_true",
                        help="validate the interface and print what would be written")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    engine, error = _load_engine()
    if engine is None:
        payload = {
            "status": "waiting_for_candidates_interface",
            "candidate_id": args.candidate_id,
            "missing": error,
            "expected_interface": CANDIDATE_INTERFACE,
            "note": "skeleton only; no candidate files were written",
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0 if args.dry_run else 2

    candidate_dir = Path(args.output_root) / args.candidate_id
    if args.dry_run:
        payload = {
            "status": "dry_run_ok",
            "candidate_id": args.candidate_id,
            "engine": "dgcad_design.candidates",
            "would_write": str(candidate_dir),
            "expected_interface": CANDIDATE_INTERFACE,
        }
        print(json.dumps(payload, indent=2, ensure_ascii=False))
        return 0

    try:
        models = engine.build_candidate(
            args.candidate_id,
            case_dir=Path(args.case_dir),
            basis_path=Path(args.basis),
            profile_path=Path(args.profile),
        )
    except Exception as exc:  # noqa: BLE001
        print(json.dumps({"status": "build_failed", "candidate_id": args.candidate_id,
                          "error": f"{type(exc).__name__}: {exc}"},
                         indent=2, ensure_ascii=False))
        return 3

    candidate_dir.mkdir(parents=True, exist_ok=True)
    payload = _summary(models, args.candidate_id)
    payload["plan_svg"] = _render_plan_if_possible(
        models, candidate_dir,
        f"Candidate {args.candidate_id} (schematic draft)")
    payload["dxf"] = _write_dxf(models, candidate_dir, Path(args.basis),
                                Path(args.profile), args.candidate_id)
    _write_json(candidate_dir / "candidate-summary.json", payload)
    if not args.quiet:
        print(json.dumps(payload, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

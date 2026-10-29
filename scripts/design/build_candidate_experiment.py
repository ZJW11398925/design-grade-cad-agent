"""M4c-3 candidate experiment: build, evaluate and publish the first
multi-candidate design decision evidence.

Reproducible path: python scripts/design/build_candidate_experiment.py
"""
from __future__ import annotations

import json
import sys
from pathlib import Path
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import yaml
from shapely.geometry import box

from dgcad_design.basis import DesignBasis
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.candidates import build_all_candidates
from dgcad_design.consistency import check_design
from dgcad_design.evaluation import (
    DEFAULT_PRIORITIES,
    basis_fingerprint as compute_basis_fingerprint,
    compare,
    evaluate_candidate,
)
from dgcad_design.green import build_green_layout
from dgcad_design.input import load_design_input
from dgcad_design.intent import build_design_intent
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout
from dgcad_design.visuals import (
    render_candidate_comparison_svg,
    render_plan_svg,
)

CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
OUT = ROOT / "docs" / "e2e" / "design-candidates-001"

ROAD_FIRST_PREFERENCES = [
    {"objective": "main_route_deviation_max_m", "direction": "minimize"},
    {"objective": "main_length_delta_abs_m", "direction": "minimize"},
    {"objective": "branch_access_route_deviation_max_m", "direction": "minimize"},
    {"objective": "access_terminal_max_delta_m", "direction": "minimize"},
    {"objective": "building_count_change", "direction": "minimize"},
    {"objective": "building_displacement_max_m", "direction": "minimize"},
    {"objective": "source_preservation_coverage", "direction": "maximize"},
    {"objective": "green_designed_ratio_delta", "direction": "maximize"},
]


def _write(path: Path, payload) -> None:
    if path.suffix in {".json", ".geojson"}:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        path.write_text(payload, encoding="utf-8")


def _main_length(models) -> float:
    return float(
        sum(
            road.centerline.length
            for road in models.road_layout.roads
            if road.class_name == "main"
        )
    )


def _overlap(models, basis) -> float:
    from dgcad_design.evaluation import _road_overlap_total

    return float(_road_overlap_total(models.building_layout, models.road_layout))


def main() -> int:
    basis = DesignBasis.from_dict(
        yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    )
    basis_fingerprint = compute_basis_fingerprint(basis)
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        rect,
    )

    # Reference = the raw source-aligned design (no main-road alignment), so the
    # change metrics measure each candidate against the original sketch trend.
    reference_road = build_road_layout(
        design_input,
        basis,
        intent,
        building_layout,
        alignment_mode="none",
    )
    reference_green = build_green_layout(
        design_input,
        building_layout,
        reference_road,
        basis,
        box(*intent.focus_bbox),
    )
    reference_parking = build_parking_layout(
        design_input, intent, reference_road, basis
    )
    reference = SimpleNamespace(
        building_layout=building_layout,
        road_layout=reference_road,
        green_layout=reference_green,
        parking_layout=reference_parking,
    )

    candidates = build_all_candidates(CASE, basis)
    evaluations = []
    for candidate in candidates.values():
        evaluations.append(
            evaluate_candidate(
                candidate,
                basis,
                reference=reference,
                intent=intent,
                site_boundary=design_input.site_boundary,
                design_input=design_input,
            )
        )
    default_decision = compare(evaluations, DEFAULT_PRIORITIES)
    road_first_decision = compare(evaluations, ROAD_FIRST_PREFERENCES)

    OUT.mkdir(parents=True, exist_ok=True)
    _write(
        OUT / "candidates.json",
        {
            "schema_id": "dgcad.design-candidates.v0.2",
            "source_case": str(CASE.relative_to(ROOT)).replace("\\", "/"),
            "reference": (
                "boundary-safe, dead-end-resolved reference (source alignment, "
                "alignment_mode='none'; boundary repair and dead-end resolution "
                "still apply), not the already-aligned M4c-2 base"
            ),
            "basis": {
                "parent_basis_id": candidates["A"].spec.parent_basis_id,
                "basis_fingerprint": candidates["A"].spec.basis_fingerprint,
            },
            "candidates": [
                {
                    "candidate_id": candidate.spec.candidate_id,
                    "strategy": candidate.spec.strategy,
                    "description": candidate.spec.description,
                    "parent_basis_id": candidate.spec.parent_basis_id,
                    "basis_fingerprint": candidate.spec.basis_fingerprint,
                    "changes": candidate.changes,
                    "main_length_m": _main_length(candidate),
                    "total_road_building_overlap_m2": _overlap(candidate, basis),
                }
                for candidate in candidates.values()
            ],
        },
    )

    plan_results = {}
    comparison_inputs = []
    for candidate, evaluation in zip(candidates.values(), evaluations):
        candidate_id = candidate.spec.candidate_id
        candidate_dir = OUT / candidate_id
        candidate_dir.mkdir(parents=True, exist_ok=True)
        plan_results[candidate_id] = render_plan_svg(
            candidate.building_layout,
            candidate.road_layout,
            candidate.green_layout,
            path=candidate_dir / "plan.svg",
            title=f"Candidate {candidate_id} - {candidate.spec.strategy}",
            site_boundary=design_input.site_boundary,
            focus_bbox=intent.focus_bbox,
        )
        eval_payload = evaluation.to_dict()
        candidate_consistency = check_design(
            design_input,
            basis,
            intent,
            candidate.building_layout,
            candidate.road_layout,
            candidate.green_layout,
            candidate.parking_layout,
            candidate.road_access,
        )
        _write(
            candidate_dir / "design-consistency.json",
            candidate_consistency.to_dict(),
        )
        from dgcad_design.project import _design_roads_geojson

        _write(
            candidate_dir / "design-roads.geojson",
            _design_roads_geojson(
                candidate.road_layout, candidate.road_access
            ),
        )
        summary_payload = {
            "schema_id": "dgcad.design-candidate-summary.v0.2",
            "candidate_id": candidate_id,
            "strategy": candidate.spec.strategy,
            "description": candidate.spec.description,
            "changes": candidate.changes,
            "main_length_m": _main_length(candidate),
            "evaluation": eval_payload,
        }
        _write(candidate_dir / "candidate-summary.json", summary_payload)
        _write(candidate_dir / "design-summary.json", summary_payload)
        buildings = []
        for building in candidate.building_layout.buildings:
            footprint = getattr(building, "footprint", None)
            buildings.append(
                {
                    "building_id": getattr(building, "building_id", None),
                    "unit_count": getattr(building, "unit_count", None),
                    "floors": getattr(building, "floors", None),
                    "footprint": (
                        None
                        if footprint is None
                        else [
                            [float(x), float(y)]
                            for x, y in footprint.exterior.coords
                        ]
                    ),
                }
            )
        _write(
            candidate_dir / "design-buildings.json",
            {
                "schema_id": "dgcad.design-candidate-buildings.v0.1",
                "candidate_id": candidate_id,
                "building_count": len(buildings),
                "unit_count": sum(
                    int(item["unit_count"] or 0) for item in buildings
                ),
                "buildings": buildings,
                "building_shifts": candidate.changes.get(
                    "building_shifts", []
                ),
            },
        )
        soft = eval_payload.get("soft") or {}
        objectives = soft.get("objectives") or {}
        hard_details = eval_payload.get("hard_details") or {}
        overlap_details = (hard_details.get("overlap_ok") or {})
        route_deviation = max(
            float(objectives.get("main_route_deviation_max_m") or 0.0),
            float(objectives.get("branch_access_route_deviation_max_m") or 0.0),
        )
        g08 = next(
            (
                float(item["delta_m"])
                for item in candidate.changes["geometry_change"][
                    "group_terminal_changes"
                ]
                if item["group_id"] == "G-08"
            ),
            0.0,
        )
        comparison_inputs.append(
            SimpleNamespace(
                candidate_id=candidate_id,
                strategy=candidate.spec.strategy,
                models=candidate,
                metrics={
                    "hard_pass": eval_payload.get("hard_pass"),
                    "strategy": candidate.spec.strategy,
                    "max_displacement_m": route_deviation,
                    "main_length_m": _main_length(candidate),
                    "road_building_overlap_m2_total": overlap_details.get(
                        "total_road_building_overlap_m2"
                    ),
                    "detail_lines": [
                        f"main dev: {float(objectives.get('main_route_deviation_max_m') or 0.0):.2f} m",
                        f"branch/access dev: {float(objectives.get('branch_access_route_deviation_max_m') or 0.0):.2f} m",
                        f"G-08 terminal: {g08:.2f} m",
                        "buildings moved: "
                        f"{float(objectives.get('building_displaced_count') or 0.0):.0f}, "
                        f"max disp {float(objectives.get('building_displacement_max_m') or 0.0):.2f} m",
                    ],
                },
            )
        )
    comparison = render_candidate_comparison_svg(
        comparison_inputs,
        path=OUT / "comparison.svg",
        title="M4c-3 candidate comparison (MAIN-19 conflict)",
    )

    _write(
        OUT / "evaluation.json",
        {
            "schema_id": "dgcad.design-candidates-evaluation.v0.2",
            "reference": (
                "boundary-safe, dead-end-resolved reference (source alignment, "
            "alignment_mode='none'; boundary repair and dead-end resolution "
            "still apply), not the already-aligned M4c-2 base"
            ),
            "evaluations": [evaluation.to_dict() for evaluation in evaluations],
            "decisions": {
                "default_preferences": default_decision,
                "road_first_preferences": road_first_decision,
            },
            "preferences_used": {
                "default": DEFAULT_PRIORITIES,
                "road_first": ROAD_FIRST_PREFERENCES,
            },
            "note": (
                "hard gates and the ten single-unit objectives are recomputed "
                "from geometry, not read from the candidate; auxiliary metrics "
                "are reported but never enter the Pareto front; no single "
                "black-box score is produced"
            ),
        },
    )
    _write(
        OUT / "comparison.json",
        {
            "comparison": comparison,
            "plans": plan_results,
        },
    )

    rows = []

    def _fmt(value, digits=2):
        return "n/a" if value is None else f"{float(value):.{digits}f}"

    for evaluation in evaluations:
        payload = evaluation.to_dict()
        soft = payload.get("soft") or {}
        objectives = soft.get("objectives") or {}
        over = (payload.get("hard_details") or {}).get("overlap_ok") or {}
        bound = (payload.get("hard_details") or {}).get("boundary_ok") or {}
        rows.append(
            "| {cid} | {hard} | {overlap:.3f} | {boundary:.3f} | {main_dev} | "
            "{branch_dev} | {terminal} | {bld_count} | {bld_moved} | {bld_disp} | "
            "{main_len} | {source_cov} | {source_dist} | {source_heading} | {green} |".format(
                cid=payload["candidate_id"],
                hard="pass" if payload["hard_pass"] else "FAIL",
                overlap=float(over.get("total_road_building_overlap_m2") or 0.0),
                boundary=float(bound.get("boundary_margin_m") or 0.0),
                main_dev=_fmt(objectives.get("main_route_deviation_max_m")),
                branch_dev=_fmt(
                    objectives.get("branch_access_route_deviation_max_m")
                ),
                terminal=_fmt(objectives.get("access_terminal_max_delta_m")),
                bld_count=_fmt(objectives.get("building_count_change"), 0),
                bld_moved=_fmt(objectives.get("building_displaced_count"), 0),
                bld_disp=_fmt(objectives.get("building_displacement_max_m")),
                main_len=_fmt(objectives.get("main_length_delta_abs_m")),
                source_cov=(
                    "n/a"
                    if objectives.get("source_preservation_coverage") is None
                    else f"{float(objectives['source_preservation_coverage']):.3f}"
                ),
                source_dist=_fmt(
                    objectives.get("source_preservation_distance_m")
                ),
                source_heading=_fmt(
                    objectives.get("source_preservation_heading_deg")
                ),
                green=_fmt(objectives.get("green_designed_ratio_delta"), 4),
            )
        )

    default_rec = default_decision["recommendation"]
    road_first_rec = road_first_decision["recommendation"]
    readme = f"""# M4c-3a — candidate comparison with explicit single-unit objectives

Generated by `python scripts/design/build_candidate_experiment.py` from the same
source, design basis and evidence. Four candidates address the **MAIN-19 /
SK-BLD-0006 / SK-BLD-0029** conflict; the M4c-2 66.235 m diversion is only one
candidate (B1), not the predetermined answer.

Reference for change metrics: **boundary-safe, dead-end-resolved reference**
(source alignment, `alignment_mode='none'`; boundary repair and dead-end
resolution still apply), not the already-aligned M4c-2 base. Hard gates and the
objectives are recomputed by `src/dgcad_design/evaluation.py` from geometry;
candidate self-reports are ignored. Every candidate is bound to the same
design basis by `parent_basis_id` + `basis_fingerprint`
(`{basis_fingerprint}`).

## Candidates

| id | strategy | description |
|---|---|---|
{chr(10).join(
    f"| {c.spec.candidate_id} | {c.spec.strategy} | {c.spec.description} |"
    for c in candidates.values()
)}

## Hard gates and objectives (single-unit, no composite score)

| id | hard | overlap m2 | boundary margin m | main deviation m | branch/access deviation m | terminal max delta m | building count change | buildings moved | building disp max m | main length delta abs m | source coverage | source distance m | source heading deg | designed green delta |
|---|---|---|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

Auxiliary diagnostics (**never** in the Pareto front or preference comparison):
green open-space ratio delta, unbuilt ratio delta, GFA/FAR invariants, added
vertices, group-integrity detail. The `group_integrity` evidence also records
`declared_relations_preserved` and per-group terminal shifts; per-group data is
in `changes["geometry_change"]["group_terminal_changes"]`.

Notable measured effects (from `geometry_change`): A moves SK-BLD-0006 by
3.172 m and re-routes its **BR-G-08** access branch by **2.826 m** (G-08
terminal shifts 2.826 m); C moves SK-BLD-0006 only 1.50 m but re-routes
**BR-G-08 by 76.700 m** and shifts the G-08 terminal by **75.315 m**; B1/B2
keep all buildings but re-route MAIN-19 (66.235 / 71.772 m), and the attached
BR-G-09 follows (7.352 / 13.645 m). C is therefore not a "small local change"
and must be read through those numbers, not through its 1.5 m building shift.

## Decision

- **Default preferences** (building_count_change → building_displaced_count →
  building_displacement_max_m → access_terminal_max_delta_m →
  main_route_deviation_max_m →
  main_length_delta_abs_m → source_preservation_coverage →
  green_designed_ratio_delta): **{default_rec}** recommended.
- **Road-first preferences** (main_route_deviation_max_m →
  main_length_delta_abs_m → branch_access_route_deviation_max_m →
  access_terminal_max_delta_m → building_count_change →
  building_displacement_max_m → source_preservation_coverage →
  green_designed_ratio_delta): **{road_first_rec}** recommended.

Pareto front (default): {", ".join(default_decision["pareto_front"])}.
Every rejection reason (default): {json.dumps(default_decision["reasons"], ensure_ascii=False)}.
Road-first reasons: {json.dumps(road_first_decision["reasons"], ensure_ascii=False)}.

There is **no single opaque score**. Each objective compares one quantity with
one unit; auxiliary metrics are reported but excluded from the Pareto front and
from the preference comparison. Historical boundary facts are archived in
`HISTORICAL_BOUNDARY_ARCHIVE` (MAIN-19 66.235 m diversion; MAIN-08/16/18
source-corridor repairs of 341.6908 / 2.4178 / 8.2909 m²); the current B1
candidate is boundary-compliant (margin 0.6735 m) and is judged only on its own
geometry.

## Reproduce

1. Base design evidence: `python scripts/design/run_design_synthesis_001.py`
2. Candidate experiment: `python scripts/design/build_candidate_experiment.py`
3. Visuals: `python scripts/design/render_visuals.py --output-dir docs/e2e/design-synthesis-001`
4. CAD path (per-candidate DXF is **not committed**; reproducible from the same
   source/basis): `python scripts/design/run_candidate_synthesis.py --candidate-id <id>`.

Per-candidate evidence files: `candidate-summary.json`, `design-summary.json`,
`design-consistency.json`, `design-roads.geojson`, `design-buildings.json`,
`plan.svg`.

## What this does and does not prove

- **Proves**: under the same constraints, the Agent can produce four distinct,
  hard-valid design responses to one real conflict, and an independent
  evaluator can compare them on explicit single-unit objectives, report the
  Pareto front and both preference-order decisions, and expose the hidden
  branch/access effects.
- **Does not prove**: that the preferred candidate is a professional design, that
  the candidate set is exhaustive, or that the objectives are complete. The
  source-segment mapping still falls back to the nearest source edges when no
  segment is covered, so source coverage is initial evidence, not proof of
  intent preservation. The full site, garage geometry, road profiles, daylight
  and code compliance remain out of scope.
"""
    (OUT / "README.md").write_text(readme, encoding="utf-8", newline="\n")
    print(
        json.dumps(
            {
                "out": str(OUT),
                "default_recommendation": default_rec,
                "road_first_recommendation": road_first_rec,
                "pareto_default": default_decision["pareto_front"],
                "comparison_svg": comparison,
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

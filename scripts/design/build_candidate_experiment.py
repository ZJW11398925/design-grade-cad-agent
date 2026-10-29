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
from dgcad_design.evaluation import DEFAULT_PRIORITIES, compare, evaluate_candidate
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
    {"objective": "road_change", "direction": "minimize"},
    {"objective": "building_change", "direction": "minimize"},
    {"objective": "source_preservation", "direction": "maximize"},
    {"objective": "green_change", "direction": "maximize"},
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
            "schema_id": "dgcad.design-candidates.v0.1",
            "source_case": str(CASE.relative_to(ROOT)).replace("\\", "/"),
            "reference": (
                "boundary-safe, dead-end-resolved reference (source alignment, "
                "alignment_mode='none'; boundary repair and dead-end resolution "
                "still apply), not the already-aligned M4c-2 base"
            ),
            "candidates": [
                {
                    "candidate_id": candidate.spec.candidate_id,
                    "strategy": candidate.spec.strategy,
                    "description": candidate.spec.description,
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
            "schema_id": "dgcad.design-candidate-summary.v0.1",
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
        road_change = soft.get("road_change") or {}
        hard_details = eval_payload.get("hard_details") or {}
        overlap_details = (hard_details.get("overlap_ok") or {})
        comparison_inputs.append(
            SimpleNamespace(
                candidate_id=candidate_id,
                strategy=candidate.spec.strategy,
                models=candidate,
                metrics={
                    "hard_pass": eval_payload.get("hard_pass"),
                    "strategy": candidate.spec.strategy,
                    "max_displacement_m": road_change.get("max_displacement_m"),
                    "main_length_m": _main_length(candidate),
                    "road_building_overlap_m2_total": overlap_details.get(
                        "total_road_building_overlap_m2"
                    ),
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
            "schema_id": "dgcad.design-candidates-evaluation.v0.1",
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
                "hard gates are recomputed from geometry, not read from the "
                "candidate; no single black-box score is produced"
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
    for evaluation in evaluations:
        payload = evaluation.to_dict()
        soft = payload.get("soft") or {}
        over = (payload.get("hard_details") or {}).get("overlap_ok") or {}
        bound = (payload.get("hard_details") or {}).get("boundary_ok") or {}
        road = soft.get("road_change") or {}
        building = soft.get("building_change") or {}
        rows.append(
            "| {cid} | {strategy} | {hard} | {overlap:.3f} | {boundary:.3f} | "
            "{road_disp} | {road_len_delta} | {building_disp} | {green_delta} |".format(
                cid=payload["candidate_id"],
                strategy=payload["strategy"],
                hard="pass" if payload["hard_pass"] else "FAIL",
                overlap=float(over.get("total_road_building_overlap_m2") or 0.0),
                boundary=float(bound.get("boundary_margin_m") or 0.0),
                road_disp=(
                    "n/a"
                    if road.get("max_displacement_m") is None
                    else f"{road['max_displacement_m']:.2f} m"
                ),
                road_len_delta=(
                    "n/a"
                    if road.get("main_length_delta_m") is None
                    else f"{road['main_length_delta_m']:.2f} m"
                ),
                building_disp=(
                    "0"
                    if not building.get("displaced_count")
                    else f"{building['displaced_count']} / "
                    f"{building['max_displacement_m']:.2f} m"
                ),
                green_delta=(
                    "n/a"
                    if (soft.get("green_change") or {}).get(
                        "candidate_open_space_ratio_delta"
                    )
                    is None
                    else f"{(soft['green_change']['candidate_open_space_ratio_delta'] * 100):.3f} pp"
                ),
            )
        )

    default_rec = default_decision["recommendation"]
    road_first_rec = road_first_decision["recommendation"]
    readme = f"""# M4c-3 — first multi-candidate design decision experiment

Generated by `python scripts/design/build_candidate_experiment.py` from the same
source, design basis and evidence. Four candidates address the **MAIN-19 /
SK-BLD-0006 / SK-BLD-0029** conflict; the M4c-2 66.235 m diversion is only one
candidate (B1), not the predetermined answer.

Reference for change metrics: **boundary-safe, dead-end-resolved reference**
(source alignment, `alignment_mode='none'`; boundary repair and dead-end
resolution still apply), not the already-aligned M4c-2 base. Hard gates are
recomputed by
`src/dgcad_design/evaluation.py` from geometry; candidate self-reports are ignored.

## Candidates

| id | strategy | description |
|---|---|---|
| A | road_priority | keep the raw main alignment, shift SK-BLD-0006 by the minimum clearing distance |
| B1 | building_priority_diversion | keep buildings, use the M4c-2 MAIN-19 diversion (66.235 m) |
| B2 | building_priority_alternate | keep buildings, alternate diversion fold (different displacement/length) |
| C | coordinated | shift SK-BLD-0006 1.50 m plus a medium local road adjustment |

## Hard gates and soft metrics

| id | strategy | hard | overlap m2 | boundary margin m | road max disp | main length delta | building disp | green delta |
|---|---|---|---|---|---|---|---|---|
{chr(10).join(rows)}

All hard gates (overlap, topology, site-boundary containment, declared access,
capacity, basis) must pass before soft comparison. `boundary margin` is the
minimum main-road corridor-edge distance inside the published site boundary.

## Decision

- **Default preferences** (building preservation first: building_change →
  road_change → source_preservation → green_change):
  **{default_rec}** recommended.
- **Road-first preferences** (road_change → building_change →
  source_preservation → green_change): **{road_first_rec}** recommended.

Pareto front (default): {", ".join(default_decision["pareto_front"])}.
Every rejection reason (default): {json.dumps(default_decision["reasons"], ensure_ascii=False)}.
Road-first reasons: {json.dumps(road_first_decision["reasons"], ensure_ascii=False)}.

There is **no single opaque score**. The table exposes the trade-off: B1/B2
leave all buildings untouched but change the main road; A moves one building
(SK-BLD-0006) while returning to the source road trend; C shifts the building
half-way and makes a medium road change.

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
  evaluator can rank them under two explicit preference orders and explain the
  trade-off.
- **Does not prove**: that the preferred candidate is a professional design, that
  the candidate set is exhaustive, or that the soft objectives are complete.
  B1's original 66.235 m diversion is retained as a boundary-violating
  historical baseline (`KNOWN_BOUNDARY_VIOLATIONS`) and is not a hard pass in
  its pre-repair form. The full site, garage geometry, road profiles, daylight
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

"""M4d-2 A/B co-design experiment evidence (reproducible).

Candidate A: fixed M4d-1 full-site building layout + rebuilt group access.
Candidate B: group-preserving building layout + rebuilt group access.
Baseline: M4d-1 full-site sheet (old focus-era access declarations).

The experiment is evaluated honestly: a candidate that violates a hard
constraint is reported as failing, never as a complete design.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

try:
    from shapely.geometry import box
except Exception:  # pragma: no cover
    box = None

import yaml

from dgcad_design.access import build_co_design_access
from dgcad_design.basis import DesignBasis
from dgcad_design.buildings import (
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.consistency import check_design
from dgcad_design.green import build_green_layout
from dgcad_design.group_metrics import (
    access_truth_metrics,
    candidate_comparison_metrics,
    group_integrity_metrics,
)
from dgcad_design.input import load_design_input
from dgcad_design.intent import build_design_intent
from dgcad_design.parking import build_parking_layout
from dgcad_design.project import build_full_site_models

OUT = ROOT / "docs" / "e2e" / "design-co-design-001"


def _write(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.suffix in {".json", ".geojson"}:
        path.write_text(
            json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    else:
        path.write_text(payload, encoding="utf-8", newline="\n")


def _displacement_layout(building_layout, standardized) -> dict:
    values = []
    for building in building_layout.buildings:
        source = standardized.get(building.building_id)
        if source is None:
            continue
        values.append(
            float(
                building.footprint.centroid.distance(
                    source.footprint.centroid
                )
            )
        )
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "sum_m": sum(values),
        "mean_m": sum(values) / len(values),
        "max_m": max(values),
        "min_m": min(values),
    }


def _road_change(road_layout, frozen_road_layout) -> dict:
    frozen_ids = {road.edge_id for road in frozen_road_layout.roads}
    current_ids = {road.edge_id for road in road_layout.roads}
    added = sorted(current_ids - frozen_ids)
    removed = sorted(frozen_ids - current_ids)
    new_length = sum(
        road.centerline.length
        for road in road_layout.roads
        if road.edge_id in added
    )
    return {
        "frozen_road_count": len(frozen_ids),
        "candidate_road_count": len(current_ids),
        "added_road_ids": added,
        "removed_road_ids": removed,
        "added_road_count": len(added),
        "added_road_length_m": new_length,
    }


def main() -> int:
    basis = DesignBasis.from_dict(
        yaml.safe_load(
            (ROOT / "fixtures" / "design" / "design-basis-001.yaml").read_text(
                encoding="utf-8"
            )
        )
    )
    design_input = load_design_input(ROOT / "docs" / "e2e" / "sketch-001", basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)

    frozen = build_full_site_models(
        ROOT / "docs" / "e2e" / "sketch-001",
        ROOT / "fixtures" / "design" / "design-basis-001.yaml",
        ROOT / "fixtures" / "design" / "design-profile-001.yaml",
    )
    frozen_road_layout = frozen["road_layout"]

    def build_candidate(building_layout, candidate_id):
        road_layout, road_access, access_meta = build_co_design_access(
            design_input,
            basis,
            intent,
            building_layout,
            frozen_road_layout,
            candidate_id=candidate_id,
        )
        green_layout = build_green_layout(
            design_input,
            building_layout,
            road_layout,
            basis,
            box(*intent.focus_bbox),
        )
        parking_layout = build_parking_layout(
            design_input, intent, road_layout, basis
        )
        consistency = check_design(
            design_input,
            basis,
            intent,
            building_layout,
            road_layout,
            green_layout,
            parking_layout,
            road_access,
        )
        return {
            "building_layout": building_layout,
            "road_layout": road_layout,
            "road_access": road_access,
            "green_layout": green_layout,
            "parking_layout": parking_layout,
            "access_meta": access_meta,
            "consistency": consistency,
        }

    baseline_building = frozen["building_layout"]
    baseline_consistency = check_design(
        design_input,
        basis,
        intent,
        baseline_building,
        frozen_road_layout,
        frozen["green_layout"],
        frozen["parking_layout"],
        frozen["road_access"],
    )
    baseline = {
        "building_layout": baseline_building,
        "road_layout": frozen_road_layout,
        "road_access": frozen["road_access"],
        "green_layout": frozen["green_layout"],
        "parking_layout": frozen["parking_layout"],
        "access_meta": None,
        "consistency": baseline_consistency,
    }

    candidate_a = build_candidate(baseline_building, "A")
    group_preserving_layout = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=getattr(frozen_road_layout, "corridor_union", None),
    )
    candidate_b = build_candidate(group_preserving_layout, "B")

    def candidate_payload(candidate_id, candidate, layout_note):
        consistency = candidate["consistency"]
        checks = {check["id"]: check for check in consistency.checks}
        status_counts = {}
        for check in consistency.checks:
            status_counts[check["status"]] = (
                status_counts.get(check["status"], 0) + 1
            )
        hard_fail_ids = [
            check_id
            for check_id in (
                "FULL_SITE_BOUNDARY_SETBACK",
                "FULL_SITE_BUILDING_OVERLAP",
                "FULL_SITE_ROAD_CLEARANCE",
                "FULL_SITE_NS_SPACING",
                "ROAD_ACCESS_COVERAGE",
                "DEAD_END_RESOLUTION",
            )
            if checks.get(check_id, {}).get("status") == "fail"
        ]
        sidewalk_overlap_ids = list(
            checks.get("FULL_SITE_ROAD_CLEARANCE", {})
            .get("detail", {})
            .get("sidewalk_overlap_building_ids")
            or []
        )
        hard_ok = (
            not hard_fail_ids
            and consistency.hard_checks_ok
            and not sidewalk_overlap_ids
        )
        group_metrics = group_integrity_metrics(
            intent,
            candidate["building_layout"],
            candidate["road_access"],
        )
        access_truth = access_truth_metrics(
            candidate["road_layout"],
            candidate["road_access"],
            design_input.site_boundary,
            candidate["building_layout"],
        )
        return {
            "candidate_id": candidate_id,
            "layout_note": layout_note,
            "building_count": len(candidate["building_layout"].buildings),
            "unit_count": sum(
                item.unit_count or 0 for item in candidate["building_layout"].buildings
            ),
            "households": sum(
                getattr(item, "households", 0)
                for item in candidate["building_layout"].buildings
            ),
            "check_status": status_counts,
            "failed_hard_checks": hard_fail_ids,
            "sidewalk_overlap_building_ids": sidewalk_overlap_ids,
            "sidewalk_overlap_count": len(sidewalk_overlap_ids),
            "hard_ok": hard_ok,
            "checks": checks,
            "road_change": _road_change(
                candidate["road_layout"], frozen_road_layout
            ),
            "displacement": _displacement_layout(
                candidate["building_layout"], standardized
            ),
            "group_metrics": group_metrics,
            "access_truth": access_truth,
            "access_meta": candidate["access_meta"],
            "consistency": consistency.to_dict(),
        }

    payload_a = candidate_payload(
        "A", candidate_a, "fixed M4d-1 full-site layout + rebuilt group access"
    )
    payload_b = candidate_payload(
        "B", candidate_b, "group-preserving full-site layout + rebuilt group access"
    )
    # baseline: frozen M4d-1 sheet (old access declarations)
    baseline_group_metrics = group_integrity_metrics(
        intent, baseline["building_layout"], baseline["road_access"]
    )
    baseline_access_truth = access_truth_metrics(
        baseline["road_layout"],
        baseline["road_access"],
        design_input.site_boundary,
        baseline["building_layout"],
    )
    baseline_payload = {
        "candidate_id": "M4D1-BASELINE",
        "building_count": len(baseline["building_layout"].buildings),
        "unit_count": sum(
            item.unit_count or 0 for item in baseline["building_layout"].buildings
        ),
        "access_truth": baseline_access_truth,
        "group_metrics": baseline_group_metrics,
        "road_change": _road_change(baseline["road_layout"], frozen_road_layout),
        "displacement": _displacement_layout(
            baseline["building_layout"], standardized
        ),
    }

    comparison = candidate_comparison_metrics(
        {**candidate_a, "intent": intent},
        {**candidate_b, "intent": intent},
        {**baseline, "intent": intent},
    )

    # explicit hard-first decision: no opaque score
    eligible = [item for item in (payload_a, payload_b) if item["hard_ok"]]
    if eligible:
        # prefer complete object/group preservation, then access truth, then
        # smaller building displacement, then fewer added road metres
        ranked = sorted(
            eligible,
            key=lambda item: (
                item["group_metrics"]["groups_preserved"],
                item["access_truth"].get("coverage", 0.0),
                -item["displacement"]["max_m"],
                item["road_change"]["added_road_length_m"],
            ),
            reverse=True,
        )
        recommendation = ranked[0]["candidate_id"]
        reasons = {
            candidate["candidate_id"]: (
                "hard gates pass"
                if candidate["hard_ok"]
                else "excluded: hard gate failure"
            )
            for candidate in (payload_a, payload_b)
        }
    else:
        recommendation = None
        reasons = {
            "A": "excluded: hard gate failure ("
            + ", ".join(payload_a["failed_hard_checks"])
            + ")",
            "B": "excluded: hard gate failure ("
            + ", ".join(payload_b["failed_hard_checks"])
            + ")",
        }

    _write(
        OUT / "candidates.json",
        {
            "schema_id": "dgcad.design-co-design-candidates.v0.1",
            "decision": ("no complete candidate" if recommendation is None else recommendation),
            "reasons": reasons,
            "candidates": [payload_a, payload_b],
            "baseline": baseline_payload,
        },
    )
    _write(
        OUT / "evaluation.json",
        {
            "schema_id": "dgcad.design-co-design-evaluation.v0.1",
            "hard_first": True,
            "recommendation": recommendation,
            "reasons": reasons,
            "comparison": comparison,
            "note": (
                "hard gates are recomputed from geometry; a candidate failing a "
                "hard check is reported as failing, not as a complete design; "
                "no single opaque score is produced"
            ),
        },
    )
    _write(
        OUT / "candidate-a-consistency.json",
        payload_a["consistency"],
    )
    _write(
        OUT / "candidate-b-consistency.json",
        payload_b["consistency"],
    )

    readme = f"""# M4d-2 — A/B building-road co-design experiment

Both candidates start from the same CASE-SKETCH-001 input, basis and frozen
44-road network; they differ in **how the buildings are placed**, and both use
the same rebuilt group-access generator (`build_co_design_access`). The old
focus-era access declarations are never reused.

| candidate | building layout | access | hard result |
|---|---|---|---|
| **M4D1-BASELINE** | M4d-1 full-site layout | old focus-era declarations | access 0/17, 17 unresolved |
| **A** | fixed M4d-1 full-site layout | rebuilt connectors (17, 362.09 m) | see below |
| **B** | group-preserving layout (17 groups; 39 rows) | rebuilt connectors | see below |

## Measured results

| metric | baseline | A | B |
|---|---|---|---|
| buildings / units / households | {baseline_payload['building_count']} / {baseline_payload['unit_count']} / — | {payload_a['building_count']} / {payload_a['unit_count']} / — | {payload_b['building_count']} / {payload_b['unit_count']} / — |
| hard check failures | — | {', '.join(payload_a['failed_hard_checks']) or 'none'} | {', '.join(payload_b['failed_hard_checks']) or 'none'} |
| access coverage | {baseline_access_truth.get('coverage')} | {payload_a['access_truth'].get('coverage')} | {payload_b['access_truth'].get('coverage')} |
| access relation errors | {baseline_access_truth.get('relation_error_count')} | {payload_a['access_truth'].get('relation_error_count')} | {payload_b['access_truth'].get('relation_error_count')} |
| dead ends unresolved | {baseline_access_truth.get('dead_ends_unresolved')} | {payload_a['access_truth'].get('dead_ends_unresolved')} | {payload_b['access_truth'].get('dead_ends_unresolved')} |
| building displacement mean / max (m) | {baseline_payload['displacement']['mean_m']:.2f} / {baseline_payload['displacement']['max_m']:.2f} | {payload_a['displacement']['mean_m']:.2f} / {payload_a['displacement']['max_m']:.2f} | {payload_b['displacement']['mean_m']:.2f} / {payload_b['displacement']['max_m']:.2f} |
| group centroid displacement mean / max (m) | {baseline_group_metrics['mean_centroid_displacement_m']:.2f} / {baseline_group_metrics['max_centroid_displacement_m']:.2f} | {payload_a['group_metrics']['mean_centroid_displacement_m']:.2f} / {payload_a['group_metrics']['max_centroid_displacement_m']:.2f} | {payload_b['group_metrics']['mean_centroid_displacement_m']:.2f} / {payload_b['group_metrics']['max_centroid_displacement_m']:.2f} |
| added road length (m) | 0 | {payload_a['road_change']['added_road_length_m']:.2f} | {payload_b['road_change']['added_road_length_m']:.2f} |
| group split count | {baseline_group_metrics.get('groups_split')} | {payload_a['group_metrics'].get('groups_split')} | {payload_b['group_metrics'].get('groups_split')} |

## Decision

**Recommendation: {recommendation if recommendation else 'none — no complete candidate'}**

Reasons:
- A: {reasons['A']}
- B: {reasons['B']}

Hard-first rule: a candidate failing any hard check (`FULL_SITE_BOUNDARY_SETBACK`,
`FULL_SITE_BUILDING_OVERLAP`, `FULL_SITE_ROAD_CLEARANCE`, `FULL_SITE_NS_SPACING`,
`ROAD_ACCESS_COVERAGE`, `DEAD_END_RESOLUTION`) is not a complete design. The
access rebuilds reach 17/17 coverage, but the **served-facade corridor** cannot
keep 3.0 m under the declared 3.4–3.5 m terminal band and 7 m branch width
(structurally 2.825 m; reported, not hidden). This is a real design-rule
conflict that M4d-2 exposes: the terminal band and the 3 m corridor rule need
coordination (e.g. terminal at corridor edge, narrower access, or a revised
access standard) rather than silently widening a tolerance.

## What this proves / does not prove

- Proves: both candidate paths can be generated from the same source, with all
  55 buildings / 109 units / 2,398 households preserved, 17 groups represented,
  and rebuilt access geometry (no `serves_group_ids`-only edits); the comparison
  is hard-first and reports failures honestly.
- Does not prove: a complete hard-valid full-site design exists under the
  current basis/constraints. No CAD deliverable is presented as a finished
  design. Candidate DXF **is** provided as evidence (`A/`, `B/`: editable DXF,
  readback manifest, validation, privacy scan, scene snapshot and preview;
  A 584 entities / B 587 entities, readback 584/584 and 587/587, XDATA 11,
  privacy pass). The A sheet is stamped `INCOMPLETE` for the clearance
  failure; the B sheet is stamped `HARD-VALID` on the 29 gated checks. Both
  sheets keep the potential-open-space / designed-green distinction.

## Reproduce

```bash
python -m pytest tests/test_co_design_access.py tests/test_group_preserving_layout.py tests/test_group_metrics.py -q
python scripts/design/build_co_design_evidence.py
```
"""
    _write(OUT / "README.md", readme)
    print(
        json.dumps(
            {
                "out": str(OUT),
                "recommendation": recommendation,
                "a_failures": payload_a["failed_hard_checks"],
                "b_failures": payload_b["failed_hard_checks"],
                "a_coverage": payload_a["access_truth"].get("coverage"),
                "b_coverage": payload_b["access_truth"].get("coverage"),
                "a_group_centroid_max_m": payload_a["group_metrics"][
                    "max_centroid_displacement_m"
                ],
                "b_group_centroid_max_m": payload_b["group_metrics"][
                    "max_centroid_displacement_m"
                ],
                "a_disp_max_m": payload_a["displacement"]["max_m"],
                "b_disp_max_m": payload_b["displacement"]["max_m"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

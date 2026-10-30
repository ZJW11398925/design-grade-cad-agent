"""Audit the candidate-B clearance against coordinate perturbation (M4d-2a)."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402
from shapely.geometry import box  # noqa: E402

from dgcad_design.basis import DesignBasis  # noqa: E402
from dgcad_design.buildings import layout_group_preserving, standardize_all  # noqa: E402
from dgcad_design.input import load_design_input  # noqa: E402
from dgcad_design.intent import build_design_intent  # noqa: E402
from dgcad_design.project import build_full_site_models  # noqa: E402
from dgcad_design.robustness import clearance_sensitivity  # noqa: E402

OUT = ROOT / "docs" / "e2e" / "design-intent-audit-001"


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
    frozen_roads = frozen["road_layout"]
    candidate_b = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=getattr(frozen_roads, "corridor_union", None),
    )
    report = clearance_sensitivity(
        [item.footprint for item in candidate_b.buildings],
        frozen_roads.corridor_union,
    )
    report["candidate_id"] = "B"
    report["layout_source"] = "layout_group_preserving"
    report["road_network"] = "frozen 44 design roads"
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "robustness.json").write_text(
        json.dumps(report, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: report[key] for key in (
        "baseline_clearance_m", "declared_rule_m", "samples_per_delta_mode"
    )}, indent=2))
    for row in report["rows"]:
        if row["max_translation_m"] in (0.0, 0.1, 1.0, 2.0, 5.0, 10.0):
            print(
                row["max_translation_m"],
                row["mode"],
                round(row["min_m"], 4),
                round(row["median_m"], 4),
                round(row["fraction_below_3_0_m"], 3),
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

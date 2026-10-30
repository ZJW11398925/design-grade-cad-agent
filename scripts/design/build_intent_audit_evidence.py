"""M4d-2a design-intent audit evidence.

This script deliberately does **not** rewrite the layout algorithm.  It reuses
the M4d-2 candidates and adds independent, descriptive measurements:

* inferred-group provenance (45 m / 8 m / Union-Find, G-01 9 vs 7);
* group quality (cohesion, fragmentation, relative position, shape, displacement);
* source-green retention (12 source objects; area retention is not intent retention);
* access semantics layers L1-L4 (when the module is present);
* clearance sensitivity to coordinate perturbation (robustness.json).

No metric is a gate, a score or a ranking.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

import yaml  # noqa: E402
from shapely.geometry import box  # noqa: E402

from dgcad_design.access import build_co_design_access  # noqa: E402
from dgcad_design.basis import DesignBasis  # noqa: E402
from dgcad_design.buildings import (  # noqa: E402
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.consistency import check_design  # noqa: E402
from dgcad_design.green import build_green_layout  # noqa: E402
from dgcad_design.green_retention import (  # noqa: E402
    green_retention_report,
    green_retention_summary,
)
from dgcad_design.input import load_design_input  # noqa: E402
from dgcad_design.intent import build_design_intent  # noqa: E402
from dgcad_design.intent_metrics import (  # noqa: E402
    compare_group_quality,
    inferred_group_provenance,
)
from dgcad_design.parking import build_parking_layout  # noqa: E402
from dgcad_design.project import build_full_site_models  # noqa: E402

OUT = ROOT / "docs" / "e2e" / "design-intent-audit-001"


def _write(name: str, payload) -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / name).write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def _status_counts(consistency) -> dict:
    counts: dict[str, int] = {}
    for check in consistency.checks:
        counts[check["status"]] = counts.get(check["status"], 0) + 1
    return counts


def _failed(consistency, ids) -> list[str]:
    by_id = {check["id"]: check for check in consistency.checks}
    return [
        check_id
        for check_id in ids
        if by_id.get(check_id, {}).get("status") == "fail"
    ]


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

    def build_candidate(building_layout, candidate_id):
        road_layout, road_access, access_meta = build_co_design_access(
            design_input,
            basis,
            intent,
            building_layout,
            frozen_roads,
            candidate_id=candidate_id,
        )
        green_layout = build_green_layout(
            design_input, building_layout, road_layout, basis, box(*intent.focus_bbox)
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
            "candidate_id": candidate_id,
            "building_layout": building_layout,
            "road_layout": road_layout,
            "road_access": road_access,
            "green_layout": green_layout,
            "parking_layout": parking_layout,
            "consistency": consistency,
            "access_meta": access_meta,
        }

    baseline = {
        "candidate_id": "BASELINE",
        "building_layout": frozen["building_layout"],
        "road_layout": frozen_roads,
        "road_access": frozen["road_access"],
        "green_layout": frozen["green_layout"],
        "parking_layout": frozen["parking_layout"],
        "consistency": check_design(
            design_input,
            basis,
            intent,
            frozen["building_layout"],
            frozen_roads,
            frozen["green_layout"],
            frozen["parking_layout"],
            frozen["road_access"],
        ),
        "access_meta": None,
    }
    candidate_a = build_candidate(frozen["building_layout"], "A")
    group_layout = layout_group_preserving(
        design_input,
        basis,
        intent,
        standardized,
        site_inner,
        road_corridor=getattr(frozen_roads, "corridor_union", None),
    )
    candidate_b = build_candidate(group_layout, "B")

    models = {"baseline": baseline, "A": candidate_a, "B": candidate_b}

    provenance = inferred_group_provenance(
        intent, basis, baseline["building_layout"]
    )
    _write("inferred-groups.json", provenance)

    group_quality = compare_group_quality(
        {"intent": intent, "building_layout": baseline["building_layout"]},
        {"intent": intent, "building_layout": candidate_a["building_layout"]},
        {"intent": intent, "building_layout": candidate_b["building_layout"]},
    )
    _write("group-quality.json", group_quality)

    green_reports = {}
    for label, model in models.items():
        report = green_retention_report(
            design_input,
            model["building_layout"],
            model["road_layout"],
            model["green_layout"],
            intent=intent,
            site_inner=site_inner,
        )
        green_reports[label] = {
            "summary": green_retention_summary(report),
            "report": report,
        }
    _write("green-retention.json", green_reports)

    access_semantics = None
    try:
        from dgcad_design.access_semantics import (  # noqa: WPS433
            access_semantics_report,
        )

        access_semantics = {
            label: access_semantics_report(
                design_input,
                intent,
                model["building_layout"],
                model["road_layout"],
                model["road_access"],
                model["parking_layout"],
            )
            for label, model in models.items()
        }
        _write("access-semantics.json", access_semantics)
    except Exception as error:  # pragma: no cover - module may be in progress
        _write(
            "access-semantics.json",
            {"available": False, "error": f"{type(error).__name__}: {error}"},
        )

    robustness_path = OUT / "robustness.json"
    robustness = (
        json.loads(robustness_path.read_text(encoding="utf-8"))
        if robustness_path.exists()
        else None
    )

    hard_ids = (
        "FULL_SITE_BOUNDARY_SETBACK",
        "FULL_SITE_BUILDING_OVERLAP",
        "FULL_SITE_ROAD_CLEARANCE",
        "FULL_SITE_NS_SPACING",
        "ROAD_ACCESS_COVERAGE",
        "DEAD_END_RESOLUTION",
    )
    four_level = {}
    for label, model in models.items():
        consistency = model["consistency"]
        counts = _status_counts(consistency)
        failed = _failed(consistency, hard_ids)
        four_level[label] = {
            "geometric_hard_checks": {
                "status": "pass" if not failed else "fail",
                "failed_checks": failed,
                "counts": counts,
                "note": "29 declared checks; no threshold widened",
            },
            "design_intent_quality": {
                "status": "descriptive_only",
                "group_fragmentation": group_quality["candidates"][label][
                    "summary"
                ].get("fragmentation.groups_non_contiguous"),
                "building_displacement_max_m": group_quality["candidates"][
                    label
                ]["summary"].get("displacement.max_m"),
                "green_building_occupied_m2": green_reports[label][
                    "summary"
                ].get("building_occupied_area_m2"),
                "note": "no pass/fail verdict; see group-quality / green-retention",
            },
            "deferred_design_items": {
                "status": "incomplete",
                "count": counts.get("deferred", 0),
                "note": "deferred items are not completed design",
            },
            "cad_host_verification": {
                "status": "not_verified",
                "note": "ezdxf readback is internal; real CAD host round-trip outstanding",
            },
        }

    audit = {
        "schema_id": "dgcad.design-intent-audit.v0.1",
        "version": "0.26.0",
        "source": "CASE-SKETCH-001",
        "candidates": ["baseline", "A", "B"],
        "inferred_groups": provenance,
        "group_quality": group_quality,
        "green_retention": green_reports,
        "access_semantics": access_semantics,
        "robustness": robustness,
        "four_level_status": four_level,
        "notes": [
            "17 groups are inferred by the Agent (45 m centroid distance, 8 m main-road buffer, transitive Union-Find); they are not designer-confirmed groups.",
            "groups_preserved only means member ids are complete; groups_split means a group occupies non-adjacent rows.",
            "G-01 has 9 inferred members; the focus layout preserves 7 of them (SK-BLD-0038/0061 are not in the focus set).",
            "source-green area retention is not spatial/intent retention; the layout buildable area does not subtract source greens.",
            "coverage 17/17 is group-level access, not 55-building frontage or garage driveway.",
            "the 1.6 cm clearance margin is not robust against a 0.1 m relative coordinate perturbation; the 3.0 m rule is unchanged.",
        ],
    }
    _write("audit.json", audit)
    print(
        json.dumps(
            {
                "out": str(OUT),
                "four_level": four_level,
                "provenance_chain_max_pairwise_m": max(
                    (
                        item.get("max_pairwise_source_distance_m") or 0.0
                        for item in provenance.get("groups", [])
                    ),
                    default=0.0,
                ),
                "green_A_building_occupied_m2": green_reports["A"]["summary"].get(
                    "building_occupied_area_m2"
                ),
                "green_B_building_occupied_m2": green_reports["B"]["summary"].get(
                    "building_occupied_area_m2"
                ),
                "access_semantics_available": access_semantics is not None,
                "robustness_available": robustness is not None,
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""M4d full-site experimental evidence (reproducible).

Writes the full-site sheet evidence plus the 29-check consistency report into
the given directory.  This is a *research draft*: the full-site layout is
geometrically valid (boundary / overlap / 20 m rows / 3 m road clearance are
measured), but the declared group-access relations and dead-end resolutions
still belong to the focus pipeline.  The access gap is reported, not hidden.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_design.consistency import check_design
from dgcad_design.project import build_full_site_models, run_full_site_evidence


def main(argv: list[str] | None = None) -> int:
    args = list(argv if argv is not None else sys.argv[1:])
    out = Path(
        args[0] if args else ROOT / "docs" / "e2e" / "design-synthesis-full-site-001"
    ).resolve()
    case = ROOT / "docs" / "e2e" / "sketch-001"
    basis = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
    profile = ROOT / "fixtures" / "design" / "design-profile-001.yaml"

    evidence = run_full_site_evidence(case, basis, profile, out)
    models = build_full_site_models(case, basis, profile)
    consistency = check_design(
        models["design_input"],
        models["basis"],
        models["intent"],
        models["building_layout"],
        models["road_layout"],
        models["green_layout"],
        models["parking_layout"],
        models["road_access"],
    )
    (out / "full-site-consistency.json").write_text(
        json.dumps(consistency.to_dict(), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(
        json.dumps(
            {
                "output_dir": str(out),
                "status": evidence.get("status"),
                "building_count": evidence.get("building_count"),
                "unit_count": evidence.get("unit_count"),
                "households": evidence.get("households"),
                "checks": len(consistency.checks),
                "check_status": {
                    status: sum(
                        1 for check in consistency.checks if check["status"] == status
                    )
                    for status in ("pass", "info", "deferred", "fail")
                },
                "road_access_coverage": consistency.metrics.get(
                    "road_access_coverage"
                ),
                "road_access_relation_error_count": consistency.metrics.get(
                    "road_access_relation_error_count"
                ),
                "full_site_min_road_clearance_m": consistency.metrics.get(
                    "full_site_min_road_clearance_m"
                ),
                "full_site_min_ns_gap_m": consistency.metrics.get(
                    "full_site_min_ns_gap_m"
                ),
                "designed_green_ratio": consistency.metrics.get(
                    "designed_green_ratio"
                ),
            },
            indent=2,
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

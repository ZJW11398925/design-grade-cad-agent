#!/usr/bin/env python3
"""Run the first autonomous standardized design synthesis pilot."""
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_design import DesignSynthesisBlocked, run_design_synthesis  # noqa: E402

CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
OUT = ROOT / "docs" / "e2e" / "design-synthesis-001"


def main() -> int:
    try:
        summary = run_design_synthesis(CASE, BASIS, PROFILE, OUT)
    except DesignSynthesisBlocked as exc:
        print(f"BLOCKED: {exc}")
        return 1
    print(
        json.dumps(
            {
                "status": summary["status"],
                "draft_id": summary["draft_id"],
                "design_authority": summary["design_authority"],
                "human_confirmed": summary["human_confirmed"],
                "focus_group": summary["focus_group_id"],
                "metrics": summary["metrics"],
                "dxf": summary["dxf"],
                "readback": summary["readback"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run CASE-SKETCH-001-HANDOFF-A and refresh its evidence directory."""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))

from dgcad_e2e import SketchHandoffProject  # noqa: E402

FIXTURE = ROOT / "fixtures" / "sketch" / "CASE-SKETCH-001-HANDOFF-A"
OUT = ROOT / "docs" / "e2e" / "sketch-handoff-a"


def main() -> int:
    readme = OUT / "README.md"
    readme_text = readme.read_text(encoding="utf-8") if readme.exists() else None
    if OUT.exists():
        shutil.rmtree(OUT)
    project = SketchHandoffProject.create(
        FIXTURE / "handoff.yaml",
        FIXTURE / "review.yaml",
        OUT,
    )
    summary = project.run_pilot()
    shutil.rmtree(OUT / "runtime", ignore_errors=True)
    if readme_text is not None:
        readme.write_text(readme_text, encoding="utf-8")
    print(
        json.dumps(
            {
                "handoff_id": summary["handoff_id"],
                "review_scope": summary["review_scope"],
                "dxf": summary["dxf"],
                "readback": summary["readback"],
                "cad_ir_verdict": summary["cad_ir_validation"]["verdict"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

#!/usr/bin/env python3
"""Run the M4c-0 open-source reuse experiments in order."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main() -> int:
    for script in (
        "exp_a_building.py",
        "exp_b_roads.py",
        "exp_c_collaborative.py",
    ):
        print(f"=== {script} ===")
        result = subprocess.run(
            [sys.executable, str(HERE / script)], check=False
        )
        if result.returncode != 0:
            return result.returncode
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

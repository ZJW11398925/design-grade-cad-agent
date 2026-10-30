"""M4d-2a robustness evidence: clearance sensitivity (no gate)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "e2e" / "design-intent-audit-001"


def _report() -> dict:
    return json.loads((EVIDENCE / "robustness.json").read_text(encoding="utf-8"))


def _rows(report: dict, mode: str) -> dict[float, dict]:
    return {
        float(row["max_translation_m"]): row
        for row in report["rows"]
        if row["mode"] == mode
    }


def test_robustness_reports_the_declared_rule_and_baseline():
    report = _report()
    assert report["declared_rule_m"] == 3.0
    assert report["baseline_clearance_m"] == pytest.approx(
        3.0164672267820585
    )
    assert report["candidate_id"] == "B"
    assert report["samples_per_delta_mode"] >= 12
    assert "pass/fail gate" in json.dumps(report).lower()


def test_common_datum_translation_does_not_change_clearance():
    rows = _rows(_report(), "common_datum")
    for delta, row in rows.items():
        assert row["min_m"] == pytest.approx(3.0164672267820585)
        assert row["max_m"] == pytest.approx(3.0164672267820585)
        assert row["fraction_below_3_0_m"] == 0.0


def test_independent_jitter_removes_the_margin():
    report = _report()
    for mode in ("buildings_only", "buildings_and_roads"):
        rows = _rows(report, mode)
        assert rows[0.0]["min_m"] == pytest.approx(3.0164672267820585)
        # A relative coordinate error of only 0.1 m already violates the 3 m
        # rule in every sample: the 1.6 cm margin is not a robust margin.
        assert rows[0.1]["fraction_below_3_0_m"] == pytest.approx(1.0)
        assert rows[0.1]["min_m"] < 3.0
        # The rule itself is never changed.
        assert report["declared_rule_m"] == 3.0


def test_robustness_is_deterministic():
    first = _report()
    second = _report()
    assert first["rows"] == second["rows"]
    assert first["seed"] == second["seed"]

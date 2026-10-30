"""M4d-2b candidate-C evidence contract tests (no-gain outcome)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "e2e" / "design-candidate-c-001"


def _load() -> dict:
    return json.loads((EVIDENCE / "candidate-c.json").read_text(encoding="utf-8"))


def test_candidate_c_search_is_bounded_and_honest():
    result = _load()
    assert result["decision"] == "no_improvement_same_as_b"
    assert result["same_as_b"] is True
    assert result["hard_ok"] is True
    assert result["variant_count"] >= 12
    assert len(result["variant_table"]) >= 12
    assert result["selected_variant"] == "default"
    assert result["selected_record"]["failed_hard_checks"] == []
    assert result["selected_record"]["check_status"].get("fail", 0) == 0


def test_default_is_hard_valid_and_not_every_variant_is_feasible():
    result = _load()
    rows = {row["variant"]: row for row in result["variant_table"]}
    assert rows["default"]["hard_ok"] is True
    valid = [row for row in rows.values() if row["hard_ok"] is True]
    invalid = [
        row
        for row in rows.values()
        if row["hard_ok"] is False
    ]
    assert valid, "the default/B-equivalent variant must remain feasible"
    assert invalid, "the search must not pretend every variant is feasible"
    for row in invalid:
        # A variant is either hard-failing a declared check or cannot even
        # generate a layout; both are recorded honestly.
        if row.get("error"):
            assert row.get("failed_hard_checks") == []
        else:
            assert row["failed_hard_checks"]
            assert row["failed_hard_checks"][0] in {
                "FULL_SITE_NS_SPACING",
                "FULL_SITE_ROAD_CLEARANCE",
            }


def test_local_repair_was_attempted_and_rejected_honestly():
    result = _load()
    local = result["local_repair"]
    assert local["proposal_count"] >= 2
    assert local["accepted_count"] == 0
    assert result["local_repair_improved"] is False
    for entry in local["log"]:
        assert entry["accepted"] is False
        assert "rejected" in entry["reason"]


def test_no_new_candidate_is_promoted_and_no_dxf_exists():
    result = _load()
    assert result["same_as_b"] is True
    assert not (EVIDENCE / "C").exists()
    assert not (EVIDENCE / "candidate-c.dxf").exists()
    assert "negative result" in (EVIDENCE / "README.md").read_text(
        encoding="utf-8"
    ).lower()

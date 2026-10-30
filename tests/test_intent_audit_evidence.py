"""M4d-2a intent-audit evidence contract tests (committed evidence)."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "e2e" / "design-intent-audit-001"


def _load(name: str) -> dict:
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_inferred_groups_are_not_designer_confirmed():
    provenance = _load("inferred-groups.json")
    assert provenance["groups_are_inferred"] is True
    assert provenance["designer_confirmed"] is False
    assert provenance["group_distance_m"] == pytest.approx(45.0)
    assert provenance["main_road_buffer_m"] == pytest.approx(8.0)
    assert provenance["group_count"] == 17
    max_pairwise = max(
        item["max_pairwise_source_distance_m"]
        for item in provenance["groups"]
    )
    assert max_pairwise > 45.0
    focus = provenance["focus_group"]
    assert focus["inferred_building_count"] == 9
    assert focus["focus_layout_building_count"] == 7
    assert set(focus["dropped_from_focus_layout"]) == {
        "SK-BLD-0038",
        "SK-BLD-0061",
    }


def test_group_quality_is_descriptive_and_shows_B_fragmentation():
    quality = _load("group-quality.json")
    assert quality["ranking"] is None
    assert quality["scoring"] is None
    assert quality["pass_fail_gate"] is None
    b = quality["candidates"]["B"]["summary"]
    assert b["fragmentation.groups_non_contiguous"] == 12
    assert b["fragmentation.total_row_runs"] == 43
    assert b["displacement.max_m"] == pytest.approx(278.4615666910247)
    a = quality["candidates"]["A"]["summary"]
    assert a["fragmentation.groups_non_contiguous"] == 10
    assert a["displacement.max_m"] == pytest.approx(147.25157520912128)


def test_source_green_is_occupied_but_area_retention_is_not_intent():
    green = _load("green-retention.json")
    for label in ("baseline", "A", "B"):
        summary = green[label]["summary"]
        assert summary["source_green_count"] == 12
        assert green[label]["report"]["area_retention_is_not_intent_retention"] is True
        assert summary["lost_area_m2"] == pytest.approx(0.0, abs=1e-6)
    assert green["A"]["summary"]["building_occupied_area_m2"] == pytest.approx(
        845.541, abs=1e-3
    )
    assert green["B"]["summary"]["building_occupied_area_m2"] == pytest.approx(
        713.445, abs=1e-3
    )
    assert green["A"]["summary"]["preserved_count"] == 7
    assert green["A"]["summary"]["shrunk_count"] == 5


def test_access_semantics_never_turns_group_access_into_building_access():
    access = _load("access-semantics.json")
    for label in ("A", "B"):
        layers = access[label]["layers"]
        l1 = layers["l1_group_external_access"]
        assert l1["status"] == "designed"
        assert l1["summary"]["group_coverage"] == pytest.approx(1.0)
        assert l1["claims"]["access_scope"] == "group_level"
        assert l1["claims"]["claims_single_building_access"] is False
        assert layers["l2_internal_group_roads"]["status"] == "not_designed"
        l3 = layers["l3_building_frontage"]
        assert l3["status"] == "geometry_measured"
        assert l3["summary"]["building_count"] == 55
        assert l3["summary"]["fronts_road_count"] < 55
        assert layers["l4_garage_driveway"]["status"] == "driveway_deferred"
        assert layers["l4_garage_driveway"]["summary"][
            "driveway_designed_count"
        ] == 0
    assert (
        access["B"]["layers"]["l1_group_external_access"]["summary"][
            "groups_served"
        ]
        == 17
    )
    assert (
        access["B"]["layers"]["l3_building_frontage"]["summary"][
            "fronts_road_count"
        ]
        == 26
    )


def test_clearance_margin_is_not_robust():
    robustness = _load("robustness.json")
    assert robustness["declared_rule_m"] == 3.0
    rows = {
        (row["mode"], row["max_translation_m"]): row
        for row in robustness["rows"]
    }
    assert rows[("buildings_only", 0.1)]["fraction_below_3_0_m"] == 1.0
    assert rows[("buildings_only", 0.1)]["min_m"] < 3.0
    assert rows[("common_datum", 10.0)]["min_m"] == pytest.approx(
        3.0164672267820585
    )


def test_four_level_status_keeps_B_incomplete():
    audit = _load("audit.json")
    status = audit["four_level_status"]
    assert status["A"]["geometric_hard_checks"]["status"] == "fail"
    assert status["A"]["geometric_hard_checks"]["failed_checks"] == [
        "FULL_SITE_ROAD_CLEARANCE"
    ]
    assert status["B"]["geometric_hard_checks"]["status"] == "pass"
    assert status["B"]["deferred_design_items"]["count"] == 5
    assert status["B"]["cad_host_verification"]["status"] == "not_verified"
    assert status["B"]["design_intent_quality"]["status"] == "descriptive_only"
    assert status["B"]["design_intent_quality"]["group_fragmentation"] == 12
    assert status["B"]["design_intent_quality"][
        "building_displacement_max_m"
    ] == pytest.approx(278.4615666910247)

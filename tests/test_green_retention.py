"""M4d-2a: traceability tests for the 12 original green objects.

The retention report is a **descriptive** post-hoc account: the building
layouts are packed without the source greens as obstacles, so these tests
assert the measured readings and the documented status semantics, not a
landscape-design pass.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from shapely.geometry import Polygon, box

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    layout_full_site,
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.green import build_green_layout
from dgcad_design.green_retention import (
    GREEN_STATUSES,
    green_retention_report,
    green_retention_summary,
)
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
EXPECTED_SOURCE_IDS = [f"SK-GRN-{index:04d}" for index in range(1, 13)]


@lru_cache(maxsize=1)
def _context():
    basis = DesignBasis.from_dict(
        yaml.safe_load(BASIS_PATH.read_text(encoding="utf-8"))
    )
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)
    site_inner = design_input.site_boundary.buffer(-basis.boundary_setback_m)
    baseline_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    road_layout = build_road_layout(
        design_input, basis, intent, baseline_layout
    )
    corridor = road_layout.corridor_union
    return {
        "basis": basis,
        "design_input": design_input,
        "intent": intent,
        "site_inner": site_inner,
        "baseline_layout": baseline_layout,
        "road_layout": road_layout,
        "corridor": corridor,
        "standardized": standardized,
    }


@lru_cache(maxsize=1)
def _reports():
    context = _context()
    basis = context["basis"]
    design_input = context["design_input"]
    intent = context["intent"]
    site_inner = context["site_inner"]
    road_layout = context["road_layout"]
    corridor = context["corridor"]
    layout_a = layout_full_site(
        design_input,
        basis,
        intent,
        context["standardized"],
        site_inner,
        road_corridor=corridor,
    )
    layout_b = layout_group_preserving(
        design_input,
        basis,
        intent,
        context["standardized"],
        site_inner,
        road_corridor=corridor,
    )
    focus_box = box(*intent.focus_bbox)
    reports = {}
    for label, layout in (
        ("baseline", context["baseline_layout"]),
        ("A", layout_a),
        ("B", layout_b),
    ):
        green_layout = build_green_layout(
            design_input, layout, road_layout, basis, focus_box
        )
        report = green_retention_report(
            design_input,
            layout,
            road_layout,
            green_layout,
            intent=intent,
            site_inner=site_inner,
        )
        reports[label] = {
            "layout": layout,
            "green_layout": green_layout,
            "report": report,
            "summary": green_retention_summary(report),
        }
    return reports


def test_all_twelve_source_greens_are_traced():
    context = _context()
    reports = _reports()
    design_input = context["design_input"]
    source_ids = [green.trace_id for green in design_input.greens]
    assert source_ids == EXPECTED_SOURCE_IDS
    for label in ("baseline", "A", "B"):
        report = reports[label]["report"]
        assert report["schema_id"] == "dgcad.green-retention.v0.1"
        assert report["area_retention_is_not_intent_retention"] is True
        assert report["descriptive_status_not_gate"] is True
        assert len(report["objects"]) == 12
        assert [item["green_id"] for item in report["objects"]] == source_ids
        assert report["summary"]["traced_green_count"] == 12
        assert report["summary"]["source_green_count"] == 12
        for item in report["objects"]:
            assert item["status"] in GREEN_STATUSES
            for field in (
                "source_area_m2",
                "inside_site_area_m2",
                "building_occupied_area_m2",
                "road_occupied_area_m2",
                "retained_open_space_area_m2",
                "retained_designed_area_m2",
                "free_space_retaining_area_m2",
                "lost_area_m2",
                "retained_open_space_ratio_of_inside",
                "candidate_cluster_id",
            ):
                assert field in item
        # every source object's in-site area is partitioned by the account
        for item in report["objects"]:
            total = (
                item["building_occupied_area_m2"]
                + item["road_occupied_area_m2"]
                + item["retained_open_space_area_m2"]
                + item["lost_area_m2"]
            )
            assert total == pytest.approx(
                item["inside_site_area_m2"], abs=0.01
            )
        status_counts = report["summary"]["status_counts"]
        assert set(status_counts) == set(GREEN_STATUSES)
        assert sum(status_counts.values()) == 12


def test_group_id_is_annotated_where_declared():
    context = _context()
    intent = context["intent"]
    report = _reports()["A"]["report"]
    declared = {}
    for group in intent.groups:
        for green_id in group.green_ids:
            declared[str(green_id)] = group.group_id
    assert declared == {
        "SK-GRN-0008": "G-01",
        "SK-GRN-0012": "G-02",
        "SK-GRN-0011": "G-17",
    }
    by_id = {item["green_id"]: item for item in report["objects"]}
    for green_id, group_id in declared.items():
        assert by_id[green_id]["group_id"] == group_id
    unassigned = [
        item for item in report["objects"] if item["green_id"] not in declared
    ]
    assert unassigned
    assert all(item["group_id"] is None for item in unassigned)


def test_real_baseline_a_b_readings():
    summaries = {label: _reports()[label]["summary"] for label in ("baseline", "A", "B")}
    # source total is 10,986.4 m2 across 12 greens, all inside the site
    for label in ("baseline", "A", "B"):
        summary = summaries[label]
        assert summary["source_area_m2"] == pytest.approx(10986.4, abs=1.0)
        assert summary["inside_site_area_m2"] == pytest.approx(
            summary["source_area_m2"], abs=0.01
        )
        assert summary["outside_site_area_m2"] == pytest.approx(0.0, abs=0.01)
        assert summary["lost_area_m2"] == pytest.approx(0.0, abs=0.5)
        assert summary["road_occupied_area_m2"] == pytest.approx(
            64.113, abs=0.5
        )
        # retained + occupied + lost = source
        partition = (
            summary["retained_open_space_area_m2"]
            + summary["building_occupied_area_m2"]
            + summary["road_occupied_area_m2"]
            + summary["lost_area_m2"]
        )
        assert partition == pytest.approx(summary["source_area_m2"], abs=0.5)
    # measured readings: the full-site layouts occupy more original green area
    # than the focus-only baseline
    assert summaries["baseline"]["building_occupied_area_m2"] == pytest.approx(
        137.895, abs=0.5
    )
    assert summaries["baseline"]["retained_open_space_area_m2"] == pytest.approx(
        10784.402, abs=0.5
    )
    assert summaries["A"]["building_occupied_area_m2"] == pytest.approx(
        845.541, abs=0.5
    )
    assert summaries["A"]["retained_open_space_area_m2"] == pytest.approx(
        10076.757, abs=0.5
    )
    assert summaries["A"]["retained_designed_area_m2"] == pytest.approx(
        10076.757, abs=0.5
    )
    assert summaries["B"]["building_occupied_area_m2"] == pytest.approx(
        713.445, abs=0.5
    )
    assert summaries["B"]["retained_open_space_area_m2"] == pytest.approx(
        10208.852, abs=0.5
    )
    assert summaries["A"]["retained_open_space_area_m2"] < summaries[
        "baseline"
    ]["retained_open_space_area_m2"]
    assert summaries["B"]["retained_open_space_area_m2"] < summaries[
        "baseline"
    ]["retained_open_space_area_m2"]
    # new open space / designed green created by the candidate layouts
    assert summaries["baseline"]["new_designed_green_area_m2"] == pytest.approx(
        2326.002, abs=1.0
    )
    assert summaries["A"]["new_designed_green_area_m2"] == pytest.approx(
        20864.147, abs=2.0
    )
    assert summaries["B"]["new_designed_green_area_m2"] == pytest.approx(
        19586.782, abs=2.0
    )
    for label in ("baseline", "A", "B"):
        assert summaries[label]["new_open_space_area_m2"] > 100000.0
        assert summaries[label]["new_open_space_area_m2"] < 130000.0
        assert summaries[label]["new_open_space_object_count"] > 0


def test_descriptive_status_labels_follow_measured_ratios():
    summaries = {
        label: _reports()[label]["summary"] for label in ("baseline", "A", "B")
    }
    # baseline: 10 greens untouched, 2 touched by a building/road
    assert summaries["baseline"]["status_counts"] == {
        "preserved": 10,
        "shrunk": 2,
        "cancelled": 0,
        "occupied_by_buildings": 0,
        "occupied_by_roads": 0,
        "moved": 0,
        "not_applicable": 0,
    }
    for label in ("A", "B"):
        counts = summaries[label]["status_counts"]
        assert counts["preserved"] + counts["shrunk"] == 12
        assert counts["cancelled"] == 0
        assert counts["occupied_by_buildings"] == 0
        assert counts["occupied_by_roads"] == 0
        assert counts["shrunk"] >= 1
    # status label matches the measured ratio for every object
    for label in ("baseline", "A", "B"):
        for item in _reports()[label]["report"]["objects"]:
            ratio = item["retained_open_space_ratio_of_inside"]
            if item["status"] == "preserved":
                assert ratio >= 0.99
            elif item["status"] == "shrunk":
                assert 0.01 <= ratio < 0.99
            elif item["status"] == "cancelled":
                assert ratio < 0.01


def test_synthetic_building_covers_green_marks_occupied():
    site = box(0.0, 0.0, 200.0, 200.0)
    source_polygon = box(10.0, 10.0, 110.0, 110.0)  # 100 x 100 = 10 000 m2
    building_polygon = box(10.0, 10.0, 70.0, 110.0)  # 60 % of the green
    design_input = SimpleNamespace(
        greens=[
            SimpleNamespace(
                trace_id="SK-GRN-T1",
                geometry=source_polygon,
                area_m2=source_polygon.area,
            )
        ],
        site_boundary=site,
        site_area_m2=site.area,
    )
    building_layout = SimpleNamespace(
        buildings=[SimpleNamespace(footprint=building_polygon)]
    )
    road_layout = SimpleNamespace(
        corridor_union=Polygon(), sidewalk_union=Polygon()
    )
    green_layout = SimpleNamespace(greens=(), full_site_green=None)
    report = green_retention_report(
        design_input,
        building_layout,
        road_layout,
        green_layout,
        site_inner=site,
    )
    item = report["objects"][0]
    assert item["status"] == "occupied_by_buildings"
    assert item["building_occupied_area_m2"] == pytest.approx(6000.0)
    assert item["retained_open_space_area_m2"] == pytest.approx(0.0)
    assert item["lost_area_m2"] == pytest.approx(4000.0)
    assert report["summary"]["status_counts"]["occupied_by_buildings"] == 1


def test_synthetic_all_cancelled_and_all_retained():
    site = box(0.0, 0.0, 200.0, 200.0)
    greens = [
        SimpleNamespace(
            trace_id=f"SK-GRN-T{index}",
            geometry=box(10.0 + index * 40.0, 10.0, 40.0 + index * 40.0, 40.0),
            area_m2=900.0,
        )
        for index in range(2)
    ]
    design_input = SimpleNamespace(
        greens=greens, site_boundary=site, site_area_m2=site.area
    )
    empty_layout = SimpleNamespace(buildings=[])
    empty_roads = SimpleNamespace(
        corridor_union=Polygon(), sidewalk_union=Polygon()
    )
    # nothing retained: no candidate open space at all
    cancelled = green_retention_report(
        design_input,
        empty_layout,
        empty_roads,
        SimpleNamespace(greens=(), full_site_green=None),
        site_inner=site,
    )
    assert [
        item["status"] for item in cancelled["objects"]
    ] == ["cancelled", "cancelled"]
    assert cancelled["summary"]["retained_open_space_area_m2"] == 0.0
    assert cancelled["summary"]["lost_area_m2"] == pytest.approx(1800.0)

    # everything retained: candidate open space covers the source exactly
    candidate = SimpleNamespace(
        greens=[
            SimpleNamespace(
                green_id="CAND-1",
                classification="supplementary_green",
                geometry=greens[0].geometry,
                area_m2=greens[0].area_m2,
            ),
            SimpleNamespace(
                green_id="CAND-2",
                classification="supplementary_green",
                geometry=greens[1].geometry,
                area_m2=greens[1].area_m2,
            ),
        ],
        full_site_green=None,
    )
    retained = green_retention_report(
        design_input,
        empty_layout,
        empty_roads,
        candidate,
        site_inner=site,
    )
    assert [item["status"] for item in retained["objects"]] == [
        "preserved",
        "preserved",
    ]
    assert retained["summary"]["retained_open_space_area_m2"] == pytest.approx(
        1800.0
    )
    assert retained["summary"]["lost_area_m2"] == pytest.approx(0.0)
    # candidate geometry already covered by source greens: no new open space
    assert retained["summary"]["new_open_space_area_m2"] == pytest.approx(0.0)
    assert retained["summary"]["new_designed_green_area_m2"] == pytest.approx(
        0.0
    )


def test_synthetic_moved_green_is_reported_as_moved():
    site = box(0.0, 0.0, 200.0, 200.0)
    source_polygon = box(10.0, 10.0, 60.0, 60.0)
    moved_polygon = box(120.0, 120.0, 170.0, 170.0)
    design_input = SimpleNamespace(
        greens=[
            SimpleNamespace(
                trace_id="SK-GRN-M1",
                geometry=source_polygon,
                area_m2=source_polygon.area,
            )
        ],
        site_boundary=site,
        site_area_m2=site.area,
    )
    green_layout = SimpleNamespace(
        greens=[
            SimpleNamespace(
                green_id="SK-GRN-M1",
                classification="cluster_green",
                geometry=moved_polygon,
                area_m2=moved_polygon.area,
            )
        ],
        full_site_green=None,
    )
    report = green_retention_report(
        design_input,
        SimpleNamespace(buildings=[]),
        SimpleNamespace(corridor_union=Polygon(), sidewalk_union=Polygon()),
        green_layout,
        site_inner=site,
    )
    item = report["objects"][0]
    assert item["status"] == "moved"
    assert item["candidate_cluster_id"] == "SK-GRN-M1"
    assert item["candidate_cluster_shared_area_m2"] == pytest.approx(0.0)
    assert report["summary"]["status_counts"]["moved"] == 1


def test_area_retention_is_not_intent_retention_statement():
    report = _reports()["A"]["report"]
    assert report["area_retention_is_not_intent_retention"] is True
    note = report["note"].lower()
    assert "area intersection" in note
    assert "continuity" in note
    assert "occupation was measured after the fact" in note
    basis = report["candidate_open_space_basis"]
    assert "free_space_retaining" in basis
    assert "retained_designed" in basis
    assert "retained_open_space" in basis
    # the thresholds are documented and explicitly non-gating
    thresholds = report["status_thresholds"]
    assert thresholds["preserved_open_space_ratio"] == 0.99
    assert "no existing check" in thresholds["note"]

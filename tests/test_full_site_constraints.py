"""Full-site constraint checks and design-synthesis contract v0.9 (M4d).

The M4d milestone extends the design from the focus block to the full site.
This module binds the new full-site checks to generated geometry and the new
contract to the live check list:

* ``FULL_SITE_BOUNDARY_SETBACK``, ``FULL_SITE_BUILDING_OVERLAP``,
  ``FULL_SITE_ROAD_CLEARANCE`` and ``FULL_SITE_NS_SPACING`` are pass/fail
  geometry checks once the full-site layout is complete (the layout id set
  equals the expected building set with no missing/unexpected/duplicate id and
  every building carries a ``row_index``); while the layout is incomplete or
  still at source positions the checks are deferred with a diagnostic value and
  are never a pass;
* ``DESIGNED_GREEN_RATIO`` stays deferred on the legacy cluster/strip account;
  the generated full-site account is **potential open space**
  (``classification="potential_open_space"``), an open-space allocation
  candidate that does not enter the designed-green numerator;
* the 20.0 m north-south row pitch is this candidate row-layout strategy's
  row-rhythm rule plus a design-basis assumption; over-spacing is a row-rhythm
  violation, not a regulatory/professional-compliance conclusion;
* ``contracts/design-synthesis-v0.9.yaml`` supersedes v0.8, the gate register
  points at v0.9, and the contract carries 32 verification names (29 design
  checks + 3 DXF-level items).

Positive and negative samples are built on fake full-site layouts (a shifted
row, an overlapping pair, a footprint outside the setback, a footprint on a
road corridor, an incomplete id set) so a fail/deferred verdict is proven by
geometry and id completeness, not by relabelling.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path

import pytest
import yaml
from shapely.affinity import translate
from shapely.geometry import box

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.access import build_road_access
from dgcad_design.buildings import (
    BuildingLayout,
    StandardBuilding,
    find_focus_design_rect,
    layout_focus_region,
    layout_full_site,
    standardize_all,
)
from dgcad_design.consistency import (
    BOUNDARY_SETBACK_TOLERANCE_M,
    BUILDING_OVERLAP_TOLERANCE_M2,
    FULL_SITE_ROW_PITCH_RULE_SCOPE,
    FULL_SITE_SPACING_TOLERANCE_M,
    GREEN_RATIO_NUMERICAL_EPSILON,
    NUMERICAL_EPSILON_M,
    check_design,
    designed_green_report,
    full_site_boundary_report,
    full_site_building_overlap_report,
    full_site_checks,
    full_site_layout_state,
    full_site_ns_spacing_report,
    full_site_road_clearance_report,
)
from dgcad_design.green import (
    POTENTIAL_OPEN_SPACE_CLASSIFICATION,
    FullSiteGreenDesign,
    build_green_layout,
)
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
CONTRACTS = ROOT / "contracts"
V8 = CONTRACTS / "design-synthesis-v0.8.yaml"
V9 = CONTRACTS / "design-synthesis-v0.9.yaml"
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"

#: verification.required names expected in v0.9, in contract order (29 design
#: checks + 3 DXF-level items = 32).
EXPECTED_VERIFICATION = [
    "far_arithmetic_scenario",
    "parking_requirement_arithmetic",
    "parking_entrance_count",
    "parking_capacity",
    "parking_entrance_proximity",
    "parking_driveway_connection",
    "parking_layout",
    "unit_count_basis_invariant",
    "focus_north_south_spacing",
    "focus_boundary_setback",
    "focus_building_overlap",
    "focus_road_clearance",
    "road_connectivity",
    "road_corridor_coverage",
    "road_access_coverage",
    "road_boundary_containment",
    "main_road_building_overlap",
    "road_alignment_evidence",
    "full_site_boundary_setback",
    "full_site_building_overlap",
    "full_site_road_clearance",
    "full_site_north_south_spacing",
    "dead_end_justification",
    "dead_end_resolution",
    "road_width_assignment",
    "candidate_open_space_ratio",
    "unbuilt_ratio",
    "designed_green_ratio",
    "far_final_verification",
    "dxf_audit",
    "dxf_readback",
    "dxf_privacy",
]

DXF_LEVEL_ITEMS = {"dxf_audit", "dxf_readback", "dxf_privacy"}

#: Expected consistency check ids for the 29 design-level verification names
#: (contract order). Uppercasing is the rule, with the two documented legacy
#: abbreviations in ``consistency.py`` (FOCUS_NS_SPACING, FULL_SITE_NS_SPACING).
EXPECTED_DESIGN_CHECK_IDS = [
    "FAR_ARITHMETIC_SCENARIO",
    "PARKING_REQUIREMENT_ARITHMETIC",
    "PARKING_ENTRANCE_COUNT",
    "PARKING_CAPACITY",
    "PARKING_ENTRANCE_PROXIMITY",
    "PARKING_DRIVEWAY_CONNECTION",
    "PARKING_LAYOUT",
    "UNIT_COUNT_BASIS_INVARIANT",
    "FOCUS_NS_SPACING",
    "FOCUS_BOUNDARY_SETBACK",
    "FOCUS_BUILDING_OVERLAP",
    "FOCUS_ROAD_CLEARANCE",
    "ROAD_CONNECTIVITY",
    "ROAD_CORRIDOR_COVERAGE",
    "ROAD_ACCESS_COVERAGE",
    "ROAD_BOUNDARY_CONTAINMENT",
    "MAIN_ROAD_BUILDING_OVERLAP",
    "ROAD_ALIGNMENT_EVIDENCE",
    "FULL_SITE_BOUNDARY_SETBACK",
    "FULL_SITE_BUILDING_OVERLAP",
    "FULL_SITE_ROAD_CLEARANCE",
    "FULL_SITE_NS_SPACING",
    "DEAD_END_JUSTIFICATION",
    "DEAD_END_RESOLUTION",
    "ROAD_WIDTH_ASSIGNMENT",
    "CANDIDATE_OPEN_SPACE_RATIO",
    "UNBUILT_RATIO",
    "DESIGNED_GREEN_RATIO",
    "FAR_FINAL_VERIFICATION",
]
CHECK_ID_OVERRIDES = {
    "focus_north_south_spacing": "FOCUS_NS_SPACING",
    "full_site_north_south_spacing": "FULL_SITE_NS_SPACING",
}

FULL_SITE_CHECK_IDS = {
    "FULL_SITE_BOUNDARY_SETBACK",
    "FULL_SITE_BUILDING_OVERLAP",
    "FULL_SITE_ROAD_CLEARANCE",
    "FULL_SITE_NS_SPACING",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _check_id(name: str) -> str:
    return CHECK_ID_OVERRIDES.get(name, name.upper())


@lru_cache(maxsize=1)
def _models() -> dict:
    """Build the committed pipeline models once (focus layout baseline)."""

    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standardized = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        design_rect,
    )
    road_layout = build_road_layout(
        design_input, basis, intent, building_layout
    )
    green_layout = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        box(*intent.focus_bbox),
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    road_access = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=design_input.site_boundary,
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
        "basis": basis,
        "design_input": design_input,
        "intent": intent,
        "building_layout": building_layout,
        "road_layout": road_layout,
        "green_layout": green_layout,
        "consistency": consistency,
    }


# --------------------------------------------------------------------- helpers
def _building(
    building_id: str,
    center: tuple[float, float],
    *,
    width: float = 20.0,
    depth: float = 10.0,
    row_index: int | None = None,
    subgroup_id: str = "SB-TEST",
) -> StandardBuilding:
    x, y = center
    footprint = box(x - width / 2, y - depth / 2, x + width / 2, y + depth / 2)
    return StandardBuilding(
        building_id=building_id,
        unit_count=2,
        is_facility=False,
        footprint=footprint,
        unit_lines=(),
        households=4,
        gfa_m2=200.0,
        height_m=30.0,
        source_centroid=(x, y),
        design_centroid=(x, y),
        displacement_m=0.0,
        source_area_m2=footprint.area,
        source_orientation_deg=0.0,
        design_orientation_deg=0.0,
        subgroup_id=subgroup_id,
        row_index=row_index,
        label_anchor=(x, y + depth / 2 + 2.0),
    )


def _layout(
    buildings: list[StandardBuilding],
    rows: tuple[dict, ...] = (),
) -> BuildingLayout:
    return BuildingLayout(
        buildings=tuple(buildings),
        focus_buildings=(),
        rows=rows,
        green_strips=(),
    )


def _row_records(
    rows: list[list[StandardBuilding]], y_values: list[float]
) -> tuple[dict, ...]:
    return tuple(
        {
            "row": index + 1,
            "subgroup_id": "SB-TEST",
            "y": y_values[index],
            "building_ids": [item.building_id for item in row],
            "north_south_gap_m": 20.0,
        }
        for index, row in enumerate(rows)
    )


@lru_cache(maxsize=1)
def _safe_block_center() -> tuple[float, float]:
    """A point inside a free polygon >= 10 m from every road corridor."""

    models = _models()
    basis = models["basis"]
    design_input = models["design_input"]
    road_layout = models["road_layout"]
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    free = site_inner.difference(road_layout.corridor_union.buffer(10.0))
    polygons = (
        list(free.geoms)
        if free.geom_type == "MultiPolygon"
        else [free]
    )
    polygons.sort(key=lambda item: -item.area)
    point = polygons[0].representative_point()
    return (float(point.x), float(point.y))


def _full_site_layout(
    *,
    y_offsets: tuple[float, float, float] = (-30.0, 0.0, 30.0),
) -> BuildingLayout:
    """A fake but geometrically valid full-site layout: 3 rows x 2 buildings."""

    cx, cy = _safe_block_center()
    buildings: list[StandardBuilding] = []
    rows: list[list[StandardBuilding]] = []
    y_values = [cy + offset for offset in y_offsets]
    for row_index, y in enumerate(y_values, start=1):
        row: list[StandardBuilding] = []
        for column, x in enumerate((cx - 15.0, cx + 15.0), start=1):
            item = _building(
                f"FAKE-BLD-{row_index}-{column}",
                (x, y),
                row_index=row_index,
            )
            row.append(item)
            buildings.append(item)
        rows.append(row)
    return _layout(buildings, _row_records(rows, y_values))


@lru_cache(maxsize=1)
def _real_full_site_layout() -> BuildingLayout:
    """The real 55-building full-site layout, placed against the case corridor."""

    models = _models()
    basis = models["basis"]
    design_input = models["design_input"]
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    return layout_full_site(
        design_input,
        basis,
        models["intent"],
        standardize_all(design_input, basis),
        site_inner,
        road_corridor=models["road_layout"].corridor_union,
    )


@lru_cache(maxsize=1)
def _shifted_real_layout() -> BuildingLayout:
    """The real layout with one row moved 0.5 m south (a row-rhythm violation)."""

    layout = _real_full_site_layout()
    rows = sorted({item.row_index for item in layout.buildings})
    target_row = rows[1]
    shifted = []
    for item in layout.buildings:
        if item.row_index != target_row:
            shifted.append(item)
            continue
        footprint = translate(item.footprint, yoff=-0.5)
        centroid = (
            item.design_centroid[0],
            item.design_centroid[1] - 0.5,
        )
        shifted.append(
            replace(
                item,
                footprint=footprint,
                design_centroid=centroid,
                label_anchor=(
                    item.label_anchor[0],
                    item.label_anchor[1] - 0.5,
                ),
            )
        )
    return _layout(shifted)


# --------------------------------------------------------------- layout state
@lru_cache(maxsize=1)
def _expected_ids() -> list[str]:
    return [item.trace_id for item in _models()["design_input"].buildings]


@lru_cache(maxsize=1)
def _real_id_layout() -> BuildingLayout:
    """A fake layout with the real 55 building ids, all row-assigned.

    The footprints are the committed focus-layout footprints (some overlap), so
    this layout is only used for id-completeness/row-assignment tests; geometry
    checks use ``_full_site_layout`` instead.
    """

    buildings = [
        replace(item, row_index=(index // 2) + 1, subgroup_id="SB-TEST")
        for index, item in enumerate(
            _models()["building_layout"].buildings
        )
    ]
    return _layout(buildings)


def test_focus_layout_is_not_a_complete_full_site_layout():
    models = _models()
    state = full_site_layout_state(
        models["building_layout"], _expected_ids()
    )
    assert state["ready"] is False
    # the id set is complete, but 48 buildings are still at source positions
    assert state["complete"] is True
    assert state["completeness_verified"] is True
    assert state["building_count"] == 55
    assert state["missing_building_ids"] == []
    assert state["unexpected_building_ids"] == []
    assert state["duplicate_building_ids"] == []
    assert len(state["missing_row_index_ids"]) == 48
    assert state["row_count"] == 4


def test_fake_full_site_layout_is_ready():
    state = full_site_layout_state(_full_site_layout())
    assert state["ready"] is True
    assert state["complete"] is True
    # without expected_building_ids, set completeness is not verified
    assert state["expected_provided"] is False
    assert state["completeness_verified"] is False
    assert state["row_count"] == 3
    assert state["missing_row_index_ids"] == []


def test_full_site_layout_state_accepts_the_expected_55_building_set():
    layout = _real_full_site_layout()
    state = full_site_layout_state(layout, _expected_ids())
    assert state["ready"] is True
    assert state["complete"] is True
    assert state["completeness_verified"] is True
    assert state["building_count"] == 55
    assert state["missing_building_ids"] == []
    assert state["unexpected_building_ids"] == []
    assert state["duplicate_building_ids"] == []
    assert state["row_count"] == len(
        {item.row_index for item in layout.buildings}
    )
    assert state["row_count"] >= 2


def test_full_site_layout_state_rejects_incomplete_id_sets():
    expected = _expected_ids()
    full = _real_id_layout()
    # missing one building
    state = full_site_layout_state(
        _layout(list(full.buildings[:-1])), expected
    )
    assert state["ready"] is False
    assert state["complete"] is False
    assert state["missing_building_ids"] == [full.buildings[-1].building_id]
    # unexpected (extra) building
    extra = _building("FAKE-BLD-EXTRA", (0.0, 0.0), row_index=1)
    state = full_site_layout_state(
        _layout(list(full.buildings) + [extra]), expected
    )
    assert state["ready"] is False
    assert state["complete"] is False
    assert state["unexpected_building_ids"] == ["FAKE-BLD-EXTRA"]
    # duplicate id
    duplicate = _building(
        full.buildings[0].building_id, (0.0, 0.0), row_index=1
    )
    state = full_site_layout_state(
        _layout(list(full.buildings) + [duplicate]), expected
    )
    assert state["ready"] is False
    assert state["complete"] is False
    assert state["duplicate_building_ids"] == [
        full.buildings[0].building_id
    ]
    # empty layout
    state = full_site_layout_state(_layout([]), expected)
    assert state["ready"] is False
    assert state["complete"] is False
    assert state["building_count"] == 0
    assert len(state["missing_building_ids"]) == 55


def test_full_site_checks_are_deferred_on_an_incomplete_id_set():
    models = _models()
    full = _real_id_layout()
    incomplete = _layout(list(full.buildings[:-1]))
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            incomplete,
            models["road_layout"],
        )
    }
    for check in checks.values():
        assert check["status"] == "deferred"
        assert check["status"] != "pass"
        assert "not complete/integrated" in check["message"]
        assert "missing" in check["message"]
    # a layout with only synthetic ids is also deferred (unexpected id set)
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            _full_site_layout(),
            models["road_layout"],
        )
    }
    for check in checks.values():
        assert check["status"] == "deferred"
        assert "unexpected" in check["message"]
        assert "missing" in check["message"]


# ------------------------------------------------------- north-south spacing
def test_full_site_ns_spacing_passes_on_declared_20m_rows():
    models = _models()
    report = full_site_ns_spacing_report(_full_site_layout(), models["basis"])
    assert report["ready"] is True
    assert report["ok"] is True
    assert report["violation_count"] == 0
    assert report["min_gap_m"] == pytest.approx(20.0, abs=1e-9)
    assert report["required"] == models["basis"].north_south_spacing_m


def test_full_site_ns_spacing_fails_on_under_spacing():
    models = _models()
    # middle row moved 0.5 m south -> 19.5 m gap to the row above
    layout = _full_site_layout(y_offsets=(-30.0, -0.5, 30.0))
    report = full_site_ns_spacing_report(layout, models["basis"])
    assert report["ok"] is False
    assert report["violation_count"] > 0
    kinds = {item["kind"] for item in report["violations"]}
    assert "under_spacing" in kinds
    under = [
        item for item in report["violations"] if item["kind"] == "under_spacing"
    ]
    assert min(item["gap_m"] for item in under) == pytest.approx(
        19.5, abs=1e-9
    )
    assert report["min_gap_m"] == pytest.approx(19.5, abs=1e-9)


def test_full_site_ns_spacing_fails_on_over_spacing():
    models = _models()
    # middle row moved 0.5 m north -> 20.5 m gap to the row below
    layout = _full_site_layout(y_offsets=(-30.0, 0.5, 30.0))
    report = full_site_ns_spacing_report(layout, models["basis"])
    assert report["ok"] is False
    kinds = {item["kind"] for item in report["violations"]}
    assert "over_spacing" in kinds
    over = [
        item for item in report["violations"] if item["kind"] == "over_spacing"
    ]
    assert max(item["gap_m"] for item in over) == pytest.approx(
        20.5, abs=1e-9
    )
    assert report["required"] == 20.0
    assert report["tolerance"] == FULL_SITE_SPACING_TOLERANCE_M == 0.01
    # the 20 m pitch is a candidate row-rhythm rule + design-basis assumption,
    # not a regulatory/professional-compliance conclusion
    assert report["rule_scope"] == FULL_SITE_ROW_PITCH_RULE_SCOPE
    assert (
        report["rule_scope"]
        == "candidate_row_rhythm_and_design_basis_assumption"
    )


def test_full_site_ns_spacing_is_deferred_without_full_site_rows():
    models = _models()
    report = full_site_ns_spacing_report(
        models["building_layout"], models["basis"]
    )
    assert report["ready"] is False
    assert report["ok"] is None
    assert report["value"] is None


# --------------------------------------------------------- boundary setback
def test_full_site_boundary_setback_passes_inside_setback():
    models = _models()
    report = full_site_boundary_report(
        models["design_input"], models["basis"], _full_site_layout()
    )
    assert report["ok"] is True
    assert report["outside"] == []
    assert report["tolerance"] == BOUNDARY_SETBACK_TOLERANCE_M == 0.01


def test_full_site_boundary_setback_fails_outside_setback():
    models = _models()
    basis = models["basis"]
    site_inner = models["design_input"].site_boundary.buffer(
        -basis.boundary_setback_m
    )
    minx, miny, _, _ = site_inner.bounds
    outside_building = _building(
        "FAKE-BLD-OUTSIDE", (minx - 2.0, miny + 10.0), row_index=1
    )
    report = full_site_boundary_report(
        models["design_input"],
        basis,
        _layout([outside_building]),
    )
    assert report["ok"] is False
    assert report["outside_count"] == 1
    record = report["outside"][0]
    assert record["building_id"] == "FAKE-BLD-OUTSIDE"
    assert record["outside_area_m2"] > 0.0
    assert report["value"] == ["FAKE-BLD-OUTSIDE"]


# --------------------------------------------------------- building overlap
def test_full_site_building_overlap_passes_on_disjoint_footprints():
    report = full_site_building_overlap_report(_full_site_layout())
    assert report["ok"] is True
    assert report["pair_count"] == 0
    assert report["tolerance_m2"] == BUILDING_OVERLAP_TOLERANCE_M2 == 0.01


def test_full_site_building_overlap_fails_on_duplicate_footprint():
    cx, cy = _safe_block_center()
    first = _building("FAKE-BLD-A", (cx, cy), row_index=1)
    second = _building("FAKE-BLD-B", (cx + 1.0, cy), row_index=1)
    report = full_site_building_overlap_report(_layout([first, second]))
    assert report["ok"] is False
    assert report["pair_count"] == 1
    pair = report["pairs"][0]
    assert {pair["a"], pair["b"]} == {"FAKE-BLD-A", "FAKE-BLD-B"}
    # 20 x 10 footprint shifted 1 m in x -> 19 m x 10 m overlap
    assert pair["overlap_area_m2"] == pytest.approx(190.0, abs=1e-6)
    assert report["max_overlap_m2"] == pytest.approx(190.0, abs=1e-6)


# ----------------------------------------------------------- road clearance
def test_full_site_road_clearance_passes_far_from_roads():
    models = _models()
    report = full_site_road_clearance_report(
        models["basis"], _full_site_layout(), models["road_layout"]
    )
    assert report["ok"] is True
    assert report["violation_count"] == 0
    assert report["min_clearance_m"] >= models["basis"].building_road_clearance_m
    assert report["required"] == models["basis"].building_road_clearance_m == 3.0
    assert report["epsilon_m"] == NUMERICAL_EPSILON_M == 1e-9


def test_full_site_road_clearance_fails_on_corridor_footprint():
    models = _models()
    road = models["road_layout"].roads[0]
    point = road.centerline.interpolate(0.5, normalized=True)
    building = _building(
        "FAKE-BLD-ONROAD", (point.x, point.y), row_index=1
    )
    report = full_site_road_clearance_report(
        models["basis"], _layout([building]), models["road_layout"]
    )
    assert report["ok"] is False
    assert report["violation_count"] == 1
    assert report["min_clearance_m"] == pytest.approx(0.0, abs=1e-9)
    violation = report["violations"][0]
    assert violation["building_id"] == "FAKE-BLD-ONROAD"
    assert violation["clearance_m"] == pytest.approx(0.0, abs=1e-9)
    assert violation["shortfall_m"] == pytest.approx(3.0, abs=1e-9)
    assert violation["nearest_road_id"] == road.edge_id
    # the achievable uniform clearance of the fixed geometry is published, and
    # the requirement is not reduced to manufacture a pass
    assert report["achievable_uniform_clearance_m"] == pytest.approx(
        0.0, abs=1e-9
    )


# ------------------------------------------------- full-site check statuses
def test_full_site_checks_are_deferred_on_the_focus_layout():
    models = _models()
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            models["building_layout"],
            models["road_layout"],
        )
    }
    assert set(checks) == FULL_SITE_CHECK_IDS
    for check in checks.values():
        assert check["status"] == "deferred"
        assert check["status"] != "pass"
    # diagnostic measurements are still recorded, never hidden
    assert checks["FULL_SITE_ROAD_CLEARANCE"]["value"] is not None
    assert checks["FULL_SITE_BOUNDARY_SETBACK"]["value"] == ["SK-BLD-0010"]
    assert checks["FULL_SITE_BUILDING_OVERLAP"]["value"]


def test_full_site_checks_pass_on_the_real_full_site_layout():
    models = _models()
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            _real_full_site_layout(),
            models["road_layout"],
        )
    }
    assert set(checks) == FULL_SITE_CHECK_IDS
    for check_id, check in checks.items():
        assert check["status"] == "pass", check_id
    assert checks["FULL_SITE_NS_SPACING"]["value"] == pytest.approx(
        20.0, abs=0.01
    )
    assert checks["FULL_SITE_BOUNDARY_SETBACK"]["value"] == []
    assert checks["FULL_SITE_BUILDING_OVERLAP"]["value"] == []
    assert checks["FULL_SITE_ROAD_CLEARANCE"]["value"] >= 3.0


def test_full_site_checks_fail_on_a_shifted_real_row():
    models = _models()
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            _shifted_real_layout(),
            models["road_layout"],
        )
    }
    assert checks["FULL_SITE_NS_SPACING"]["status"] == "fail"
    assert checks["FULL_SITE_NS_SPACING"]["detail"]["violation_count"] > 0
    kinds = {
        item["kind"]
        for item in checks["FULL_SITE_NS_SPACING"]["detail"]["violations"]
    }
    assert "under_spacing" in kinds or "over_spacing" in kinds


# ------------------------------------------------- potential open space (not green)
def test_potential_open_space_account_is_not_designed_green():
    models = _models()
    green_layout = models["green_layout"]
    site_area = models["design_input"].site_area_m2
    full = green_layout.full_site_green
    assert isinstance(full, FullSiteGreenDesign)
    assert full.parcels, "the generated potential-open-space account has parcels"
    assert full.account_kind == POTENTIAL_OPEN_SPACE_CLASSIFICATION
    assert full.account_kind == "potential_open_space"
    assert full.area_m2 == pytest.approx(
        sum(item.area_m2 for item in full.parcels), rel=1e-12
    )
    assert full.ratio == pytest.approx(full.area_m2 / site_area, rel=1e-12)
    assert full.target_ratio == models["basis"].green_ratio_min == 0.30
    assert full.gap_m2 == pytest.approx(
        max(0.0, full.target_area_m2 - full.area_m2), abs=1e-9
    )
    # every parcel is potential open space, never designed green
    for parcel in full.parcels:
        assert parcel.classification == "potential_open_space"
        assert parcel.classification != "designed_green"
        assert parcel.area_m2 >= full.criteria["min_parcel_area_m2"]
        assert parcel.geometry.is_valid
        assert parcel.geometry.area == pytest.approx(parcel.area_m2, rel=1e-12)
    payload = full.to_dict()
    assert payload["account_kind"] == "potential_open_space"
    assert payload["participates_in_designed_green_ratio"] is False
    assert payload["potential_open_space_area_m2"] == pytest.approx(
        full.area_m2, rel=1e-12
    )
    assert payload["potential_open_space_ratio"] == pytest.approx(
        full.ratio, rel=1e-12
    )
    assert "designed_green_area_m2" not in payload
    assert "designed_green_ratio" not in payload
    assert full.criteria["account_kind"] == "potential_open_space"
    assert (
        full.criteria["participates_in_designed_green_ratio"] is False
    )
    report = designed_green_report(green_layout)
    assert report["ready"] is True
    assert report["account_kind"] == "potential_open_space"
    assert report["participates_in_designed_green_ratio"] is False
    assert report["value"] == pytest.approx(full.ratio, rel=1e-12)
    # the potential-open-space account does NOT make DESIGNED_GREEN_RATIO pass:
    # the check stays deferred on the legacy designed-green account
    checks = {item["id"]: item for item in models["consistency"].checks}
    check = checks["DESIGNED_GREEN_RATIO"]
    assert check["status"] == "deferred"
    assert check["value"] == pytest.approx(
        green_layout.designed_green_ratio, rel=1e-12
    )
    assert check["value"] < check["required"]
    detail = check["detail"]
    assert detail["open_space_account_kind"] == "potential_open_space"
    assert (
        detail["open_space_account_participates_in_designed_green_ratio"]
        is False
    )
    assert detail["open_space_account_area_m2"] == pytest.approx(
        full.area_m2, rel=1e-12
    )
    assert "potential open space" in check["message"]
    assert "not designed green" in check["message"].lower()


def test_potential_open_space_account_reports_gap_below_target():
    models = _models()
    green_layout = models["green_layout"]
    site_area = models["design_input"].site_area_m2
    target_area = 0.30 * site_area
    area = target_area - 1000.0
    fake = FullSiteGreenDesign(
        parcels=(),
        area_m2=area,
        ratio=area / site_area,
        target_ratio=0.30,
        target_area_m2=target_area,
        gap_m2=1000.0,
        gap_ratio=1000.0 / site_area,
        residual_area_m2=0.0,
        open_space_area_m2=area,
        criteria={},
    )
    report = designed_green_report(replace(green_layout, full_site_green=fake))
    assert report["ready"] is True
    assert report["ok"] is False
    assert report["account_kind"] == "potential_open_space"
    assert report["participates_in_designed_green_ratio"] is False
    assert report["value"] < 0.30
    assert report["gap_m2"] == pytest.approx(1000.0, abs=1e-9)
    assert report["gap_ratio"] == pytest.approx(1000.0 / site_area, rel=1e-12)
    # an account below the target is still not a designed-green verdict
    checks = {item["id"]: item for item in models["consistency"].checks}
    assert checks["DESIGNED_GREEN_RATIO"]["status"] == "deferred"
    assert GREEN_RATIO_NUMERICAL_EPSILON == 1e-9


# --------------------------------------------------------------- contract v9
def test_contract_v9_supersedes_v8_and_v8_is_marked_superseded():
    v9 = _load(V9)
    v8 = _load(V8)
    assert v9["schema_id"] == "dgcad.design-synthesis.v0.9"
    assert v9["status"] == "living_contract"
    assert v9["supersedes"] == "design-synthesis-v0.8.yaml"
    assert v8["schema_id"] == "dgcad.design-synthesis.v0.8"
    assert v8["status"] == "superseded"
    assert v8["superseded_by"] == "design-synthesis-v0.9.yaml"


def test_contract_v9_verification_count_order_and_check_id_mapping():
    required = _load(V9)["verification"]["required"]
    assert required == EXPECTED_VERIFICATION
    assert len(required) == 32
    assert len(set(required)) == len(required)
    design_names = [
        name for name in required if name not in DXF_LEVEL_ITEMS
    ]
    assert len(design_names) == 29
    assert [_check_id(name) for name in design_names] == (
        EXPECTED_DESIGN_CHECK_IDS
    )
    assert len(set(EXPECTED_DESIGN_CHECK_IDS)) == 29
    # 32 = 29 design checks + 3 DXF-level items
    assert len(required) == len(design_names) + 3


def test_contract_v9_matches_live_check_ids_and_order():
    checks = _models()["consistency"].checks
    live_ids = [check["id"] for check in checks]
    assert live_ids == EXPECTED_DESIGN_CHECK_IDS
    assert len(live_ids) == 29
    required = _load(V9)["verification"]["required"]
    design_names = [
        name for name in required if name not in DXF_LEVEL_ITEMS
    ]
    assert [_check_id(name) for name in design_names] == live_ids


def test_contract_v9_new_checks_are_bound_to_status_rules():
    required = _load(V9)["verification"]["required"]
    for name in (
        "full_site_boundary_setback",
        "full_site_building_overlap",
        "full_site_road_clearance",
        "full_site_north_south_spacing",
        "designed_green_ratio",
    ):
        assert name in required
    checks = {
        item["id"]: item for item in _models()["consistency"].checks
    }
    for check_id in FULL_SITE_CHECK_IDS:
        assert checks[check_id]["status"] in {"pass", "fail", "deferred"}
    assert checks["DESIGNED_GREEN_RATIO"]["status"] == "deferred"


def test_contract_v9_verification_rules_declare_full_site_rules():
    rules = " | ".join(_load(V9)["verification"]["rules"])
    assert "the full-site geometry checks are pass/fail only when the full-site layout is complete" in rules
    assert "no missing, unexpected or duplicate id" in rules
    assert "all building footprints must lie inside the published site boundary reduced by the declared boundary setback" in rules
    assert "any two building footprints may overlap by at most 0.01 m2" in rules
    assert "under-spacing and over-spacing are both recorded as violations" in rules
    assert "row-rhythm rule of this candidate row-layout strategy" in rules
    assert "not a regulatory or professional-compliance conclusion" in rules
    assert "every building footprint must be at least 3.0 m from every road corridor edge" in rules
    assert "an infeasible fixed-road state fails honestly" in rules
    # the full-site account is potential open space, not designed green
    assert "the full-site generated account is potential open space" in rules
    assert "potential open space is not designed green and does not enter the DESIGNED_GREEN_RATIO numerator" in rules
    assert "the sketch-evidence cluster/strip green account, the potential-open-space account and the unbuilt geometric union are three separate accounts" in rules
    assert "a deferred check is not a pass" in rules
    # the v0.8 blanket deferral of these checks must be gone
    assert "full-site road clearance is deferred until every group is designed" not in rules


def test_contract_v9_constraints_include_full_site_names():
    constraints = _load(V9)["constraints"]["required"]
    for name in (
        "full_site_boundary_setback",
        "full_site_building_overlap",
        "full_site_north_south_spacing",
        "full_site_road_clearance",
        "designed_green_ratio",
    ):
        assert name in constraints
    rules = " | ".join(_load(V9)["constraints"]["rules"])
    assert "designed_green_ratio stays deferred until a real designed green layer exists" in rules
    assert "the declared 20.0 m north-south row rhythm has a 0.01 m tolerance" in rules
    assert "row-rhythm rule of this candidate row-layout strategy" in rules
    assert "the 3.0 m road-corridor clearance uses a floating-point epsilon only" in rules
    assert "no missing, unexpected or duplicate id" in rules


def test_contract_v9_non_claims_drop_the_deferred_full_site_claims():
    non_claims = " | ".join(_load(V9)["non_claims"])
    assert "the full-site north-south spacing is deferred until each group is designed" not in non_claims
    assert "the full-site potential-open-space layer is an open-space allocation candidate" in non_claims
    assert "the full-site row layout is a schematic placement" in non_claims
    assert "the 20.0 m north-south row pitch is this candidate row-layout strategy's row rhythm" in non_claims


def test_full_site_ns_spacing_message_declares_candidate_row_rhythm():
    models = _models()
    checks = {
        item["id"]: item
        for item in full_site_checks(
            models["design_input"],
            models["basis"],
            _shifted_real_layout(),
            models["road_layout"],
        )
    }
    check = checks["FULL_SITE_NS_SPACING"]
    assert check["status"] == "fail"  # a shifted row is a rhythm violation
    assert "row-rhythm rule of this candidate row-layout strategy" in check["message"]
    assert "not a regulatory or professional-compliance conclusion" in check["message"]
    assert "design-basis assumption" in check["message"]
    detail = check["detail"]
    assert detail["rule_scope"] == FULL_SITE_ROW_PITCH_RULE_SCOPE
    assert detail["basis_assumption"] is True
    assert (
        detail["over_spacing_meaning"]
        == "row_rhythm_violation_not_regulatory_compliance"
    )


def test_evidence_gate_register_points_design_package_at_v09():
    gate = _load(GATE_REGISTER)
    design = [
        package
        for package in gate["packages"]
        if package["package_id"] == "EP-R1-DESIGN-001"
    ]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.9.yaml"

"""M4d-2a access semantics layering tests (L1-L4).

The delivered ``ROAD_ACCESS_COVERAGE`` is group-level external access; these
tests lock the four independent layers so that no layer can impersonate
another: L1 "groups served" must never be read as L3 "buildings front a road",
L2 internal roads stay not designed, and L4 driveways stay deferred even when
entrances are near a road.  All thresholds are the declared basis values; the
module only reads ``RoadAccessLayout`` / ``RoadLayout`` and never mutates them.
"""
from __future__ import annotations

from dataclasses import replace
from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
import yaml
from shapely.geometry import LineString, box

from dgcad_design import DesignBasis
from dgcad_design.access import (
    TERMINAL_DISTANCE_MAX_M,
    TERMINAL_DISTANCE_MIN_M,
    RoadAccessLayout,
    build_co_design_access,
)
from dgcad_design.access_semantics import (
    FRONTAGE_BAND_FAR,
    LAYER_ORDER,
    SCHEMA_ID,
    access_semantics_report,
)
from dgcad_design.buildings import BuildingLayout
from dgcad_design.intent import BuildingGroup, DesignIntent
from dgcad_design.parking import build_parking_layout
from dgcad_design.project import build_full_site_models
from dgcad_design.roads import RoadDesign, RoadLayout
from dgcad_design.topology import noded_road_topology

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE_PATH = ROOT / "fixtures" / "design" / "design-profile-001.yaml"


def load_basis() -> DesignBasis:
    return DesignBasis.from_dict(
        yaml.safe_load(BASIS_PATH.read_text(encoding="utf-8"))
    )


@lru_cache(maxsize=1)
def _models():
    """Real models: M4d-1 baseline (old access) and candidate A (rebuilt)."""
    basis = load_basis()
    models = build_full_site_models(CASE, BASIS_PATH, PROFILE_PATH)
    design_input = models["design_input"]
    intent = models["intent"]
    frozen_road = models["road_layout"]
    road_layout, road_access, _meta = build_co_design_access(
        design_input,
        basis,
        intent,
        models["building_layout"],
        frozen_road,
        candidate_id="A",
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    return basis, models, intent, road_layout, road_access, parking_layout


@lru_cache(maxsize=1)
def _candidate_a_report():
    basis, models, intent, road_layout, road_access, parking_layout = (
        _models()
    )
    return access_semantics_report(
        models["design_input"],
        intent,
        models["building_layout"],
        road_layout,
        road_access,
        parking_layout,
        basis=basis,
        green_layout=None,
        candidate_id="A",
    )


@lru_cache(maxsize=1)
def _baseline_report():
    basis, models, intent, _road_layout, _road_access, _parking = _models()
    return access_semantics_report(
        models["design_input"],
        intent,
        models["building_layout"],
        models["road_layout"],
        models["road_access"],
        models["parking_layout"],
        basis=basis,
        green_layout=models["green_layout"],
        candidate_id="M4D1-BASELINE",
    )


def test_four_layers_are_independent_and_never_merged():
    report = _candidate_a_report()
    assert report["schema_id"] == SCHEMA_ID
    assert report["no_combined_coverage"] is True
    assert "coverage" not in report
    assert "road_access_coverage" not in report
    assert tuple(report["layer_order"]) == LAYER_ORDER
    layers = report["layers"]
    assert set(layers) == set(LAYER_ORDER)
    for layer_id in LAYER_ORDER:
        layer = layers[layer_id]
        assert layer["layer"] == layer_id
        assert layer["status"]
        assert layer["label"]
        assert layer["scope"] in {"group", "building", "entrance"}
        assert isinstance(layer["claims"], dict)
        assert "coverage" not in layer["summary"]
    # statuses / labels are layer-specific, not a shared "coverage" field
    assert layers["l1_group_external_access"]["scope"] == "group"
    assert layers["l2_internal_group_roads"]["scope"] == "group"
    assert layers["l3_building_frontage"]["scope"] == "building"
    assert layers["l4_garage_driveway"]["scope"] == "entrance"
    assert len(
        {
            layers[key]["label"]
            for key in LAYER_ORDER
        }
    ) == 4


def test_l1_group_external_access_reports_group_level_only():
    road_access = _models()[4]
    report = _candidate_a_report()
    l1 = report["layers"]["l1_group_external_access"]
    assert l1["status"] == "designed"
    assert l1["label"] == "group_level_declared_access"
    assert l1["summary"]["groups_total"] == 17
    assert l1["summary"]["groups_served"] == 17
    assert l1["summary"]["group_coverage"] == pytest.approx(1.0)
    assert l1["summary"]["relation_error_count"] == 0
    assert l1["claims"]["access_scope"] == "group_level"
    assert l1["claims"]["claims_single_building_access"] is False
    assert l1["claims"]["claims_internal_group_roads"] is False
    assert l1["claims"]["claims_garage_driveway"] is False
    assert len(l1["groups"]) == 17
    for record in l1["groups"]:
        assert record["served"] is True
        assert record["declared"] is True
        assert record["terminal_band_ok"] is True
        assert record["serving_road_id"] is not None
        assert record["relation_errors"] == []
    # the L1 numbers are a read-only echo of the untouched RoadAccessLayout
    assert l1["summary"]["groups_served"] == road_access.groups_served
    assert l1["summary"]["relation_error_count"] == len(
        road_access.relation_errors
    )


def test_l2_internal_group_roads_stay_not_designed():
    report = _candidate_a_report()
    l2 = report["layers"]["l2_internal_group_roads"]
    assert l2["status"] == "not_designed"
    assert l2["label"] == "internal_group_roads"
    assert l2["summary"]["groups_with_internal_roads"] == 0
    assert l2["summary"]["internal_road_length_m"] == 0.0
    assert l2["claims"]["internal_roads_designed"] is False
    assert l2["claims"]["l1_connector_is_not_internal_road"] is True
    assert len(l2["groups"]) == 17
    assert all(
        record["status"] == "not_designed"
        and record["internal_road_count"] == 0
        for record in l2["groups"]
    )


def test_l3_is_geometry_only_for_all_55_buildings():
    report = _candidate_a_report()
    l3 = report["layers"]["l3_building_frontage"]
    assert l3["status"] == "geometry_measured"
    assert l3["label"] == "frontage_geometry_only"
    assert l3["claims"]["geometry_only"] is True
    assert l3["claims"]["entrance_designed"] is False
    assert l3["claims"]["address_assigned"] is False
    assert l3["claims"]["plot_access_designed"] is False
    buildings = l3["buildings"]
    assert len(buildings) == 55
    assert len({row["building_id"] for row in buildings}) == 55
    for row in buildings:
        assert row["distance_to_corridor_edge_m"] is not None
        assert row["distance_to_corridor_edge_m"] >= 0.0
        assert row["nearest_road_id"] is not None
        assert isinstance(row["fronts_road"], bool)
        assert row["frontage_band"] in {
            "within_sidewalk_width",
            "within_frontage_reserve",
            "close_setback_5_to_10_m",
            "far_setback_over_10_m",
        }
        assert isinstance(row["blocked_by_building_ids"], list)
        # green obstruction is unknown (not "unblocked") when no green layout
        assert row["blocked_by_green_ids"] is None
        # geometry only: no entrance / address / driveway fields are claimed
        assert "entrance" not in {key.lower() for key in row}
    summary = l3["summary"]
    assert summary["building_count"] == 55
    assert summary["group_count"] == 17
    assert summary["frontage_reserve_m"] == pytest.approx(
        load_basis().building_road_clearance_m
        + load_basis().sidewalk_width_m
    )
    assert summary["distance_stats_m"]["count"] == 55
    distances = [row["distance_to_corridor_edge_m"] for row in buildings]
    assert summary["distance_stats_m"]["min"] == pytest.approx(
        min(distances)
    )
    assert summary["distance_stats_m"]["max"] == pytest.approx(
        max(distances)
    )
    assert summary["fronts_road_count"] == sum(
        1 for row in buildings if row["fronts_road"]
    )
    assert len(l3["group_summary"]) == 17


def test_l1_full_coverage_does_not_imply_l3_frontage():
    report = _candidate_a_report()
    l1 = report["layers"]["l1_group_external_access"]
    l3 = report["layers"]["l3_building_frontage"]
    assert l1["summary"]["group_coverage"] == pytest.approx(1.0)
    # every group is served, yet not every building fronts a road and the
    # farthest building is far from any corridor edge
    assert l3["summary"]["fronts_road_count"] < l3["summary"]["building_count"]
    assert l3["summary"]["distance_stats_m"]["max"] > 10.0
    assert l3["summary"]["sidewalk_adjacent_count"] == 0
    # L1 must not be republished as a building-level statement
    assert "building" not in l1["label"]
    assert l1["scope"] == "group"
    assert l3["scope"] == "building"


def test_baseline_l1_zero_but_l3_still_measured():
    report = _baseline_report()
    l1 = report["layers"]["l1_group_external_access"]
    l3 = report["layers"]["l3_building_frontage"]
    assert l1["status"] == "not_designed"
    assert l1["summary"]["groups_served"] == 0
    assert l1["summary"]["group_coverage"] == pytest.approx(0.0)
    assert l1["summary"]["relation_error_count"] == 17
    # L3 is independent of L1: it is measured for all 55 buildings anyway
    assert l3["summary"]["building_count"] == 55
    assert len(l3["buildings"]) == 55
    assert l3["summary"]["distance_stats_m"]["max"] > 10.0


def test_l4_entrances_are_proximity_only_and_driveways_deferred():
    road_access = _models()[4]
    parking = _models()[5]
    report = _candidate_a_report()
    l4 = report["layers"]["l4_garage_driveway"]
    assert l4["status"] == "driveway_deferred"
    assert l4["label"] == "underground_garage_entrance_proximity"
    assert l4["claims"]["entrance_proximity_only"] is True
    assert l4["claims"]["driveway_designed"] is False
    assert l4["claims"]["garage_layout_designed"] is False
    assert l4["summary"]["entrance_count"] == 5
    assert l4["summary"]["entrance_count"] == len(road_access.entrances)
    assert l4["summary"]["parking_entrance_count"] == len(parking.entrances)
    assert l4["summary"]["driveway_designed_count"] == 0
    assert len(l4["entrances"]) == 5
    for row in l4["entrances"]:
        assert row["driveway_designed"] is False
        assert isinstance(row["proximity_connected"], bool)
        assert row["nearest_road_id"] is not None
    assert l4["summary"]["proximity_connected_count"] == sum(
        1 for row in l4["entrances"] if row["proximity_connected"]
    )


def test_report_does_not_mutate_or_rethreshold_road_access():
    basis, models, intent, road_layout, road_access, parking = _models()
    road_access_before = road_access.to_dict()
    road_layout_before = road_layout.to_dict()
    access_semantics_report(
        models["design_input"],
        intent,
        models["building_layout"],
        road_layout,
        road_access,
        parking,
        basis=basis,
    )
    assert road_access.to_dict() == road_access_before
    assert road_layout.to_dict() == road_layout_before
    # the declared terminal band constants are untouched
    assert (TERMINAL_DISTANCE_MIN_M, TERMINAL_DISTANCE_MAX_M) == (3.4, 3.5)


def _synthetic_far_case():
    """Two buildings: one 3 m from a road, one 100+ m away, plus green block."""
    basis = load_basis()
    template = _models()[1]["building_layout"].buildings[0]
    near = replace(
        template,
        building_id="SYN-NEAR",
        unit_count=2,
        households=22,
        footprint=box(10.0, 14.0, 30.0, 24.0),
        design_centroid=(20.0, 19.0),
        label_anchor=(20.0, 19.0),
    )
    far = replace(
        template,
        building_id="SYN-FAR",
        unit_count=2,
        households=22,
        footprint=box(120.0, 120.0, 140.0, 130.0),
        design_centroid=(130.0, 125.0),
        label_anchor=(130.0, 125.0),
    )
    building_layout = BuildingLayout(
        buildings=(near, far),
        focus_buildings=(),
        rows=(),
        green_strips=(),
    )
    near_line = LineString([(0.0, 5.0), (200.0, 5.0)])
    road = RoadDesign(
        edge_id="SYN-ROAD",
        class_name="main",
        width_m=12.0,
        centerline=near_line,
        corridor=near_line.buffer(
            6.0, cap_style="flat", join_style="mitre"
        ),
        is_new_connector=False,
        reason="synthetic road",
        source_edge_ids=(),
    )
    road_layout = RoadLayout(
        roads=(road,),
        corridor_union=road.corridor,
        sidewalk_union=box(0.0, 0.0, 0.0, 0.0),
        junction_nodes=(),
        dead_end_nodes=(),
        corridor_generator="synthetic",
        not_professional_alignment=True,
        corridor_union_pieces=1,
        noded_topology=noded_road_topology((road,), ()),
        explicit_junctions=(),
        simplification={},
    )
    group = BuildingGroup(
        group_id="SYN-G1",
        building_ids=("SYN-NEAR", "SYN-FAR"),
        unit_count=4,
        households=44,
        centroid=(75.0, 70.0),
        bbox=(10.0, 14.0, 140.0, 130.0),
        green_ids=(),
        main_road_distance_m=None,
    )
    intent = DesignIntent(
        groups=(group,),
        road_hierarchy={},
        principles=(),
        focus_group_id="SYN-G1",
        focus_bbox=(10.0, 14.0, 140.0, 130.0),
        focus_building_ids=("SYN-NEAR", "SYN-FAR"),
        focus_green_ids=(),
        focus_road_ids=(),
        focus_subgroups={},
    )
    design_input = SimpleNamespace(
        case_id="SYNTH-ACCESS-SEMANTICS",
        site_boundary=box(0.0, 0.0, 200.0, 200.0),
    )
    road_access = RoadAccessLayout(
        groups=(),
        entrances=(),
        dead_ends=(),
    )
    parking_layout = SimpleNamespace(
        entrances=(), garage_layout="not_designed"
    )
    green_layout = SimpleNamespace(
        greens=(
            SimpleNamespace(
                green_id="SYN-GREEN-01",
                classification="green_strip",
                geometry=box(0.0, 11.5, 40.0, 13.5),
            ),
        )
    )
    return (
        basis,
        design_input,
        intent,
        building_layout,
        road_layout,
        road_access,
        parking_layout,
        green_layout,
    )


def test_synthetic_building_far_from_road_is_reported_honestly():
    (
        basis,
        design_input,
        intent,
        building_layout,
        road_layout,
        road_access,
        parking_layout,
        green_layout,
    ) = _synthetic_far_case()
    report = access_semantics_report(
        design_input,
        intent,
        building_layout,
        road_layout,
        road_access,
        parking_layout,
        basis=basis,
        green_layout=green_layout,
        candidate_id="SYNTH",
    )
    l3 = report["layers"]["l3_building_frontage"]
    rows = {row["building_id"]: row for row in l3["buildings"]}
    near_row = rows["SYN-NEAR"]
    far_row = rows["SYN-FAR"]
    # the near building is 3 m from the pavement edge -> inside the reserve
    assert near_row["distance_to_corridor_edge_m"] == pytest.approx(3.0)
    assert near_row["fronts_road"] is True
    assert near_row["frontage_band"] == "within_frontage_reserve"
    assert near_row["blocked_by_green_ids"]  # green strip crosses frontage
    # the far building is honestly reported as far and not fronting
    assert far_row["distance_to_corridor_edge_m"] > 100.0
    assert far_row["fronts_road"] is False
    assert far_row["frontage_band"] == FRONTAGE_BAND_FAR
    assert far_row["blocked_by_building_ids"] == []
    assert l3["summary"]["building_count"] == 2
    assert l3["summary"]["fronts_road_count"] == 1
    assert l3["summary"]["distance_stats_m"]["max"] > 100.0
    # L1 has no declared group access here: geometry frontage never fakes it
    l1 = report["layers"]["l1_group_external_access"]
    assert l1["status"] == "not_designed"
    assert l1["summary"]["groups_total"] == 1
    assert l1["summary"]["groups_in_access_evidence"] == 0
    assert l1["summary"]["groups_served"] == 0
    assert l1["summary"]["group_coverage"] == pytest.approx(0.0)
    # L4 has no entrances -> not applicable, still no driveway claim
    l4 = report["layers"]["l4_garage_driveway"]
    assert l4["status"] == "not_applicable"
    assert l4["summary"]["driveway_designed_count"] == 0

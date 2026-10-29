from __future__ import annotations

import hashlib
import json
from pathlib import Path

import ezdxf
import pytest
import yaml

from dgcad_design import (
    DesignBasis,
    build_design_intent,
    load_design_input,
    run_design_synthesis,
)
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.consistency import check_design
from dgcad_design.green import build_green_layout
from dgcad_design.parking import build_parking_layout
from dgcad_design.roads import build_road_layout
from dgcad_e2e import scan_dxf_privacy

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
PROFILE = ROOT / "fixtures" / "design" / "design-profile-001.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"


def load_basis() -> DesignBasis:
    return DesignBasis.from_dict(
        yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    )


def test_basis_math_hits_the_declared_constraints():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    assert basis.basis_id == "design-assumption-v0.2"
    assert len(basis.parameter_sources) == 21
    assert design_input.site_area_m2 == pytest.approx(
        204122.7864634952, rel=1e-9
    )
    assert design_input.staircase_count == 109
    assert design_input.facility_count == 1
    households = basis.households(109)
    assert households == 2398
    assert basis.parking_spaces(households) == 2398
    assert basis.required_entrances(2398) == 5
    far = basis.far(design_input.site_area_m2, 109)
    assert 1.55 <= far <= 1.60
    assert far == pytest.approx(1.5654107291796402, rel=1e-9)
    assert basis.building_width(3) == 72.0
    assert basis.building_height_m() == 33.0
    assert basis.human_confirmed is False
    assert basis.design_authority == "rule_derived"


def test_basis_rejects_human_confirmation_and_short_spacing():
    data = yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    data["human_confirmed"] = True
    with pytest.raises(ValueError):
        DesignBasis.from_dict(data)
    data = yaml.safe_load(BASIS.read_text(encoding="utf-8"))
    data["north_south_spacing_m"] = 19.0
    with pytest.raises(ValueError):
        DesignBasis.from_dict(data)


def test_design_input_loads_all_site_objects():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    assert len(design_input.buildings) == 55
    assert len(design_input.greens) == 12
    assert len(design_input.entrances) == 3
    assert len(design_input.roads) == 333
    assert len(design_input.road_graph.nodes) == 309
    assert len(design_input.road_graph.edges) == 333
    assert design_input.source_manifest["source_sketch_sha256"]


def test_intent_groups_and_focus_region():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    assert len(intent.groups) >= 10
    focus = next(
        group
        for group in intent.groups
        if group.group_id == intent.focus_group_id
    )
    assert focus.building_ids
    assert focus.unit_count >= 19
    assert intent.focus_building_ids == focus.building_ids
    assert intent.focus_bbox[0] < intent.focus_bbox[2]
    assert intent.focus_road_ids
    assert intent.principles
    assert intent.road_hierarchy["main_edges"] == 65


def test_focus_block_is_buildable_and_road_clear():
    basis = load_basis()
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    rect = find_focus_design_rect(design_input, intent, basis)
    assert rect is not None
    minx, miny, maxx, maxy = rect
    assert maxx - minx >= 120.0
    assert maxy - miny >= 90.0
    assert design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    ).contains(
        __import__("shapely.geometry", fromlist=["box"]).box(*rect)
    )


def test_design_synthesis_end_to_end(tmp_path):
    summary = run_design_synthesis(
        CASE, BASIS, PROFILE, tmp_path / "design"
    )
    metrics = summary["metrics"]
    checks = {
        check["id"]: check
        for check in summary["consistency"]["checks"]
    }
    assert summary["status"] == "autonomous_design_draft"
    assert summary["design_authority"] == "rule_derived"
    assert summary["human_confirmed"] is False
    assert 1.55 <= metrics["far"] <= 1.60
    assert metrics["parking_spaces"] >= metrics["households"]
    assert metrics["parking_entrances"] >= metrics[
        "parking_entrances_required"
    ]
    assert metrics["focus_min_ns_gap_m"] >= 20.0 - 1e-6
    # honesty semantics: candidate open space != designed green;
    # strict unbuilt is a geometric union; capacity is an assumption
    assert metrics["candidate_open_space_ratio"] == pytest.approx(
        0.616391083609783, rel=1e-12
    )
    assert metrics["candidate_open_space_area_m2"] == pytest.approx(
        125819.46553768215, rel=1e-9
    )
    assert metrics["unbuilt_ratio"] == pytest.approx(
        0.6407354465472117, rel=1e-9
    )
    assert metrics["unbuilt_area_m2"] == pytest.approx(
        130788.70473514873, rel=1e-9
    )
    assert metrics["unbuilt_ratio"] > metrics["candidate_open_space_ratio"]
    assert metrics["open_space_filters"] == {
        "boundary_setback_m": 5.0,
        "obstacle_buffer_m": 0.5,
        "min_supplementary_polygon_m2": 100.0,
    }
    assert metrics["designed_green_ratio"] == pytest.approx(
        0.06538561066069971, rel=1e-9
    )
    assert (
        metrics["designed_green_ratio"]
        < metrics["candidate_open_space_ratio"]
    )
    assert metrics["parking_assumed_nominal_capacity"] == 1000
    assert metrics["parking_capacity_required"] == 2398
    assert metrics["garage_layout"] == "not_designed"
    assert metrics["road_noded_component_count"] == 1
    assert metrics["corridor_union_pieces"] == 1
    assert metrics["max_endpoint_gap_m"] == 0.0
    assert metrics["road_topology"]["component_count"] == 1
    assert (
        sum(
            1
            for item in metrics["road_topology"]["connector_states"]
            if item["state"] == "crossing_only"
        )
        == 0
    )
    assert summary["road_topology"]["schema_id"] == "dgcad.design-road-topology.v0.1"
    assert summary["design_roads"]["road_count"] == 44
    # M4c-1e: declared access relations, not nearest-endpoint inference
    assert metrics["road_access_coverage"] == pytest.approx(1.0)
    assert metrics["road_groups_total"] == metrics["road_groups_served"] == 17
    assert metrics["road_groups_unserved"] == []
    assert metrics["road_relation_error_count"] == 0
    assert metrics["dead_end_justified_count"] == 17
    assert metrics["dead_end_unfinished_count"] == 1
    assert metrics["dead_end_unclassified_count"] == 1
    assert metrics["dead_end_unresolved_count"] == 0
    assert metrics["dead_end_resolved_count"] == 7
    assert metrics["entrance_proximity_connected_count"] == 2
    assert metrics["entrance_driveway_designed_count"] == 0
    assert metrics["entrance_count"] == 5
    assert metrics["main_road_building_overlap_m2"] == pytest.approx(
        0.0, abs=0.01
    )
    assert metrics["main_road_building_overlap_before_m2"] == pytest.approx(
        38.19068149970835, rel=1e-12
    )
    assert metrics["main_road_overlap_before_records_m2"] == pytest.approx(
        34.421783197612406, rel=1e-12
    )
    assert metrics[
        "main_road_overlap_before_boundary_replaced_m2"
    ] == pytest.approx(3.768898302095937, rel=1e-9)
    assert metrics["main_road_building_overlap_before_m2"] == pytest.approx(
        metrics["main_road_overlap_before_records_m2"]
        + metrics["main_road_overlap_before_boundary_replaced_m2"]
    )
    assert metrics["main_road_building_overlap_status"] == "resolved"
    assert metrics["main_alignment_adjusted_count"] == 1
    assert metrics["main_alignment_max_displacement_m"] > 0.0
    assert metrics["dead_end_unresolved_count"] == 0
    assert metrics["dead_end_resolved_count"] == 7
    access = summary["road_access"]
    assert access["road_access_coverage"] == pytest.approx(1.0)
    assert access["groups_served"] == 17
    assert access["relation_error_count"] == 0
    assert all(item["served"] for item in access["groups"])
    assert all(item["declared"] for item in access["groups"])
    assert all(item["served_by_relation"] for item in access["groups"])
    group_by_id = {item["group_id"]: item for item in access["groups"]}
    assert group_by_id["G-08"]["access_road_id"] == "BR-G-08"
    assert group_by_id["G-13"]["access_road_id"] == "BR-G-13"
    assert group_by_id["G-12"]["access_road_id"] == "ACC-G-12"
    for item in access["groups"]:
        if item["group_id"] == "G-01":
            continue
        assert 3.4 - 1e-9 <= item["terminal_centerline_distance_m"] <= 3.5 + 1e-9
    assert group_by_id["G-08"]["terminal_corridor_edge_clearance_m"] == (
        pytest.approx(0.0, abs=1e-6)
    )
    assert group_by_id["G-12"]["terminal_corridor_edge_clearance_m"] == (
        pytest.approx(1.5, abs=0.01)
    )
    assert summary["main_road_building_overlap"]["status"] == "resolved"
    assert summary["main_road_building_overlap"]["area_m2"] == pytest.approx(
        0.0, abs=0.01
    )
    assert summary["main_road_building_overlap"]["conflicts"] == []
    assert len(summary["road_alignment"]["records"]) == 1
    assert len(summary["road_alignment"]["dead_end_resolutions"]) == 7
    assert summary["road_alignment"]["main_overlap_status"] == "resolved"
    assert summary["road_alignment"]["main_overlap_after_m2"] == pytest.approx(
        0.0, abs=0.01
    )
    assert summary["full_site_road_clearance"]["status"] == "deferred"
    assert len(checks) == 29
    pass_ids = {
        "FOCUS_NS_SPACING",
        "FOCUS_BOUNDARY_SETBACK",
        "FOCUS_BUILDING_OVERLAP",
        "FOCUS_ROAD_CLEARANCE",
        "ROAD_CONNECTIVITY",
        "ROAD_ACCESS_COVERAGE",
        "ROAD_BOUNDARY_CONTAINMENT",
        "MAIN_ROAD_BUILDING_OVERLAP",
        "DEAD_END_RESOLUTION",
    }
    info_ids = {
        "FAR_ARITHMETIC_SCENARIO",
        "PARKING_REQUIREMENT_ARITHMETIC",
        "PARKING_ENTRANCE_COUNT",
        "PARKING_ENTRANCE_PROXIMITY",
        "UNIT_COUNT_BASIS_INVARIANT",
        "ROAD_CORRIDOR_COVERAGE",
        "ROAD_ALIGNMENT_EVIDENCE",
        "DEAD_END_JUSTIFICATION",
        "ROAD_WIDTH_ASSIGNMENT",
        "CANDIDATE_OPEN_SPACE_RATIO",
        "UNBUILT_RATIO",
    }
    deferred_ids = {
        "PARKING_CAPACITY",
        "PARKING_DRIVEWAY_CONNECTION",
        "PARKING_LAYOUT",
        "DESIGNED_GREEN_RATIO",
        "FULL_SITE_BOUNDARY_SETBACK",
        "FULL_SITE_BUILDING_OVERLAP",
        "FULL_SITE_ROAD_CLEARANCE",
        "FULL_SITE_NS_SPACING",
        "FAR_FINAL_VERIFICATION",
    }
    assert pass_ids | info_ids | deferred_ids == set(checks)
    assert {name for name, item in checks.items() if item["status"] == "pass"} == pass_ids
    assert {name for name, item in checks.items() if item["status"] == "info"} == info_ids
    assert {
        name for name, item in checks.items() if item["status"] == "deferred"
    } == deferred_ids
    assert checks["MAIN_ROAD_BUILDING_OVERLAP"]["status"] == "pass"
    assert checks["MAIN_ROAD_BUILDING_OVERLAP"]["value"] == pytest.approx(
        0.0, abs=0.01
    )
    assert checks["DEAD_END_RESOLUTION"]["status"] == "pass"
    assert checks["DEAD_END_RESOLUTION"]["value"] == "0 unresolved"
    assert checks["ROAD_ALIGNMENT_EVIDENCE"]["status"] == "info"
    assert checks["ROAD_ALIGNMENT_EVIDENCE"]["value"] == 1
    assert checks["PARKING_DRIVEWAY_CONNECTION"]["status"] == "deferred"
    assert checks["FULL_SITE_ROAD_CLEARANCE"]["status"] == "deferred"
    for name in ("FAR_ARITHMETIC_SCENARIO", "UNIT_COUNT_BASIS_INVARIANT"):
        assert checks[name]["derived_from"] == "design_basis_arithmetic"
    assert checks["ROAD_WIDTH_ASSIGNMENT"]["derived_from"] == "design_basis_assignment"
    assert checks["FAR_FINAL_VERIFICATION"]["value"] is None
    assert checks["DESIGNED_GREEN_RATIO"]["value"] == pytest.approx(
        metrics["designed_green_ratio"]
    )
    assert checks["CANDIDATE_OPEN_SPACE_RATIO"]["value"] == pytest.approx(
        metrics["candidate_open_space_ratio"]
    )
    assert checks["UNBUILT_RATIO"]["value"] == pytest.approx(
        metrics["unbuilt_ratio"]
    )
    basis_block = summary["design_basis"]
    assert basis_block["basis_id"] == "design-assumption-v0.2"
    assert basis_block["design_authority"] == "rule_derived"
    assert basis_block["human_confirmed"] is False
    assert basis_block["provenance_authentication"] == "declarative"
    assert len(basis_block["parameter_sources"]) == 21
    assert all(
        item["confirmed"] is False
        for item in basis_block["parameter_sources"].values()
    )
    assert sum(basis_block["authority_counts"].values()) == 21
    assert "agent_assumption" in basis_block["authority_counts"]
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["confirmation_scopes"] == ["design_draft"]
    assert summary["cad_ir_validation"]["verdict"] == (
        "pass_with_scope_limits"
    )
    assert {
        issue["code"] for issue in summary["cad_ir_validation"]["issues"]
    } == {"UNKNOWN_HEIGHT_ALLOWED"}
    assert summary["privacy"]["ok"] is True
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0

    dxf_path = tmp_path / "design" / "design-proposal.dxf"
    doc = ezdxf.readfile(dxf_path)
    layers = {layer.dxf.name for layer in doc.layers}
    for layer in (
        "A-BUILDING-OUTLINE",
        "A-UNIT-LINE",
        "C-ROAD-MAIN",
        "C-ROAD-BRANCH",
        "C-ROAD-ACCESS",
        "C-SIDEWALK",
        "L-GREEN",
        "A-TITLE",
        "A-LEGEND",
        "A-NORTH",
        "A-SCALE",
        "A-KEYPLAN",
    ):
        assert layer in layers
    texts = [
        entity.dxf.text
        for entity in doc.modelspace()
        if entity.dxftype() == "TEXT"
    ]
    assert any("AUTONOMOUS DESIGN DRAFT" in text for text in texts)
    assert any("NOT HUMAN-CONFIRMED" in text for text in texts)
    assert any("FAR 1.565" in text for text in texts)
    assert any("SK-BLD-0007" in text for text in texts)
    assert not any("human_confirmed" in text for text in texts)

    draft = json.loads(
        (tmp_path / "design" / "draft-manifest.json").read_text(
            encoding="utf-8"
        )
    )
    assert draft["status"] == "autonomous_draft"
    assert draft["human_confirmed"] is False
    assert draft["design_authority"] == "rule_derived"
    scene = json.loads(
        (tmp_path / "design" / "scene-snapshot.json").read_text(
            encoding="utf-8"
        )
    )
    assert scene["world"] == "proposal_preview"
    assert scene["objects"]
    assert {
        obj["authority_state"] for obj in scene["objects"]
    } == {"rule_derived"}


def test_design_diff_records_design_changes_and_drops():
    summary = json.loads(
        (EVIDENCE / "design-summary.json").read_text(encoding="utf-8")
    )
    diff = summary["diff"]
    assert len(diff["buildings"]) == 7
    assert diff["dropped_focus_building_ids"] == [
        "SK-BLD-0038",
        "SK-BLD-0061",
    ]
    assert diff["changed"]
    assert diff["preserved"]
    assert diff["roads"]["corridor_generator"] == (
        "round_buffer_hierarchy_v0.1"
    )
    assert diff["roads"]["not_professional_alignment"] is True
    assert diff["parking"]["proposed_entrances"] == 2
    assert diff["parking"]["existing_entrances"] == 3
    assert diff["parking"]["assumed_nominal_capacity_spaces"] == 1000
    assert diff["parking"]["garage_layout"] == "not_designed"
    assert diff["green"]["candidate_open_space_ratio"] == pytest.approx(
        0.616391083609783, rel=1e-12
    )
    assert diff["green"]["unbuilt_ratio"] == pytest.approx(
        0.6407354465472117, rel=1e-9
    )
    assert diff["green"]["open_space_filters"] == {
        "boundary_setback_m": 5.0,
        "obstacle_buffer_m": 0.5,
        "min_supplementary_polygon_m2": 100.0,
    }
    assert diff["green"]["designed_green_ratio"] == pytest.approx(
        0.06538561066069971, rel=1e-9
    )
    assert diff["green"]["designed_green_area_m2"] < (
        diff["green"]["candidate_open_space_area_m2"]
    )


def test_committed_design_evidence_is_consistent():
    summary = json.loads(
        (EVIDENCE / "design-summary.json").read_text(encoding="utf-8")
    )
    manifest = json.loads(
        (EVIDENCE / "readback-manifest.json").read_text(encoding="utf-8")
    )
    privacy = scan_dxf_privacy(EVIDENCE / "design-proposal.dxf")
    assert summary["status"] == "autonomous_design_draft"
    assert summary["human_confirmed"] is False
    assert summary["design_authority"] == "rule_derived"
    assert summary["readback"]["verdict"] == "pass"
    assert summary["readback"]["confirmation_scopes"] == ["design_draft"]
    assert manifest["confirmation_scopes"] == ["design_draft"]
    assert summary["dxf"]["audit_errors"] == 0
    assert summary["dxf"]["audit_fixes"] == 0
    assert summary["focus_design_rect"] is not None
    assert summary["diff"]["focus_design_rect"] == summary["focus_design_rect"]
    checks = {check["id"]: check for check in summary["consistency"]["checks"]}
    assert len(checks) == 29
    assert checks["DESIGNED_GREEN_RATIO"]["status"] == "deferred"
    assert checks["PARKING_CAPACITY"]["status"] == "deferred"
    assert checks["PARKING_LAYOUT"]["status"] == "deferred"
    assert checks["FAR_FINAL_VERIFICATION"]["status"] == "deferred"
    assert checks["CANDIDATE_OPEN_SPACE_RATIO"]["status"] == "info"
    assert checks["UNBUILT_RATIO"]["status"] == "info"
    assert checks["ROAD_ACCESS_COVERAGE"]["status"] == "pass"
    assert checks["PARKING_ENTRANCE_PROXIMITY"]["status"] == "info"
    assert checks["PARKING_DRIVEWAY_CONNECTION"]["status"] == "deferred"
    assert checks["MAIN_ROAD_BUILDING_OVERLAP"]["status"] == "pass"
    assert checks["MAIN_ROAD_BUILDING_OVERLAP"]["value"] == pytest.approx(
        0.0, abs=0.01
    )
    assert checks["FULL_SITE_ROAD_CLEARANCE"]["status"] == "deferred"
    assert checks["DEAD_END_JUSTIFICATION"]["status"] == "info"
    assert checks["DEAD_END_RESOLUTION"]["status"] == "pass"
    assert checks["DEAD_END_RESOLUTION"]["value"] == "0 unresolved"
    assert checks["ROAD_ALIGNMENT_EVIDENCE"]["status"] == "info"
    assert checks["ROAD_ALIGNMENT_EVIDENCE"]["value"] == 1
    assert {
        name for name, item in checks.items() if item["status"] == "pass"
    } == {
        "FOCUS_NS_SPACING",
        "FOCUS_BOUNDARY_SETBACK",
        "FOCUS_BUILDING_OVERLAP",
        "FOCUS_ROAD_CLEARANCE",
        "ROAD_CONNECTIVITY",
        "ROAD_ACCESS_COVERAGE",
        "ROAD_BOUNDARY_CONTAINMENT",
        "MAIN_ROAD_BUILDING_OVERLAP",
        "DEAD_END_RESOLUTION",
    }
    assert summary["metrics"]["candidate_open_space_ratio"] == pytest.approx(
        0.616391083609783, rel=1e-12
    )
    assert summary["metrics"]["unbuilt_ratio"] == pytest.approx(
        0.6407354465472117, rel=1e-9
    )
    assert summary["metrics"]["designed_green_ratio"] == pytest.approx(
        0.06538561066069971, rel=1e-9
    )
    assert summary["metrics"]["parking_assumed_nominal_capacity"] == 1000
    assert summary["metrics"]["parking_capacity_required"] == 2398
    assert len(summary["design_basis"]["parameter_sources"]) == 21
    assert summary["design_basis"]["provenance_authentication"] == (
        "declarative"
    )
    assert all(
        item["confirmed"] is False
        for item in summary["design_basis"]["parameter_sources"].values()
    )
    assert hashlib.sha256(
        (EVIDENCE / "design-proposal.dxf").read_bytes()
    ).hexdigest() == summary["dxf"]["sha256"] == manifest["dxf_sha256"]
    assert privacy["ok"] is True
    assert (EVIDENCE / "design-preview.png").is_file()
    assert (EVIDENCE / "design-basis.yaml").is_file()
    assert (EVIDENCE / "design-diff.json").is_file()
    assert (EVIDENCE / "design-intent.json").is_file()


class _RoadDouble:
    """Minimal RoadDesign-compatible object for evidence recomputation."""

    def __init__(self, feature: dict):
        from shapely.geometry import shape

        properties = feature["properties"]
        geometry = feature["geometry"]
        assert geometry["type"] == "LineString"
        self.edge_id = properties["edge_id"]
        self.class_name = properties["class_name"]
        self.centerline = shape(geometry)
        self.start_junction_id = properties["start_junction_id"]
        self.end_junction_id = properties["end_junction_id"]


def _junction_records_from_features(
    payload: dict,
) -> tuple[dict, ...]:
    """Read the explicit junction records embedded in the committed artefact."""
    junctions = tuple(dict(item) for item in payload["junctions"])
    assert payload["junction_count"] == len(junctions) == 24
    for junction in junctions:
        assert set(junction) == {"id", "x", "y", "road_ids"}
        # each junction joins exactly two roads (main/branch or branch/loop)
        assert len(junction["road_ids"]) == 2
    return junctions


def test_committed_design_roads_artifact_recomputes_topology():
    from dgcad_design.topology import noded_road_topology, topology_violations

    summary = json.loads(
        (EVIDENCE / "design-summary.json").read_text(encoding="utf-8")
    )
    roads_path = EVIDENCE / "design-roads.geojson"
    assert roads_path.is_file()
    payload = json.loads(roads_path.read_text(encoding="utf-8"))
    features = payload["features"]
    assert len(features) == 44 == payload["road_count"]
    assert payload["road_access_coverage"] == pytest.approx(1.0)
    assert payload["road_access_relation_error_count"] == 0
    assert payload["main_road_building_overlap"]["status"] == "resolved"
    assert payload["main_road_building_overlap"]["area_m2"] == pytest.approx(
        0.0, abs=0.01
    )
    assert len(payload["main_alignment_records"]) == 1
    assert len(payload["dead_end_resolution_records"]) == 7
    assert payload["road_building_overlap_m2_main_before"] == pytest.approx(
        summary["metrics"]["main_road_building_overlap_before_m2"]
    )
    assert payload["road_building_overlap_m2_main_after"] == pytest.approx(
        summary["metrics"]["main_road_building_overlap_m2"]
    )
    assert payload["road_building_overlap_m2_new_access"] == pytest.approx(
        summary["metrics"]["road_building_overlap_m2_new_access"]
    )
    assert payload["road_building_overlap_m2_total_after"] == pytest.approx(
        summary["metrics"]["road_building_overlap_m2_total"]
    )
    assert payload["road_building_overlap_m2_total_after"] == pytest.approx(
        payload["road_building_overlap_m2_new_access"]
        + payload["road_building_overlap_m2_main_after"]
    )
    assert payload[
        "road_building_overlap_m2_main_before"
    ] == pytest.approx(
        payload["road_building_overlap_m2_alignment_records_before"]
        + payload["road_building_overlap_m2_boundary_replaced_before"]
    )
    assert payload[
        "road_building_overlap_m2_alignment_records_before"
    ] == pytest.approx(
        summary["metrics"]["main_road_overlap_before_records_m2"]
    )
    assert payload[
        "road_building_overlap_m2_boundary_replaced_before"
    ] == pytest.approx(
        summary["metrics"]["main_road_overlap_before_boundary_replaced_m2"]
    )
    declared_groups = [
        group_id
        for feature in features
        for group_id in feature["properties"]["serves_group_ids"]
    ]
    assert len(declared_groups) == 17
    assert sorted(declared_groups) == sorted(
        item["group_id"] for item in summary["road_access"]["groups"]
    )
    for feature in features:
        properties = feature["properties"]
        if properties["serves_group_ids"]:
            assert properties["access_terminal_xy"] is not None
        else:
            assert properties["access_terminal_xy"] is None
    assert len(payload["group_access"]) == 17
    assert all(item["served"] for item in payload["group_access"])
    assert all(item["declared"] for item in payload["group_access"])
    assert len(payload["dead_end_justification"]) == (
        summary["metrics"]["dead_end_justified_count"]
        + summary["metrics"]["dead_end_unfinished_count"]
        + summary["metrics"]["dead_end_unclassified_count"]
    )
    assert hashlib.sha256(roads_path.read_bytes()).hexdigest() == (
        summary["design_roads"]["sha256"]
    )
    roads = [_RoadDouble(feature) for feature in features]
    junctions = _junction_records_from_features(payload)
    topology = noded_road_topology(roads, junctions)
    assert topology.component_count == 1
    assert topology.road_count == 44
    assert topology.explicit_junction_count == 24
    # the endpoint-gap check must be a real measurement from committed evidence,
    # not the empty-set default: junction records carry both member roads.
    assert topology.max_endpoint_gap_m == 0.0
    assert topology_violations(topology) == ()
    # JSON round-trip normalises tuple fields and integer histogram keys
    assert json.loads(json.dumps(topology.to_dict(), sort_keys=True)) == (
        summary["road_topology"]
    )
    classes = sorted({feature["properties"]["class_name"] for feature in features})
    assert classes == ["access", "branch", "main"]

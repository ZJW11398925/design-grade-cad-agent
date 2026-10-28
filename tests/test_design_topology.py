"""Exact-coordinate noded topology tests for the design road network (M4c-1a).

Positive tests build the real CASE-SKETCH-001 R1 design through the committed
pipeline (same call sequence as ``experiments/m4c0/exp_c_collaborative.py``) and
assert the repaired network is exactly connected.  Negative tests are synthetic
networks that must fail closed: split branch, 1e-12 m endpoint gap, a
"repair" done only with snap/precision/rounding, a crossing without shared
vertex, and an isolated closed ring.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from types import SimpleNamespace

import pytest
from shapely.geometry import LineString
from shapely.ops import snap
from shapely import set_precision

from dgcad_design import DesignBasis, build_design_intent, load_design_input
from dgcad_design.buildings import (
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.roads import build_road_layout
from dgcad_design.topology import (
    ENDPOINT_GAP_TOLERANCE_M,
    REQUIRED_FIELDS,
    SCHEMA_ID,
    VIOLATION_COMPONENT_COUNT,
    VIOLATION_CROSSING_ONLY,
    VIOLATION_UNDECLARED_RING,
    noded_road_topology,
    topology_violations,
)

ROOT = Path(__file__).resolve().parents[1]
CASE = ROOT / "docs" / "e2e" / "sketch-001"
BASIS = ROOT / "fixtures" / "design" / "design-basis-001.yaml"
TOPOLOGY_SOURCE = ROOT / "src" / "dgcad_design" / "topology.py"


def _fake_road(
    edge_id: str,
    class_name: str,
    coords: list[tuple[float, float]],
    *,
    start_junction_id: str | None = None,
    end_junction_id: str | None = None,
) -> SimpleNamespace:
    return SimpleNamespace(
        edge_id=edge_id,
        class_name=class_name,
        centerline=LineString(coords),
        start_junction_id=start_junction_id,
        end_junction_id=end_junction_id,
    )


def _violation_codes(topology) -> set[str]:
    return {violation["code"] for violation in topology_violations(topology)}


def _connector_states(topology) -> dict[str, str]:
    return {
        item["road_id"]: item["state"] for item in topology.connector_states
    }


def _crossing_only_count(topology) -> int:
    return sum(
        1
        for item in topology.connector_states
        if item["state"] == "crossing_only"
    )


@lru_cache(maxsize=1)
def _r1_layout():
    basis = DesignBasis.load(str(BASIS))
    design_input = load_design_input(CASE, basis)
    intent = build_design_intent(design_input, basis)
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    standard = standardize_all(design_input, basis)
    design_rect = find_focus_design_rect(design_input, intent, basis)
    building_layout = layout_focus_region(
        design_input,
        intent,
        basis,
        standard,
        site_inner,
        design_rect,
    )
    return build_road_layout(design_input, basis, intent, building_layout)


# ----------------------------------------------------------------- positive
def test_schema_contract_fields():
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"
    assert REQUIRED_FIELDS == (
        "road_count",
        "noded_segment_count",
        "node_count",
        "edge_count",
        "component_count",
        "cyclomatic",
        "degree_histogram",
        "dead_end_count",
        "junction_count",
        "explicit_junction_count",
        "max_endpoint_gap_m",
        "closed_ring_count",
        "components",
        "connector_states",
    )
    payload = _r1_layout().noded_topology.to_dict()
    assert set(payload) == set(REQUIRED_FIELDS) | {"schema_id"}
    assert payload["schema_id"] == SCHEMA_ID
    for component in payload["components"]:
        assert set(component) == {"node_count", "edge_count", "road_ids"}
    for entry in payload["connector_states"]:
        assert set(entry) == {"road_id", "class_name", "state"}


def test_r1_design_network_is_exactly_connected():
    layout = _r1_layout()
    topology = layout.noded_topology
    assert len(layout.roads) == 44
    assert sum(1 for r in layout.roads if r.class_name == "main") == 25
    assert sum(1 for r in layout.roads if r.class_name == "branch") == 17
    assert sum(1 for r in layout.roads if r.class_name == "access") == 2
    assert layout.corridor_union_pieces == 1
    assert topology.component_count == 1
    assert topology.max_endpoint_gap_m == 0.0
    assert _crossing_only_count(topology) == 0
    assert topology_violations(topology) == ()
    assert topology.closed_ring_count == 3
    assert topology.explicit_junction_count == 24


def test_r1_noded_graph_numbers():
    topology = _r1_layout().noded_topology
    assert topology.node_count == 57
    assert topology.edge_count == 66
    assert topology.noded_segment_count == 66
    assert topology.cyclomatic == 10
    assert topology.degree_histogram == {1: 19, 2: 3, 3: 33, 4: 2}
    assert topology.dead_end_count == 19
    assert topology.junction_count == 35
    assert topology.components[0]["road_ids"] == sorted(
        road.edge_id for road in _r1_layout().roads
    )
    assert len(_r1_layout().junction_nodes) == 35
    assert len(_r1_layout().dead_end_nodes) == 19


def test_r1_junctions_are_explicit_shared_vertices():
    layout = _r1_layout()
    road_by_id = {road.edge_id: road for road in layout.roads}
    for junction in layout.explicit_junctions:
        assert set(junction) == {"id", "x", "y", "road_ids"}
        point = (junction["x"], junction["y"])
        for road_id in junction["road_ids"]:
            vertices = {
                (float(x), float(y))
                for x, y in road_by_id[road_id].centerline.coords
            }
            assert point in vertices, (junction["id"], road_id)
    # branch main-side junctions are declared on the road itself
    for road in layout.roads:
        if road.class_name == "main":
            continue
        if road.edge_id == "BR-FOCUS":
            assert road.start_junction_id is not None
            assert road.end_junction_id is not None
        elif road.edge_id == "ACC-FOCUS-01":
            # the ring junction is an interior vertex of the closed ring
            assert road.start_junction_id is None
        else:
            assert road.start_junction_id is not None
            assert road.end_junction_id is None
    states = _connector_states(layout.noded_topology)
    assert states["BR-FOCUS"] == "shared_vertex"
    assert states["ACC-FOCUS-01"] == "shared_vertex"
    assert sum(1 for state in states.values() if state == "dead_end") == 17


def test_r1_main_alignment_and_network_areas_are_stable():
    """M4c-1a added collinear vertices; M4c-1b added access branches.

    The main-road alignment and its length are unchanged by the junction
    repair; the road/sidewalk areas grow with the M4c-1b access network, so
    they are re-baselined against the current design, not the 4c-1a design.
    """
    layout = _r1_layout()
    main_length = sum(
        road.centerline.length
        for road in layout.roads
        if road.class_name == "main"
    )
    assert main_length == pytest.approx(2126.392617984018, rel=1e-12)
    assert layout.road_area_m2 == pytest.approx(
        27369.822509945796, rel=1e-12
    )
    assert layout.sidewalk_area_m2 == pytest.approx(
        9889.900380276495, rel=1e-12
    )


def test_shared_vertex_junction_passes():
    roads = [
        _fake_road("M", "main", [(0.0, 0.0), (50.0, 0.0), (100.0, 0.0)]),
        _fake_road(
            "B", "branch", [(50.0, 0.0), (50.0, 10.0)],
            start_junction_id="J-01",
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    assert topology.component_count == 1
    assert topology.max_endpoint_gap_m == 0.0
    assert _connector_states(topology)["B"] == "dead_end"
    assert topology_violations(topology) == ()


# ----------------------------------------------------------------- negative
def test_split_branch_fails_closed():
    roads = [
        _fake_road("M", "main", [(0.0, 0.0), (100.0, 0.0)]),
        _fake_road("B", "branch", [(50.0, 10.0), (50.0, 20.0)]),
    ]
    topology = noded_road_topology(roads)
    assert topology.component_count == 2
    assert VIOLATION_COMPONENT_COUNT in _violation_codes(topology)


def test_one_picometre_endpoint_gap_is_detected():
    gap = 1e-12
    roads = [
        _fake_road("M", "main", [(0.0, 0.0), (100.0, 0.0)]),
        _fake_road(
            "B", "branch", [(50.0, gap), (50.0, 10.0)],
            start_junction_id="J-01",
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    assert topology.max_endpoint_gap_m > 0.0
    assert topology.max_endpoint_gap_m == pytest.approx(gap, rel=1e-6)
    # recorded but below the 1e-9 failure tolerance; the disconnection fails
    assert topology.max_endpoint_gap_m <= ENDPOINT_GAP_TOLERANCE_M
    assert topology.component_count == 2
    assert VIOLATION_COMPONENT_COUNT in _violation_codes(topology)


def test_snap_repair_without_shared_vertex_is_rejected():
    """``shapely.ops.snap`` only moves vertices onto *vertices* of the other
    line; it cannot create the intended junction, so the network stays split."""
    main = LineString([(0.0, 0.0), (100.0, 0.0)])
    branch = LineString([(50.0, 0.001), (50.0, 10.0)])
    snapped = snap(branch, main, 2e-3)
    assert list(snapped.coords) == list(branch.coords)  # snap did not help
    roads = [
        _fake_road("M", "main", list(main.coords)),
        _fake_road(
            "B", "branch", list(snapped.coords), start_junction_id="J-01"
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    assert topology.component_count == 2
    assert topology.max_endpoint_gap_m > 0.0
    assert VIOLATION_COMPONENT_COUNT in _violation_codes(topology)


def test_round_repair_without_shared_vertex_is_rejected():
    """Rounding the coordinates can make the float distance zero without making
    the junction a shared vertex; the crossing defect must catch it."""
    main = [(0.0, 0.0), (100.0, 0.0)]
    branch = [(50.0, 1e-4), (50.0, 10.0)]
    rounded_branch = [
        (round(x, 3), round(y, 3)) for x, y in branch
    ]
    assert rounded_branch[0] == (50.0, 0.0)
    roads = [
        _fake_road("M", "main", main),
        _fake_road(
            "B", "branch", rounded_branch, start_junction_id="J-01"
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    assert topology.component_count == 1
    assert _crossing_only_count(topology) == 1
    assert VIOLATION_CROSSING_ONLY in _violation_codes(topology)


def test_set_precision_rounding_repair_is_rejected():
    main = LineString([(0.0, 0.0), (100.0, 0.0)])
    branch = LineString([(50.0, 0.001), (50.0, 10.0)])
    rounded_main = set_precision(main, 0.01)
    rounded_branch = set_precision(branch, 0.01)
    roads = [
        _fake_road("M", "main", list(rounded_main.coords)),
        _fake_road(
            "B", "branch", list(rounded_branch.coords),
            start_junction_id="J-01",
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    assert topology_violations(topology) != ()
    assert (
        VIOLATION_CROSSING_ONLY in _violation_codes(topology)
        or VIOLATION_COMPONENT_COUNT in _violation_codes(topology)
    )


def test_crossing_without_shared_vertex_is_a_defect():
    roads = [
        _fake_road("M", "main", [(0.0, 0.0), (100.0, 0.0)]),
        _fake_road(
            "B", "branch", [(50.0, 0.0), (50.0, 10.0)],
            start_junction_id="J-01",
        ),
    ]
    junctions = [{"id": "J-01", "x": 50.0, "y": 0.0, "road_ids": ["M", "B"]}]
    topology = noded_road_topology(roads, junctions)
    # connected topologically, but only because the endpoint happens to lie on
    # the main line's interior: not an explicit junction.
    assert topology.component_count == 1
    assert topology.max_endpoint_gap_m == 0.0
    assert _connector_states(topology)["B"] == "crossing_only"
    assert VIOLATION_CROSSING_ONLY in _violation_codes(topology)


def test_isolated_closed_ring_is_an_undeclared_ring():
    ring = [
        (200.0, 0.0),
        (210.0, 0.0),
        (210.0, 10.0),
        (200.0, 10.0),
        (200.0, 0.0),
    ]
    roads = [
        _fake_road("M", "main", [(0.0, 0.0), (100.0, 0.0)]),
        _fake_road("LOOP", "access", ring),
    ]
    topology = noded_road_topology(roads)
    assert topology.component_count == 2
    assert topology.closed_ring_count == 1
    assert _connector_states(topology)["LOOP"] == "isolated_ring"
    assert VIOLATION_UNDECLARED_RING in _violation_codes(topology)


def test_topology_module_contains_no_tolerance_or_snap():
    """Guard: the check itself must not round/buffer/snap to find connectivity."""
    source = TOPOLOGY_SOURCE.read_text(encoding="utf-8")
    for forbidden in (
        ".buffer(",
        "set_precision(",
        "snap(",
        "round(",
        "buffer_",
        "simplify(",
    ):
        assert forbidden not in source, forbidden

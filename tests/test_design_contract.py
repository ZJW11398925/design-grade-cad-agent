"""Contract-completeness tests for the design-synthesis contract (M4c-3, v0.8).

The living contract must never drift back into "prose only": every machine-relevant
list is parsed from YAML (never string-grepped) and bound to the live
``dgcad_design`` modules. A rename, reorder, dropped basis key, taxonomy break, or
access/alignment/boundary-rule change fails here instead of publishing a stale
contract.

M4c-3 additions (v0.8):
* ``road_boundary_containment`` becomes a pass/fail check: the main-road corridor
  edge (centreline plus half width) must stay inside the published site boundary
  within 0.01 m — this machines the M4c-2 boundary defect;
* the contract now carries 30 verification names: 27 design check ids
  (``.upper()`` with two documented abbreviations) + 3 DXF-level items, and the
  27 design check ids must exist in the committed evidence after regeneration.
"""
from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import yaml

from dgcad_design.basis import (
    PARAMETER_AUTHORITIES,
    PARAMETER_SOURCE_KEYS,
    PROVENANCE_AUTHENTICATION,
)
from dgcad_design.topology import (
    CONNECTOR_STATES,
    ENDPOINT_GAP_TOLERANCE_M,
    REQUIRED_FIELDS,
    SCHEMA_ID,
    NodedRoadTopology,
)

ROOT = Path(__file__).resolve().parents[1]
CONTRACTS = ROOT / "contracts"
V1 = CONTRACTS / "design-synthesis-v0.1.yaml"
V2 = CONTRACTS / "design-synthesis-v0.2.yaml"
V3 = CONTRACTS / "design-synthesis-v0.3.yaml"
V4 = CONTRACTS / "design-synthesis-v0.4.yaml"
V5 = CONTRACTS / "design-synthesis-v0.5.yaml"
V6 = CONTRACTS / "design-synthesis-v0.6.yaml"
V7 = CONTRACTS / "design-synthesis-v0.7.yaml"
V8 = CONTRACTS / "design-synthesis-v0.8.yaml"
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"

#: verification.required names expected in v0.8, in contract order.
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
    "full_site_road_clearance",
    "dead_end_justification",
    "dead_end_resolution",
    "road_width_assignment",
    "candidate_open_space_ratio",
    "unbuilt_ratio",
    "designed_green_ratio",
    "full_site_north_south_spacing",
    "far_final_verification",
    "dxf_audit",
    "dxf_readback",
    "dxf_privacy",
]

#: Verification names that are proven at the DXF layer, not by a consistency check.
DXF_LEVEL_ITEMS = {"dxf_audit", "dxf_readback", "dxf_privacy"}

#: Expected consistency check ids for the 27 design-level verification names
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
    "FULL_SITE_ROAD_CLEARANCE",
    "DEAD_END_JUSTIFICATION",
    "DEAD_END_RESOLUTION",
    "ROAD_WIDTH_ASSIGNMENT",
    "CANDIDATE_OPEN_SPACE_RATIO",
    "UNBUILT_RATIO",
    "DESIGNED_GREEN_RATIO",
    "FULL_SITE_NS_SPACING",
    "FAR_FINAL_VERIFICATION",
]
CHECK_ID_OVERRIDES = {
    "focus_north_south_spacing": "FOCUS_NS_SPACING",
    "full_site_north_south_spacing": "FULL_SITE_NS_SPACING",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _topology_block() -> dict:
    return _load(V8)["road_design"]["topology"]


def _check_id(name: str) -> str:
    return CHECK_ID_OVERRIDES.get(name, name.upper())


def test_contract_v8_topology_required_matches_live_module_in_order():
    required = _topology_block()["required"]
    assert len(required) == len(REQUIRED_FIELDS)
    assert set(required) == set(REQUIRED_FIELDS)
    assert required == list(REQUIRED_FIELDS)  # order is part of the contract
    assert len(set(required)) == len(required)
    dataclass_fields = [item.name for item in fields(NodedRoadTopology)]
    assert dataclass_fields == list(REQUIRED_FIELDS)


def test_contract_v8_topology_schema_id_matches_live_module():
    assert _topology_block()["schema_id"] == SCHEMA_ID
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"


def test_contract_v8_connector_states_cover_live_module_states():
    declared = _topology_block()["connector_states"]
    assert declared == list(CONNECTOR_STATES)
    assert len(set(declared)) == len(CONNECTOR_STATES)


def test_contract_v8_fail_closed_covers_every_violation_family():
    text = " | ".join(_topology_block()["fail_closed"])
    assert "component_count" in text
    assert "max_endpoint_gap_m" in text
    assert "crossing" in text
    assert "ring" in text
    assert "1e-9" in text
    assert ENDPOINT_GAP_TOLERANCE_M == 1e-9


def test_supersede_chain_v01_to_v08():
    versions = [_load(path) for path in (V1, V2, V3, V4, V5, V6, V7, V8)]
    expected_superseded_by = [
        "design-synthesis-v0.2.yaml",
        "design-synthesis-v0.3.yaml",
        "design-synthesis-v0.4.yaml",
        "design-synthesis-v0.5.yaml",
        "design-synthesis-v0.6.yaml",
        "design-synthesis-v0.7.yaml",
        "design-synthesis-v0.8.yaml",
    ]
    for version, expected in zip(versions[:7], expected_superseded_by):
        assert version["status"] == "superseded"
        assert version["superseded_by"] == expected
    v8 = versions[7]
    assert v8["status"] == "living_contract"
    assert v8["schema_id"] == "dgcad.design-synthesis.v0.8"
    assert v8["supersedes"] == "design-synthesis-v0.7.yaml"


def test_contract_v8_basis_provenance_binds_live_module():
    basis = _load(V8)["basis"]
    assert "parameter_sources" in basis["required"]
    assert basis["parameter_authorities"] == list(PARAMETER_AUTHORITIES)
    assert basis["parameter_source_keys"] == list(PARAMETER_SOURCE_KEYS)
    assert basis["provenance_authentication"] == PROVENANCE_AUTHENTICATION == "declarative"
    rules = " | ".join(basis["rules"])
    assert "confirmed: true requires an approval_ref" in rules


def test_contract_v8_verification_ids_are_exact_and_map_to_check_ids():
    required = _load(V8)["verification"]["required"]
    assert required == EXPECTED_VERIFICATION
    assert len(required) == 30
    assert len(set(required)) == len(required)
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    assert len(design_names) == 27
    assert [_check_id(name) for name in design_names] == EXPECTED_DESIGN_CHECK_IDS
    assert len(set(EXPECTED_DESIGN_CHECK_IDS)) == 27


def test_contract_v8_design_checks_match_committed_evidence():
    """The 27 design check ids must exist in the committed evidence.

    Green only after the M4c-3 evidence regeneration (Lead task-66); allowed to
    fail while the contract is ahead of the committed evidence.
    """
    required = _load(V8)["verification"]["required"]
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    expected = {_check_id(name) for name in design_names}
    evidence = json.loads(
        (EVIDENCE / "design-consistency.json").read_text(encoding="utf-8")
    )
    assert {check["id"] for check in evidence["checks"]} == expected


def test_contract_v8_verification_rules_declare_boundary_and_alignment():
    rules = " | ".join(_load(V8)["verification"]["rules"])
    assert "pass is reserved for checks that verify generated geometry against a declared constraint" in rules
    assert "a deferred check is not a pass" in rules
    assert "main-road corridor-edge clearance must be at least 3.0 m" in rules
    assert "the main-road corridor edge (centreline plus half width) must lie inside the published site boundary with a tolerance of at most 0.01 m" in rules
    assert "corridor-edge containment and centreline containment are reported separately" in rules
    assert "main-road/building overlap must be at most 0.01 m2 after alignment" in rules
    assert "dead_end_resolution is a pass only when every dead end is resolved" in rules
    assert "source main edges remain in the evidence after alignment" in rules
    assert "main alignment must not change the declared access service relations" in rules
    assert "no road may be silently deleted" in rules
    assert "the declared access terminal must lie in the [3.4, 3.5] m centreline band" in rules
    assert "full-site road clearance is deferred until every group is designed" in rules


def test_contract_v8_constraints_include_boundary_containment():
    constraints = _load(V8)["constraints"]["required"]
    for name in (
        "road_access_coverage",
        "road_boundary_containment",
        "main_road_building_overlap",
        "road_alignment_evidence",
        "full_site_road_clearance",
        "dead_end_resolution",
    ):
        assert name in constraints
    rules = " | ".join(_load(V8)["constraints"]["rules"])
    assert "main-road corridor edges must stay inside the published site boundary within 0.01 m" in rules
    assert "main-road alignment is recorded as evidence" in rules


def test_contract_v8_verification_rules_keep_access_and_resolution_rules():
    rules = " | ".join(_load(V8)["verification"]["rules"])
    assert "an access service relation must be declared through serves_group_ids, not inferred from proximity" in rules
    assert "must lie on its serving road centreline or one of its endpoints within 1e-6 m" in rules
    assert "names a group with no buildings is an orphan relation error" in rules
    assert "road access coverage counts groups whose declared serving road passes validation" in rules
    assert "main-road/building overlap must be at most 0.01 m2 after alignment" in rules
    assert "each resolved conflict records before/after overlap per road and building" in rules
    assert "road_alignment_evidence is informational" in rules
    assert "dead ends are classified as justified group terminals, resolved site-edge termini, bridged or trimmed" in rules
    assert "all dead ends are classified and resolved, not all justified" in rules
    assert "parking entrance proximity is not a driveway connection" in rules
    assert "the 1.0 m2 per-route budget continues to constrain only newly generated group-access roads" in rules


def test_contract_v8_constraints_include_the_deferred_metrics():
    constraints = _load(V8)["constraints"]["required"]
    for name in (
        "designed_green_ratio",
        "parking_capacity",
        "far_final_verification",
        "parking_entrance_proximity",
        "parking_driveway_connection",
        "dead_end_justification",
        "dead_end_resolution",
    ):
        assert name in constraints
    rules = " | ".join(_load(V8)["constraints"]["rules"])
    assert "a deferred check is never a pass" in rules


def test_evidence_gate_register_points_design_package_at_v08():
    gate = _load(GATE_REGISTER)
    design = [p for p in gate["packages"] if p["package_id"] == "EP-R1-DESIGN-001"]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.8.yaml"

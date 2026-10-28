"""Contract-completeness tests for the design-synthesis / basis / topology contract.

These tests exist so the contract cannot drift back into "prose only": every
machine-relevant list in the living design-synthesis contract is parsed from YAML
(never string-grepped) and bound to the live ``dgcad_design`` modules. If either
side renames a field, reorders a report, changes the fail-closed families, drops a
basis provenance key, breaks the pass/info/deferred taxonomy, or changes an access
rule, CI fails here instead of silently publishing a stale contract.

M4c-1b additions (contract v0.5):
* three geometric access checks enter ``verification.required`` /
  ``constraints.required``: ``road_access_coverage``,
  ``parking_entrance_connection``, ``dead_end_justification``;
* the contract now carries 24 verification names: 21 design check ids
  (``.upper()`` with two documented abbreviations) + 3 DXF-level items, and the
  21 design check ids must exist in the committed evidence after regeneration.
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
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"

#: verification.required names expected in v0.5, in contract order.
EXPECTED_VERIFICATION = [
    "far_arithmetic_scenario",
    "parking_requirement_arithmetic",
    "parking_entrance_count",
    "parking_capacity",
    "parking_entrance_connection",
    "parking_layout",
    "unit_count_basis_invariant",
    "focus_north_south_spacing",
    "focus_boundary_setback",
    "focus_building_overlap",
    "focus_road_clearance",
    "road_connectivity",
    "road_corridor_coverage",
    "road_access_coverage",
    "dead_end_justification",
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

#: Expected consistency check ids for the 21 design-level verification names
#: (contract order). Uppercasing is the rule, with the two documented legacy
#: abbreviations that exist in ``consistency.py`` (FOCUS_NS_SPACING,
#: FULL_SITE_NS_SPACING). If the consistency layer renames a check id, this list
#: is the alarm and must be updated together with the contract and the code.
EXPECTED_DESIGN_CHECK_IDS = [
    "FAR_ARITHMETIC_SCENARIO",
    "PARKING_REQUIREMENT_ARITHMETIC",
    "PARKING_ENTRANCE_COUNT",
    "PARKING_CAPACITY",
    "PARKING_ENTRANCE_CONNECTION",
    "PARKING_LAYOUT",
    "UNIT_COUNT_BASIS_INVARIANT",
    "FOCUS_NS_SPACING",
    "FOCUS_BOUNDARY_SETBACK",
    "FOCUS_BUILDING_OVERLAP",
    "FOCUS_ROAD_CLEARANCE",
    "ROAD_CONNECTIVITY",
    "ROAD_CORRIDOR_COVERAGE",
    "ROAD_ACCESS_COVERAGE",
    "DEAD_END_JUSTIFICATION",
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
    return _load(V5)["road_design"]["topology"]


def _check_id(name: str) -> str:
    return CHECK_ID_OVERRIDES.get(name, name.upper())


def test_contract_v5_topology_required_matches_live_module_in_order():
    required = _topology_block()["required"]
    assert len(required) == len(REQUIRED_FIELDS)
    assert set(required) == set(REQUIRED_FIELDS)
    assert required == list(REQUIRED_FIELDS)  # order is part of the contract
    assert len(set(required)) == len(required)  # no duplicate field
    dataclass_fields = [item.name for item in fields(NodedRoadTopology)]
    assert dataclass_fields == list(REQUIRED_FIELDS)
    assert set(required) == set(dataclass_fields)


def test_contract_v5_topology_schema_id_matches_live_module():
    assert _topology_block()["schema_id"] == SCHEMA_ID
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"


def test_contract_v5_connector_states_cover_live_module_states():
    declared = _topology_block()["connector_states"]
    assert declared == list(CONNECTOR_STATES)
    assert set(declared) == set(CONNECTOR_STATES)
    assert len(set(declared)) == len(CONNECTOR_STATES)


def test_contract_v5_fail_closed_covers_every_violation_family():
    text = " | ".join(_topology_block()["fail_closed"])
    assert "component_count" in text
    assert "max_endpoint_gap_m" in text
    assert "crossing" in text
    assert "ring" in text
    assert "1e-9" in text
    assert ENDPOINT_GAP_TOLERANCE_M == 1e-9


def test_supersede_chain_v01_to_v05():
    v1 = _load(V1)
    v2 = _load(V2)
    v3 = _load(V3)
    v4 = _load(V4)
    v5 = _load(V5)
    assert v1["status"] == "superseded"
    assert v1["superseded_by"] == "design-synthesis-v0.2.yaml"
    assert v2["status"] == "superseded"
    assert v2["superseded_by"] == "design-synthesis-v0.3.yaml"
    assert v3["status"] == "superseded"
    assert v3["superseded_by"] == "design-synthesis-v0.4.yaml"
    assert v4["status"] == "superseded"
    assert v4["superseded_by"] == "design-synthesis-v0.5.yaml"
    assert v5["status"] == "living_contract"
    assert v5["schema_id"] == "dgcad.design-synthesis.v0.5"
    assert v5["supersedes"] == "design-synthesis-v0.4.yaml"


def test_contract_v5_basis_provenance_binds_live_module():
    basis = _load(V5)["basis"]
    assert "parameter_sources" in basis["required"]
    assert basis["parameter_authorities"] == list(PARAMETER_AUTHORITIES)
    assert basis["parameter_source_keys"] == list(PARAMETER_SOURCE_KEYS)
    assert len(PARAMETER_SOURCE_KEYS) == 21
    assert basis["provenance_authentication"] == PROVENANCE_AUTHENTICATION
    assert PROVENANCE_AUTHENTICATION == "declarative"
    rules = " | ".join(basis["rules"])
    assert "confirmed: true requires an approval_ref" in rules
    assert (
        "provenance is declarative metadata and is not authenticated until "
        "the authority layer binds it"
    ) in rules


def test_contract_v5_verification_ids_are_exact_and_map_to_check_ids():
    required = _load(V5)["verification"]["required"]
    assert required == EXPECTED_VERIFICATION
    assert len(required) == 24
    assert len(set(required)) == len(required)
    assert DXF_LEVEL_ITEMS.issubset(set(required))
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    assert len(design_names) == 21
    assert [_check_id(name) for name in design_names] == EXPECTED_DESIGN_CHECK_IDS
    assert len(set(EXPECTED_DESIGN_CHECK_IDS)) == 21


def test_contract_v5_design_checks_match_committed_evidence():
    """The 21 design check ids must exist in the committed evidence.

    This turns green only after the M4c-1b evidence regeneration (Lead); it is
    intentionally allowed to fail on a branch where the contract is ahead of the
    committed evidence, and it must never be weakened to a substring check.
    """
    required = _load(V5)["verification"]["required"]
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    expected = {_check_id(name) for name in design_names}
    evidence = json.loads(
        (EVIDENCE / "design-consistency.json").read_text(encoding="utf-8")
    )
    evidence_ids = {check["id"] for check in evidence["checks"]}
    assert evidence_ids == expected


def test_contract_v5_verification_rules_state_the_pass_taxonomy_and_access_rules():
    rules = " | ".join(_load(V5)["verification"]["rules"])
    # reserved-pass taxonomy from v0.4
    assert "pass is reserved for checks that verify generated geometry against a declared constraint" in rules
    assert "basis-derived arithmetic, assignment and count invariants are info, not pass" in rules
    assert "a deferred check is not a pass" in rules
    assert "candidate open-space ratio records its filters; the unbuilt ratio is a geometric union" in rules
    assert "the open-space ratio is not a designed-green ratio" in rules
    assert "parking entrance count is not parking capacity" in rules
    assert (
        "FAR/GFA are basis arithmetic; final FAR verification is deferred until "
        "the basis is confirmed"
    ) in rules
    # M4c-1b access rules
    assert "building-road clearance + 0.5 m" in rules
    assert "outside the footprint" in rules
    assert "at most 0.1 m" in rules
    assert "served building groups divided by groups that contain buildings" in rules
    assert "entrance point must be a Point" in rules
    assert "half the road width + 1.0 m" in rules
    assert "dead ends are classified as justified group terminals or unfinished main stubs" in rules
    assert "access is a geometric relation, not a component count" in rules


def test_contract_v5_constraints_include_access_and_deferred_metrics():
    constraints = _load(V5)["constraints"]
    required = constraints["required"]
    assert required[0] == "far"
    for name in (
        "designed_green_ratio",
        "parking_capacity",
        "far_final_verification",
        "road_access_coverage",
        "parking_entrance_connection",
        "dead_end_justification",
    ):
        assert name in required
    rules = " | ".join(constraints["rules"])
    assert "a deferred check is never a pass" in rules
    assert "far_final_verification is deferred until the basis is confirmed" in rules
    assert "an unserved group or an unfinished dead end is reported, never silently dropped" in rules


def test_evidence_gate_register_points_design_package_at_v05():
    gate = _load(GATE_REGISTER)
    design = [p for p in gate["packages"] if p["package_id"] == "EP-R1-DESIGN-001"]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.5.yaml"

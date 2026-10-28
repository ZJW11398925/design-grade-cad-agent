"""Contract-completeness tests for the design-synthesis / basis / topology contract.

These tests exist so the contract cannot drift back into "prose only": every
machine-relevant list in the living design-synthesis contract is parsed from YAML
(never string-grepped) and bound to the live ``dgcad_design`` modules. If either
side renames a field, reorders a report, changes the fail-closed families, drops a
basis provenance key, or breaks the pass/info/deferred taxonomy, CI fails here
instead of silently publishing a stale contract.

M4c-1d additions (contract v0.4):
* ``basis.provenance_authentication`` must be ``declarative`` and match the live
  ``dgcad_design.basis.PROVENANCE_AUTHENTICATION`` constant;
* the reserved-pass taxonomy: 21 verification names -> 18 design check ids
  (``.upper()`` with two documented abbreviations) + 3 DXF-level items, and the
  18 design check ids must exist in the committed evidence after regeneration.
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
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"

#: verification.required names expected in v0.4, in contract order.
EXPECTED_VERIFICATION = [
    "far_arithmetic_scenario",
    "parking_requirement_arithmetic",
    "parking_entrance_count",
    "parking_capacity",
    "parking_layout",
    "unit_count_basis_invariant",
    "focus_north_south_spacing",
    "focus_boundary_setback",
    "focus_building_overlap",
    "focus_road_clearance",
    "road_connectivity",
    "road_corridor_coverage",
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

#: Expected consistency check ids for the 18 design-level verification names
#: (contract order). Uppercasing is the rule, with the two documented legacy
#: abbreviations that exist in ``consistency.py`` (FOCUS_NS_SPACING,
#: FULL_SITE_NS_SPACING). If the consistency layer renames a check id, this list
#: is the alarm and must be updated together with the contract and the code.
EXPECTED_DESIGN_CHECK_IDS = [
    "FAR_ARITHMETIC_SCENARIO",
    "PARKING_REQUIREMENT_ARITHMETIC",
    "PARKING_ENTRANCE_COUNT",
    "PARKING_CAPACITY",
    "PARKING_LAYOUT",
    "UNIT_COUNT_BASIS_INVARIANT",
    "FOCUS_NS_SPACING",
    "FOCUS_BOUNDARY_SETBACK",
    "FOCUS_BUILDING_OVERLAP",
    "FOCUS_ROAD_CLEARANCE",
    "ROAD_CONNECTIVITY",
    "ROAD_CORRIDOR_COVERAGE",
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
    return _load(V4)["road_design"]["topology"]


def _check_id(name: str) -> str:
    return CHECK_ID_OVERRIDES.get(name, name.upper())


def test_contract_v4_topology_required_matches_live_module_in_order():
    required = _topology_block()["required"]
    assert len(required) == len(REQUIRED_FIELDS)
    assert set(required) == set(REQUIRED_FIELDS)
    assert required == list(REQUIRED_FIELDS)  # order is part of the contract
    assert len(set(required)) == len(required)  # no duplicate field
    # every declared field is an actual dataclass field of the live report, in order
    dataclass_fields = [item.name for item in fields(NodedRoadTopology)]
    assert dataclass_fields == list(REQUIRED_FIELDS)
    assert set(required) == set(dataclass_fields)


def test_contract_v4_topology_schema_id_matches_live_module():
    assert _topology_block()["schema_id"] == SCHEMA_ID
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"


def test_contract_v4_connector_states_cover_live_module_states():
    declared = _topology_block()["connector_states"]
    assert declared == list(CONNECTOR_STATES)
    assert set(declared) == set(CONNECTOR_STATES)
    assert len(set(declared)) == len(CONNECTOR_STATES)


def test_contract_v4_fail_closed_covers_every_violation_family():
    text = " | ".join(_topology_block()["fail_closed"])
    assert "component_count" in text
    assert "max_endpoint_gap_m" in text
    assert "crossing" in text  # crossing_only_count
    assert "ring" in text  # undeclared closed ring
    assert "1e-9" in text
    assert ENDPOINT_GAP_TOLERANCE_M == 1e-9


def test_supersede_chain_v01_to_v04():
    v1 = _load(V1)
    v2 = _load(V2)
    v3 = _load(V3)
    v4 = _load(V4)
    assert v1["status"] == "superseded"
    assert v1["superseded_by"] == "design-synthesis-v0.2.yaml"
    assert v2["status"] == "superseded"
    assert v2["superseded_by"] == "design-synthesis-v0.3.yaml"
    assert v3["status"] == "superseded"
    assert v3["superseded_by"] == "design-synthesis-v0.4.yaml"
    assert v4["status"] == "living_contract"
    assert v4["schema_id"] == "dgcad.design-synthesis.v0.4"
    assert v4["supersedes"] == "design-synthesis-v0.3.yaml"


def test_contract_v4_basis_provenance_binds_live_module():
    basis = _load(V4)["basis"]
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
    assert "every basis parameter declares source, authority and confirmation state" in rules
    assert "agent_assumption parameters cannot be presented as verified project requirements" in rules
    assert "human confirmation is never claimed by the Agent" in rules


def test_contract_v4_verification_ids_are_exact_and_map_to_check_ids():
    required = _load(V4)["verification"]["required"]
    assert required == EXPECTED_VERIFICATION
    assert len(required) == 21
    assert len(set(required)) == len(required)
    assert DXF_LEVEL_ITEMS.issubset(set(required))
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    assert len(design_names) == 18
    assert [_check_id(name) for name in design_names] == EXPECTED_DESIGN_CHECK_IDS
    assert len(set(EXPECTED_DESIGN_CHECK_IDS)) == 18


def test_contract_v4_design_checks_match_committed_evidence():
    """The 18 design check ids must exist in the committed evidence.

    This turns green only after the M4c-1d evidence regeneration (Lead task); it is
    intentionally allowed to fail on a branch where the contract is ahead of the
    committed evidence, and it must never be weakened to a substring check.
    """
    required = _load(V4)["verification"]["required"]
    design_names = [name for name in required if name not in DXF_LEVEL_ITEMS]
    expected = {_check_id(name) for name in design_names}
    evidence = json.loads(
        (EVIDENCE / "design-consistency.json").read_text(encoding="utf-8")
    )
    evidence_ids = {check["id"] for check in evidence["checks"]}
    assert evidence_ids == expected


def test_contract_v4_verification_rules_state_the_pass_taxonomy():
    rules = " | ".join(_load(V4)["verification"]["rules"])
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
    assert "noded centreline component count" in rules
    assert "non-gating" in rules


def test_contract_v4_constraints_include_deferred_metrics():
    constraints = _load(V4)["constraints"]
    required = constraints["required"]
    assert required[0] == "far"
    assert "designed_green_ratio" in required
    assert "parking_capacity" in required
    assert "far_final_verification" in required
    rules = " | ".join(constraints["rules"])
    assert "a deferred check is never a pass" in rules
    assert "far_final_verification is deferred until the basis is confirmed" in rules


def test_evidence_gate_register_points_design_package_at_v04():
    gate = _load(GATE_REGISTER)
    design = [p for p in gate["packages"] if p["package_id"] == "EP-R1-DESIGN-001"]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.4.yaml"

"""Contract-completeness tests for the design-synthesis / basis / topology contract.

These tests exist so the contract cannot drift back into "prose only": every
machine-relevant list in ``contracts/design-synthesis-v0.3.yaml`` is parsed from
YAML (never string-grepped) and bound to the live ``dgcad_design`` modules. If
either side renames a field, reorders a report, changes the fail-closed families,
or drops a basis provenance key, CI fails here instead of silently publishing a
stale contract.

M4c-1c adds two bindings:
* ``basis.parameter_authorities`` / ``basis.parameter_source_keys`` must equal the
  live ``dgcad_design.basis`` tuples (the contract cannot promise what the code
  does not implement);
* every ``verification.required`` name must map to a real check id in the
  consistency layer (``consistency.py``), including the documented abbreviation
  ``full_site_north_south_spacing -> FULL_SITE_NS_SPACING``.
"""
from __future__ import annotations

import json
from dataclasses import fields
from pathlib import Path

import yaml

from dgcad_design.basis import PARAMETER_AUTHORITIES, PARAMETER_SOURCE_KEYS
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
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"
EVIDENCE = ROOT / "docs" / "e2e" / "design-synthesis-001"

#: verification.required names expected in v0.3, in contract order.
EXPECTED_VERIFICATION = [
    "far_range",
    "parking_requirement_arithmetic",
    "parking_entrance_count",
    "parking_capacity",
    "parking_layout",
    "unit_count_preserved",
    "focus_north_south_spacing",
    "focus_boundary_setback",
    "focus_building_overlap",
    "focus_road_clearance",
    "road_connectivity",
    "road_corridor_coverage",
    "road_widths",
    "open_space_ratio",
    "designed_green_ratio",
    "full_site_north_south_spacing",
    "dxf_audit",
    "dxf_readback",
    "dxf_privacy",
]

#: verification name -> consistency check id. Uppercasing is the rule, with the
#: two documented legacy abbreviations that exist in ``consistency.py``
#: (FOCUS_NS_SPACING, FULL_SITE_NS_SPACING). If the consistency layer renames a
#: check id, this table is the alarm and must be updated together with the
#: contract and the implementation.
CHECK_ID_OVERRIDES = {
    "focus_north_south_spacing": "FOCUS_NS_SPACING",
    "full_site_north_south_spacing": "FULL_SITE_NS_SPACING",
}


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _topology_block() -> dict:
    return _load(V3)["road_design"]["topology"]


def _check_id(name: str) -> str:
    return CHECK_ID_OVERRIDES.get(name, name.upper())


def test_contract_v3_topology_required_matches_live_module_in_order():
    required = _topology_block()["required"]
    assert len(required) == len(REQUIRED_FIELDS)
    assert set(required) == set(REQUIRED_FIELDS)
    assert required == list(REQUIRED_FIELDS)  # order is part of the contract
    assert len(set(required)) == len(required)  # no duplicate field
    # every declared field is an actual dataclass field of the live report, in order
    dataclass_fields = [item.name for item in fields(NodedRoadTopology)]
    assert dataclass_fields == list(REQUIRED_FIELDS)
    assert set(required) == set(dataclass_fields)


def test_contract_v3_topology_schema_id_matches_live_module():
    assert _topology_block()["schema_id"] == SCHEMA_ID
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"


def test_contract_v3_connector_states_cover_live_module_states():
    declared = _topology_block()["connector_states"]
    assert declared == list(CONNECTOR_STATES)
    assert set(declared) == set(CONNECTOR_STATES)
    assert len(set(declared)) == len(CONNECTOR_STATES)


def test_contract_v3_fail_closed_covers_every_violation_family():
    text = " | ".join(_topology_block()["fail_closed"])
    assert "component_count" in text
    assert "max_endpoint_gap_m" in text
    assert "crossing" in text  # crossing_only_count
    assert "ring" in text  # undeclared closed ring
    assert "1e-9" in text
    assert ENDPOINT_GAP_TOLERANCE_M == 1e-9


def test_supersede_chain_v01_to_v02_to_v03():
    v1 = _load(V1)
    v2 = _load(V2)
    v3 = _load(V3)
    assert v1["status"] == "superseded"
    assert v1["superseded_by"] == "design-synthesis-v0.2.yaml"
    assert v2["status"] == "superseded"
    assert v2["superseded_by"] == "design-synthesis-v0.3.yaml"
    assert v3["status"] == "living_contract"
    assert v3["schema_id"] == "dgcad.design-synthesis.v0.3"
    assert v3["supersedes"] == "design-synthesis-v0.2.yaml"


def test_contract_v3_basis_requires_parameter_sources_and_binds_live_tuples():
    basis = _load(V3)["basis"]
    assert "parameter_sources" in basis["required"]
    assert basis["parameter_authorities"] == list(PARAMETER_AUTHORITIES)
    assert basis["parameter_source_keys"] == list(PARAMETER_SOURCE_KEYS)
    assert len(PARAMETER_SOURCE_KEYS) == 21
    rules = " | ".join(basis["rules"])
    assert "every basis parameter declares source, authority and confirmation state" in rules
    assert "agent_assumption parameters cannot be presented as verified project requirements" in rules
    assert "human confirmation is never claimed by the Agent" in rules


def test_contract_v3_verification_ids_are_exact_and_map_to_check_ids():
    verification = _load(V3)["verification"]
    required = verification["required"]
    assert required == EXPECTED_VERIFICATION
    assert len(set(required)) == len(required)
    mapped = [_check_id(name) for name in required]
    assert len(set(mapped)) == len(mapped)
    assert mapped == [
        "FAR_RANGE",
        "PARKING_REQUIREMENT_ARITHMETIC",
        "PARKING_ENTRANCE_COUNT",
        "PARKING_CAPACITY",
        "PARKING_LAYOUT",
        "UNIT_COUNT_PRESERVED",
        "FOCUS_NS_SPACING",
        "FOCUS_BOUNDARY_SETBACK",
        "FOCUS_BUILDING_OVERLAP",
        "FOCUS_ROAD_CLEARANCE",
        "ROAD_CONNECTIVITY",
        "ROAD_CORRIDOR_COVERAGE",
        "ROAD_WIDTHS",
        "OPEN_SPACE_RATIO",
        "DESIGNED_GREEN_RATIO",
        "FULL_SITE_NS_SPACING",
        "DXF_AUDIT",
        "DXF_READBACK",
        "DXF_PRIVACY",
    ]
    # the design-check half of the verification list must exist in the committed
    # evidence under exactly these ids (the alias mapping above is not enough:
    # a rename in the consistency layer must fail this test, not just the alias).
    evidence = json.loads(
        (EVIDENCE / "design-consistency.json").read_text(encoding="utf-8")
    )
    evidence_ids = {check["id"] for check in evidence["checks"]}
    assert set(mapped[:16]) == evidence_ids


def test_contract_v3_verification_rules_state_metric_honesty():
    rules = " | ".join(_load(V3)["verification"]["rules"])
    assert "noded centreline component count" in rules
    assert "non-gating" in rules
    assert "a deferred check is not a pass" in rules
    assert "the open-space ratio is not a designed-green ratio" in rules
    assert "parking entrance count is not parking capacity" in rules
    assert "FAR/GFA are basis arithmetic, not a spatial design result" in rules


def test_contract_v3_constraints_include_deferred_metrics():
    constraints = _load(V3)["constraints"]
    assert "designed_green_ratio" in constraints["required"]
    assert "parking_capacity" in constraints["required"]
    rules = " | ".join(constraints["rules"])
    assert "a deferred check is never a pass" in rules


def test_evidence_gate_register_points_design_package_at_v03():
    gate = _load(GATE_REGISTER)
    design = [p for p in gate["packages"] if p["package_id"] == "EP-R1-DESIGN-001"]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.3.yaml"

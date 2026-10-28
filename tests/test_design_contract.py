"""Contract-completeness tests for the design-synthesis / road-topology contract.

M4c-1a made the road topology a first-class contract term. These tests exist so the
contract cannot drift back into "prose only": every machine-relevant list in
``contracts/design-synthesis-v0.2.yaml`` is parsed from YAML (never string-grepped)
and bound to the live ``dgcad_design.topology`` module. If either side renames a
field, reorders the topology report, or changes the fail-closed families, CI fails
here instead of silently publishing a stale contract.
"""
from __future__ import annotations

from dataclasses import fields
from pathlib import Path

import yaml

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
GATE_REGISTER = CONTRACTS / "evidence-gate-register-v0.2.yaml"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _topology_block() -> dict:
    return _load(V2)["road_design"]["topology"]


def test_contract_v2_topology_required_matches_live_module_in_order():
    required = _topology_block()["required"]
    assert len(required) == len(REQUIRED_FIELDS)
    assert set(required) == set(REQUIRED_FIELDS)
    assert required == list(REQUIRED_FIELDS)  # order is part of the contract
    assert len(set(required)) == len(required)  # no duplicate field
    # every declared field is an actual dataclass field of the live report, in order
    dataclass_fields = [item.name for item in fields(NodedRoadTopology)]
    assert dataclass_fields == list(REQUIRED_FIELDS)
    assert set(required) == set(dataclass_fields)


def test_contract_v2_topology_schema_id_matches_live_module():
    assert _topology_block()["schema_id"] == SCHEMA_ID
    assert SCHEMA_ID == "dgcad.design-road-topology.v0.1"


def test_contract_v2_connector_states_cover_live_module_states():
    declared = _topology_block()["connector_states"]
    assert declared == list(CONNECTOR_STATES)
    assert set(declared) == set(CONNECTOR_STATES)
    assert len(set(declared)) == len(CONNECTOR_STATES)


def test_contract_v2_fail_closed_covers_every_violation_family():
    text = " | ".join(_topology_block()["fail_closed"])
    assert "component_count" in text
    assert "max_endpoint_gap_m" in text
    assert "crossing" in text  # crossing_only_count
    assert "ring" in text  # undeclared closed ring
    assert "1e-9" in text
    assert ENDPOINT_GAP_TOLERANCE_M == 1e-9


def test_v01_is_superseded_and_v02_is_the_living_contract():
    v1 = _load(V1)
    v2 = _load(V2)
    assert v1["status"] == "superseded"
    assert v1["superseded_by"] == "design-synthesis-v0.2.yaml"
    assert v2["status"] == "living_contract"
    assert v2["schema_id"] == "dgcad.design-synthesis.v0.2"
    assert v2["supersedes"] == "design-synthesis-v0.1.yaml"


def test_contract_v2_verification_declares_noded_connectivity_and_coverage():
    verification = _load(V2)["verification"]
    required = verification["required"]
    assert "road_connectivity" in required
    assert "road_corridor_coverage" in required
    # the connectivity item must not be satisfied by the corridor-union count
    assert "focus_road_clearance" in required  # pre-existing items are preserved
    rules = " | ".join(verification["rules"])
    assert "noded centreline component count" in rules
    assert "non-gating" in rules


def test_evidence_gate_register_points_design_package_at_v02():
    gate = _load(GATE_REGISTER)
    design = [p for p in gate["packages"] if p["package_id"] == "EP-R1-DESIGN-001"]
    assert len(design) == 1
    assert design[0]["contract"] == "contracts/design-synthesis-v0.2.yaml"

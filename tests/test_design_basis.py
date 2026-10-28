"""Per-parameter provenance and authority tests for the design basis (M4c-1c).

The design basis is an explicit set of assumptions, not measured facts. These
tests pin the machine-readable provenance contract: every one of the 21 design
parameters must declare ``source``, ``authority`` and ``confirmed``, unknown
authorities are rejected, and an ``agent_assumption`` can never be marked
confirmed (the Agent may not self-confirm a parameter).
"""
from __future__ import annotations

import copy
from pathlib import Path

import pytest
import yaml

from dgcad_design.basis import (
    PARAMETER_AUTHORITIES,
    PARAMETER_SOURCE_KEYS,
    PROVENANCE_AUTHENTICATION,
    DesignBasis,
)

ROOT = Path(__file__).resolve().parents[1]
BASIS_PATH = ROOT / "fixtures" / "design" / "design-basis-001.yaml"


def fixture_data() -> dict:
    return copy.deepcopy(
        yaml.safe_load(BASIS_PATH.read_text(encoding="utf-8"))
    )


def load_fixture() -> DesignBasis:
    return DesignBasis.from_dict(fixture_data())


def test_fixture_loads_and_declares_all_21_parameter_sources():
    basis = load_fixture()
    assert basis.basis_id == "design-assumption-v0.2"
    assert basis.version == "0.2.0"
    assert set(basis.parameter_sources) == set(PARAMETER_SOURCE_KEYS)
    assert len(PARAMETER_SOURCE_KEYS) == 21
    assert len(basis.parameter_sources) == 21


def test_fixture_every_parameter_is_unconfirmed_and_authority_is_legal():
    basis = load_fixture()
    for key in PARAMETER_SOURCE_KEYS:
        entry = basis.parameter_sources[key]
        assert isinstance(entry["source"], str) and entry["source"].strip(), key
        assert entry["authority"] in PARAMETER_AUTHORITIES, key
        assert entry["confirmed"] is False, key
    assert basis.human_confirmed is False
    assert basis.design_authority == "rule_derived"


def test_fixture_authority_classification_is_the_declared_split():
    basis = load_fixture()
    by_authority: dict[str, list[str]] = {}
    for key, entry in basis.parameter_sources.items():
        by_authority.setdefault(entry["authority"], []).append(key)
    assert sorted(by_authority["declared_requirement"]) == [
        "far_max",
        "far_min",
        "green_ratio_min",
        "north_south_spacing_m",
        "parking_spaces_per_household",
    ]
    assert sorted(by_authority["designer_stated"]) == [
        "floors",
        "households_per_staircase_per_floor",
    ]
    assert sorted(by_authority["inferred_from_sketch"]) == [
        "facility_gfa_m2",
        "origin_px",
        "scale_px_per_m",
    ]
    assert len(by_authority["agent_assumption"]) == 11
    assert "project_condition" not in by_authority  # allowed enum, unused here


def test_missing_parameter_sources_is_value_error_not_key_error():
    data = fixture_data()
    del data["parameter_sources"]
    with pytest.raises(ValueError, match="parameter_sources is required"):
        DesignBasis.from_dict(data)


def test_missing_single_parameter_source_key_is_rejected():
    data = fixture_data()
    del data["parameter_sources"]["floors"]
    with pytest.raises(ValueError, match="missing declared parameters: floors"):
        DesignBasis.from_dict(data)


def test_unknown_authority_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["floors"]["authority"] = "certified_truth"
    with pytest.raises(ValueError, match="authority 'certified_truth' is not one of"):
        DesignBasis.from_dict(data)


def test_agent_assumption_cannot_be_confirmed():
    data = fixture_data()
    assert data["parameter_sources"]["floor_height_m"]["authority"] == "agent_assumption"
    data["parameter_sources"]["floor_height_m"]["confirmed"] = True
    with pytest.raises(ValueError, match="agent_assumption cannot be confirmed"):
        DesignBasis.from_dict(data)


def test_provenance_authentication_is_declarative():
    assert PROVENANCE_AUTHENTICATION == "declarative"
    provenance = load_fixture().provenance()
    assert provenance["provenance_authentication"] == "declarative"
    assert provenance["provenance_authentication"] == PROVENANCE_AUTHENTICATION


def test_confirmed_without_approval_ref_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["floors"]["confirmed"] = True
    with pytest.raises(
        ValueError,
        match="confirmed requires approval_ref; provenance is declarative, not authenticated",
    ):
        DesignBasis.from_dict(data)


def test_confirmed_with_blank_approval_ref_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["floors"]["confirmed"] = True
    data["parameter_sources"]["floors"]["approval_ref"] = "   "
    with pytest.raises(ValueError, match="confirmed requires approval_ref"):
        DesignBasis.from_dict(data)


def test_confirmed_with_non_string_approval_ref_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["floors"]["confirmed"] = True
    data["parameter_sources"]["floors"]["approval_ref"] = True
    with pytest.raises(ValueError, match="confirmed requires approval_ref"):
        DesignBasis.from_dict(data)


def test_confirmed_with_approval_ref_passes_but_stays_declarative():
    data = fixture_data()
    data["parameter_sources"]["floors"]["confirmed"] = True
    data["parameter_sources"]["floors"]["approval_ref"] = "APPROVAL-REF-001"
    basis = DesignBasis.from_dict(data)
    assert basis.parameter_sources["floors"]["confirmed"] is True
    assert basis.parameter_sources["floors"]["approval_ref"] == "APPROVAL-REF-001"
    provenance = basis.provenance()
    assert provenance["confirmed_parameters"] == ["floors"]
    # a written approval reference still does not authenticate the provenance
    assert provenance["provenance_authentication"] == "declarative"
    assert basis.human_confirmed is False


def test_agent_assumption_cannot_be_confirmed_even_with_approval_ref():
    data = fixture_data()
    data["parameter_sources"]["floor_height_m"]["confirmed"] = True
    data["parameter_sources"]["floor_height_m"]["approval_ref"] = "APPROVAL-REF-001"
    with pytest.raises(ValueError, match="agent_assumption cannot be confirmed"):
        DesignBasis.from_dict(data)


def test_confirmed_designer_stated_value_is_allowed_by_shape():
    # the Agent-facing rule is about agent_assumption only; a human-sourced
    # parameter may carry confirmed: true + approval_ref (the draft still records
    # human_confirmed: false at basis level).
    data = fixture_data()
    data["parameter_sources"]["floors"]["confirmed"] = True
    data["parameter_sources"]["floors"]["approval_ref"] = "APPROVAL-REF-001"
    basis = DesignBasis.from_dict(data)
    assert basis.parameter_sources["floors"]["confirmed"] is True
    assert basis.human_confirmed is False


def test_non_mapping_parameter_source_entry_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["road_widths"] = "declared"
    with pytest.raises(ValueError, match="must be a mapping"):
        DesignBasis.from_dict(data)


def test_empty_source_string_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["far_min"]["source"] = "   "
    with pytest.raises(ValueError, match="source must be a non-empty string"):
        DesignBasis.from_dict(data)


def test_non_bool_confirmed_is_rejected():
    data = fixture_data()
    data["parameter_sources"]["far_max"]["confirmed"] = "false"
    with pytest.raises(ValueError, match="confirmed must be a bool"):
        DesignBasis.from_dict(data)


def test_extra_parameter_source_keys_are_tolerated_but_validated():
    data = fixture_data()
    data["parameter_sources"]["elevation_datum"] = {
        "source": "Agent assumed datum for schematic massing",
        "authority": "agent_assumption",
        "confirmed": False,
    }
    basis = DesignBasis.from_dict(data)
    assert set(PARAMETER_SOURCE_KEYS) <= set(basis.parameter_sources)

    data = fixture_data()
    data["parameter_sources"]["elevation_datum"] = {
        "source": "Agent assumed datum",
        "authority": "certified_truth",
        "confirmed": False,
    }
    with pytest.raises(ValueError, match="authority 'certified_truth' is not one of"):
        DesignBasis.from_dict(data)


def test_to_dict_includes_parameter_sources_and_roundtrips():
    basis = load_fixture()
    payload = basis.to_dict()
    assert "parameter_sources" in payload
    assert payload["parameter_sources"] == basis.parameter_sources
    assert payload["basis_id"] == "design-assumption-v0.2"
    again = DesignBasis.from_dict(payload)
    assert again.to_dict() == payload


def test_provenance_summary_reports_authority_counts_and_unconfirmed_keys():
    basis = load_fixture()
    provenance = basis.provenance()
    assert provenance["basis_id"] == basis.basis_id
    assert provenance["human_confirmed"] is False
    assert provenance["authority_counts"] == {
        "agent_assumption": 11,
        "declared_requirement": 5,
        "designer_stated": 2,
        "inferred_from_sketch": 3,
    }
    assert provenance["unconfirmed_parameters"] == sorted(PARAMETER_SOURCE_KEYS)
    assert provenance["confirmed_parameters"] == []
    assert len(provenance["agent_assumption_parameters"]) == 11
    assert provenance["all_parameters_confirmed"] is False
    assert provenance["provenance_authentication"] == "declarative"
    assert provenance["parameters"]["floors"]["authority"] == "designer_stated"

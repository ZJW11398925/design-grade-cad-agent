from __future__ import annotations

import hashlib
import json
from pathlib import Path

EVIDENCE = (
    Path(__file__).resolve().parents[2]
    / "docs"
    / "e2e"
    / "third-party-003c"
)


def _load(name: str):
    return json.loads((EVIDENCE / name).read_text(encoding="utf-8"))


def test_autocad_roundtrip_is_semantic_pass_with_serialization_differences():
    comparison = _load("comparison.json")
    environment = _load("environment.json")

    assert comparison["verdict"] == (
        "semantic_pass_with_serialization_differences"
    )
    assert comparison["tool"] == "AutoCAD Core Console"
    assert comparison["validator"]["verdict"] == "pass"
    assert comparison["validator"]["codes"] == []
    assert comparison["scope"]["matrix_status"] == "partial"
    assert "AutoCAD 2024 Core Console" in comparison["scope"][
        "apps_executed"
    ]
    assert "LibreCAD" in comparison["scope"]["apps_not_executed"]
    assert "FreeCAD" in comparison["scope"]["apps_not_executed"]

    input_state = comparison["input"]["state"]
    roundtrip_state = comparison["roundtrip"]["state"]
    assert input_state["dxf_version"] == "AC1024"
    assert roundtrip_state["dxf_version"] == "AC1032"
    assert input_state["insunits"] == roundtrip_state["insunits"] == 6
    assert input_state["entity_count"] == roundtrip_state["entity_count"] == 15
    assert input_state["entity_types"] == roundtrip_state["entity_types"]
    assert input_state["xdata_count"] == roundtrip_state["xdata_count"] == 15
    assert input_state["audit_errors"] == roundtrip_state["audit_errors"] == 0
    assert input_state["audit_fixes"] == roundtrip_state["audit_fixes"] == 0
    assert input_state["blocks"] == roundtrip_state["blocks"]
    assert input_state["dimstyles"] == roundtrip_state["dimstyles"]
    assert input_state["text_styles"] == roundtrip_state["text_styles"]

    assert (
        input_state["layers"]["A-BUILDING-OUTLINE"]["linetype"]
        == "CONTINUOUS"
    )
    assert (
        roundtrip_state["layers"]["A-BUILDING-OUTLINE"]["linetype"]
        == "Continuous"
    )

    kinds = {item["kind"] for item in comparison["differences"]}
    assert kinds == {"dxf_version", "symbol_name_case"}
    assert any(
        item["kind"] == "symbol_name_case"
        and item["input"] == "CONTINUOUS"
        and item["roundtrip"] == "Continuous"
        for item in comparison["differences"]
    )

    input_path = EVIDENCE / comparison["input"]["file"]
    roundtrip_path = EVIDENCE / comparison["roundtrip"]["file"]
    assert input_path.is_file()
    assert roundtrip_path.is_file()
    assert (
        comparison["input"]["sha256"]
        == hashlib.sha256(input_path.read_bytes()).hexdigest()
    )
    assert (
        comparison["roundtrip"]["sha256"]
        == hashlib.sha256(roundtrip_path.read_bytes()).hexdigest()
    )

    assert environment["returncode"] == 0
    assert environment["timed_out"] is False
    assert environment["autocad_file_version"] == "24.3.61.0.0"
    assert environment["autocad_executable"].endswith("accoreconsole.exe")
    assert "/isolate" in environment["command"]


def test_third_party_evidence_does_not_claim_a_complete_matrix():
    comparison = _load("comparison.json")
    assert comparison["scope"]["matrix_status"] == "partial"
    assert comparison["scope"]["apps_not_executed"] == [
        "LibreCAD",
        "FreeCAD",
        "AutoCAD GUI visual QA",
    ]
    assert comparison["verdict"] != "semantic_pass"
    assert any(
        "no LibreCAD/FreeCAD/GUI" in item
        for item in comparison["non_claims"]
    )
    assert any(
        "not a general CAD compatibility proof" in item
        for item in comparison["non_claims"]
    )

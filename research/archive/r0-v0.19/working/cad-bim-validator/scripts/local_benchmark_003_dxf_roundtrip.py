#!/usr/bin/env python3
"""Synthetic DXF writer-reader + design-profile validator probe.

Uses ezdxf installed in the current runtime. Profile values are test fixtures,
not any real design institute or Chinese standard. This validates DXF
serialization and our custom profile checks, not design correctness.
"""
from __future__ import annotations

import json
import copy
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

import ezdxf
import yaml
from ezdxf.lldxf import validator as dxf_validator

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "cad-profile-test-v0.1.yaml"
OUT_JSON = ROOT / "local-benchmark-003-dxf.json"
SAMPLE_DIR = ROOT / "samples"
SAMPLE_DIR.mkdir(parents=True, exist_ok=True)
VALID_DXF = SAMPLE_DIR / "sample-design-office-profile-test.dxf"


def make_document(profile: dict[str, Any]) -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = profile["units"]["insunits"]
    doc.header["$LWDISPLAY"] = profile["units"]["expected_lwdisplay"]

    for name, attrs in profile["required_layers"].items():
        if name not in doc.layers:
            doc.layers.new(name, dxfattribs=attrs)
        else:
            layer = doc.layers.get(name)
            layer.dxf.color = attrs["color"]
            layer.dxf.linetype = attrs["linetype"]
            layer.dxf.lineweight = attrs["lineweight"]

    if "CN_TEXT" not in doc.styles:
        doc.styles.new("CN_TEXT", dxfattribs={"font": "txt.shx"})
    if "SITE-DIM" not in doc.dimstyles:
        doc.dimstyles.new("SITE-DIM", dxfattribs={"dimtxt": 2.5, "dimasz": 2.5, "dimscale": 1.0})
    if "BLDG-MASS" not in doc.blocks:
        block = doc.blocks.new("BLDG-MASS")
        block.add_lwpolyline([(0, 0), (8, 0), (8, 6), (0, 6)], close=True,
                             dxfattribs={"layer": "A-BUILDING-OUTLINE"})

    # Keep the standard default layout and add a named paper layout for the fixture.
    if "A3" not in doc.layouts:
        doc.layouts.new("A3")

    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 0), (100, 0), (100, 80), (0, 80)], close=True,
                       dxfattribs={"layer": "A-SITE-BOUNDARY"})
    msp.add_lwpolyline([(20, 20), (35, 20), (35, 32), (20, 32)], close=True,
                       dxfattribs={"layer": "A-BUILDING-OUTLINE"})
    msp.add_line((0, 40), (100, 40), dxfattribs={"layer": "C-ROAD-CENTER"})
    msp.add_lwpolyline([(60, 10), (90, 10), (90, 25), (60, 25)], close=True,
                       dxfattribs={"layer": "L-GREEN"})
    msp.add_blockref("BLDG-MASS", (42, 20), dxfattribs={"layer": "A-BUILDING-OUTLINE"})
    msp.add_text("TEST SITE", dxfattribs={"layer": "ANNO-DIM", "style": "CN_TEXT", "height": 2.5}).set_placement((5, 85))
    msp.add_linear_dim(base=(20, 15), p1=(20, 20), p2=(35, 20), dimstyle="SITE-DIM",
                       dxfattribs={"layer": "ANNO-DIM"}).render()
    return doc


def custom_validate(doc: ezdxf.document.Drawing, profile: dict[str, Any]) -> list[dict[str, Any]]:
    errors: list[dict[str, Any]] = []

    def err(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    if doc.header.get("$INSUNITS") != profile["units"]["insunits"]:
        err("UNITS_MISMATCH", f"$INSUNITS={doc.header.get('$INSUNITS')}")
    if doc.header.get("$LWDISPLAY") != profile["units"]["expected_lwdisplay"]:
        err("LWDISPLAY_MISMATCH", f"$LWDISPLAY={doc.header.get('$LWDISPLAY')}")

    linetype_map = {entry.dxf.name.upper(): entry.dxf.name for entry in doc.linetypes}
    linetypes_upper = set(linetype_map)
    for name in profile["required_linetypes"]:
        if name.upper() not in linetypes_upper:
            err("MISSING_LINETYPE", name)

    layers = {entry.dxf.name: entry for entry in doc.layers}
    for name, expected in profile["required_layers"].items():
        if not dxf_validator.is_valid_lineweight(expected["lineweight"]):
            err("PROFILE_LINEWEIGHT_INVALID", f"{name}: configured lineweight {expected['lineweight']} is not a valid DXF lineweight")
        if name not in layers:
            err("MISSING_LAYER", name)
            continue
        layer = layers[name]
        for key in ("color", "linetype", "lineweight"):
            actual = getattr(layer.dxf, key, None)
            if key == "linetype":
                same = str(actual).upper() == str(expected[key]).upper()
            else:
                same = actual == expected[key]
            if not same:
                err("LAYER_PROPERTY_MISMATCH", f"{name}.{key}: expected {expected[key]!r}, got {actual!r}")
        if layer.dxf.linetype.upper() not in linetypes_upper:
            err("UNDEFINED_LAYER_LINETYPE", f"{name}: {layer.dxf.linetype}")
        if not dxf_validator.is_valid_lineweight(layer.dxf.lineweight):
            err("INVALID_LAYER_LINEWEIGHT", f"{name}: {layer.dxf.lineweight}")

    layout_names = set(doc.layouts.names())
    for name in profile["required_layouts"]:
        if name not in layout_names:
            err("MISSING_LAYOUT", name)
    block_names = {b.name for b in doc.blocks}
    for name in profile["required_blocks"]:
        if name not in block_names:
            err("MISSING_BLOCK", name)
    text_styles = {s.dxf.name for s in doc.styles}
    for name in profile["required_text_styles"]:
        if name not in text_styles:
            err("MISSING_TEXT_STYLE", name)
    dimstyles = {s.dxf.name for s in doc.dimstyles}
    for name in profile["required_dimstyles"]:
        if name not in dimstyles:
            err("MISSING_DIMSTYLE", name)

    msp = doc.modelspace()
    counts = Counter(entity.dxf.layer for entity in msp)
    for layer, minimum in profile["entity_requirements"]["modelspace_min_count_by_layer"].items():
        if counts[layer] < minimum:
            err("ENTITY_COUNT_TOO_LOW", f"{layer}: expected >= {minimum}, got {counts[layer]}")

    for entity in msp:
        if entity.dxf.layer not in layers:
            err("ENTITY_LAYER_UNDEFINED", f"{entity.dxftype()} on {entity.dxf.layer}")
        linetype = entity.dxf.get("linetype", "BYLAYER")
        if str(linetype).upper() not in {"BYLAYER", "BYBLOCK"} and str(linetype).upper() not in linetypes_upper:
            err("ENTITY_LINETYPE_UNDEFINED", f"{entity.dxftype()} uses {linetype}")
        if profile.get("entity_properties", {}).get("linetype_policy") == "BYLAYER_ONLY" and str(linetype).upper() != "BYLAYER":
            err("ENTITY_LINETYPE_OVERRIDE", f"{entity.dxftype()} explicitly uses {linetype}; profile requires BYLAYER")
        if entity.dxf.hasattr("lineweight") and not dxf_validator.is_valid_lineweight(entity.dxf.lineweight):
            err("ENTITY_LINEWEIGHT_INVALID", f"{entity.dxftype()} has {entity.dxf.lineweight}")
        if profile.get("entity_properties", {}).get("lineweight_policy") == "BYLAYER_ONLY" and entity.dxf.hasattr("lineweight"):
            err("ENTITY_LINEWEIGHT_OVERRIDE", f"{entity.dxftype()} explicitly overrides layer lineweight with {entity.dxf.lineweight}")
    return errors


def structural_snapshot(doc: ezdxf.document.Drawing) -> dict[str, Any]:
    msp = doc.modelspace()
    return {
        "version": doc.dxfversion,
        "insunits": doc.header.get("$INSUNITS"),
        "lwdisplay": doc.header.get("$LWDISPLAY"),
        "layers": {layer.dxf.name: {"color": layer.dxf.color, "linetype": layer.dxf.linetype, "lineweight": layer.dxf.lineweight} for layer in doc.layers if layer.dxf.name not in {"0", "Defpoints"}},
        "linetypes": sorted({entry.dxf.name for entry in doc.linetypes}),
        "layouts": sorted(doc.layouts.names()),
        "blocks": sorted({block.name for block in doc.blocks if not block.name.startswith("*")}),
        "text_styles": sorted({style.dxf.name for style in doc.styles}),
        "dimstyles": sorted({style.dxf.name for style in doc.dimstyles}),
        "entity_counts_by_layer": dict(sorted(Counter(entity.dxf.layer for entity in msp).items())),
        "entity_types": dict(sorted(Counter(entity.dxftype() for entity in msp).items())),
    }


def run() -> dict[str, Any]:
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    doc = make_document(profile)
    pre_errors = custom_validate(doc, profile)
    doc.saveas(VALID_DXF)
    reopened = ezdxf.readfile(VALID_DXF)
    post_errors = custom_validate(reopened, profile)
    audit = reopened.audit()
    audit_error_count = len(audit.errors)
    audit_fix_count = len(audit.fixes)

    # Adversarial mutation: custom spec violations in an otherwise parseable DXF.
    mutant = ezdxf.readfile(VALID_DXF)
    road = next(e for e in mutant.modelspace() if e.dxf.layer == "C-ROAD-CENTER")
    road.dxf.linetype = "NOT_DEFINED"
    road.dxf.lineweight = 30  # valid DXF value, but violates this profile
    mutant_errors = custom_validate(mutant, profile)
    mutant_codes = sorted({e["code"] for e in mutant_errors})

    # Adversarial profile input: ezdxf normalizes unsupported lineweight values
    # on assignment, so the profile itself must be checked before export.
    bad_profile = copy.deepcopy(profile)
    bad_profile["required_layers"]["C-ROAD-CENTER"]["lineweight"] = 27
    bad_profile_doc = make_document(bad_profile)
    bad_profile_errors = custom_validate(bad_profile_doc, bad_profile)
    bad_profile_codes = sorted({e["code"] for e in bad_profile_errors})
    lineweight_probe_doc = ezdxf.new("R2010", setup=True)
    probe_entity = lineweight_probe_doc.modelspace().add_line((0, 0), (1, 0))
    probe_entity.dxf.lineweight = 27
    lineweight_assignment_stored_value = probe_entity.dxf.lineweight
    invalid_profile_rejected = "PROFILE_LINEWEIGHT_INVALID" in bad_profile_codes

    baseline = structural_snapshot(doc)
    after = structural_snapshot(reopened)
    roundtrip_equal = baseline == after
    expected_mutant_catches = "ENTITY_LINETYPE_UNDEFINED" in mutant_codes and "ENTITY_LINEWEIGHT_OVERRIDE" in mutant_codes

    return {
        "benchmark_id": "LOCAL-CAD-003",
        "version": "0.1",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "status": "local-dxf-roundtrip-probe",
        "environment": {"python": __import__("sys").version.split()[0], "ezdxf": ezdxf.__version__},
        "profile": profile["profile_id"],
        "profile_warning": profile["warning"],
        "valid_fixture": str(VALID_DXF.relative_to(ROOT)),
        "baseline_profile_errors": pre_errors,
        "roundtrip_profile_errors": post_errors,
        "ezdxf_audit_error_count": audit_error_count,
        "ezdxf_audit_fix_count": audit_fix_count,
        "roundtrip_structural_snapshot_equal": roundtrip_equal,
        "roundtrip_snapshot": after,
        "mutant_profile_error_codes": mutant_codes,
        "mutant_custom_validator_catches_expected_violations": expected_mutant_catches,
        "checks": {
            "baseline_profile_valid": len(pre_errors) == 0,
            "roundtrip_profile_valid": len(post_errors) == 0,
            "structural_roundtrip_equal": roundtrip_equal,
            "ezdxf_audit_no_unfixed_errors": audit_error_count == 0,
            "mutant_spec_violations_detected": expected_mutant_catches,
            "invalid_profile_lineweight_rejected": invalid_profile_rejected,
        },
        "bad_profile_error_codes": bad_profile_codes,
        "lineweight_assignment_probe": {"requested": 27, "stored_by_ezdxf": lineweight_assignment_stored_value, "note": "This observed coercion is version-specific behavior; reject invalid profile values before DXF emission."},
        "all_checks_passed": len(pre_errors) == 0 and len(post_errors) == 0 and roundtrip_equal and audit_error_count == 0 and expected_mutant_catches and invalid_profile_rejected,
        "scope_limit": "Synthetic DXF profile only. No real design-office standard, no AutoCAD/LibreCAD third-party open-save roundtrip, no geometry correctness or regulatory compliance claim.",
    }


if __name__ == "__main__":
    result = run()
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({"all_checks_passed": result["all_checks_passed"], "checks": result["checks"], "baseline_errors": result["baseline_profile_errors"], "roundtrip_errors": result["roundtrip_profile_errors"], "audit_errors": result["ezdxf_audit_error_count"], "mutant_codes": result["mutant_profile_error_codes"], "bad_profile_codes": result["bad_profile_error_codes"], "lineweight_probe": result["lineweight_assignment_probe"], "sample": result["valid_fixture"]}, ensure_ascii=False, indent=2))

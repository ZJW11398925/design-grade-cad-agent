#!/usr/bin/env python3
"""Source-backed excerpt probe for Beijing DB11/T 1948-2021.

This is NOT a full compliance validator and the sample coordinates are not
Beijing georeferenced coordinates. It tests whether a profile can carry exact
source-backed layer names/RGB and geometry-topology rules without inventing
unspecified lineweights.
"""
from __future__ import annotations

import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import ezdxf
import yaml
from ezdxf.colors import rgb2int
from shapely.geometry import Polygon

ROOT = Path(__file__).resolve().parents[1]
PROFILE_PATH = ROOT / "db11t1948-profile-extract-v0.1.yaml"
OUT_JSON = ROOT / "local-benchmark-004-db11t1948.json"
SAMPLE_DXF = ROOT / "samples" / "sample-db11t1948-excerpt.dxf"
SAMPLE_MANIFEST = ROOT / "samples" / "sample-db11t1948-excerpt.manifest.json"


def profile_layers(profile: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {rule["value"]["layer_name"]: rule["value"] for rule in profile["rules"] if rule["rule_id"].startswith("DB11-1948-ROAD-")}


def make_doc(profile: dict[str, Any]) -> ezdxf.document.Drawing:
    doc = ezdxf.new("R2010", setup=True)
    doc.header["$INSUNITS"] = 6  # metre; source-backed units rule 2.2.3
    doc.header["$LWDISPLAY"] = 1

    layers = profile_layers(profile)
    for name, attrs in layers.items():
        layer = doc.layers.new(name, dxfattribs={"true_color": rgb2int(tuple(attrs["rgb"]))})
        # The standard does not provide a fixed lineweight for these examples;
        # do not set a fabricated value.

    # Source-backed land-use layers from Appendix B, Table B.1.
    land_layers = {
        "XX_B_GTYDFL_070101_一类城镇住宅用地": [223, 187, 33],
        "XX_B_GTYDFL_070102_二类城镇住宅用地": [255, 255, 45],
    }
    for name, rgb in land_layers.items():
        doc.layers.new(name, dxfattribs={"true_color": rgb2int(tuple(rgb))})

    msp = doc.modelspace()
    msp.add_lwpolyline([(0, 10), (10, 10), (20, 10)], dxfattribs={"layer": "XX_FH_DS_已定道路中线"})
    msp.add_lwpolyline([(0, 8), (20, 8)], dxfattribs={"layer": "XX_FH_DS_已定道路红线"})
    msp.add_lwpolyline([(0, 12), (20, 12)], dxfattribs={"layer": "XX_FH_DS_新定道路红线"})
    msp.add_lwpolyline([(0, 20), (10, 20), (10, 30), (0, 30)], close=True,
                       dxfattribs={"layer": "XX_B_GTYDFL_070101_一类城镇住宅用地"})
    msp.add_lwpolyline([(10, 20), (20, 20), (20, 30), (10, 30)], close=True,
                       dxfattribs={"layer": "XX_B_GTYDFL_070102_二类城镇住宅用地"})
    return doc


def polygon_from_lwpolyline(entity) -> Polygon:
    points = [(p[0], p[1]) for p in entity.get_points("xy")]
    return Polygon(points)


def validate_source_backed_subset(doc: ezdxf.document.Drawing, profile: dict[str, Any]) -> dict[str, Any]:
    errors: list[dict[str, str]] = []
    blocked: list[dict[str, str]] = []

    def err(code: str, detail: str) -> None:
        errors.append({"code": code, "detail": detail})

    def block(code: str, detail: str) -> None:
        blocked.append({"code": code, "detail": detail})

    if doc.header.get("$INSUNITS") != 6:
        err("UNITS_MISMATCH", f"Expected metres (INSUNITS=6), got {doc.header.get('$INSUNITS')}")

    for name, attrs in profile_layers(profile).items():
        if name not in doc.layers:
            err("MISSING_SOURCE_BACKED_LAYER", name)
            continue
        layer = doc.layers.get(name)
        actual_rgb = list(__import__("ezdxf.colors", fromlist=["int2rgb"]).int2rgb(layer.dxf.true_color)) if layer.dxf.hasattr("true_color") else None
        if actual_rgb != attrs["rgb"]:
            err("TRUE_COLOR_MISMATCH", f"{name}: expected {attrs['rgb']}, got {actual_rgb}")

    msp = doc.modelspace()
    linear_layers = set(profile_layers(profile))
    for entity in msp:
        if entity.dxf.layer in linear_layers and entity.dxftype() not in {"LWPOLYLINE", "ARC"}:
            err("LINEAR_ENTITY_TYPE_MISMATCH", f"{entity.dxf.layer}: {entity.dxftype()}")

    area_layers = {
        "XX_B_GTYDFL_070101_一类城镇住宅用地",
        "XX_B_GTYDFL_070102_二类城镇住宅用地",
    }
    area_entities = [e for e in msp if e.dxf.layer in area_layers]
    polygons = []
    for entity in area_entities:
        if entity.dxftype() != "LWPOLYLINE" or not entity.closed:
            err("AREA_NOT_CLOSED_POLYLINE", f"{entity.dxf.layer}: {entity.dxftype()} closed={getattr(entity, 'closed', None)}")
            continue
        polygon = polygon_from_lwpolyline(entity)
        polygons.append((entity.dxf.layer, polygon))
        if not polygon.is_valid:
            err("AREA_SELF_INTERSECTION_OR_INVALID", entity.dxf.layer)

    for i in range(len(polygons)):
        for j in range(i + 1, len(polygons)):
            name_a, poly_a = polygons[i]
            name_b, poly_b = polygons[j]
            if poly_a.intersection(poly_b).area > 1e-9:
                err("ADJACENT_AREA_OVERLAP", f"{name_a} overlaps {name_b} by {poly_a.intersection(poly_b).area:.6f} square metres")

    # This fixture intentionally has only local metric coordinates. It cannot
    # prove the Beijing local plane/elevation coordinate reference requirement.
    block("COORDINATE_REFERENCE_NOT_ESTABLISHED", "Synthetic local coordinates do not prove compliance with clause 2.2.1.")

    # Do not validate lineweight because the selected source rows do not define
    # a fixed numeric lineweight; the source-backed profile marks this as discretionary.
    return {"errors": errors, "blocked": blocked, "all_testable_checks_passed": len(errors) == 0}


def main() -> dict[str, Any]:
    profile = yaml.safe_load(PROFILE_PATH.read_text(encoding="utf-8"))
    doc = make_doc(profile)
    doc.saveas(SAMPLE_DXF)
    reread = ezdxf.readfile(SAMPLE_DXF)
    audit = reread.audit()
    valid_result = validate_source_backed_subset(reread, profile)

    # Mutant: shift the second land-use polygon 0.5 m left, creating an overlap.
    mutant = ezdxf.readfile(SAMPLE_DXF)
    second = next(e for e in mutant.modelspace() if e.dxf.layer == "XX_B_GTYDFL_070102_二类城镇住宅用地")
    points = [(p[0] - 0.5, p[1]) for p in second.get_points("xy")]
    second.set_points(points, format="xy")
    mutant_result = validate_source_backed_subset(mutant, profile)
    mutant_detected = any(e["code"] == "ADJACENT_AREA_OVERLAP" for e in mutant_result["errors"])

    manifest = {
        "artifact": SAMPLE_DXF.name,
        "profile_id": profile["profile_id"],
        "standard_id": "DB11/T 1948-2021",
        "coordinate_state": "synthetic_local_not_beijing_reference",
        "not_a_compliant_beijing_deliverable": True,
        "notes": [
            "Exact selected layer names/RGB are sourced from the official standard excerpt.",
            "No numeric lineweight was fabricated where the source leaves it discretionary.",
            "Coordinate reference requirement 2.2.1 remains blocked because coordinates are synthetic.",
        ],
    }
    SAMPLE_MANIFEST.write_text(json.dumps(manifest, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    return {
        "benchmark_id": "LOCAL-CAD-004",
        "version": "0.1",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "status": "source-backed-profile-excerpt-probe",
        "environment": {"python": __import__("sys").version.split()[0], "ezdxf": ezdxf.__version__},
        "profile_id": profile["profile_id"],
        "source_standard": "DB11/T 1948-2021",
        "source_standard_scope": "Beijing detailed spatial planning only",
        "valid_sample": str(SAMPLE_DXF.relative_to(ROOT)),
        "valid_sample_manifest": str(SAMPLE_MANIFEST.relative_to(ROOT)),
        "ezdxf_audit_errors": len(audit.errors),
        "valid_subset_result": valid_result,
        "mutant_overlap_errors": mutant_result["errors"],
        "mutant_overlap_detected": mutant_detected,
        "lineweight_rule": "not_enforced_for_selected rows because the source leaves line width discretionary in the cited cases",
        "coordinate_reference_rule": "blocked_not_proven_by_synthetic_local_coordinates",
        "all_testable_checks_passed": valid_result["all_testable_checks_passed"] and len(audit.errors) == 0 and mutant_detected,
        "full_profile_compliance": False,
        "scope_limit": "Only a small excerpt was encoded. The sample is not georeferenced to Beijing and must not be represented as compliant with the complete standard.",
    }


if __name__ == "__main__":
    result = main()
    OUT_JSON.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({
        "all_testable_checks_passed": result["all_testable_checks_passed"],
        "full_profile_compliance": result["full_profile_compliance"],
        "ezdxf_audit_errors": result["ezdxf_audit_errors"],
        "valid_errors": result["valid_subset_result"]["errors"],
        "blocked": result["valid_subset_result"]["blocked"],
        "mutant_overlap_detected": result["mutant_overlap_detected"],
        "sample": result["valid_sample"],
    }, ensure_ascii=False, indent=2))

#!/usr/bin/env python3
"""Synthetic validator benchmark for building-footprint regularization.

This does NOT run Building Regulariser or CartAGen. It tests whether the
proposed validator metrics detect known adversarial changes to Shapely geometry.
All coordinates are synthetic metres. No acceptance thresholds are frozen.
"""
from __future__ import annotations

import json
import math
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from shapely import affinity, hausdorff_distance
from shapely.geometry import Polygon, MultiPolygon, box
from shapely.geometry.base import BaseGeometry

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "local-benchmark-002-regularization.json"


def polygons(g: BaseGeometry) -> list[Polygon]:
    if isinstance(g, Polygon):
        return [g]
    if isinstance(g, MultiPolygon):
        return list(g.geoms)
    if hasattr(g, "geoms"):
        return [p for part in g.geoms for p in polygons(part)]
    return []


def component_count(g: BaseGeometry) -> int:
    return len(polygons(g))


def hole_count(g: BaseGeometry) -> int:
    return sum(len(p.interiors) for p in polygons(g))


def iou(a: BaseGeometry, b: BaseGeometry) -> float:
    union = a.union(b).area
    return a.intersection(b).area / union if union else 1.0


def metrics(source: BaseGeometry, candidate: BaseGeometry) -> dict[str, Any]:
    source_area = source.area
    candidate_area = candidate.area
    return {
        "source_valid": bool(source.is_valid),
        "candidate_valid": bool(candidate.is_valid),
        "source_geom_type": source.geom_type,
        "candidate_geom_type": candidate.geom_type,
        "source_components": component_count(source),
        "candidate_components": component_count(candidate),
        "source_holes": hole_count(source),
        "candidate_holes": hole_count(candidate),
        "iou": round(iou(source, candidate), 6),
        "hausdorff_m": round(hausdorff_distance(source.boundary, candidate.boundary, densify=0.25), 6),
        "symmetric_difference_area_m2": round(source.symmetric_difference(candidate).area, 6),
        "relative_area_error": round(abs(candidate_area - source_area) / source_area, 6) if source_area else None,
        "centroid_shift_m": round(source.centroid.distance(candidate.centroid), 6),
        "source_area_m2": round(source_area, 6),
        "candidate_area_m2": round(candidate_area, 6),
    }


def run() -> dict[str, Any]:
    cases: list[dict[str, Any]] = []

    # BEN-BLDG-001: a slightly hand-wobbled rectangle. Candidate is the
    # axis-aligned envelope; useful as a candidate, not assumed correct.
    jitter = Polygon([
        (0.00, 0.00), (5.00, -0.04), (10.00, 0.02), (15.00, -0.03),
        (20.00, 0.00), (20.03, 3.00), (19.98, 6.00), (20.02, 9.00),
        (20.00, 12.00), (15.00, 12.04), (10.00, 11.98), (5.00, 12.03),
        (0.00, 12.00), (-0.03, 9.00), (0.02, 6.00), (-0.02, 3.00),
    ])
    jitter_candidate = jitter.envelope
    cases.append({
        "case_id": "BEN-BLDG-001A",
        "name": "hand-wobbled rectangle -> axis-aligned envelope candidate",
        "purpose": "Check whether low area error alone masks boundary displacement.",
        "synthetic_only": True,
        "metrics": metrics(jitter, jitter_candidate),
        "expected_validator_behavior": "Report a candidate with a full diff; acceptance threshold requires calibration against human-marked intent.",
    })

    # BEN-BLDG-005: intended rotation, but candidate is forcibly axis-aligned.
    rotated = affinity.rotate(box(-10, -5, 10, 5), 17, origin=(0, 0), use_radians=False)
    forced_axis = rotated.envelope
    cases.append({
        "case_id": "BEN-BLDG-005A",
        "name": "intentionally rotated rectangle -> forced global-axis envelope",
        "purpose": "Detect destructive global-axis alignment of an intentional rotation.",
        "synthetic_only": True,
        "metrics": metrics(rotated, forced_axis),
        "expected_validator_behavior": "Do not auto-accept global-axis alignment; preserve trace and request intent evidence or review.",
    })

    # BEN-BLDG-006: U-shaped footprint with a true open recess.
    u_shape = Polygon([(0, 0), (12, 0), (12, 10), (9, 10), (9, 3), (3, 3), (3, 10), (0, 10)])
    u_candidate = u_shape.envelope
    cases.append({
        "case_id": "BEN-BLDG-006A",
        "name": "U-shaped footprint -> bounding rectangle",
        "purpose": "Ensure concavity loss is surfaced, not treated as harmless cleanup.",
        "synthetic_only": True,
        "metrics": metrics(u_shape, u_candidate),
        "expected_validator_behavior": "Flag large concavity loss; require explicit approval before replacing a U/L/courtyard intent.",
    })

    # BEN-BLDG-006B: courtyard represented as a hole.
    courtyard = Polygon([(0, 0), (12, 0), (12, 10), (0, 10)], holes=[[(3, 2), (9, 2), (9, 8), (3, 8)]])
    courtyard_candidate = box(0, 0, 12, 10)
    cases.append({
        "case_id": "BEN-BLDG-006B",
        "name": "courtyard footprint -> solid rectangle",
        "purpose": "Ensure hole-count/topology checks catch courtyard deletion.",
        "synthetic_only": True,
        "metrics": metrics(courtyard, courtyard_candidate),
        "expected_validator_behavior": "Hard reject if a confirmed hole/courtyard disappears without an explicit design change.",
    })

    # BEN-BLDG-008 / issue #8 analogue: two buildings sharing a wall are
    # processed independently and move away from the shared boundary.
    a = box(0, 0, 10, 8)
    b = box(10, 0, 20, 8)
    a_candidate = box(0, 0, 9.95, 8)
    b_candidate = box(10.05, 0, 20, 8)
    cases.append({
        "case_id": "BEN-BLDG-014A",
        "name": "two attached buildings -> independent regularization gap",
        "purpose": "Measure group-topology regression even when each footprint remains individually valid.",
        "synthetic_only": True,
        "source_relation": {"touches": bool(a.touches(b)), "shared_boundary_length_m": round(a.boundary.intersection(b.boundary).length, 6), "distance_m": round(a.distance(b), 6)},
        "candidate_relation": {"touches": bool(a_candidate.touches(b_candidate)), "shared_boundary_length_m": round(a_candidate.boundary.intersection(b_candidate.boundary).length, 6), "distance_m": round(a_candidate.distance(b_candidate), 6), "gap_area_m2": round(box(9.95, 0, 10.05, 8).area, 6)},
        "metrics_a": metrics(a, a_candidate),
        "metrics_b": metrics(b, b_candidate),
        "expected_validator_behavior": "Compare site-level adjacency graph and shared-boundary invariants; individual IoU is insufficient.",
    })

    # BEN-BLDG-008B: two distinct near neighbours must not be merged.
    near_a = box(0, 0, 9.8, 8)
    near_b = box(10.2, 0, 20, 8)
    source_pair = MultiPolygon([near_a, near_b])
    merged = box(0, 0, 20, 8)  # deliberately unauthorized merge candidate
    cases.append({
        "case_id": "BEN-BLDG-015A",
        "name": "two distinct near buildings -> merged candidate",
        "purpose": "Ensure object identity/count is protected against geometry unions.",
        "synthetic_only": True,
        "source_object_count": 2,
        "candidate_object_count": 1,
        "source_component_count": component_count(source_pair),
        "candidate_component_count": component_count(merged),
        "source_gap_m": round(near_a.distance(near_b), 6),
        "metrics": metrics(source_pair, merged),
        "expected_validator_behavior": "Reject an unapproved identity merge; object count and IDs are hard invariants unless the designer explicitly merges them.",
    })

    # BEN-BLDG-007: curved building represented by a sampled arc-like polygon.
    outer = [(10 * math.cos(math.radians(a)), 10 * math.sin(math.radians(a))) for a in range(0, 181, 10)]
    inner = [(7 * math.cos(math.radians(a)), 7 * math.sin(math.radians(a))) for a in range(180, -1, -10)]
    curved = Polygon(outer + inner)
    curved_candidate = curved.minimum_rotated_rectangle
    cases.append({
        "case_id": "BEN-BLDG-007A",
        "name": "curved annular segment -> minimum rotated rectangle",
        "purpose": "Detect destructive loss of intentional curvature.",
        "synthetic_only": True,
        "metrics": metrics(curved, curved_candidate),
        "expected_validator_behavior": "Curvature/segment distribution outside the approved profile should trigger preserve or needs-review, not forced rectification.",
    })

    # BEN-BLDG-009: no height evidence. This is a state-validation case rather
    # than a geometric transform.
    cases.append({
        "case_id": "BEN-BLDG-009A",
        "name": "footprint without height evidence",
        "synthetic_only": True,
        "input": {"footprint_state": "confirmed", "height_source": None, "height_state": "unknown", "floors_source": None, "floors_state": "unknown"},
        "expected_validator_behavior": "2D footprint may pass; 3D body must remain absent or explicitly schematic/proposed and must not invent a confirmed height or floor count.",
    })

    by_id = {case["case_id"]: case for case in cases}
    checks = [
        {
            "check_id": "CHK-01",
            "question": "Can a high per-object IoU hide a broken shared-boundary relation?",
            "observed": bool(by_id["BEN-BLDG-014A"]["metrics_a"]["iou"] >= 0.99
                and by_id["BEN-BLDG-014A"]["metrics_b"]["iou"] >= 0.99
                and by_id["BEN-BLDG-014A"]["source_relation"]["touches"]
                and not by_id["BEN-BLDG-014A"]["candidate_relation"]["touches"]),
            "expected": True,
            "meaning": "Per-object overlap is insufficient; site-level relation checks are required.",
        },
        {
            "check_id": "CHK-02",
            "question": "Can a high global IoU hide a two-object-to-one-object merge?",
            "observed": bool(by_id["BEN-BLDG-015A"]["metrics"]["iou"] >= 0.98
                and by_id["BEN-BLDG-015A"]["source_object_count"] == 2
                and by_id["BEN-BLDG-015A"]["candidate_object_count"] == 1),
            "expected": True,
            "meaning": "Object identity/count is a hard invariant independent of overlap metrics.",
        },
        {
            "check_id": "CHK-03",
            "question": "Does the validator expose a deleted courtyard hole?",
            "observed": bool(by_id["BEN-BLDG-006B"]["metrics"]["source_holes"] == 1
                and by_id["BEN-BLDG-006B"]["metrics"]["candidate_holes"] == 0),
            "expected": True,
            "meaning": "Hole count is a required topology invariant.",
        },
        {
            "check_id": "CHK-04",
            "question": "Does a curved-intent adversarial candidate show large boundary/area deviation?",
            "observed": bool(by_id["BEN-BLDG-007A"]["metrics"]["iou"] < 0.5
                and by_id["BEN-BLDG-007A"]["metrics"]["hausdorff_m"] > 5.0),
            "expected": True,
            "meaning": "Curved outlines need a preserve/review route; no production threshold is implied.",
        },
        {
            "check_id": "CHK-05",
            "question": "Does the no-height-evidence fixture retain unknown height/floor states?",
            "observed": bool(by_id["BEN-BLDG-009A"]["input"]["height_state"] == "unknown"
                and by_id["BEN-BLDG-009A"]["input"]["floors_state"] == "unknown"),
            "expected": True,
            "meaning": "Geometry processing must not fabricate massing evidence.",
        },
    ]
    for check in checks:
        check["passed"] = check["observed"] == check["expected"]

    return {
        "benchmark_id": "LOCAL-BLDG-002",
        "version": "0.1",
        "run_date": datetime.now(timezone.utc).isoformat(),
        "status": "synthetic-validator-probe",
        "execution_scope": "Shapely geometry metric probe only; does not execute Building Regulariser, CartAGen, IfcOpenShell, or any CAD/BIM exporter.",
        "environment": {"shapely": __import__("shapely").__version__},
        "threshold_policy": "No numeric acceptance thresholds frozen. Distances are meaningful only under the synthetic metre coordinate system; real thresholds must be calibrated to source scale, annotation uncertainty, drawing purpose, and reviewed design intent.",
        "checks": checks,
        "all_checks_passed": all(check["passed"] for check in checks),
        "cases": cases,
    }


if __name__ == "__main__":
    result = run()
    OUT.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUT}")
    print("all_checks_passed:", result["all_checks_passed"])
    for check in result["checks"]:
        print(check["check_id"], "PASS" if check["passed"] else "FAIL", "-", check["question"])
    for case in result["cases"]:
        if "metrics" in case:
            m = case["metrics"]
            print(case["case_id"], "IoU", m["iou"], "Hausdorff", m["hausdorff_m"], "area_err", m["relative_area_error"], "components", m["source_components"], "->", m["candidate_components"], "holes", m["source_holes"], "->", m["candidate_holes"])
        elif "metrics_a" in case:
            print(case["case_id"], "source_touch", case["source_relation"]["touches"], "candidate_touch", case["candidate_relation"]["touches"], "gap", case["candidate_relation"]["distance_m"])
        else:
            print(case["case_id"], "state-only check")

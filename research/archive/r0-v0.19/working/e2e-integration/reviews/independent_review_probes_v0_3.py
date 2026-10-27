"""Isolated second-pass probes for E2E-FIXTURE-001 v0.2.

These probes intentionally test cases not present in the packet's internal mutation suite.
They record observed validator behavior; a PASS here means the review script ran, not that
all tested mutations were correctly rejected.
"""
from __future__ import annotations
import json, shutil, sys, tempfile
from pathlib import Path
from datetime import datetime, timezone, timedelta
import ezdxf

HERE = Path(__file__).resolve().parent
E2E = HERE.parent
ROOT = E2E.parents[1]
sys.path.insert(0, str(E2E))
sys.path.insert(0, str(ROOT / "working" / "environment-analysis"))
from dxf_validator import validate_dxf_file, LAYER_SPECS
from solar_shadow import Blocker, SolarPosition, assess_sensor_direct_sun, sampled_direct_sun_hours
from shapely.geometry import box

CAD_IR = json.loads((E2E / "site-fixture-cad-ir-v0.2.json").read_text(encoding="utf-8"))
DXF = E2E / "site-fixture-v0.2.dxf"


def dxf_probe(name, mutator, classification):
    with tempfile.TemporaryDirectory(prefix="cad-review-v03-") as td:
        path = Path(td) / f"{name}.dxf"
        shutil.copy2(DXF, path)
        doc = ezdxf.readfile(path)
        mutator(doc)
        doc.saveas(path)
        result = validate_dxf_file(path, CAD_IR, LAYER_SPECS)
        accepted = bool(result["passed"])
        return {
            "probe": name,
            "classification": classification,
            "validator_passed": accepted,
            "finding": ("FALSE_ACCEPT" if classification == "hard_reject" and accepted else
                        "REJECTED_AS_EXPECTED" if classification == "hard_reject" else
                        "POLICY_GAP_ACCEPTED" if accepted else "POLICY_GAP_REJECTED"),
            "entity_count_modelspace": result["entity_count"],
            "expected_entity_count": result["expected_entity_count"],
            "audit_errors": result["audit_error_count"],
            "audit_fixes": result["audit_fix_count"],
            "all_entities_checked": result["all_entities_checked"],
            "layers_pass": result["layers_pass"],
        }


def main():
    probes = []
    probes.append(dxf_probe("paper-space-rogue-entity", lambda d: d.layouts.get("Layout1").add_line((0, 0), (3, 3)), "hard_reject"))

    def lwpolyline_z(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        ent.dxf.elevation = 123.0
    probes.append(dxf_probe("lwpolyline-elevation-z", lwpolyline_z, "hard_reject"))

    def entity_color_override(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        ent.dxf.color = 1  # Layer is ACI 7; entity override changes displayed color.
    probes.append(dxf_probe("entity-color-override", entity_color_override, "policy_gap"))

    def entity_lineweight_override(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        ent.dxf.lineweight = 211
    probes.append(dxf_probe("entity-lineweight-override", entity_lineweight_override, "policy_gap"))

    def entity_linetype_override(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        ent.dxf.linetype = "CONTINUOUS"  # Visually same today, but no longer BYLAYER.
    probes.append(dxf_probe("entity-linetype-explicit-override", entity_linetype_override, "policy_gap"))

    def entity_truecolor_override(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        ent.dxf.true_color = 0xFF0000
    probes.append(dxf_probe("entity-truecolor-override", entity_truecolor_override, "policy_gap"))

    def circle_z(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "CIRCLE")
        ent.dxf.center = (ent.dxf.center.x, ent.dxf.center.y, 99.0)
    probes.append(dxf_probe("point-marker-z", circle_z, "hard_reject"))

    def text_rotation(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "TEXT")
        ent.dxf.rotation = 90.0
    probes.append(dxf_probe("text-rotation", text_rotation, "policy_gap"))

    def text_z(d):
        ent = next(e for e in d.modelspace() if e.dxftype() == "TEXT")
        ent.dxf.insert = (ent.dxf.insert.x, ent.dxf.insert.y, 99.0)
    probes.append(dxf_probe("text-insert-z", text_z, "hard_reject"))

    probes.append(dxf_probe("extra-unused-layer", lambda d: d.layers.new("UNEXPECTED-EXTRA", dxfattribs={"color": 5}), "policy_gap"))

    # Runtime type checks should reject bool values even though bool subclasses int in Python.
    try:
        Blocker("BOOL-HEIGHT", box(1, 1, 2, 2), height_m=True, height_status="confirmed").validate()
        boolean_height = {"accepted": True, "finding": "FALSE_ACCEPT"}
    except Exception as exc:
        boolean_height = {"accepted": False, "finding": "REJECTED_AS_EXPECTED", "error": str(exc)}

    boolean_sensor = assess_sensor_direct_sun(
        (True, 0.0), 0.0, SolarPosition(45.0, 180.0, 0.0, 0.0), [],
        project_y_axis_bearing_deg=0.0, context_complete=True,
    )

    zenith = assess_sensor_direct_sun(
        (0.0, 0.0), 0.0, SolarPosition(90.0, 180.0, 23.4, 0.0), [],
        project_y_axis_bearing_deg=0.0, context_complete=True,
    )
    t0 = datetime(2026, 6, 21, 12, tzinfo=timezone.utc)
    duration = []
    for n in (1, 2, 3):
        times = [t0 + timedelta(hours=i) for i in range(n)]
        result = sampled_direct_sun_hours(
            (0.0, 0.0), 0.0, times, 0.0, 0.0, [], timestep_hours=1.0,
            project_y_axis_bearing_deg=0.0, context_complete=True,
        )
        duration.append({"sample_count": n, "reported_hours": result["lower_bound_hours"], "upper_bound_hours": result["upper_bound_hours"]})

    out = {
        "review_id": "REVIEW-E2E-FIXTURE-001-R2-ISOLATED-PASS-01",
        "review_mode": "isolated second-pass by same assistant session; not external review",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "manifest_hash_verification": "PASS (33/33 artifacts verified separately before probes)",
        "dxf_probes": probes,
        "input_type_probes": {
            "boolean_confirmed_height": boolean_height,
            "boolean_sensor_coordinate": {"input": [True, 0.0], "observed_status": boolean_sensor["status"], "accepted": True},
        },
        "solar_zenith_probe": {
            "elevation_deg": 90.0,
            "observed": zenith,
            "expected_status_for_clear_context": "confirmed_sunlit_given_declared_context",
            "finding": "FALSE_UNKNOWN" if zenith["status"] == "invalid_solar_vector" else "NO_FALSE_UNKNOWN",
        },
        "duration_interval_probe": {
            "samples": duration,
            "observed_rule": "reported duration equals sample_count * timestep_hours",
            "open_question": "Must the API contract explicitly declare every timestamp as the start of a following interval, including the final sample?",
        },
        "summary": {
            "dxf_hard_false_accepts": sum(p["finding"] == "FALSE_ACCEPT" for p in probes),
            "dxf_policy_gaps_accepted": sum(p["finding"] == "POLICY_GAP_ACCEPTED" for p in probes),
            "dxf_probes": len(probes),
            "zenith_false_unknown": zenith["status"] == "invalid_solar_vector",
            "boolean_height_false_accept": boolean_height["accepted"],
            "boolean_sensor_coordinate_accepted": True,
            "external_review_completed": False,
            "status": "conditional",
        },
    }
    target = HERE / "independent-review-results-v0.3.json"
    target.write_text(json.dumps(out, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")
    print(json.dumps(out["summary"], ensure_ascii=False, indent=2))
    for p in probes:
        print(p["probe"], p["finding"], "validator_passed=", p["validator_passed"])
    print("boolean height", boolean_height)
    print("boolean sensor coordinate", boolean_sensor["status"])
    print("zenith", out["solar_zenith_probe"]["finding"], zenith["status"])
    print("duration", duration)
    print("result", target)

if __name__ == "__main__":
    main()

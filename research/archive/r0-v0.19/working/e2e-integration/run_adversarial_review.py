"""Adversarial regression probes for E2E-FIXTURE-001 R2.

Runs mutations in temporary copies so the canonical fixture and DXF are untouched.
These probes are an internal adversarial audit, not an external independent review.
"""
from __future__ import annotations
import copy, hashlib, json, shutil, sys, tempfile, io
from contextlib import redirect_stdout
from pathlib import Path
import ezdxf

ROOT = Path(__file__).resolve().parent
WORKING = ROOT.parent
ENV_MODULE = WORKING / "environment-analysis" / "solar_shadow.py"
sys.path.insert(0, str(ROOT))
import run_fixture_benchmark_v0_2 as env_runner  # noqa: E402
import compile_fixture_to_dxf_v0_2 as dxf_compiler  # noqa: E402
import dxf_validator as dxf_validator_module  # noqa: E402


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode()).hexdigest()


def write_json(path, obj):
    path.write_text(json.dumps(obj, ensure_ascii=False, indent=2, allow_nan=False) + "\n", encoding="utf-8")


def run_height_mutation(name, mutate):
    tmp = Path(tempfile.mkdtemp(prefix=f"e2e-review-{name}-"))
    (tmp / "environment-analysis").mkdir()
    (tmp / "e2e-integration").mkdir()
    shutil.copy2(ENV_MODULE, tmp / "environment-analysis" / "solar_shadow.py")
    shutil.copy2(ROOT / "run_fixture_benchmark_v0_2.py", tmp / "e2e-integration" / "run_fixture_benchmark_v0_2.py")
    fixture = json.loads((ROOT / "site-fixture-v0.2.json").read_text(encoding="utf-8"))
    mutate(fixture, next(o for o in fixture["objects"] if o["object_id"] == "BLDG-01"))
    write_json(tmp / "e2e-integration" / "site-fixture-v0.2.json", fixture)
    previous_root = env_runner.ROOT
    try:
        env_runner.ROOT = tmp / "e2e-integration"
        with redirect_stdout(io.StringIO()):
            result = env_runner.run()
    finally:
        env_runner.ROOT = previous_root
    return {"name": name, "status": result["status"], "fingerprint": result["dependency_fingerprint_sha256"], "sensor_statuses": {r["sensor_id"]: r["actual"]["status"] for r in result["sensor_results"]}, "body_checks_pass": all(c["passed"] for c in result["stored_body_mesh_checks"])}


def run():
    base_env = json.loads((ROOT / "local-e2e-fixture-env-002.json").read_text(encoding="utf-8"))
    base_fingerprint = base_env["dependency_fingerprint_sha256"]
    height_probe = run_height_mutation("height-value", lambda f, o: o["massing"].update(height_m=5.0))
    state_probe = run_height_mutation("height-state", lambda f, o: (o["massing"].update(height_state="estimated"), o["massing"].update(height_m=22.0)))
    base_elev_probe = run_height_mutation("base-elevation", lambda f, o: o["massing"].update(base_elevation_m=1.0))
    body_probe = run_height_mutation("body-geometry", lambda f, o: o["representations"]["body_3d"]["geometry"]["vertices"][4].__setitem__(0, 12.5))
    body_bottom_probe = run_height_mutation("body-bottom-vertex", lambda f, o: o["representations"]["body_3d"]["geometry"]["vertices"][0].__setitem__(2, 0.5))

    # Hole preservation probe: add an interior ring to green space and compile a temporary CAD-IR.
    tmp = Path(tempfile.mkdtemp(prefix="e2e-review-hole-r2-"))
    for folder in ["e2e-integration", "environment-analysis"]:
        (tmp / folder).mkdir()
    for name in ["compile_fixture_to_dxf_v0_2.py", "dxf_validator.py"]:
        shutil.copy2(ROOT / name, tmp / "e2e-integration" / name)
    shutil.copy2(ROOT / "local-e2e-fixture-env-002.json", tmp / "e2e-integration" / "local-e2e-fixture-env-002.json")
    cad_ir = json.loads((ROOT / "site-fixture-cad-ir-v0.2.json").read_text(encoding="utf-8"))
    green = next(o for o in cad_ir["objects"] if o["object_id"] == "GREEN-AREA-01")
    green["geometry_data"]["coordinates"].append([[8, 3], [8, 4], [10, 4], [10, 3], [8, 3]])
    green["geometry_content_hash_sha256"] = canonical_hash(green["geometry_data"])
    write_json(tmp / "e2e-integration" / "site-fixture-cad-ir-v0.2.json", cad_ir)
    with redirect_stdout(io.StringIO()):
        hole_manifest = dxf_compiler.compile_fixture_to_dxf(
            tmp / "e2e-integration" / "site-fixture-cad-ir-v0.2.json",
            tmp / "e2e-integration" / "local-e2e-fixture-env-002.json",
            tmp / "e2e-integration" / "hole-test.dxf",
            tmp / "e2e-integration" / "hole-test-manifest.json",
        )
    hole_doc = ezdxf.readfile(str(tmp / "e2e-integration" / "hole-test.dxf"))
    green_roles = []
    for e in hole_doc.modelspace():
        if e.has_xdata("DESIGN_GRADE"):
            vals = [tag.value for tag in e.get_xdata("DESIGN_GRADE") if tag.code == 1000]
            if vals and vals[0] == "GREEN-AREA-01":
                green_roles.append(vals[8])

    # Mutations to a valid artifact must be caught by the separate code-path validator.
    sys.path.insert(0, str(ROOT))
    validate_dxf_file, LAYER_SPECS = dxf_validator_module.validate_dxf_file, dxf_validator_module.LAYER_SPECS
    base_cad_ir = json.loads((ROOT / "site-fixture-cad-ir-v0.2.json").read_text(encoding="utf-8"))
    base_dxf = ROOT / "site-fixture-v0.2.dxf"
    baseline_validation = validate_dxf_file(base_dxf, base_cad_ir, LAYER_SPECS)

    def mutated_dxf(name, mutator):
        p = tmp / f"mutated-{name}.dxf"
        shutil.copy2(base_dxf, p)
        doc = ezdxf.readfile(str(p))
        mutator(doc)
        doc.saveas(p)
        val = validate_dxf_file(p, base_cad_ir, LAYER_SPECS)
        return {"name": name, "validator_status": val["status"], "passed": val["passed"], "layer_pass": val["layers_pass"], "all_objects_pass": val["all_object_checks_pass"], "entity_count": val["entity_count"], "expected_entity_count": val["expected_entity_count"]}

    profile_mutation = mutated_dxf("layer-lineweight", lambda d: setattr(d.layers.get("L-GREEN").dxf, "lineweight", 25))
    units_mutation = mutated_dxf("units", lambda d: d.header.__setitem__("$INSUNITS", ezdxf.units.MM))
    text_mutation = mutated_dxf("label-text", lambda d: next(e for e in d.modelspace() if e.dxftype() == "TEXT" and e.dxf.text == "SENSOR-GREEN-01").dxf.__setattr__("text", "WRONG-LABEL"))
    rogue_mutation = mutated_dxf("rogue-entity", lambda d: d.modelspace().add_circle((100, 100), radius=1, dxfattribs={"layer": "L-GREEN"}))
    def move_building_vertex(doc):
        entity = next(e for e in doc.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")
        pts = [tuple(p[:2]) for p in entity.get_points("xy")]
        pts[0] = (pts[0][0] + 0.5, pts[0][1])
        entity.set_points(pts, format="xy")
    geometry_mutation = mutated_dxf("polyline-coordinate", move_building_vertex)

    probes = {
        "base_fingerprint": base_fingerprint,
        "base_dependency_revision_checks": base_env["revision_checks"],
        "all_base_dependency_revision_checks_pass": all(base_env["revision_checks"].values()),
        "baseline_dxf_validation": {"status": baseline_validation["status"], "passed": baseline_validation["passed"], "entity_count": baseline_validation["entity_count"], "expected_entity_count": baseline_validation["expected_entity_count"], "layers_pass": baseline_validation["layers_pass"], "units_pass": baseline_validation["units_pass"]},
        "height_value_mutation": height_probe,
        "height_state_mutation": state_probe,
        "base_elevation_mutation": base_elev_probe,
        "body_geometry_mutation": body_probe,
        "body_bottom_vertex_mutation": body_bottom_probe,
        "dependency_mutations_change_fingerprint": all(x["fingerprint"] != base_fingerprint for x in [height_probe, state_probe, base_elev_probe, body_probe, body_bottom_probe]),
        "polygon_hole_export": {"compile_status": hole_manifest["status"], "manifest_status": hole_manifest["status"], "green_ring_roles": green_roles, "hole_ring_preserved": "hole" in green_roles},
        "profile_mutation_detected": not profile_mutation["passed"],
        "units_mutation_detected": not units_mutation["passed"],
        "text_mutation_detected": not text_mutation["passed"],
        "rogue_entity_detected": not rogue_mutation["passed"],
        "geometry_mutation_detected": not geometry_mutation["passed"],
        "dxf_mutations": [profile_mutation, units_mutation, text_mutation, rogue_mutation, geometry_mutation],
    }
    probes["all_adversarial_probes_pass"] = (
        probes["dependency_mutations_change_fingerprint"]
        and probes["all_base_dependency_revision_checks_pass"]
        and probes["body_bottom_vertex_mutation"]["body_checks_pass"] is False
        and probes["polygon_hole_export"]["hole_ring_preserved"]
        and probes["baseline_dxf_validation"]["passed"]
        and probes["profile_mutation_detected"] and probes["units_mutation_detected"] and probes["text_mutation_detected"]
        and probes["rogue_entity_detected"] and probes["geometry_mutation_detected"]
    )
    out = ROOT / "adversarial-review-results-v0.2.json"
    write_json(out, probes)
    print(json.dumps({k: v for k, v in probes.items() if k != "dxf_mutations"}, ensure_ascii=False, indent=2))
    print("dxf_mutations:", json.dumps(probes["dxf_mutations"], ensure_ascii=False))
    return probes


if __name__ == "__main__":
    result = run()
    raise SystemExit(0 if result["all_adversarial_probes_pass"] else 1)

from __future__ import annotations
import json, shutil, sys
from pathlib import Path
import ezdxf
import pytest

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from dxf_validator_v0_3 import validate_dxf_file, LAYER_SPECS

CAD_IR = json.loads((ROOT / "site-fixture-cad-ir-v0.3.json").read_text(encoding="utf-8"))
BASE_DXF = ROOT / "site-fixture-v0.3.dxf"


def mutate_and_validate(tmp_path, name, mutator):
    path = tmp_path / f"{name}.dxf"
    shutil.copy2(BASE_DXF, path)
    doc = ezdxf.readfile(path)
    mutator(doc)
    doc.saveas(path)
    return validate_dxf_file(path, CAD_IR, LAYER_SPECS)


def building_polyline(doc):
    return next(e for e in doc.modelspace() if e.dxftype() == "LWPOLYLINE" and e.dxf.layer == "A-BUILDING-OUTLINE")


def test_v03_baseline_passes():
    result = validate_dxf_file(BASE_DXF, CAD_IR, LAYER_SPECS)
    assert result["passed"] is True
    assert result["entity_count"] == result["expected_entity_count"] == 11
    assert result["non_modelspace_entity_count"] == 0
    assert result["unexpected_layers"] == []


def test_paper_space_entity_is_rejected(tmp_path):
    result = mutate_and_validate(tmp_path, "paper-space", lambda d: d.layouts.get("Layout1").add_line((0, 0), (3, 3)))
    assert result["passed"] is False
    assert result["layout_scope_pass"] is False
    assert result["non_modelspace_entity_count"] == 1


def test_nonzero_lwpolyline_elevation_is_rejected(tmp_path):
    result = mutate_and_validate(tmp_path, "polyline-z", lambda d: setattr(building_polyline(d).dxf, "elevation", 123.0))
    assert result["passed"] is False
    checks = result["object_checks"]["BLDG-01"]["entity_checks"]
    assert any(not x.get("world_xy_plane_pass", True) for x in checks)


def test_nonzero_circle_z_is_rejected(tmp_path):
    def mutation(d):
        e = next(x for x in d.modelspace() if x.dxftype() == "CIRCLE")
        e.dxf.center = (e.dxf.center.x, e.dxf.center.y, 99.0)
    result = mutate_and_validate(tmp_path, "circle-z", mutation)
    assert result["passed"] is False


def test_nonzero_text_z_is_rejected(tmp_path):
    def mutation(d):
        e = next(x for x in d.modelspace() if x.dxftype() == "TEXT")
        e.dxf.insert = (e.dxf.insert.x, e.dxf.insert.y, 99.0)
    result = mutate_and_validate(tmp_path, "text-z", mutation)
    assert result["passed"] is False


@pytest.mark.parametrize("name,attribute,value", [
    ("color", "color", 1),
    ("lineweight", "lineweight", 211),
    ("linetype", "linetype", "CONTINUOUS"),
    ("true-color", "true_color", 0xFF0000),
])
def test_entity_style_overrides_are_rejected(tmp_path, name, attribute, value):
    def mutation(d):
        building_polyline(d).dxf.set(attribute, value)
    result = mutate_and_validate(tmp_path, f"style-{name}", mutation)
    assert result["passed"] is False


def test_text_rotation_is_rejected(tmp_path):
    def mutation(d):
        e = next(x for x in d.modelspace() if x.dxftype() == "TEXT")
        e.dxf.rotation = 90.0
    result = mutate_and_validate(tmp_path, "text-rotation", mutation)
    assert result["passed"] is False


def test_extra_layer_is_rejected(tmp_path):
    result = mutate_and_validate(tmp_path, "extra-layer", lambda d: d.layers.new("UNEXPECTED-EXTRA", dxfattribs={"color": 5}))
    assert result["passed"] is False
    assert "UNEXPECTED-EXTRA" in result["unexpected_layers"]


def test_mismatched_profile_reference_or_version_is_rejected():
    cad_ir = json.loads((ROOT / "site-fixture-cad-ir-v0.3.json").read_text(encoding="utf-8"))
    cad_ir["project"]["profile_version"] = "0.1.0"
    result = validate_dxf_file(BASE_DXF, cad_ir, LAYER_SPECS)
    assert result["passed"] is False
    assert result["profile_ref_pass"] is False

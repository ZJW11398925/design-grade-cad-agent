"""Regression tests for the deterministic SVG visual deliverables.

Uses small in-memory fake layouts (no pipeline run): the renderers must be
pure, deterministic (same bytes on every render), UTF-8/LF, self-describing
(legend/title/candidate ids) and safe for the CLI wrappers.
"""
from __future__ import annotations

import hashlib
import importlib.util
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

import pytest
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dgcad_design.buildings import BuildingLayout, StandardBuilding  # noqa: E402
from dgcad_design.green import GreenDesign, GreenLayout  # noqa: E402
from dgcad_design.roads import RoadDesign, RoadLayout  # noqa: E402
from dgcad_design.visuals import (  # noqa: E402
    render_candidate_comparison_svg,
    render_overlay_svg,
    render_plan_svg,
)


# ---------------------------------------------------------------------------
# fake layouts
# ---------------------------------------------------------------------------


def _building(building_id: str, x0: float, y0: float,
              x1: float, y1: float) -> StandardBuilding:
    footprint = box(x0, y0, x1, y1)
    return StandardBuilding(
        building_id=building_id,
        unit_count=2,
        is_facility=False,
        footprint=footprint,
        unit_lines=(),
        households=22,
        gfa_m2=264.0,
        height_m=33.0,
        source_centroid=(footprint.centroid.x, footprint.centroid.y),
        design_centroid=(footprint.centroid.x, footprint.centroid.y),
        displacement_m=0.0,
        source_area_m2=footprint.area,
        source_orientation_deg=0.0,
        design_orientation_deg=0.0,
        subgroup_id="FOCUS-1",
        row_index=0,
        label_anchor=(x1, y1),
    )


def fake_building_layout() -> BuildingLayout:
    buildings = (
        _building("SK-BLD-0001", 10.0, 10.0, 30.0, 21.0),
        _building("SK-BLD-0002", 10.0, 30.0, 30.0, 41.0),
    )
    return BuildingLayout(
        buildings=buildings,
        focus_buildings=buildings,
        rows=(),
        green_strips=(),
        dropped_focus_building_ids=(),
    )


def _road(edge_id: str, class_name: str, width_m: float,
          coordinates, **overrides) -> RoadDesign:
    centerline = LineString(coordinates)
    corridor = centerline.buffer(width_m / 2.0, cap_style=2)
    payload = dict(
        edge_id=edge_id,
        class_name=class_name,
        width_m=width_m,
        centerline=centerline,
        corridor=corridor,
        is_new_connector=class_name != "main",
        reason="test fixture",
        source_edge_ids=(),
        source_trace_ref=None,
        start_junction_id=None,
        end_junction_id=None,
        serves_group_ids=(),
        access_terminal_xy=None,
    )
    payload.update(overrides)
    return RoadDesign(**payload)


def fake_road_layout(main_shift: float = 0.0) -> RoadLayout:
    roads = (
        _road("MAIN-01", "main", 12.0,
              [(0.0, 0.0), (60.0, main_shift), (120.0, main_shift)]),
        _road("BR-G-01", "branch", 7.0, [(60.0, 0.0), (60.0, 40.0)]),
    )
    corridors = unary_union([road.corridor for road in roads])
    return RoadLayout(
        roads=roads,
        corridor_union=corridors,
        sidewalk_union=Polygon(),
        junction_nodes=(),
        dead_end_nodes=(),
        corridor_generator="test",
        not_professional_alignment=True,
        corridor_union_pieces=1,
        noded_topology=None,
        explicit_junctions=(),
        simplification={},
        road_building_overlap_m2_new_access=0.0,
        road_building_overlap_m2_main=0.0,
        road_building_overlap_m2_total=0.0,
        group_access_unserved=(),
        main_alignment_records=(
            {
                "road_id": "MAIN-01",
                "overlap_before_m2": 4.0,
                "overlap_after_m2": 0.0,
                "max_displacement_m": main_shift or 0.0,
            },
        ) if main_shift else (),
        dead_end_resolutions=(),
        road_building_overlap_m2_main_after=0.0,
        main_overlap_resolved=True,
    )


def fake_green_layout() -> GreenLayout:
    green = GreenDesign(
        green_id="G-001",
        geometry=box(70.0, 10.0, 100.0, 30.0),
        classification="cluster_green",
        area_m2=600.0,
        label_anchor=(85.0, 20.0),
    )
    return GreenLayout(
        greens=(green,),
        focus_greens=(green,),
        cluster_area_m2=600.0,
        strip_area_m2=0.0,
        supplementary_area_m2=0.0,
        candidate_open_space_area_m2=600.0,
        candidate_open_space_ratio=0.5,
        unbuilt_area_m2=500.0,
        unbuilt_ratio=0.4,
        designed_green_area_m2=600.0,
        designed_green_ratio=0.5,
        target_ratio=0.3,
        dropped_cluster_ids=(),
    )


def fake_models(main_shift: float = 0.0) -> dict:
    return {
        "building_layout": fake_building_layout(),
        "road_layout": fake_road_layout(main_shift),
        "green_layout": fake_green_layout(),
        "site_boundary": box(-10.0, -10.0, 140.0, 60.0),
        "focus_bbox": (0.0, 0.0, 120.0, 41.0),
    }


# ---------------------------------------------------------------------------
# A. plan SVG
# ---------------------------------------------------------------------------


def _read_svg(path: Path) -> str:
    data = path.read_bytes()
    assert b"\r\n" not in data, "SVG must use LF newlines"
    return data.decode("utf-8")


def _assert_valid_svg(path: Path) -> None:
    tree = ET.parse(path)
    assert tree.getroot().tag.endswith("svg")


def test_plan_svg_is_deterministic_and_describes_the_scene(tmp_path):
    models = fake_models()
    first = render_plan_svg(
        models["building_layout"], models["road_layout"],
        green_layout=models["green_layout"],
        site_boundary=models["site_boundary"],
        focus_bbox=models["focus_bbox"],
        path=tmp_path / "a.svg", title="Plan A")
    second = render_plan_svg(
        models["building_layout"], models["road_layout"],
        green_layout=models["green_layout"],
        site_boundary=models["site_boundary"],
        focus_bbox=models["focus_bbox"],
        path=tmp_path / "b.svg", title="Plan A")

    assert Path(first["path"]).is_file() and first["bytes"] > 1000
    assert hashlib.sha256(Path(first["path"]).read_bytes()).hexdigest() == first["sha256"]
    assert Path(first["path"]).read_bytes() == Path(second["path"]).read_bytes()
    assert first["counts"] == {"buildings": 2, "roads": 2, "green": 1,
                               "main_roads": 1, "centerlines": 2}
    assert len(first["bounds"]) == 4

    svg = _read_svg(Path(first["path"]))
    for expected in ("<svg", "Plan A", "Legend", "Building", "Main road",
                     "Branch road", "Access road", "Green space", "N</text>"):
        assert expected in svg, expected
    _assert_valid_svg(Path(first["path"]))


def test_plan_svg_without_optional_layers_is_valid(tmp_path):
    models = fake_models()
    artifact = render_plan_svg(models["building_layout"], models["road_layout"],
                               path=tmp_path / "bare.svg", title="Bare plan")
    svg = _read_svg(Path(artifact["path"]))
    assert "Green space" in svg  # legend entry is always present
    assert artifact["counts"]["green"] == 0
    _assert_valid_svg(Path(artifact["path"]))


# ---------------------------------------------------------------------------
# B. overlay SVG
# ---------------------------------------------------------------------------


def test_overlay_marks_changed_main_road_and_displacement(tmp_path):
    base = {"building_layout": fake_building_layout(),
            "roads": [{"edge_id": "MAIN-01", "class_name": "main",
                       "width_m": 12.0,
                       "centerline": LineString([(0.0, 0.0), (60.0, 0.0),
                                                 (120.0, 0.0)])}]}
    candidate = {
        "building_layout": fake_building_layout(),
        "road_layout": fake_road_layout(main_shift=5.0),
        "alignment_records": [
            {"road_id": "MAIN-01", "overlap_before_m2": 4.0,
             "overlap_after_m2": 0.0, "max_displacement_m": 5.0},
        ],
    }
    artifact = render_overlay_svg(base, candidate, path=tmp_path / "overlay.svg",
                                 title="Overlay")
    svg = _read_svg(Path(artifact["path"]))
    assert "MAIN-01" in svg
    assert "displacement vector" in svg
    assert "before" in svg and "after" in svg
    assert "Adjusted main roads" in svg
    assert artifact["changed_roads"] and artifact["changed_roads"][0]["edge_id"] == "MAIN-01"
    assert artifact["changed_roads"][0]["max_displacement_m"] == pytest.approx(5.0, abs=0.2)
    _assert_valid_svg(Path(artifact["path"]))

    again = render_overlay_svg(base, candidate, path=tmp_path / "overlay2.svg",
                               title="Overlay")
    assert Path(artifact["path"]).read_bytes() == Path(again["path"]).read_bytes()


def test_overlay_falls_back_to_alignment_records(tmp_path):
    # Base and candidate road geometry identical (rendered on the committed
    # design), but the alignment records still describe the before/after lines.
    same = {"edge_id": "MAIN-01", "class_name": "main", "width_m": 12.0,
            "centerline": LineString([(0.0, 0.0), (60.0, 0.0), (120.0, 0.0)])}
    base = {"building_layout": fake_building_layout(), "roads": [same]}
    candidate = {
        "building_layout": fake_building_layout(),
        "roads": [same],
        "alignment_records": [
            {
                "road_id": "MAIN-01",
                "overlap_before_m2": 4.0,
                "overlap_after_m2": 0.0,
                "max_displacement_m": 6.0,
                "original_centerline": [(0.0, 0.0), (60.0, 0.0), (120.0, 0.0)],
                "adjusted_centerline": [(0.0, 0.0), (60.0, 6.0), (120.0, 6.0)],
            },
        ],
    }
    artifact = render_overlay_svg(base, candidate, path=tmp_path / "fallback.svg")
    svg = _read_svg(Path(artifact["path"]))
    assert artifact["changed_roads"]
    assert artifact["changed_roads"][0]["edge_id"] == "MAIN-01"
    assert artifact["changed_roads"][0]["source"] == "alignment_record"
    assert "MAIN-01" in svg and "6 m" in svg
    _assert_valid_svg(Path(artifact["path"]))


def test_overlay_skips_when_no_geometry(tmp_path):
    with pytest.raises(ValueError):
        render_overlay_svg({}, {}, path=tmp_path / "empty.svg")


# ---------------------------------------------------------------------------
# C. candidate comparison
# ---------------------------------------------------------------------------


def _candidate(candidate_id: str, shift: float, *, hard: bool,
               overlap: float, main_len: float) -> dict:
    return {
        "candidate_id": candidate_id,
        "strategy": f"strategy-{candidate_id}",
        "models": fake_models(main_shift=shift),
        "metrics": {
            "hard_pass": hard,
            "max_displacement_m": shift,
            "main_length_m": main_len,
            "road_building_overlap_m2_total": overlap,
        },
    }


def test_candidate_comparison_grid_contains_ids_and_metrics(tmp_path):
    candidates = [
        _candidate("C2", 0.0, hard=True, overlap=1.25, main_len=2100.0),
        _candidate("C1", 12.5, hard=False, overlap=3.5, main_len=2150.0),
    ]
    artifact = render_candidate_comparison_svg(candidates,
                                               path=tmp_path / "cmp.svg",
                                               title="Candidate comparison")
    svg = _read_svg(Path(artifact["path"]))
    assert artifact["candidate_ids"] == ["C1", "C2"]  # sorted, deterministic
    assert artifact["shown"] == 2
    for expected in ("Candidate comparison", "C1", "C2", "strategy-C1",
                     "hard: pass", "hard: FAIL", "main length", "overlap",
                     "2x2"):
        assert expected in svg, expected
    _assert_valid_svg(Path(artifact["path"]))

    again = render_candidate_comparison_svg(candidates,
                                            path=tmp_path / "cmp2.svg",
                                            title="Candidate comparison")
    assert Path(artifact["path"]).read_bytes() == Path(again["path"]).read_bytes()


def test_candidate_comparison_truncates_to_four(tmp_path):
    candidates = [_candidate(f"C{i}", float(i), hard=True, overlap=float(i),
                             main_len=2000.0 + i) for i in range(1, 6)]
    artifact = render_candidate_comparison_svg(candidates,
                                               path=tmp_path / "cmp5.svg")
    svg = _read_svg(Path(artifact["path"]))
    assert artifact["shown"] == 4
    assert artifact["candidate_ids"] == [f"C{i}" for i in range(1, 6)]
    assert "only the first 4" in svg


def test_candidate_comparison_renders_detail_lines(tmp_path):
    detail_lines = [
        "main deviation: 0 m (unchanged)",
        "branch/access deviation: max 12.5 m (2 roads)",
        "G-08 terminal displacement: 3.5 m",
        "buildings moved: 3",
    ]
    candidate = _candidate("D1", 12.5, hard=True, overlap=0.55, main_len=2126.0)
    candidate["metrics"]["detail_lines"] = detail_lines
    artifact = render_candidate_comparison_svg([candidate],
                                               path=tmp_path / "detail.svg",
                                               title="Detail comparison")
    svg = _read_svg(Path(artifact["path"]))
    for line in detail_lines:
        assert line in svg, line
    assert svg.count('font-size="10.5"') == len(detail_lines)
    _assert_valid_svg(Path(artifact["path"]))

    again = render_candidate_comparison_svg([candidate],
                                            path=tmp_path / "detail2.svg",
                                            title="Detail comparison")
    assert Path(artifact["path"]).read_bytes() == Path(again["path"]).read_bytes()


def test_candidate_comparison_detail_lines_are_backward_compatible(tmp_path):
    # no detail_lines key vs an explicit empty list must render byte-identically
    without = _candidate("B1", 0.0, hard=True, overlap=1.0, main_len=2100.0)
    empty = _candidate("B1", 0.0, hard=True, overlap=1.0, main_len=2100.0)
    empty["metrics"]["detail_lines"] = []
    first = render_candidate_comparison_svg([without], path=tmp_path / "a.svg")
    second = render_candidate_comparison_svg([empty], path=tmp_path / "b.svg")
    assert Path(first["path"]).read_bytes() == Path(second["path"]).read_bytes()
    assert 'font-size="10.5"' not in _read_svg(Path(first["path"]))

    # a candidate with detail lines differs only by those rendered lines
    detail = _candidate("B1", 0.0, hard=True, overlap=1.0, main_len=2100.0)
    detail["metrics"]["detail_lines"] = ["G-08 terminal displacement: 3.5 m"]
    third = render_candidate_comparison_svg([detail], path=tmp_path / "c.svg")
    plain_svg = _read_svg(Path(first["path"]))
    detail_svg = _read_svg(Path(third["path"]))
    assert "G-08 terminal displacement: 3.5 m" in detail_svg
    assert "G-08 terminal displacement" not in plain_svg


def test_candidate_comparison_detail_lines_limited_to_six(tmp_path):
    candidate = _candidate("L1", 0.0, hard=True, overlap=0.0, main_len=2000.0)
    candidate["metrics"]["detail_lines"] = [f"detail-{i}" for i in range(10)]
    artifact = render_candidate_comparison_svg([candidate],
                                               path=tmp_path / "limited.svg")
    svg = _read_svg(Path(artifact["path"]))
    assert svg.count('font-size="10.5"') == 6
    assert "detail-5" in svg
    assert "detail-6" not in svg


# ---------------------------------------------------------------------------
# D. script import / dry-run
# ---------------------------------------------------------------------------


def _load_script(relpath: str):
    path = ROOT / relpath
    spec = importlib.util.spec_from_file_location(path.stem, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_render_visuals_script_imports_without_side_effects():
    module = _load_script("scripts/design/render_visuals.py")
    assert callable(module.main)
    assert callable(module.build_models)
    assert callable(module.render_png)


def test_run_candidate_synthesis_dry_run_reports_interface(tmp_path, capsys):
    module = _load_script("scripts/design/run_candidate_synthesis.py")
    assert callable(module.main)
    exit_code = module.main([
        "--candidate-id", "C1",
        "--dry-run",
        "--output-root", str(tmp_path / "candidates"),
    ])
    assert exit_code == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["candidate_id"] == "C1"
    assert payload["status"] in {"dry_run_ok", "waiting_for_candidates_interface"}
    if payload["status"] == "waiting_for_candidates_interface":
        assert "build_candidate" in payload["expected_interface"]["callable"]
    # dry-run must not create candidate directories
    assert not (tmp_path / "candidates" / "C1").exists()


def test_render_png_degrades_when_matplotlib_missing(monkeypatch, tmp_path):
    module = _load_script("scripts/design/render_visuals.py")
    monkeypatch.setitem(sys.modules, "matplotlib", None)
    monkeypatch.setitem(sys.modules, "matplotlib.pyplot", None)
    result = module.render_png(fake_models(), tmp_path / "preview.png")
    assert result["status"] in {"unavailable", "failed"}
    assert "path" not in result or result.get("status") != "rendered"
    assert not (tmp_path / "preview.png").exists()

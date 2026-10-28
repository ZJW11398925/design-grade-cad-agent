from __future__ import annotations

import tomllib
from pathlib import Path

import ezdxf
import yaml

from dgcad_e2e import scan_dxf_privacy

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / "docs" / "e2e" / "open-source-reuse-001"


def test_reuse_matrix_covers_candidates_and_verdicts():
    matrix = yaml.safe_load(
        (EVIDENCE / "reuse-matrix.yaml").read_text(encoding="utf-8")
    )
    names = {item["name"] for item in matrix["projects"]}
    assert {
        "Building Regulariser",
        "UrbGEN",
        "OSMnx",
        "PyGeoOps",
        "Clothoids / PyClothoids",
        "Street Generator / rue-lib",
        "momepy",
    } <= names
    assert "buildingregulariser" in matrix["decisions"]["adopt_optional"]
    assert "osmnx" in matrix["decisions"]["adopt_optional"]
    assert "pyclothoids" in matrix["decisions"]["defer"]
    assert "urbgen" in matrix["decisions"]["reference_only"]
    failed = {
        item["id"] if "id" in item else next(iter(item))
        for item in matrix["failed_cases"]
    }
    assert "design_4c_road_topology" in failed
    assert matrix["tested_environment"]["python"] == "3.13"


def test_reuse_evidence_files_and_dxf_are_present():
    for relative in (
        "README.md",
        "reuse-matrix.yaml",
        "exp-a/metrics.json",
        "exp-a/overlay.png",
        "exp-b/metrics.json",
        "exp-b/overlay-osmnx.png",
        "exp-b/overlay-centerlines.png",
        "exp-b/osmnx-consolidated-8m.geojson",
        "exp-b/pygeoops-centerlines.geojson",
        "exp-c/metrics.json",
        "exp-c/comparison.png",
        "exp-c/design-notes.md",
        "exp-c/candidate-corrected.dxf",
    ):
        assert (EVIDENCE / relative).is_file(), relative
    doc = ezdxf.readfile(EVIDENCE / "exp-c" / "candidate-corrected.dxf")
    assert doc.dxfversion == "AC1024"
    assert len(doc.modelspace()) > 0
    assert scan_dxf_privacy(
        EVIDENCE / "exp-c" / "candidate-corrected.dxf"
    )["ok"] is True


def test_core_dependencies_remain_minimal():
    configuration = tomllib.loads(
        (ROOT / "pyproject.toml").read_text(encoding="utf-8")
    )
    dependencies = configuration["project"]["dependencies"]
    lowered = " ".join(dependencies).lower()
    for candidate in ("osmnx", "geopandas", "momepy", "buildingregulariser"):
        assert candidate not in lowered
    assert any("PyYAML" in item for item in dependencies)
    assert any("shapely" in item.lower() for item in dependencies)
    assert any("ezdxf" in item.lower() for item in dependencies)

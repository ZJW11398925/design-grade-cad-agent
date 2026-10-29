#!/usr/bin/env python3
"""Render the full-site (A-102) deliverables: DXF evidence + preview SVG/PNG.

Rebuilds the current design case from its fixtures, lays out the whole site
(using the full-site layout engine when ``dgcad_design.buildings.layout_full_site``
exists, otherwise the current pipeline layout with an explicit
``layout_source`` marker), and writes into an explicit output directory:

* ``full-site-proposal.dxf`` — the A-102 sheet with all 55 buildings (footprint,
  unit lines, labels), all 44 roads, all greens, dimensions and the usual sheet
  furniture; same 11-field XDATA / layers as the focus sheet;
* ``full-site-preview.svg`` — plan overview rendered from the same layouts;
* ``full-site-preview.png`` — optional matplotlib raster (skipped/degraded when
  matplotlib is not importable; never adds a dependency);
* ``full-site-summary.json``, ``full-site-readback-manifest.json``,
  ``full-site-validation.json``, ``full-site-privacy.json``,
  ``full-site-scene-snapshot.json`` — evidence for the sheet;
* ``full-site-visuals.json`` — preview render result.

The default output directory is scratch; nothing here touches committed
evidence.  Usage::

    python scripts/design/render_full_site.py
    python scripts/design/render_full_site.py --output-dir docs/e2e/design-synthesis-001
    python scripts/design/render_full_site.py --layout current --no-png
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from dgcad_design.buildings import (  # noqa: E402
    BuildingLayout,
    find_focus_design_rect,
    layout_focus_region,
    standardize_all,
)
from dgcad_design.basis import DesignBasis  # noqa: E402
from dgcad_design.input import load_design_input  # noqa: E402
from dgcad_design.intent import build_design_intent  # noqa: E402
from dgcad_design.project import (  # noqa: E402
    build_full_site_models,
    run_full_site_evidence,
)
from dgcad_design.visuals import render_plan_svg  # noqa: E402
import yaml  # noqa: E402

DEFAULT_CASE = ROOT / "docs/e2e/sketch-001"
DEFAULT_BASIS = ROOT / "fixtures/design/design-basis-001.yaml"
DEFAULT_PROFILE = ROOT / "fixtures/design/design-profile-001.yaml"
DEFAULT_OUTPUT = ROOT / "scratch/team/site-pipeline/full-site"


def _current_layout(design_input, basis, intent, standardized) -> BuildingLayout:
    design_rect = find_focus_design_rect(design_input, intent, basis)
    return layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        design_input.site_boundary.buffer(-basis.boundary_setback_m),
        design_rect,
    )


def render_png(models: dict, path: Path, width: int = 1600) -> dict:
    """Optional raster preview. Never raises; degrades to ``unavailable``."""
    try:
        import matplotlib  # noqa: PLC0415

        matplotlib.use("Agg")
        import matplotlib.pyplot as plt  # noqa: PLC0415
        from matplotlib.patches import Polygon as MplPolygon  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001
        return {
            "status": "unavailable",
            "reason": f"matplotlib not importable: {type(exc).__name__}",
        }
    try:
        fig, ax = plt.subplots(figsize=(width / 160.0, width / 160.0 * 0.62))
        for item in getattr(models["road_layout"], "roads", ()):
            corridor = getattr(item, "corridor", None)
            if corridor is None or corridor.is_empty:
                continue
            polygons = (
                [corridor]
                if corridor.geom_type == "Polygon"
                else list(getattr(corridor, "geoms", ()))
            )
            for polygon in polygons:
                ax.add_patch(
                    MplPolygon(
                        list(polygon.exterior.coords),
                        closed=True,
                        alpha=0.28,
                        facecolor={
                            "main": "#d73027",
                            "branch": "#fc8d59",
                            "access": "#4575b4",
                        }.get(item.class_name, "#888888"),
                        edgecolor="none",
                    )
                )
            centerline = getattr(item, "centerline", None)
            if centerline is not None and not centerline.is_empty:
                coords = list(centerline.coords)
                ax.plot(
                    [x for x, _ in coords],
                    [y for _, y in coords],
                    color="#333333",
                    linewidth=0.7,
                )
        for green in getattr(models["green_layout"], "greens", ()):
            geometry = green.geometry
            polygons = (
                [geometry]
                if geometry.geom_type == "Polygon"
                else list(getattr(geometry, "geoms", ()))
            )
            for polygon in polygons:
                ax.add_patch(
                    MplPolygon(
                        list(polygon.exterior.coords),
                        closed=True,
                        alpha=0.5,
                        facecolor="#8dd3a8",
                        edgecolor="none",
                    )
                )
        for building in getattr(models["building_layout"], "buildings", ()):
            ax.add_patch(
                MplPolygon(
                    list(building.footprint.exterior.coords),
                    closed=True,
                    facecolor="#e8e8e8",
                    edgecolor="#4d4d4d",
                    linewidth=0.8,
                )
            )
        site = models["design_input"].site_boundary
        ax.plot(
            [x for x, _ in site.exterior.coords],
            [y for _, y in site.exterior.coords],
            color="#111111",
            linewidth=1.0,
            linestyle="--",
        )
        x0, y0, x1, y1 = models["intent"].focus_bbox
        ax.plot(
            [x0, x1, x1, x0, x0],
            [y0, y0, y1, y1, y0],
            color="#1f78b4",
            linewidth=1.0,
            linestyle=":",
        )
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(
            "DGCAD full-site design draft (schematic, not human-confirmed)"
        )
        path.parent.mkdir(parents=True, exist_ok=True)
        fig.savefig(
            path, dpi=140, bbox_inches="tight", metadata={"Software": None}
        )
        plt.close(fig)
        return {
            "status": "rendered",
            "path": str(path),
            "bytes": path.stat().st_size,
        }
    except Exception as exc:  # noqa: BLE001
        return {"status": "failed", "reason": f"{type(exc).__name__}: {exc}"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="directory for the full-site DXF and previews (default: scratch)",
    )
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--basis", type=Path, default=DEFAULT_BASIS)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
    parser.add_argument(
        "--layout",
        choices=("auto", "current", "full-site"),
        default="auto",
        help=(
            "auto: use layout_full_site when importable, else the current "
            "layout; full-site: require layout_full_site; current: force the "
            "current pipeline layout (all three share one model path, so the "
            "DXF and the preview always show the same geometry)"
        ),
    )
    parser.add_argument("--width", type=int, default=1600)
    parser.add_argument("--no-png", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    args = parser.parse_args(argv)

    output_dir = Path(args.output_dir).resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    basis = DesignBasis.from_dict(
        yaml.safe_load(Path(args.basis).read_text(encoding="utf-8"))
    )
    design_input = load_design_input(Path(args.case_dir), basis)
    intent = build_design_intent(design_input, basis)
    standardized = standardize_all(design_input, basis)

    if args.layout == "current":
        layout = _current_layout(
            design_input, basis, intent, standardized
        )
        models = build_full_site_models(
            args.case_dir,
            args.basis,
            args.profile,
            building_layout=layout,
        )
        models["layout_source"] = "focus_region_fallback"
        models["layout_note"] = "forced by --layout current"
    else:
        models = build_full_site_models(
            args.case_dir,
            args.basis,
            args.profile,
            use_full_site_layout=True,
        )
        if args.layout == "full-site" and (
            models["layout_source"] != "full_site_layout"
        ):
            parser.error(
                "layout_full_site is required but unavailable: "
                f"{models['layout_note']}"
            )
    layout_reason = models["layout_note"]
    summary = run_full_site_evidence(
        args.case_dir,
        args.basis,
        args.profile,
        output_dir,
        models=models,
    )

    preview_green_layout = models["green_layout"]
    full_site_green = getattr(preview_green_layout, "full_site_green", None)
    if full_site_green is not None:
        # The A-102 sheet draws the generated designed-green parcels, so the
        # preview must show the same parcels instead of the source green set.
        preview_green_layout = replace(
            preview_green_layout, greens=full_site_green.parcels
        )
    preview = render_plan_svg(
        models["building_layout"],
        models["road_layout"],
        green_layout=preview_green_layout,
        site_boundary=design_input.site_boundary,
        focus_bbox=models["intent"].focus_bbox,
        path=output_dir / "full-site-preview.svg",
        title="Full-site plan (schematic autonomous design draft)",
        width=args.width,
    )
    result: dict = {
        "layout_source": summary["layout_source"],
        "layout_note": layout_reason,
        "dxf": summary["dxf"],
        "readback": summary["readback"],
        "privacy_ok": summary["privacy"]["ok"],
        "preview": preview,
    }
    if args.no_png:
        result["png"] = {"status": "skipped", "reason": "--no-png"}
    else:
        result["png"] = render_png(
            models, output_dir / "full-site-preview.png", width=args.width
        )
    (output_dir / "full-site-visuals.json").write_text(
        json.dumps(
            {
                "layout_source": summary["layout_source"],
                "layout_note": layout_reason,
                "preview": preview,
                "png": result["png"],
            },
            indent=2,
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    if not args.quiet:
        print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

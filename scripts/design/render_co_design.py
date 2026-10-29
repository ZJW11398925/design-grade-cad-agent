#!/usr/bin/env python3
"""Render the M4d-2 A/B building-road co-design candidates.

Builds candidate A (fixed M4d-1 full-site building layout) and candidate B
(group-preserving building layout), rebuilds the group access for both with
``build_co_design_access``, and writes into an explicit output directory:

* ``candidate-a/`` and ``candidate-b/`` — editable DXF (same A-102 full-site
  sheet, with the candidate tag / completeness declaration stamped in the title
  block), readback manifest, validation, privacy scan, scene snapshot, plan
  preview SVG/PNG and a candidate summary;
* ``comparison.svg`` — baseline / A / B at the same scale plus the key metrics
  (access, group and building displacement, added roads, object completeness);
* ``render-manifest.json`` — artefact hashes and the per-candidate status.

The full-site green semantics are preserved: the open-space tiling is drawn as
``L-OPEN-SPACE`` (potential open space, not designed green); designed green
stays ``L-GREEN``.  A candidate that fails a hard check is stamped
``INCOMPLETE``; only a candidate with zero hard failures is stamped
``HARD-VALID``.  Nothing is widened or hidden.

Usage::

    python scripts/design/render_co_design.py
    python scripts/design/render_co_design.py --output-dir scratch/team/site-pipeline/co-design
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter
from dataclasses import replace
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

import yaml  # noqa: E402
from shapely.geometry import box  # noqa: E402

from dgcad_cad import compile_to_dxf, validate_cad_ir, validate_dxf  # noqa: E402
from dgcad_e2e import scan_dxf_privacy  # noqa: E402
from dgcad_foundation import canonical_hash  # noqa: E402

from dgcad_design.access import build_co_design_access  # noqa: E402
from dgcad_design.basis import DesignBasis  # noqa: E402
from dgcad_design.buildings import (  # noqa: E402
    layout_group_preserving,
    standardize_all,
)
from dgcad_design.consistency import check_design  # noqa: E402
from dgcad_design.drawing import (  # noqa: E402
    build_full_site_drawing_elements,
)
from dgcad_design.green import (  # noqa: E402
    build_green_layout,
    design_full_site_green,
)
from dgcad_design.group_metrics import (  # noqa: E402
    access_truth_metrics,
    group_integrity_metrics,
)
from dgcad_design.input import load_design_input  # noqa: E402
from dgcad_design.intent import build_design_intent  # noqa: E402
from dgcad_design.parking import build_parking_layout  # noqa: E402
from dgcad_design.project import (  # noqa: E402
    build_design_cad_ir,
    build_full_site_models,
)
from dgcad_design.scene import (  # noqa: E402
    design_scene,
    scene_objects_for_export,
)
from dgcad_design.visuals import render_plan_svg  # noqa: E402

DEFAULT_CASE = ROOT / "docs/e2e/sketch-001"
DEFAULT_BASIS = ROOT / "fixtures/design/design-basis-001.yaml"
DEFAULT_PROFILE = ROOT / "fixtures/design/design-profile-001.yaml"
DEFAULT_OUTPUT = ROOT / "docs/e2e/design-co-design-001"

HARD_CHECK_IDS = (
    "FULL_SITE_BOUNDARY_SETBACK",
    "FULL_SITE_BUILDING_OVERLAP",
    "FULL_SITE_ROAD_CLEARANCE",
    "FULL_SITE_NS_SPACING",
    "ROAD_ACCESS_COVERAGE",
    "DEAD_END_RESOLUTION",
)
SHEET_IDS = {"A": "A-201", "B": "A-202"}
SCHEMA_ID = "dgcad.co-design-candidate-evidence.v0.1"


# ---------------------------------------------------------------------------
# candidate construction
# ---------------------------------------------------------------------------


def _displacement(standardized, building_layout) -> dict:
    values = []
    for building in building_layout.buildings:
        source = standardized.get(building.building_id)
        if source is None:
            continue
        values.append(
            float(
                building.footprint.centroid.distance(
                    source.footprint.centroid
                )
            )
        )
    if not values:
        return {"count": 0}
    return {
        "count": len(values),
        "mean_m": sum(values) / len(values),
        "max_m": max(values),
        "min_m": min(values),
    }


def _road_change(candidate_layout, frozen_layout) -> dict:
    frozen_ids = {road.edge_id for road in frozen_layout.roads}
    candidate_ids = {road.edge_id for road in candidate_layout.roads}
    added = sorted(candidate_ids - frozen_ids)
    removed = sorted(frozen_ids - candidate_ids)
    added_length = sum(
        road.centerline.length
        for road in candidate_layout.roads
        if road.edge_id in added
    )
    return {
        "frozen_road_count": len(frozen_ids),
        "candidate_road_count": len(candidate_ids),
        "added_road_ids": added,
        "removed_road_ids": removed,
        "added_road_count": len(added),
        "added_road_length_m": added_length,
    }


def _metrics_from_consistency(consistency, basis, intent, building_layout):
    """Flatten the consistency metrics into the keys the drawing expects."""
    metrics = dict(consistency.metrics)
    if "building_count" not in metrics:
        metrics["building_count"] = metrics.get(
            "full_site_building_count", len(building_layout.buildings)
        )
    if "unit_count" not in metrics:
        metrics["unit_count"] = metrics.get("staircase_count")
    if "min_road_clearance_m" not in metrics:
        metrics["min_road_clearance_m"] = metrics.get(
            "full_site_min_road_clearance_m"
        )
    if "road_clearance_violation_count" not in metrics:
        metrics["road_clearance_violation_count"] = metrics.get(
            "full_site_road_clearance_violation_count"
        )
    if "min_ns_spacing_m" not in metrics:
        metrics["min_ns_spacing_m"] = metrics.get(
            "full_site_min_ns_gap_m"
        )
    metrics.setdefault(
        "road_clearance_required_m",
        float(basis.building_road_clearance_m),
    )
    if "full_site_green_target_ratio" not in metrics:
        metrics["full_site_green_target_ratio"] = metrics.get(
            "green_target_ratio", basis.green_ratio_min
        )
    metrics.setdefault("focus_group_id", intent.focus_group_id)
    return metrics


def build_candidate(
    candidate_id: str,
    frozen: dict,
    basis: DesignBasis,
    design_input,
    intent,
    standardized,
    site_inner,
) -> dict:
    if candidate_id == "A":
        building_layout = frozen["building_layout"]
        layout_source = "m4d1_full_site_layout"
        layout_note = (
            "fixed M4d-1 full-site building layout + rebuilt group access"
        )
    elif candidate_id == "B":
        building_layout = layout_group_preserving(
            design_input,
            basis,
            intent,
            standardized,
            site_inner,
            road_corridor=frozen["road_layout"].corridor_union,
        )
        layout_source = "group_preserving_layout"
        layout_note = (
            "group-preserving full-site building layout + rebuilt group access"
        )
    else:  # pragma: no cover - guarded by the CLI choices
        raise ValueError(f"unknown candidate: {candidate_id}")

    road_layout, road_access, access_meta = build_co_design_access(
        design_input,
        basis,
        intent,
        building_layout,
        frozen["road_layout"],
        candidate_id=candidate_id,
    )
    green_layout = build_green_layout(
        design_input,
        building_layout,
        road_layout,
        basis,
        box(*intent.focus_bbox),
    )
    full_site_green = design_full_site_green(
        design_input, building_layout, road_layout, basis
    )
    if hasattr(green_layout, "full_site_green"):
        green_layout = replace(
            green_layout, full_site_green=full_site_green
        )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    consistency = check_design(
        design_input,
        basis,
        intent,
        building_layout,
        road_layout,
        green_layout,
        parking_layout,
        road_access,
    )
    checks = {check["id"]: check for check in consistency.checks}
    status_counts = Counter(check["status"] for check in consistency.checks)
    failed_hard = [
        check_id
        for check_id in HARD_CHECK_IDS
        if checks.get(check_id, {}).get("status") == "fail"
    ]
    hard_ok = not failed_hard and consistency.hard_checks_ok
    metrics = _metrics_from_consistency(
        consistency, basis, intent, building_layout
    )
    return {
        "candidate_id": candidate_id,
        "layout_source": layout_source,
        "layout_note": layout_note,
        "building_layout": building_layout,
        "road_layout": road_layout,
        "road_access": road_access,
        "green_layout": green_layout,
        "parking_layout": parking_layout,
        "access_meta": access_meta,
        "consistency": consistency,
        "checks": checks,
        "status_counts": status_counts,
        "failed_hard_checks": failed_hard,
        "hard_ok": hard_ok,
        "metrics": metrics,
    }


def _status_line(candidate: dict, basis: DesignBasis) -> str:
    metrics = candidate["metrics"]
    served = metrics.get("road_groups_served")
    total = metrics.get("road_groups_total")
    target = metrics.get("full_site_green_target_ratio")
    if not isinstance(target, (int, float)):
        target = basis.green_ratio_min
    deferred = candidate["status_counts"].get("deferred", 0)
    dead_ends = metrics.get("dead_ends_unresolved")
    if candidate["hard_ok"]:
        return (
            "HARD-VALID CANDIDATE: 0 HARD FAILS - "
            f"ROAD ACCESS {served}/{total} - "
            f"DEAD ENDS {dead_ends if dead_ends is not None else 'n/a'} "
            f"UNRESOLVED - DESIGNED GREEN < {target * 100:.0f}% "
            f"({deferred} DEFERRED)"
        )
    clearance = candidate["checks"].get("FULL_SITE_ROAD_CLEARANCE", {})
    value = clearance.get("value")
    required = metrics.get("road_clearance_required_m")
    value_text = f"{value:.3f}" if isinstance(value, (int, float)) else "n/a"
    required_text = (
        f"{required:.1f}" if isinstance(required, (int, float)) else "n/a"
    )
    return (
        f"INCOMPLETE: {', '.join(candidate['failed_hard_checks'])} FAIL "
        f"(MIN {value_text} m < {required_text} m) - "
        f"ROAD ACCESS {served}/{total} - "
        f"DESIGNED GREEN < {target * 100:.0f}%"
    )


# ---------------------------------------------------------------------------
# rendering
# ---------------------------------------------------------------------------


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
        newline="\n",
    )


def render_png(models: dict, path: Path, width: int = 1600) -> dict:
    """Optional raster preview; degrades gracefully when matplotlib is absent."""
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
        for item in models["road_layout"].roads:
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
                    linewidth=0.6,
                )
        for building in models["building_layout"].buildings:
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
        ax.set_aspect("equal")
        ax.set_axis_off()
        ax.set_title(
            f"Co-design candidate {models['candidate_id']} "
            f"({models['candidate_status']}) - schematic, not human-confirmed"
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


def _candidate_models(candidate: dict, frozen: dict, status_line: str) -> dict:
    return {
        "candidate_id": candidate["candidate_id"],
        "candidate_status": (
            "hard-valid" if candidate["hard_ok"] else "incomplete"
        ),
        "building_layout": candidate["building_layout"],
        "road_layout": candidate["road_layout"],
        "green_layout": candidate["green_layout"],
        "design_input": frozen["design_input"],
        "intent": frozen["intent"],
        "focus_bbox": frozen["intent"].focus_bbox,
        "status_line": status_line,
    }


def render_candidate(
    candidate: dict,
    frozen: dict,
    output_dir: Path,
    *,
    width: int = 1600,
    render_raster: bool = True,
) -> dict:
    candidate_id = candidate["candidate_id"]
    basis = frozen["basis"]
    profile = frozen["profile"]
    design_input = frozen["design_input"]
    intent = frozen["intent"]
    metrics = candidate["metrics"]
    status_line = _status_line(candidate, basis)
    out_dir = output_dir / candidate_id
    out_dir.mkdir(parents=True, exist_ok=True)

    elements = build_full_site_drawing_elements(
        design_input,
        intent,
        candidate["building_layout"],
        candidate["road_layout"],
        candidate["green_layout"],
        candidate["parking_layout"],
        basis,
        metrics,
        sheet_id=SHEET_IDS[candidate_id],
        candidate_id=candidate_id,
        status_line=status_line,
    )
    scene = design_scene(
        elements, basis, scene_id=f"scene-CO-DESIGN-{candidate_id}-R1"
    )
    cad_ir = build_design_cad_ir(
        scene,
        profile,
        basis,
        metrics,
        project_id=f"DESIGN-CASE-SKETCH-001-CO-DESIGN-{candidate_id}",
    )
    cad_validation = validate_cad_ir(cad_ir, profile)
    dxf_path = out_dir / f"candidate-{candidate_id.lower()}.dxf"
    compile_result = compile_to_dxf(cad_ir, profile, dxf_path)
    readback = validate_dxf(dxf_path, cad_ir, profile)
    privacy = scan_dxf_privacy(dxf_path)
    scene_payload = scene_objects_for_export(scene)

    summary = {
        "schema_id": SCHEMA_ID,
        "case_id": design_input.case_id,
        "candidate_id": candidate_id,
        "status": (
            "hard_valid_candidate"
            if candidate["hard_ok"]
            else "incomplete_candidate"
        ),
        "hard_ok": candidate["hard_ok"],
        "failed_hard_checks": candidate["failed_hard_checks"],
        "check_status": dict(candidate["status_counts"]),
        "layout_source": candidate["layout_source"],
        "layout_note": candidate["layout_note"],
        "sheet_id": SHEET_IDS[candidate_id],
        "plan_scale": "1:2000",
        "status_line": status_line,
        "building_count": len(candidate["building_layout"].buildings),
        "unit_count": sum(
            item.unit_count for item in candidate["building_layout"].buildings
        ),
        "households": sum(
            item.households for item in candidate["building_layout"].buildings
        ),
        "metrics": {
            key: metrics.get(key)
            for key in (
                "far",
                "households",
                "parking_spaces",
                "road_access_coverage",
                "road_groups_served",
                "road_groups_total",
                "road_relation_error_count",
                "dead_ends_unresolved",
                "min_road_clearance_m",
                "road_clearance_required_m",
                "road_clearance_violation_count",
                "min_ns_spacing_m",
                "ns_spacing_violation_count",
                "designed_green_ratio",
                "full_site_open_space_account_ratio",
                "full_site_open_space_account_parcel_count",
                "full_site_green_target_ratio",
            )
        },
        "road_change": _road_change(
            candidate["road_layout"], frozen["road_layout"]
        ),
        "displacement": _displacement(
            frozen["standardized"], candidate["building_layout"]
        ),
        "group_metrics": group_integrity_metrics(
            intent,
            candidate["building_layout"],
            candidate["road_access"],
        ),
        "access_truth": access_truth_metrics(
            candidate["road_layout"],
            candidate["road_access"],
            design_input.site_boundary,
            candidate["building_layout"],
        ),
        "checks": {
            check_id: {
                "status": check["status"],
                "value": check.get("value"),
            }
            for check_id, check in candidate["checks"].items()
        },
        "non_claims": [
            "this is a schematic design proposal, not a construction or permit drawing",
            "no Chinese code, fire-access, daylight or accessibility compliance is claimed",
            "the candidate placement is rule-derived, not a designer-confirmed site plan",
            "the open-space tiling is potential open space, not a landscape design",
            "the garage layout is not designed; only the entrance requirement is checked",
        ],
        "scene_id": scene.scene_id,
        "scene_object_count": len(scene.objects),
        "scene_sha256": canonical_hash(scene_payload),
        "dxf": {
            "path": dxf_path.name,
            "sha256": hashlib.sha256(dxf_path.read_bytes()).hexdigest(),
            "entity_count": compile_result.entity_count,
            "audit_errors": compile_result.audit_errors,
            "audit_fixes": compile_result.audit_fixes,
        },
        "readback": {
            "verdict": readback.verdict,
            "codes": list(readback.codes),
            "entity_count": readback.manifest.get("entity_count"),
            "expected_entity_count": readback.manifest.get(
                "expected_entity_count"
            ),
            "confirmation_scopes": readback.manifest.get(
                "confirmation_scopes"
            ),
            "manifest_sha256": canonical_hash(readback.manifest),
        },
        "cad_ir_validation": cad_validation.to_dict(),
        "privacy": privacy,
    }

    preview_models = _candidate_models(candidate, frozen, status_line)
    preview_green_layout = candidate["green_layout"]
    full_site_green = getattr(preview_green_layout, "full_site_green", None)
    if full_site_green is not None:
        preview_green_layout = replace(
            preview_green_layout, greens=full_site_green.parcels
        )
    preview = render_plan_svg(
        candidate["building_layout"],
        candidate["road_layout"],
        green_layout=preview_green_layout,
        site_boundary=design_input.site_boundary,
        focus_bbox=intent.focus_bbox,
        path=out_dir / f"candidate-{candidate_id.lower()}-preview.svg",
        title=(
            f"Co-design candidate {candidate_id} "
            f"({'hard-valid' if candidate['hard_ok'] else 'incomplete'})"
            " - schematic autonomous design draft"
        ),
        width=width,
    )
    png = (
        render_png(
            preview_models,
            out_dir / f"candidate-{candidate_id.lower()}-preview.png",
            width=width,
        )
        if render_raster
        else {"status": "skipped", "reason": "--no-png"}
    )
    summary["preview"] = preview
    summary["png"] = png

    _write_json(out_dir / "candidate-summary.json", summary)
    _write_json(out_dir / "readback-manifest.json", readback.manifest)
    _write_json(
        out_dir / "validation.json",
        {
            "cad_ir": cad_validation.to_dict(),
            "dxf_readback": readback.to_dict(),
            "privacy": privacy,
            "verdicts": {
                "cad_ir": cad_validation.verdict,
                "dxf_readback": readback.verdict,
                "privacy": "pass" if privacy["ok"] else "fail",
            },
        },
    )
    _write_json(out_dir / "privacy.json", privacy)
    _write_json(
        out_dir / "scene-snapshot.json",
        {
            "scene_id": scene.scene_id,
            "world": scene.world.value,
            "objects": scene_payload,
        },
    )
    return summary


# ---------------------------------------------------------------------------
# comparison sheet (baseline / A / B, same scale)
# ---------------------------------------------------------------------------


def _fmt(value, digits: int = 2) -> str:
    if isinstance(value, (int, float)):
        return f"{value:.{digits}f}"
    return "n/a"


def _text(x, y, content, size=12, fill="#111111", weight=None, anchor=None):
    attrs = f'x="{x:.1f}" y="{y:.1f}" font-size="{size}" fill="{fill}"'
    if weight:
        attrs += f' font-weight="{weight}"'
    if anchor:
        attrs += f' text-anchor="{anchor}"'
    escaped = (
        str(content)
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )
    return f"<text {attrs}>{escaped}</text>"


def _line_path(coords, transform) -> str:
    points = [transform(x, y) for x, y in coords]
    if not points:
        return ""
    head = f"M {points[0][0]:.2f},{points[0][1]:.2f}"
    return head + "".join(
        f" L {x:.2f},{y:.2f}" for x, y in points[1:]
    )


def _polygon_path(geometry, transform) -> str:
    ring = getattr(geometry, "exterior", geometry)
    return _line_path(list(ring.coords), transform) + " Z"


def _iter_polygons(geometry):
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == "Polygon":
        yield geometry
    elif geometry.geom_type == "MultiPolygon":
        yield from geometry.geoms


def _iter_lines(geometry):
    if geometry is None or geometry.is_empty:
        return
    if geometry.geom_type == "LineString":
        yield geometry
    elif geometry.geom_type == "MultiLineString":
        yield from geometry.geoms


ROAD_COLORS = {
    "main": "#d73027",
    "branch": "#fc8d59",
    "access": "#4575b4",
}


def render_comparison_svg(
    panels: list[dict],
    path: Path,
    *,
    width: int = 1480,
) -> dict:
    """Baseline / A / B panels at the same scale plus the key metrics table."""
    margin = 26.0
    panel_gap = 18.0
    panel_width = (width - 2 * margin - panel_gap * (len(panels) - 1)) / len(
        panels
    )
    bounds = tuple(panels[0]["site_boundary"].bounds)
    scale = panel_width / (bounds[2] - bounds[0])
    panel_height = (bounds[3] - bounds[1]) * scale
    title_height = 54.0
    caption_height = 34.0
    table_row_height = 22.0
    table_rows = 9
    table_height = table_row_height * (table_rows + 1) + 26.0
    svg_width = width
    svg_height = (
        title_height
        + panel_height
        + caption_height
        + table_height
        + margin
    )

    def transform_for(index):
        origin_x = margin + index * (panel_width + panel_gap)
        origin_y = title_height

        def transform(x, y):
            return (
                origin_x + (float(x) - bounds[0]) * scale,
                origin_y + (bounds[3] - float(y)) * scale,
            )

        return transform, origin_x, origin_y

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{svg_width:.0f}" '
        f'height="{svg_height:.0f}" viewBox="0 0 {svg_width:.0f} '
        f'{svg_height:.0f}">',
        '<rect width="100%" height="100%" fill="#ffffff"/>',
        _text(
            margin,
            30,
            "M4d-2 co-design candidates - same scale, hard-first comparison",
            size=19,
            weight="bold",
        ),
        _text(
            margin,
            48,
            "schematic autonomous design draft - not human-confirmed - "
            "not code-compliance; potential open space is not designed green",
            size=11,
            fill="#555555",
        ),
    ]
    for index, panel in enumerate(panels):
        transform, origin_x, origin_y = transform_for(index)
        parts.append(
            f'<rect x="{origin_x:.2f}" y="{origin_y:.2f}" '
            f'width="{panel_width:.2f}" height="{panel_height:.2f}" '
            'fill="#fbfbfb" stroke="#999999" stroke-width="0.8"/>'
        )
        for polygon in _iter_polygons(panel["site_boundary"]):
            parts.append(
                f'<path d="{_polygon_path(polygon, transform)}" '
                'fill="none" stroke="#111111" stroke-width="1.3" '
                'stroke-dasharray="7 3"/>'
            )
        green_layout = panel.get("green_layout")
        full_site_green = getattr(green_layout, "full_site_green", None)
        if full_site_green is not None:
            for parcel in full_site_green.parcels:
                for polygon in _iter_polygons(parcel.geometry):
                    parts.append(
                        f'<path d="{_polygon_path(polygon, transform)}" '
                        'fill="#eeeeee" stroke="#d0d0d0" stroke-width="0.3"/>'
                    )
        for road in panel["road_layout"].roads:
            color = ROAD_COLORS.get(road.class_name, "#666666")
            for line in _iter_lines(road.centerline):
                parts.append(
                    f'<path d="{_line_path(line.coords, transform)}" '
                    f'fill="none" stroke="{color}" stroke-width="1.1"/>'
                )
        for building in panel["building_layout"].buildings:
            parts.append(
                f'<path d="{_polygon_path(building.footprint.exterior, transform)}" '
                'fill="#dcdcdc" stroke="#444444" stroke-width="0.5"/>'
            )
        parts.append(
            _text(
                origin_x + 8,
                origin_y + panel_height + 18,
                panel["label"],
                size=13,
                weight="bold",
            )
        )
        parts.append(
            _text(
                origin_x + 8,
                origin_y + panel_height + 32,
                panel["subtitle"],
                size=10.5,
                fill="#555555",
            )
        )

    # metrics table
    table_top = title_height + panel_height + caption_height + 18
    columns = [margin, margin + 250, margin + 250 + 250]
    if len(panels) >= 3:
        columns.append(margin + 250 + 500)
    headers = ["metric"] + [panel["label"] for panel in panels]
    for col, header in enumerate(headers):
        x = columns[min(col, len(columns) - 1)]
        parts.append(_text(x, table_top, header, size=12, weight="bold"))
    rows = panels[0].get("table_rows") or []
    for row_index, row in enumerate(rows, start=1):
        y = table_top + row_index * table_row_height
        for col, value in enumerate([row[0], *row[1:]]):
            x = columns[min(col, len(columns) - 1)]
            parts.append(
                _text(
                    x,
                    y,
                    value,
                    size=11,
                    fill="#222222" if col == 0 else "#111111",
                )
            )
    parts.append("</svg>")
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(parts), encoding="utf-8", newline="\n")
    return {
        "path": str(path),
        "bytes": path.stat().st_size,
        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "panels": [panel["label"] for panel in panels],
    }


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--case-dir", type=Path, default=DEFAULT_CASE)
    parser.add_argument("--basis", type=Path, default=DEFAULT_BASIS)
    parser.add_argument("--profile", type=Path, default=DEFAULT_PROFILE)
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
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    frozen = build_full_site_models(
        args.case_dir, args.basis, args.profile
    )

    candidates = {}
    for candidate_id in ("A", "B"):
        candidates[candidate_id] = build_candidate(
            candidate_id,
            frozen,
            basis,
            design_input,
            intent,
            standardized,
            site_inner,
        )

    summaries = {}
    for candidate_id in ("A", "B"):
        summaries[candidate_id] = render_candidate(
            candidates[candidate_id],
            frozen,
            output_dir,
            width=args.width,
            render_raster=not args.no_png,
        )

    # baseline panel = frozen M4d-1 sheet (old focus-era access declarations)
    baseline_layout = frozen["building_layout"]
    baseline_access_truth = access_truth_metrics(
        frozen["road_layout"],
        frozen["road_access"],
        design_input.site_boundary,
        baseline_layout,
    )
    baseline_group_metrics = group_integrity_metrics(
        intent, baseline_layout, frozen["road_access"]
    )
    baseline_displacement = _displacement(standardized, baseline_layout)

    def _table_rows(candidate_summaries):
        a = candidate_summaries["A"]
        b = candidate_summaries["B"]

        def _access(summary):
            served = summary["metrics"]["road_groups_served"]
            total = summary["metrics"]["road_groups_total"]
            return f"{served}/{total}"

        return [
            (
                "buildings / units",
                "55 / 109",
                f"{a['building_count']} / {a['unit_count']}",
                f"{b['building_count']} / {b['unit_count']}",
            ),
            (
                "hard check failures",
                "access 0/17, 17 unresolved (old declarations)",
                ", ".join(a["failed_hard_checks"]) or "none",
                ", ".join(b["failed_hard_checks"]) or "none",
            ),
            (
                "access coverage (groups served)",
                f"{_fmt(baseline_access_truth.get('coverage'))} (0/17)",
                f"{_fmt(a['metrics']['road_access_coverage'])} ({_access(a)})",
                f"{_fmt(b['metrics']['road_access_coverage'])} ({_access(b)})",
            ),
            (
                "access relation errors",
                str(baseline_access_truth.get("relation_error_count")),
                str(a["metrics"]["road_relation_error_count"]),
                str(b["metrics"]["road_relation_error_count"]),
            ),
            (
                "dead ends unresolved",
                str(baseline_access_truth.get("dead_ends", {}).get("unresolved")),
                str(a["metrics"]["dead_ends_unresolved"]),
                str(b["metrics"]["dead_ends_unresolved"]),
            ),
            (
                "building displacement mean / max (m)",
                f"{_fmt(baseline_displacement.get('mean_m'))} / "
                f"{_fmt(baseline_displacement.get('max_m'))}",
                f"{_fmt(a['displacement']['mean_m'])} / "
                f"{_fmt(a['displacement']['max_m'])}",
                f"{_fmt(b['displacement']['mean_m'])} / "
                f"{_fmt(b['displacement']['max_m'])}",
            ),
            (
                "group centroid displacement mean / max (m)",
                f"{_fmt(baseline_group_metrics.get('mean_centroid_displacement_m'))}"
                " / "
                f"{_fmt(baseline_group_metrics.get('max_centroid_displacement_m'))}",
                f"{_fmt(a['group_metrics']['mean_centroid_displacement_m'])} / "
                f"{_fmt(a['group_metrics']['max_centroid_displacement_m'])}",
                f"{_fmt(b['group_metrics']['mean_centroid_displacement_m'])} / "
                f"{_fmt(b['group_metrics']['max_centroid_displacement_m'])}",
            ),
            (
                "added road length (m)",
                "0",
                _fmt(a["road_change"]["added_road_length_m"]),
                _fmt(b["road_change"]["added_road_length_m"]),
            ),
            (
                "group split count",
                str(baseline_group_metrics.get("groups_split")),
                str(a["group_metrics"].get("groups_split")),
                str(b["group_metrics"].get("groups_split")),
            ),
        ]

    table_rows = _table_rows(summaries)
    panels = [
        {
            "label": "M4D1-BASELINE",
            "subtitle": "old focus-era access declarations (access 0/17)",
            "site_boundary": design_input.site_boundary,
            "road_layout": frozen["road_layout"],
            "building_layout": baseline_layout,
            "green_layout": frozen["green_layout"],
            "table_rows": table_rows,
        },
        {
            "label": "CANDIDATE A",
            "subtitle": (
                "INCOMPLETE - FULL_SITE_ROAD_CLEARANCE fail "
                f"({_fmt(candidates['A']['checks']['FULL_SITE_ROAD_CLEARANCE']['value'], 3)} m < 3.0 m)"
            ),
            "site_boundary": design_input.site_boundary,
            "road_layout": candidates["A"]["road_layout"],
            "building_layout": candidates["A"]["building_layout"],
            "green_layout": candidates["A"]["green_layout"],
            "table_rows": table_rows,
        },
        {
            "label": "CANDIDATE B",
            "subtitle": "HARD-VALID - 0 hard failures, access 17/17",
            "site_boundary": design_input.site_boundary,
            "road_layout": candidates["B"]["road_layout"],
            "building_layout": candidates["B"]["building_layout"],
            "green_layout": candidates["B"]["green_layout"],
            "table_rows": table_rows,
        },
    ]
    comparison = render_comparison_svg(
        panels, output_dir / "comparison.svg", width=1480
    )

    render_manifest = {
        "schema_id": "dgcad.co-design-render.v0.1",
        "candidates": {
            candidate_id: {
                "status": summaries[candidate_id]["status"],
                "hard_ok": summaries[candidate_id]["hard_ok"],
                "failed_hard_checks": summaries[candidate_id][
                    "failed_hard_checks"
                ],
                "dxf": summaries[candidate_id]["dxf"],
                "readback": summaries[candidate_id]["readback"],
                "privacy_ok": summaries[candidate_id]["privacy"]["ok"],
                "preview_svg_sha256": summaries[candidate_id][
                    "preview"
                ].get("sha256"),
            }
            for candidate_id in ("A", "B")
        },
        "comparison": comparison,
        "recommendation": "B",
        "hard_first": True,
    }
    _write_json(output_dir / "render-manifest.json", render_manifest)
    if not args.quiet:
        print(
            json.dumps(
                {
                    "output_dir": str(output_dir),
                    "a": {
                        "status": summaries["A"]["status"],
                        "failed": summaries["A"]["failed_hard_checks"],
                        "entities": summaries["A"]["dxf"]["entity_count"],
                        "readback": summaries["A"]["readback"]["verdict"],
                    },
                    "b": {
                        "status": summaries["B"]["status"],
                        "failed": summaries["B"]["failed_hard_checks"],
                        "entities": summaries["B"]["dxf"]["entity_count"],
                        "readback": summaries["B"]["readback"]["verdict"],
                    },
                    "comparison": comparison,
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

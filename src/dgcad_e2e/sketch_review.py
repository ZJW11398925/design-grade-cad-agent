from __future__ import annotations

import hashlib
import html
import json
from pathlib import Path
from typing import Any

import yaml
from shapely.geometry import shape

from dgcad_domain import SketchHandoff


PACKET_SCHEMA_ID = "dgcad.sketch-review-packet.v0.1"
REQUEST_SCHEMA_ID = "dgcad.sketch-review-request.v0.1"
REVIEW_TEMPLATE_SCHEMA_ID = "dgcad.sketch-handoff-review.v0.2"


def _hex_color(index: int) -> str:
    palette = (
        "#d62728",
        "#1f77b4",
        "#2ca02c",
        "#ff7f0e",
        "#9467bd",
        "#8c564b",
        "#17becf",
    )
    return palette[index % len(palette)]


def _ring_path(coords: list[list[float]]) -> str:
    if not coords:
        return ""
    parts = [f"M {coords[0][0]:.3f},{coords[0][1]:.3f}"]
    parts.extend(f"L {x:.3f},{y:.3f}" for x, y in coords[1:])
    parts.append("Z")
    return " ".join(parts)


def _geometry_paths(geometry: dict[str, Any]) -> list[str]:
    kind = geometry["type"]
    coords = geometry["coordinates"]
    if kind == "Polygon":
        return [_ring_path(ring) for ring in coords]
    if kind == "MultiPolygon":
        paths: list[str] = []
        for polygon in coords:
            paths.extend(_ring_path(ring) for ring in polygon)
        return paths
    if kind == "LineString":
        return [
            " ".join(
                [
                    f"M {coords[0][0]:.3f},{coords[0][1]:.3f}",
                    *(
                        f"L {x:.3f},{y:.3f}" for x, y in coords[1:]
                    ),
                ]
            )
        ]
    if kind == "Point":
        x, y = coords
        return [f"M {x - 6:.3f},{y:.3f} a 6,6 0 1,0 12,0 a 6,6 0 1,0 -12,0"]
    return []


def _svg_overlay(
    handoff: SketchHandoff,
    width: int,
    height: int,
) -> str:
    paths = []
    labels = []
    for index, obj in enumerate(handoff.objects.values()):
        color = _hex_color(index)
        for path in _geometry_paths(obj.geometry):
            paths.append(
                f'<path d="{path}" fill="none" stroke="{color}" '
                'stroke-width="2.5" stroke-opacity="0.95" '
                'vector-effect="non-scaling-stroke"/>'
            )
        minx, miny, maxx, maxy = shape(obj.geometry).bounds
        labels.append(
            f'<text x="{maxx + 4:.1f}" y="{max(miny + 12, height - 4):.1f}" '
            f'fill="{color}" font-size="13" font-family="monospace">'
            f"{html.escape(obj.source_id)}</text>"
        )
    return (
        f'<svg viewBox="0 0 {width} {height}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="position:absolute;inset:0;width:100%;height:100%">'
        + "".join(paths)
        + "".join(labels)
        + "</svg>"
    )


def _local_svg(
    handoff: SketchHandoff, obj, *, size: int = 220
) -> str:
    local = handoff.coordinate.transform_geometry(obj.geometry)
    geom = shape(local)
    minx, miny, maxx, maxy = geom.bounds
    span = max(maxx - minx, maxy - miny, 1.0)
    pad = span * 0.12
    scale = (size - 20) / (span + 2 * pad)

    def sx(x: float) -> float:
        return 10 + (x - minx + pad) * scale

    def sy(y: float) -> float:
        return size - 10 - (y - miny + pad) * scale

    if local["type"] == "Polygon":
        polygons = [local["coordinates"]]
    elif local["type"] == "MultiPolygon":
        polygons = local["coordinates"]
    else:
        polygons = []
    paths = []
    if polygons:
        for polygon in polygons:
            for ring in polygon:
                d = " ".join(
                    [
                        f"M {sx(ring[0][0]):.2f},{sy(ring[0][1]):.2f}",
                        *(
                            f"L {sx(x):.2f},{sy(y):.2f}"
                            for x, y in ring[1:]
                        ),
                        "Z",
                    ]
                )
                paths.append(
                    f'<path d="{d}" fill="none" stroke="#111" '
                    'stroke-width="1.5" fill-rule="evenodd"/>'
                )
    else:
        coords = local["coordinates"]
        d = " ".join(
            [
                f"M {sx(coords[0][0]):.2f},{sy(coords[0][1]):.2f}",
                *(
                    f"L {sx(x):.2f},{sy(y):.2f}"
                    for x, y in coords[1:]
                ),
            ]
        )
        paths.append(
            f'<path d="{d}" fill="none" stroke="#111" stroke-width="1.5"/>'
        )
    bar = span * scale * 0.35
    return (
        f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}" '
        'xmlns="http://www.w3.org/2000/svg" '
        'style="background:#fafafa;border:1px solid #ccc">'
        + "".join(paths)
        + f'<line x1="16" y1="{size - 8}" x2="{16 + bar:.1f}" '
        f'y2="{size - 8}" stroke="#333" stroke-width="2"/>'
        + f'<text x="16" y="{size - 14}" font-size="10" '
        'font-family="monospace">'
        f"{span * 0.35:.2f} m</text>"
        + "</svg>"
    )


def build_review_packet(
    handoff: SketchHandoff,
    output_dir: str | Path,
    *,
    sketch_path: str,
    sketch_href: str,
    image_size: tuple[int, int],
) -> dict[str, Any]:
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    width, height = image_size
    sensitivity = {
        item["source_id"]: item
        for item in handoff.coordinate_sensitivity_report()
    }

    rows = []
    request_objects = []
    decisions = []
    for index, obj in enumerate(handoff.objects.values()):
        local = handoff.coordinate.transform_geometry(obj.geometry)
        metric = sensitivity[obj.source_id]
        overlay_id = f"object-{html.escape(obj.source_id)}"
        rows.append(
            {
                "source_id": obj.source_id,
                "trace_id": obj.trace_id,
                "canonical_id": obj.canonical_id,
                "semantic_role": obj.semantic_role,
                "geometry_state": obj.geometry_state,
                "source_file": obj.provenance["source_file"],
                "source_object_id": obj.provenance["source_object_id"],
                "source_geometry_sha256": obj.provenance[
                    "source_geometry_sha256"
                ],
                "image_geometry": obj.geometry,
                "local_geometry": local,
                "scale_sensitivity": metric,
                "overlay": f"review-packet.html#{overlay_id}",
                "color": _hex_color(index),
            }
        )
        request_objects.append(
            {
                "source_id": obj.source_id,
                "semantic_role": obj.semantic_role,
                "geometry_state": obj.geometry_state,
                "questions": {
                    "semantic": (
                        "Is this object's semantic role correct?"
                    ),
                    "geometry": (
                        "Does the outline match the drawn object at "
                        "pilot-subset scope?"
                    ),
                    "coordinate": (
                        "Is the local metric placement acceptable given the "
                        "approximate uniform scale and no distortion "
                        "correction?"
                    ),
                },
                "evidence": {
                    "overlay": f"review-packet.html#{overlay_id}",
                    "source_geometry_sha256": obj.provenance[
                        "source_geometry_sha256"
                    ],
                    "source_file": obj.provenance["source_file"],
                },
                "decision": {
                    "semantic": "",
                    "geometry": "",
                    "coordinate": "",
                    "evidence_ref": "",
                    "note": "",
                },
            }
        )
        decisions.append(
            {
                "source_id": obj.source_id,
                "semantic": "confirmed",
                "geometry": "",
                "coordinate": "",
                "evidence_ref": "",
            }
        )

    packet = {
        "schema_id": PACKET_SCHEMA_ID,
        "handoff_id": handoff.handoff_id,
        "case_id": handoff.case_id,
        "status": "review_required",
        "review_kind": handoff.review.review_kind,
        "object_geometry_review": handoff.review.object_geometry_review,
        "human_confirmation_claimed": False,
        "human_confirmed_trace": False,
        "review_scope": handoff.review.review_scope,
        "reviewer_role": handoff.review.reviewer_role,
        "review_basis": handoff.review.basis,
        "source_sketch": {
            "path": sketch_path,
            "sha256": handoff.source_sketch_sha256,
        },
        "site_boundary_authority": handoff.site_boundary_authority,
        "coordinate_handoff": {
            "source_frame": handoff.coordinate.source_frame,
            "target_frame": handoff.coordinate.target_frame,
            "transform_kind": handoff.coordinate.transform_kind,
            "homography_applied": handoff.coordinate.homography_applied,
            "shape_correction": handoff.coordinate.shape_correction,
            "axis_orientation": handoff.coordinate.axis_orientation,
            "scale_px_per_m": handoff.coordinate.scale_px_per_m,
            "scale_range_px_per_m": list(
                handoff.coordinate.scale_range_px_per_m
            ),
            "scale_source": handoff.coordinate.scale_source,
            "origin_px": list(handoff.coordinate.origin_px),
            "origin_source": handoff.coordinate.origin_source,
            "accuracy": handoff.coordinate.accuracy,
            "not_survey_grade": handoff.coordinate.not_survey_grade,
            "uncertainty_method": handoff.coordinate.uncertainty_method,
        },
        "objects": rows,
        "road_topology": handoff.road_topology_report(),
        "non_claims": list(handoff.non_claims)
        + [
            "this packet is a review request, not a confirmation",
            "the uniform-scale transform does not correct local sketch distortion",
        ],
    }
    packet_path = output_dir / "review-packet.json"
    packet_bytes = json.dumps(
        packet, indent=2, ensure_ascii=False
    ).encode("utf-8")
    packet_path.write_bytes(packet_bytes)
    packet_sha256 = hashlib.sha256(packet_bytes).hexdigest()

    request = {
        "schema_id": REQUEST_SCHEMA_ID,
        "handoff_id": handoff.handoff_id,
        "status": "review_required",
        "template_not_signed": True,
        "human_confirmation_claimed": False,
        "instructions": (
            "Inspect review-packet.html. Record per-object semantic, "
            "geometry and coordinate decisions. Do not mark geometry "
            "confirmed unless you actually inspected the object."
        ),
        "review_packet_sha256": packet_sha256,
        "objects": request_objects,
    }
    (output_dir / "review-request.yaml").write_text(
        yaml.safe_dump(request, sort_keys=False), encoding="utf-8"
    )

    template = {
        "schema_id": REVIEW_TEMPLATE_SCHEMA_ID,
        "handoff_id": handoff.handoff_id,
        "review_kind": "human_object_review",
        "object_geometry_review": True,
        "reviewer": "",
        "reviewer_role": "designer",
        "review_scope": handoff.review.review_scope,
        "human_confirmed_trace": False,
        "reviewed_at": "",
        "basis": "",
        "evidence_refs": ["review-packet.html"],
        "review_packet_sha256": packet_sha256,
        "template_not_signed": True,
        "decisions": decisions,
        "limitations": [
            "fill every geometry and coordinate decision after inspection",
            "pilot subset only; not a full-case geometry review",
            "not survey-grade",
        ],
        "non_claims": [
            "an unsigned template is not a human confirmation",
            "a successful DXF readback is not a compliance conclusion",
        ],
    }
    (output_dir / "review-confirmation-template.yaml").write_text(
        yaml.safe_dump(template, sort_keys=False), encoding="utf-8"
    )

    object_sections = []
    for item in rows:
        obj = handoff.objects[item["source_id"]]
        metric = item["scale_sensitivity"]
        object_sections.append(
            f'<section id="object-{html.escape(item["source_id"])}" '
            'style="border-top:1px solid #ddd;padding:14px 0">'
            f'<h3 style="margin:0 0 6px"><span style="color:{item["color"]}">'
            f'{html.escape(item["source_id"])}</span> '
            f'<small>{html.escape(item["semantic_role"])} → '
            f'{html.escape(item["canonical_id"])}</small></h3>'
            f'<div style="display:flex;gap:16px;flex-wrap:wrap">'
            f'{_local_svg(handoff, obj)}'
            '<table style="font-size:13px;border-collapse:collapse">'
            f'<tr><td>geometry state</td><td><b>{html.escape(item["geometry_state"])}</b></td></tr>'
            f'<tr><td>source object</td><td><code>{html.escape(item["source_object_id"])}</code></td></tr>'
            f'<tr><td>area (local)</td><td>{metric["area_m2"]:.2f} m² '
            f'[{metric["area_range_m2"][0]:.2f}, {metric["area_range_m2"][1]:.2f}]</td></tr>'
            f'<tr><td>perimeter (local)</td><td>{metric["perimeter_m"]:.2f} m '
            f'[{metric["perimeter_range_m"][0]:.2f}, {metric["perimeter_range_m"][1]:.2f}]</td></tr>'
            f'<tr><td>centroid shift</td><td>{metric["centroid_shift_m"]:.3f} m</td></tr>'
            f'<tr><td>geometry hash</td><td><code>{html.escape(item["source_geometry_sha256"][:16])}…</code></td></tr>'
            '</table></div>'
            '<p style="margin:8px 0 0;font-size:13px">'
            'Questions: semantic role? outline at pilot scope? local metric '
            'placement acceptable?</p>'
            "</section>"
        )

    html_text = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8">
<title>CASE-SKETCH-001-HANDOFF-A review packet</title>
<style>
body{{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:1180px;margin:24px auto;padding:0 20px;color:#111}}
code{{font-family:ui-monospace,Consolas,monospace}}
.sketch{{position:relative;width:100%;max-width:760px;border:1px solid #ccc;background:#fff}}
.sketch img{{display:block;width:100%;height:auto}}
.badge{{display:inline-block;padding:3px 8px;border-radius:4px;background:#fff3cd;border:1px solid #e0c56b;font-size:12px}}
</style></head><body>
<h1>CASE-SKETCH-001-HANDOFF-A — review packet</h1>
<p><span class="badge">review required</span>
<span class="badge">not a confirmation</span>
<span class="badge">pilot subset, not survey-grade</span></p>
<p>Source sketch: <code>{html.escape(sketch_path)}</code>
(SHA-256 <code>{handoff.source_sketch_sha256[:16]}…</code>)</p>
<p>Review kind: <b>{html.escape(handoff.review.review_kind)}</b>;
object geometry review: <b>{handoff.review.object_geometry_review}</b>;
human confirmation claimed: <b>false</b>.</p>
<p>Transform: <b>{html.escape(handoff.coordinate.transform_kind)}</b>;
homography applied: <b>{handoff.coordinate.homography_applied}</b>;
frame: <b>{html.escape(handoff.coordinate.target_frame)}</b>;
scale {handoff.coordinate.scale_px_per_m} px/m
(range {handoff.coordinate.scale_range_px_per_m[0]}–{handoff.coordinate.scale_range_px_per_m[1]});
scale source: {html.escape(handoff.coordinate.scale_source)};
origin source: {html.escape(handoff.coordinate.origin_source)}.</p>
<p>Site boundary authority: <b>{html.escape(handoff.site_boundary_authority)}</b>.
The published sketch boundary is not the authoritative site boundary and
does not become canonical SITE-001.</p>
<div class="sketch">
<img src="{html.escape(sketch_href)}" alt="CASE-SKETCH-001 sketch">
{_svg_overlay(handoff, width, height)}
</div>
<p style="font-size:13px">Coloured outlines mark the selected objects in
image space. The small panels below show each object in local metric space
with a scale bar; the bar length follows the declared scale range.</p>
{''.join(object_sections)}
<h2>Road topology</h2>
<pre>{html.escape(json.dumps(handoff.road_topology_report(), indent=2))}</pre>
<h2>How to confirm</h2>
<p>Fill <code>review-confirmation-template.yaml</code>, set
<code>human_confirmed_trace: true</code>, record <code>reviewed_at</code>
and <code>basis</code>, and give every object a geometry and coordinate
decision. The Agent cannot sign this for you.</p>
</body></html>
"""
    (output_dir / "review-packet.html").write_text(html_text, encoding="utf-8")

    return {
        "packet_sha256": packet_sha256,
        "packet_path": packet_path,
        "objects": len(rows),
    }

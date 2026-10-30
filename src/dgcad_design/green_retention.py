"""Post-hoc retention accounting for the 12 original sketch green objects.

M4d-2a scope: **traceability only**.  The building layouts are packed without
treating the original green objects as obstacles, and ``build_green_layout``
clips/generates greens afterwards.  This module measures what happened to each
``SK-GRN-*`` object after the fact; it does not change any layout or check and
it does not claim a landscape design.

Two different questions are reported separately on purpose:

* **area retention** — how much of a source green's area is still candidate
  open space / designed green / geometrically unbuilt ground;
* **intent retention** — whether the *place* stayed a usable, continuous,
  accessible green.  This module cannot establish that.  Retained area is an
  area intersection, not continuity, usability, access, planting or design
  intent; ``area_retention_is_not_intent_retention`` stays ``True`` in every
  report.

Status labels are **descriptive, not gates**.  No tolerance is widened and no
threshold is added to any existing check.
"""
from __future__ import annotations

from typing import Any

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .green import OPEN_SPACE_FILTERS, GreenLayout

SCHEMA_ID = "dgcad.green-retention.v0.1"

#: Descriptive status labels (never a pass/fail gate).
GREEN_STATUSES = (
    "preserved",
    "shrunk",
    "cancelled",
    "occupied_by_buildings",
    "occupied_by_roads",
    "moved",
    "not_applicable",
)

#: A source green counts as *preserved* when at least this share of its
#: in-site area is still candidate open space.  This is a descriptive label
#: boundary, not a design gate (no existing check uses it).
PRESERVED_OPEN_SPACE_RATIO = 0.99
#: Below this share of candidate open space a green is labelled *cancelled*.
CANCELLED_OPEN_SPACE_RATIO = 0.01
#: Building/road occupation share that makes the occupation label dominant.
OCCUPATION_DOMINANT_RATIO = 0.5
#: Area tolerance for "shares no area" (moved test).
SHARED_AREA_TOLERANCE_M2 = 0.01

#: The two candidate open-space layers used by the intersection account.
DESIGNED_GREEN_CLASSIFICATIONS = ("cluster_green", "green_strip")
OPEN_SPACE_CLASSIFICATIONS = (
    "cluster_green",
    "green_strip",
    "supplementary_green",
    "potential_open_space",
)


def _union(geometries) -> Polygon:
    items = [item for item in geometries if item is not None and not item.is_empty]
    if not items:
        return Polygon()
    return unary_union(items)


def _safe_area(geometry) -> float:
    if geometry is None or geometry.is_empty:
        return 0.0
    return float(geometry.area)


def _ratio(part: float, whole: float) -> float:
    if whole <= 0.0:
        return 0.0
    return float(part) / float(whole)


def _describe_status(
    inside_area: float,
    building_area: float,
    road_area: float,
    retained_area: float,
    moved: bool,
    source_area: float,
) -> str:
    """Descriptive label (documented priority; never a gate)."""
    if source_area <= 1e-9 or _ratio(inside_area, source_area) < 0.01:
        return "not_applicable"
    if moved:
        return "moved"
    if _ratio(building_area, inside_area) >= OCCUPATION_DOMINANT_RATIO:
        return "occupied_by_buildings"
    if _ratio(road_area, inside_area) >= OCCUPATION_DOMINANT_RATIO:
        return "occupied_by_roads"
    retained_ratio = _ratio(retained_area, inside_area)
    if retained_ratio < CANCELLED_OPEN_SPACE_RATIO:
        return "cancelled"
    if retained_ratio >= PRESERVED_OPEN_SPACE_RATIO:
        return "preserved"
    return "shrunk"


def green_retention_report(
    design_input: Any,
    building_layout: Any,
    road_layout: Any,
    green_layout: GreenLayout,
    *,
    intent: Any | None = None,
    site_inner: Polygon | None = None,
) -> dict[str, Any]:
    """Measure what happened to every ``design_input.greens`` object.

    Parameters
    ----------
    design_input:
        Case input; ``greens`` are the source objects and ``site_boundary`` /
        ``site_area_m2`` define the site.
    building_layout, road_layout:
        Candidate layouts (duck-typed: ``buildings[*].footprint``,
        ``corridor_union`` / ``sidewalk_union``).
    green_layout:
        Candidate ``GreenLayout`` (its ``greens`` and ``full_site_green``
        parcels are the candidate open-space layer).
    intent:
        Optional ``DesignIntent``; when supplied the source green is annotated
        with the ``group_id`` whose ``green_ids`` contain it (else ``None``).
    site_inner:
        Optional buildable-boundary polygon; defaults to
        ``site_boundary.buffer(-OPEN_SPACE_FILTERS['boundary_setback_m'])``.

    Returns a JSON-serialisable report with per-object detail and a site-level
    summary.  The candidate open-space basis is documented inside the report:
    ``retained_open_space`` intersects the source green with the union of the
    candidate green geometries plus full-site potential-open-space parcels;
    ``retained_designed`` uses only designed classifications; and
    ``free_space_retaining`` uses the strict geometric unbuilt ground
    (site_inner minus buildings, road corridors and sidewalks).
    """
    if site_inner is None:
        site_inner = design_input.site_boundary.buffer(
            -OPEN_SPACE_FILTERS["boundary_setback_m"]
        )
    buildings = list(getattr(building_layout, "buildings", ()) or ())
    building_union = _union([item.footprint for item in buildings])
    road_union = _union(
        [
            getattr(road_layout, "corridor_union", None),
            getattr(road_layout, "sidewalk_union", None),
        ]
    )
    free_space = site_inner.difference(building_union).difference(road_union)

    candidate_greens = list(getattr(green_layout, "greens", ()) or ())
    full_site_green = getattr(green_layout, "full_site_green", None)
    candidate_objects = [
        {
            "green_id": str(item.green_id),
            "classification": str(item.classification),
            "geometry": item.geometry,
            "area_m2": float(item.area_m2),
        }
        for item in candidate_greens
    ]
    if full_site_green is not None:
        candidate_objects.extend(
            {
                "green_id": str(item.green_id),
                "classification": str(item.classification),
                "geometry": item.geometry,
                "area_m2": float(item.area_m2),
            }
            for item in full_site_green.parcels
        )
    designed_union = _union(
        [
            item["geometry"]
            for item in candidate_objects
            if item["classification"] in DESIGNED_GREEN_CLASSIFICATIONS
        ]
    )
    open_space_union = _union(
        [
            item["geometry"]
            for item in candidate_objects
            if item["classification"] in OPEN_SPACE_CLASSIFICATIONS
        ]
    )
    source_greens = list(getattr(design_input, "greens", ()) or ())
    source_union = _union([item.geometry for item in source_greens])

    group_by_green: dict[str, str] = {}
    if intent is not None:
        for group in getattr(intent, "groups", ()) or ():
            for green_id in getattr(group, "green_ids", ()) or ():
                group_by_green[str(green_id)] = str(group.group_id)

    cluster_by_source: dict[str, Any] = {}
    for item in candidate_greens:
        if item.classification != "cluster_green":
            continue
        cluster_by_source.setdefault(str(item.green_id), item)

    objects: list[dict[str, Any]] = []
    totals = {
        "source_area_m2": 0.0,
        "inside_site_area_m2": 0.0,
        "building_occupied_area_m2": 0.0,
        "road_occupied_area_m2": 0.0,
        "retained_open_space_area_m2": 0.0,
        "retained_designed_area_m2": 0.0,
        "free_space_retaining_area_m2": 0.0,
        "lost_area_m2": 0.0,
        "outside_site_area_m2": 0.0,
    }
    status_counts = {status: 0 for status in GREEN_STATUSES}
    for source in source_greens:
        source_area = float(getattr(source, "area_m2", source.geometry.area))
        inside = source.geometry.intersection(site_inner)
        inside_area = _safe_area(inside)
        outside_area = max(0.0, source_area - inside_area)
        building_area = _safe_area(inside.intersection(building_union))
        road_area = _safe_area(
            inside.difference(building_union).intersection(road_union)
        )
        ground = inside.difference(building_union).difference(road_union)
        retained_open = _safe_area(ground.intersection(open_space_union))
        retained_designed = _safe_area(
            ground.intersection(designed_union)
        )
        free_space_area = _safe_area(inside.intersection(free_space))
        lost_area = max(
            0.0, inside_area - building_area - road_area - retained_open
        )
        candidate_cluster = cluster_by_source.get(str(source.trace_id))
        candidate_cluster_area = (
            None
            if candidate_cluster is None
            else float(candidate_cluster.area_m2)
        )
        candidate_cluster_shared = (
            None
            if candidate_cluster is None
            else _safe_area(
                candidate_cluster.geometry.intersection(source.geometry)
            )
        )
        moved = bool(
            candidate_cluster is not None
            and candidate_cluster_area is not None
            and candidate_cluster_area > 0.0
            and candidate_cluster_shared is not None
            and candidate_cluster_shared <= SHARED_AREA_TOLERANCE_M2
        )
        status = _describe_status(
            inside_area=inside_area,
            building_area=building_area,
            road_area=road_area,
            retained_area=retained_open,
            moved=moved,
            source_area=source_area,
        )
        status_counts[status] += 1
        totals["source_area_m2"] += source_area
        totals["inside_site_area_m2"] += inside_area
        totals["building_occupied_area_m2"] += building_area
        totals["road_occupied_area_m2"] += road_area
        totals["retained_open_space_area_m2"] += retained_open
        totals["retained_designed_area_m2"] += retained_designed
        totals["free_space_retaining_area_m2"] += free_space_area
        totals["lost_area_m2"] += lost_area
        totals["outside_site_area_m2"] += outside_area
        objects.append(
            {
                "green_id": str(source.trace_id),
                "group_id": group_by_green.get(str(source.trace_id)),
                "status": status,
                "source_area_m2": round(source_area, 3),
                "inside_site_area_m2": round(inside_area, 3),
                "outside_site_area_m2": round(outside_area, 3),
                "building_occupied_area_m2": round(building_area, 3),
                "road_occupied_area_m2": round(road_area, 3),
                "retained_open_space_area_m2": round(retained_open, 3),
                "retained_designed_area_m2": round(retained_designed, 3),
                "free_space_retaining_area_m2": round(free_space_area, 3),
                "lost_area_m2": round(lost_area, 3),
                "inside_site_ratio": round(
                    _ratio(inside_area, source_area), 4
                ),
                "retained_open_space_ratio_of_inside": round(
                    _ratio(retained_open, inside_area), 4
                ),
                "retained_open_space_ratio_of_source": round(
                    _ratio(retained_open, source_area), 4
                ),
                "occupied_by_buildings_ratio_of_inside": round(
                    _ratio(building_area, inside_area), 4
                ),
                "occupied_by_roads_ratio_of_inside": round(
                    _ratio(road_area, inside_area), 4
                ),
                "lost_ratio_of_inside": round(
                    _ratio(lost_area, inside_area), 4
                ),
                "candidate_cluster_id": (
                    None
                    if candidate_cluster is None
                    else str(candidate_cluster.green_id)
                ),
                "candidate_cluster_area_m2": (
                    None
                    if candidate_cluster_area is None
                    else round(candidate_cluster_area, 3)
                ),
                "candidate_cluster_shared_area_m2": (
                    None
                    if candidate_cluster_shared is None
                    else round(candidate_cluster_shared, 3)
                ),
            }
        )

    # ---- new open space: candidate area that is not source green area -----
    candidate_details = []
    for item in candidate_objects:
        overlap = _safe_area(item["geometry"].intersection(source_union))
        new_area = max(0.0, item["area_m2"] - overlap)
        candidate_details.append(
            {
                "green_id": item["green_id"],
                "classification": item["classification"],
                "area_m2": round(item["area_m2"], 3),
                "overlap_with_source_greens_m2": round(overlap, 3),
                "new_area_m2": round(new_area, 3),
            }
        )
    # set-based totals: candidate objects may overlap each other (designed
    # greens also appear as full-site parcels), so the totals are union areas,
    # never a sum of per-object remainders
    new_open_space_area = _safe_area(open_space_union.difference(source_union))
    new_designed_area = _safe_area(designed_union.difference(source_union))

    def _ratio_of_source(value: float) -> float:
        return round(_ratio(value, totals["source_area_m2"]), 4)

    summary = {
        "source_green_count": len(source_greens),
        "traced_green_count": len(objects),
        "status_counts": status_counts,
        "source_area_m2": round(totals["source_area_m2"], 3),
        "inside_site_area_m2": round(totals["inside_site_area_m2"], 3),
        "outside_site_area_m2": round(totals["outside_site_area_m2"], 3),
        "building_occupied_area_m2": round(
            totals["building_occupied_area_m2"], 3
        ),
        "road_occupied_area_m2": round(totals["road_occupied_area_m2"], 3),
        "retained_open_space_area_m2": round(
            totals["retained_open_space_area_m2"], 3
        ),
        "retained_designed_area_m2": round(
            totals["retained_designed_area_m2"], 3
        ),
        "free_space_retaining_area_m2": round(
            totals["free_space_retaining_area_m2"], 3
        ),
        "lost_area_m2": round(totals["lost_area_m2"], 3),
        "retained_open_space_ratio_of_source": _ratio_of_source(
            totals["retained_open_space_area_m2"]
        ),
        "retained_designed_ratio_of_source": _ratio_of_source(
            totals["retained_designed_area_m2"]
        ),
        "free_space_retaining_ratio_of_source": _ratio_of_source(
            totals["free_space_retaining_area_m2"]
        ),
        "building_occupied_ratio_of_source": _ratio_of_source(
            totals["building_occupied_area_m2"]
        ),
        "road_occupied_ratio_of_source": _ratio_of_source(
            totals["road_occupied_area_m2"]
        ),
        "lost_ratio_of_source": _ratio_of_source(totals["lost_area_m2"]),
        "new_open_space_area_m2": round(new_open_space_area, 3),
        "new_designed_green_area_m2": round(new_designed_area, 3),
        "candidate_object_count": len(candidate_objects),
        "new_open_space_object_count": sum(
            1 for item in candidate_details if item["new_area_m2"] > 0.01
        ),
    }
    candidate_basis = {
        "retained_open_space": (
            "source green ∩ union(candidate green geometries + full-site "
            "potential-open-space parcels)"
        ),
        "retained_designed": (
            "source green ∩ union(cluster_green, green_strip)"
        ),
        "free_space_retaining": (
            "source green ∩ (site_inner − building footprints − road "
            "corridor − sidewalks)"
        ),
        "note": (
            "the building layout is packed without the source greens as "
            "obstacles; every number is a post-hoc area intersection"
        ),
    }

    return {
        "schema_id": SCHEMA_ID,
        "area_retention_is_not_intent_retention": True,
        "descriptive_status_not_gate": True,
        "status_labels": list(GREEN_STATUSES),
        "candidate_open_space_basis": candidate_basis,
        "status_thresholds": {
            "preserved_open_space_ratio": PRESERVED_OPEN_SPACE_RATIO,
            "cancelled_open_space_ratio": CANCELLED_OPEN_SPACE_RATIO,
            "occupation_dominant_ratio": OCCUPATION_DOMINANT_RATIO,
            "shared_area_tolerance_m2": SHARED_AREA_TOLERANCE_M2,
            "note": (
                "labels are descriptive reporting devices; no existing check "
                "reads them and no tolerance was widened"
            ),
        },
        "summary": summary,
        "objects": objects,
        "candidate_objects": candidate_details,
        "note": (
            "retained area is an area intersection; it does not establish "
            "spatial continuity, usability, access, planting or design intent "
            "for the original green. The source greens are not treated as "
            "obstacles by the building layout, so occupation was measured "
            "after the fact, not prevented."
        ),
    }


def green_retention_summary(report: dict[str, Any]) -> dict[str, Any]:
    """Small helper: the A/B/baseline comparison row for a report."""
    summary = dict(report["summary"])
    summary["preserved_count"] = report["summary"]["status_counts"]["preserved"]
    summary["shrunk_count"] = report["summary"]["status_counts"]["shrunk"]
    summary["cancelled_count"] = report["summary"]["status_counts"]["cancelled"]
    summary["occupied_by_buildings_count"] = report["summary"][
        "status_counts"
    ]["occupied_by_buildings"]
    summary["occupied_by_roads_count"] = report["summary"]["status_counts"][
        "occupied_by_roads"
    ]
    summary["moved_count"] = report["summary"]["status_counts"]["moved"]
    summary["not_applicable_count"] = report["summary"]["status_counts"][
        "not_applicable"
    ]
    return summary

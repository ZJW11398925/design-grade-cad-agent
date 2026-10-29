from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .input import DesignInput
from .roads import RoadLayout

#: Filter rules behind the *candidate* open-space accounting.  The candidate
#: number is produced by these filters and by summing classified areas; the
#: unbuilt number is the plain geometric union area (no extra filters).
OPEN_SPACE_FILTERS = {
    "boundary_setback_m": 5.0,
    "obstacle_buffer_m": 0.5,
    "min_supplementary_polygon_m2": 100.0,
}

#: Rules behind the *full-site designed green* account.  The designed green
#: layer is generated as disjoint parcels of the open space that is left after
#: all building footprints, road corridors and sidewalks are removed (plus the
#: declared obstacle buffer).  A parcel is designed green only if it is large
#: enough and wide enough to be a usable green area; narrower or smaller
#: leftovers stay in ``residual_open_space_area_m2`` and are not counted.
#: These are a schematic allocation rule, not a landscape design: no plaza,
#: hardscape, path, planting-species, continuity or green-quality criterion is
#: claimed.
FULL_SITE_GREEN_CRITERIA = {
    "boundary_setback_m": 5.0,
    "obstacle_buffer_m": 0.5,
    "min_parcel_area_m2": 100.0,
    "min_parcel_width_m": 3.0,
}


def _geometry_payload(geometry) -> dict[str, Any]:
    """Serialise a Polygon / MultiPolygon green geometry honestly.

    A clipped green can be a MultiPolygon (e.g. a cluster split by a building
    or road); the payload keeps every part instead of assuming a single
    exterior ring.
    """

    if geometry.geom_type == "Polygon":
        return {
            "type": "Polygon",
            "coordinates": [
                [list(coord) for coord in geometry.exterior.coords]
            ],
        }
    if geometry.geom_type == "MultiPolygon":
        return {
            "type": "MultiPolygon",
            "coordinates": [
                [[list(coord) for coord in part.exterior.coords]]
                for part in geometry.geoms
            ],
        }
    return {"type": geometry.geom_type, "coordinates": None}


@dataclass(frozen=True)
class GreenDesign:
    green_id: str
    geometry: Polygon
    classification: str
    area_m2: float
    label_anchor: tuple[float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "green_id": self.green_id,
            "classification": self.classification,
            "area_m2": self.area_m2,
            "label_anchor": list(self.label_anchor),
            "geometry": _geometry_payload(self.geometry),
        }



@dataclass(frozen=True)
class FullSiteGreenDesign:
    """Generated full-site designed-green account (all 55 buildings / 44 roads).

    ``parcels`` are disjoint polygons of the open space left after removing all
    building footprints, road corridors and sidewalks (plus the declared
    obstacle buffer) and after dropping parcels that are too small or too
    narrow to be usable green.  ``area_m2`` is the sum of the parcel areas;
    ``ratio`` uses the published site area as denominator (the same denominator
    as the candidate and unbuilt accounts).  ``gap_m2`` is the shortfall to the
    declared ``target_ratio`` and is ``0.0`` only when the target is met.

    This is a schematic *allocation* of open space as green parcels.  It is not
    a landscape design and claims no continuity, usability, planting or
    green-quality criterion.
    """

    parcels: tuple[GreenDesign, ...]
    area_m2: float
    ratio: float
    target_ratio: float
    target_area_m2: float
    gap_m2: float
    gap_ratio: float
    residual_area_m2: float
    open_space_area_m2: float
    criteria: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "parcel_count": len(self.parcels),
            "designed_green_area_m2": self.area_m2,
            "designed_green_ratio": self.ratio,
            "target_ratio": self.target_ratio,
            "target_area_m2": self.target_area_m2,
            "gap_m2": self.gap_m2,
            "gap_ratio": self.gap_ratio,
            "residual_open_space_area_m2": self.residual_area_m2,
            "open_space_area_m2": self.open_space_area_m2,
            "criteria": dict(self.criteria),
            "parcels": [item.to_dict() for item in self.parcels],
        }


@dataclass(frozen=True)
class GreenLayout:
    """Honest green-space semantics with two distinct open-space accounts.

    ``candidate_open_space_*`` is the candidate open space of the current
    filter rules (5 m boundary setback, 0.5 m obstacle buffer, supplementary
    polygons >= 100 m2) and is the sum of the classified green areas; it is
    **not** a geometric open-space measurement and **not** designed green.

    ``unbuilt_area_m2`` / ``unbuilt_ratio`` are the strict geometric account:
    the area of ``site_boundary.buffer(-5.0)`` minus the union of building
    footprints, road corridors and sidewalks, with no extra buffer and no
    minimum-area filtering.

    ``designed_green_*`` covers only the designed classifications (cluster
    green + green strips); the supplementary classification is the remaining
    occupiable space whose planning meaning is expressed by the upper-layer
    checks, not by this data model.

    ``full_site_green`` is a separate, generated full-site account: disjoint
    designed green parcels of the open space left outside every building
    footprint, road corridor and sidewalk, with the gap to the declared
    ``green_ratio_min`` target.  It is not the same account as
    ``candidate_open_space_*`` or ``unbuilt_*`` and it is not a landscape
    design.
    """

    greens: tuple[GreenDesign, ...]
    focus_greens: tuple[GreenDesign, ...]
    cluster_area_m2: float
    strip_area_m2: float
    supplementary_area_m2: float
    candidate_open_space_area_m2: float
    candidate_open_space_ratio: float
    unbuilt_area_m2: float
    unbuilt_ratio: float
    designed_green_area_m2: float
    designed_green_ratio: float
    target_ratio: float
    dropped_cluster_ids: tuple[str, ...]
    full_site_green: FullSiteGreenDesign | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "green_count": len(self.greens),
            "cluster_area_m2": self.cluster_area_m2,
            "strip_area_m2": self.strip_area_m2,
            "supplementary_area_m2": self.supplementary_area_m2,
            "candidate_open_space_area_m2": self.candidate_open_space_area_m2,
            "candidate_open_space_ratio": self.candidate_open_space_ratio,
            "unbuilt_area_m2": self.unbuilt_area_m2,
            "unbuilt_ratio": self.unbuilt_ratio,
            "designed_green_area_m2": self.designed_green_area_m2,
            "designed_green_ratio": self.designed_green_ratio,
            "open_space_filters": dict(OPEN_SPACE_FILTERS),
            "target_ratio": self.target_ratio,
            "dropped_cluster_ids": list(self.dropped_cluster_ids),
            "greens": [item.to_dict() for item in self.greens],
            "full_site_green": (
                None
                if self.full_site_green is None
                else self.full_site_green.to_dict()
            ),
        }


def _explode(geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    return []


def _anchor(polygon: Polygon) -> tuple[float, float]:
    point = polygon.representative_point()
    return (float(point.x), float(point.y))


def _parcel_min_width_ok(polygon: Polygon, min_width_m: float) -> bool:
    """True when ``polygon`` contains a disc of radius ``min_width_m / 2``.

    The erosion test is a conservative usable-width criterion: a parcel that
    disappears after eroding by half the declared minimum width is too narrow
    to be a designed green parcel and stays in the residual open space.
    """

    if min_width_m <= 0:
        return True
    return not polygon.buffer(-min_width_m / 2.0).is_empty


def design_full_site_green(
    design_input: DesignInput,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    basis: DesignBasis,
    *,
    open_space=None,
) -> FullSiteGreenDesign:
    """Generate the full-site designed-green parcels (all buildings / roads).

    The open space is ``site_boundary.buffer(-boundary_setback)`` minus every
    building footprint, road corridor and sidewalk, minus the declared obstacle
    buffer.  Each connected component that is at least
    ``FULL_SITE_GREEN_CRITERIA["min_parcel_area_m2"]`` and at least
    ``FULL_SITE_GREEN_CRITERIA["min_parcel_width_m"]`` wide becomes one designed
    green parcel with recorded geometry, area and label anchor.  Everything
    else is reported as residual open space and is **not** counted as green.

    The target ratio is ``basis.green_ratio_min``; the gap to the target is
    reported as ``gap_m2`` / ``gap_ratio`` and is never hidden.  This function
    does not widen a tolerance or relabel the unbuilt account as green.
    """

    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    obstacle_buffer_m = OPEN_SPACE_FILTERS["obstacle_buffer_m"]
    if open_space is None:
        obstacles = unary_union(
            [item.footprint for item in building_layout.buildings]
            + [road_layout.corridor_union, road_layout.sidewalk_union]
        )
        open_space = site_inner.difference(
            obstacles.buffer(obstacle_buffer_m)
        )
    criteria = {
        "boundary_setback_m": basis.boundary_setback_m,
        "obstacle_buffer_m": obstacle_buffer_m,
        "min_parcel_area_m2": FULL_SITE_GREEN_CRITERIA[
            "min_parcel_area_m2"
        ],
        "min_parcel_width_m": FULL_SITE_GREEN_CRITERIA[
            "min_parcel_width_m"
        ],
    }
    parts = sorted(
        _explode(open_space),
        key=lambda item: (-item.area, item.bounds),
    )
    parcels: list[GreenDesign] = []
    residual_area = 0.0
    for polygon in parts:
        if polygon.area < criteria["min_parcel_area_m2"]:
            residual_area += polygon.area
            continue
        if not _parcel_min_width_ok(
            polygon, criteria["min_parcel_width_m"]
        ):
            residual_area += polygon.area
            continue
        parcels.append(
            GreenDesign(
                green_id=f"GREEN-FS-{len(parcels) + 1:03d}",
                geometry=polygon,
                classification="designed_green",
                area_m2=float(polygon.area),
                label_anchor=_anchor(polygon),
            )
        )
    area = float(sum(item.area_m2 for item in parcels))
    site_area = float(design_input.site_area_m2)
    target_ratio = float(basis.green_ratio_min)
    target_area = target_ratio * site_area
    gap = max(0.0, target_area - area)
    return FullSiteGreenDesign(
        parcels=tuple(parcels),
        area_m2=area,
        ratio=(area / site_area) if site_area else 0.0,
        target_ratio=target_ratio,
        target_area_m2=target_area,
        gap_m2=gap,
        gap_ratio=(gap / site_area) if site_area else 0.0,
        residual_area_m2=float(residual_area),
        open_space_area_m2=float(open_space.area),
        criteria=criteria,
    )


def build_green_layout(
    design_input: DesignInput,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    basis: DesignBasis,
    focus_box,
) -> GreenLayout:
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    obstacles = unary_union(
        [item.footprint for item in building_layout.buildings]
        + [road_layout.corridor_union, road_layout.sidewalk_union]
    )
    available = site_inner.difference(
        obstacles.buffer(OPEN_SPACE_FILTERS["obstacle_buffer_m"])
    )
    # strict geometric account: no extra buffer, no minimum-area filtering
    unbuilt_area = float(site_inner.difference(obstacles).area)
    full_site_green = design_full_site_green(
        design_input,
        building_layout,
        road_layout,
        basis,
        open_space=available,
    )

    greens: list[GreenDesign] = []
    dropped: list[str] = []
    cluster_geometries = []
    for cluster in design_input.greens:
        clipped = cluster.geometry.intersection(site_inner).difference(
            obstacles
        )
        if clipped.is_empty or clipped.area < 1.0:
            dropped.append(cluster.trace_id)
            continue
        if clipped.area < cluster.area_m2 * 0.5:
            dropped.append(cluster.trace_id)
            continue
        cluster_geometries.append(clipped)
        greens.append(
            GreenDesign(
                green_id=cluster.trace_id,
                geometry=clipped,
                classification="cluster_green",
                area_m2=float(clipped.area),
                label_anchor=_anchor(clipped),
            )
        )

    strip_geometries = []
    for index, strip in enumerate(building_layout.green_strips, start=1):
        clipped = strip.intersection(site_inner).difference(obstacles)
        if clipped.is_empty or clipped.area < 1.0:
            continue
        strip_geometries.append(clipped)
        greens.append(
            GreenDesign(
                green_id=f"GREEN-STRIP-{index:02d}",
                geometry=clipped,
                classification="green_strip",
                area_m2=float(clipped.area),
                label_anchor=_anchor(clipped),
            )
        )

    occupied = unary_union(cluster_geometries + strip_geometries)
    supplementary = available.difference(occupied)
    for index, polygon in enumerate(
        sorted(_explode(supplementary), key=lambda item: -item.area),
        start=1,
    ):
        if polygon.area < OPEN_SPACE_FILTERS["min_supplementary_polygon_m2"]:
            continue
        greens.append(
            GreenDesign(
                green_id=f"GREEN-SUPP-{index:03d}",
                geometry=polygon,
                classification="supplementary_green",
                area_m2=float(polygon.area),
                label_anchor=_anchor(polygon),
            )
        )

    cluster_area = sum(
        item.area_m2
        for item in greens
        if item.classification == "cluster_green"
    )
    strip_area = sum(
        item.area_m2
        for item in greens
        if item.classification == "green_strip"
    )
    supplementary_area = sum(
        item.area_m2
        for item in greens
        if item.classification == "supplementary_green"
    )
    total_area = cluster_area + strip_area + supplementary_area
    designed_green_area = cluster_area + strip_area
    site_area = design_input.site_area_m2
    focus_greens = tuple(
        item for item in greens if item.geometry.intersects(focus_box)
    )
    return GreenLayout(
        greens=tuple(greens),
        focus_greens=focus_greens,
        cluster_area_m2=cluster_area,
        strip_area_m2=strip_area,
        supplementary_area_m2=supplementary_area,
        candidate_open_space_area_m2=total_area,
        candidate_open_space_ratio=total_area / site_area,
        unbuilt_area_m2=unbuilt_area,
        unbuilt_ratio=unbuilt_area / site_area,
        designed_green_area_m2=designed_green_area,
        designed_green_ratio=designed_green_area / site_area,
        target_ratio=basis.green_ratio_min,
        dropped_cluster_ids=tuple(dropped),
        full_site_green=full_site_green,
    )

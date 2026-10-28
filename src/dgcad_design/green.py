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
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [list(coord) for coord in self.geometry.exterior.coords]
                ],
            },
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
    )

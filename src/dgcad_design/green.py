from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import Polygon
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .input import DesignInput
from .roads import RoadLayout


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
    """Honest green-space semantics.

    ``open_space_*`` is the total unbuilt/open space; it is NOT "designed
    green".  ``designed_green_*`` covers only the designed classifications
    (cluster green + green strips); the supplementary classification is the
    remaining occupiable space, whose planning meaning is expressed by the
    upper-layer checks, not by this data model.
    """

    greens: tuple[GreenDesign, ...]
    focus_greens: tuple[GreenDesign, ...]
    cluster_area_m2: float
    strip_area_m2: float
    supplementary_area_m2: float
    open_space_area_m2: float
    designed_green_area_m2: float
    open_space_ratio: float
    designed_green_ratio: float
    target_ratio: float
    dropped_cluster_ids: tuple[str, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "green_count": len(self.greens),
            "cluster_area_m2": self.cluster_area_m2,
            "strip_area_m2": self.strip_area_m2,
            "supplementary_area_m2": self.supplementary_area_m2,
            "open_space_area_m2": self.open_space_area_m2,
            "designed_green_area_m2": self.designed_green_area_m2,
            "open_space_ratio": self.open_space_ratio,
            "designed_green_ratio": self.designed_green_ratio,
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
    available = site_inner.difference(obstacles.buffer(0.5))

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
        if polygon.area < 100.0:
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
        open_space_area_m2=total_area,
        designed_green_area_m2=designed_green_area,
        open_space_ratio=total_area / site_area,
        designed_green_ratio=designed_green_area / site_area,
        target_ratio=basis.green_ratio_min,
        dropped_cluster_ids=tuple(dropped),
    )

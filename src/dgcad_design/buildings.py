from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union

from .basis import DesignBasis
from .input import BuildingInput, DesignInput
from .intent import DesignIntent


@dataclass(frozen=True)
class StandardBuilding:
    building_id: str
    unit_count: int
    is_facility: bool
    footprint: Polygon
    unit_lines: tuple[LineString, ...]
    households: int
    gfa_m2: float
    height_m: float
    source_centroid: tuple[float, float]
    design_centroid: tuple[float, float]
    displacement_m: float
    source_area_m2: float
    source_orientation_deg: float
    design_orientation_deg: float
    subgroup_id: str | None
    row_index: int | None
    label_anchor: tuple[float, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "building_id": self.building_id,
            "unit_count": self.unit_count,
            "is_facility": self.is_facility,
            "households": self.households,
            "gfa_m2": self.gfa_m2,
            "height_m": self.height_m,
            "footprint": {
                "type": "Polygon",
                "coordinates": [
                    [list(coord) for coord in self.footprint.exterior.coords]
                ],
            },
            "unit_lines": [
                [list(coord) for coord in line.coords]
                for line in self.unit_lines
            ],
            "source_centroid": list(self.source_centroid),
            "design_centroid": list(self.design_centroid),
            "displacement_m": self.displacement_m,
            "source_area_m2": self.source_area_m2,
            "design_area_m2": self.footprint.area,
            "source_orientation_deg": self.source_orientation_deg,
            "design_orientation_deg": self.design_orientation_deg,
            "subgroup_id": self.subgroup_id,
            "row_index": self.row_index,
            "label_anchor": list(self.label_anchor),
        }


@dataclass(frozen=True)
class BuildingLayout:
    buildings: tuple[StandardBuilding, ...]
    focus_buildings: tuple[StandardBuilding, ...]
    rows: tuple[dict[str, Any], ...]
    green_strips: tuple[Polygon, ...]
    dropped_focus_building_ids: tuple[str, ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "building_count": len(self.buildings),
            "focus_building_count": len(self.focus_buildings),
            "dropped_focus_building_ids": list(
                self.dropped_focus_building_ids
            ),
            "rows": list(self.rows),
            "buildings": [item.to_dict() for item in self.buildings],
            "green_strip_count": len(self.green_strips),
            "green_strip_area_m2": sum(
                polygon.area for polygon in self.green_strips
            ),
        }


def _rect(center: tuple[float, float], width: float, depth: float, angle: float) -> Polygon:
    rectangle = box(
        -width / 2,
        -depth / 2,
        width / 2,
        depth / 2,
    )
    if angle:
        rectangle = rotate(
            rectangle, angle, origin=(0, 0), use_radians=False
        )
    return translate(rectangle, xoff=center[0], yoff=center[1])


def _unit_lines(
    center: tuple[float, float],
    width: float,
    depth: float,
    unit_width: float,
    unit_count: int,
    angle: float,
) -> tuple[LineString, ...]:
    lines = []
    for index in range(1, unit_count):
        x = -width / 2 + index * unit_width
        line = LineString([(x, -depth / 2), (x, depth / 2)])
        if angle:
            line = rotate(line, angle, origin=(0, 0), use_radians=False)
        lines.append(translate(line, xoff=center[0], yoff=center[1]))
    return tuple(lines)


def _standard_building(
    item: BuildingInput,
    basis: DesignBasis,
    *,
    center: tuple[float, float] | None = None,
    angle: float | None = None,
    row_index: int | None = None,
    subgroup_id: str | None = None,
) -> StandardBuilding:
    if item.is_facility:
        width = 30.0
        depth = 20.0
        unit_count = 0
        households = 0
        gfa = basis.facility_gfa_m2
    else:
        unit_count = int(item.unit_count or 0)
        width = basis.building_width(unit_count)
        depth = basis.staircase_depth_m
        households = basis.households(unit_count)
        gfa = (
            unit_count
            * basis.households_per_staircase_per_floor
            * basis.dwelling_gfa_m2
            * basis.floors
        )
    design_center = center or item.centroid
    design_angle = item.orientation_deg if angle is None else angle
    footprint = _rect(design_center, width, depth, design_angle)
    lines = _unit_lines(
        design_center,
        width,
        depth,
        basis.staircase_width_m,
        unit_count,
        design_angle,
    )
    displacement = math.hypot(
        design_center[0] - item.centroid[0],
        design_center[1] - item.centroid[1],
    )
    label_anchor = (
        design_center[0],
        design_center[1] + depth / 2 + 2.0,
    )
    return StandardBuilding(
        building_id=item.trace_id,
        unit_count=unit_count,
        is_facility=item.is_facility,
        footprint=footprint,
        unit_lines=lines,
        households=households,
        gfa_m2=gfa,
        height_m=basis.building_height_m(),
        source_centroid=item.centroid,
        design_centroid=design_center,
        displacement_m=displacement,
        source_area_m2=item.area_m2,
        source_orientation_deg=item.orientation_deg,
        design_orientation_deg=design_angle,
        subgroup_id=subgroup_id,
        row_index=row_index,
        label_anchor=label_anchor,
    )


def standardize_all(
    design_input: DesignInput, basis: DesignBasis
) -> dict[str, StandardBuilding]:
    return {
        item.trace_id: _standard_building(item, basis)
        for item in design_input.buildings
    }


def find_focus_design_rect(
    design_input: DesignInput,
    intent: DesignIntent,
    basis: DesignBasis,
) -> tuple[float, float, float, float] | None:
    site_inner = design_input.site_boundary.buffer(
        -basis.boundary_setback_m
    )
    main_lines = [
        road.centerline
        for road in design_input.roads
        if road.class_candidate == "main_road"
    ]
    if not main_lines:
        return None
    main_union = unary_union(main_lines)
    obstacle = main_union.buffer(
        basis.road_widths["main_road"] / 2
        + basis.building_road_clearance_m
        + 1.0
    )
    focus_area = box(*intent.focus_bbox).intersection(site_inner)
    free = focus_area.difference(obstacle)
    minx, miny, maxx, maxy = focus_area.bounds
    for width in (160.0, 150.0, 140.0, 130.0, 120.0):
        for height in (140.0, 130.0, 120.0, 110.0, 100.0, 90.0):
            x = minx
            while x + width <= maxx:
                y = miny
                while y + height <= maxy:
                    candidate = box(x, y, x + width, y + height)
                    if free.contains(candidate):
                        return (x, y, x + width, y + height)
                    y += 5.0
                x += 5.0
    return None


def layout_focus_region(
    design_input: DesignInput,
    intent: DesignIntent,
    basis: DesignBasis,
    standardized: dict[str, StandardBuilding],
    site_inner: Polygon,
    design_rect: tuple[float, float, float, float] | None = None,
) -> BuildingLayout:
    focus_ids = set(intent.focus_building_ids)
    by_id = {item.trace_id: item for item in design_input.buildings}
    focus = [by_id[trace_id] for trace_id in intent.focus_building_ids]
    focus.sort(
        key=lambda item: (
            -(item.unit_count or 0),
            item.centroid[1],
            item.centroid[0],
        )
    )

    if design_rect is not None:
        minx, miny, maxx, maxy = design_rect
        margin = 5.0
        capacity = (maxx - minx) - 2 * margin
    else:
        source_boxes = [
            by_id[trace_id].geometry.bounds for trace_id in focus_ids
        ]
        minx = min(item[0] for item in source_boxes)
        miny = min(item[1] for item in source_boxes)
        maxx = max(item[2] for item in source_boxes)
        maxy = max(item[3] for item in source_boxes)
        margin = 15.0
        capacity = (maxx - minx) + 20.0 - 2 * margin
    side_gap = basis.side_spacing_m
    depth = basis.staircase_depth_m
    row_gap = basis.north_south_spacing_m

    rows: list[list[BuildingInput]] = []
    current: list[BuildingInput] = []
    current_width = 0.0
    for item in focus:
        width = (
            30.0
            if item.is_facility
            else basis.building_width(int(item.unit_count or 0))
        )
        extra = width if not current else side_gap + width
        if current and current_width + extra > capacity:
            rows.append(current)
            current = [item]
            current_width = width
        else:
            current.append(item)
            current_width += extra
    if current:
        rows.append(current)

    row_y = miny
    placed: dict[str, StandardBuilding] = {}
    row_records: list[dict[str, Any]] = []
    green_strips: list[Polygon] = []
    dropped: list[str] = []
    for row_index, row in enumerate(rows, start=1):
        if row_y + depth > maxy:
            dropped.extend(item.trace_id for item in row)
            continue
        widths = [
            30.0
            if item.is_facility
            else basis.building_width(int(item.unit_count or 0))
            for item in row
        ]
        total_width = sum(widths) + side_gap * (len(row) - 1)
        start_x = minx + margin + (capacity - total_width) / 2
        cursor = start_x
        subgroup_id = f"FOCUS-{min(3, (row_index + 1) // 2)}"
        row_ids: list[str] = []
        for item, width in zip(row, widths):
            center = (cursor + width / 2, row_y + depth / 2)
            building = _standard_building(
                item,
                basis,
                center=center,
                angle=0.0,
                row_index=row_index,
                subgroup_id=subgroup_id,
            )
            placed[item.trace_id] = building
            row_ids.append(item.trace_id)
            cursor += width + side_gap
        row_records.append(
            {
                "row": row_index,
                "subgroup_id": subgroup_id,
                "y": row_y,
                "building_ids": row_ids,
                "north_south_gap_m": row_gap,
            }
        )
        if row_y + depth + row_gap <= maxy:
            strip = box(
                minx + margin,
                row_y + depth + row_gap / 2 - 4.0,
                maxx - margin,
                row_y + depth + row_gap / 2 + 4.0,
            )
            green_strips.append(strip)
        row_y += depth + row_gap

    if design_rect is None:
        tolerant = site_inner.buffer(0.01)
        shift_x = 0.0
        while shift_x < 80.0:
            if all(
                tolerant.contains(
                    translate(item.footprint, xoff=shift_x)
                )
                for item in placed.values()
            ):
                break
            shift_x += 2.0
        if shift_x >= 80.0:
            raise ValueError(
                "focus layout cannot fit inside the declared boundary setback"
            )
        if shift_x:
            placed = {
                trace_id: _standard_building(
                    by_id[trace_id],
                    basis,
                    center=(
                        building.design_centroid[0] + shift_x,
                        building.design_centroid[1],
                    ),
                    angle=0.0,
                    row_index=building.row_index,
                    subgroup_id=building.subgroup_id,
                )
                for trace_id, building in placed.items()
            }
            green_strips = [
                translate(strip, xoff=shift_x)
                for strip in green_strips
            ]

    dropped.extend(
        trace_id
        for trace_id in intent.focus_building_ids
        if trace_id not in placed
    )
    focus_buildings = tuple(
        placed[trace_id]
        for trace_id in intent.focus_building_ids
        if trace_id in placed
    )
    all_buildings = []
    for item in design_input.buildings:
        if item.trace_id in placed:
            all_buildings.append(placed[item.trace_id])
        else:
            all_buildings.append(standardized[item.trace_id])
    return BuildingLayout(
        buildings=tuple(all_buildings),
        focus_buildings=focus_buildings,
        rows=tuple(row_records),
        green_strips=tuple(green_strips),
        dropped_focus_building_ids=tuple(sorted(set(dropped))),
    )


def row_spacing_report(
    layout: BuildingLayout, basis: DesignBasis
) -> dict[str, Any]:
    pairs = []
    violations = []
    buildings = sorted(
        layout.focus_buildings, key=lambda item: item.design_centroid[1]
    )
    for index, first in enumerate(buildings):
        for second in buildings[index + 1 :]:
            first_bounds = first.footprint.bounds
            second_bounds = second.footprint.bounds
            x_overlap = min(first_bounds[2], second_bounds[2]) - max(
                first_bounds[0], second_bounds[0]
            )
            if x_overlap <= 0:
                continue
            gap = max(
                second_bounds[1] - first_bounds[3],
                first_bounds[1] - second_bounds[3],
            )
            pairs.append(
                {
                    "a": first.building_id,
                    "b": second.building_id,
                    "gap_m": gap,
                }
            )
            if gap < basis.north_south_spacing_m - 1e-6:
                violations.append(
                    {
                        "a": first.building_id,
                        "b": second.building_id,
                        "gap_m": gap,
                    }
                )
    return {
        "pairs": pairs,
        "violations": violations,
        "min_gap_m": min((item["gap_m"] for item in pairs), default=None),
        "required_gap_m": basis.north_south_spacing_m,
        "ok": not violations,
    }

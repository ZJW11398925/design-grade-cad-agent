from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.affinity import rotate, translate
from shapely.geometry import LineString, Point, Polygon, box
from shapely.ops import unary_union
from shapely.prepared import prep

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


#: Deterministic scan step used when deriving where a standardized footprint
#: can stand inside the buildable area of a row.  The scan is conservative: a
#: feasible sliver narrower than this step is not claimed as usable.
_FULL_SITE_SCAN_STEP_M = 0.5
#: Extra margin added to the 3 m building-road clearance buffer so the measured
#: clearance cannot fall below 3 m through buffer arc discretisation (the
#: placement is deliberately stricter than the declared requirement).
_FULL_SITE_CLEARANCE_MARGIN_M = 0.02
#: Bisection iterations used to refine a scanned feasible interval edge.
_FULL_SITE_REFINE_ITERATIONS = 24
#: Row assignments only consider rows within this many lattice steps of the
#: source row before widening the search window.
_FULL_SITE_NEAR_ROWS = 4


def _polygon_parts(geometry) -> list[Polygon]:
    """Polygonal parts of a shapely geometry, largest area first."""
    if geometry.is_empty:
        return []
    candidates = (
        list(geometry.geoms)
        if geometry.geom_type in {"MultiPolygon", "GeometryCollection"}
        else [geometry]
    )
    parts = [
        item
        for item in candidates
        if item.geom_type == "Polygon" and item.area > 0.0
    ]
    return sorted(parts, key=lambda item: -item.area)


def _prepared_rect_ok(prepared, x: float, y: float, width: float, depth: float) -> bool:
    return bool(prepared.contains(box(x, y, x + width, y + depth)))


def _feasible_start_ranges(
    prepared,
    y: float,
    depth: float,
    width: float,
    x_bounds: tuple[float, float],
    step: float = _FULL_SITE_SCAN_STEP_M,
) -> list[tuple[float, float]]:
    """Contiguous ranges of west-edge x where a w x depth rectangle fits.

    ``prepared`` is a prepared polygon (the row's buildable area).  The result
    is the set of start positions where ``box(x, y, x + width, y + depth)`` is
    fully contained, as inclusive ``(first, last)`` start pairs.
    """
    minx, maxx = x_bounds
    last_start = maxx - width
    if last_start < minx:
        return []
    ranges: list[tuple[float, float]] = []
    run_start: float | None = None
    run_end: float | None = None
    x = minx
    while x <= last_start + 1e-9:
        if _prepared_rect_ok(prepared, x, y, width, depth):
            if run_start is None:
                run_start = x
            run_end = x
        elif run_start is not None:
            ranges.append((run_start, run_end))
            run_start = None
            run_end = None
        x += step
    if run_start is not None:
        ranges.append((run_start, run_end))

    refined: list[tuple[float, float]] = []
    for first, last in ranges:
        left_low = max(minx, first - step)
        if left_low < first:
            low, high = left_low, first
            for _ in range(_FULL_SITE_REFINE_ITERATIONS):
                middle = (low + high) / 2.0
                if _prepared_rect_ok(prepared, middle, y, width, depth):
                    high = middle
                else:
                    low = middle
            first = high
        right_high = min(last_start, last + step)
        if right_high > last:
            low, high = last, right_high
            for _ in range(_FULL_SITE_REFINE_ITERATIONS):
                middle = (low + high) / 2.0
                if _prepared_rect_ok(prepared, middle, y, width, depth):
                    low = middle
                else:
                    high = middle
            last = low
        if first <= last:
            refined.append((first, last))
    return refined


def _trimmed_row_geometry(free_area, y: float, depth: float):
    """Free area clipped to the horizontal band a row's footprints occupy."""
    return free_area.intersection(box(-1e6, y, 1e6, y + depth))


def _free_strip_intervals(
    prepared,
    y: float,
    depth: float,
    x_bounds: tuple[float, float],
    step: float = 0.25,
    epsilon: float = 0.01,
) -> list[tuple[float, float]]:
    """X intervals where a full-depth vertical strip is inside the free area.

    A footprint of width ``w`` fits with its west edge at ``x`` exactly when
    ``[x, x + w]`` is inside one of these intervals, so all building widths
    share one segment structure (unlike a per-width start list).
    """
    minx, maxx = x_bounds

    def strip_ok(x: float) -> bool:
        return bool(
            prepared.contains(box(x, y, x + epsilon, y + depth))
        )

    los: list[float] = []
    his: list[float] = []
    run_start = None
    run_end = None
    x = minx
    while x + epsilon <= maxx + 1e-9:
        if strip_ok(x):
            if run_start is None:
                run_start = x
            run_end = x
        elif run_start is not None:
            los.append(run_start)
            his.append(run_end)
            run_start = None
            run_end = None
        x += step
    if run_start is not None:
        los.append(run_start)
        his.append(run_end)
    result: list[tuple[float, float]] = []
    for low_sample, high_sample in zip(los, his):
        low, high = max(minx, low_sample - step), low_sample
        for _ in range(_FULL_SITE_REFINE_ITERATIONS):
            middle = (low + high) / 2.0
            if strip_ok(middle):
                high = middle
            else:
                low = middle
        left = high
        low, high = high_sample, min(maxx, high_sample + step)
        for _ in range(_FULL_SITE_REFINE_ITERATIONS):
            middle = (low + high) / 2.0
            if strip_ok(middle):
                low = middle
            else:
                high = middle
        right = low + epsilon
        if right - left > 1e-9:
            result.append((left, right))
    return result


def _pack_row(
    ranges_by_id: dict[str, list[tuple[float, float] | None]],
    items: list[BuildingInput],
    widths: dict[str, float],
    source_centers: dict[str, float],
    side_gap: float,
) -> tuple[float, dict[str, float]] | None:
    """Place one row's buildings on the row's feasible start ranges.

    Buildings keep their source-x order.  Contiguous groups are assigned to
    feasible ranges with dynamic programming so the summed horizontal
    displacement is minimal for that order, then each group is positioned at
    the clamped median of its members' source centres.
    """
    if not items:
        return 0.0, {}
    ordered = sorted(
        items, key=lambda item: (source_centers[item.trace_id], item.trace_id)
    )
    count = len(ordered)
    range_lists = [
        ranges_by_id.get(item.trace_id, []) for item in ordered
    ]
    if any(not ranges for ranges in range_lists):
        return None
    range_count = max(len(ranges) for ranges in range_lists)

    group_cache: dict[tuple[int, int], tuple[float, float, list[float]] | None] = {}

    def group(t_start: int, t_end: int):
        """Best placement of ordered[t_start:t_end] in one feasible range."""
        key = (t_start, t_end)
        if key in group_cache:
            return group_cache[key]
        result = None
        for range_index in range(range_count):
            members = ordered[t_start:t_end]
            offsets: list[float] = []
            offset = 0.0
            low = -math.inf
            high = math.inf
            ok = True
            for member in members:
                ranges = range_lists[t_start + len(offsets)]
                if range_index >= len(ranges):
                    ok = False
                    break
                entry = ranges[range_index]
                if entry is None:
                    ok = False
                    break
                first, last = entry
                low = max(low, first - offset)
                high = min(high, last - offset)
                offsets.append(offset)
                offset += widths[member.trace_id] + side_gap
            if not ok or low > high + 1e-9:
                continue
            desired = [
                source_centers[member.trace_id]
                - widths[member.trace_id] / 2.0
                - offsets[index]
                for index, member in enumerate(members)
            ]
            desired.sort()
            middle = len(desired) // 2
            if len(desired) % 2:
                optimal = desired[middle]
            else:
                optimal = (desired[middle - 1] + desired[middle]) / 2.0
            start = min(max(optimal, low), high)
            cost = sum(
                abs(
                    start
                    + offsets[index]
                    + widths[member.trace_id] / 2.0
                    - source_centers[member.trace_id]
                )
                for index, member in enumerate(members)
            )
            if result is None or cost < result[0] - 1e-9:
                result = (cost, start, list(offsets))
        group_cache[key] = result
        return result

    inf = math.inf
    best = [[inf] * (range_count + 1) for _ in range(count + 1)]
    parent: list[list[tuple[int, int, float] | None]] = [
        [None] * (range_count + 1) for _ in range(count + 1)
    ]
    for range_index in range(range_count + 1):
        best[0][range_index] = 0.0
    for placed in range(1, count + 1):
        for range_index in range(1, range_count + 1):
            candidate = best[placed][range_index - 1]
            parent[placed][range_index] = parent[placed][range_index - 1]
            for t_start in range(placed):
                previous = best[t_start][range_index - 1]
                if previous == inf:
                    continue
                placed_group = group(t_start, placed)
                if placed_group is None:
                    continue
                total = previous + placed_group[0]
                if total < candidate - 1e-9:
                    candidate = total
                    parent[placed][range_index] = (
                        t_start,
                        range_index - 1,
                        placed_group[1],
                    )
            best[placed][range_index] = candidate
    if best[count][range_count] == inf:
        return None
    positions: dict[str, float] = {}
    placed = count
    range_index = range_count
    while placed > 0 and range_index > 0:
        entry = parent[placed][range_index]
        if entry is None:
            range_index -= 1
            continue
        t_start, previous_range, start = entry
        if t_start == placed:
            range_index -= 1
            continue
        offset = 0.0
        for index in range(t_start, placed):
            member = ordered[index]
            positions[member.trace_id] = start + offset
            offset += widths[member.trace_id] + side_gap
        placed = t_start
        range_index = previous_range
    if len(positions) != count:
        return None
    return best[count][range_count], positions


def _frozen_road_corridor(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    baseline: BuildingLayout,
) -> Polygon:
    """Corridor union of the 44 fixed design roads of the published network.

    ``roads`` imports this module, so the import is deferred to the call.  The
    baseline layout is the existing focus-only layout and the road layout is
    built exactly as the design pipeline builds it (default auto alignment),
    so the corridor matches the committed ``design-roads.geojson`` network.
    """
    from .roads import build_road_layout

    road_layout = build_road_layout(
        design_input,
        basis,
        intent,
        baseline,
    )
    return road_layout.corridor_union


def layout_full_site(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    standardized: dict[str, StandardBuilding],
    site_inner: Polygon,
    *,
    road_corridor: Polygon | None = None,
    max_displacement_m: float | None = None,
    preserve_focus: bool = True,
) -> BuildingLayout:
    """Place all 55 buildings in rows across the whole site.

    The focus group's existing row layout is preserved exactly (same ids,
    units and footprints) unless ``preserve_focus`` is false, in which case the
    same 7 buildings / 16 units are re-placed as ordinary row buildings near
    their source positions.  Every remaining building is snapped to one global
    31 m (11 m depth + 20 m north-south spacing) row lattice and positioned
    inside the road-free buildable area, so adjacent rows keep exactly 20 m.
    The 44 design roads are fixed: the frozen corridor plus the 3 m
    building-road clearance defines the buildable area, and buildings are
    never moved onto that corridor.  Nothing is dropped.

    ``max_displacement_m`` enables the group-anchored mode: each building the
    function is allowed to move must stay within that straight-line distance
    of its source centroid (focus buildings stay fixed when
    ``preserve_focus`` is true).  When the fixed roads/lattice make a capped
    placement impossible the function raises with the offending building ids
    rather than relaxing the cap or inventing a tolerance.
    """
    width_by_id = {
        item.trace_id: (
            30.0
            if item.is_facility
            else basis.building_width(int(item.unit_count or 0))
        )
        for item in design_input.buildings
    }
    input_by_id = {item.trace_id: item for item in design_input.buildings}
    depth = basis.staircase_depth_m
    side_gap = basis.side_spacing_m
    ns_spacing = basis.north_south_spacing_m
    pitch = depth + ns_spacing

    baseline = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    corridor = (
        road_corridor
        if road_corridor is not None
        else _frozen_road_corridor(design_input, basis, intent, baseline)
    )
    if max_displacement_m is not None:
        # A displacement cap never makes an already-valid uncapped layout
        # invalid; reuse it when it already satisfies the cap so the capped
        # search does not fail on a layout the engine can already produce.
        unrestricted = layout_full_site(
            design_input,
            basis,
            intent,
            standardized,
            site_inner,
            road_corridor=corridor,
            max_displacement_m=None,
            preserve_focus=preserve_focus,
        )
        if (
            max(
                item.displacement_m for item in unrestricted.buildings
            )
            <= max_displacement_m + 1e-6
        ):
            return unrestricted
    buildable = site_inner.difference(
        corridor.buffer(
            basis.building_road_clearance_m
            + _FULL_SITE_CLEARANCE_MARGIN_M
        )
    )
    minx, miny, maxx, maxy = site_inner.bounds

    # ---- fixed (already placed) footprints: the focus group --------------
    # ``preserve_focus`` keeps the existing focus row layout byte-identical.
    # In the group-anchored mode the same 7 focus buildings / 16 units are
    # re-placed as ordinary row buildings so they can honour the displacement
    # cap too; the focus group id/units are still preserved.
    focus_placed: dict[str, StandardBuilding] = {}
    if preserve_focus:
        focus_placed = {
            item.building_id: item for item in baseline.focus_buildings
        }
    # Focus buildings the existing focus layout could not place (it reports
    # them as dropped) are ordinary row buildings of the full-site layout.
    focus_ids = set(focus_placed)
    focus_building_ids = [
        item.building_id for item in baseline.focus_buildings
    ]
    focus_subgroup_by_id = {
        item.building_id: item.subgroup_id
        for item in baseline.focus_buildings
    }
    focus_union = (
        unary_union([item.footprint for item in focus_placed.values()])
        if focus_placed
        else Polygon()
    )

    # ---- row lattice: anchored on the preserved focus rows ----------------
    if baseline.rows:
        y_base = min(float(row["y"]) for row in baseline.rows)
    else:
        y_base = miny
    k_min = math.ceil((miny - y_base) / pitch - 1e-9)
    k_max = math.floor((maxy - depth - y_base) / pitch + 1e-9)
    full_row_ys = {
        k: y_base + k * pitch for k in range(k_min, k_max + 1)
    }

    # Areas already claimed by the focus layout keep their side spacing; the
    # 20 m north-south gap is guaranteed by the shared lattice.
    free_area = (
        buildable.difference(focus_union.buffer(side_gap))
        if not focus_union.is_empty
        else buildable
    )

    # ---- contiguous usable-row block --------------------------------------
    # An empty lattice row between two occupied rows would leave two rows two
    # pitches apart (over-spacing) while the row ordinals still look adjacent.
    # Placement is therefore restricted to the largest contiguous run of rows
    # that can physically host a building, and the run must contain the focus
    # rows (whose geometry is preserved).
    min_building_width = min(
        30.0 if item.is_facility else width_by_id[item.trace_id]
        for item in design_input.buildings
    )

    def row_has_capacity(k: int) -> bool:
        prepared = prep(
            _trimmed_row_geometry(free_area, full_row_ys[k], depth)
        )
        intervals = _free_strip_intervals(
            prepared, full_row_ys[k], depth, (minx, maxx)
        )
        return any(
            last - first >= min_building_width - 1e-9
            for first, last in intervals
        )

    usable_rows = [k for k in sorted(full_row_ys) if row_has_capacity(k)]
    runs: list[list[int]] = []
    for k in usable_rows:
        if runs and k == runs[-1][-1] + 1:
            runs[-1].append(k)
        else:
            runs.append([k])
    focus_row_ks: list[int] = []
    for k in sorted(full_row_ys):
        for building in focus_placed.values():
            if (
                abs(
                    full_row_ys[k]
                    - (building.design_centroid[1] - depth / 2.0)
                )
                <= 1e-6
            ):
                focus_row_ks.append(k)
                break
    block = None
    for run in sorted(runs, key=lambda item: -len(item)):
        if not focus_row_ks or set(focus_row_ks).issubset(run):
            block = run
            break
    if block is None:
        block = max(runs, key=len) if runs else []
    row_ys = {
        k: full_row_ys[k] for k in block
    }
    if not row_ys:
        raise ValueError(
            "layout_full_site found no usable row band inside the "
            "fixed-road buildable area"
        )

    # ---- displacement cap (group-anchored mode) --------------------------
    def capped_window(item: BuildingInput, k: int):
        """``(dy, dx_available)`` when row k is inside the cap, else None."""
        if max_displacement_m is None:
            return 0.0, math.inf
        center_y = (
            row_ys[k] + 10.0 if item.is_facility else row_ys[k] + depth / 2.0
        )
        dy = center_y - item.centroid[1]
        if abs(dy) > max_displacement_m - 1e-9:
            return None
        dx = math.sqrt(
            max(0.0, max_displacement_m * max_displacement_m - dy * dy)
        )
        return dy, dx

    source_center = {
        item.trace_id: (item.centroid[0], item.centroid[1])
        for item in design_input.buildings
    }
    remaining = [
        item
        for item in design_input.buildings
        if item.trace_id not in focus_ids
    ]
    facility_items = [item for item in remaining if item.is_facility]
    if len(facility_items) > 1:
        raise ValueError("layout_full_site supports at most one facility")
    facility = facility_items[0] if facility_items else None
    residential = [item for item in remaining if not item.is_facility]

    facility_placement: tuple[BuildingInput, float, float] | None = None
    if facility is not None:
        facility_depth = 20.0
        facility_width = 30.0
        facility_free = free_area
        facility_prepared = prep(facility_free)
        desired_bottom = facility.centroid[1] - facility_depth / 2.0
        candidates = sorted(
            (
                (abs(y + facility_depth / 2.0 - facility.centroid[1]), k, y)
                for k, y in row_ys.items()
                if y + facility_depth <= maxy + 1e-9
                and (
                    max_displacement_m is None
                    or abs(y + facility_depth / 2.0 - facility.centroid[1])
                    <= max_displacement_m - 1e-9
                )
            ),
            key=lambda entry: (entry[0], entry[1]),
        )
        chosen = None
        for _, k, y in candidates:
            ranges = _feasible_start_ranges(
                facility_prepared,
                y,
                facility_depth,
                facility_width,
                (minx, maxx),
            )
            if not ranges:
                continue
            if max_displacement_m is not None:
                dy = y + facility_depth / 2.0 - facility.centroid[1]
                dx = math.sqrt(
                    max(
                        0.0,
                        max_displacement_m * max_displacement_m - dy * dy,
                    )
                )
                low = facility.centroid[0] - dx - facility_width / 2.0
                high = facility.centroid[0] + dx - facility_width / 2.0
                ranges = [
                    (max(first, low), min(last, high))
                    for first, last in ranges
                    if min(last, high) >= max(first, low) - 1e-9
                ]
                if not ranges:
                    continue
            desired_start = facility.centroid[0] - facility_width / 2.0
            best_start = None
            for first, last in ranges:
                start = min(max(desired_start, first), last)
                cost = abs(start + facility_width / 2.0 - facility.centroid[0])
                if best_start is None or cost < best_start[0] - 1e-9:
                    best_start = (cost, start)
            chosen = (y, best_start[1])
            break
        if chosen is None:
            raise ValueError(
                "facility cannot be placed in any 31 m row inside the "
                "fixed-road buildable area"
            )
        facility_y, facility_start = chosen
        facility_placement = (facility, facility_start, facility_y)
        # The facility is 20 m deep: it fills its row band plus the 20 m gap
        # towards the next row, so reserve its footprint (plus side spacing)
        # on the row itself and on the row above.
        free_area = free_area.difference(
            box(
                facility_start,
                facility_y,
                facility_start + facility_width,
                facility_y + facility_depth,
            ).buffer(side_gap)
        )
        remaining = [item for item in residential]

    ranges_cache: dict[tuple[int, float], list[tuple[float, float] | None]] = {}
    strip_cache: dict[int, list[tuple[float, float]]] = {}
    prepared_cache: dict[int, Any] = {}

    def row_prepared(k: int):
        if k not in prepared_cache:
            prepared_cache[k] = prep(
                _trimmed_row_geometry(free_area, row_ys[k], depth)
            )
        return prepared_cache[k]

    def row_strips(k: int) -> list[tuple[float, float]]:
        if k not in strip_cache:
            strip_cache[k] = _free_strip_intervals(
                row_prepared(k), row_ys[k], depth, (minx, maxx)
            )
        return strip_cache[k]

    def row_ranges(k: int, width: float) -> list[tuple[float, float] | None]:
        key = (k, width)
        if key not in ranges_cache:
            ranges: list[tuple[float, float] | None] = []
            for first, last in row_strips(k):
                if last - first >= width - 1e-9:
                    ranges.append((first, last - width))
                else:
                    ranges.append(None)
            ranges_cache[key] = ranges
        return ranges_cache[key]

    def windowed_ranges(
        k: int, item: BuildingInput
    ) -> list[tuple[float, float] | None]:
        """Row start ranges additionally clipped to the displacement cap."""
        ranges = list(row_ranges(k, width_by_id[item.trace_id]))
        if max_displacement_m is None:
            return ranges
        window = capped_window(item, k)
        if window is None:
            return []
        _, dx_available = window
        width = width_by_id[item.trace_id]
        low = item.centroid[0] - dx_available - width / 2.0
        high = item.centroid[0] + dx_available - width / 2.0
        clipped: list[tuple[float, float] | None] = []
        for entry in ranges:
            if entry is None:
                clipped.append(None)
                continue
            first, last = entry
            new_first = max(first, low)
            new_last = min(last, high)
            clipped.append(
                (new_first, new_last)
                if new_last >= new_first - 1e-9
                else None
            )
        return clipped

    pack_cache: dict[
        tuple[int, tuple[str, ...]], tuple[float, dict[str, float]] | None
    ] = {}

    def pack(k: int, items: list[BuildingInput]):
        if not items:
            return 0.0, {}
        key = (k, tuple(sorted(item.trace_id for item in items)))
        if key in pack_cache:
            return pack_cache[key]
        ranges_by_id = {
            item.trace_id: windowed_ranges(k, item) for item in items
        }
        result = _pack_row(
            ranges_by_id,
            items,
            width_by_id,
            {item.trace_id: item.centroid[0] for item in items},
            side_gap,
        )
        if result is not None and not row_contains_check(k, result):
            result = None
        pack_cache[key] = result
        return result

    def row_valid(packed: tuple[float, dict[str, float]]) -> bool:
        """Reject row layouts that leave the rows, overlap or break spacing."""
        starts = packed[1]
        if not starts:
            return True
        ordered = sorted(
            starts.items(), key=lambda entry: (entry[1], entry[0])
        )
        for index, (trace_id, start) in enumerate(ordered):
            width = width_by_id[trace_id]
            if index:
                previous_id, previous_start = ordered[index - 1]
                previous_end = previous_start + width_by_id[previous_id]
                if start - previous_end < side_gap - 1e-6:
                    return False
            if start < minx - 1e-6 or start + width > maxx + 1e-6:
                return False
        return True

    def row_contains_check(k: int, packed) -> bool:
        """Exact containment of every footprint in the row's free area."""
        prepared = row_prepared(k)
        for trace_id, start in packed[1].items():
            if not prepared.contains(
                box(
                    start,
                    row_ys[k],
                    start + width_by_id[trace_id],
                    row_ys[k] + depth,
                )
            ):
                return False
        return True

    all_items = {item.trace_id: item for item in design_input.buildings}

    def building_cost(trace_id: str, k: int, packed) -> float | None:
        if trace_id not in packed[1]:
            return None
        item = all_items[trace_id]
        horizontal = abs(
            packed[1][trace_id]
            + width_by_id[trace_id] / 2.0
            - item.centroid[0]
        )
        vertical = abs(row_ys[k] + depth / 2.0 - item.centroid[1])
        return horizontal + vertical

    greedy_diagnostics: dict[str, list[str]] = {"unplaced": []}

    def greedy(order) -> tuple[dict, dict] | None:
        row_items: dict[int, list[BuildingInput]] = {k: [] for k in row_ys}
        row_pack: dict[int, tuple[float, dict[str, float]]] = {
            k: (0.0, {}) for k in row_ys
        }

        def try_add(k: int, item: BuildingInput):
            packed = pack(k, row_items[k] + [item])
            if packed is None or not row_valid(packed):
                return None
            return packed

        unplaced: list[BuildingInput] = []
        for item in sorted(remaining, key=order):
            preference = round(
                (item.centroid[1] - depth / 2.0 - y_base) / pitch
            )
            allowed_rows = [
                k
                for k in row_ys
                if max_displacement_m is None
                or capped_window(item, k) is not None
            ]
            candidates = sorted(
                allowed_rows,
                key=lambda k: (
                    abs(k - preference),
                    abs(
                        row_ys[k]
                        + (10.0 if item.is_facility else depth / 2.0)
                        - item.centroid[1]
                    ),
                    k,
                ),
            )
            if not candidates:
                unplaced.append(item)
                continue
            window = [
                k
                for k in candidates
                if abs(k - preference) <= _FULL_SITE_NEAR_ROWS
            ]
            placed_at = None
            for k in window + [k for k in candidates if k not in window]:
                packed = try_add(k, item)
                if packed is None:
                    continue
                score = building_cost(item.trace_id, k, packed)
                if placed_at is None or score < placed_at[0] - 1e-9:
                    placed_at = (score, k, packed)
            if placed_at is None:
                unplaced.append(item)
            else:
                _, k, packed = placed_at
                row_items[k].append(item)
                row_pack[k] = packed
        attempts = 0
        while unplaced and attempts < 400:
            attempts += 1
            item = unplaced.pop(0)
            preference = round(
                (item.centroid[1] - depth / 2.0 - y_base) / pitch
            )
            allowed_rows = [
                k
                for k in row_ys
                if max_displacement_m is None
                or capped_window(item, k) is not None
            ]
            candidates = sorted(
                allowed_rows, key=lambda k: (abs(k - preference), k)
            )
            progress = False
            for k in candidates:
                packed = pack(k, row_items[k] + [item])
                if packed is not None and row_valid(packed):
                    row_items[k].append(item)
                    row_pack[k] = packed
                    progress = True
                    break
                residents = sorted(
                    row_items[k],
                    key=lambda resident: (
                        -width_by_id[resident.trace_id],
                        resident.trace_id,
                    ),
                )
                for resident in residents:
                    reduced = [
                        other
                        for other in row_items[k]
                        if other.trace_id != resident.trace_id
                    ]
                    reduced_packed = pack(k, reduced)
                    if reduced_packed is None or not row_valid(
                        reduced_packed
                    ):
                        continue
                    trial = pack(k, reduced + [item])
                    if trial is None or not row_valid(trial):
                        continue
                    row_items[k] = reduced + [item]
                    row_pack[k] = trial
                    unplaced.append(resident)
                    progress = True
                    break
                if progress:
                    break
            if not progress:
                greedy_diagnostics["unplaced"] = sorted(
                    item.trace_id for item in unplaced
                )
                return None
        if unplaced:
            greedy_diagnostics["unplaced"] = sorted(
                item.trace_id for item in unplaced
            )
            return None
        return row_items, row_pack

    def total_cost(row_items: dict, row_pack: dict) -> float:
        total = 0.0
        for k, items in row_items.items():
            for item in items:
                cost = building_cost(item.trace_id, k, row_pack[k])
                total += 0.0 if cost is None else cost
        return total

    def local_search(row_items: dict, row_pack: dict) -> None:
        row_of = {
            item.trace_id: k
            for k, items in row_items.items()
            for item in items
        }
        for _ in range(6):
            improved = False
            # single moves: any row, not just a neighbourhood window
            for trace_id in sorted(row_of):
                item = all_items[trace_id]
                current_k = row_of[trace_id]
                current = building_cost(
                    trace_id, current_k, row_pack[current_k]
                )
                without = [
                    other
                    for other in row_items[current_k]
                    if other.trace_id != trace_id
                ]
                without_packed = pack(current_k, without)
                if without_packed is None or not row_valid(without_packed):
                    continue
                best = None
                for k in row_ys:
                    if k == current_k:
                        continue
                    trial = pack(k, row_items[k] + [item])
                    if trial is None or not row_valid(trial):
                        continue
                    cost = building_cost(trace_id, k, trial)
                    if cost is None or cost >= current - 1e-6:
                        continue
                    if best is None or cost < best[0] - 1e-9:
                        best = (cost, k, trial)
                if best is None:
                    continue
                _, k, trial = best
                row_items[current_k] = without
                row_pack[current_k] = without_packed
                row_items[k] = row_items[k] + [item]
                row_pack[k] = trial
                row_of[trace_id] = k
                improved = True
            # pairwise swaps between nearby rows
            ids = sorted(row_of)
            for index, first_id in enumerate(ids):
                for second_id in ids[index + 1 :]:
                    first_k = row_of[first_id]
                    second_k = row_of[second_id]
                    if first_k == second_k or abs(first_k - second_k) > 8:
                        continue
                    first = all_items[first_id]
                    second = all_items[second_id]
                    moved_first = [
                        other
                        for other in row_items[first_k]
                        if other.trace_id not in {first_id, second_id}
                    ] + [second]
                    moved_second = [
                        other
                        for other in row_items[second_k]
                        if other.trace_id not in {first_id, second_id}
                    ] + [first]
                    packed_first = pack(first_k, moved_first)
                    packed_second = pack(second_k, moved_second)
                    if (
                        packed_first is None
                        or packed_second is None
                        or not row_valid(packed_first)
                        or not row_valid(packed_second)
                    ):
                        continue
                    old_first = building_cost(
                        first_id, first_k, row_pack[first_k]
                    )
                    old_second = building_cost(
                        second_id, second_k, row_pack[second_k]
                    )
                    if old_first is None or old_second is None:
                        continue
                    old = old_first + old_second
                    new_first = building_cost(
                        second_id, first_k, packed_first
                    )
                    new_second = building_cost(
                        first_id, second_k, packed_second
                    )
                    if new_first is None or new_second is None:
                        continue
                    new = new_first + new_second
                    if new >= old - 1e-6:
                        continue
                    row_items[first_k] = moved_first
                    row_items[second_k] = moved_second
                    row_pack[first_k] = packed_first
                    row_pack[second_k] = packed_second
                    row_of[first_id], row_of[second_id] = second_k, first_k
                    improved = True
            if not improved:
                break

    strategies = (
        lambda item: (
            -width_by_id[item.trace_id],
            item.centroid[1],
            item.trace_id,
        ),
        lambda item: (
            item.centroid[1],
            -width_by_id[item.trace_id],
            item.trace_id,
        ),
    )
    best_state = None
    for order in strategies:
        state = greedy(order)
        if state is None:
            continue
        row_items, row_pack = state
        local_search(row_items, row_pack)
        cost = total_cost(row_items, row_pack)
        maximum = max(
            (
                building_cost(item.trace_id, k, row_pack[k]) or 0.0
                for k, items in row_items.items()
                for item in items
            ),
            default=0.0,
        )
        key = (cost, maximum)
        if best_state is None or key < best_state[0]:
            best_state = (key, row_items, row_pack)
    if best_state is None:
        unplaceable = greedy_diagnostics["unplaced"]
        no_row = []
        if max_displacement_m is not None:
            for item in remaining:
                feasible_rows = [
                    k
                    for k in row_ys
                    if capped_window(item, k) is not None
                    and any(
                        entry is not None
                        for entry in windowed_ranges(k, item)
                    )
                ]
                if not feasible_rows:
                    no_row.append(item.trace_id)
        detail = ""
        if no_row:
            detail += (
                "; no row at all within max_displacement_m="
                f"{max_displacement_m} for: " + ", ".join(sorted(no_row))
            )
        if unplaceable:
            detail += "; greedy could not place: " + ", ".join(unplaceable)
        raise ValueError(
            "layout_full_site cannot place every building on the fixed-road "
            "31 m row lattice" + detail
        )
    _, row_items, row_pack = best_state

    # ---- ejection-chain refinement: repair high-displacement outliers -----
    def _state_copy(items_map: dict, packs: dict):
        return (
            {key: list(value) for key, value in items_map.items()},
            dict(packs),
        )

    def _state_total(items_map: dict, packs: dict) -> float:
        return total_cost(items_map, packs)

    def _best_free_row(trace_id: str, items_map: dict, packs: dict, skip):
        """Cheapest row accepting a building without evicting anyone."""
        item = all_items[trace_id]
        best = None
        candidates = sorted(
            row_ys,
            key=lambda k: abs(row_ys[k] + depth / 2.0 - item.centroid[1]),
        )
        for k in candidates:
            if k in skip:
                continue
            trial = pack(k, items_map[k] + [item])
            if trial is None or not row_valid(trial):
                continue
            cost = building_cost(trace_id, k, trial)
            if cost is None:
                continue
            if best is None or cost < best[0] - 1e-9:
                best = (cost, k, trial)
        return best

    def ejection_search(items_map: dict, packs: dict) -> None:
        for _ in range(8):
            row_of_local = {
                item.trace_id: k
                for k, its in items_map.items()
                for item in its
            }
            base = _state_total(items_map, packs)
            ranked = sorted(
                row_of_local,
                key=lambda trace_id: -(
                    building_cost(
                        trace_id,
                        row_of_local[trace_id],
                        packs[row_of_local[trace_id]],
                    )
                    or 0.0
                ),
            )
            applied = False
            for trace_id in ranked:
                current_k = row_of_local[trace_id]
                current_cost = (
                    building_cost(trace_id, current_k, packs[current_k])
                    or 0.0
                )
                if current_cost < 40.0:
                    break
                item = all_items[trace_id]
                target_rows = sorted(
                    (k for k in row_ys if k != current_k),
                    key=lambda k: abs(
                        row_ys[k] + depth / 2.0 - item.centroid[1]
                    ),
                )[:7]
                best = None
                for k in target_rows:
                    for resident in items_map[k]:
                        resident_id = resident.trace_id
                        new_map, new_packs = _state_copy(items_map, packs)
                        new_map[current_k] = [
                            other
                            for other in new_map[current_k]
                            if other.trace_id != trace_id
                        ]
                        new_map[k] = [
                            other
                            for other in new_map[k]
                            if other.trace_id != resident_id
                        ] + [item]
                        packed_k = pack(k, new_map[k])
                        if packed_k is None or not row_valid(packed_k):
                            continue
                        new_packs[k] = packed_k
                        packed_current = pack(
                            current_k, new_map[current_k]
                        )
                        if packed_current is None or not row_valid(
                            packed_current
                        ):
                            continue
                        new_packs[current_k] = packed_current
                        relocation = _best_free_row(
                            resident_id,
                            new_map,
                            new_packs,
                            skip={k, current_k},
                        )
                        if relocation is None:
                            continue
                        _, k2, packed_k2 = relocation
                        new_map[k2] = new_map[k2] + [resident]
                        new_packs[k2] = packed_k2
                        total = _state_total(new_map, new_packs)
                        if total < base - 1e-6 and (
                            best is None or total < best[0] - 1e-9
                        ):
                            best = (total, new_map, new_packs)
                if best is not None:
                    _, items_map, packs = best
                    applied = True
                    break
            if not applied:
                break

    ejection_search(row_items, row_pack)

    # ---- dense contiguous row block: no physically adjacent over-spacing ---
    # Every row between the southernmost and northernmost occupied row must be
    # occupied too, so consecutive row ordinals are always one pitch (31 m)
    # apart.  Edge rows that stayed empty are trimmed; an interior empty row
    # is filled by moving the cheapest building that fits it.
    facility_row_k = None
    if facility_placement is not None:
        facility_row_k = min(
            row_ys, key=lambda k: abs(row_ys[k] - facility_placement[2])
        )

    def row_occupied(k: int) -> bool:
        return bool(row_items.get(k)) or k == facility_row_k

    occupied_ks = sorted(k for k in row_ys if row_occupied(k))
    if not occupied_ks:
        raise ValueError("layout_full_site placed no building on any row")
    low_k, high_k = occupied_ks[0], occupied_ks[-1]
    trimmed_ks = [k for k in sorted(row_ys) if low_k <= k <= high_k]
    for k in trimmed_ks:
        if row_occupied(k):
            continue
        best_move = None
        for source_k in sorted(trimmed_ks, key=lambda value: abs(value - k)):
            if source_k == k:
                continue
            for item in list(row_items.get(source_k, [])):
                trial = pack(k, [item])
                if trial is None or not row_valid(trial):
                    continue
                without = [
                    other
                    for other in row_items[source_k]
                    if other.trace_id != item.trace_id
                ]
                without_packed = pack(source_k, without)
                if without_packed is None or not row_valid(without_packed):
                    continue
                if not without:
                    # an empty source row would just move the hole
                    continue
                old = building_cost(
                    item.trace_id, source_k, row_pack[source_k]
                )
                new = building_cost(item.trace_id, k, trial)
                if old is None or new is None:
                    continue
                if best_move is None or new - old < best_move[0] - 1e-9:
                    best_move = (
                        new - old,
                        source_k,
                        item,
                        trial,
                        without_packed,
                    )
        if best_move is None:
            raise ValueError(
                "layout_full_site cannot fill the empty row band "
                f"y={row_ys[k]:.2f} needed for contiguous 20 m row spacing"
            )
        _, source_k, item, trial, without_packed = best_move
        row_items[k] = [item]
        row_pack[k] = trial
        row_items[source_k] = [
            other
            for other in row_items[source_k]
            if other.trace_id != item.trace_id
        ]
        row_pack[source_k] = without_packed
    row_ys = {k: row_ys[k] for k in trimmed_ks}
    for stale in [k for k in row_items if k not in row_ys]:
        row_items.pop(stale, None)
        row_pack.pop(stale, None)

    # ---- materialise StandardBuilding objects ----------------------------
    row_order = {
        k: index + 1 for index, k in enumerate(sorted(row_ys))
    }
    pockets = [
        part for part in _polygon_parts(buildable) if part.area >= 1.0
    ]
    superblock_of: dict[int, int] = {}
    placed_buildings: dict[str, StandardBuilding] = {}

    def superblock_for(point: Point) -> int:
        for index, part in enumerate(pockets):
            if part.contains(point) or part.distance(point) <= 1e-6:
                return index
        raise ValueError(
            "placed footprint centroid is outside every buildable superblock"
        )

    if facility_placement is not None:
        item, start, y = facility_placement
        center = (start + 30.0 / 2.0, y + 20.0 / 2.0)
        building = _standard_building(
            item,
            basis,
            center=center,
            angle=0.0,
            row_index=row_order[
                min(row_ys, key=lambda k: abs(row_ys[k] - y))
            ],
            subgroup_id=None,
        )
        placed_buildings[item.trace_id] = building

    for k, items in row_items.items():
        starts = row_pack[k][1]
        for item in items:
            start = starts[item.trace_id]
            center = (start + width_by_id[item.trace_id] / 2.0, row_ys[k] + depth / 2.0)
            building = _standard_building(
                item,
                basis,
                center=center,
                angle=0.0,
                row_index=row_order[k],
                subgroup_id=None,
            )
            placed_buildings[item.trace_id] = building

    # Superblock (buildable pocket) id per placed building; the focus group
    # keeps its existing FOCUS-* subgroup ids.
    superblock_ids: dict[str, str] = {}
    for trace_id, building in placed_buildings.items():
        index = superblock_for(
            Point(building.footprint.centroid.x, building.footprint.centroid.y)
        )
        superblock_of[index] = superblock_of.get(index, 0) + 1
        superblock_ids[trace_id] = f"SB-{index + 1:02d}"
    for trace_id, building in focus_placed.items():
        index = superblock_for(
            Point(building.footprint.centroid.x, building.footprint.centroid.y)
        )
        superblock_ids[trace_id] = building.subgroup_id or f"SB-{index + 1:02d}"
    # The declared focus group keeps its FOCUS-* subgroup ids even when it is
    # re-placed row-wise in the group-anchored mode.
    for trace_id in focus_building_ids:
        if trace_id in superblock_ids and trace_id in focus_subgroup_by_id:
            superblock_ids[trace_id] = focus_subgroup_by_id[trace_id]

    reindexed: dict[str, StandardBuilding] = {}
    for trace_id, building in placed_buildings.items():
        reindexed[trace_id] = _standard_building(
            all_items[trace_id],
            basis,
            center=building.design_centroid,
            angle=0.0,
            row_index=building.row_index,
            subgroup_id=superblock_ids[trace_id],
        )
    for trace_id, building in focus_placed.items():
        reindexed[trace_id] = _standard_building(
            all_items[trace_id],
            basis,
            center=building.design_centroid,
            angle=0.0,
            row_index=row_order[
                min(row_ys, key=lambda k: abs(row_ys[k] - building.design_centroid[1] - depth / 2.0))
            ],
            subgroup_id=superblock_ids[trace_id],
        )

    # ---- rows + green strips, one record per (row, superblock) segment -----
    segments: dict[tuple[int, str], list[str]] = {}
    for trace_id, building in reindexed.items():
        key = (int(building.row_index), str(building.subgroup_id))
        segments.setdefault(key, []).append(trace_id)
    row_records: list[dict[str, Any]] = []
    green_strips: list[Polygon] = []
    for (row_index, subgroup_id), building_ids in sorted(
        segments.items(), key=lambda entry: (entry[0][0], entry[0][1])
    ):
        ordered_ids = sorted(
            building_ids,
            key=lambda trace_id: (
                reindexed[trace_id].footprint.bounds[0],
                trace_id,
            ),
        )
        y = min(reindexed[trace_id].footprint.bounds[1] for trace_id in ordered_ids)
        row_records.append(
            {
                "row": row_index,
                "subgroup_id": subgroup_id,
                "y": y,
                "building_ids": ordered_ids,
                "north_south_gap_m": ns_spacing,
            }
        )
        strip = box(
            min(
                reindexed[trace_id].footprint.bounds[0]
                for trace_id in ordered_ids
            ),
            y + depth + ns_spacing / 2.0 - 4.0,
            max(
                reindexed[trace_id].footprint.bounds[2]
                for trace_id in ordered_ids
            ),
            y + depth + ns_spacing / 2.0 + 4.0,
        ).intersection(site_inner)
        if not strip.is_empty and strip.area >= 1.0:
            green_strips.append(strip)

    all_buildings = tuple(
        reindexed[item.trace_id] for item in design_input.buildings
    )
    # Only the buildings the existing focus layout actually placed are the
    # preserved focus group; dropped focus buildings are ordinary row
    # buildings now, because the full-site layout drops nothing.
    focus_buildings = tuple(
        reindexed[item.building_id]
        for item in baseline.focus_buildings
        if item.building_id in reindexed
    )
    if max_displacement_m is not None:
        exempt = set(focus_placed)
        cap_violations = [
            (item.building_id, round(item.displacement_m, 6))
            for item in reindexed.values()
            if item.building_id not in exempt
            and item.displacement_m > max_displacement_m + 1e-6
        ]
        if cap_violations:
            raise ValueError(
                "layout_full_site could not keep placement inside "
                f"max_displacement_m={max_displacement_m}: "
                + ", ".join(
                    f"{trace_id} ({value} m)"
                    for trace_id, value in sorted(cap_violations)
                )
            )
    return BuildingLayout(
        buildings=all_buildings,
        focus_buildings=focus_buildings,
        rows=tuple(row_records),
        green_strips=tuple(green_strips),
        dropped_focus_building_ids=(),
    )


def full_site_layout_report(
    layout: BuildingLayout,
    basis: DesignBasis,
    site_inner: Polygon,
    road_corridor: Polygon,
) -> dict[str, Any]:
    """Measured metrics for a full-site layout (evidence, not a pass claim)."""
    buildings = list(layout.buildings)
    ids = [item.building_id for item in buildings]
    unit_total = sum(item.unit_count for item in buildings)
    households = sum(item.households for item in buildings)
    focus_ids = {item.building_id for item in layout.focus_buildings}
    focus_units = sum(item.unit_count for item in layout.focus_buildings)
    tolerant = site_inner.buffer(0.01)
    boundary_violations = [
        item.building_id
        for item in buildings
        if not tolerant.contains(item.footprint)
    ]
    clearance_buffer = road_corridor.buffer(basis.building_road_clearance_m)
    road_clearances = [
        (item.building_id, item.footprint.distance(road_corridor))
        for item in buildings
    ]
    road_violations = [
        item.building_id
        for item in buildings
        if item.footprint.intersection(clearance_buffer).area > 0.01
    ]
    overlap_pairs = []
    for index, first in enumerate(buildings):
        for second in buildings[index + 1 :]:
            area = first.footprint.intersection(second.footprint).area
            if area > 0.01:
                overlap_pairs.append(
                    [first.building_id, second.building_id, round(area, 3)]
                )
    spacing_violations = []
    by_row: dict[int, list[StandardBuilding]] = {}
    for item in buildings:
        by_row.setdefault(int(item.row_index or 0), []).append(item)
    for row_index, row_buildings in by_row.items():
        ordered = sorted(
            row_buildings, key=lambda item: item.footprint.bounds[0]
        )
        for index, first in enumerate(ordered):
            for second in ordered[index + 1 :]:
                first_bounds = first.footprint.bounds
                second_bounds = second.footprint.bounds
                if (
                    min(first_bounds[3], second_bounds[3])
                    - max(first_bounds[1], second_bounds[1])
                    <= 0.0
                ):
                    continue
                side_gap = second_bounds[0] - first_bounds[2]
                if side_gap < basis.side_spacing_m - 1e-6:
                    spacing_violations.append(
                        {
                            "row": row_index,
                            "a": first.building_id,
                            "b": second.building_id,
                            "gap_m": round(side_gap, 3),
                        }
                    )
    ns_pairs = []
    ns_violations = []
    adjacent_pairs = []
    under_spacing = []
    over_spacing = []
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            second_bounds = second.footprint.bounds
            x_overlap = min(first_bounds[2], second_bounds[2]) - max(
                first_bounds[0], second_bounds[0]
            )
            if x_overlap <= 0.0:
                continue
            gap = max(
                second_bounds[1] - first_bounds[3],
                first_bounds[1] - second_bounds[3],
            )
            ns_pairs.append((first.building_id, second.building_id, gap))
            if gap < basis.north_south_spacing_m - 0.01:
                ns_violations.append(
                    {
                        "a": first.building_id,
                        "b": second.building_id,
                        "gap_m": round(gap, 3),
                    }
                )
            row_delta = abs(
                int(first.row_index or 0) - int(second.row_index or 0)
            )
            if row_delta == 1:
                entry = {
                    "a": first.building_id,
                    "b": second.building_id,
                    "rows": sorted(
                        [int(first.row_index or 0), int(second.row_index or 0)]
                    ),
                    "gap_m": round(gap, 3),
                }
                adjacent_pairs.append(entry)
                if gap < basis.north_south_spacing_m - 0.01:
                    under_spacing.append(entry)
                elif gap > basis.north_south_spacing_m + 0.01:
                    over_spacing.append(entry)
    displacements = [
        {
            "building_id": item.building_id,
            "row": item.row_index,
            "subgroup_id": item.subgroup_id,
            "displacement_m": item.displacement_m,
            "dx_m": item.design_centroid[0] - item.source_centroid[0],
            "dy_m": item.design_centroid[1] - item.source_centroid[1],
        }
        for item in buildings
    ]
    non_focus = [
        item for item in buildings if item.building_id not in focus_ids
    ]
    return {
        "building_count": len(buildings),
        "unique_building_ids": len(set(ids)),
        "unit_count_total": unit_total,
        "households_total": households,
        "facility_count": sum(1 for item in buildings if item.is_facility),
        "row_count": len({item.row_index for item in buildings}),
        "superblock_count": len({item.subgroup_id for item in buildings}),
        "row_records": len(layout.rows),
        "focus_building_count": len(layout.focus_buildings),
        "focus_unit_count": focus_units,
        "focus_building_ids": sorted(focus_ids),
        "dropped_focus_building_ids": list(
            layout.dropped_focus_building_ids
        ),
        "dropped_building_ids": [],
        "boundary_violations": sorted(boundary_violations),
        "road_clearance_min_m": (
            min(value for _, value in road_clearances)
            if road_clearances
            else None
        ),
        "road_clearance_required_m": basis.building_road_clearance_m,
        "road_clearance_violations": sorted(road_violations),
        "overlap_pairs": overlap_pairs,
        "side_spacing_violations": spacing_violations,
        "north_south_pair_count": len(ns_pairs),
        "north_south_min_gap_m": (
            min(gap for _, _, gap in ns_pairs) if ns_pairs else None
        ),
        "north_south_required_m": basis.north_south_spacing_m,
        "north_south_violations": ns_violations,
        "north_south_adjacent_pair_count": len(adjacent_pairs),
        "north_south_adjacent_min_gap_m": (
            min(item["gap_m"] for item in adjacent_pairs)
            if adjacent_pairs
            else None
        ),
        "north_south_under_spacing_violations": under_spacing,
        "north_south_over_spacing_violations": over_spacing,
        "row_index_range": [
            min(int(item.row_index or 0) for item in buildings),
            max(int(item.row_index or 0) for item in buildings),
        ],
        "row_index_contiguous": (
            sorted({int(item.row_index or 0) for item in buildings})
            == list(
                range(
                    min(int(item.row_index or 0) for item in buildings),
                    max(int(item.row_index or 0) for item in buildings) + 1,
                )
            )
        ),
        "displacement_sum_m": sum(item.displacement_m for item in buildings),
        "displacement_mean_m": (
            sum(item.displacement_m for item in buildings) / len(buildings)
            if buildings
            else 0.0
        ),
        "displacement_max_m": max(
            (item.displacement_m for item in buildings), default=0.0
        ),
        "displacement_min_m": min(
            (item.displacement_m for item in buildings), default=0.0
        ),
        "displacement_sum_non_focus_m": sum(
            item.displacement_m for item in non_focus
        ),
        "displacement_max_non_focus_m": max(
            (item.displacement_m for item in non_focus), default=0.0
        ),
        "displacement_max_focus_m": max(
            (item.displacement_m for item in layout.focus_buildings),
            default=0.0,
        ),
        "displacements": displacements,
    }


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

# ---------------------------------------------------------------------------
# M4d-2 candidate B: group-preserving full-site layout
# ---------------------------------------------------------------------------

#: Phase grid (metres) used to search the group-local 31 m row lattice origin.
#: Groups may use different phases, so no global row grid is imposed.
_GROUP_ROW_PHASE_STEP_M = 1.0


def _subtract_start_intervals(
    ranges: list[tuple[float, float]],
    forbidden: list[tuple[float, float]],
) -> list[tuple[float, float]]:
    """Remove forbidden start intervals from a list of allowed start ranges."""
    pieces = list(ranges)
    for block_low, block_high in forbidden:
        if block_high <= block_low or not pieces:
            continue
        remaining: list[tuple[float, float]] = []
        for low, high in pieces:
            if block_high <= low or block_low >= high:
                remaining.append((low, high))
                continue
            if low < block_low:
                remaining.append((low, block_low))
            if block_high < high:
                remaining.append((block_high, high))
        pieces = remaining
    return pieces


def layout_group_preserving(
    design_input: DesignInput,
    basis: DesignBasis,
    intent: DesignIntent,
    standardized: dict[str, StandardBuilding],
    site_inner: Polygon,
    *,
    road_corridor: Polygon | None = None,
    group_order: tuple[str, ...] | None = None,
) -> BuildingLayout:
    """Candidate B: keep the 17 intent groups together while regularising rows.

    Each ``intent.groups`` group is laid out on its own local 31 m
    (11 m depth + 20 m north-south spacing) row lattice: the phase of that
    lattice is chosen per group to minimise its members' displacement, so no
    global row grid is imposed and groups may sit at different row positions.
    Within a row buildings keep the 13 m side spacing; row bands are 20 m apart.
    Footprints stay inside the boundary setback and 3 m clear of the fixed 44
    road corridors; every building avoids overlap, side-spacing and <20 m
    x-overlapping row conflicts against buildings already placed (focus group
    and earlier groups).  The focus G-01 layout (7 buildings / 16 units) is
    preserved byte-identically.  Nothing is dropped.
    """
    width_by_id = {
        item.trace_id: (
            30.0
            if item.is_facility
            else basis.building_width(int(item.unit_count or 0))
        )
        for item in design_input.buildings
    }
    input_by_id = {item.trace_id: item for item in design_input.buildings}
    depth = basis.staircase_depth_m
    side_gap = basis.side_spacing_m
    ns_spacing = basis.north_south_spacing_m
    pitch = depth + ns_spacing
    minx, miny, maxx, maxy = site_inner.bounds

    baseline = layout_focus_region(
        design_input,
        intent,
        basis,
        standardized,
        site_inner,
        find_focus_design_rect(design_input, intent, basis),
    )
    corridor = (
        road_corridor
        if road_corridor is not None
        else _frozen_road_corridor(design_input, basis, intent, baseline)
    )
    buildable = site_inner.difference(
        corridor.buffer(
            basis.building_road_clearance_m
            + _FULL_SITE_CLEARANCE_MARGIN_M
        )
    )
    focus_placed = {
        item.building_id: item for item in baseline.focus_buildings
    }
    focus_ids = set(focus_placed)
    focus_union = unary_union(
        [item.footprint for item in focus_placed.values()]
    )
    free_area = buildable.difference(focus_union.buffer(side_gap))

    group_by_id: dict[str, str] = {}
    group_order_list: list[str] = []
    group_members: dict[str, list[BuildingInput]] = {}
    for group in intent.groups:
        group_order_list.append(group.group_id)
        members = [
            input_by_id[trace_id]
            for trace_id in group.building_ids
            if trace_id in input_by_id
        ]
        group_members[group.group_id] = members
        for member in members:
            group_by_id[member.trace_id] = group.group_id

    placed: dict[str, StandardBuilding] = dict(focus_placed)
    strip_cache: dict[float, list[tuple[float, float]]] = {}
    base_range_cache: dict[tuple[float, float], list[tuple[float, float]]] = {}
    forbidden_cache: dict[
        tuple[float, float, float], list[tuple[float, float]]
    ] = {}
    allowed_cache: dict[
        tuple[float, float, float], list[tuple[float, float]]
    ] = {}

    def row_strips(y: float, row_depth: float = depth):
        key = (round(y, 3), round(row_depth, 3))
        if key not in strip_cache:
            prepared = prep(_trimmed_row_geometry(free_area, y, row_depth))
            strip_cache[key] = _free_strip_intervals(
                prepared,
                y,
                row_depth,
                (minx, maxx),
                step=1.0,
            )
        return strip_cache[key]

    def base_start_ranges(
        y: float, width: float, row_depth: float = depth
    ) -> list[tuple[float, float]]:
        key = (round(y, 3), round(width, 3), round(row_depth, 3))
        if key not in base_range_cache:
            ranges = []
            for first, last in row_strips(y, row_depth):
                if last - first >= width - 1e-9:
                    ranges.append((first, last - width))
            base_range_cache[key] = ranges
        return base_range_cache[key]

    def forbidden_start_intervals(
        y: float, width: float, row_depth: float = depth
    ) -> list[tuple[float, float]]:
        key = (round(y, 3), round(width, 3), round(row_depth, 3))
        if key in forbidden_cache:
            return forbidden_cache[key]
        forbidden: list[tuple[float, float]] = []
        row_bottom = y
        row_top = y + row_depth
        for other in placed.values():
            bounds = other.footprint.bounds
            if bounds[1] < row_top - 1e-9 and row_bottom < bounds[3] - 1e-9:
                # row bands overlap: need 13 m side spacing / no overlap
                forbidden.append(
                    (bounds[0] - side_gap - width, bounds[2] + side_gap)
                )
                continue
            vertical_gap = max(
                0.0, row_bottom - bounds[3], bounds[1] - row_top
            )
            if vertical_gap < ns_spacing - 1e-6:
                # different rows closer than 20 m: x ranges must not overlap
                forbidden.append((bounds[0] - width, bounds[2]))
        forbidden_cache[key] = forbidden
        return forbidden

    def allowed_start_ranges(
        y: float, width: float, row_depth: float = depth
    ) -> list[tuple[float, float]]:
        key = (round(y, 3), round(width, 3), round(row_depth, 3))
        if key not in allowed_cache:
            allowed_cache[key] = _subtract_start_intervals(
                base_start_ranges(y, width, row_depth),
                forbidden_start_intervals(y, width, row_depth),
            )
        return allowed_cache[key]

    def pack_row(y: float, items: list[BuildingInput], row_depth: float = depth):
        """Left-to-right greedy placement of one row; None when impossible."""
        ordered = sorted(
            items, key=lambda item: (item.centroid[0], item.trace_id)
        )
        cursor = -math.inf
        positions: dict[str, float] = {}
        for item in ordered:
            width = width_by_id[item.trace_id]
            desired = item.centroid[0] - width / 2.0
            best = None
            for low, high in allowed_start_ranges(y, width, row_depth):
                start = min(max(desired, low), high)
                if cursor != -math.inf and cursor > start:
                    start = cursor
                if start > high + 1e-9:
                    continue
                cost = abs(start - desired)
                if best is None or cost < best[0] - 1e-9:
                    best = (cost, start)
            if best is None:
                return None
            start = best[1]
            positions[item.trace_id] = start
            cursor = start + width + side_gap
        return positions

    phases = [
        index * _GROUP_ROW_PHASE_STEP_M
        for index in range(int(round(pitch / _GROUP_ROW_PHASE_STEP_M)))
    ]
    # the preserved focus rows define extra phases: a group that contains focus
    # members (G-01) must be able to share its row lattice so all its rows stay
    # whole pitch steps apart
    anchor_phases = sorted(
        {round(float(row["y"]) % pitch, 9) for row in baseline.rows}
    )
    # coarse-to-fine phase search keeps the layout fast and deterministic
    coarse_phases = sorted(
        {
            index * 4.0 * _GROUP_ROW_PHASE_STEP_M
            for index in range(
                int(round(pitch / (4.0 * _GROUP_ROW_PHASE_STEP_M)))
            )
        }
        | set(anchor_phases)
    )

    def refine_phases(phase: float) -> list[float]:
        candidates = {
            round((phase + delta) % pitch, 6)
            for delta in (-3.0, -2.0, -1.0, 1.0, 2.0, 3.0)
        }
        candidates |= {
            round((phase + delta) % pitch, 9)
            for delta in (-0.5, -0.25, 0.25, 0.5)
        }
        return sorted(
            value for value in candidates if value not in coarse_phases
        )

    def rows_for_phase(phase: float) -> list[float]:
        first_k = math.ceil((miny - phase) / pitch - 1e-9)
        last_k = math.floor((maxy - depth - phase) / pitch + 1e-9)
        return [phase + k * pitch for k in range(first_k, last_k + 1)]

    def try_group(items: list[BuildingInput], phase: float):
        rows = rows_for_phase(phase)
        rows_by_y: dict[float, list[BuildingInput]] = {y: [] for y in rows}
        for item in sorted(
            items,
            key=lambda value: (
                value.centroid[1],
                -width_by_id[value.trace_id],
                value.trace_id,
            ),
        ):
            center_y = item.centroid[1]
            ranked = sorted(
                rows,
                key=lambda y: (abs(y + depth / 2.0 - center_y), y),
            )
            placed_row = None
            for y in ranked:
                trial = rows_by_y[y] + [item]
                if pack_row(y, trial) is not None:
                    rows_by_y[y] = trial
                    placed_row = y
                    break
            if placed_row is None:
                return None
        total = 0.0
        centres: dict[str, tuple[float, float]] = {}
        row_y_by_id: dict[str, float] = {}
        for y, row_items in rows_by_y.items():
            if not row_items:
                continue
            positions = pack_row(y, row_items)
            if positions is None:
                return None
            for item in row_items:
                width = width_by_id[item.trace_id]
                center_x = positions[item.trace_id] + width / 2.0
                centre_y = y + depth / 2.0
                centres[item.trace_id] = (center_x, centre_y)
                row_y_by_id[item.trace_id] = y
                total += math.hypot(
                    center_x - item.centroid[0],
                    centre_y - item.centroid[1],
                )
        return total, centres, row_y_by_id

    def commit(
        item: BuildingInput,
        center: tuple[float, float],
        row_y: float,
        group_id: str,
    ) -> None:
        building = _standard_building(
            item,
            basis,
            center=center,
            angle=0.0,
            row_index=0,
            subgroup_id=group_id,
        )
        placed[item.trace_id] = building

    # ---- facility placement is independent of group order -----------------
    facility = next(
        (item for item in design_input.buildings if item.is_facility),
        None,
    )
    facility_group = group_by_id.get(facility.trace_id) if facility else None
    facility_placement = None
    if facility is not None:
        facility_width = 30.0
        facility_depth = 20.0

        def facility_option(y: float):
            ranges = allowed_start_ranges(
                y, facility_width, facility_depth
            )
            if not ranges:
                return None
            desired = facility.centroid[0] - facility_width / 2.0
            best = None
            for low, high in ranges:
                start = min(max(desired, low), high)
                center = (
                    start + facility_width / 2.0,
                    y + facility_depth / 2.0,
                )
                cost = math.hypot(
                    center[0] - facility.centroid[0],
                    center[1] - facility.centroid[1],
                )
                if best is None or cost < best[0] - 1e-9:
                    best = (cost, center, y)
            return best

        best_facility = None
        for offset in range(0, int(maxy - miny - facility_depth) + 1, 2):
            option = facility_option(miny + offset)
            if option is not None and (
                best_facility is None or option[0] < best_facility[0] - 1e-9
            ):
                best_facility = option
        if best_facility is not None:
            base_y = best_facility[2]
            for delta in range(-8, 9):
                y = base_y + delta * 0.25
                if y < miny or y + facility_depth > maxy + 1e-9:
                    continue
                option = facility_option(y)
                if option is not None and (
                    option[0] < best_facility[0] - 1e-9
                ):
                    best_facility = option
        if best_facility is None:
            raise ValueError(
                "layout_group_preserving cannot place the facility inside "
                "the fixed-road buildable area"
            )
        facility_placement = (best_facility[1], best_facility[2])

    # ---- group order ------------------------------------------------------
    # Default is south-to-north by source group centroid: on the reference
    # case it gave the best measured group cohesion (max group centroid
    # displacement 140.1 m, mean 32.6 m; that maximum is dominated by the
    # groups whose source pocket is occupied by the preserved focus block).
    group_ids = list(group_order_list)

    def group_centroid_y(group_id: str) -> float:
        members = group_members[group_id]
        if not members:
            return 0.0
        return sum(member.centroid[1] for member in members) / len(members)

    if group_order is not None:
        orders = [tuple(group_order)]
    else:
        # groups that own preserved focus buildings go first so their movable
        # members can share the focus row lattice; the rest go south-to-north
        focus_groups = sorted(
            group_id
            for group_id in group_ids
            if any(
                member.trace_id in focus_ids
                for member in group_members[group_id]
            )
        )
        rest = [group_id for group_id in group_ids if group_id not in focus_groups]
        orders = [
            tuple(focus_groups)
            + tuple(
                sorted(
                    rest,
                    key=lambda value: (
                        round(group_centroid_y(value), 6),
                        value,
                    ),
                )
            )
        ]

    def run_order(order: tuple[str, ...]):
        placed.clear()
        placed.update(focus_placed)
        forbidden_cache.clear()
        allowed_cache.clear()
        if facility is not None and facility_placement is not None:
            commit(
                facility,
                facility_placement[0],
                facility_placement[1],
                facility_group or "G-FACILITY",
            )
        for group_id in order:
            items = [
                item
                for item in group_members[group_id]
                if item.trace_id not in placed
            ]
            if not items:
                continue
            forbidden_cache.clear()
            allowed_cache.clear()

            def evaluate_phases(candidates):
                best = None
                for phase in candidates:
                    option = try_group(items, phase)
                    if option is None:
                        continue
                    key = (round(option[0], 9), phase)
                    if best is None or key < best[0]:
                        best = (key, phase, option)
                return best

            best_option = evaluate_phases(coarse_phases)
            if best_option is not None:
                refined = evaluate_phases(refine_phases(best_option[1]))
                if refined is not None and refined[0] < best_option[0]:
                    best_option = refined
            else:
                best_option = evaluate_phases(phases)
            if best_option is not None:
                _, phase, option = best_option
                _, centres, row_y_by_id = option
                item_by_id = {item.trace_id: item for item in items}
                # A group may use any local row phase, but two of its rows must
                # not end up two pitches apart with overlapping x extents: that
                # is an over-spacing (51 m) gap at the global row check.  Merge
                # such group rows into one row when the combined row still
                # packs inside the road-free strip.
                merged = True
                while merged:
                    merged = False
                    trace_ids = list(row_y_by_id)
                    for index, first_id in enumerate(trace_ids):
                        for second_id in trace_ids[index + 1 :]:
                            first_y = row_y_by_id[first_id]
                            second_y = row_y_by_id[second_id]
                            if abs(second_y - first_y) <= pitch + 1e-6:
                                continue
                            first_width = width_by_id[first_id]
                            second_width = width_by_id[second_id]
                            first_left = centres[first_id][0] - first_width / 2.0
                            first_right = centres[first_id][0] + first_width / 2.0
                            second_left = (
                                centres[second_id][0] - second_width / 2.0
                            )
                            second_right = (
                                centres[second_id][0] + second_width / 2.0
                            )
                            if (
                                min(first_right, second_right)
                                - max(first_left, second_left)
                                <= 0.0
                            ):
                                continue
                            # only a pair with no occupied row between them
                            # becomes consecutive in the global row index
                            low_y = min(first_y, second_y)
                            high_y = max(first_y, second_y)
                            between = any(
                                low_y + 1e-6
                                < round(other.footprint.bounds[1], 6)
                                < high_y - 1e-6
                                for other in placed.values()
                            ) or any(
                                low_y + 1e-6 < value < high_y - 1e-6
                                for value in row_y_by_id.values()
                            )
                            if between:
                                continue
                            for mover, target in (
                                (second_id, first_id),
                                (first_id, second_id),
                            ):
                                target_y = row_y_by_id[target]
                                row_ids = [
                                    trace_id
                                    for trace_id in row_y_by_id
                                    if abs(
                                        row_y_by_id[trace_id] - target_y
                                    )
                                    <= 1e-6
                                ]
                                trial_ids = row_ids + [mover]
                                positions = pack_row(
                                    target_y,
                                    [
                                        item_by_id[trace_id]
                                        for trace_id in trial_ids
                                    ],
                                )
                                if positions is None:
                                    continue
                                row_y_by_id[mover] = target_y
                                for trace_id in trial_ids:
                                    width = width_by_id[trace_id]
                                    centres[trace_id] = (
                                        positions[trace_id] + width / 2.0,
                                        target_y + depth / 2.0,
                                    )
                                merged = True
                                break
                            if merged:
                                break
                        if merged:
                            break
                for item in items:
                    commit(
                        item,
                        centres[item.trace_id],
                        row_y_by_id[item.trace_id],
                        group_id,
                    )
                continue
            # fallback: place each building individually at its nearest
            # feasible row phase (group rows are still used, not shared)
            for item in items:
                def scan_rows(phase: float):
                    spot = None
                    for y in rows_for_phase(phase):
                        positions = pack_row(y, [item])
                        if positions is None:
                            continue
                        start = positions[item.trace_id]
                        center = (
                            start + width_by_id[item.trace_id] / 2.0,
                            y + depth / 2.0,
                        )
                        cost = math.hypot(
                            center[0] - item.centroid[0],
                            center[1] - item.centroid[1],
                        )
                        key = (round(cost, 9), round(y, 6))
                        if spot is None or key < spot[0]:
                            spot = (key, center, y)
                    return spot

                best_spot = None
                coarse_phase = None
                for phase in coarse_phases:
                    spot = scan_rows(phase)
                    if spot is not None and (
                        best_spot is None or spot[0] < best_spot[0]
                    ):
                        best_spot = spot
                        coarse_phase = phase
                if coarse_phase is not None:
                    for phase in refine_phases(coarse_phase):
                        spot = scan_rows(phase)
                        if spot is not None and spot[0] < best_spot[0]:
                            best_spot = spot
                if best_spot is None:
                    raise ValueError(
                        "layout_group_preserving cannot place building "
                        f"{item.trace_id} of group {group_id} anywhere "
                        "inside the fixed-road buildable area"
                    )
                _, center, row_y = best_spot
                commit(item, center, row_y, group_id)

        # ---- global row repair: no over-spaced consecutive rows -----------
        # Two occupied rows that end up next to each other in the global row
        # order must be exactly one 20 m pitch apart wherever their x extents
        # overlap (otherwise the row check reports a 51 m gap).  Relocate or
        # merge the offending building when the road-free strip allows it.
        def consecutive_over_spacing_pairs():
            rows: dict[float, list[StandardBuilding]] = {}
            for building in placed.values():
                rows.setdefault(
                    round(building.footprint.bounds[1], 6), []
                ).append(building)
            ordered_rows = sorted(rows)
            pairs = []
            for lower_y, upper_y in zip(ordered_rows, ordered_rows[1:]):
                if upper_y - lower_y <= pitch + 0.01:
                    continue
                for first in rows[lower_y]:
                    first_bounds = first.footprint.bounds
                    for second in rows[upper_y]:
                        second_bounds = second.footprint.bounds
                        x_overlap = min(
                            first_bounds[2], second_bounds[2]
                        ) - max(first_bounds[0], second_bounds[0])
                        if x_overlap <= 0.0:
                            continue
                        gap = max(
                            second_bounds[1] - first_bounds[3],
                            first_bounds[1] - second_bounds[3],
                        )
                        if gap > ns_spacing + 0.01:
                            pairs.append((lower_y, upper_y, first, second))
            return pairs

        for _ in range(120):
            pairs = consecutive_over_spacing_pairs()
            if not pairs:
                break
            applied = False
            for lower_y, upper_y, first, second in pairs:
                movers = [
                    candidate
                    for candidate in (second, first)
                    if candidate.building_id not in focus_ids
                    and not candidate.is_facility
                ]
                for mover in movers:
                    target_candidates = []
                    for target_y in (
                        lower_y + pitch,
                        upper_y - pitch,
                        lower_y,
                    ):
                        if target_y < miny - 1e-9:
                            continue
                        if target_y + depth > maxy + 1e-9:
                            continue
                        if abs(target_y - upper_y) <= 1e-6:
                            continue
                        if target_y not in target_candidates:
                            target_candidates.append(target_y)
                    for target_y in target_candidates:
                        row_ids = [
                            other.building_id
                            for other in placed.values()
                            if abs(
                                other.footprint.bounds[1] - target_y
                            )
                            <= 1e-6
                        ]
                        if mover.building_id in row_ids:
                            continue
                        before = len(pairs)
                        original = {
                            trace_id: placed[trace_id]
                            for trace_id in row_ids + [mover.building_id]
                            if trace_id in placed
                        }
                        for trace_id in original:
                            placed.pop(trace_id, None)
                        positions = pack_row(
                            target_y,
                            [
                                input_by_id[trace_id]
                                for trace_id in row_ids + [mover.building_id]
                            ],
                        )
                        if positions is None:
                            placed.update(original)
                            continue
                        for trace_id in row_ids + [mover.building_id]:
                            item = input_by_id[trace_id]
                            width = width_by_id[trace_id]
                            commit(
                                item,
                                (
                                    positions[trace_id] + width / 2.0,
                                    target_y + depth / 2.0,
                                ),
                                target_y,
                                group_by_id.get(trace_id, "G-00"),
                            )
                        after = len(consecutive_over_spacing_pairs())
                        if after < before:
                            applied = True
                            break
                        for trace_id in row_ids + [mover.building_id]:
                            placed.pop(trace_id, None)
                        placed.update(original)
                    if applied:
                        break
                if applied:
                    break
            if not applied:
                break
        group_centroid_displacements = []
        building_displacements = []
        for group_id, members in group_members.items():
            present = [
                placed[member.trace_id]
                for member in members
                if member.trace_id in placed
            ]
            if not present:
                continue
            source_cx = sum(
                item.source_centroid[0] for item in present
            ) / len(present)
            source_cy = sum(
                item.source_centroid[1] for item in present
            ) / len(present)
            design_cx = sum(
                item.design_centroid[0] for item in present
            ) / len(present)
            design_cy = sum(
                item.design_centroid[1] for item in present
            ) / len(present)
            group_centroid_displacements.append(
                math.hypot(design_cx - source_cx, design_cy - source_cy)
            )
            building_displacements.extend(
                item.displacement_m for item in present
            )
        key = (
            round(max(group_centroid_displacements, default=0.0), 6),
            round(max(building_displacements, default=0.0), 6),
            round(sum(building_displacements), 6),
        )
        return dict(placed), key

    best_result = None
    for order in orders:
        result, key = run_order(order)
        if best_result is None or key < best_result[0]:
            best_result = (key, result)
    placed = dict(best_result[1])

    # ---- rows, row_index and green strips --------------------------------
    row_ys = sorted(
        {
            round(building.footprint.bounds[1], 6)
            for building in placed.values()
        }
    )
    row_order = {y: index + 1 for index, y in enumerate(row_ys)}
    indexed: dict[str, StandardBuilding] = {}
    for trace_id, building in placed.items():
        subgroup = group_by_id.get(trace_id, "G-00")
        indexed[trace_id] = _standard_building(
            input_by_id[trace_id],
            basis,
            center=building.design_centroid,
            angle=0.0,
            row_index=row_order[round(building.footprint.bounds[1], 6)],
            subgroup_id=subgroup,
        )

    segments: dict[tuple[int, str], list[str]] = {}
    for trace_id, building in indexed.items():
        key = (int(building.row_index), str(building.subgroup_id))
        segments.setdefault(key, []).append(trace_id)
    row_records: list[dict[str, Any]] = []
    green_strips: list[Polygon] = []
    for (row_index, subgroup_id), building_ids in sorted(
        segments.items(), key=lambda entry: (entry[0][0], entry[0][1])
    ):
        ordered_ids = sorted(
            building_ids,
            key=lambda trace_id: (
                indexed[trace_id].footprint.bounds[0],
                trace_id,
            ),
        )
        row_y = min(
            indexed[trace_id].footprint.bounds[1]
            for trace_id in ordered_ids
        )
        row_bottom = row_y
        row_height = max(
            indexed[trace_id].footprint.bounds[3] - row_bottom
            for trace_id in ordered_ids
        )
        row_records.append(
            {
                "row": row_index,
                "subgroup_id": subgroup_id,
                "y": row_y,
                "building_ids": ordered_ids,
                "north_south_gap_m": ns_spacing,
            }
        )
        strip = box(
            min(
                indexed[trace_id].footprint.bounds[0]
                for trace_id in ordered_ids
            ),
            row_y + row_height + ns_spacing / 2.0 - 4.0,
            max(
                indexed[trace_id].footprint.bounds[2]
                for trace_id in ordered_ids
            ),
            row_y + row_height + ns_spacing / 2.0 + 4.0,
        ).intersection(site_inner)
        if not strip.is_empty and strip.area >= 1.0:
            green_strips.append(strip)

    all_buildings = tuple(
        indexed[item.trace_id] for item in design_input.buildings
    )
    focus_buildings = tuple(
        indexed[item.building_id]
        for item in baseline.focus_buildings
        if item.building_id in indexed
    )
    return BuildingLayout(
        buildings=all_buildings,
        focus_buildings=focus_buildings,
        rows=tuple(row_records),
        green_strips=tuple(green_strips),
        dropped_focus_building_ids=(),
    )

def group_preserving_layout_report(
    layout: BuildingLayout,
    basis: DesignBasis,
    design_input: DesignInput,
    intent: DesignIntent,
    site_inner: Polygon,
    road_corridor: Polygon,
) -> dict[str, Any]:
    """Measured candidate-B metrics: group cohesion, row rules and clearances."""
    buildings = list(layout.buildings)
    by_group: dict[str, list[StandardBuilding]] = {}
    for item in buildings:
        by_group.setdefault(str(item.subgroup_id), []).append(item)
    expected_ids: set[str] = set()
    for group in intent.groups:
        expected_ids.update(group.building_ids)

    # ---- conservation ----------------------------------------------------
    unit_total = sum(item.unit_count for item in buildings)
    households = sum(item.households for item in buildings)
    placed_ids = {item.building_id for item in buildings}

    # ---- per building / per group displacement ---------------------------
    displacements = [
        {
            "building_id": item.building_id,
            "group_id": str(item.subgroup_id),
            "row": item.row_index,
            "displacement_m": item.displacement_m,
            "dx_m": item.design_centroid[0] - item.source_centroid[0],
            "dy_m": item.design_centroid[1] - item.source_centroid[1],
        }
        for item in buildings
    ]
    groups_report = []
    for group in intent.groups:
        members = [
            item
            for item in by_group.get(group.group_id, [])
            if item.building_id in group.building_ids
        ]
        if not members:
            groups_report.append(
                {
                    "group_id": group.group_id,
                    "present": False,
                    "building_count": 0,
                    "max_building_displacement_m": None,
                    "centroid_displacement_m": None,
                }
            )
            continue
        source_cx = sum(item.source_centroid[0] for item in members) / len(
            members
        )
        source_cy = sum(item.source_centroid[1] for item in members) / len(
            members
        )
        design_cx = sum(item.design_centroid[0] for item in members) / len(
            members
        )
        design_cy = sum(item.design_centroid[1] for item in members) / len(
            members
        )
        source_bbox = list(group.bbox)
        design_bounds = unary_union(
            [item.footprint for item in members]
        ).bounds
        groups_report.append(
            {
                "group_id": group.group_id,
                "present": True,
                "building_count": len(members),
                "unit_count": sum(item.unit_count for item in members),
                "max_building_displacement_m": round(
                    max(item.displacement_m for item in members), 3
                ),
                "mean_building_displacement_m": round(
                    sum(item.displacement_m for item in members)
                    / len(members),
                    3,
                ),
                "centroid_displacement_m": round(
                    math.hypot(design_cx - source_cx, design_cy - source_cy),
                    3,
                ),
                "centroid_dx_m": round(design_cx - source_cx, 3),
                "centroid_dy_m": round(design_cy - source_cy, 3),
                "source_bbox": [round(value, 3) for value in source_bbox],
                "design_bbox": [round(value, 3) for value in design_bounds],
                "bbox_center_dx_m": round(
                    (design_bounds[0] + design_bounds[2]) / 2.0
                    - (source_bbox[0] + source_bbox[2]) / 2.0,
                    3,
                ),
                "bbox_center_dy_m": round(
                    (design_bounds[1] + design_bounds[3]) / 2.0
                    - (source_bbox[1] + source_bbox[3]) / 2.0,
                    3,
                ),
                "bbox_width_change_m": round(
                    (design_bounds[2] - design_bounds[0])
                    - (source_bbox[2] - source_bbox[0]),
                    3,
                ),
                "bbox_height_change_m": round(
                    (design_bounds[3] - design_bounds[1])
                    - (source_bbox[3] - source_bbox[1]),
                    3,
                ),
            }
        )

    # ---- boundary / overlap / side spacing / road clearance --------------
    tolerant = site_inner.buffer(0.01)
    boundary_violations = [
        item.building_id
        for item in buildings
        if not tolerant.contains(item.footprint)
    ]
    overlap_pairs = []
    for index, first in enumerate(buildings):
        for second in buildings[index + 1 :]:
            area = first.footprint.intersection(second.footprint).area
            if area > 0.01:
                overlap_pairs.append(
                    [first.building_id, second.building_id, round(area, 3)]
                )
    side_spacing_violations = []
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            second_bounds = second.footprint.bounds
            if (
                min(first_bounds[3], second_bounds[3])
                - max(first_bounds[1], second_bounds[1])
                <= 0.0
            ):
                continue
            gap = max(
                second_bounds[0] - first_bounds[2],
                first_bounds[0] - second_bounds[2],
            )
            if gap < basis.side_spacing_m - 1e-6:
                side_spacing_violations.append(
                    {
                        "a": first.building_id,
                        "b": second.building_id,
                        "gap_m": round(gap, 3),
                    }
                )
    clearance_buffer = road_corridor.buffer(
        basis.building_road_clearance_m
    )
    road_clearances = [
        (item.building_id, item.footprint.distance(road_corridor))
        for item in buildings
    ]
    road_clearance_violations = [
        item.building_id
        for item in buildings
        if item.footprint.intersection(clearance_buffer).area > 0.01
    ]

    # ---- 20 m north-south row spacing ------------------------------------
    within_group = []
    cross_group = []
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            second_bounds = second.footprint.bounds
            x_overlap = min(first_bounds[2], second_bounds[2]) - max(
                first_bounds[0], second_bounds[0]
            )
            if x_overlap <= 0.0:
                continue
            gap = max(
                second_bounds[1] - first_bounds[3],
                first_bounds[1] - second_bounds[3],
            )
            if gap >= basis.north_south_spacing_m - 0.01:
                continue
            record = {
                "a": first.building_id,
                "b": second.building_id,
                "a_group": str(first.subgroup_id),
                "b_group": str(second.subgroup_id),
                "gap_m": round(gap, 3),
            }
            if first.subgroup_id == second.subgroup_id:
                within_group.append(record)
            else:
                cross_group.append(record)

    # ---- consecutive row ordinals must be exactly 20 m apart -------------
    consecutive_ns = []
    for index, first in enumerate(buildings):
        first_bounds = first.footprint.bounds
        for second in buildings[index + 1 :]:
            if abs(
                int(first.row_index or 0) - int(second.row_index or 0)
            ) != 1:
                continue
            second_bounds = second.footprint.bounds
            x_overlap = min(first_bounds[2], second_bounds[2]) - max(
                first_bounds[0], second_bounds[0]
            )
            if x_overlap <= 0.0:
                continue
            gap = max(
                second_bounds[1] - first_bounds[3],
                first_bounds[1] - second_bounds[3],
            )
            consecutive_ns.append(
                {
                    "a": first.building_id,
                    "b": second.building_id,
                    "rows": [
                        min(
                            int(first.row_index or 0),
                            int(second.row_index or 0),
                        ),
                        max(
                            int(first.row_index or 0),
                            int(second.row_index or 0),
                        ),
                    ],
                    "gap_m": round(gap, 3),
                }
            )
    consecutive_under = [
        item
        for item in consecutive_ns
        if item["gap_m"] < basis.north_south_spacing_m - 0.01
    ]
    consecutive_over = [
        item
        for item in consecutive_ns
        if item["gap_m"] > basis.north_south_spacing_m + 0.01
    ]

    relocated_groups = sorted(
        item["group_id"]
        for item in groups_report
        if item["present"]
        and (
            (item["max_building_displacement_m"] or 0.0) > 45.0
            or (item["centroid_displacement_m"] or 0.0) > 25.0
        )
    )
    return {
        "building_count": len(buildings),
        "unique_building_ids": len(placed_ids),
        "unit_count_total": unit_total,
        "households_total": households,
        "facility_count": sum(1 for item in buildings if item.is_facility),
        "expected_building_count": len(expected_ids),
        "dropped_building_ids": sorted(expected_ids - placed_ids),
        "group_count": len(intent.groups),
        "present_group_count": sum(
            1 for item in groups_report if item["present"]
        ),
        "row_count": len({item.row_index for item in buildings}),
        "row_records": len(layout.rows),
        "focus_building_count": len(layout.focus_buildings),
        "focus_unit_count": sum(
            item.unit_count for item in layout.focus_buildings
        ),
        "focus_building_ids": sorted(
            item.building_id for item in layout.focus_buildings
        ),
        "boundary_violations": sorted(boundary_violations),
        "overlap_pairs": overlap_pairs,
        "side_spacing_violations": side_spacing_violations,
        "road_clearance_min_m": (
            min(value for _, value in road_clearances)
            if road_clearances
            else None
        ),
        "road_clearance_required_m": basis.building_road_clearance_m,
        "road_clearance_violations": sorted(road_clearance_violations),
        "within_group_ns_violations": within_group,
        "cross_group_ns_violations": cross_group,
        "consecutive_row_ns_pairs": len(consecutive_ns),
        "consecutive_row_ns_min_gap_m": (
            min(item["gap_m"] for item in consecutive_ns)
            if consecutive_ns
            else None
        ),
        "consecutive_row_ns_max_gap_m": (
            max(item["gap_m"] for item in consecutive_ns)
            if consecutive_ns
            else None
        ),
        "consecutive_row_under_spacing_violations": consecutive_under,
        "consecutive_row_over_spacing_violations": consecutive_over,
        "group_centroid_displacement_max_m": max(
            (
                item["centroid_displacement_m"]
                for item in groups_report
                if item["centroid_displacement_m"] is not None
            ),
            default=0.0,
        ),
        "group_centroid_displacement_mean_m": (
            sum(
                item["centroid_displacement_m"]
                for item in groups_report
                if item["centroid_displacement_m"] is not None
            )
            / max(
                1,
                sum(
                    1
                    for item in groups_report
                    if item["centroid_displacement_m"] is not None
                ),
            )
        ),
        "building_displacement_max_m": max(
            (item.displacement_m for item in buildings), default=0.0
        ),
        "building_displacement_sum_m": sum(
            item.displacement_m for item in buildings
        ),
        "groups_outside_source_proximity": relocated_groups,
        "groups": groups_report,
        "displacements": displacements,
    }

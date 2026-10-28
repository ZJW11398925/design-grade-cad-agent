from __future__ import annotations

import math
from typing import Any

from shapely.geometry import (
    GeometryCollection,
    LineString,
    MultiLineString,
    MultiPolygon,
    Point,
    Polygon,
    box,
)
from shapely.ops import unary_union

from dgcad_domain import geometry_to_geojson

from .basis import DesignBasis
from .buildings import BuildingLayout
from .green import GreenLayout
from .input import DesignInput
from .intent import DesignIntent
from .parking import ParkingLayout
from .roads import RoadLayout
from .scene import DesignElement


def _text(
    element_id: str,
    x: float,
    y: float,
    text: str,
    height: float,
    layer: str,
    *,
    rotation: float = 0.0,
    role: str | None = None,
) -> DesignElement:
    return DesignElement(
        element_id=element_id,
        object_class="annotation_text",
        layer_key=layer,
        representation_kind="text",
        geometry={"type": "Point", "coordinates": [round(x, 6), round(y, 6)]},
        text=text,
        text_height=height,
        rotation=rotation,
        annotation_role=role,
    )


def _polyline(
    element_id: str,
    geometry,
    layer: str,
    *,
    role: str | None = None,
) -> DesignElement:
    if geometry.geom_type == "LinearRing":
        geometry = LineString(geometry.coords)
    return DesignElement(
        element_id=element_id,
        object_class="annotation_polyline",
        layer_key=layer,
        representation_kind="polyline",
        geometry=geometry_to_geojson(geometry),
        annotation_role=role,
    )


def _polygon(
    element_id: str,
    geometry,
    object_class: str,
    layer: str,
    *,
    source_trace_ref: str | None = None,
    role: str | None = None,
) -> DesignElement:
    return DesignElement(
        element_id=element_id,
        object_class=object_class,
        layer_key=layer,
        representation_kind="polygon_ring",
        geometry=geometry_to_geojson(geometry),
        source_trace_ref=source_trace_ref,
        annotation_role=role,
    )


def _line_elements(geometry) -> list[LineString]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "LineString":
        return [geometry]
    if geometry.geom_type == "MultiLineString":
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        lines: list[LineString] = []
        for item in geometry.geoms:
            lines.extend(_line_elements(item))
        return lines
    return []


def _polygon_elements(geometry) -> list[Polygon]:
    if geometry.is_empty:
        return []
    if geometry.geom_type == "Polygon":
        return [geometry]
    if geometry.geom_type == "MultiPolygon":
        return list(geometry.geoms)
    if geometry.geom_type == "GeometryCollection":
        polygons: list[Polygon] = []
        for item in geometry.geoms:
            polygons.extend(_polygon_elements(item))
        return polygons
    return []


def _angle(line: LineString) -> float:
    coords = list(line.coords)
    dx = coords[-1][0] - coords[0][0]
    dy = coords[-1][1] - coords[0][1]
    angle = math.degrees(math.atan2(dy, dx))
    while angle > 90:
        angle -= 180
    while angle <= -90:
        angle += 180
    return angle


def _midpoint(line: LineString) -> tuple[float, float]:
    point = line.interpolate(0.5, normalized=True)
    return (float(point.x), float(point.y))


def build_drawing_elements(
    design_input: DesignInput,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    green_layout: GreenLayout,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
    metrics: dict[str, Any],
) -> tuple[DesignElement, ...]:
    elements: list[DesignElement] = []
    focus_box = box(*intent.focus_bbox)
    placed_bounds = unary_union(
        [item.footprint for item in building_layout.focus_buildings]
    ).bounds
    plan_box = box(
        placed_bounds[0] - 25.0,
        placed_bounds[1] - 25.0,
        placed_bounds[2] + 25.0,
        placed_bounds[3] + 25.0,
    )
    depth = basis.staircase_depth_m

    boundary_lines = _line_elements(
        design_input.site_boundary.exterior.intersection(plan_box)
    )
    for index, line in enumerate(boundary_lines, start=1):
        elements.append(
            _polyline(
                f"SITE-BOUNDARY-VIEW-{index}",
                line,
                "A-SITE-BOUNDARY",
                role="site_boundary_view",
            )
        )

    for building in building_layout.focus_buildings:
        elements.append(
            DesignElement(
                element_id=f"B-{building.building_id}",
                object_class="building",
                layer_key="A-BUILDING-OUTLINE",
                representation_kind="polygon_ring",
                geometry=geometry_to_geojson(building.footprint),
                massing={
                    "height_m": building.height_m,
                    "height_state": "proposed",
                    "base_elevation_m": 0.0,
                    "height_source": basis.basis_id,
                },
                source_trace_ref=building.building_id,
                annotation_role="standardized_building",
            )
        )
        for index, line in enumerate(building.unit_lines, start=1):
            elements.append(
                _polyline(
                    f"UL-{building.building_id}-{index:02d}",
                    line,
                    "A-UNIT-LINE",
                    role="unit_division",
                )
            )
        width = (
            30.0
            if building.is_facility
            else basis.building_width(building.unit_count)
        )
        if building.is_facility:
            heading = f"{building.building_id}  FACILITY"
            stats = f"{building.gfa_m2:.0f}m2  H{building.height_m:.1f}m"
        else:
            heading = (
                f"{building.building_id}  {building.unit_count}U"
            )
            stats = (
                f"{building.households}HH  H{building.height_m:.1f}m  "
                f"{width:.1f}x{depth:.1f}"
            )
        elements.append(
            _text(
                f"LBL-{building.building_id}-HEAD",
                building.label_anchor[0],
                building.label_anchor[1],
                heading,
                2.2,
                "A-BUILDING-LABEL",
                role="building_label",
            )
        )
        elements.append(
            _text(
                f"LBL-{building.building_id}-STATS",
                building.label_anchor[0],
                building.label_anchor[1] - 4.0,
                stats,
                1.8,
                "A-BUILDING-LABEL",
                role="building_label",
            )
        )

    focus_roads = [
        road
        for road in road_layout.roads
        if road.centerline.intersects(plan_box)
    ]
    road_layers = {
        "main": "C-ROAD-MAIN",
        "branch": "C-ROAD-BRANCH",
        "access": "C-ROAD-ACCESS",
    }
    for class_name, layer in road_layers.items():
        class_roads = [
            road for road in focus_roads if road.class_name == class_name
        ]
        if not class_roads:
            continue
        corridor = unary_union(
            [road.corridor for road in class_roads]
        ).intersection(plan_box)
        for index, polygon in enumerate(
            _polygon_elements(corridor), start=1
        ):
            elements.append(
                _polygon(
                    f"ROAD-{class_name.upper()}-{index}",
                    polygon,
                    "road_corridor",
                    layer,
                    role=f"schematic_{class_name}_corridor",
                )
            )
    sidewalk = road_layout.sidewalk_union.intersection(plan_box)
    for index, polygon in enumerate(_polygon_elements(sidewalk), start=1):
        elements.append(
            _polygon(
                f"SIDEWALK-FOCUS-{index}",
                polygon,
                "road_sidewalk",
                "C-SIDEWALK",
                role="schematic_sidewalk",
            )
        )
    for road in focus_roads:
        clipped = road.centerline.intersection(plan_box.buffer(5.0))
        for index, line in enumerate(_line_elements(clipped), start=1):
            elements.append(
                DesignElement(
                    element_id=f"CL-{road.edge_id}-{index}",
                    object_class="road_centerline",
                    layer_key="C-ROAD-CENTER",
                    representation_kind="centerline",
                    geometry=geometry_to_geojson(line),
                    source_trace_ref=road.edge_id,
                    annotation_role="road_centerline",
                )
            )
            x, y = _midpoint(line)
            elements.append(
                _text(
                    f"RLBL-{road.edge_id}-{index}",
                    x,
                    y + 1.5,
                    f"{road.class_name.upper()} {road.width_m:.1f}m",
                    2.0,
                    "C-ROAD-LABEL",
                    rotation=_angle(line),
                    role="road_label",
                )
            )

    for green in green_layout.focus_greens:
        if not green.geometry.intersects(plan_box):
            continue
        clipped = green.geometry.intersection(plan_box)
        for index, polygon in enumerate(
            _polygon_elements(clipped), start=1
        ):
            elements.append(
                _polygon(
                    f"GRN-{green.green_id}-{index}",
                    polygon,
                    "green_space",
                    "L-GREEN",
                    source_trace_ref=(
                        green.green_id
                        if green.classification == "cluster_green"
                        else None
                    ),
                    role=green.classification,
                )
            )
        if (
            green.area_m2 >= 500.0
            or green.classification in {"cluster_green", "green_strip"}
        ):
            elements.append(
                _text(
                    f"LBL-{green.green_id}",
                    green.label_anchor[0],
                    green.label_anchor[1],
                    (
                        f"{green.classification.replace('_', ' ').upper()} "
                        f"{green.area_m2:.0f}m2"
                    ),
                    1.8,
                    "L-GREEN-LABEL",
                    role="green_label",
                )
            )

    for entrance in parking_layout.entrances:
        if not plan_box.contains(entrance.point):
            continue
        elements.append(
            _polygon(
                f"ENT-{entrance.entrance_id}",
                entrance.point.buffer(2.0, quad_segs=16),
                "entrance",
                "A-ENTRANCE",
                source_trace_ref=(
                    entrance.entrance_id
                    if entrance.status == "existing"
                    else None
                ),
                role=f"garage_entrance_{entrance.status}",
            )
        )
        elements.append(
            _text(
                f"LBL-ENT-{entrance.entrance_id}",
                entrance.point.x + 3.0,
                entrance.point.y + 3.0,
                f"{entrance.status.upper()} GARAGE",
                2.0,
                "A-ANNO-TEXT",
                role="entrance_label",
            )
        )

    if len(building_layout.rows) >= 2:
        first_row = building_layout.rows[0]
        second_row = building_layout.rows[1]
        x = intent.focus_bbox[0] + 4.0
        y1 = float(first_row["y"]) + depth
        y2 = float(second_row["y"])
        elements.append(
            _polyline(
                "DIM-NS-01",
                LineString([(x, y1), (x, y2)]),
                "A-DIM",
                role="dimension",
            )
        )
        for tick_y in (y1, y2):
            elements.append(
                _polyline(
                    f"DIM-NS-TICK-{tick_y:.1f}",
                    LineString([(x - 2, tick_y), (x + 2, tick_y)]),
                    "A-DIM",
                    role="dimension_tick",
                )
            )
        elements.append(
            _text(
                "DIM-NS-LABEL",
                x - 9.0,
                (y1 + y2) / 2,
                "20.0 m N-S",
                2.2,
                "A-DIM",
                role="dimension_text",
            )
        )

    bounds = plan_box.bounds
    elements.append(
        _polyline(
            "DIM-FOCUS-W",
            LineString([(bounds[0], bounds[1] - 8), (bounds[2], bounds[1] - 8)]),
            "A-DIM",
            role="dimension",
        )
    )
    elements.append(
        _text(
            "DIM-FOCUS-W-LABEL",
            (bounds[0] + bounds[2]) / 2,
            bounds[1] - 11,
            f"{bounds[2] - bounds[0]:.1f} m",
            2.2,
            "A-DIM",
            role="dimension_text",
        )
    )
    elements.append(
        _polyline(
            "DIM-FOCUS-H",
            LineString([(bounds[0] - 10, bounds[1]), (bounds[0] - 10, bounds[3])]),
            "A-DIM",
            role="dimension",
        )
    )
    elements.append(
        _text(
            "DIM-FOCUS-H-LABEL",
            bounds[0] - 13,
            (bounds[1] + bounds[3]) / 2,
            f"{bounds[3] - bounds[1]:.1f} m",
            2.2,
            "A-DIM",
            rotation=90.0,
            role="dimension_text",
        )
    )

    elements.append(
        _polyline(
            "DRAWING-FRAME",
            box(10.0, 290.0, 560.0, 670.0).exterior,
            "A-FRAME",
            role="drawing_frame",
        )
    )
    elements.append(
        _polyline(
            "TITLE-BLOCK",
            box(270.0, 300.0, 555.0, 400.0).exterior,
            "A-TITLE",
            role="title_block",
        )
    )
    for y in (300.0, 310.0, 328.0, 346.0, 364.0, 382.0):
        elements.append(
            _polyline(
                f"TITLE-LINE-{int(y)}",
                LineString([(270, y), (555, y)]),
                "A-TITLE",
                role="title_block_line",
            )
        )
    title_lines = (
        (390.0, "CASE-SKETCH-001 / AUTONOMOUS DESIGN DRAFT", 2.8),
        (372.0, "SITE PLAN - FOCUS GROUP A", 3.2),
        (
            354.0,
            "SCALE 1:1000 (A2) | UNITS: m | SHEET A-101 | "
            f"STANDARD: {basis.drawing_standard}",
            1.9,
        ),
        (
            336.0,
            (
                f"FOCUS {metrics['focus_group_id']}: "
                f"{metrics['focus_building_count']}B / "
                f"{metrics['focus_unit_count']}U | "
                f"BASIS: {basis.basis_id}"
            ),
            1.9,
        ),
        (
            318.0,
            (
                f"FAR {metrics['far']:.3f} | {metrics['households']} HH | "
                f"{metrics['parking_spaces']} PARKING | "
                f"{metrics['parking_entrances']} ENTRANCES | "
                f"UNBUILT {metrics['unbuilt_ratio'] * 100:.1f}% | "
                f"CAND OPEN SPACE "
                f"{metrics['candidate_open_space_ratio'] * 100:.1f}% | "
                f"DESIGNED GREEN "
                f"{metrics['designed_green_ratio'] * 100:.1f}% (DEFERRED)"
            ),
            1.9,
        ),
        (
            305.0,
            "AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT CODE-COMPLIANCE",
            1.8,
        ),
    )
    for index, (y, text, height) in enumerate(title_lines, start=1):
        elements.append(
            _text(
                f"TITLE-{index:02d}",
                276.0,
                y,
                text,
                height,
                "A-TITLE",
                role="title_text",
            )
        )

    key_scale = 0.25
    key_ox = 270.0
    key_oy = 420.0

    def key_point(coords):
        return [
            (key_ox + float(x) * key_scale, key_oy + float(y) * key_scale)
            for x, y in coords
        ]

    site_coords = key_point(
        list(design_input.site_boundary.exterior.coords)
    )
    elements.append(
        _polyline(
            "KEY-SITE-BOUNDARY",
            LineString(site_coords),
            "A-KEYPLAN",
            role="key_plan",
        )
    )
    for group in intent.groups:
        bbox = group.bbox
        rectangle = box(*bbox)
        elements.append(
            _polyline(
                f"KEY-GROUP-{group.group_id}",
                LineString(key_point(list(rectangle.exterior.coords))),
                "A-KEYPLAN",
                role="key_plan",
            )
        )
        elements.append(
            _text(
                f"KEY-LBL-{group.group_id}",
                key_ox + group.centroid[0] * key_scale,
                key_oy + group.centroid[1] * key_scale,
                f"{group.group_id} {group.unit_count}U",
                1.8,
                "A-KEYPLAN",
                role="key_plan_label",
            )
        )
    for road in road_layout.roads:
        if road.class_name != "main":
            continue
        coords = key_point(list(road.centerline.coords))
        elements.append(
            _polyline(
                f"KEY-MAIN-{road.edge_id}",
                LineString(coords),
                "A-KEYPLAN",
                role="key_plan",
            )
        )
    focus_rect = plan_box
    elements.append(
        _polyline(
            "KEY-FOCUS-BBOX",
            LineString(key_point(list(focus_rect.exterior.coords))),
            "A-SITE-BOUNDARY",
            role="key_plan_focus",
        )
    )
    elements.append(
        _text(
            "KEY-FOCUS-LABEL",
            key_ox + plan_box.bounds[0] * key_scale,
            key_oy + plan_box.bounds[3] * key_scale + 5.0,
            "FOCUS",
            2.0,
            "A-SITE-BOUNDARY",
            role="key_plan_label",
        )
    )
    elements.append(
        _text(
            "KEY-FOCUS-DESIGN",
            key_ox + plan_box.bounds[0] * key_scale,
            key_oy + plan_box.bounds[1] * key_scale - 6.0,
            (
                f"FOCUS {metrics['focus_group_id']}: "
                f"{metrics['focus_building_count']}B / "
                f"{metrics['focus_unit_count']}U DESIGNED"
            ),
            2.0,
            "A-KEYPLAN",
            role="key_plan_label",
        )
    )
    elements.append(
        _text(
            "KEY-TITLE",
            270.0,
            650.0,
            "SITE CONTEXT 1:4000",
            2.2,
            "A-KEYPLAN",
            role="key_plan_title",
        )
    )

    elements.append(
        _text(
            "LEGEND-TITLE", 420.0, 648.0, "LEGEND", 2.5, "A-LEGEND",
            role="legend_title",
        )
    )
    legend_items = (
        ("A-BUILDING-OUTLINE", "BUILDING OUTLINE"),
        ("A-UNIT-LINE", "UNIT LINE"),
        ("C-ROAD-MAIN", "MAIN ROAD"),
        ("C-ROAD-BRANCH", "BRANCH ROAD"),
        ("C-ROAD-ACCESS", "ACCESS ROAD"),
        ("C-SIDEWALK", "SIDEWALK"),
        ("L-GREEN", "GREEN SPACE"),
        ("A-ENTRANCE", "GARAGE ENTRANCE"),
        ("A-DIM", "DIMENSION"),
    )
    for index, (layer, label) in enumerate(legend_items):
        y = 628.0 - index * 16.0
        elements.append(
            _polyline(
                f"LEGEND-SWATCH-{index:02d}",
                box(420.0, y - 4.0, 436.0, y + 4.0).exterior,
                layer,
                role="legend_swatch",
            )
        )
        elements.append(
            _text(
                f"LEGEND-LABEL-{index:02d}",
                442.0,
                y - 1.0,
                label,
                2.0,
                "A-LEGEND",
                role="legend_label",
            )
        )

    elements.append(
        _polyline(
            "NORTH-ARROW",
            Polygon(
                [(250, 640), (244, 620), (256, 620), (250, 640)]
            ).exterior,
            "A-NORTH",
            role="north_arrow",
        )
    )
    elements.append(
        _text(
            "NORTH-LABEL", 245.0, 645.0, "N", 3.0, "A-NORTH",
            role="north_label",
        )
    )

    elements.append(
        _polyline(
            "SCALE-BAR",
            LineString([(30, 300), (80, 300), (130, 300)]),
            "A-SCALE",
            role="scale_bar",
        )
    )
    for x in (30, 80, 130):
        elements.append(
            _polyline(
                f"SCALE-TICK-{x}",
                LineString([(x, 297), (x, 303)]),
                "A-SCALE",
                role="scale_bar_tick",
            )
        )
    elements.append(
        _text(
            "SCALE-LABEL",
            30.0,
            292.0,
            "0          50          100 m",
            2.0,
            "A-SCALE",
            role="scale_bar_label",
        )
    )
    return tuple(elements)

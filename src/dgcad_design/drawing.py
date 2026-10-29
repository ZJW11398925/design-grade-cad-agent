from __future__ import annotations

import math
from typing import Any

from shapely import make_valid
from shapely.affinity import affine_transform
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

try:  # M4d-1a renamed the full-site parcel classification
    from .green import POTENTIAL_OPEN_SPACE_CLASSIFICATION
except ImportError:  # pragma: no cover - compatibility with older green.py
    POTENTIAL_OPEN_SPACE_CLASSIFICATION = "potential_open_space"

#: Full-site open-space tiling parcels are NOT designed green.  The current
#: classification is ``potential_open_space``; the older names are accepted so
#: a drawing built against an older ``green.py`` still lands on the neutral
#: layer instead of silently relabelling open space as designed green.
POTENTIAL_OPEN_SPACE_CLASSIFICATIONS = frozenset(
    {
        POTENTIAL_OPEN_SPACE_CLASSIFICATION,
        "potential_open_space",
        "designed_green",
        "landscape_allocation_candidate",
        "open_space_allocation",
    }
)


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


#: Full-site sheet (A-102) plan transform: 1 sheet unit = 1 mm, plan scale
#: 1:2000, so one design metre is 0.5 sheet units.  The site bounds are
#: 0-388 x 0-630 m, which maps to x 30-224, y 320-635 on the A2 frame
#: (10-560 x 290-670) already used by the focus sheet (A-101).
FULL_SITE_SHEET_ID = "A-102"
FULL_SITE_PLAN_SCALE = 0.5
FULL_SITE_PLAN_ORIGIN = (30.0, 320.0)


def _sheet_point(x: float, y: float) -> tuple[float, float]:
    origin_x, origin_y = FULL_SITE_PLAN_ORIGIN
    return (
        origin_x + FULL_SITE_PLAN_SCALE * float(x),
        origin_y + FULL_SITE_PLAN_SCALE * float(y),
    )


def _sheet_geometry(geometry):
    origin_x, origin_y = FULL_SITE_PLAN_ORIGIN
    scale = FULL_SITE_PLAN_SCALE
    transformed = affine_transform(
        geometry, [scale, 0.0, 0.0, scale, origin_x, origin_y]
    )
    if not transformed.is_valid:
        # Downscaling to 1:2000 can collapse near-coincident vertices of dense
        # buffered rings and produce a self-intersection at the drawing scale.
        # This repairs the *sheet* geometry only; the design geometry in the
        # layouts and the focus sheet is untouched.
        transformed = make_valid(transformed)
    return transformed


def _frame_and_title_elements(
    title_lines: tuple[tuple[float, str, float], ...],
    *,
    title_block: tuple[float, float, float, float] = (
        270.0,
        300.0,
        555.0,
        400.0,
    ),
    title_block_lines: tuple[float, ...] = (
        300.0,
        310.0,
        328.0,
        346.0,
        364.0,
        382.0,
    ),
) -> list[DesignElement]:
    elements = [
        _polyline(
            "DRAWING-FRAME",
            box(10.0, 290.0, 560.0, 670.0).exterior,
            "A-FRAME",
            role="drawing_frame",
        ),
        _polyline(
            "TITLE-BLOCK",
            box(*title_block).exterior,
            "A-TITLE",
            role="title_block",
        ),
    ]
    for y in title_block_lines:
        elements.append(
            _polyline(
                f"TITLE-LINE-{int(y)}",
                LineString([(270, y), (555, y)]),
                "A-TITLE",
                role="title_block_line",
            )
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
    return elements


def _key_plan_elements(
    design_input: DesignInput,
    intent: DesignIntent,
    road_layout: RoadLayout,
    focus_rect: Polygon,
    metrics: dict[str, Any],
) -> list[DesignElement]:
    elements: list[DesignElement] = []
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
            key_ox + focus_rect.bounds[0] * key_scale,
            key_oy + focus_rect.bounds[3] * key_scale + 5.0,
            "FOCUS",
            2.0,
            "A-SITE-BOUNDARY",
            role="key_plan_label",
        )
    )
    elements.append(
        _text(
            "KEY-FOCUS-DESIGN",
            key_ox + focus_rect.bounds[0] * key_scale,
            key_oy + focus_rect.bounds[1] * key_scale - 6.0,
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
    return elements


_DEFAULT_LEGEND_ITEMS = (
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

#: Full-site legend: the open-space tiling is potential open space, not a
#: landscape design; designed green keeps its own layer.
FULL_SITE_LEGEND_ITEMS = (
    ("A-BUILDING-OUTLINE", "BUILDING OUTLINE"),
    ("A-UNIT-LINE", "UNIT LINE"),
    ("C-ROAD-MAIN", "MAIN ROAD"),
    ("C-ROAD-BRANCH", "BRANCH ROAD"),
    ("C-ROAD-ACCESS", "ACCESS ROAD"),
    ("C-SIDEWALK", "SIDEWALK"),
    ("L-OPEN-SPACE", "POTENTIAL OPEN SPACE (NOT LANDSCAPE DESIGN)"),
    ("L-GREEN", "DESIGNED GREEN"),
    ("A-ENTRANCE", "GARAGE ENTRANCE"),
    ("A-DIM", "DIMENSION"),
)


def _legend_elements(
    legend_items: tuple[tuple[str, str], ...] = _DEFAULT_LEGEND_ITEMS,
) -> list[DesignElement]:
    elements = [
        _text(
            "LEGEND-TITLE", 420.0, 648.0, "LEGEND", 2.5, "A-LEGEND",
            role="legend_title",
        )
    ]
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
    return elements


def _north_elements() -> list[DesignElement]:
    return [
        _polyline(
            "NORTH-ARROW",
            Polygon(
                [(250, 640), (244, 620), (256, 620), (250, 640)]
            ).exterior,
            "A-NORTH",
            role="north_arrow",
        ),
        _text(
            "NORTH-LABEL", 245.0, 645.0, "N", 3.0, "A-NORTH",
            role="north_label",
        ),
    ]


def _scale_bar_elements() -> list[DesignElement]:
    elements = [
        _polyline(
            "SCALE-BAR",
            LineString([(30, 300), (80, 300), (130, 300)]),
            "A-SCALE",
            role="scale_bar",
        )
    ]
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
    return elements


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
                f"{metrics['parking_entrances']} ENT | "
                f"ACCESS {metrics['road_access_coverage'] * 100:.0f}% "
                f"({metrics['road_groups_served']}/"
                f"{metrics['road_groups_total']}) | "
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
    elements.extend(_frame_and_title_elements(title_lines))

    elements.extend(
        _key_plan_elements(
            design_input, intent, road_layout, plan_box, metrics
        )
    )

    elements.extend(_legend_elements())
    elements.extend(_north_elements())
    elements.extend(_scale_bar_elements())
    return tuple(elements)


def _potential_open_space_ratio(metrics: dict[str, Any]) -> float | None:
    """The full-site open-space tiling ratio (auxiliary, not designed green)."""
    for key in (
        "full_site_potential_open_space_ratio",
        "full_site_open_space_account_ratio",
        "full_site_open_space_ratio",
        "potential_open_space_ratio",
        "full_site_designed_green_ratio",
    ):
        value = metrics.get(key)
        if isinstance(value, (int, float)):
            return float(value)
    return None


def _dead_ends_unresolved(
    metrics: dict[str, Any],
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    intent: DesignIntent,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
    design_input: DesignInput,
) -> int | None:
    """Unresolved dead ends for the incomplete declaration.

    Prefers the metric published by the pipeline; falls back to measuring the
    same quantity from the layouts (same public access model the consistency
    checks use) so the number is never hard-coded.
    """
    for key in ("dead_ends_unresolved", "dead_end_unresolved_count"):
        value = metrics.get(key)
        if isinstance(value, int):
            return value
    try:
        from .access import build_road_access  # noqa: PLC0415

        access = build_road_access(
            building_layout,
            road_layout,
            intent,
            parking_layout,
            basis,
            site_boundary=design_input.site_boundary,
        )
        return int(access.dead_ends_unresolved)
    except Exception:  # noqa: BLE001 - declaration must not crash the sheet
        return None


def build_full_site_drawing_elements(
    design_input: DesignInput,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    green_layout: GreenLayout,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
    metrics: dict[str, Any],
    *,
    sheet_id: str = "A-102",
    candidate_id: str | None = None,
    status_line: str | None = None,
) -> tuple[DesignElement, ...]:
    """Build the full-site sheet (A-102): every building, road and green.

    The focus sheet (A-101, :func:`build_drawing_elements`) is unchanged: it
    draws the 7 focus buildings in detail at 1:1 in design metres.  This sheet
    draws the whole site at 1:2000 (0.5 sheet units per metre) so all 55
    buildings appear with their design geometry: footprint, unit division
    lines and the two-line building label.  Element IDs follow the same
    ``B-*`` / ``UL-*`` / ``LBL-*`` convention so the CAD/XDATA chain is
    identical; only the plan transform and the label text heights differ
    (the sheet scale is 1:2000, not 1:1000).

    ``sheet_id``, ``candidate_id`` and ``status_line`` let a co-design
    candidate reuse this sheet verbatim: the sheet number, the candidate tag
    and the completeness declaration (e.g. a hard-valid candidate or an
    ``INCOMPLETE`` clearance failure) are stamped in the title block.  The
    defaults reproduce the A-102 sheet exactly.
    """
    elements: list[DesignElement] = []
    site_box = box(*design_input.site_boundary.bounds)
    depth = basis.staircase_depth_m

    elements.append(
        _polyline(
            "SITE-BOUNDARY-VIEW-1",
            _sheet_geometry(
                LineString(design_input.site_boundary.exterior.coords)
            ),
            "A-SITE-BOUNDARY",
            role="site_boundary_view",
        )
    )

    for building in sorted(
        building_layout.buildings, key=lambda item: item.building_id
    ):
        elements.append(
            DesignElement(
                element_id=f"B-{building.building_id}",
                object_class="building",
                layer_key="A-BUILDING-OUTLINE",
                representation_kind="polygon_ring",
                geometry=geometry_to_geojson(
                    _sheet_geometry(building.footprint)
                ),
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
                    _sheet_geometry(line),
                    "A-UNIT-LINE",
                    role="unit_division",
                )
            )
        if building.is_facility:
            heading = f"{building.building_id}  FACILITY"
            stats = f"{building.gfa_m2:.0f}m2 H{building.height_m:.1f}m"
        else:
            heading = f"{building.building_id}  {building.unit_count}U"
            stats = (
                f"{building.households}HH H{building.height_m:.1f}m "
                f"{basis.building_width(building.unit_count):.0f}x{depth:.0f}m"
            )
        anchor_x, anchor_y = _sheet_point(*building.label_anchor)
        elements.append(
            _text(
                f"LBL-{building.building_id}-HEAD",
                anchor_x,
                anchor_y,
                heading,
                1.4,
                "A-BUILDING-LABEL",
                role="building_label",
            )
        )
        elements.append(
            _text(
                f"LBL-{building.building_id}-STATS",
                anchor_x,
                anchor_y - 2.2,
                stats,
                1.1,
                "A-BUILDING-LABEL",
                role="building_label",
            )
        )

    road_layers = {
        "main": "C-ROAD-MAIN",
        "branch": "C-ROAD-BRANCH",
        "access": "C-ROAD-ACCESS",
    }
    for class_name, layer in road_layers.items():
        class_roads = [
            road
            for road in road_layout.roads
            if road.class_name == class_name
        ]
        if not class_roads:
            continue
        corridor = unary_union(
            [road.corridor for road in class_roads]
        ).intersection(site_box)
        for index, polygon in enumerate(
            _polygon_elements(_sheet_geometry(corridor)), start=1
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
    sidewalk = road_layout.sidewalk_union.intersection(site_box)
    for index, polygon in enumerate(
        _polygon_elements(_sheet_geometry(sidewalk)), start=1
    ):
        elements.append(
            _polygon(
                f"SIDEWALK-SITE-{index}",
                polygon,
                "road_sidewalk",
                "C-SIDEWALK",
                role="schematic_sidewalk",
            )
        )
    for road in road_layout.roads:
        clipped = _sheet_geometry(road.centerline)
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
                    y + 1.2,
                    f"{road.class_name.upper()} {road.width_m:.1f}m",
                    1.1,
                    "C-ROAD-LABEL",
                    rotation=_angle(line),
                    role="road_label",
                )
            )

    # The full-site open-space tiling is potential open space, NOT designed
    # green: it is drawn on the neutral L-OPEN-SPACE layer and labelled as
    # such.  Designed green (focus cluster/strip/supplementary) keeps L-GREEN
    # on the focus sheet; it is never re-drawn as potential open space.
    full_site_green = getattr(green_layout, "full_site_green", None)
    if full_site_green is not None:
        open_space_items = tuple(
            getattr(full_site_green, "parcels", ()) or ()
        )
    else:
        open_space_items = ()
    for green in open_space_items:
        classification = str(getattr(green, "classification", ""))
        is_potential = classification in POTENTIAL_OPEN_SPACE_CLASSIFICATIONS
        layer = "L-OPEN-SPACE" if is_potential else "L-GREEN"
        role = "potential_open_space" if is_potential else classification
        prefix = "OPS" if is_potential else "GRN"
        clipped = green.geometry.intersection(site_box)
        if clipped.is_empty:
            continue
        for index, polygon in enumerate(
            _polygon_elements(_sheet_geometry(clipped)), start=1
        ):
            elements.append(
                _polygon(
                    f"{prefix}-{green.green_id}-{index}",
                    polygon,
                    "green_space",
                    layer,
                    source_trace_ref=None,
                    role=role,
                )
            )
        if green.area_m2 >= 500.0 or is_potential:
            label_x, label_y = _sheet_point(*green.label_anchor)
            if is_potential:
                label_text = (
                    f"POTENTIAL OPEN SPACE {green.area_m2:.0f}m2"
                )
                label_layer = "L-OPEN-SPACE"
                label_role = "potential_open_space_label"
            else:
                label_text = (
                    f"{classification.replace('_', ' ').upper()} "
                    f"{green.area_m2:.0f}m2"
                )
                label_layer = "L-GREEN-LABEL"
                label_role = "green_label"
            elements.append(
                _text(
                    f"LBL-{green.green_id}",
                    label_x,
                    label_y,
                    label_text,
                    1.2,
                    label_layer,
                    role=label_role,
                )
            )
    if full_site_green is None:
        # Compatibility path: older green layouts have no full-site account, so
        # the source greens are drawn on L-GREEN as before.
        for green in green_layout.greens:
            clipped = green.geometry.intersection(site_box)
            if clipped.is_empty:
                continue
            for index, polygon in enumerate(
                _polygon_elements(_sheet_geometry(clipped)), start=1
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
                or green.classification
                in {"cluster_green", "green_strip"}
            ):
                label_x, label_y = _sheet_point(*green.label_anchor)
                elements.append(
                    _text(
                        f"LBL-{green.green_id}",
                        label_x,
                        label_y,
                        (
                            f"{green.classification.replace('_', ' ').upper()} "
                            f"{green.area_m2:.0f}m2"
                        ),
                        1.2,
                        "L-GREEN-LABEL",
                        role="green_label",
                    )
                )

    for entrance in parking_layout.entrances:
        if not site_box.contains(entrance.point):
            continue
        point = _sheet_point(entrance.point.x, entrance.point.y)
        elements.append(
            _polygon(
                f"ENT-{entrance.entrance_id}",
                Point(point).buffer(
                    FULL_SITE_PLAN_SCALE * 2.0, quad_segs=16
                ),
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
                point[0] + 1.5,
                point[1] + 1.5,
                f"{entrance.status.upper()} GARAGE",
                1.1,
                "A-ANNO-TEXT",
                role="entrance_label",
            )
        )

    focus_rect = box(*intent.focus_bbox)
    elements.append(
        _polyline(
            "FOCUS-EXTENT",
            LineString(
                [
                    _sheet_point(x, y)
                    for x, y in list(focus_rect.exterior.coords)
                ]
            ),
            "A-SITE-BOUNDARY",
            role="focus_extent",
        )
    )
    focus_label = _sheet_point(
        focus_rect.bounds[0], focus_rect.bounds[3]
    )
    elements.append(
        _text(
            "FOCUS-EXTENT-LABEL",
            focus_label[0],
            focus_label[1] + 2.0,
            (
                f"FOCUS {metrics['focus_group_id']} "
                f"({metrics['focus_building_count']}B)"
            ),
            1.4,
            "A-SITE-BOUNDARY",
            role="focus_extent_label",
        )
    )

    min_x, min_y, max_x, max_y = design_input.site_boundary.bounds
    plan_min_x, plan_min_y = _sheet_point(min_x, min_y)
    plan_max_x, plan_max_y = _sheet_point(max_x, max_y)
    width_m = max_x - min_x
    height_m = max_y - min_y
    dim_y = plan_min_y - 8.0
    elements.append(
        _polyline(
            "DIM-SITE-W",
            LineString([(plan_min_x, dim_y), (plan_max_x, dim_y)]),
            "A-DIM",
            role="dimension",
        )
    )
    for tick_x in (plan_min_x, plan_max_x):
        elements.append(
            _polyline(
                f"DIM-SITE-W-TICK-{tick_x:.1f}",
                LineString([(tick_x, dim_y - 2), (tick_x, dim_y + 2)]),
                "A-DIM",
                role="dimension_tick",
            )
        )
    elements.append(
        _text(
            "DIM-SITE-W-LABEL",
            (plan_min_x + plan_max_x) / 2,
            dim_y - 4.0,
            f"{width_m:.1f} m",
            2.0,
            "A-DIM",
            role="dimension_text",
        )
    )
    dim_x = plan_min_x - 6.0
    elements.append(
        _polyline(
            "DIM-SITE-H",
            LineString([(dim_x, plan_min_y), (dim_x, plan_max_y)]),
            "A-DIM",
            role="dimension",
        )
    )
    for tick_y in (plan_min_y, plan_max_y):
        elements.append(
            _polyline(
                f"DIM-SITE-H-TICK-{tick_y:.1f}",
                LineString([(dim_x - 2, tick_y), (dim_x + 2, tick_y)]),
                "A-DIM",
                role="dimension_tick",
            )
        )
    elements.append(
        _text(
            "DIM-SITE-H-LABEL",
            dim_x - 4.0,
            (plan_min_y + plan_max_y) / 2,
            f"{height_m:.1f} m",
            2.0,
            "A-DIM",
            rotation=90.0,
            role="dimension_text",
        )
    )

    # Designed green is the legacy cluster+strip account (never the open-space
    # tiling); the potential open space is a separate auxiliary account.
    designed_green_ratio = metrics["designed_green_ratio"]
    potential_open_space_ratio = _potential_open_space_ratio(metrics)
    green_target = metrics.get("full_site_green_target_ratio")
    if not isinstance(green_target, (int, float)):
        green_target = metrics.get(
            "full_site_open_space_account_target_ratio"
        )
    if not isinstance(green_target, (int, float)):
        green_target = metrics.get("target_ratio", basis.green_ratio_min)
    served = int(metrics.get("road_groups_served", 0))
    groups_total = int(metrics.get("road_groups_total", 0))
    dead_ends_unresolved = _dead_ends_unresolved(
        metrics,
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        design_input,
    )
    dead_ends_text = (
        str(dead_ends_unresolved)
        if dead_ends_unresolved is not None
        else "n/a"
    )
    incomplete_parts = [
        f"ROAD ACCESS {served}/{groups_total}",
        f"DEAD ENDS {dead_ends_text} UNRESOLVED",
    ]
    if designed_green_ratio < float(green_target) - 1e-12:
        incomplete_parts.append(
            f"DESIGNED GREEN < {float(green_target) * 100:.0f}%"
        )
    incomplete_line = "INCOMPLETE: " + " - ".join(incomplete_parts)
    min_clearance = metrics.get("min_road_clearance_m")
    clearance_text = (
        f"{min_clearance:.2f}"
        if isinstance(min_clearance, (int, float))
        else "n/a"
    )
    clearance_violations = metrics.get("road_clearance_violation_count")
    clearance_violation_text = (
        str(clearance_violations)
        if clearance_violations is not None
        else "n/a"
    )
    min_ns = metrics.get("min_ns_spacing_m")
    ns_text = f"{min_ns:.1f}" if isinstance(min_ns, (int, float)) else "n/a"
    potential_text = (
        f"{potential_open_space_ratio * 100:.2f}%"
        if potential_open_space_ratio is not None
        else "n/a"
    )
    title_lines = (
        (396.0, "CASE-SKETCH-001 / AUTONOMOUS DESIGN DRAFT", 2.4),
        (
            385.0,
            (
                "SITE PLAN - FULL SITE"
                if candidate_id is None
                else f"SITE PLAN - FULL SITE - CANDIDATE {candidate_id}"
            ),
            2.8,
        ),
        (
            371.0,
            f"SCALE 1:2000 (A2) | UNITS: m | SHEET {sheet_id} | "
            f"STANDARD: {basis.drawing_standard} | BASIS: {basis.basis_id}",
            1.9,
        ),
        (
            357.0,
            (
                f"FULL SITE {metrics['building_count']}B / "
                f"{metrics['unit_count']}U | "
                f"FOCUS {metrics['focus_group_id']}: "
                f"{metrics['focus_building_count']}B / "
                f"{metrics['focus_unit_count']}U | "
                f"FAR {metrics['far']:.3f} | "
                f"{metrics['households']} HH | "
                f"{metrics['parking_spaces']} PARKING | "
                f"{metrics['parking_entrances']} ENT | "
                f"ROAD CLEAR {clearance_text}m "
                f"({clearance_violation_text} VIOL) | NS {ns_text}m"
            ),
            1.9,
        ),
        (
            343.0,
            f"DESIGNED GREEN {designed_green_ratio * 100:.2f}% - INCOMPLETE",
            1.9,
        ),
        (
            329.0,
            f"POTENTIAL OPEN SPACE {potential_text} - NOT LANDSCAPE DESIGN",
            1.9,
        ),
        (
            315.0,
            incomplete_line if status_line is None else status_line,
            1.9,
        ),
        (
            301.0,
            "AGENT-GENERATED PROPOSAL - NOT HUMAN-CONFIRMED - NOT CODE-COMPLIANCE",
            1.8,
        ),
    )
    elements.extend(
        _frame_and_title_elements(
            title_lines,
            title_block=(270.0, 290.0, 555.0, 400.0),
            title_block_lines=(
                290.0,
                304.0,
                318.0,
                332.0,
                346.0,
                360.0,
                374.0,
                388.0,
            ),
        )
    )
    elements.extend(
        _key_plan_elements(
            design_input, intent, road_layout, focus_rect, metrics
        )
    )
    elements.extend(_legend_elements(FULL_SITE_LEGEND_ITEMS))
    elements.extend(_north_elements())
    elements.extend(_scale_bar_elements())
    return tuple(elements)

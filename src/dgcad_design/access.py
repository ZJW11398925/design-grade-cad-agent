"""Design-aware road access evidence (M4c-1b / M4c-1e).

M4c-1a proved the *road network* is connected; M4c-1b showed that a group can sit
next to a road and still have no designed access. M4c-1e removes the last
proximity inference: a group is served only when a road **declares** it via
``serves_group_ids`` and carries an explicit ``access_terminal_xy``. The
evidence therefore distinguishes:

* ``declared`` — a road claims to serve the group;
* ``served_by_relation`` — the declared terminal satisfies the geometric rules
  (distance in ``[3.4, 3.5] m`` of the group footprint, outside every footprint,
  route crossing the footprint <= 0.1 m, access-road class);
* ``terminal_corridor_edge_clearance_m`` — how close the serving road's corridor
  comes to the nearest group building. This is a *different* quantity from the
  3.0 m centreline clearance: a 7 m branch round cap can be tangent (0.0 m)
  while a 4 m access road can sit ~1.5 m away.

Everything here is read-only: it consumes ``BuildingLayout``, ``RoadLayout``,
``DesignIntent``, ``ParkingLayout`` and ``DesignBasis`` and never mutates
geometry. "Access is a declared geometric relation, not a proximity guess."
"""
from __future__ import annotations

from dataclasses import dataclass, field, fields, is_dataclass
from typing import Any

from shapely.geometry import LineString, Point
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .intent import DesignIntent
from .parking import ParkingLayout, build_parking_layout
from .roads import RoadLayout, rebuild_group_access

SCHEMA_ID = "dgcad.design-road-access.v0.2"

#: Road classes that may serve a group as an access road.
ACCESS_ROAD_CLASSES = ("branch", "access")

#: Declared terminal distance from the group footprint must be inside this band.
TERMINAL_DISTANCE_MIN_M = 3.4
TERMINAL_DISTANCE_MAX_M = 3.5

#: A route may brush a building footprint by at most this length.
ROUTE_CROSSING_MAX_M = 0.1

#: Endpoint clustering precision (1e-9 m) for dead-end detection.
ENDPOINT_CLUSTER_DECIMALS = 9

#: A main-road stub farther than this from any building is "unfinished".
MAIN_STUB_UNFINISHED_DISTANCE_M = 10.0

#: Entrance proximity is "connected" within half the nearest road width + this.
ENTRANCE_CONNECTION_MARGIN_M = 1.0

#: Distance predicate for T-junction detection and float-inclusive bounds.
PASS_THROUGH_EPSILON_M = 1e-9

#: A declared terminal must sit on its serving road's centreline (or one of its
#: endpoints) within this tolerance; otherwise the declaration is fabricated.
TERMINAL_ON_ROAD_TOLERANCE_M = 1e-6

#: Statuses emitted when a declared service relation fails validation.
RELATION_DECLARED = "declared_relation_ok"
RELATION_NO_DECLARATION = "no_declared_serving_road"
RELATION_MULTIPLE_DECLARATIONS = "multiple_declared_serving_roads"
RELATION_MISSING_TERMINAL = "declared_terminal_missing"
RELATION_NOT_ACCESS_CLASS = "serving_road_is_not_an_access_road"
RELATION_TERMINAL_NOT_ON_ROAD = "declared_terminal_not_on_serving_road"
RELATION_TERMINAL_DISTANCE = "terminal_distance_out_of_band"
RELATION_TERMINAL_INSIDE_FOOTPRINT = "terminal_inside_building_footprint"
RELATION_ROUTE_CROSSING = "route_crosses_building_footprint"
ORPHAN_DECLARED_GROUP = "orphan_declared_group"

#: A site-edge terminus counts when its endpoint is at most this far from the
#: published site boundary.
SITE_EDGE_BOUNDARY_BAND_M = 5.0

#: Geometric tolerance for resolution verification (endpoint coincidence).
RESOLUTION_GEOMETRY_TOLERANCE_M = 1e-6

#: A bridge segment may brush a building footprint by at most this length.
BRIDGE_CROSSING_MAX_M = 0.1

DEAD_END_CLASSIFICATIONS = (
    "group_terminal_justified",
    "main_stub_unfinished",
    "unclassified",
)

MAIN_ROAD_OVERLAP_STATUS = "known_unresolved"


@dataclass(frozen=True)
class GroupAccess:
    group_id: str
    building_ids: tuple[str, ...]
    served: bool
    access_road_id: str | None
    terminal_xy: tuple[float, float] | None
    nearest_building_id: str | None
    terminal_to_building_m: float | None
    route_crossing_length_m: float | None
    reason: str
    declared: bool = False
    served_by_relation: bool = False
    terminal_centerline_distance_m: float | None = None
    terminal_corridor_edge_clearance_m: float | None = None
    relation_errors: tuple[dict[str, Any], ...] = ()

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "building_ids": list(self.building_ids),
            "served": self.served,
            "declared": self.declared,
            "served_by_relation": self.served_by_relation,
            "access_road_id": self.access_road_id,
            "terminal_xy": (
                None
                if self.terminal_xy is None
                else [float(self.terminal_xy[0]), float(self.terminal_xy[1])]
            ),
            "nearest_building_id": self.nearest_building_id,
            "terminal_to_building_m": self.terminal_to_building_m,
            "terminal_centerline_distance_m": self.terminal_centerline_distance_m,
            "terminal_corridor_edge_clearance_m": (
                self.terminal_corridor_edge_clearance_m
            ),
            "route_crossing_length_m": self.route_crossing_length_m,
            "relation_errors": [dict(item) for item in self.relation_errors],
            "reason": self.reason,
        }


@dataclass(frozen=True)
class EntranceAccess:
    entrance_id: str
    status: str
    point_xy: tuple[float, float]
    nearest_road_id: str | None
    distance_m: float | None
    connected: bool
    reason: str
    proximity_connected: bool = False
    driveway_designed: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrance_id": self.entrance_id,
            "status": self.status,
            "point_xy": [float(self.point_xy[0]), float(self.point_xy[1])],
            "nearest_road_id": self.nearest_road_id,
            "distance_m": self.distance_m,
            "connected": self.connected,
            "proximity_connected": self.proximity_connected,
            "driveway_designed": self.driveway_designed,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class DeadEndRecord:
    node_id: str
    coordinate: tuple[float, float]
    road_id: str
    road_class: str
    nearest_building_id: str | None
    distance_m: float | None
    classification: str
    justified: bool
    resolution: str | None = None
    resolved: bool = False
    resolution_verified: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "node_id": self.node_id,
            "coordinate": [float(self.coordinate[0]), float(self.coordinate[1])],
            "road_id": self.road_id,
            "road_class": self.road_class,
            "nearest_building_id": self.nearest_building_id,
            "distance_m": self.distance_m,
            "classification": self.classification,
            "justified": self.justified,
            "resolution": self.resolution,
            "resolved": self.resolved,
            "resolution_verified": self.resolution_verified,
        }


@dataclass(frozen=True)
class RoadAccessLayout:
    groups: tuple[GroupAccess, ...]
    entrances: tuple[EntranceAccess, ...]
    dead_ends: tuple[DeadEndRecord, ...]
    main_road_overlap: dict[str, Any] = field(default_factory=dict)
    orphan_declarations: tuple[dict[str, Any], ...] = ()
    main_alignment_records: tuple[Any, ...] = ()
    dead_end_resolutions: tuple[Any, ...] = ()

    @property
    def groups_total(self) -> int:
        return len(self.groups)

    @property
    def groups_served(self) -> int:
        return sum(1 for group in self.groups if group.served)

    @property
    def road_access_coverage(self) -> float:
        if not self.groups:
            return 0.0
        return self.groups_served / self.groups_total

    @property
    def unserved_group_ids(self) -> tuple[str, ...]:
        return tuple(
            sorted(group.group_id for group in self.groups if not group.served)
        )

    @property
    def relation_errors(self) -> tuple[dict[str, Any], ...]:
        return self.orphan_declarations + tuple(
            error for group in self.groups for error in group.relation_errors
        )

    @property
    def dead_ends_justified(self) -> int:
        return sum(1 for item in self.dead_ends if item.justified)

    @property
    def dead_ends_unfinished(self) -> int:
        return sum(
            1
            for item in self.dead_ends
            if item.classification == "main_stub_unfinished"
        )

    @property
    def dead_ends_unresolved(self) -> int:
        return sum(
            1
            for item in self.dead_ends
            if not item.resolved and not item.justified
        )

    @property
    def dead_ends_resolved(self) -> int:
        return sum(1 for item in self.dead_ends if item.resolved)

    @property
    def road_alignment_count(self) -> int:
        return len(self.main_alignment_records)

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "groups_total": self.groups_total,
            "groups_served": self.groups_served,
            "road_access_coverage": self.road_access_coverage,
            "unserved_group_ids": list(self.unserved_group_ids),
            "relation_error_count": len(self.relation_errors),
            "orphan_declared_group_ids": [
                item["group_id"] for item in self.orphan_declarations
            ],
            "road_alignment_count": self.road_alignment_count,
            "dead_ends_justified": self.dead_ends_justified,
            "dead_ends_unfinished": self.dead_ends_unfinished,
            "dead_ends_unresolved": self.dead_ends_unresolved,
            "dead_ends_resolved": self.dead_ends_resolved,
            "main_road_overlap": dict(self.main_road_overlap),
            "main_alignment_records": [
                _record_to_dict(item) for item in self.main_alignment_records
            ],
            "dead_end_resolutions": [
                _record_to_dict(item) for item in self.dead_end_resolutions
            ],
            "groups": [group.to_dict() for group in self.groups],
            "entrances": [item.to_dict() for item in self.entrances],
            "dead_ends": [item.to_dict() for item in self.dead_ends],
        }


def _group_footprints(
    building_layout: BuildingLayout, building_ids: tuple[str, ...]
) -> tuple[tuple[str, ...], Any]:
    buildings = {item.building_id: item for item in building_layout.buildings}
    present = tuple(bid for bid in building_ids if bid in buildings)
    if not present:
        return (), None
    return present, unary_union([buildings[bid].footprint for bid in present])


def _declared_serving_roads(
    road_layout: RoadLayout, group_id: str
) -> list[Any]:
    declared = []
    for road in road_layout.roads:
        serves = getattr(road, "serves_group_ids", ()) or ()
        if group_id in tuple(serves):
            declared.append(road)
    return declared


def _terminal_corridor_edge_clearance(
    road: Any, group_union: Any
) -> float | None:
    corridor = getattr(road, "corridor", None)
    if corridor is None:
        return None
    return float(corridor.distance(group_union))


def _relation_for_group(
    group_id: str,
    present_ids: tuple[str, ...],
    group_union: Any,
    road_layout: RoadLayout,
    building_layout: BuildingLayout,
) -> dict[str, Any]:
    """Validate the declared service relation for one group (no inference)."""
    buildings = {item.building_id: item for item in building_layout.buildings}
    declared = _declared_serving_roads(road_layout, group_id)
    errors: list[dict[str, Any]] = []
    result: dict[str, Any] = {
        "declared": bool(declared),
        "served_by_relation": False,
        "access_road_id": None,
        "terminal_xy": None,
        "nearest_building_id": None,
        "terminal_to_building_m": None,
        "terminal_centerline_distance_m": None,
        "terminal_corridor_edge_clearance_m": None,
        "route_crossing_length_m": None,
        "relation_errors": (),
    }
    if not declared:
        errors.append({"code": RELATION_NO_DECLARATION, "group_id": group_id})
        result["relation_errors"] = tuple(errors)
        return result
    if len(declared) > 1:
        errors.append({
            "code": RELATION_MULTIPLE_DECLARATIONS,
            "group_id": group_id,
            "road_ids": [road.edge_id for road in declared],
        })
        result["relation_errors"] = tuple(errors)
        return result

    road = declared[0]
    result["access_road_id"] = road.edge_id
    if road.class_name not in ACCESS_ROAD_CLASSES:
        errors.append({
            "code": RELATION_NOT_ACCESS_CLASS,
            "group_id": group_id,
            "road_id": road.edge_id,
            "road_class": road.class_name,
        })
    terminal_xy = getattr(road, "access_terminal_xy", None)
    if terminal_xy is None:
        errors.append({
            "code": RELATION_MISSING_TERMINAL,
            "group_id": group_id,
            "road_id": road.edge_id,
        })
        result["relation_errors"] = tuple(errors)
        return result

    terminal = Point(float(terminal_xy[0]), float(terminal_xy[1]))
    result["terminal_xy"] = (float(terminal.x), float(terminal.y))
    coordinates = list(road.centerline.coords)
    on_centreline = (
        terminal.distance(road.centerline) <= TERMINAL_ON_ROAD_TOLERANCE_M
        or any(
            terminal.distance(Point(float(x), float(y)))
            <= TERMINAL_ON_ROAD_TOLERANCE_M
            for x, y in (coordinates[0], coordinates[-1])
        )
    )
    if not on_centreline:
        errors.append({
            "code": RELATION_TERMINAL_NOT_ON_ROAD,
            "group_id": group_id,
            "road_id": road.edge_id,
            "terminal_distance_to_centerline_m": float(
                terminal.distance(road.centerline)
            ),
            "tolerance_m": TERMINAL_ON_ROAD_TOLERANCE_M,
        })
    distance = float(terminal.distance(group_union))
    nearest_id = min(
        present_ids, key=lambda bid: terminal.distance(buildings[bid].footprint)
    )
    result["nearest_building_id"] = nearest_id
    result["terminal_centerline_distance_m"] = distance
    result["terminal_to_building_m"] = distance
    if not (
        TERMINAL_DISTANCE_MIN_M - PASS_THROUGH_EPSILON_M
        <= distance
        <= TERMINAL_DISTANCE_MAX_M + PASS_THROUGH_EPSILON_M
    ):
        errors.append({
            "code": RELATION_TERMINAL_DISTANCE,
            "group_id": group_id,
            "road_id": road.edge_id,
            "terminal_centerline_distance_m": distance,
            "required_band_m": [TERMINAL_DISTANCE_MIN_M, TERMINAL_DISTANCE_MAX_M],
        })
    inside = [
        item.building_id
        for item in building_layout.buildings
        if item.footprint.contains(terminal)
    ]
    if inside:
        errors.append({
            "code": RELATION_TERMINAL_INSIDE_FOOTPRINT,
            "group_id": group_id,
            "road_id": road.edge_id,
            "building_ids": inside,
        })
    crossing_m = float(road.centerline.intersection(group_union).length)
    result["route_crossing_length_m"] = crossing_m
    if crossing_m > ROUTE_CROSSING_MAX_M + PASS_THROUGH_EPSILON_M:
        errors.append({
            "code": RELATION_ROUTE_CROSSING,
            "group_id": group_id,
            "road_id": road.edge_id,
            "route_crossing_length_m": crossing_m,
        })
    result["terminal_corridor_edge_clearance_m"] = (
        _terminal_corridor_edge_clearance(road, group_union)
    )
    result["relation_errors"] = tuple(errors)
    result["served_by_relation"] = not errors
    return result


def main_road_building_overlap(
    building_layout: BuildingLayout, road_layout: RoadLayout
) -> dict[str, Any]:
    """Read-only area overlap between main-road corridors and building footprints.

    Publishes the overlap instead of hiding it; after the M4c-2 main-road
    alignment the expected area is zero and the status becomes ``resolved``.
    """
    conflicts: list[dict[str, Any]] = []
    total = 0.0
    main_roads = [road for road in road_layout.roads if road.class_name == "main"]
    for road in main_roads:
        corridor = getattr(road, "corridor", None)
        if corridor is None:
            continue
        for building in building_layout.buildings:
            area = float(corridor.intersection(building.footprint).area)
            if area <= 0.01:
                continue
            conflicts.append({
                "road_id": road.edge_id,
                "building_id": building.building_id,
                "area_m2": area,
            })
            total += area
    conflicts.sort(key=lambda item: (-item["area_m2"], item["road_id"]))
    return {
        "area_m2": total,
        "conflicts": conflicts,
        "status": "resolved" if total <= 0.01 else MAIN_ROAD_OVERLAP_STATUS,
    }


def _record_to_dict(item: Any) -> dict[str, Any]:
    """Normalise a records entry (dict, dataclass or object) to a plain dict."""
    if isinstance(item, dict):
        return dict(item)
    to_dict = getattr(item, "to_dict", None)
    if callable(to_dict):
        return dict(to_dict())
    if is_dataclass(item):
        return {field_item.name: getattr(item, field_item.name) for field_item in fields(item)}
    return {key: value for key, value in vars(item).items() if not key.startswith("_")}


def _resolution_records(road_layout: RoadLayout) -> dict[Any, dict[str, Any]]:
    """Map node id / coordinate keys to the full, normalised resolution record."""
    mapping: dict[Any, dict[str, Any]] = {}
    for item in getattr(road_layout, "dead_end_resolutions", ()) or ():
        if isinstance(item, dict):
            record = dict(item)
        elif is_dataclass(item):
            record = {
                field_item.name: getattr(item, field_item.name)
                for field_item in fields(item)
            }
        else:
            record = {
                key: value
                for key, value in vars(item).items()
                if not key.startswith("_")
            }
        strategy = (
            record.get("resolution")
            or record.get("strategy")
            or record.get("kind")
        )
        if not strategy:
            continue
        record["strategy"] = str(strategy)
        node_id = record.get("node_id")
        if node_id:
            mapping[("id", str(node_id))] = record
        for key in ("coordinate", "original_xy", "adjusted_xy"):
            value = record.get(key)
            if (
                isinstance(value, (list, tuple))
                and len(value) == 2
                and None not in value
            ):
                mapping.setdefault(
                    (
                        "xy",
                        (
                            round(float(value[0]), 6),
                            round(float(value[1]), 6),
                        ),
                    ),
                    record,
                )
    return mapping


def _explicit_junctions(road_layout: RoadLayout) -> dict[str, tuple[float, float]]:
    """Map junction id -> coordinate from the explicit junction records."""
    junctions: dict[str, tuple[float, float]] = {}
    for item in getattr(road_layout, "explicit_junctions", ()) or ():
        if isinstance(item, dict):
            junction_id = item.get("id")
            x_value, y_value = item.get("x"), item.get("y")
        else:
            junction_id = getattr(item, "id", None)
            x_value, y_value = getattr(item, "x", None), getattr(item, "y", None)
        if junction_id is not None and x_value is not None and y_value is not None:
            junctions[str(junction_id)] = (float(x_value), float(y_value))
    return junctions


def _resolution_verified(
    record: dict[str, Any],
    road_layout: RoadLayout,
    building_layout: BuildingLayout,
    dead_end_coordinates: tuple[tuple[float, float], ...],
    site_boundary: Any | None,
) -> bool:
    """Phase 0: a resolution must be criterion_met AND geometrically true.

    * ``trimmed``: the adjusted endpoint is no longer a degree-1 node and it is
      attached to a junction or another design road;
    * ``bridged``: the named junction exists, the bridge segment does not cross a
      building footprint, and it lands on the declared bridge road;
    * ``site_edge_terminus``: the endpoint is within the boundary band (exactly on
      the boundary when extended), and no design road vertex lies outside the
      published site boundary.

    The record itself is never trusted beyond its claimed strategy/coordinates;
    every predicate below is re-computed from the design geometry.
    """
    if record.get("criterion_met") is not True:
        return False
    adjusted = record.get("adjusted_xy")
    if adjusted is None or len(adjusted) != 2:
        return False
    point = Point(float(adjusted[0]), float(adjusted[1]))
    own_road = next(
        (road for road in road_layout.roads if road.edge_id == record.get("road_id")),
        None,
    )
    if own_road is None:
        return False
    if own_road.centerline.distance(point) > RESOLUTION_GEOMETRY_TOLERANCE_M:
        return False
    strategy = record.get("strategy")
    junctions = _explicit_junctions(road_layout)
    if strategy == "trimmed":
        if any(
            point.distance(Point(*coordinate)) <= RESOLUTION_GEOMETRY_TOLERANCE_M
            for coordinate in dead_end_coordinates
        ):
            return False  # the trimmed endpoint is still degree-1
        if any(
            point.distance(Point(*coordinate)) <= RESOLUTION_GEOMETRY_TOLERANCE_M
            for coordinate in junctions.values()
        ):
            return True
        return any(
            road.edge_id != own_road.edge_id
            and road.centerline.distance(point) <= RESOLUTION_GEOMETRY_TOLERANCE_M
            for road in road_layout.roads
        )
    if strategy == "bridged":
        junction_id = record.get("junction_id")
        if junction_id is None or str(junction_id) not in junctions:
            return False
        junction_point = Point(*junctions[str(junction_id)])
        bridge = LineString([(point.x, point.y), (junction_point.x, junction_point.y)])
        for building in building_layout.buildings:
            if bridge.intersection(building.footprint).length > BRIDGE_CROSSING_MAX_M:
                return False
        bridge_road_id = record.get("bridge_road_id")
        if bridge_road_id is not None:
            return any(
                road.edge_id == bridge_road_id
                and road.centerline.distance(junction_point)
                <= RESOLUTION_GEOMETRY_TOLERANCE_M
                for road in road_layout.roads
            )
        return True
    if strategy == "site_edge_terminus":
        if site_boundary is None:
            return False  # cannot verify the published boundary
        allowed = site_boundary.buffer(SITE_EDGE_BOUNDARY_BAND_M)
        if not allowed.covers(point):
            return False  # the terminus itself is outside the published boundary
        corridor = getattr(own_road, "corridor", None)
        if corridor is None:
            return False
        # the resolving road's corridor must stay inside the boundary (the road
        # ends at a corridor-safe boundary line, it does not continue outside)
        containment = site_boundary.buffer(RESOLUTION_GEOMETRY_TOLERANCE_M)
        outside = corridor.difference(containment)
        if not outside.is_empty:
            return False
        # and the corridor must actually reach the boundary: a road stopping far
        # inside the site is not a site-edge terminus
        if float(corridor.boundary.distance(site_boundary.boundary)) > SITE_EDGE_BOUNDARY_BAND_M:
            return False
        for x_value, y_value in own_road.centerline.coords:
            if not containment.covers(Point(float(x_value), float(y_value))):
                return False
        return True
    return False


def _entrance_access(
    parking_layout: ParkingLayout | None, road_layout: RoadLayout
) -> tuple[EntranceAccess, ...]:
    records: list[EntranceAccess] = []
    for entrance in getattr(parking_layout, "entrances", ()) or ():
        point = entrance.point
        if not road_layout.roads:
            records.append(
                EntranceAccess(
                    entrance_id=entrance.entrance_id,
                    status=entrance.status,
                    point_xy=(float(point.x), float(point.y)),
                    nearest_road_id=None,
                    distance_m=None,
                    connected=False,
                    reason="no design road exists to connect the entrance",
                    proximity_connected=False,
                    driveway_designed=False,
                )
            )
            continue
        nearest = min(
            road_layout.roads,
            key=lambda road: point.distance(road.centerline),
        )
        distance = float(point.distance(nearest.centerline))
        limit = nearest.width_m / 2.0 + ENTRANCE_CONNECTION_MARGIN_M
        proximity = distance <= limit
        if proximity:
            reason = (
                f"proximity only; driveway geometry not designed "
                f"({distance:.3f} m from the nearest centreline, within half the "
                f"{nearest.width_m:.1f} m road width + {ENTRANCE_CONNECTION_MARGIN_M:.1f} m)"
            )
        elif entrance.status == "existing":
            reason = (
                "designer-marked garage face; driveway connection not designed "
                f"(proximity only, {distance:.3f} m from the nearest centreline)"
            )
        else:
            reason = (
                f"proximity only; driveway geometry not designed "
                f"({distance:.3f} m beyond half the {nearest.width_m:.1f} m road "
                f"width + {ENTRANCE_CONNECTION_MARGIN_M:.1f} m)"
            )
        records.append(
            EntranceAccess(
                entrance_id=entrance.entrance_id,
                status=entrance.status,
                point_xy=(float(point.x), float(point.y)),
                nearest_road_id=nearest.edge_id,
                distance_m=distance,
                connected=proximity,
                reason=reason,
                proximity_connected=proximity,
                driveway_designed=False,
            )
        )
    return tuple(records)


def _touched_by_other_road(
    point: Point, own_road_id: str, road_layout: RoadLayout
) -> bool:
    """True when another centreline passes through ``point`` (a T-junction).

    A road endpoint that lands on the interior of another road is a plain T
    junction after noding (degree >= 3), not a dead end.
    """
    return any(
        road.edge_id != own_road_id
        and road.centerline.distance(point) <= PASS_THROUGH_EPSILON_M
        for road in road_layout.roads
    )


def _dead_ends(
    road_layout: RoadLayout,
    building_layout: BuildingLayout,
    clearance_m: float,
    site_boundary: Any | None = None,
) -> tuple[DeadEndRecord, ...]:
    resolution_map = _resolution_records(road_layout)
    counts: dict[tuple[float, float], int] = {}
    owner: dict[tuple[float, float], tuple[Any, tuple[float, float]]] = {}
    for road in road_layout.roads:
        coordinates = list(road.centerline.coords)
        for terminal in (coordinates[0], coordinates[-1]):
            key = (
                round(float(terminal[0]), ENDPOINT_CLUSTER_DECIMALS),
                round(float(terminal[1]), ENDPOINT_CLUSTER_DECIMALS),
            )
            counts[key] = counts.get(key, 0) + 1
            owner.setdefault(key, (road, (float(terminal[0]), float(terminal[1]))))

    buildings = list(building_layout.buildings)
    threshold = TERMINAL_DISTANCE_MAX_M
    records: list[DeadEndRecord] = []
    dead_end_keys = sorted(
        key
        for key, count in counts.items()
        if count == 1
        and not _touched_by_other_road(
            Point(key[0], key[1]), owner[key][0].edge_id, road_layout
        )
    )
    dead_end_coordinates = tuple(
        (float(key[0]), float(key[1])) for key in dead_end_keys
    )
    for index, key in enumerate(dead_end_keys, start=1):
        road, coordinate = owner[key]
        point = Point(coordinate[0], coordinate[1])
        if buildings:
            nearest = min(buildings, key=lambda item: point.distance(item.footprint))
            distance = float(point.distance(nearest.footprint))
            nearest_id: str | None = nearest.building_id
        else:
            distance = None
            nearest_id = None
        if road.class_name in ACCESS_ROAD_CLASSES and distance is not None and distance <= threshold:
            classification = "group_terminal_justified"
        elif road.class_name == "main" and distance is not None and distance > MAIN_STUB_UNFINISHED_DISTANCE_M:
            classification = "main_stub_unfinished"
        else:
            classification = "unclassified"
        node_id = f"DE-{index:02d}"
        record = resolution_map.get(("id", node_id))
        if record is None:
            record = resolution_map.get(
                ("xy", (round(coordinate[0], 6), round(coordinate[1], 6)))
            )
        resolution = None if record is None else str(record.get("strategy"))
        verified = (
            False
            if record is None
            else _resolution_verified(
                record,
                road_layout,
                building_layout,
                dead_end_coordinates,
                site_boundary,
            )
        )
        records.append(
            DeadEndRecord(
                node_id=node_id,
                coordinate=coordinate,
                road_id=road.edge_id,
                road_class=road.class_name,
                nearest_building_id=nearest_id,
                distance_m=distance,
                classification=classification,
                justified=classification == "group_terminal_justified",
                resolution=resolution,
                resolved=verified,
                resolution_verified=verified,
            )
        )
    return tuple(records)


def build_road_access(
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    intent: DesignIntent,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
    site_boundary: Any | None = None,
) -> RoadAccessLayout:
    """Compute declared group access, entrance proximity and dead-end classes.

    ``site_boundary`` is the published site polygon; it is required to verify a
    ``site_edge_terminus`` dead-end resolution geometrically (Phase 0). When it is
    omitted, site-edge resolutions are reported as unverified (never as resolved).
    """
    groups: list[GroupAccess] = []
    for group in intent.groups:
        present_ids, group_union = _group_footprints(
            building_layout, group.building_ids
        )
        if not present_ids or group_union is None:
            continue
        relation = _relation_for_group(
            group.group_id, present_ids, group_union, road_layout, building_layout
        )
        served = bool(relation["served_by_relation"])
        if served:
            reason = (
                "road "
                f"{relation['access_road_id']} declares this group; terminal is "
                f"{relation['terminal_centerline_distance_m']:.3f} m from the "
                f"group footprint (band {TERMINAL_DISTANCE_MIN_M}-"
                f"{TERMINAL_DISTANCE_MAX_M} m), outside every footprint, route "
                f"crossing {relation['route_crossing_length_m']:.3f} m; "
                "corridor-edge clearance "
                f"{relation['terminal_corridor_edge_clearance_m']}"
            )
        elif relation["declared"]:
            codes = ", ".join(item["code"] for item in relation["relation_errors"])
            reason = f"declared serving relation failed validation: {codes}"
        else:
            reason = "no road declares serves_group_ids for this group"
        groups.append(
            GroupAccess(
                group_id=group.group_id,
                building_ids=present_ids,
                served=served,
                access_road_id=relation["access_road_id"],
                terminal_xy=relation["terminal_xy"],
                nearest_building_id=relation["nearest_building_id"],
                terminal_to_building_m=relation["terminal_to_building_m"],
                route_crossing_length_m=relation["route_crossing_length_m"],
                reason=reason,
                declared=bool(relation["declared"]),
                served_by_relation=bool(relation["served_by_relation"]),
                terminal_centerline_distance_m=relation[
                    "terminal_centerline_distance_m"
                ],
                terminal_corridor_edge_clearance_m=relation[
                    "terminal_corridor_edge_clearance_m"
                ],
                relation_errors=tuple(relation["relation_errors"]),
            )
        )
    known_group_ids = {group.group_id for group in groups}
    declared_by_group: dict[str, list[str]] = {}
    for road in road_layout.roads:
        for group_id in getattr(road, "serves_group_ids", ()) or ():
            declared_by_group.setdefault(group_id, []).append(road.edge_id)
    orphan_declarations = tuple(
        {
            "code": ORPHAN_DECLARED_GROUP,
            "group_id": group_id,
            "road_ids": sorted(declared_by_group[group_id]),
        }
        for group_id in sorted(declared_by_group)
        if group_id not in known_group_ids
    )
    return RoadAccessLayout(
        groups=tuple(groups),
        entrances=_entrance_access(parking_layout, road_layout),
        dead_ends=_dead_ends(
            road_layout,
            building_layout,
            basis.building_road_clearance_m,
            site_boundary,
        ),
        main_road_overlap=main_road_building_overlap(building_layout, road_layout),
        orphan_declarations=orphan_declarations,
        main_alignment_records=tuple(
            getattr(road_layout, "main_alignment_records", ()) or ()
        ),
        dead_end_resolutions=tuple(
            getattr(road_layout, "dead_end_resolutions", ()) or ()
        ),
    )


# ---------------------------------------------------------------------------
# M4d-2 candidate A — co-designed full-site access model
# ---------------------------------------------------------------------------
#
# The M4d-1 full-site layout moved the 55 buildings off the focus positions the
# frozen 44-road network was designed around.  Candidate A keeps both the fixed
# building layout and the frozen network and rebuilds each group's declared
# access as a *new* connector (``roads.rebuild_group_access``); this function
# assembles the model that consumes it: the new RoadLayout, the
# RoadAccessLayout measured from that geometry, and the evidence metrics.

CO_DESIGN_ACCESS_SCHEMA_ID = "dgcad.co-design-access.v0.1"


def build_co_design_access(
    design_input: Any,
    basis: DesignBasis,
    intent: DesignIntent,
    building_layout: BuildingLayout,
    frozen_road_layout: RoadLayout,
    *,
    route_cell_m: float | None = None,
    candidate_id: str | None = None,
) -> tuple[RoadLayout, RoadAccessLayout, dict[str, Any]]:
    """Candidate A/B model: fixed buildings + frozen 44 roads + rebuilt access.

    Returns ``(RoadLayout, RoadAccessLayout, metrics)``.  The road layout keeps
    every frozen road exactly as delivered and adds one connector per group;
    the access layout is then *measured* from that geometry with
    :func:`build_road_access`, never inferred.  Groups whose connector geometry
    cannot be built honestly stay unserved and are listed in
    ``metrics["unresolved_group_ids"]`` / ``metrics["connector_failures"]``.
    ``candidate_id`` (``"A"`` / ``"B"``) is passed through from the caller and
    echoed in both the access meta and the road-layout report; it is never
    guessed, so a candidate B model cannot be mislabelled.
    """
    road_layout, connector_report = rebuild_group_access(
        design_input,
        basis,
        intent,
        building_layout,
        frozen_road_layout,
        **({} if route_cell_m is None else {"route_cell_m": route_cell_m}),
        candidate_id=candidate_id,
    )
    parking_layout = build_parking_layout(
        design_input, intent, road_layout, basis
    )
    access_layout = build_road_access(
        building_layout,
        road_layout,
        intent,
        parking_layout,
        basis,
        site_boundary=design_input.site_boundary,
    )
    dead_end_classes: dict[str, int] = {}
    for record in access_layout.dead_ends:
        dead_end_classes[record.classification] = (
            dead_end_classes.get(record.classification, 0) + 1
        )
    buildings = {item.building_id: item for item in building_layout.buildings}
    scattered_groups: list[dict[str, Any]] = []
    for group in intent.groups:
        present = [
            buildings[building_id]
            for building_id in group.building_ids
            if building_id in buildings
        ]
        if len(present) < 2:
            continue
        span = 0.0
        for index, first in enumerate(present):
            first_point = Point(*first.design_centroid)
            for second in present[index + 1:]:
                span = max(
                    span,
                    first_point.distance(Point(*second.design_centroid)),
                )
        if span > float(basis.group_distance_m) + 1e-9:
            scattered_groups.append(
                {
                    "group_id": group.group_id,
                    "max_member_span_m": float(span),
                }
            )
    metrics: dict[str, Any] = {
        "schema_id": CO_DESIGN_ACCESS_SCHEMA_ID,
        "groups_total": access_layout.groups_total,
        "groups_served": access_layout.groups_served,
        "road_access_coverage": access_layout.road_access_coverage,
        "unserved_group_ids": list(access_layout.unserved_group_ids),
        "relation_error_count": len(access_layout.relation_errors),
        "relation_errors": [
            dict(item) for item in access_layout.relation_errors
        ],
        "dead_ends_total": len(access_layout.dead_ends),
        "dead_ends_justified": access_layout.dead_ends_justified,
        "dead_ends_unresolved": access_layout.dead_ends_unresolved,
        "dead_ends_unfinished": access_layout.dead_ends_unfinished,
        "dead_ends_resolved": access_layout.dead_ends_resolved,
        "dead_end_classifications": dict(sorted(dead_end_classes.items())),
        "dead_end_records": [
            record.to_dict() for record in access_layout.dead_ends
        ],
        "connector_count": connector_report["connector_count"],
        "connector_branch_count": connector_report["branch_count"],
        "connector_access_count": connector_report["access_count"],
        "connector_total_length_m": connector_report[
            "connector_total_length_m"
        ],
        "connectors": connector_report["connectors"],
        "relink_count": connector_report["relink_count"],
        "relink_total_length_m": connector_report[
            "relink_total_length_m"
        ],
        "relinks": connector_report["relinks"],
        "relink_failures": connector_report["relink_failures"],
        "relink_skipped": connector_report["relink_skipped"],
        "new_road_count": connector_report["new_road_count"],
        "connector_failures": connector_report["failures"],
        "unresolved_group_ids_from_connectors": connector_report[
            "unresolved_group_ids"
        ],
        "superseded_declarations": connector_report[
            "superseded_declarations"
        ],
        "frozen_road_count": connector_report["frozen_road_count"],
        "road_count": connector_report["road_count"],
        "original_roads_unchanged": connector_report[
            "original_roads_unchanged"
        ],
        "original_road_problems": connector_report[
            "original_road_problems"
        ],
        "corridor_overlap_m2": connector_report["corridor_overlap_m2"],
        "sidewalk": connector_report["sidewalk"],
        "clearance_m": connector_report["clearance_m"],
        "topology": connector_report["topology"],
        "terminal_band_m": connector_report["terminal_band_m"],
        "parking_entrance_count": len(parking_layout.entrances),
        "groups_scattered_beyond_group_distance": [
            record["group_id"] for record in scattered_groups
        ],
        "group_member_spans_m": {
            record["group_id"]: record["max_member_span_m"]
            for record in scattered_groups
        },
        "notes": [
            connector_report["clearance_m"]["note"],
            (
                "the frozen 44-road group-access declarations were superseded "
                "(metadata only) and moved to the new connectors; every frozen "
                "road keeps its id, class, width and exact centreline"
            ),
        ],
    }
    if candidate_id is not None:
        metrics["candidate_id"] = candidate_id
    if scattered_groups:
        worst = max(
            record["max_member_span_m"] for record in scattered_groups
        )
        metrics["notes"].append(
            "the M4d-1 layout scatters "
            f"{len(scattered_groups)} group(s) beyond the declared "
            f"{float(basis.group_distance_m):.0f} m group distance (largest "
            f"member-centroid span {worst:.1f} m); the declared access relation "
            "is group-level, so one connector serves the group declaration but "
            "does not physically touch every member"
        )
    if connector_report["relink_count"] or connector_report["relink_failures"]:
        metrics["relink_unresolved_group_ids"] = sorted(
            item["group_id"] for item in connector_report["relink_failures"]
        )
        metrics["notes"].append(
            f"{connector_report['relink_count']} frozen group terminal(s) are "
            "enclosed by the fixed road network and were reconnected by short "
            "new relink connectors (the frozen branches themselves are "
            "unchanged); a relink failure is reported as an unresolved dangling "
            "stub, never hidden"
        )
    return road_layout, access_layout, metrics

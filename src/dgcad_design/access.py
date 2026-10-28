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

from dataclasses import dataclass, field
from typing import Any

from shapely.geometry import Point
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .intent import DesignIntent
from .parking import ParkingLayout
from .roads import RoadLayout

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
        }


@dataclass(frozen=True)
class RoadAccessLayout:
    groups: tuple[GroupAccess, ...]
    entrances: tuple[EntranceAccess, ...]
    dead_ends: tuple[DeadEndRecord, ...]
    main_road_overlap: dict[str, Any] = field(default_factory=dict)
    orphan_declarations: tuple[dict[str, Any], ...] = ()

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
        return sum(1 for item in self.dead_ends if not item.justified)

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
            "dead_ends_justified": self.dead_ends_justified,
            "dead_ends_unfinished": self.dead_ends_unfinished,
            "dead_ends_unresolved": self.dead_ends_unresolved,
            "main_road_overlap": dict(self.main_road_overlap),
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

    Publishes the known unresolved conflict instead of hiding it: every
    main-road/building pair with more than 0.01 m2 intersection is listed.
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
        "status": MAIN_ROAD_OVERLAP_STATUS,
    }


def _entrance_access(
    parking_layout: ParkingLayout, road_layout: RoadLayout
) -> tuple[EntranceAccess, ...]:
    records: list[EntranceAccess] = []
    for entrance in parking_layout.entrances:
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
    road_layout: RoadLayout, building_layout: BuildingLayout, clearance_m: float
) -> tuple[DeadEndRecord, ...]:
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
        records.append(
            DeadEndRecord(
                node_id=f"DE-{index:02d}",
                coordinate=coordinate,
                road_id=road.edge_id,
                road_class=road.class_name,
                nearest_building_id=nearest_id,
                distance_m=distance,
                classification=classification,
                justified=classification == "group_terminal_justified",
            )
        )
    return tuple(records)


def build_road_access(
    building_layout: BuildingLayout,
    road_layout: RoadLayout,
    intent: DesignIntent,
    parking_layout: ParkingLayout,
    basis: DesignBasis,
) -> RoadAccessLayout:
    """Compute declared group access, entrance proximity and dead-end classes."""
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
            road_layout, building_layout, basis.building_road_clearance_m
        ),
        main_road_overlap=main_road_building_overlap(building_layout, road_layout),
        orphan_declarations=orphan_declarations,
    )

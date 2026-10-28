"""Design-aware road access evidence (M4c-1b).

M4c-1a proved the *road network* is connected. M4c-1b asks a different, weaker
and more honest question: is each **building group** actually reached by an
access road, is the geometry plausible (terminal next to the group, no route
cutting through a footprint), and are the remaining dead ends classified as
justified group terminals or unfinished main-road stubs?

Everything here is read-only: it consumes ``BuildingLayout``, ``RoadLayout``,
``DesignIntent``, ``ParkingLayout`` and ``DesignBasis`` and never mutates
geometry. "Access is a geometric relation, not a component count" — the noded
graph being one component says nothing about whether a group has a driveway.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point
from shapely.ops import unary_union

from .basis import DesignBasis
from .buildings import BuildingLayout
from .intent import DesignIntent
from .parking import ParkingLayout
from .roads import RoadLayout

SCHEMA_ID = "dgcad.design-road-access.v0.1"

#: Road classes that may serve a group as an access road.
ACCESS_ROAD_CLASSES = ("branch", "access")

#: Terminal is "near" a group when it is within clearance + this tolerance.
TERMINAL_DISTANCE_TOLERANCE_M = 0.5

#: A route may brush a building footprint by at most this length.
ROUTE_CROSSING_MAX_M = 0.1

#: Endpoint clustering precision (1e-9 m) for dead-end detection.
ENDPOINT_CLUSTER_DECIMALS = 9

#: A main-road stub farther than this from any building is "unfinished".
MAIN_STUB_UNFINISHED_DISTANCE_M = 10.0

#: Entrance counts as connected within half the nearest road width + this margin.
ENTRANCE_CONNECTION_MARGIN_M = 1.0

#: Distance predicate used to decide whether another centreline passes through a
#: candidate dead-end coordinate (a T-junction endpoint is not a dead end).
PASS_THROUGH_EPSILON_M = 1e-9

DEAD_END_CLASSIFICATIONS = (
    "group_terminal_justified",
    "main_stub_unfinished",
    "unclassified",
)


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

    def to_dict(self) -> dict[str, Any]:
        return {
            "group_id": self.group_id,
            "building_ids": list(self.building_ids),
            "served": self.served,
            "access_road_id": self.access_road_id,
            "terminal_xy": (
                None
                if self.terminal_xy is None
                else [float(self.terminal_xy[0]), float(self.terminal_xy[1])]
            ),
            "nearest_building_id": self.nearest_building_id,
            "terminal_to_building_m": self.terminal_to_building_m,
            "route_crossing_length_m": self.route_crossing_length_m,
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

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrance_id": self.entrance_id,
            "status": self.status,
            "point_xy": [float(self.point_xy[0]), float(self.point_xy[1])],
            "nearest_road_id": self.nearest_road_id,
            "distance_m": self.distance_m,
            "connected": self.connected,
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
    def dead_ends_justified(self) -> int:
        return sum(1 for item in self.dead_ends if item.justified)

    @property
    def dead_ends_unfinished(self) -> int:
        return sum(
            1
            for item in self.dead_ends
            if item.classification == "main_stub_unfinished"
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_id": SCHEMA_ID,
            "groups_total": self.groups_total,
            "groups_served": self.groups_served,
            "road_access_coverage": self.road_access_coverage,
            "unserved_group_ids": list(self.unserved_group_ids),
            "dead_ends_justified": self.dead_ends_justified,
            "dead_ends_unfinished": self.dead_ends_unfinished,
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


def _served_candidate(
    group_ids: tuple[str, ...],
    group_union: Any,
    road_layout: RoadLayout,
    building_layout: BuildingLayout,
    clearance_m: float,
) -> dict[str, Any] | None:
    buildings = {item.building_id: item for item in building_layout.buildings}
    threshold = clearance_m + TERMINAL_DISTANCE_TOLERANCE_M
    best: dict[str, Any] | None = None
    for road in road_layout.roads:
        if road.class_name not in ACCESS_ROAD_CLASSES:
            continue
        coordinates = list(road.centerline.coords)
        for terminal in (coordinates[0], coordinates[-1]):
            point = Point(float(terminal[0]), float(terminal[1]))
            if group_union.contains(point):
                continue  # a terminal inside a footprint is not a driveway
            distance = point.distance(group_union)
            # terminals are generated exactly at clearance + tolerance, so the
            # inclusive bound must tolerate float representation error
            if distance > threshold + PASS_THROUGH_EPSILON_M:
                continue
            crossing_m = float(road.centerline.intersection(group_union).length)
            if crossing_m > ROUTE_CROSSING_MAX_M + PASS_THROUGH_EPSILON_M:
                continue
            nearest_id = min(
                group_ids,
                key=lambda bid: point.distance(buildings[bid].footprint),
            )
            candidate = {
                "access_road_id": road.edge_id,
                "terminal_xy": (float(terminal[0]), float(terminal[1])),
                "nearest_building_id": nearest_id,
                "terminal_to_building_m": float(distance),
                "route_crossing_length_m": crossing_m,
            }
            if best is None or candidate["terminal_to_building_m"] < best["terminal_to_building_m"]:
                best = candidate
    return best


def _entrance_access(
    parking_layout: ParkingLayout, road_layout: RoadLayout
) -> tuple[EntranceAccess, ...]:
    records: list[EntranceAccess] = []
    for entrance in parking_layout.entrances:
        point = entrance.point
        if road_layout.roads:
            nearest = min(
                road_layout.roads,
                key=lambda road: point.distance(road.centerline),
            )
            distance = float(point.distance(nearest.centerline))
            limit = nearest.width_m / 2.0 + ENTRANCE_CONNECTION_MARGIN_M
            connected = distance <= limit
            if connected:
                reason = (
                    f"point is {distance:.3f} m from the nearest centreline, "
                    f"within half the {nearest.width_m:.1f} m road width + "
                    f"{ENTRANCE_CONNECTION_MARGIN_M:.1f} m"
                )
            elif entrance.status == "existing":
                reason = (
                    "designer-marked garage face; driveway connection not "
                    f"designed ({distance:.3f} m from the nearest centreline)"
                )
            else:
                reason = (
                    f"point is {distance:.3f} m from the nearest centreline, "
                    f"beyond half the {nearest.width_m:.1f} m road width + "
                    f"{ENTRANCE_CONNECTION_MARGIN_M:.1f} m"
                )
            records.append(
                EntranceAccess(
                    entrance_id=entrance.entrance_id,
                    status=entrance.status,
                    point_xy=(float(point.x), float(point.y)),
                    nearest_road_id=nearest.edge_id,
                    distance_m=distance,
                    connected=connected,
                    reason=reason,
                )
            )
        else:
            records.append(
                EntranceAccess(
                    entrance_id=entrance.entrance_id,
                    status=entrance.status,
                    point_xy=(float(point.x), float(point.y)),
                    nearest_road_id=None,
                    distance_m=None,
                    connected=False,
                    reason="no design road exists to connect the entrance",
                )
            )
    return tuple(records)


def _touched_by_other_road(
    point: Point, own_road_id: str, road_layout: RoadLayout
) -> bool:
    """True when another centreline passes through ``point`` (a T-junction).

    A road endpoint that lands on the interior of another road is a plain T
    junction after noding (degree >= 3), not a dead end. Only the endpoint count
    is not enough to tell the two apart, so the candidate coordinate is also
    checked against every other centreline at the 1e-9 endpoint tolerance.
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
    threshold = clearance_m + TERMINAL_DISTANCE_TOLERANCE_M
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
    """Compute group access, entrance connection and dead-end classification."""
    groups: list[GroupAccess] = []
    for group in intent.groups:
        present_ids, group_union = _group_footprints(
            building_layout, group.building_ids
        )
        if not present_ids or group_union is None:
            continue
        candidate = _served_candidate(
            present_ids, group_union, road_layout, building_layout,
            basis.building_road_clearance_m,
        )
        if candidate is not None:
            groups.append(
                GroupAccess(
                    group_id=group.group_id,
                    building_ids=present_ids,
                    served=True,
                    access_road_id=candidate["access_road_id"],
                    terminal_xy=candidate["terminal_xy"],
                    nearest_building_id=candidate["nearest_building_id"],
                    terminal_to_building_m=candidate["terminal_to_building_m"],
                    route_crossing_length_m=candidate["route_crossing_length_m"],
                    reason=(
                        "access-road terminal is "
                        f"{candidate['terminal_to_building_m']:.3f} m from the "
                        "group footprint (clearance + 0.5 m tolerance) and the "
                        f"route crosses the footprint by "
                        f"{candidate['route_crossing_length_m']:.3f} m"
                    ),
                )
            )
        else:
            groups.append(
                GroupAccess(
                    group_id=group.group_id,
                    building_ids=present_ids,
                    served=False,
                    access_road_id=None,
                    terminal_xy=None,
                    nearest_building_id=None,
                    terminal_to_building_m=None,
                    route_crossing_length_m=None,
                    reason=(
                        "no branch/access terminal within building-road "
                        f"clearance + {TERMINAL_DISTANCE_TOLERANCE_M} m of the "
                        "group footprint without cutting through it"
                    ),
                )
            )
    return RoadAccessLayout(
        groups=tuple(groups),
        entrances=_entrance_access(parking_layout, road_layout),
        dead_ends=_dead_ends(
            road_layout, building_layout, basis.building_road_clearance_m
        ),
    )

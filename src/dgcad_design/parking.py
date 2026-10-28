from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

from .basis import DesignBasis
from .input import DesignInput
from .intent import DesignIntent
from .roads import RoadLayout


@dataclass(frozen=True)
class ParkingEntrance:
    entrance_id: str
    point: Point
    status: str
    serves_group_id: str | None
    capacity_spaces: int
    reason: str
    footprint: Polygon | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "entrance_id": self.entrance_id,
            "point": [float(self.point.x), float(self.point.y)],
            "status": self.status,
            "serves_group_id": self.serves_group_id,
            "capacity_spaces": self.capacity_spaces,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class ParkingLayout:
    households: int
    spaces_required: int
    spaces_per_entrance: int
    entrances_required: int
    entrances: tuple[ParkingEntrance, ...]
    underground: bool
    garage_layout: str
    assumed_nominal_capacity_spaces: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "households": self.households,
            "spaces_required": self.spaces_required,
            "spaces_per_entrance": self.spaces_per_entrance,
            "entrances_required": self.entrances_required,
            "entrance_count": len(self.entrances),
            "assumed_nominal_capacity_spaces": (
                self.assumed_nominal_capacity_spaces
            ),
            "existing_entrance_count": sum(
                1 for item in self.entrances if item.status == "existing"
            ),
            "proposed_entrance_count": sum(
                1 for item in self.entrances if item.status == "proposed"
            ),
            "spaces_per_household": (
                self.spaces_required / self.households
                if self.households
                else 0.0
            ),
            "underground": self.underground,
            "garage_layout": self.garage_layout,
            "entrances": [item.to_dict() for item in self.entrances],
        }


def _entrance_point(geometry: Any) -> tuple[Point, Polygon | None]:
    """Return a Point plus the original footprint polygon when the source is one.

    The published sketch marks the garage-entrance candidates as polygons, not
    points (R18). Storing that polygon directly made ``to_dict()`` crash on
    ``.x`` and left the entrance geometry ambiguous, so existing entrances keep
    the polygon as ``footprint`` and expose a Point for connection checks.
    """
    if isinstance(geometry, Point) or geometry.geom_type == "Point":
        return geometry, None
    if geometry.geom_type == "Polygon":
        return geometry.representative_point(), geometry
    return geometry.centroid, None


def build_parking_layout(
    design_input: DesignInput,
    intent: DesignIntent,
    road_layout: RoadLayout,
    basis: DesignBasis,
) -> ParkingLayout:
    households = basis.households(design_input.staircase_count)
    spaces = basis.parking_spaces(households)
    required = basis.required_entrances(spaces)
    existing = []
    for item in design_input.entrances:
        point, footprint = _entrance_point(item.point)
        existing.append(
            ParkingEntrance(
                entrance_id=item.trace_id,
                point=point,
                status="existing",
                serves_group_id=None,
                capacity_spaces=0,
                reason="designer-marked underground garage entrance",
                footprint=footprint,
            )
        )
    main_lines = [
        road.centerline
        for road in road_layout.roads
        if road.class_name == "main"
    ]
    main_network = unary_union(main_lines) if main_lines else None
    proposed: list[ParkingEntrance] = []
    if main_network is not None and required > len(existing):
        ordered_groups = sorted(
            intent.groups, key=lambda group: -group.unit_count
        )
        for group in ordered_groups:
            if len(existing) + len(proposed) >= required:
                break
            point = main_network.interpolate(
                main_network.project(Point(group.centroid))
            )
            distances = [
                point.distance(item.point)
                for item in existing + proposed
            ]
            if distances and min(distances) < 60.0:
                continue
            proposed.append(
                ParkingEntrance(
                    entrance_id=f"GARAGE-ENTRANCE-P{len(proposed) + 1:02d}",
                    point=point,
                    status="proposed",
                    serves_group_id=group.group_id,
                    capacity_spaces=basis.spaces_per_entrance,
                    reason=(
                        "declared 1 space/household and "
                        f"{basis.spaces_per_entrance} spaces/entrance; "
                        "placed on the main road near the group"
                    ),
                )
            )
    entrances = existing + proposed
    return ParkingLayout(
        households=households,
        spaces_required=spaces,
        spaces_per_entrance=basis.spaces_per_entrance,
        entrances_required=required,
        entrances=tuple(entrances),
        underground=True,
        garage_layout="not_designed",
        assumed_nominal_capacity_spaces=sum(
            item.capacity_spaces for item in entrances
        ),
    )

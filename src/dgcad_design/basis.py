from __future__ import annotations

import math
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


#: Allowed authority classes for a design-basis parameter. The Agent may choose
#: values under ``agent_assumption`` but may never mark them confirmed; only a
#: human supplies ``declared_requirement`` confirmation or promotes a value.
PARAMETER_AUTHORITIES = (
    "declared_requirement",
    "designer_stated",
    "inferred_from_sketch",
    "agent_assumption",
    "project_condition",
)

#: The 21 design parameters that must each declare provenance. This tuple is the
#: single source of truth for ``parameter_sources`` completeness and is asserted
#: against the fixture and the contract by tests.
PARAMETER_SOURCE_KEYS = (
    "households_per_staircase_per_floor",
    "floors",
    "floor_height_m",
    "staircase_width_m",
    "staircase_depth_m",
    "dwelling_gfa_m2",
    "facility_gfa_m2",
    "far_min",
    "far_max",
    "parking_spaces_per_household",
    "spaces_per_entrance",
    "north_south_spacing_m",
    "side_spacing_m",
    "boundary_setback_m",
    "building_road_clearance_m",
    "green_ratio_min",
    "road_widths",
    "sidewalk_width_m",
    "group_distance_m",
    "scale_px_per_m",
    "origin_px",
)


@dataclass(frozen=True)
class DesignBasis:
    basis_id: str
    version: str
    case_id: str
    households_per_staircase_per_floor: int
    floors: int
    floor_height_m: float
    staircase_width_m: float
    staircase_depth_m: float
    dwelling_gfa_m2: float
    facility_gfa_m2: float
    far_min: float
    far_max: float
    parking_spaces_per_household: float
    spaces_per_entrance: int
    north_south_spacing_m: float
    side_spacing_m: float
    boundary_setback_m: float
    building_road_clearance_m: float
    green_ratio_min: float
    road_widths: dict[str, float]
    sidewalk_width_m: float
    group_distance_m: float
    scale_px_per_m: float
    origin_px: tuple[float, float]
    target_frame: str
    drawing_standard: str
    claim_scope: str
    design_authority: str = "rule_derived"
    human_confirmed: bool = False
    parameter_sources: dict[str, dict[str, Any]] = field(
        default_factory=dict
    )

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "DesignBasis":
        road_widths = {
            str(key): float(value)
            for key, value in data["road_widths"].items()
        }
        origin = tuple(float(value) for value in data["origin_px"])
        if "parameter_sources" not in data:
            raise ValueError(
                "parameter_sources is required: every basis parameter must "
                "declare source, authority and confirmation state"
            )
        raw_sources = data["parameter_sources"]
        if not isinstance(raw_sources, dict):
            raise ValueError("parameter_sources must be a mapping")
        parameter_sources: dict[str, dict[str, Any]] = {}
        for key, entry in raw_sources.items():
            if not isinstance(entry, dict):
                raise ValueError(
                    f"parameter_sources[{key!r}] must be a mapping with "
                    "source, authority and confirmed"
                )
            parameter_sources[str(key)] = dict(entry)
        basis = cls(
            basis_id=str(data["basis_id"]),
            version=str(data["version"]),
            case_id=str(data["case_id"]),
            households_per_staircase_per_floor=int(
                data["households_per_staircase_per_floor"]
            ),
            floors=int(data["floors"]),
            floor_height_m=float(data["floor_height_m"]),
            staircase_width_m=float(data["staircase_width_m"]),
            staircase_depth_m=float(data["staircase_depth_m"]),
            dwelling_gfa_m2=float(data["dwelling_gfa_m2"]),
            facility_gfa_m2=float(data["facility_gfa_m2"]),
            far_min=float(data["far_min"]),
            far_max=float(data["far_max"]),
            parking_spaces_per_household=float(
                data["parking_spaces_per_household"]
            ),
            spaces_per_entrance=int(data["spaces_per_entrance"]),
            north_south_spacing_m=float(data["north_south_spacing_m"]),
            side_spacing_m=float(data["side_spacing_m"]),
            boundary_setback_m=float(data["boundary_setback_m"]),
            building_road_clearance_m=float(
                data["building_road_clearance_m"]
            ),
            green_ratio_min=float(data["green_ratio_min"]),
            road_widths=road_widths,
            sidewalk_width_m=float(data["sidewalk_width_m"]),
            group_distance_m=float(data["group_distance_m"]),
            scale_px_per_m=float(data["scale_px_per_m"]),
            origin_px=(origin[0], origin[1]),
            target_frame=str(data["target_frame"]),
            drawing_standard=str(data["drawing_standard"]),
            claim_scope=str(data["claim_scope"]),
            design_authority=str(
                data.get("design_authority", "rule_derived")
            ),
            human_confirmed=bool(data.get("human_confirmed", False)),
            parameter_sources=parameter_sources,
        )
        basis.validate()
        return basis

    @classmethod
    def load(cls, path: str) -> "DesignBasis":
        return cls.from_dict(
            yaml.safe_load(Path(path).read_text(encoding="utf-8"))
        )

    def validate(self) -> None:
        if self.households_per_staircase_per_floor < 1:
            raise ValueError("households_per_staircase_per_floor must be >= 1")
        if self.floors < 1:
            raise ValueError("floors must be >= 1")
        if self.floor_height_m <= 0:
            raise ValueError("floor_height_m must be positive")
        if self.staircase_width_m <= 0 or self.staircase_depth_m <= 0:
            raise ValueError("staircase dimensions must be positive")
        if self.dwelling_gfa_m2 <= 0:
            raise ValueError("dwelling_gfa_m2 must be positive")
        floorplate = (
            self.households_per_staircase_per_floor * self.dwelling_gfa_m2
        )
        module = self.staircase_width_m * self.staircase_depth_m
        if abs(floorplate - module) > 1e-6:
            raise ValueError(
                "households x dwelling_gfa must equal the staircase module "
                f"area: {floorplate} != {module}"
            )
        if not (0 < self.far_min <= self.far_max):
            raise ValueError("invalid FAR range")
        if self.parking_spaces_per_household < 1.0:
            raise ValueError(
                "parking_spaces_per_household must be at least 1.0"
            )
        if self.spaces_per_entrance < 1:
            raise ValueError("spaces_per_entrance must be >= 1")
        if self.north_south_spacing_m < 20.0:
            raise ValueError("north_south_spacing_m must be at least 20 m")
        if self.boundary_setback_m < 0:
            raise ValueError("boundary_setback_m must be non-negative")
        if self.green_ratio_min <= 0 or self.green_ratio_min > 1:
            raise ValueError("green_ratio_min must be in (0, 1]")
        for name, width in self.road_widths.items():
            if width <= 0:
                raise ValueError(f"road width {name} must be positive")
        if self.human_confirmed:
            raise ValueError(
                "an autonomous design basis cannot be human_confirmed"
            )
        if self.design_authority != "rule_derived":
            raise ValueError(
                "an autonomous design basis must be rule_derived"
            )
        self._validate_parameter_sources()

    def _validate_parameter_sources(self) -> None:
        """Enforce per-parameter provenance and the Agent self-confirmation ban."""
        sources = self.parameter_sources
        if not isinstance(sources, dict):
            raise ValueError("parameter_sources must be a mapping")
        missing = [
            key for key in PARAMETER_SOURCE_KEYS if key not in sources
        ]
        if missing:
            raise ValueError(
                "parameter_sources is missing declared parameters: "
                + ", ".join(missing)
            )
        for key, entry in sources.items():
            if not isinstance(entry, dict):
                raise ValueError(
                    f"parameter_sources[{key!r}] must be a mapping"
                )
            for required in ("source", "authority", "confirmed"):
                if required not in entry:
                    raise ValueError(
                        f"parameter_sources[{key!r}] is missing {required!r}"
                    )
            source = entry["source"]
            if not isinstance(source, str) or not source.strip():
                raise ValueError(
                    f"parameter_sources[{key!r}].source must be a non-empty "
                    "string"
                )
            authority = entry["authority"]
            if authority not in PARAMETER_AUTHORITIES:
                raise ValueError(
                    f"parameter_sources[{key!r}].authority {authority!r} is "
                    "not one of " + ", ".join(PARAMETER_AUTHORITIES)
                )
            if not isinstance(entry["confirmed"], bool):
                raise ValueError(
                    f"parameter_sources[{key!r}].confirmed must be a bool"
                )
            if authority == "agent_assumption" and entry["confirmed"]:
                raise ValueError(
                    f"parameter_sources[{key!r}]: an agent_assumption cannot "
                    "be confirmed; the Agent may not self-confirm a parameter"
                )

    @property
    def building_width_for_units(self) -> dict[int, float]:
        return {
            units: units * self.staircase_width_m
            for units in (1, 2, 3)
        }

    def building_width(self, unit_count: int) -> float:
        return unit_count * self.staircase_width_m

    def households(self, staircases: int) -> int:
        return (
            staircases
            * self.households_per_staircase_per_floor
            * self.floors
        )

    def residential_gfa(self, staircases: int) -> float:
        return (
            staircases
            * self.households_per_staircase_per_floor
            * self.dwelling_gfa_m2
            * self.floors
        )

    def total_gfa(self, staircases: int) -> float:
        return self.residential_gfa(staircases) + self.facility_gfa_m2

    def far(self, site_area_m2: float, staircases: int) -> float:
        if site_area_m2 <= 0:
            raise ValueError("site area must be positive")
        return self.total_gfa(staircases) / site_area_m2

    def far_ok(self, site_area_m2: float, staircases: int) -> bool:
        value = self.far(site_area_m2, staircases)
        return self.far_min <= value <= self.far_max

    def parking_spaces(self, households: int) -> int:
        return math.ceil(
            households * self.parking_spaces_per_household
        )

    def required_entrances(self, spaces: int) -> int:
        return math.ceil(spaces / self.spaces_per_entrance)

    def building_height_m(self) -> float:
        return self.floors * self.floor_height_m

    def to_dict(self) -> dict[str, Any]:
        return {
            "basis_id": self.basis_id,
            "version": self.version,
            "case_id": self.case_id,
            "households_per_staircase_per_floor": (
                self.households_per_staircase_per_floor
            ),
            "floors": self.floors,
            "floor_height_m": self.floor_height_m,
            "staircase_width_m": self.staircase_width_m,
            "staircase_depth_m": self.staircase_depth_m,
            "dwelling_gfa_m2": self.dwelling_gfa_m2,
            "facility_gfa_m2": self.facility_gfa_m2,
            "far_min": self.far_min,
            "far_max": self.far_max,
            "parking_spaces_per_household": (
                self.parking_spaces_per_household
            ),
            "spaces_per_entrance": self.spaces_per_entrance,
            "north_south_spacing_m": self.north_south_spacing_m,
            "side_spacing_m": self.side_spacing_m,
            "boundary_setback_m": self.boundary_setback_m,
            "building_road_clearance_m": self.building_road_clearance_m,
            "green_ratio_min": self.green_ratio_min,
            "road_widths": dict(self.road_widths),
            "sidewalk_width_m": self.sidewalk_width_m,
            "group_distance_m": self.group_distance_m,
            "scale_px_per_m": self.scale_px_per_m,
            "origin_px": list(self.origin_px),
            "target_frame": self.target_frame,
            "drawing_standard": self.drawing_standard,
            "claim_scope": self.claim_scope,
            "design_authority": self.design_authority,
            "human_confirmed": self.human_confirmed,
            "parameter_sources": {
                key: dict(value)
                for key, value in sorted(self.parameter_sources.items())
            },
        }

    def provenance(self) -> dict[str, Any]:
        """Machine-readable provenance summary for evidence and summaries.

        Reports every parameter's source/authority/confirmation state plus
        aggregate counts, so a reader can see which values are Agent
        assumptions and which are still unconfirmed.
        """
        counts: dict[str, int] = {}
        for entry in self.parameter_sources.values():
            authority = entry["authority"]
            counts[authority] = counts.get(authority, 0) + 1
        unconfirmed = sorted(
            key
            for key, entry in self.parameter_sources.items()
            if not entry["confirmed"]
        )
        agent_assumptions = sorted(
            key
            for key, entry in self.parameter_sources.items()
            if entry["authority"] == "agent_assumption"
        )
        confirmed = sorted(
            key
            for key, entry in self.parameter_sources.items()
            if entry["confirmed"]
        )
        return {
            "basis_id": self.basis_id,
            "version": self.version,
            "case_id": self.case_id,
            "human_confirmed": self.human_confirmed,
            "design_authority": self.design_authority,
            "parameters": {
                key: dict(value)
                for key, value in sorted(self.parameter_sources.items())
            },
            "authority_counts": dict(sorted(counts.items())),
            "unconfirmed_parameters": unconfirmed,
            "confirmed_parameters": confirmed,
            "agent_assumption_parameters": agent_assumptions,
            "all_parameters_confirmed": bool(
                self.parameter_sources and not unconfirmed
            ),
        }

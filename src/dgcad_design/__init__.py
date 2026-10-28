"""Autonomous design synthesis: intent, draft, geometry and standardized CAD."""

from .basis import DesignBasis
from .buildings import BuildingLayout, StandardBuilding
from .consistency import DesignConsistency
from .input import DesignInput, load_design_input
from .intent import DesignIntent, build_design_intent
from .project import DesignSynthesisBlocked, run_design_synthesis
from .scene import DesignElement, design_scene

__all__ = [
    "BuildingLayout",
    "DesignBasis",
    "DesignConsistency",
    "DesignElement",
    "DesignInput",
    "DesignIntent",
    "DesignSynthesisBlocked",
    "StandardBuilding",
    "build_design_intent",
    "design_scene",
    "load_design_input",
    "run_design_synthesis",
]

"""Synthetic environment-analysis baseline for the living E2E slice."""

from .solar import (
    COVERAGE_LIMITS,
    METHOD_ID,
    METHOD_VERSION,
    ShadowAnalysisResult,
    ShadowBlocker,
    ShadowConfig,
    ShadowSample,
    ShadowSampleResult,
    SolarPosition,
    blockers_from_scene,
    evaluate_sample,
    run_shadow_baseline,
    solar_position_noaa,
    sun_vector_project,
)

__all__ = [
    "COVERAGE_LIMITS",
    "METHOD_ID",
    "METHOD_VERSION",
    "ShadowAnalysisResult",
    "ShadowBlocker",
    "ShadowConfig",
    "ShadowSample",
    "ShadowSampleResult",
    "SolarPosition",
    "blockers_from_scene",
    "evaluate_sample",
    "run_shadow_baseline",
    "solar_position_noaa",
    "sun_vector_project",
]

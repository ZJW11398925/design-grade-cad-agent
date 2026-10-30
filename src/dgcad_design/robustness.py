"""Geometric robustness of the declared road-corridor clearance.

M4d-2a asks a bounded question: the candidate-B minimum clearance is
3.0164672267820585 m, only 0.016 m above the 3.0 m rule.  The source sketch
registration has a mean homography residual of 24.51 px (max 43.42 px) at
2.438 px/m, i.e. a ~10 m order of magnitude.  This module perturbs the
generated geometry deterministically and reports how the clearance margin
behaves; it never changes the 3.0 m threshold and never turns the result into
a pass/fail gate.
"""
from __future__ import annotations

import random
from typing import Any, Iterable

from shapely.affinity import translate
from shapely.geometry.base import BaseGeometry

DEFAULT_DELTAS_M = (0.0, 0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.0, 5.0, 10.0)
DEFAULT_SAMPLES = 24

MODES = (
    "common_datum",       # all geometry translated together: control
    "buildings_only",     # each building translated independently
    "buildings_and_roads",  # buildings independent + corridor union independent
)


def _min_clearance(
    buildings: Iterable[BaseGeometry], corridor: BaseGeometry
) -> float:
    best = float("inf")
    for footprint in buildings:
        distance = float(footprint.distance(corridor))
        if distance < best:
            best = distance
    return best


def clearance_sensitivity(
    building_footprints: Iterable[BaseGeometry],
    corridor_union: BaseGeometry,
    *,
    deltas_m: Iterable[float] = DEFAULT_DELTAS_M,
    samples: int = DEFAULT_SAMPLES,
    seed: int = 20261030,
) -> dict[str, Any]:
    """Report clearance distribution under independent coordinate jitter.

    ``deltas_m`` are maximum absolute translations per axis (uniform).  The
    returned values are descriptive; there is no pass/fail field.
    """

    footprints = [item for item in building_footprints if not item.is_empty]
    if not footprints:
        raise ValueError("no building footprints to perturb")
    rows: list[dict[str, Any]] = []
    for delta in deltas_m:
        for mode in MODES:
            rng = random.Random(seed + int(round(delta * 1000)))
            values: list[float] = []
            for _ in range(samples):
                if mode == "common_datum":
                    dx = rng.uniform(-delta, delta) if delta else 0.0
                    dy = rng.uniform(-delta, delta) if delta else 0.0
                    shifted_buildings = [
                        translate(item, xoff=dx, yoff=dy) for item in footprints
                    ]
                    shifted_corridor = translate(
                        corridor_union, xoff=dx, yoff=dy
                    )
                else:
                    shifted_buildings = [
                        translate(
                            item,
                            xoff=rng.uniform(-delta, delta),
                            yoff=rng.uniform(-delta, delta),
                        )
                        for item in footprints
                    ]
                    if mode == "buildings_only":
                        shifted_corridor = corridor_union
                    else:
                        shifted_corridor = translate(
                            corridor_union,
                            xoff=rng.uniform(-delta, delta),
                            yoff=rng.uniform(-delta, delta),
                        )
                values.append(
                    _min_clearance(shifted_buildings, shifted_corridor)
                )
            values.sort()
            count = len(values)
            below_3 = sum(1 for value in values if value < 3.0)
            below_baseline = sum(
                1 for value in values if value < 3.0164672267820585
            )
            rows.append(
                {
                    "max_translation_m": delta,
                    "mode": mode,
                    "samples": count,
                    "min_m": values[0],
                    "p05_m": values[max(0, int(round(0.05 * (count - 1))))],
                    "median_m": values[count // 2],
                    "max_m": values[-1],
                    "fraction_below_3_0_m": below_3 / count,
                    "fraction_below_baseline_clearance": (
                        below_baseline / count
                    ),
                }
            )
    return {
        "schema_id": "dgcad.clearance-sensitivity.v0.1",
        "declared_rule_m": 3.0,
        "baseline_clearance_m": 3.0164672267820585,
        "deltas_m": list(deltas_m),
        "samples_per_delta_mode": samples,
        "seed": seed,
        "modes": list(MODES),
        "rows": rows,
        "note": (
            "descriptive sensitivity only; the 3.0 m rule is unchanged and no "
            "row is a pass/fail gate.  Translation magnitude is not a "
            "calibrated survey error; it probes the order of magnitude of the "
            "source registration residual."
        ),
    }

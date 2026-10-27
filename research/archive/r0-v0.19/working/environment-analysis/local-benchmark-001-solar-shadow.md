# LOCAL-ENV-001 — Solar position, geometric shadow and dependency invalidation

**Run:** `RUN-005-01`  
**Date:** 2026-10-26  
**Status:** `passed_with_scope_limits`  
**Evidence class:** local synthetic benchmark + cross-check against a published implementation example. Not a professional simulation validation or a regulatory compliance result.

## 1. What was executed

A local deterministic probe was implemented with Python's standard library and Shapely 2.1.2. It contains:

1. a low-precision NOAA fractional-year solar-position calculation for offset-aware timestamps;
2. conversion from true-north solar azimuth to a declared local project coordinate frame;
3. geometric ray-segment intersection against vertical-prism building footprints;
4. tri-state sun visibility (`sunlit`, `shaded`, `unknown`) so missing heights/context cannot be silently promoted to a confirmed answer;
5. a canonical JSON SHA-256 dependency fingerprint so changes to footprint/body/height/placement/terrain/north/time/method/context can invalidate prior results;
6. sampled direct-sun-hour bounds, where unknown samples widen the possible interval instead of being counted as sunlit.

## 2. Results

| Check | Result | Interpretation |
|---|---|---|
| Local assertion functions | 17 passed / 0 failed | Includes timezone/timestamp validation, coordinate bounds, unit solar vector, known/estimated/unknown blockers, explicit north, irregular/empty time samples, finite-height checks, staleness and deterministic hashing. |
| Solar position cross-check | Pass within 0.5° tolerance | Sydney, 15 Nov 11:00 +10:00, latitude −33.87°, longitude 151.22°: local approximation 72.0467° altitude / 32.3093° azimuth; Ladybug published example 72.26° / 32.37°. Absolute differences 0.2133° / 0.0607°. |
| Tall confirmed blocker | `confirmed_shaded` | 6 m obstacle reaches the ray for a synthetic 45° altitude / eastward sun. |
| Short confirmed blocker | `confirmed_sunlit_given_declared_context` | 2 m obstacle does not reach that sensor ray in the same analytic case. |
| Unknown-height blocker | `unknown_obstruction_height` | The result is not silently reported as sunlit. |
| Estimated-height blocker | `estimated_height_affects_result` | Even a short estimate cannot confirm sunlit if the footprint is on the sunward ray. |
| Missing north bearing | Rejected | Daytime geometry requires an explicit project +Y true-north bearing; no default north is silently assumed. |
| Irregular time samples | Rejected | Sample intervals must match the declared timestep in UTC elapsed time. |
| Missing surrounding context | `incomplete_surrounding_context` | The result is not confirmed even if no supplied blocker intersects. |
| North rotation | Pass | Changing the project's +Y true-north bearing rotates the local sun vector and changes which local obstruction can shade the sensor. |
| Height revision change | Stale | Changing `height_revision` changes the dependency fingerprint and invalidates the old result. |
| Sampled direct sun hours with unknown obstruction | 0.0–2.0 hours; `bounded_or_unknown` | Two unknown samples are not counted as confirmed sunlight. This is a deliberate uncertainty test, not a meaningful site estimate. |

Machine-readable output: `local-benchmark-001-solar-shadow.json`.

## 3. Independent reference and its limit

Ladybug's official repository README and tests publish a Sydney solar-position example and state that their tests compare solar positions with NOAA formulas. The local low-precision implementation is checked against the published values with a stated 0.5° tolerance. NREL's SPA report and pvlib's `spa_python` API are recorded as a stronger independent reference route.

This is a **sanity cross-check only**: the exact year is abstracted in Ladybug's README example, the local formula is low-precision, and neither pvlib nor Ladybug could be installed/run in this sandbox because DNS/network access was unavailable. No claim is made that this test establishes survey-grade solar position or production simulation accuracy.

## 4. Important model assumptions / limitations

- Local geometry is planar metric XY with Z up; the default project +Y axis points to true north. The coordinate convention and north bearing must be explicitly supplied.
- Blockers are opaque vertical prisms with constant footprint and base elevation. Sloped terrain, sloping roofs, facade apertures, balconies, transparent materials, reflections, atmospheric refraction and complex mesh intersection are outside this probe.
- The sun-position function requires a timezone-aware timestamp with UTC offset. It does not infer the site's timezone, DST rules, geodetic datum or coordinate transformation.
- `context_complete=true` means complete only for the declared benchmark scene. Real-world completeness must be tied to a boundary, source date and source data inventory.
- The direct-sun-hours result is a discrete-time geometric visibility count. It is not weather-weighted annual daylight, illuminance, radiation, energy use, or a legal sunlight-hours determination.
- The test functions passed when directly invoked. In this sandbox, the pytest CLI did not terminate cleanly before timeout; the normal test runner should be rechecked in a clean runtime. This is an execution-environment caveat, not evidence of a failing assertion.

## 5. Gate conclusion

`LOCAL-ENV-001` supports a narrow claim: a low-dependency geometric baseline can expose critical input uncertainty and stale results in a reproducible synthetic test. It does **not** select Ladybug/Honeybee/pvlib as the final stack, validate annual simulation accuracy, or establish planning-code compliance.

Next evidence needed before any production claim:

1. run the same fixed fixtures with pvlib or Ladybug solar position and compare outputs over solstice/equinox, morning/noon/evening and both hemispheres;
2. run an independent 3D engine (e.g. Honeybee-Radiance/Radiance) on a minimal fixed model and compare sensor sun-visibility results under matching timestep/north/context;
3. test non-flat terrain, non-zero base elevation, concave footprints, holes, overlapping blockers and coordinate-frame transformations;
4. validate result invalidation after real Footprint/Body/Height/Placement revisions in the upstream object model;
5. only then investigate jurisdiction-specific solar-access thresholds, using verified current primary standards and their precise scope.

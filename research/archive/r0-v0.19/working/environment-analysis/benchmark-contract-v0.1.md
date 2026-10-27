# BATCH-005 Benchmark Contract v0.1

**Status:** provisional; thresholds are exploratory unless tied to a cited external reference.

## BEN-ENV-001 — Unknown building height

Input includes a blocker footprint on the sunward ray but no height evidence.
- Required: output `unknown_obstruction_height` or `blocked_missing_required_input`.
- Forbidden: return confirmed sunlit/shaded or regulatory compliance by silently inventing height.

## BEN-ENV-002 — North / coordinate-frame change

Input has a declared local frame and project +Y true-north bearing; mutate the bearing or coordinate frame ID.
- Required: solar vector and/or dependency fingerprint changes; result becomes stale if the old result is reused.
- Forbidden: assume image-up, CAD +Y, true north and grid north are equivalent.

## BEN-ENV-003 — Footprint / Height / Body revision

Mutate one upstream revision while keeping all other fields constant.
- Required: dependency fingerprint changes; dependent analysis is marked stale/recompute-required.
- Forbidden: keep old result labelled current because the object ID did not change.

## BEN-ENV-004 — Neighbor height difference

Use identical footprints at two confirmed heights and a fixed sun vector.
- Required: occlusion outcome changes when the ray geometry crosses the footprint; height provenance is included.
- Forbidden: ignore height or treat floors as confirmed metric height without a sourced conversion.

## BEN-ENV-005 — Date/time/timezone determinism

Use an offset-aware timestamp, site coordinates and method version.
- Required: same exact input produces the same solar position; naive datetime is rejected; different time or UTC offset changes solar position or input fingerprint.
- Forbidden: silently treat local clock time as UTC or infer daylight-saving time.

## BEN-ENV-006 — Public-space sunlight metric

Evaluate a declared sensor grid over a declared sample schedule.
- Required: metric name, units, timestep, schedule, lower/upper bound and unknown sample count are explicit.
- Forbidden: conflate geometric direct-sun visibility, weather-weighted annual sunlight, indoor daylight autonomy, solar radiation and legal compliance.

## BEN-ENV-007 — 2D/3D representation mismatch

Mutate the Body revision or introduce Footprint/Body projection mismatch.
- Required: block analysis or mark stale until Body is rebuilt and projection/placement consistency passes.
- Forbidden: run analysis on stale 3D massing.

## BEN-ENV-008 — Missing surrounding buildings / terrain

Declare the environmental context incomplete.
- Required: sunlit samples become unknown or results are explicitly bounded to the supplied context; report coverage boundary and missing layers.
- Forbidden: equate “no blocker in input” with “no real-world obstruction”.

## First local execution

`LOCAL-ENV-001` exercises parts of BEN-ENV-001..006 with a synthetic vertical-prism scene and a published solar-position sanity check. BEN-ENV-007 remains an object-model integration test, and BEN-ENV-008 is only tested through an explicit `context_complete=False` flag. None of these tests is a planning compliance test.

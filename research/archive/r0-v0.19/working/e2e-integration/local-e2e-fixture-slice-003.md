# E2E-FIXTURE-001 — Local Vertical Slice v0.3

**Status:** `passed_with_scope_limits` for the synthetic contract slice.  
**Source fixture:** `site-fixture-v0.2.json` (`fixture_revision: r2`, retained unchanged).  
**Adapter/Profile revision:** 0.3.0.  
**Not a production or compliance approval.**

## What changed after the isolated review of v0.2

The review of v0.2 reproduced four hard false-accepts and identified several unexpressed Profile policies. The v0.3 adapter uses a versioned synthetic Profile and a separate validator revision. The old v0.2 files remain as historical evidence.

- DXF validation now rejects any entity in non-modelspace layouts under the declared `modelspace_only` policy.
- The layer table is constrained to the declared layer set plus allowed system layers `0` and `Defpoints`.
- Plan geometry must lie at Z=0 with world-XY extrusion. Polyline elevation, circle center Z, text insertion/alignment Z and extrusion are checked.
- Entity graphics must inherit layer style (`BYLAYER`); explicit color, linetype, lineweight, true-color and transparency overrides are rejected by this synthetic Profile.
- Text style, rotation, width factor, alignment and height are part of the declared representation contract.
- Solar zenith is handled explicitly rather than returning `invalid_solar_vector` for a vertical sun ray.
- Boolean values are rejected as metric values/coordinates, despite Python's `bool` being a subclass of `int`.
- `sampled_direct_sun_hours()` now requires an explicit `interval_convention`: `timestamp_starts_interval` or `timestamp_is_instant`, and returns interval count and covered time bounds.

## Reproduced results

- Existing v0.2 solar tests + new v0.3 solar tests: **44 passed**.
- New v0.3 DXF validator regression tests: **12 passed**.
- Environment fixture: **3/3 sensor outcomes**, **2/2 stored-body checks** passed.
- Dependency invalidation controls: unchanged manifest remains current; all 13 declared dependency mutations stale the prior result.
- DXF: **8 object IDs**, **11 modelspace entities**, **0 audit errors**, **0 audit fixes**.
- DXF mutation regressions reject paper-space entities, nonzero Z/elevation, entity style overrides, text rotation and undeclared extra layers.
- The synthetic Profile ID/version must match the CAD-IR export target; a mismatched Profile reference is not accepted.

## Executable artifacts

- `synthetic-dxf-profile-v0.3.json`
- `dxf_validator_v0_3.py`
- `compile_fixture_to_dxf_v0_3.py`
- `fixture_to_cad_ir_v0_3.py`
- `run_fixture_benchmark_v0_3.py`
- `site-fixture-cad-ir-v0.3.json`
- `local-e2e-fixture-env-003.json`
- `site-fixture-v0.3.dxf`
- `site-fixture-v0.3-dxf-manifest.json`
- `test_dxf_validator_v0_3.py`
- `../environment-analysis/solar_shadow_v0_3.py`
- `../environment-analysis/test_solar_shadow_v0_3.py`

## Remaining limits

This is still a synthetic, modelspace-only, 2D DXF test slice. It does not contain a real raster-to-Trace run, professional road design, a real design-office Profile, IFC output, a third-party CAD application round-trip, or an independent solar simulation engine. It does not certify geometry from real input, architectural/urban-design correctness, standard compliance or legal compliance. The v0.3 Profile is a test contract, not a national or design-office standard.

## Next gate

Submit the immutable v0.3 review packet to a reviewer who did not author the implementation, then run a separate CAD application open/save/re-read test. The current in-thread review and local tests do not satisfy external review or A1.

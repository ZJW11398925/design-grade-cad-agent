# E2E-FIXTURE-001 — shared synthetic vertical slice

The active v0.3 adapter/profile is a bounded synthetic test, not a real design workflow.

## Immutable history

- v0.1 and v0.2 fixture/artifact files remain as historical evidence.
- `reviews/independent-review-report-v0.3.md` documents an isolated second-pass review of the v0.2 packet. Its disposition is `conditional`; it is not external sign-off.
- `local-e2e-fixture-slice-003.md` documents the bounded v0.3 fixes and test results.

## Reproduce v0.3

From the workspace root, in an environment with `shapely`, `ezdxf` and `pytest` installed:

```bash
python -m pytest working/environment-analysis/test_solar_shadow.py working/environment-analysis/test_solar_shadow_v0_3.py working/e2e-integration/test_dxf_validator_v0_3.py -q
python working/e2e-integration/run_fixture_benchmark_v0_3.py
python working/e2e-integration/fixture_to_cad_ir_v0_3.py
python working/e2e-integration/compile_fixture_to_dxf_v0_3.py
```

The v0.3 validator enforces the versioned `synthetic-dxf-profile-v0.3.json`: R2010, metre units, a declared layer allowlist, BYLAYER entity styling, modelspace-only content and a Z=0 plan plane. These are synthetic test rules, not a professional design standard.

## Current state

Local regression tests pass, but `external_review_completed=false`. A reviewer who did not author the implementation and a third-party CAD application round-trip are still required. The slice does not include real raster-to-Trace, professional road generation, IFC, an independent solar engine, or domain/regulatory compliance.

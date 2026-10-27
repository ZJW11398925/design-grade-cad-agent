# External Review Checklist — E2E-FIXTURE-001 R2

**Status:** awaiting a reviewer who did not author this fixture. Do not mark this checklist complete from the same authoring thread alone.

## Review artifacts

1. `site-fixture-v0.2.json` and `site-fixture-contract-v0.2.md`
2. `site-fixture-cad-ir-v0.2.json` and `cad-ir-contract-v0.1.yaml`
3. `run_fixture_benchmark_v0_2.py`, `solar_shadow.py`, `local-e2e-fixture-env-002.json`
4. `compile_fixture_to_dxf_v0_2.py`, `dxf_validator.py`, `site-fixture-v0.2.dxf`, `site-fixture-v0.2-dxf-manifest.json`
5. `run_adversarial_review.py`, `adversarial-review-results-v0.2.json`
6. `local-e2e-fixture-slice-002.md` and `adversarial-review-report-v0.1.md`
7. `analysis-dependency-contract-v0.1.yaml`, `environment-analysis-result-schema-v0.1.yaml`, `trace-object-schema-v0.1.yaml`

## Required independent checks

- Verify manifest hashes before inspecting artifacts.
- Re-run environment tests and base fixture. Confirm unknown height is never promoted and result status is tied to exact geometry/massing/context/method inputs.
- Mutate height value/state/base elevation/body geometry without revision bumps. Confirm fingerprint changes and inconsistent body geometry fails closed.
- Inspect the stored synthetic prism mesh; confirm top/bottom projections are derived from mesh coordinates, not copied from footprint data.
- Add an interior ring and confirm it is exported with `ring_role=hole`; confirm the report does not overclaim filled-region semantics.
- Alter DXF layer properties, INSUNITS, text, a polyline vertex, and add an untagged entity. Confirm the validator rejects each mutation.
- Check that source geometry hash and exported representation hash are distinct concepts and that point Z is not silently claimed as exported in 2D DXF.
- State any false-positive/false-negative risks and whether the test suite would catch them.

## Required response

Return `review_status`: `pass_for_next_experiment`, `conditional`, or `fail`; list findings with severity, reproduction, expected/observed behavior, required changes and remaining limits.

## Prohibited inferences

Do not claim a complete Sketch → Professional Site Model → CAD/BIM pipeline; do not claim real-site accuracy, third-party CAD compatibility, IFC correctness, professional-design correctness, or legal compliance. Do not promote this review to project A1/production approval. A DXF file passing the same-library validator is not an independent CAD round-trip.

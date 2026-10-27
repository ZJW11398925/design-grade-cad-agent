# R0 v0.9 Workspace Snapshot

**Date:** 2026-10-27  
**Status:** research workspace snapshot; not a production release.

## What changed from v0.8

The shared E2E fixture has been versioned correctly: v0.1 remains immutable historical evidence; v0.2 uses `fixture_revision: r2` and new filenames. The active slice now includes an explicit synthetic prism mesh, more complete dependency fingerprints, a separate DXF artifact validator, tagged polygon/multipolygon rings, and adversarial mutation probes.

### Main results

- Environment analysis: 3/3 expected sensor states match; 2/2 stored body checks pass.
- Dependency invalidation: height revision/value/state, base elevation, body geometry, footprint content and north-bearing mutations change the fingerprint. Invalid body mutations fail the mesh/footprint check.
- DXF: 8 stable object IDs, 11 entities, R2010 version and metre units; all synthetic layer properties and entity mapping checks pass; ezdxf reports 0 audit errors and 0 fixes.
- Adversarial mutations: layer lineweight, units, text label, unexpected entity and polyline coordinate changes are rejected. The baseline dependency suite covers 14 checks (one unchanged-manifest control plus 13 invalidation cases). Polygon interior ring mutation retains both `outer` and `hole` ring roles.
- Environment unit tests: `pytest -q working/environment-analysis/test_solar_shadow.py` → 17 passed.

## Important correction

The previous R1 harness contained false-confidence defects: a footprint projection was compared with itself; height values/states and base elevation were not fully represented in the dependency fingerprint; polygon interior rings could be silently omitted; and the DXF check did not assert several profile/geometry details. R2 corrects these and records reproducible adversarial probes.

## Current gate status

`E2E-FIXTURE-001 v0.2`: `conditional / external_review_pending`.

This is an internal adversarial pass, not an external independent review. No A1 or production gate is approved. No real raster-to-Trace run, road-generation run, IFC file, independent CAD application round-trip, independent solar simulation engine, real design-office profile or regulatory compliance determination exists.

## Mainline next action

`NEXT-E2E-003`: deliver the v0.2 review packet to a reviewer who did not author the artifacts, then separately pursue a third-party CAD application round-trip. Real paired site-sketch evidence and IFC validation remain separate gates. The project stays on the end-to-end mainline; no single subtopic is promoted to final architecture.

# Adversarial Review Report — E2E-FIXTURE-001 R2

**Review mode:** internal adversarial review using a separate artifact-validation code path and mutation tests  
**Date:** 2026-10-27  
**Disposition:** `conditional`  
**External reviewer:** not yet assigned / not completed

## Executive conclusion

The previous R1 vertical slice was not as strongly validated as its green status suggested. The most important defects were in the test harness and compiler validation rather than in the basic expected sensor outputs. R2 corrects those issues and the new mutation suite passes. However, the review cannot be marked as an independent external approval because the same project thread prepared the artifacts and ran the audit. The next gate remains external review plus a separate CAD application round-trip.

## Findings

### F-001 — Body projection check was tautological

- **Severity:** High
- **Prior artifact:** `run_fixture_benchmark_v0_2.py`, `projected_footprint = footprint`
- **Reproduction:** the previous check compared a footprint object with itself, so the symmetric difference was necessarily zero; it did not read a body mesh.
- **Risk:** false confidence in 2D/3D identity.
- **Disposition:** Fixed in R2. `BLDG-01` now contains an explicit synthetic prism mesh. The checker derives top/bottom projections from stored mesh vertices, checks expected elevations, identical top/bottom XY sets, and closed-shell edge counts. Top- and bottom-vertex mutations fail.
- **Residual limit:** still not a geometric-kernel or IFC round-trip.

### F-002 — Environment dependency fingerprint omitted material values

- **Severity:** High
- **Prior artifact:** `run_fixture_benchmark_v0_2.py`, dependency manifest `object_revisions`
- **Reproduction:** changing `BLDG-01.height_m` from 22 to 5 while retaining `height_revision` changed `SENSOR-GREEN-01` from shaded to sunlit but left the old dependency fingerprint unchanged.
- **Risk:** changed results could be presented as current.
- **Disposition:** Fixed in R2. The fingerprint includes height value/state, base elevation/value state, body representation metadata/content hash, footprint content hash, placement/body/height revisions, timestamp, method versions, sensor-grid content, terrain content and context coverage. The baseline suite checks one unchanged-manifest control plus 13 invalidation cases; mutation tests confirm fingerprint changes even when revision identifiers are reused.

### F-003 — Polygon interior rings were silently dropped

- **Severity:** High
- **Prior artifact:** `compile_fixture_to_dxf_v0_2.py`, polygon path selected only `coordinates[0]`
- **Reproduction:** add an interior ring to `GREEN-AREA-01`; R1 emitted only the exterior ring and still passed.
- **Risk:** courtyard holes or other interior boundaries disappear from output without a warning.
- **Disposition:** Fixed in R2. Polygon and MultiPolygon rings are emitted as separately tagged closed polylines with part/ring index and `outer`/`hole` roles. The adversarial fixture exports both roles and passes with 12 expected entities.
- **Residual limit:** tagged outline linework is not a filled DXF region and does not prove external applications preserve polygon topology semantics.

### F-004 — DXF validation did not cover enough of the claimed mapping

- **Severity:** High
- **Prior artifact:** R1 mapping check
- **Reproduction:** R1 did not assert layer color/linetype/lineweight, units, text content/placement, entity type and exact entity count as complete profile conditions.
- **Risk:** malformed or altered drawings could pass object-ID checks.
- **Disposition:** Fixed in R2 by a separate `dxf_validator.py` code path. It checks DXF version, INSUNITS, declared layer properties, exact expected entity count, no untagged/unknown entities, entity type, source and representation hashes, geometry coordinates/closure, point marker and text label fields, and zero audit errors/fixes. Mutations to lineweight, units, label, coordinates and unexpected entities are rejected.
- **Residual limit:** generator and validator still use ezdxf; no independent CAD application has been run.

### F-005 — Source geometry hash and exported representation were conflated

- **Severity:** Medium
- **Disposition:** Fixed in R2. XDATA now separates `source_hash` from `representation_hash`, and tags ring/part/entity roles. Point-marker XY projection is explicitly identified as presentation output, not the full source Point geometry.

### F-006 — Duration metric interval semantics are not explicit

- **Severity:** Medium, open, outside the one-timestamp E2E slice
- **Artifact:** `environment-analysis/solar_shadow.py`, `sampled_direct_sun_hours()`
- **Concern:** the function counts `sample_count × timestep_hours`; that is valid if each timestamp is defined as the start of a following interval, but the public contract does not yet make that convention explicit enough to prevent alternative interpretations.
- **Required action:** define the interval convention and add endpoint/coverage tests before presenting duration metrics as reliable. The current fixture does not test duration metrics.

### F-007 — External independence and compatibility remain unproven

- **Severity:** High, open
- **Concern:** this review was run in the authoring workspace. No external reviewer has inspected the v0.2 packet, and no third-party CAD application has read/written the DXF.
- **Required action:** independent reviewer must return findings and disposition; a separate CAD application round-trip must be run when available.

## Test summary

- Environment tests: **17 passed**.
- Base E2E fixture: **3/3 sensor states**, **2/2 stored body-state checks**.
- Dependency mutation probes: 14 baseline checks (same-manifest control plus 13 invalidation cases) cover height revision/value/state, base elevation, body/footprint content, north bearing, timestamp, method versions, sensor grid, terrain and context coverage. Separate fixture mutations to height value/state, base elevation and body top/bottom vertices change the fingerprint; invalid body mutations fail validation.
- DXF base artifact: **8 object IDs**, **11 entities**, expected R2010 version, metre units, synthetic layer properties and geometry mapping pass; **0 audit errors / 0 fixes**.
- DXF mutation probes: lineweight, units, label text, unexpected entity and polyline-coordinate mutations all detected.
- Polygon-hole probe: exterior and interior rings both retained with role metadata; 12 expected entities.

## Explicit non-claims

This report does not certify real-site accuracy, real sketch-to-CAD performance, third-party CAD compatibility, IFC/BIM correctness, professional design correctness, design-office standard compliance, or legal/regulatory compliance. It does not approve A1 or production release.

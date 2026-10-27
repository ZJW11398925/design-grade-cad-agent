# E2E-FIXTURE-001 v0.2 — Isolated Second-Pass Review

**Review ID:** `REVIEW-E2E-FIXTURE-001-R2-ISOLATED-PASS-01`  
**Review date:** 2026-10-27  
**Disposition:** `conditional`  
**Review mode:** isolated second-pass execution and additional mutation probes by the same assistant session; **not an external independent review**.  
**External review completed:** `false`.

## 1. Reproducibility

- Review packet manifest: **33/33 files passed SHA-256 and byte-length verification** before execution.
- Runtime: Python environment with Shapely `2.1.2`, ezdxf `1.4.4`, pytest `9.0.2`.
- Required commands rerun from a freshly extracted packet directory:
  - environment tests: **17 passed**;
  - fixture benchmark: **3/3 sensor outcomes and 2/2 stored-body checks passed**;
  - CAD-IR regeneration: **8 objects / 2 building objects**;
  - DXF compilation and validation: **11 expected modelspace entities, 0 audit errors, 0 audit fixes**;
  - original mutation suite: all listed probes reported as detected.
- Additional reviewer probes: 10 DXF mutations plus solar zenith, duration convention and numeric-type checks.

This establishes reproducibility of the supplied synthetic test packet, not correctness of a real design pipeline.

## 2. Findings

### F-008 — Non-modelspace entities are outside the validator's scan

- **Severity:** High for a claim that all drawing entities are checked.
- **Artifact:** `working/e2e-integration/dxf_validator.py`, entity enumeration in `validate_dxf_file()`.
- **Reproduction:** add an untagged `LINE` to `Layout1` (paper space) in a copy of the passing DXF; save and validate.
- **Expected:** either reject non-modelspace entities under the current modelspace-only profile, or validate them against an explicit layout contract.
- **Observed:** validator returns `passed_with_scope_limits`; `entity_count` remains 11 and `all_entities_checked=true`.
- **Required change:** enumerate every layout and explicitly declare whether non-modelspace entities are allowed. Do not report all entities checked while ignoring paper-space content.

### F-009 — Nonzero Z/elevation can pass the 2D plan validator

- **Severity:** High for downstream coordinate correctness.
- **Artifact:** `dxf_validator.py`, entity geometry checks.
- **Reproduction:** set a building `LWPOLYLINE` elevation to `123`; separately set a sensor `CIRCLE` center Z or `TEXT` insertion Z to `99`, leaving XY unchanged.
- **Expected:** reject nonzero Z for the declared 2D plan representation, or validate an explicitly declared plane/elevation policy.
- **Observed:** all three mutated files pass.
- **Required change:** check polyline elevation and extrusion; circle center Z and extrusion; text insertion/alignment Z and extrusion. Include the accepted Z/plane policy in the profile and representation checks.

### F-010 — Entity-level style overrides are not constrained by the current Profile

- **Severity:** Medium; contract gap rather than a violation of an already explicit BYLAYER rule.
- **Artifact:** synthetic DXF Profile and `dxf_validator.py`.
- **Reproduction:** on an `A-BUILDING-OUTLINE` polyline, set `color=1`, `lineweight=211`, explicit `linetype=CONTINUOUS`, or `true_color=0xFF0000`. All four pass. A text rotation change to 90 degrees also passes.
- **Observed:** layer-table attributes remain valid, so the validator accepts entity-level overrides and unprofiled text orientation.
- **Required change:** the Profile must explicitly state whether entities must use BYLAYER or may override color/linetype/lineweight/true-color/transparency; it must also define required text style, rotation, width, alignment and Z. Enforce that policy in the validator. Do not treat this as a confirmed violation until the Profile's policy is fixed.

### F-011 — Unused extra layers are accepted without a declared extension policy

- **Severity:** Medium / specification gap.
- **Artifact:** `dxf_validator.py`, layer-table checks.
- **Reproduction:** add an unused `UNEXPECTED-EXTRA` layer; validation still passes.
- **Expected:** the Profile should declare an allowlist or an explicit extension policy.
- **Observed:** required layers are checked, but the actual layer set is not constrained.
- **Required change:** define allowed system layers (for example `0` and `Defpoints`) and whether any additional layers are allowed; enforce the declaration.

### F-012 — Exact solar zenith is misclassified as an invalid vector

- **Severity:** Medium; an edge case that can occur near local solar noon in suitable latitudes/seasons.
- **Artifact:** `working/environment-analysis/solar_shadow.py`, `assess_sensor_direct_sun()`.
- **Reproduction:** call with `SolarPosition(elevation_deg=90.0, ...)`, an empty blocker list, complete context and a valid project north bearing.
- **Expected:** for a ground sensor not covered by a blocker, direct sun is confirmed under the declared complete context; if context is incomplete, remain unknown.
- **Observed:** `invalid_solar_vector` because the horizontal component is near zero.
- **Required change:** explicitly handle the zenith case, checking sensor/blocker overlap and context completeness before returning a result.

### F-013 — Boolean values are accepted as numeric geometry inputs

- **Severity:** Medium; schema/input validation gap.
- **Artifact:** `solar_shadow.py`, `Blocker.validate()` and sensor-coordinate validation.
- **Reproduction:** `Blocker(..., height_m=True, height_status="confirmed").validate()` succeeds; `sensor_xy=(True, 0.0)` is accepted. In Python, `bool` subclasses `int` and passes the current numeric checks.
- **Expected:** booleans are not valid metric values or coordinates.
- **Required change:** use explicit finite-real validation that rejects booleans for heights, elevations, coordinates, angles and timestep values.

### F-014 — Sampled duration interval convention remains underspecified

- **Severity:** Medium; already noted as open in the v0.2 report.
- **Artifact:** `sampled_direct_sun_hours()`.
- **Reproduction:** with one, two and three hourly timestamps, output durations are 1, 2 and 3 hours respectively.
- **Concern:** this is correct only if each timestamp starts a forward interval, including the final timestamp. If timestamps are sample instants spanning a closed interval, the final sample should not add another hour.
- **Required change:** make the interval convention an explicit API argument or contract field, return the covered interval bounds, and add endpoint tests for both conventions.

## 3. Probe summary

- Four hard false-accepts under the current stated 2D/output-validation scope: paper-space entity, nonzero polyline elevation, nonzero circle Z, nonzero text insertion Z.
- Six additional profile-policy gaps were accepted: entity color, lineweight, linetype and true-color overrides; text rotation; extra unused layer. These require a declared policy before they can be called formal violations.
- Exact zenith returned a false unknown/invalid status.
- Boolean metric inputs were accepted.
- Duration semantics remain ambiguous.

Machine-readable details are in `independent-review-results-v0.3.json`; reproduction code is `independent_review_probes_v0_3.py`.

## 4. Review disposition and limits

**Disposition: `conditional`.** The packet is reproducible, but it should not be passed to a third party as a claim that its validator is already hardened. Fix F-008/F-009/F-012/F-013; specify and enforce the policies in F-010/F-011; close F-014 with a clear interval contract; then rerun all regression and mutation tests and produce a new immutable review packet.

This is not an external reviewer sign-off. No real raster-to-Trace input, road generation, IFC output, independent solar engine, third-party CAD application round-trip, professional design review, or regulatory compliance determination was performed. No A1 or production gate is approved.

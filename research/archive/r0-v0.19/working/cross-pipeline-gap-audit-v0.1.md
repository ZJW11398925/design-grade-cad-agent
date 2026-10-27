# Cross-pipeline Gap Audit v0.1 — R0 v0.8

**Date:** 2026-10-26  
**Purpose:** Find the next highest-value integration proof after the BATCH-005 bounded checkpoint.  
**Status:** evidence audit, not A1, not an architecture approval.

## 1. Evidence inventory

| Stage | Current evidence | Evidence class | What is still not proven | Status |
|---|---|---|---|---|
| Source image / coordinate calibration | `LOCAL-SKETCH-001`; trace schema and real Benchmark contract | Local synthetic numerical benchmark + candidate contract | No paired Tier B/C real site sketch with reviewed Trace/semantic ground truth; no independent A1 | `ready-for-A1 / unclosed` |
| Semantic candidates / Trace | OpenCV/SAM/GDAL/Potrace source research; source/trace schema | Official-source review + synthetic trace metrics | No end-to-end reviewed raster-to-Trace run on real planning sketch; no calibrated confidence gate | `unclosed` |
| 2D geometry / road topology | Road profile schema, source map and road candidate research | Candidate schemas and bounded source review | No single integrated Road Graph → alignment → cross-section → junction → surface benchmark; road standard/profile blockers remain | `bounded-paused / unclosed` |
| Building Footprint / Massing | `LOCAL-BLDG-001` identity metric probe; `LOCAL-BLDG-002` topology/regularization Validator probe; site-topology contract | Synthetic geometry/Validator tests | No real design sketch benchmark, no execution of Building Regulariser/CartAGen as part of this pipeline, no real IFC round-trip | `bounded-paused / unclosed` |
| 2D ↔ 3D / IFC | Building schema and IFC representation lifecycle contract | Source/API inspection + synthetic consistency tests | IfcOpenShell unavailable in sandbox; no written/read IFC fixture proving GlobalId, placement, units and Footprint/Body survive | `blocked / unclosed` |
| Environment analysis | `LOCAL-ENV-001`, 15 assertion functions, solar reference sanity check, dependency fingerprint contract | Local synthetic ray/prism baseline + published solar-position cross-check | No independent Radiance/Honeybee run; no real terrain/context; no multi-season error distribution; no legal threshold check | `bounded-checkpoint / unclosed` |
| DXF compiler / Profile Validator | `LOCAL-CAD-003`, `LOCAL-CAD-004`; sample DXF files | Local ezdxf write/read + self-authored checks; small source-backed Profile excerpt | No independent CAD open/save round-trip; source Profile coordinate system blocked; no user/design-office Profile | `bounded-paused / unclosed` |
| Standards / rule applicability | DB11/T 1948-2021 excerpt and Profile contracts; road standards source map | Primary-source excerpt for a specific Beijing standard; other road sources remain incomplete | No user jurisdiction/profile confirmed; no general-purpose Chinese compliance package; no current full applicability resolution for the target project | `partial / unclosed` |
| Cross-stage identity / change governance | Shared fixture → provisional CAD-IR → environment slice → DXF XDATA/manifest | `LOCAL-E2E-ENV-001` and `LOCAL-E2E-CAD-001` passed on synthetic data | No real Source/Trace extraction, no independent CAD reader, no IFC, no lock-preserving repair proposal, no real input case | `partial synthetic vertical slice` |

## 2. The main integration gap

The project has several useful **local proofs**, but they do not yet share one canonical site fixture or one revision/provenance graph. The largest risk is therefore not a missing named library. It is that each sub-system may use different IDs, coordinate assumptions, height states, geometry revisions, or meanings of `confirmed`.

Examples:

- The trace schema has `trace_id` and `coordinate_frame_id`; the building schema has its own `id`, `source_trace_ref` and representation states; the road schema has corridor/segment IDs; CAD-IR has `object_id` and geometry revision; environment results require footprint/body/height/placement revisions.
- These fields are individually sensible, but no current benchmark demonstrates that one building keeps the same identity from Trace → Footprint → Body → environment result → DXF/IFC.
- `LOCAL-ENV-001` proves that a height revision can invalidate an environment result when the revision is in the manifest. It does not yet prove that the upstream building model emits that revision correctly or that downstream CAD output consumes the same revision.
- Internal DXF re-read proves file structure under ezdxf; it does not prove third-party CAD compatibility or that the exported objects match the canonical site model.

## 3. Priority order for the next integration step

### P0 — One shared canonical synthetic site fixture

Create one deliberately small fixture containing site boundary, road centerline/corridor, green space, two buildings (one with known synthetic height, one with unknown height), coordinate frame/north, site/time context, and a small sensor grid. Give every object a stable ID, revision, source/provenance stub, geometry state and confidence/evidence state. Make the fixture explicit that all geometry and values are synthetic, not engineering defaults.

Why first: it gives the existing local probes a common referent and exposes schema incompatibilities before any one library is selected.

### P1 — Vertical-slice identity and stale-state test

Use the shared fixture to prove a narrow but real software contract:

1. stable object IDs and geometry revisions survive fixture loading;
2. Footprint → synthetic Massing retains the same building identity;
3. environment analysis reads the same footprint/height revisions and returns the expected sunlit/shaded/unknown statuses;
4. changing height, north or footprint revision changes the dependency fingerprint and marks prior analysis stale;
5. the canonical object list can be compiled to the current synthetic DXF profile and re-read, with object mapping retained in a manifest.

This is an integration/contract test, not a claim that the overall drawing is professional or standards-compliant.

### P2 — External-engine comparison only after fixture stability

Once the fixture and coordinate conventions are stable, run it through pvlib/Ladybug and Honeybee-Radiance/Radiance when a usable runtime exists. Keep solar-position comparison, geometric occlusion comparison, and climate/daylight metrics as separate results.

### P3 — Real input benchmark and project Profile

Only after the synthetic cross-stage fixture is stable should the project spend effort on a real paired site-sketch dataset and the user's actual jurisdiction/design-office Profile. Synthetic tests cannot calibrate real trace fidelity, professional geometry thresholds or compliance.

## 4. Follow-up result: shared-fixture vertical slice

The initially recommended `NEXT-E2E-001` has now been executed:

- `LOCAL-E2E-ENV-001`: 3/3 sensor statuses matched the expected fixture outcomes; 2/2 synthetic Footprint/Body identity checks passed; height revision, geometry-content mutation without revision bump, and north mutations marked the old result stale.
- `LOCAL-E2E-CAD-001`: 8 object IDs mapped into 11 editable DXF entities; ezdxf audit reported 0 errors/fixes; IDs, classes, geometry revisions, geometry hashes, layers and tested coordinates/closure survived same-library re-read.
- The DXF compiler now consumes `site-fixture-cad-ir-v0.1.json`, rather than compiling directly from the raw fixture. The CAD-IR instance preserves fixture IDs, coordinate frame, source Trace stubs, height state, revision fields and validation states.
- `BLDG-02` remains a footprint-only object because height is unknown; no 3D body is invented.

These results close only the **synthetic interface-contract probe**. The raw fixture does not run semantic segmentation, road generation, building regularization, IFC, or a third-party CAD application.

## 5. Recommended next action

`NEXT-E2E-002`: send the fixture, CAD-IR instance, environment result, DXF and mapping manifest through an **independent review** using `independent-review-checklist-v0.1.md`. In parallel, keep two separate external blockers visible: (a) a real paired site-sketch/Trace benchmark for BATCH-002 and (b) an independent CAD application round-trip. Do not self-approve the synthetic slice as production readiness.

## 6. Gate and limits

- This audit does not approve any A1 and does not close BATCH-001..005.
- No final technology stack or canonical IR is selected here.
- The fixture must not contain unsourced real engineering parameters or masquerade as a real planning project.
- Passing the shared fixture would prove only the tested interfaces and synthetic invariants; real-site performance, third-party interoperability and regulatory compliance remain separate gates.

# LOCAL-E2E-FIXTURE-001-R2 — Adversarially checked shared fixture slice

**Date:** 2026-10-27  
**Status:** `passed_with_scope_limits; external_review_pending`  
**Scope:** synthetic fixture → environment analysis → provisional CAD-IR → editable 2D DXF → separate code-path DXF artifact validation.

## 1. Why R2 exists

A separate adversarial pass found four false-confidence risks in the earlier R1 test harness. The earlier body-projection check assigned the footprint object to the projected footprint, the environment dependency fingerprint omitted numeric height/base-elevation and height-state values, polygon interior rings could be dropped while compilation passed, and the DXF check did not fully assert units/layer styles/text/unexpected entities. These have been patched and tested in R2.

## 2. Current baseline results

- Environment statuses: **3/3** expected sensor states match.
- Stored synthetic body mesh: **2/2** body-state checks pass. `BLDG-01` uses an explicit 8-vertex/6-face synthetic prism mesh; top and bottom face projections, elevation planes, vertex elevations and closed-shell edge counts are checked against its footprint. `BLDG-02` remains body-blocked because height is unknown.
- Dependency fingerprint: same manifest remains current; mutations to height revision, numeric height, height state, base elevation, body geometry hash, footprint geometry hash and north bearing all produce a different fingerprint.
- North-bearing probe: changing the project +Y true-north bearing changes the sensor result signature and invalidates the previous result.
- CAD-IR: **8 stable object IDs** are mapped.
- DXF: **11 entities** for the base fixture; expected entity count, DXF R2010 version, metre units, all declared synthetic layer colors/linetypes/lineweights, entity type, object/class/revision/source hash, representation hash, coordinates/closure, point marker and text label content/placement all pass. `ezdxf` audit reports **0 errors and 0 fixes**.

## 3. Adversarial mutations

`run_adversarial_review.py` executes mutations in temporary copies. The canonical fixture and DXF are not mutated by these probes.

| Mutation | Expected behavior | R2 result |
|---|---|---|
| Height changes from 22 m to 5 m while `height_revision` is reused | Dependency fingerprint changes; stale geometry/body state fails closed | Detected; fingerprint changes and body consistency check fails |
| Height state changes from confirmed to estimated without revision bump | Dependency fingerprint changes; result cannot silently remain confirmed | Detected; fingerprint changes and sunlit states become estimated/unknown where affected |
| Base elevation changes without revision bump | Fingerprint changes and mesh/height consistency is rechecked | Detected |
| Top or bottom body vertex mutates while `body_revision` is reused | Body projection/mesh validation fails and dependency fingerprint changes | Detected |
| Polygon gets an interior ring | Inner ring is not silently dropped | Outer and `hole` rings emitted as separately tagged polylines; **12 entities**; validator passes the declared linework contract |
| Layer lineweight changes after export | Profile validation fails | Detected |
| `$INSUNITS` changes from metres | Unit validation fails | Detected |
| Sensor label text changes | Representation validation fails | Detected |
| Untagged extra entity is added | Unexpected entity is rejected | Detected |
| Building polyline coordinate changes while XDATA is retained | Geometry/representation check fails | Detected |

Machine-readable result: `adversarial-review-results-v0.2.json`; the script reports `all_adversarial_probes_pass=true`. The baseline dependency suite has 14 checks (one current-manifest control plus 13 invalidation cases).

## 4. Important semantic limits

- Polygon holes and MultiPolygon parts are emitted as separate closed polylines with explicit ring/part role metadata. This preserves the outline contract; it does **not** make a filled DXF region or prove that another CAD application interprets those rings as a topological surface.
- Point markers are a 2D plan presentation. A source Point may contain Z; the source geometry hash is preserved, while the DXF marker uses XY. The 3D source value remains in CAD-IR/sidecar data.
- The synthetic body mesh is not IFC, not a production geometric-kernel solid and not a real building model.
- `ezdxf` artifact validation is a separate code path from generation, but both use ezdxf. No LibreCAD, AutoCAD, FreeCAD or other independent CAD application has been run.
- The sun/shadow method remains a low-precision geometric probe. No independent Radiance/Honeybee/pvlib engine was run.
- `sampled_direct_sun_hours()` interval-boundary semantics remain an open follow-up; the current fixture tests one timestamp, not duration metrics.
- No real sketch-to-Trace, road generation, professional geometry regularization, IFC output, design-office Profile, or legal compliance test is included.

## 5. Review disposition

**Internal adversarial status: conditional pass for the next experiment.** The identified harness defects are fixed and their regression probes pass. This is not an external independent review: the project gate remains `external_review_pending`, and this thread does not approve A1, production readiness, real-site accuracy, third-party CAD compatibility, or legal compliance.

## 6. Next gate

`NEXT-E2E-003`: give the v0.2 review packet to a reviewer who did not author this fixture, and separately obtain a third-party CAD application round-trip. These are independent gates; neither substitutes for real paired site-sketch evidence or IFC validation.

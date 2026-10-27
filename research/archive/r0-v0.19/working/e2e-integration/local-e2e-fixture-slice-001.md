# LOCAL-E2E-FIXTURE-001 — Shared site fixture vertical slice

**Date:** 2026-10-26  
**Status:** `passed_with_scope_limits`  
**Scope:** synthetic fixture → provisional CAD-IR instance → environment-analysis slice → editable DXF → same-library DXF re-read.

## 1. Artifacts executed

- `site-fixture-v0.1.json` — shared synthetic scene: site boundary, road centerline, green area, two building footprints, three environment sensors, coordinate frame, north, timestamp, height provenance and expected results.
- `run_fixture_benchmark.py` → `local-e2e-fixture-env-001.json` — consumes the shared fixture's building footprints/heights and sensor grid.
- `fixture_to_cad_ir.py` → `site-fixture-cad-ir-v0.1.json` — maps the same stable IDs, geometry revisions, provenance stubs, layer keys, height states and validation states into the provisional CAD-IR contract.
- `compile_fixture_to_dxf.py` → `site-fixture-v0.1.dxf` and `site-fixture-v0.1-dxf-manifest.json` — compiles the CAD-IR instance, embeds object ID/class/revision/geometry hash in XDATA, reopens the DXF with ezdxf, and verifies the mapping.

## 2. Results

| Check | Result | Meaning |
|---|---|---|
| Environment sensor grid | 3/3 expected statuses matched | Known-height blocker shades `SENSOR-GREEN-01`; unknown-height blocker makes `SENSOR-GREEN-02` unknown; `SENSOR-GREEN-03` is sunlit within the declared fixture context. |
| Synthetic Footprint → Body contract | 2/2 checks passed | `BLDG-01` has a current synthetic vertical-prism body whose XY projection matches its footprint; `BLDG-02` remains without a body because its height is unknown. No IFC solid was created. |
| Revision invalidation | Height and north changes mark result stale | Changing `height_revision` or project +Y true-north bearing changes the dependency fingerprint. |
| CAD-IR instance | 8 stable object IDs | Boundary, road, green space, two building footprints and three sensors mapped to the provisional CAD-IR shape. |
| DXF output | 11 entities; 0 ezdxf audit errors/fixes | Editable 2D entities were written in R2010 DXF with metre units and synthetic layers. |
| Object identity / revision / geometry | All mapping checks passed | Every expected object ID is present; class, geometry revision, geometry hash, layer and tested coordinates/closure survived same-library write/read. |
| North rotation probe | Results changed | With the project's +Y true-north bearing changed to 90°, the declared sensor statuses change; the prior result is stale and cannot be reused. |

## 3. What this proves

This is the first common-fixture vertical slice connecting environmental analysis and CAD output. It demonstrates that a stable object/revision contract can be exercised across multiple components, rather than presenting unrelated tool demos. It also makes the missing-height policy observable: the fixture's second building is retained as a 2D footprint but does not receive an invented 3D body.

## 4. What this does not prove

- No real raster sketch, semantic segmentation, Trace extraction, road centerline generation, junction construction, building regularization, or design optimization was run; the fixture supplies already-defined synthetic objects.
- The synthetic massing check verifies extrusion metadata and XY projection only. It is not a geometric-kernel or IFC round-trip.
- The DXF round-trip is with ezdxf itself. No LibreCAD, AutoCAD, FreeCAD or other independent CAD application was run.
- No IFC file was generated. The DXF contains 2D editable entities; height/massing metadata remains in the CAD-IR and sidecar manifest.
- The synthetic Profile is not a real design-office standard and the result is not a national/local code compliance finding.
- The site geometry is local metric geometry, not georeferenced. Sydney is used only as a solar-position reference input.

## 5. Next gate

The next highest-value proof is **independent review and external compatibility**, not another arbitrary synthetic feature. The current fixture and manifests should be reviewed against the provisional CAD-IR contract, then tested with an independent CAD reader when available. Separately, BATCH-002 still needs a real paired site-sketch/Trace case before claims about input quality can advance. These are separate gates and must not be merged into a single green status.

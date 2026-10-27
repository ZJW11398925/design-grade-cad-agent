# E2E-003 — Adversarial Delivery Regression

Status: implemented (same-library, synthetic scope)
Version: 0.6.0
Date: 2026-10-27

## Purpose

Turn the historical DXF delivery failure modes into repeatable CI evidence. At E2E-003 close, every scenario was either detected, passed as a positive check, or was a strict xfail linked to an accurate issue. Milestone 3a converted all xfails to positive checks; silent acceptance was never allowed.

This round does **not** systematically fix `DEV-CAD-001..008`, does not add third-party CAD evidence, does not extend to paper space, and does not change the deferred road-surface scope.

## Existing coverage reused

These were already covered before E2E-003 and were not duplicated:

| Scenario | Test | Result |
|---|---|---|
| Vertex mutation | `test_readback_detects_vertex_mutation` | detected (`COORDINATE_MISMATCH`) |
| Unexpected layer | `test_readback_detects_unexpected_layer` | detected (`UNEXPECTED_LAYER`) |
| Entity-type substitution | `test_readback_detects_entity_type_substitution_without_crashing` | detected (`ENTITY_TYPE_MISMATCH`), no crash |
| LWPOLYLINE bulge | `test_bulge_mutation_is_detected` | detected (`BULGE_MISMATCH`) |
| LWPOLYLINE constant width | `test_constant_width_mutation_is_detected` | detected (`CONST_WIDTH_MISMATCH`) |

## New positive coverage

| Scenario | Result |
|---|---|
| LWPOLYLINE non-zero elevation | detected (`NONZERO_Z`), category `cad_format_semantics` |
| MultiPolygon, 2 parts + 1 hole | 3 entities, audit 0/0, readback `pass`; ring roles outer/outer/hole. `ring_index` is global within the object (part order, then ring order); stable ring identity across revisions remains a Milestone 3 decision. |
| One layer linetype case (`Continuous`) | readback `pass`; no `LAYER_PROPERTY_MISMATCH`. Full symbol-table equivalence remains #5. |
| Missing XDATA | detected (`MISSING_XDATA`), category `interoperability` |
| Delivery comparison artifact | `delivery-comparison.json` contains object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit, profile fields, `dxf_sha256` and `readback_manifest_sha256`; both hashes are verified against the actual files |
| Issue categories | `UNEXPECTED_LAYER` → `profile_violation`; `COORDINATE_MISMATCH` → `cad_format_semantics`; unknown future codes → `unclassified`; contract-sync test enforces the mapping |

## Milestone 3a hardened checks (previously strict xfails)

All are now positive checks; no permanent xfail remains.

| Scenario | Detected code |
|---|---|
| CIRCLE center Z | `CIRCLE_NONZERO_Z` |
| TEXT insertion Z | `TEXT_NONZERO_Z` |
| TEXT rotation | `TEXT_ROTATION_MISMATCH` |
| TEXT width + alignment | `TEXT_WIDTH_MISMATCH`, `TEXT_ALIGNMENT_MISMATCH` |
| Entity color override | `ENTITY_COLOR_OVERRIDE` |
| Entity linetype override | `ENTITY_LINETYPE_OVERRIDE` |
| Entity lineweight override | `ENTITY_LINEWEIGHT_OVERRIDE` |
| Entity true-color override | `ENTITY_TRUE_COLOR_OVERRIDE` |
| Entity transparency override | `ENTITY_TRANSPARENCY_OVERRIDE` |
| LWPOLYLINE bulge | `BULGE_MISMATCH` |
| LWPOLYLINE constant width | `CONST_WIDTH_MISMATCH` |
| LWPOLYLINE start/end width | `VERTEX_WIDTH_MISMATCH` |
| LWPOLYLINE thickness | `THICKNESS_MISMATCH` |
| LWPOLYLINE extrusion | `EXTRUSION_MISMATCH` |
| Validator error | structured `VALIDATOR_ERROR` result |

## Issue category model

The living validator now exposes a category per issue:

- `cad_format_semantics` — DXF entity/geometry semantics.
- `interoperability` — CAD-IR ↔ DXF identity/provenance mismatch.
- `profile_violation` — delivery profile/layer policy violation.
- `serialization_difference` — normalization that is not a design failure.
- `validator_error` — validator could not complete; never a pass or design failure.

`VALIDATOR_ERROR` is now returned as a structured result for malformed DXF or validator-internal exceptions (Milestone 3a).

## Boundaries and non-claims

- **Same-library only.** Both compile and readback use `ezdxf`. This is not third-party CAD round-trip evidence; DEV-CAD-006 / issue #6 remains open.
- **Modelspace only.** Paper-space handling is intentionally out of scope.
- **Milestone 3a is a targeted validator fix, not the full DEV-CAD matrix.** 3b/3c remain.
- **No road surface geometry.** `SURFACE-R-002` remains deferred.
- **No real sketch, IFC, standards or design-office profile.**
- **Problem A remains open.** CAD-IR fingerprint vs registered dependency-key consistency is tracked as issue #16 (DEV-CAD-011) and was not fixed here.

## Test result

```text
tests/e2e/test_e2e_003_adversarial.py: 20 passed
full suite: 141 passed
```

## Milestone 3a (0.6.0)

- Structured `VALIDATOR_ERROR` wrapper; malformed DXF returns a structured failure.
- Entity BYLAYER style policy enforced for color/linetype/lineweight/true color/transparency.
- CIRCLE center Z, TEXT insertion Z and TEXT rotation/width/alignment checked.
- LWPOLYLINE bulge, start/end width, constant width, thickness and extrusion checked.
- `DeliveryProfile.text_style_policy` added; compiler writes explicit TEXT rotation/width/alignment.
- All 15 strict xfails converted to positive tests; full suite 141/141 passing.

## Correction (0.5.1)

- `delivery-comparison.json` previously named the DXF hash `manifest_sha256`. It is now `dxf_sha256`; a separate `readback_manifest_sha256` covers the written manifest file. The test now recomputes both hashes from the files.
- The readback manifest itself now names its DXF hash `dxf_sha256`.
- Unknown issue codes now default to `unclassified`; a contract-sync test asserts every code has an explicit category.
- Symbol-table wording is narrowed to one layer linetype reference case; #5 remains open for full symbol-table equivalence.
- MultiPolygon `ring_index` semantics are documented as global within the object; ring identity stability is a Milestone 3 decision.
- Issue #2 is narrowed to safe entity dispatch and closed with evidence; structured `validator_error` remains #7.
- Status and testing docs now include E2E-003 and no longer duplicate the third-party round-trip status.

## Reproduce

```bash
python -m pytest tests/e2e/test_e2e_003_adversarial.py -q
```

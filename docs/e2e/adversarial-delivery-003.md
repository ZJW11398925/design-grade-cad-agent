# E2E-003 — Adversarial Delivery Regression

Status: implemented (same-library, synthetic scope)
Version: 0.5.0
Date: 2026-10-27

## Purpose

Turn the historical DXF delivery failure modes into repeatable CI evidence. Every scenario must be either detected, pass as a positive check, or be a strict xfail linked to an accurate issue. Silent acceptance is not allowed.

This round does **not** systematically fix `DEV-CAD-001..008`, does not add third-party CAD evidence, does not extend to paper space, and does not change the deferred road-surface scope.

## Existing coverage reused

These were already covered before E2E-003 and were not duplicated:

| Scenario | Test | Result |
|---|---|---|
| Vertex mutation | `test_readback_detects_vertex_mutation` | detected (`COORDINATE_MISMATCH`) |
| Unexpected layer | `test_readback_detects_unexpected_layer` | detected (`UNEXPECTED_LAYER`) |
| Entity-type substitution | `test_readback_detects_entity_type_substitution_without_crashing` | detected (`ENTITY_TYPE_MISMATCH`), no crash |
| LWPOLYLINE bulge | `test_known_gap_bulge_mutation_is_not_detected` | strict xfail, issue #3 |
| LWPOLYLINE constant width | `test_known_gap_constant_width_mutation_is_not_detected` | strict xfail, issue #3 |

## New positive coverage

| Scenario | Result |
|---|---|
| LWPOLYLINE non-zero elevation | detected (`NONZERO_Z`), category `cad_format_semantics` |
| MultiPolygon, 2 parts + 1 hole | 3 entities, audit 0/0, readback `pass`; ring roles outer/outer/hole |
| Symbol-table linetype case (`Continuous`) | readback `pass`; no `LAYER_PROPERTY_MISMATCH` |
| Missing XDATA | detected (`MISSING_XDATA`), category `interoperability` |
| Delivery comparison artifact | `delivery-comparison.json` contains object IDs, canonical revisions, CAD-IR fingerprint, readback verdict, audit and profile fields |
| Issue categories | `UNEXPECTED_LAYER` → `profile_violation`; `COORDINATE_MISMATCH` → `cad_format_semantics` |

## New strict xfails

All are `strict=True`, so implementing the missing check will produce XPASS and force removal of the xfail.

| Scenario | Issue |
|---|---|
| CIRCLE center Z | #18 / DEV-CAD-010 |
| TEXT insertion Z | #18 / DEV-CAD-010 |
| TEXT rotation | #18 / DEV-CAD-010 |
| TEXT width + alignment | #18 / DEV-CAD-010 |
| Entity color override | #17 / DEV-CAD-009 |
| Entity linetype override | #17 / DEV-CAD-009 |
| Entity lineweight override | #17 / DEV-CAD-009 |
| Entity true-color override | #17 / DEV-CAD-009 |
| Entity transparency override | #17 / DEV-CAD-009 |
| LWPOLYLINE start/end width | #3 / DEV-CAD-003 |
| LWPOLYLINE thickness | #3 / DEV-CAD-003 |
| LWPOLYLINE extrusion | #3 / DEV-CAD-003 |
| Validator error structured result | #7 / DEV-CAD-007 |

## Issue category model

The living validator now exposes a category per issue:

- `cad_format_semantics` — DXF entity/geometry semantics.
- `interoperability` — CAD-IR ↔ DXF identity/provenance mismatch.
- `profile_violation` — delivery profile/layer policy violation.
- `serialization_difference` — normalization that is not a design failure.
- `validator_error` — validator could not complete; never a pass or design failure.

`VALIDATOR_ERROR` remains a strict xfail because a malformed DXF currently raises before a structured result can be returned.

## Boundaries and non-claims

- **Same-library only.** Both compile and readback use `ezdxf`. This is not third-party CAD round-trip evidence; DEV-CAD-006 / issue #6 remains open.
- **Modelspace only.** Paper-space handling is intentionally out of scope.
- **No DEV-CAD systematic fix.** Only test/evidence/contract work plus the issue-category field and `delivery-comparison.json`.
- **No road surface geometry.** `SURFACE-R-002` remains deferred.
- **No real sketch, IFC, standards or design-office profile.**
- **Problem A remains open.** CAD-IR fingerprint vs registered dependency-key consistency is tracked as issue #16 (DEV-CAD-011) and was not fixed here.

## Test result

```text
tests/e2e/test_e2e_003_adversarial.py: 6 passed, 13 xfailed
full suite: 125 passed, 15 xfailed (140 collected)
```

## Reproduce

```bash
python -m pytest tests/e2e/test_e2e_003_adversarial.py -q
```

# E2E-003b — Semantic Equivalence & Dependency Closure

Status: implemented (same-library, synthetic scope)
Version: 0.7.0
Date: 2026-10-27

## Purpose

Close the semantic-equivalence and dependency-closure gaps left after Milestone 3a:

- CAD-IR fingerprint vs registered dependency keys;
- full symbol-table name semantics;
- stable ring identity for multi-part polygons;
- raw DXF semantics plus canonical geometry in the readback evidence;
- serialization differences vs project-profile violations.

## 1. CAD-IR fingerprint consistency (#16)

The CAD-IR fingerprint no longer includes the global `canonical_scene_revision`. It is recorded as `built_from_scene_revision` metadata and excluded from the semantic hash.

Verified:

- An unrelated `RN-001.junction` change advances the scene revision but leaves CAD-IR and DXF `current`.
- Recomputing CAD-IR after that commit produces the **same** dependency fingerprint and a different `built_from_scene_revision`.
- A road hierarchy change (`R-001.semantic`) now stales CAD-IR and DXF, and changes the fingerprint.
- CAD-IR dependency registration covers `.semantic`, `.geometry` and `.parameter` for every exported object plus `SHADOW-E2E-002`.

## 2. Full symbol-table case semantics (#5)

- Layer names, linetypes and text styles compare case-insensitively by default; `symbol_name_policy: exact` is available.
- Layer-table names and entity layer references are matched by case-folded keys while preserving original spelling in diagnostics/manifest.
- Required text styles, blocks and dimstyles are checked case-insensitively (`TEXT_STYLE_MISSING`, `BLOCK_MISSING`, `DIMSTYLE_MISSING`).
- `TEXT_STYLE_MISMATCH` is detected when the name differs semantically.
- A comparator test covers layer, linetype, text style, block and dimstyle names.

Verified cases:

- `a-building-outline` vs `A-BUILDING-OUTLINE` → pass with case-insensitive policy; fail with `exact`.
- `standard` vs `Standard` → pass.
- `Other` vs `Standard` → `TEXT_STYLE_MISMATCH`.
- Required `BLOCK-A` / `DIM-A` satisfied by `block-a` / `dim-a` → pass; missing block → `BLOCK_MISSING`.

## 3. Stable ring identity (#1)

- XDATA now carries a content-derived `ring_key` (object ID, entity role, ring role, rounded coordinates) in addition to part/ring indices.
- `RING_KEY_MISMATCH` is an interoperability error.
- MultiPolygon with 2 parts + 1 hole still round-trips as 3 entities.
- Inserting a sibling part at the front changes `part_index`/`ring_index`, but the original 3 ring keys remain stable; the new part adds one key.

The global `ring_index` remains a build/index field; `ring_key` is the identity field for comparison.

## 4. Raw DXF semantics + canonical geometry (#4)

- The readback manifest now records both `canonical_target` and `raw_dxf_semantics` per entity.
- LWPOLYLINE raw fields: closed, elevation, per-vertex bulge/start width/end width, constant width, thickness, extrusion.
- CIRCLE raw fields: center (including Z), radius.
- TEXT raw fields: insert (including Z), height, rotation, width, halign, valign, style, text.
- Numeric tolerance is `1e-9`, version `0.1`, recorded in `contracts/cad-ir-v0.1.yaml`.
- Canvas coordinate mutations and raw-field mutations are both detected; neither representation alone can hide a change.

## 5. Serialization vs profile semantics (#8)

- Entity linetype override → `ENTITY_LINETYPE_OVERRIDE`, category `profile_violation`.
- Consequent ezdxf audit normalization → `AUDIT_FIX`, category `serialization_difference`.
- CAD geometry mismatch → `cad_format_semantics`.
- CAD-IR/DXF identity mismatch → `interoperability`.
- Validator-internal failure → `validator_error`.

## Test result

```text
tests/e2e/test_e2e_003b_semantics.py: 11 passed
full suite: 152 passed
```

## Remaining scope

- Third-party CAD round-trip (#6) — Milestone 3c.
- Arcs/splines are not in the current delivery entity set; raw/canonical validation covers LWPOLYLINE, CIRCLE and TEXT.
- Real sketch input, road surface geometry, IFC and standards compliance remain separate evidence packages.

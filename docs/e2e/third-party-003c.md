# E2E-003c — Third-Party CAD Round-Trip (AutoCAD 2024 Core Console)

Status: **partial** — one real third-party CAD host executed; the full matrix is not complete.
Version: 0.8.0
Date: 2026-10-27

## What was executed

- Host: **AutoCAD 2024 Core Console** (`accoreconsole.exe`, file version `24.3.61.0.0`, Core Console `U.61.0.0`)
- Platform: Windows 11 / 10.0.26100
- Mode: isolated user profile (`/isolate DGCAD`), no GUI
- Input: `input.dxf` generated from the E2E synthetic site model (15 modelspace entities, 15 carrying `DESIGN_GRADE` XDATA)
- Operation: AutoCAD opened the input, saved it as DXF (default R2018), and quit
- Output: `roundtrip.dxf` (85 KB, AC1032 / R2018)

Reproduce:

```bash
python scripts/third_party/autocad_core_roundtrip.py --output-dir docs/e2e/third-party-003c --timeout 120
```

## Result

```text
verdict: semantic_pass_with_serialization_differences
validator: pass with R2018 delivery profile
```

| Check | Input | Round-trip |
|---|---|---|
| DXF version | AC1024 / R2010 | AC1032 / R2018 |
| INSUNITS | 6 (metre) | 6 (metre) |
| Entities | 15 | 15 |
| Entity types | 7 LWPOLYLINE, 4 CIRCLE, 4 TEXT | same |
| Entities with `DESIGN_GRADE` XDATA | 15 | 15 |
| XDATA values | — | identical |
| Layers / colors / lineweights | — | preserved |
| Blocks / dimstyles / text styles | — | preserved |
| Audit errors / fixes | 0 / 0 | 0 / 0 |

Recorded differences:

1. DXF version upgrade `AC1024 → AC1032` (R2010 → R2018).
2. Layer linetype spelling normalized `CONTINUOUS → Continuous` on six layers.

Both are **serialization differences**, not design-semantic failures. The living validator passes when given an R2018 semantic-equivalence profile, including layer/linetype case-insensitive comparison, XDATA identity/revision/hash checks, geometry, text style/placement, and ring keys.

## Evidence files

- `docs/e2e/third-party-003c/input.dxf`
- `docs/e2e/third-party-003c/roundtrip.dxf`
- `docs/e2e/third-party-003c/environment.json`
- `docs/e2e/third-party-003c/comparison.json`
- `docs/e2e/third-party-003c/save.scr`
- `docs/e2e/third-party-003c/stdout.txt`

The comparison records SHA-256 for both DXF files, the command, return code, timeout flag and AutoCAD file version.

## Scope boundary

`comparison.json` declares:

```text
matrix_status: partial
apps_executed: [AutoCAD 2024 Core Console]
apps_not_executed: [LibreCAD, FreeCAD, AutoCAD GUI visual QA]
```

This is **not** a completed third-party compatibility matrix. It does not prove:

- LibreCAD or FreeCAD interoperability;
- AutoCAD GUI visual/print QA;
- a real design-office profile;
- real sketch or road engineering correctness;
- IFC/BIM interoperability;
- general CAD compatibility beyond this one synthetic fixture and one host version.

Same-library `ezdxf` read/write remains separate and is never presented as third-party evidence.

## Issue status

- `DEV-CAD-006` / #6 remains open: the AutoCAD 2024 Core Console leg is recorded, but the LibreCAD/FreeCAD/GUI matrix is not executed.
- A host without AutoCAD must record `blocked`, not a pass.

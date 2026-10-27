# E2E-FIXTURE-001 v0.2 — External Review Packet

**Requested disposition:** `pass_for_next_experiment`, `conditional`, or `fail`  
**Current project state:** internal adversarial probes pass; external independent review pending.  
**Important:** the reviewer must not assume the internal report is an independent approval.

## Purpose

Review the synthetic end-to-end contract slice from stored site fixture through environment analysis, provisional CAD-IR, and editable DXF. The review should focus on false-positive risks and mutation detection, not on whether the synthetic drawing looks plausible.

## Before running

1. Verify `review-manifest.json` SHA-256 hashes against the files in this packet.
2. Inspect `working/e2e-integration/adversarial-review-report-v0.2.md` and the checklist.
3. Confirm the v0.1 fixture remains historical and the active fixture is v0.2 / `fixture_revision: r2`.

## Re-run commands

From the unzipped packet root, in a Python environment with Shapely, ezdxf and pytest installed:

```bash
python -m pytest working/environment-analysis/test_solar_shadow.py -q
python working/e2e-integration/run_fixture_benchmark_v0_2.py
python working/e2e-integration/fixture_to_cad_ir_v0_2.py
python working/e2e-integration/compile_fixture_to_dxf_v0_2.py
python working/e2e-integration/run_adversarial_review.py
```

The mutation suite uses temporary copies and should not mutate the canonical fixture or DXF.

## Required review response

Please provide:

- `review_status`: `pass_for_next_experiment`, `conditional`, or `fail`;
- findings with severity, artifact/field, reproduction steps, expected/observed behavior and required changes;
- any false-positive / false-negative concerns;
- whether the packet itself is reproducible in your environment;
- explicit statement that this review does not certify real-site accuracy, third-party CAD compatibility, IFC correctness, professional design correctness or legal compliance.

## Scope limits

This packet contains a synthetic fixture only. It has no real raster-to-Trace input, professional road generation, real project Profile, IFC file, independent solar engine or third-party CAD application round-trip. DXF validation uses ezdxf in a separate code path, not a different CAD application. No A1 or production gate is approved by this packet.

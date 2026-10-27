# Test Suites

```bash
python -m pytest -q
```

| File | Tests | Scope |
|---|---|---|
| `test_foundation_contracts.py` | 21 | Canonical identity, revisions, authority, atomic changes, preview isolation, dependency, locks, audit, migration, gateway |
| `test_runtime_contracts.py` | 22 | Proposals, approvals, jobs, artifacts, idempotency, restart recovery, stale writers, CLI/MCP semantic parity |
| `test_deployment_contracts.py` | 8 | SQLite WAL/CAS, artifact dedup/tamper/reopen, service parity, MCP-unverified marking |
| `test_lifecycle_contracts.py` | 14 | Discovery, pairing, sessions, roles, loopback HTTP security, lease, CAD bridge registration/expiry |
| `test_domain_contracts.py` | 26 | Confirmed trace, building footprint/height, road class/profile, T-junction atomic change set, stale artifacts, validators, runtime integration |
| `test_analysis_contracts.py` | 7 | Solar position, confirmed/unknown blockers, context completeness, dependency fingerprint |
| `test_cad_delivery_contracts.py` | 9 | CAD-IR mapping, DXF compile/readback, mutation detection, bulge/width/LWPOLYLINE semantics |
| `e2e/test_living_pipeline.py` | 8 | Full living pipeline, evidence files, declared unknowns, living-package-only check |
| `e2e/test_e2e_002_mutations.py` | 6 | Height change, node move, north bearing, rebuild worker, manifest comparison, road-surface deferral |
| `e2e/test_e2e_003_adversarial.py` | 20 | Geometry, style, identity, serialization and validator-error adversarial cases |

## Rules

- A test name states the contract, not the implementation.
- Every capability needs at least one negative or adversarial case.
- External dependencies that are unavailable (AutoCAD, FreeCAD, MCP SDK) must be recorded as blockers, not silently skipped.
- A defect found by review becomes a named regression test before the fix.
- Keep fixtures immutable; add a new revision instead of editing an existing one.

See [../docs/development/testing.md](../docs/development/testing.md) for the full strategy.

# Project Status

Updated: 2026-10-27
Version: `0.1.0` (formal workspace)
Research basis: R0 v0.19 + R1 deployment-entry v0.2

## 1. One-line status

The project has a working, tested **governance and runtime contract layer**; it does **not** yet have a domain slice that turns a confirmed sketch/trace into building/road geometry, DXF output, or real-world validated behavior.

## 2. Test baseline

```text
python -m pytest -q
65 passed
```

| Suite | Tests | Status |
|---|---|---|
| Foundation | 21 | passing |
| Runtime | 22 | passing |
| Deployment | 8 | passing |
| Lifecycle | 14 | passing |

## 3. Capability status

| Capability | Status | Notes |
|---|---|---|
| Canonical identity / revision / authority | implemented | three revision axes; proposal-only Agent writes |
| Atomic multi-object changes | implemented | all-or-nothing commit with stale rejection |
| Preview isolation | implemented | preview world cannot mutate canonical current |
| Dependency and stale propagation | implemented | object/profile/method dependency keys; transitive invalidation |
| Audit log | implemented | append-only JSONL in research prototype |
| Stateful runtime | implemented | proposals, approvals, jobs, artifacts, idempotency |
| Human Control Plane | implemented (prototype) | approve/unlock only; separate principal |
| Local sidecar lifecycle | implemented (prototype) | discovery, pairing, sessions, lease, bridge registry |
| SQLite/WAL persistence | spike | not wired into `StatefulRuntime` save/load |
| MCP wire protocol | **blocked** | official SDK unavailable |
| Real AutoCAD / FreeCAD bridge | **blocked** | no host environment |
| Building/Road domain geometry | **not started** | next milestone |
| Real sketch → trace | **not validated** | no Tier B/C data |
| Real design-office profile | **not validated** | synthetic and DB11 subset only |
| IFC round-trip | **blocked** | IfcOpenShell unavailable |
| Independent solar engine | **not validated** | synthetic NOAA baseline only |
| Third-party CAD round-trip | **partial** | one AutoCAD 2022 core-engine user review; defects deferred to development |

## 4. Evidence gates

| Gate | Requirement | Status |
|---|---|---|
| R1-G01 Identity | stable identity across canonical/3D/DXF/IFC | partial (no IFC execution) |
| R1-G02 Authority | no bypass path | pass for prototype scope |
| R1-G03 Dependency | correct stale/local rebuild | pass for contract scope |
| R1-G04 Geometry | representative failure cases fail closed | partial (DXF defects deferred) |
| R1-G05 Delivery | third-party semantic round-trip + real profile | not started |
| R1-G06 Preview | no canonical pollution | pass for prototype scope |
| R1-G07 Real Case | one non-synthetic site sketch | not started |
| R1-G08 Spikes | IFC + independent ENV + real profile | not started |

## 5. Known defects carried forward

These were reproduced after the v0.3 synthetic hardening and are accepted as **development acceptance items**, not research tasks:

- `DEV-CAD-001` MultiPolygon expected-entity contract raises `KeyError`.
- `DEV-CAD-002` entity-type mismatch raises unhandled `AttributeError`.
- `DEV-CAD-003` LWPOLYLINE bulge / constant width mutations are falsely accepted.
- `DEV-CAD-004` raw DXF semantics and canonical geometry are not both validated.
- `DEV-CAD-005` symbol-table name comparison is case-sensitive; AutoCAD normalizes `CONTINUOUS` to `Continuous`.
- `DEV-CAD-006` third-party round-trip matrix not implemented.
- `DEV-CAD-007` some validator failures are not structured issues.
- `DEV-CAD-008` CAD serialization differences vs project profile rules are not fully separated.

See `research/archive/r0-v0.19/working/cad-bim-validator/development-acceptance-contract-v0.1.md`.

## 6. Current non-claims

- `research_complete = false`
- `release_authorized = false`
- No production security approval.
- No production database decision.
- No Chinese road/building daylight compliance conclusion.
- No claim that MCP, AutoCAD, FreeCAD or IFC have been executed.

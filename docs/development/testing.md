# Testing Strategy

Testing is the primary engineering control in this project. Research claims are not promoted by prose; they are promoted by executable evidence with a declared scope.

## 1. Test layers

| Layer | Purpose | Current state |
|---|---|---|
| L0 Contract / conformance | Prove governance invariants: identity, revision, authority, dependency, idempotency, lifecycle | **65 tests passing** |
| L1 Domain contract | Prove building/road/analysis domain objects and adapters | not started |
| L2 Integration | Prove the synthetic E2E pipeline: fixture → analysis → CAD-IR → DXF → readback | archived scripts, not yet in CI |
| L3 Third-party | Prove semantic round-trip through independent CAD/BIM applications | partial; one user-run AutoCAD core-engine review |
| L4 Security / lifecycle | Prove loopback, roles, pairing, lease, bridge expiry, stale writers | 14 lifecycle tests |

A passing lower layer never promotes a higher-layer claim automatically.

## 2. Current suites

| Suite | File | Tests |
|---|---|---|
| Foundation | `tests/test_foundation_contracts.py` | 21 |
| Runtime | `tests/test_runtime_contracts.py` | 22 |
| Deployment | `tests/test_deployment_contracts.py` | 8 |
| Lifecycle | `tests/test_lifecycle_contracts.py` | 14 |

Run all:

```bash
python -m pytest -q
```

Run one suite:

```bash
python -m pytest tests/test_lifecycle_contracts.py -q
```

Coverage:

```bash
python -m pytest -q --cov --cov-report=term-missing
```

## 3. What the current tests prove

- Stable `object_id` survives revisions; revision axes change independently.
- Preview worlds cannot mutate canonical current state.
- Atomic change sets either commit entirely or not at all; stale proposals are rejected.
- External world cannot write canonical directly.
- Locks enforce axis- or field-level protection and require explicit human unlock.
- Dependency invalidation is transitive but scoped to affected artifacts.
- Validation failures are structured, not exception text.
- Canonical hashing is deterministic and rejects non-finite floats.
- Dependency cycles are rejected; rebuild order is topological.
- Proposal rebase is conservative and resets approval on conflict-free rebase.
- Agent gateway injects actor context; the Agent cannot fabricate human confirmation.
- Runtime job recovery is at-least-once; old workers cannot complete reclaimed jobs.
- Two runtime instances detect lost updates rather than overwriting.
- SQLite CAS distinguishes concurrent modification from hash corruption.
- Artifact store deduplicates and detects tampering.
- Discovery is token-free; pairing is role-bound, single-use and cannot escalate.
- Agent tokens are rejected by the human approval route; human tokens are accepted.
- Loopback HTTP rejects non-loopback bind and DNS-rebinding-style Host/Origin.
- Project lease prevents split-brain; expired takeover increments generation.
- CAD bridge registration requires a bridge role and expires without heartbeat.

## 4. What the current tests do **not** prove

- That MCP wire protocol works (no official SDK executed).
- That AutoCAD or FreeCAD host plug-ins work (no host installed).
- That the runtime is production-safe, crash-safe on power loss, or multi-host.
- That SQLite is integrated into the runtime save/load path (it is a separate spike).
- That real sketch recognition, geometry construction, road design or building regularization works.
- That DXF output is compliant with any real project/design-office profile.
- That IFC round-trip preserves identity.
- That shadow analysis matches an independent engine.
- That any Chinese regulatory threshold is satisfied.

Every test file and contract carries this scope boundary. Do not delete or weaken the non-claim statements when adding features.

## 5. Test design rules

1. **Fail closed.** Unknown or unsupported input returns a structured error code, never a default pass.
2. **No silent defaults.** Missing height, scale, north, profile or time must remain `unknown`/`blocked`.
3. **One behavior per test.** Tests are named as contracts, not implementation details.
4. **Adversarial by default.** Every feature needs at least one negative case: stale writer, tampered payload, role escalation, missing prerequisite, malformed entity.
5. **Scope tags.** A test proves only its named scope. Do not rename a scoped test into a global claim.
6. **Fixtures are immutable evidence.** Changing a fixture requires a new revision and a changelog entry.

## 6. Adding a new test layer

When introducing a domain or integration suite:

1. Create a fixture under `fixtures/` with a schema ID and explicit `synthetic_only` / evidence status.
2. Add the test under `tests/<layer>/`.
3. Add the suite to CI.
4. Document what it proves and what it does not prove in this file.
5. If the test depends on an external host (AutoCAD, MCP SDK), mark it `blocked` rather than skipped silently, and record the blocker.

## 7. Regression policy

A defect found by an independent review or user report becomes a named regression test **before** the fix. The test name references the defect ID where one exists (for example `DEV-CAD-001`). Fixes without a failing test are not accepted.

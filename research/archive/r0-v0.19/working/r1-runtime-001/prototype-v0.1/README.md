# Design-Grade CAD Agent — R1 Stateful Runtime Entry v0.1

This is a **research-only executable contract prototype**, not production CAD software.

It extends the 21-contract Foundation prototype with a stateful runtime layer for project persistence, proposal/approval/job/artifact registries, idempotency, recovery and transport parity.

## Current result

```text
21 Foundation contract tests
22 Runtime contract tests
43 total tests passing
```

Run:

```bash
python -m pytest -q
```

## Proven architecture direction

```text
Agent
  -> MCP / CLI adapter
  -> AgentToolSurface
  -> StatefulRuntime
       -> Human Control Plane (separate privileged path)
       -> Project / Proposal / Approval / Job / Artifact registries
       -> Foundation Core
       -> domain workers later
```

The Agent never receives a raw canonical write API and cannot mint human approval.

## Important files

- `runtime-contract-register-v0.1.yaml`
- `stateful-runtime-architecture-v0.1.md`
- `recovery-idempotency-policy-v0.1.md`
- `contracts/runtime-agent-surface-v0.1.yaml`
- `contracts/runtime-state-contract-v0.1.yaml`
- `runtime-entry-review-v0.1.md`

## Scope limits

The persistence layer is deliberately a single atomic JSON envelope so runtime semantics can be tested without prematurely choosing a database. The MCP and CLI adapters are semantic shims, not wire-level implementations.

Do not interpret 43/43 as production readiness.

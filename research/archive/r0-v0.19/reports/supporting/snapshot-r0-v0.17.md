# R0 v0.17 snapshot — Stateful Runtime contract checkpoint

Date: 2026-10-27

## Mainline position

`NEXT-R1-RUNTIME-001` reached a bounded research checkpoint. The project now has an executable, protocol-neutral stateful runtime prototype above the Foundation Core.

## Evidence

- Foundation contract tests: 21/21 passing.
- Runtime contract tests: 22/22 passing.
- Combined: 43/43 passing after clean ZIP extraction.
- Runtime prototype includes project persistence, idempotency, proposal/approval/job/artifact registries, restart recovery, transitive stale/rebuild scheduling, optimistic concurrent-writer detection, CLI/MCP semantic parity, and server-side human approval separation.

## Important architecture result

Recommended integration shape remains:

```text
Agent -> MCP adapter -> DGCAD Runtime -> Foundation Core -> domain workers/adapters
                         ^
                         |
                 Human Control Plane
```

Approval/unlock are server-side state and are not Agent tool arguments.

## Explicit non-claims

This snapshot does not establish production database durability, distributed locking, network authentication, actual MCP wire interoperability, CAD application bridge execution, multi-user collaboration, or production release readiness.

## Next action

`NEXT-R1-RUNTIME-002`: deployment-boundary research: local sidecar vs CAD-embedded bridge vs remote service; local transactional storage candidate; single-writer process lifecycle; actual MCP/CLI binding; Human Control Plane handshake; CAD bridge boundary.

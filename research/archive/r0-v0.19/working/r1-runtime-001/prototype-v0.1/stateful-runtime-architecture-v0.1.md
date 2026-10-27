# Stateful Runtime Architecture v0.1

Status: **research checkpoint / provisional**.

## Why a runtime exists

The Agent must not own canonical CAD state. The runtime is the authority boundary between probabilistic intent generation and deterministic project mutation.

```text
Agent / LLM
    |
    v
Agent adapter (MCP first; CLI parity)
    |
    v
Agent Tool Surface
    |
    +---- inspect / propose / preview / validate / request_commit / rebuild / export
    |
    v
DGCAD Runtime  <---------------- Human Control Plane
    |                                 |
    |                                 +-- approve / unlock / resolve conflict
    |
    +-- Project Store
    +-- Proposal Registry
    +-- Approval Registry
    +-- Job Registry
    +-- Artifact Registry
    +-- Idempotency Registry
    +-- Audit
    |
    v
Foundation Core
    |
    +-- Canonical Site IR
    +-- authority / revisions / locks
    +-- dependency graph
    +-- deterministic validators
    |
    +------> domain adapters / workers
             road | building | shadow | DXF | IFC | CAD bridge
```

## Runtime is not the Agent

The runtime does not decide what a good site plan is. It decides whether an attempted state transition is admissible, reproducible, attributable and recoverable.

The Agent may propose intent. The runtime owns project mutation.

## Recommended agent-facing shape

The long-term agent integration should expose **intent-level tools**, not internal CRUD.

Preferred examples:

- `scene_summary`
- `object_view`
- `propose_change`
- `propose_changeset`
- `preview_change`
- `validate`
- `request_commit`
- `rebuild_stale`
- `job_status`
- `export`
- `reconcile_external`

The following should not be Agent tools:

- raw `set_field`
- raw SQL / JSON writes
- `is_human=true`
- `confirmed=true`
- approval-token minting
- arbitrary Python execution inside the canonical process

## Human approval model

Approval is **server-side state**, not an Agent-supplied boolean.

A Human Control Plane issues an approval grant bound to:

- proposal identity;
- complete ChangeSet hash;
- scene revision;
- grant kind (`confirm` / `unlock`);
- human actor;
- expiration.

The Agent later calls only `request_commit(proposal_id)`. The runtime locates and consumes a valid grant. The grant is never created by the Agent tool surface.

## Persistence model proven in this research prototype

The prototype intentionally uses one atomically-replaced, hash-enveloped JSON state file so registry/canonical/audit transitions can be tested without introducing a database dependency.

It proves semantics, not the production storage engine.

For a real local-first R1 implementation, the leading provisional shape is:

```text
SQLite metadata / transactions
+ content-addressed artifact directory
+ worker processes
+ project-scoped runtime service
```

For later multi-user/cloud operation, this may evolve to a transactional server database plus object storage and distributed workers. This is not yet an adoption decision.

## Concurrency semantics

The prototype uses optimistic compare-and-swap of the persisted state hash. Two stale runtime instances cannot silently overwrite each other.

This is deliberately weaker than a production database transaction / lock system. A runtime instance that hits `PROJECT_STATE_CONCURRENT_MODIFICATION` must be discarded or reloaded.

## Job semantics

The worker contract is **at least once**, not exactly once.

Therefore:

- jobs have attempt generations;
- completion is bound to `(job_id, worker_id, attempt)`;
- a restarted runtime requeues interrupted jobs;
- the old worker cannot complete after another worker reclaims the job;
- builders should produce deterministic/content-addressed artifacts where feasible.

## CLI / MCP relationship

CLI and MCP are adapters, not separate implementations. Both must call the same `AgentToolSurface` and therefore produce the same authority, idempotency and validation behavior.

The current `McpAdapter` is only a protocol-neutral shim proving semantic parity. It is **not evidence of wire-level MCP conformance**.

## Deployment shape: provisional recommendation

For the first real implementation, prefer a **local project runtime / sidecar** on the designer's workstation:

```text
ChatGPT / other Agent
       |
     MCP
       |
DGCAD local runtime
  |        |       |
review UI  CLI   CAD bridge
  |
SQLite + artifact store
```

Reasons:

1. project files and CAD applications are often local;
2. AutoCAD/FreeCAD bridges may require workstation-local access;
3. the human review/control plane benefits from being near the design application;
4. Agent model/provider can change without changing canonical project storage.

Heavy remote compute can later be attached as workers without moving authority into the LLM.

## Remaining runtime research gaps

- database transaction choice and migration strategy;
- OS/process ownership and project locking;
- session authentication and cryptographic actor identity;
- approval provenance stronger than local trusted storage;
- worker leases / heartbeat / distributed retry;
- content-addressed artifact store and garbage collection;
- structured validation-job integration;
- actual CLI parser and actual MCP server implementation;
- CAD-process bridge contract;
- multi-user merge and branch semantics;
- runtime schema migration across versions.

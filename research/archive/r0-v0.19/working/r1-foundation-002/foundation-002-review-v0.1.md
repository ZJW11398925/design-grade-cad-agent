# NEXT-R1-FOUNDATION-002 Review v0.1

**Status:** `foundation-v0.2-research-candidate`  
**Date:** 2026-10-27

## Scope

This checkpoint addresses Foundation-only questions and the final Agent integration shape. It deliberately does not add road, building, sketch, DXF/IFC or environmental domain capabilities.

## Executable findings

The standalone prototype v0.2 currently passes **21 contract tests**. Added coverage includes:

- deterministic canonical serialization/hash;
- rejection of non-finite canonical numeric state;
- dependency-cycle rejection;
- dependency-safe rebuild ordering;
- append-only audit events with JSONL round-trip;
- conservative stale-proposal rebase;
- fail-closed same-field rebase conflict;
- field-path lock behavior;
- explicit schema migration registry;
- transport-agnostic AgentGateway with host-injected ActorContext;
- no Agent-exposed raw canonical mutation.

These are research contracts, not persistence, security or distributed-system production qualification.

## Agent integration candidate

Recommended shape:

`Agent -> MCP adapter -> DGCAD Runtime -> Foundation Core -> Domain/Adapter modules`

Human approval is a separate authenticated control-plane path. MCP is preferred as the first Agent protocol because its tool/resource split maps naturally to action vs read-only design context. Foundation remains protocol-agnostic and must also be callable through CLI/tests.

A2A is deferred. It becomes relevant only if DGCAD is later packaged as an independent specialist Agent with its own task lifecycle, rather than a controlled tool/runtime.

## Remaining Foundation research before freeze

- durable project store and crash/recovery semantics beyond JSONL audit evidence;
- idempotency keys and retry semantics for side-effecting tools;
- proposal registry lifecycle / cancellation / expiry;
- job registry and restart-safe derived rebuild scheduling;
- capability/authentication model for multi-process or remote runtime;
- canonical schema migration across persisted project versions;
- large geometry/artifact reference policy;
- protocol adapter spike proving CLI and MCP map to the same runtime commands without authority leakage.

## Verdict

`foundation_v0_2_survives_with_runtime_boundary`

The new evidence supports moving the next Foundation research from in-memory object semantics to a **stateful runtime boundary**. It does not authorize domain feature expansion yet.

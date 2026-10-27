# Design-Grade CAD Agent — R1.0 Foundation Entry Prototype v0.2

**Status:** research-entry prototype, not production CAD software.

This repository intentionally contains **no AI model, no geometry kernel, no DXF/IFC adapter, no UI, and no road/building design algorithm**. Its only job is to test whether the R0 architecture can be expressed as executable contracts before domain features are added.

## What this prototype proves if tests pass

- stable canonical object identity survives revisions;
- semantic / geometry / parameter revision axes can be changed independently;
- proposals are checked against the exact revision they were based on;
- multi-object changes are all-or-nothing;
- preview snapshots cannot mutate canonical current state;
- locked design state requires explicit human unlock;
- external artifacts cannot directly overwrite canonical truth;
- dependency invalidation can remain local;
- validator failures are structured data rather than uncaught exception text;
- first typed fixtures are machine-parseable.

## What it does not prove

It does **not** prove sketch recognition, geometry correctness, road engineering, building regularization, BIM round-trip, DXF compliance, environmental accuracy, or professional design quality. Those remain behind the R1 Evidence Gates.

## Run

```bash
python -m pytest
```

## Entry rule

No domain adapter should be added until these Foundation contracts are stable enough to support R1-G01/G02/G03/G06 contract testing.

## v0.2 Foundation-only additions

The second entry prototype adds deterministic serialization/hashing, dependency-cycle rejection, dependency-safe rebuild planning, append-only audit JSONL, conservative proposal rebasing, field-path locks, explicit schema migration and a transport-agnostic `AgentGateway`.

The Agent-facing decision is now explicit: internal Foundation classes are **not** the final Agent API. See:

- `agent-integration-architecture-v0.1.md`
- `agent-authority-boundary-v0.1.md`
- `contracts/agent-tool-contract-v0.1.yaml`

The preferred first protocol adapter is MCP, but MCP is deliberately absent as a runtime dependency in this prototype. The contract must remain usable from CLI/tests and a future human UI without protocol logic entering Foundation Core.

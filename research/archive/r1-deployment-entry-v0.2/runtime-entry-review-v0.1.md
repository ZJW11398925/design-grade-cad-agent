# R1 Runtime Entry Review v0.1

## Verdict

**`stateful_runtime_contract_checkpoint_passed / production_runtime_not_authorized`**

## Test result

- Foundation contracts: 21/21
- Runtime contracts: 22/22
- Total: 43/43

## What this checkpoint establishes

The research prototype demonstrates a coherent path from protocol-neutral Agent intent to persisted runtime state while preserving canonical authority boundaries across restart, retries and common failure cases.

Most importantly, it demonstrates that MCP/CLI can be thin adapters over one runtime instead of becoming independent implementations.

## Defects found during adversarial review

The first runtime implementation passed 37 tests but further probes found:

1. transient `empty` job claims were incorrectly cacheable;
2. recovered jobs had no claim-generation protection against old-worker completion;
3. two concurrently loaded runtime instances could overwrite each other without optimistic state comparison;
4. the agent entry surface could not yet register a genuine multi-object AtomicChangeSet;
5. mixed `human_unlock` + `human_confirm` operations needed explicit whole-ChangeSet approval semantics.

All five are now represented by regression contracts.

## Explicit limits

This checkpoint does **not** prove:

- production database durability;
- real multi-process locking;
- authenticated network sessions;
- cryptographic human identity;
- distributed workers;
- actual MCP protocol interoperability;
- AutoCAD/FreeCAD bridge execution;
- road/building/domain correctness;
- release readiness.

## Recommended next research action

`NEXT-R1-RUNTIME-002` should stop extending in-memory semantics and challenge the proposed deployment boundary:

1. local sidecar vs embedded CAD plugin vs remote service;
2. local transactional storage candidate (SQLite) and artifact-store split;
3. project single-writer ownership / process lifecycle;
4. actual MCP server binding and CLI command parity;
5. Human Control Plane handshake;
6. CAD bridge boundary for AutoCAD/FreeCAD without granting the Agent raw application control.

Domain feature development should still remain out of scope until this boundary is stable enough to host it.

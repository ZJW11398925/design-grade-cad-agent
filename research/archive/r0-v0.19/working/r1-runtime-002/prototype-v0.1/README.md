# Design-Grade CAD Agent — Deployment Entry v0.1

Research-only prototype for `NEXT-R1-RUNTIME-002`.

## Current verdict

**Recommended R1 deployment direction:** local sidecar runtime + thin CAD-local bridges + separate Human Control Plane + MCP/CLI adapters. Optional remote workers may be added later, but they do not own canonical project state.

This package does **not** claim production readiness, actual AutoCAD/FreeCAD bridge execution, or wire-level MCP interoperability.

## What is executable here

- the full Foundation + Stateful Runtime suite from the previous checkpoint;
- SQLite/WAL project-state spike with deterministic payload hash and compare-and-swap revision;
- content-addressed artifact store;
- SQLite artifact metadata registry;
- two-connection stale-writer rejection;
- disk/hash corruption detection;
- CLI adapter that calls the same `DeploymentService` as the agent surface;
- machine-readable deployment/CAD-bridge/MCP contracts.

Run:

```bash
python -m pytest -q
```

Expected at this checkpoint: **51 passed**.

## Important MCP limitation

The official MCP Python SDK v2 is not installed in the current environment. A `pip install 'mcp>=2,<3'` attempt failed because DNS/network resolution was unavailable. Official documentation was reviewed and the binding contract was updated, but no wire-level MCP server/client test was executed.

## Key files

- `deployment-boundary-decision-v0.1.md`
- `deployment-mode-matrix-v0.1.yaml`
- `sqlite-artifact-spike-v0.1.md`
- `human-control-plane-boundary-v0.1.md`
- `deployment-boundary-review-v0.1.md`
- `contracts/deployment-boundary-contract-v0.1.yaml`
- `contracts/mcp-binding-v0.2.yaml`
- `contracts/cad-bridge-contract-v0.1.yaml`
- `source-locators.md`

## State semantics

- `research_complete=false`
- `release_authorized=false`

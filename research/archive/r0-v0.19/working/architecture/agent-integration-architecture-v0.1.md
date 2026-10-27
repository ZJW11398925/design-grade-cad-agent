# Agent Integration Architecture v0.1

**Status:** research candidate. This document answers how the Design-Grade CAD capability should ultimately be presented to an Agent; it does not start product integration.

## 1. Recommendation

Do **not** make the Agent import the internal Python package and do **not** expose the Canonical Store as a generic CRUD API.

Use four layers:

1. **`dgcad-core`** — deterministic typed library: Canonical IR, revisions, authority, dependency, validators. No Agent protocol dependency.
2. **`dgcad-runtime`** — stateful application/control-plane service that owns projects, proposal records, previews, audit history, jobs, artifact registry and authenticated actor context.
3. **`dgcad-mcp`** — thin Agent-facing protocol adapter. It translates MCP tools/resources into `dgcad-runtime` operations. It owns no design truth.
4. **`dgcad-cli` / test harness** — deterministic developer and CI entrypoint using the same runtime API without an LLM.

A human review UI is a **separate privileged client** of `dgcad-runtime`, not another Agent tool.

## 2. Why MCP is the preferred first Agent surface

Current MCP SDK documentation separates **tools** (model chooses an action), **resources** (read-only application-provided context) and **prompts** (user-invoked templates). That split matches this project well: scene/object/validation state are resources; proposal/preview/validate/export are tools.

MCP is therefore a transport/adaptation layer, not the architectural core. The same runtime should remain callable from CLI, tests, a desktop UI or a future HTTP API.

## 3. Why A2A is not the first interface

A2A is aimed at communication between independent agentic systems. The A2A specification itself distinguishes agent-to-agent communication from MCP-style agent-to-tool communication.

The CAD Foundation should initially behave as a **tool/runtime**, not as an autonomous peer Agent. A future specialist “CAD Design Agent” may expose A2A after it has its own task lifecycle and autonomous orchestration, but that is R2+ and must wrap the same controlled runtime.

## 4. Trust boundary

```text
LLM / Agent
    |
    | MCP tools + read-only resources
    v
Agent Gateway (unprivileged session)
    |
    | typed application commands
    v
DGCAD Runtime / Control Plane
    |---- server-injected ActorContext
    |---- proposal registry
    |---- preview registry
    |---- audit/event log
    |---- job/artifact registry
    v
Foundation Core
    |---- Canonical Store
    |---- Authority
    |---- Dependency DAG
    |---- Validation contracts
    v
Domain / geometry / analysis / CAD-BIM adapters
```

A human UI reaches the runtime through a separate authenticated control path:

```text
Human reviewer UI ---> approve / reject / unlock / resolve
                         |
                         v
                    DGCAD Runtime
```

The Agent never receives a boolean such as `is_human=true` as a tool argument. Identity and privileges are injected by the host/runtime.

## 5. Agent sees intentions, not raw mutations

Bad Agent surface:

```text
set_object_field(object_id, path, value)
execute_python(code)
write_canonical_json(blob)
```

Preferred surface:

```text
propose_change(...)
preview_change(...)
validate(...)
request_commit(...)
reconcile_external(...)
rebuild_stale(...)
export(...)
```

Domain-specific tools can later exist, e.g. `road.propose_node_move` or `building.propose_height_change`, but each must compile into Foundation `ChangeProposal` / `AtomicChangeSet` objects and pass the same authority and validation path.

## 6. Read model vs write model

The Agent should inspect state through compact read models/resources rather than loading the entire Canonical IR into every prompt.

Recommended resources:

- scene summary;
- object view;
- proposal diff;
- preview snapshot summary;
- validation evidence;
- stale artifact status;
- applicable rule/profile summary.

Large geometry should be referenced by artifact/geometry IDs and retrieved only when needed. The Agent should reason over semantically meaningful summaries while deterministic geometry code owns exact coordinates.

## 7. Human-in-the-loop behavior

For a human-confirmed design change:

```text
Agent -> cad.propose_change
      -> cad.preview_change
      -> cad.validate
      -> cad.request_commit
             |
             +-- approval_required
                     |
Human UI ------------+
      -> approve proposal
      -> runtime commits AtomicChangeSet
      -> stale propagation
      -> rebuild derived artifacts
```

The Agent may explain why approval is needed, but cannot satisfy the approval requirement itself.

## 8. Long-running work

Geometry generation, IFC export, shadow analysis and future optimization may become long-running. The runtime should therefore own job IDs and artifact lifecycle. The Agent tool call should receive a structured job/artifact reference rather than keeping the model call alive while domain work runs.

This runtime job model should be protocol-neutral. MCP, CLI and future UI adapters consume the same job state.

## 9. Recommended packaging trajectory

### R1.0
- `dgcad-foundation` Python library;
- in-process `AgentGateway` research facade;
- CLI contract harness;
- protocol-neutral typed tool contract.

### R1.1–R1.5
- stateful local runtime/daemon;
- MCP adapter over the runtime;
- separate human approval UI/control endpoint;
- domain tools added behind Evidence Gates.

### R2+
- remote multi-user runtime if needed;
- optional HTTP/gRPC SDK surface;
- optional A2A wrapper only if DGCAD becomes an independent specialist agent.

## 10. Architectural decision candidate

**Candidate:** `ADR-AGENT-001`

> The primary Agent integration shall be a narrow capability gateway over a stateful DGCAD runtime. MCP is the preferred first protocol adapter. Canonical mutation, human confirmation, unlock and rule promotion are not exposed as self-assertable Agent capabilities. The internal Foundation remains protocol-agnostic.

This decision should be challenged in R1 by testing whether the same contract works from CLI and MCP without protocol-specific logic leaking into Foundation.

## References

- Model Context Protocol Python SDK, server concepts: https://py.sdk.modelcontextprotocol.io/servers/
- Model Context Protocol Python SDK, first steps: https://py.sdk.modelcontextprotocol.io/get-started/first-steps/
- Agent2Agent Protocol specification: https://a2a-protocol.org/latest/specification/

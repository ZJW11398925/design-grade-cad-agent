# DGCAD Local Sidecar Startup & Connection Lifecycle v0.1

Status: **research candidate**. This document defines the R1 interactive startup path. It is not a production installer/service specification.

## 1. Recommended ownership

For the interactive R1 product, the **DGCAD Desktop/Tray Launcher** owns the sidecar lifecycle. Neither the LLM Agent nor the AutoCAD/FreeCAD bridge owns the canonical runtime process.

A CAD bridge may ask the launcher to start DGCAD when discovery is absent, but it does not become the runtime owner. The MCP adapter normally discovers an already-running runtime. CLI/CI may create an ephemeral runtime for isolated automation.

## 2. Startup order

```text
User launches DGCAD / DGCAD-enabled CAD command
        ↓
Trusted local launcher
        ↓
Acquire project single-writer lease
        ↓
Bind 127.0.0.1:<random-port>
        ↓
Publish token-free discovery record
        ↓
Mint one-time role-bound pairings OUT OF BAND
   ├─ agent/MCP adapter pairing
   ├─ human review pairing
   └─ CAD bridge pairing
        ↓
Each component exchanges its pairing for a short-lived bearer session
        ↓
CAD bridge registers current host/document context
        ↓
Agent may inspect/propose/preview; Human Review owns approve/unlock
```

The ordering is intentional. Discovery is not published until the project lease and loopback bind both succeed. This avoids advertising a runtime that does not own the project.

## 3. Discovery

The discovery record contains only:

- schema/version;
- runtime instance ID;
- PID;
- loopback host/port;
- protocol;
- start time;
- lease generation.

It contains **no bearer token, pairing token, approval token or human capability**.

The POSIX spike writes this file with mode `0600`. Windows ACL/DPAPI handling remains unverified and must be implemented separately before a Windows production claim.

## 4. Pairing and capability sessions

Pairing is a bootstrap handoff from a trusted launcher/control plane to one intended component. A pairing grant is bound server-side to exactly one role and actor. The exchange endpoint does not accept a requested role.

Therefore an Agent that receives an `agent` pairing cannot submit `role=human_review` and escalate. Pairings are short-lived and single-use. The exchanged bearer token is also short-lived and revocable.

The research roles are:

- `agent`: inspect/propose/preview/request_commit/rebuild;
- `human_review`: approve/unlock/review/conflict resolution;
- `cad_bridge`: external document read/write/view synchronization only;
- `cli_admin`: development/CI parity with the agent semantic surface, not human approval.

## 5. HTTP security boundary

The local research control server binds loopback only. It rejects non-loopback bind configuration, validates `Host`, validates `Origin` when present, and requires bearer capability checks on privileged routes.

This mirrors the current MCP SDK guidance for local Streamable HTTP, which enables localhost Host/Origin protections against DNS rebinding by default. The prototype control server is **not MCP** and does not claim MCP conformance.

## 6. Project single-writer lease

The local project store holds a short runtime lease with:

- `project_id`;
- `instance_id`;
- lease generation;
- expiry time.

A second runtime cannot acquire the same project while the first lease is live. After expiry, another runtime may take over with a higher generation. The old runtime then fails heartbeat and must stop mutating.

This is an R1 local split-brain guard, not a distributed consensus protocol.

## 7. CAD bridge lifecycle

A CAD bridge connects with the `cad_bridge` role, then registers:

- host type (`autocad`, `freecad`, ...);
- host PID;
- current document key/fingerprint;
- heartbeat TTL.

Bridge expiry means the runtime stops assuming the external application is reachable. A bridge may write/update external CAD representation only after runtime instruction; it cannot write canonical state or create human approvals.

Current executable evidence covers generic bridge register/heartbeat over loopback HTTP. No AutoCAD or FreeCAD host exists in this container, so actual host-plugin exchange remains blocked.

## 8. Shutdown

Preferred graceful shutdown:

1. stop accepting new mutations;
2. let running jobs finish or mark them recoverable;
3. invalidate in-memory sessions and unconsumed pairings;
4. stop the loopback service;
5. release the project lease;
6. remove the discovery record only if it is still owned by this instance.

Forced process death requires lease expiry and existing job-recovery semantics. A future desktop implementation should shorten recovery through an OS process supervisor, but must not bypass lease generation checks.

## 9. User-visible startup path

The intended user experience is approximately:

```text
Open AutoCAD
↓
DGCAD bridge loads
↓
Bridge sees no runtime → asks DGCAD Launcher to start
↓
DGCAD tray/review UI appears and attaches current drawing to project
↓
Agent host connects through MCP using an agent-scoped session
↓
User: “把 3 号楼往东移 3 米，看看下午阴影”
↓
Agent creates Proposal + Preview
↓
Human Review UI shows diff / shadow / validation
↓
User approves
↓
Runtime commits canonical revision
↓
CAD bridge receives rebuild/update instruction
↓
AutoCAD external representation updates
```

The critical invariant is that the user approval happens in the Human Control Plane, not by trusting a natural-language statement from the Agent.

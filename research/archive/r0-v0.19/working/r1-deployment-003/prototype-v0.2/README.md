# Design-Grade CAD Agent — R1 Deployment Entry v0.2

Status: **research-only deployment/lifecycle checkpoint**. Not a production release, not a security certification, not a validated AutoCAD plug-in.

This package extends the v0.1 deployment-boundary spike into `NEXT-R1-DEPLOY-003`: local sidecar startup/discovery, role-bound pairing, loopback HTTP control plane, single-writer project lease, Human Review separation, and CAD bridge registration/heartbeat.

## Current executable result

```bash
python -m pytest -q
```

Expected in this snapshot:

```text
65 passed
```

The 65 tests include the previous Foundation + Stateful Runtime + SQLite/artifact deployment contracts plus lifecycle/security contracts.

A separate child-process probe is recorded in:

- `spikes/sidecar-process-probe-result.json`

It demonstrates an actual child process and TCP loopback boundary:

1. child acquires the project lease;
2. child binds a random `127.0.0.1` port;
3. child publishes token-free discovery;
4. trusted launcher hands a mode-0600 one-time agent pairing token out of band;
5. recipient deletes the handoff file after reading it;
6. client exchanges pairing for an `agent` bearer session;
7. authenticated `/whoami` reports `agent`;
8. child stops, releases lease and removes discovery.

This is **not MCP traffic**. The official MCP Python SDK is unavailable in this environment, so wire-level MCP conformance remains blocked.

## Recommended interactive shape

```text
DGCAD Desktop/Tray Launcher
        │ owns lifecycle
        ▼
Local Sidecar Runtime (canonical authority)
   ├─ MCP adapter         → Agent role
   ├─ Human Review UI     → approve/unlock role
   ├─ AutoCAD thin bridge → external CAD role
   ├─ FreeCAD thin bridge → external CAD role
   └─ CLI                 → dev/CI role
```

The Agent does not own the runtime process, project DB, Human approval, or CAD host credentials.

## Key contracts

- `contracts/sidecar-lifecycle-contract-v0.1.yaml`
- `contracts/local-auth-capability-contract-v0.1.yaml`
- `contracts/cad-bridge-lifecycle-contract-v0.2.yaml`
- `startup-connection-lifecycle-v0.1.md`
- `local-sidecar-threat-model-v0.1.md`
- `deployment-lifecycle-review-v0.1.md`

## Important boundaries

- Discovery never contains bearer/pairing secrets.
- Pairing grants are bound to one server-side role before exchange and are single-use.
- Agent, Human Review, and CAD Bridge are separate principals.
- Agent cannot call the Human approval route with an Agent token.
- Local HTTP binds loopback only and validates `Host` / `Origin`.
- One project has one active sidecar writer lease; expired takeover increments generation.
- CAD bridge authority expires without heartbeat and cannot mutate canonical state directly.

## Explicit gaps

- No official MCP SDK execution / OAuth resource-server test.
- No AutoCAD or FreeCAD host is installed here; actual host plug-in message exchange is unexecuted.
- POSIX file mode `0600` is tested; Windows ACL/DPAPI handoff is not.
- Same-OS-user malware resistance is out of scope for this R1 prototype.
- Lease timing under suspend/resume and forced process termination needs production hardening.

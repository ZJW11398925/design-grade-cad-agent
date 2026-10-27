# Local Sidecar Threat Model v0.1

Scope: R1 same-machine deployment. This is a research threat model, not a security certification.

## Assets

- canonical project state and revisions;
- human approvals/unlocks;
- proposal and audit history;
- generated artifacts;
- CAD external document linkage;
- local bearer/pairing credentials.

## Trust boundaries

- LLM/Agent is **not** a human principal;
- Human Review UI is privileged for approve/unlock;
- CAD bridge is privileged only for external CAD representation operations;
- the local Runtime is the canonical authority;
- discovery metadata is not a credential;
- project DB/artifacts are not directly exposed to Agent tools.

## Covered attacks in this spike

| Threat | Research defense |
|---|---|
| Agent claims human authority | separate server-side role/capabilities; no approval field on agent tools |
| Agent asks session exchange for human role | pairing role fixed before exchange; exchange takes no role selector |
| Pairing replay | one-time pairing grant |
| Long-lived stolen token | short TTL + revocation semantics |
| DNS rebinding/browser drives localhost | loopback bind + Host/Origin validation |
| Two local runtimes mutate same project | SQLite lease + generation |
| Old runtime resumes after takeover | heartbeat generation mismatch |
| Agent impersonates CAD bridge | bridge capability required |
| Bridge B heartbeats Bridge A | actor-bound bridge session |
| Runtime dies leaving discovery | graceful cleanup + lease expiry; stale discovery detection still to harden |

## Not yet covered

- hostile process running as the same OS user reading local files/memory;
- Windows token/ACL/DPAPI implementation;
- signed binaries / installer trust / update chain;
- real OAuth 2.1 / MCP resource server;
- browser UI CSRF beyond bearer + Host/Origin boundary;
- remote/multi-host deployment;
- malicious CAD drawing exploiting host application/plugin APIs.

Same-user hostile-process resistance should not be overstated. R1 security primarily prevents accidental/Agent privilege escalation and browser/network-style localhost abuse; it is not a sandbox against malware with the user's OS privileges.

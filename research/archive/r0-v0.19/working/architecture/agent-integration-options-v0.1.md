# Agent Integration Options v0.1

| Form | Benefit | Main problem | R1 decision |
|---|---|---|---|
| Agent imports Python library directly | simplest prototype | Agent process gains excessive coupling and mutation reach | reject as final surface |
| CLI only | deterministic, easy CI | awkward context, approvals and structured interactive use | keep as developer/test adapter |
| Generic REST API only | broad client compatibility | every Agent needs custom wrapper/tool schema | useful runtime API later, not primary Agent UX |
| MCP server with state embedded inside server | good Agent tool UX | protocol server becomes architecture/core and persistence boundary | avoid |
| Stateful DGCAD Runtime + thin MCP adapter | stable truth/authority boundary; replaceable Agent clients | one additional service layer | **preferred** |
| A2A specialist Agent | cross-agent delegation | too autonomous/high-level for current controlled CAD engine | defer to R2+ |
| Prompt/Skill only | easy onboarding | cannot enforce geometry, authority or validation | use only as workflow guidance |

## Preferred packaging

1. `dgcad-core` — protocol-agnostic typed contracts and deterministic logic.
2. `dgcad-runtime` — project state, proposals, previews, approvals, audit, jobs, artifacts.
3. `dgcad-mcp` — Agent-facing MCP adapter exposing narrow tools/resources.
4. `dgcad-cli` — CI/debug/manual deterministic adapter.
5. `dgcad-review-ui` — human confirmation/unlock/conflict-resolution client.
6. `dgcad-agent-skill` — optional thin instruction package describing the safe workflow; never an enforcement layer.
7. `dgcad-a2a` — optional future wrapper only if DGCAD itself becomes a remote specialist Agent.

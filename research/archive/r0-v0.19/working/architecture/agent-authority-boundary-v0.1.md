# Agent Authority Boundary v0.1

## Core rule

The Agent can **observe, propose, preview, request validation, request export, request derived rebuild, and request commit**. It cannot self-grant human identity, unlock a protected scope, promote a candidate rule, or bypass the proposal/validation path.

## Capability classes

| Capability | Agent | Deterministic runtime | Human/control plane |
|---|---:|---:|---:|
| Read scene/object summaries | yes | yes | yes |
| Create candidate proposal | yes | yes | yes |
| Preview proposal | yes | yes | yes |
| Run validator | yes | yes | yes |
| Rebuild stale derived artifact | request | yes | yes |
| Export derived CAD/IFC | request | yes | yes |
| Commit deterministic derived metadata | no direct write | yes, if policy permits | yes |
| Commit design-intent change requiring confirmation | request only | no without approval token | yes |
| Unlock geometry/parameter/semantic scope | no | no | yes |
| Resolve ambiguous external reconciliation | propose | no silent resolution | yes |
| Promote rule/profile authority | no | no | yes/authorized admin |
| Direct canonical CRUD | no | internal only | no generic CRUD |

## Security invariant

`ActorContext` is created from authenticated session/process context. Any tool input fields that attempt to declare `is_human`, `can_unlock`, `confirmed`, or `unlock_confirmed` are invalid by contract.

## Design invariant

Agent-facing tools describe **intent and requested operation**, while Foundation contracts decide whether the operation is legal. This keeps model behavior replaceable and prevents prompt wording from becoming an authority mechanism.

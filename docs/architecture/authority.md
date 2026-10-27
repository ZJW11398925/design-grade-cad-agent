# Authority and Permission Model (Living)

Status: living architecture document
Promoted from: `research/archive/r0-v0.19/working/architecture/agent-authority-matrix-v0.1.md`
Implementation: `src/dgcad_foundation/authority.py`, `src/dgcad_runtime/control.py`

## 1. Roles

| Role | Purpose | Canonical write authority |
|---|---|---|
| Agent | propose changes, orchestrate tools, explain evidence | none |
| Deterministic engine | compute geometry, compile, analyze | only `deterministic_auto` derived representations |
| Rule/Profile engine | resolve applicability, parameters, overrides | none directly; produces rule bindings |
| Validator | evaluate and reject within a declared scope | none |
| Human reviewer/designer | confirm intent, unlock protected objects, approve project profile | the only source of `human_confirmed`/unlock |
| CAD bridge | read/write external CAD representation | external representation only; never canonical |

## 2. Permission codes

- `R` — read.
- `P` — propose, but not commit as confirmed.
- `E` — execute deterministic computation; result still subject to authority state.
- `C` — confirm and authorize canonical write.
- `V` — validate/reject, but not modify design.
- `LOCK` — automatic modification forbidden.

## 3. Permission matrix

| Action | Agent | Deterministic engine | Rule/Profile | Validator | Designer/Human |
|---|---|---|---|---|---|
| Read Source/Trace/Canonical | R | R | R | R | R |
| Modify original Source | LOCK | LOCK | LOCK | LOCK | new Source revision only |
| Create segmentation/trace candidate | P | E | — | V | C/revise |
| Confirm object semantics | P | — | constraints | V | C |
| Snap/node/validity repair | P | E | — | V | C if design meaning changes |
| Road class/function assignment | P | candidate | constraints | V | C when evidence insufficient |
| Select design profile | P | — | resolve | V | C when project context unclear |
| Generate centerline/alignment candidate | P | E | parameter constraints | V | C |
| Modify locked road control point | LOCK | LOCK | LOCK | — | C after explicit unlock |
| Building regularization | P | E | constraints | V | C |
| Assign unknown building height | P | — | constraints | V | C |
| Extrude massing from confirmed height | P | E | — | V | automatic derived commit allowed |
| Set mandatory/project parameters | LOCK | — | E (verified profile only) | V | C/project override |
| Update canonical confirmed geometry | P | — | — | V | C, or authorized deterministic rule |
| Generate DXF/IFC | P | E | profile input | V | no per-entity confirmation |
| Accept third-party round-trip difference | P | — | policy input | V | C when outside policy |
| Clear stale state | LOCK | only after rebuild | — | V | never manually |
| Generate local repair | P | E candidate | rule constraint | V | C if design intent changes |
| Claim regulatory compliance | LOCK | — | rule result only | V within scope | C + full gate; not allowed in R0/R1 |
| Production release | LOCK | — | — | V | C at formal release gate |

## 4. Commit paths

### Path A — evidence commit

Source/Trace revisions are committed as immutable evidence. No professional judgment is allowed. Evidence objects remain readable forever and are never overwritten by later professional geometry.

### Path B — deterministic low-risk commit

Confirmed input plus an authorized deterministic rule may create a derived representation without per-object human confirmation. Examples:

- confirmed footprint + confirmed height → massing;
- confirmed canonical revision → DXF/IFC;
- upstream revision change → stale propagation.

### Path C — design-intent change

Everything else requires a proposal, diff, validator result and human confirmation. Examples:

- changing road connectivity;
- regularizing an intentionally rotated building;
- reclassifying a road;
- assigning a previously unknown height;
- choosing between conflicting profiles.

## 5. Authority states

| State | Meaning |
|---|---|
| `evidence_only` | Source/Trace evidence; cannot be overwritten by professionalization |
| `candidate` | Machine/Agent candidate; not confirmed design truth |
| `rule_derived` | Produced by a deterministic, authorized rule with traceable rule version |
| `human_confirmed` | Explicitly confirmed by the designer |
| `locked` | Automatic transformation forbidden until explicit human unlock |

## 6. Mandatory escalation to human confirmation

An Agent may only propose when any of the following holds:

1. professional geometry deviates from trace beyond a calibrated gate;
2. road connectivity or building object count changes;
3. a locked redline/control point/project coordinate would move;
4. road use or building height is unknown;
5. profile applicability conflicts or standard version is unclear;
6. validator returns `conditional` or `validator_error`;
7. round-trip difference falls outside the semantic equivalence policy;
8. a local repair would cascade to more than one adjacent design object.

## 7. Locks

- `locks` covers revision axes (`semantic`, `geometry`, `parameter`, `all`).
- `locked_paths` covers field-level protection.
- A lock is bypassed only by `RequiredAuthority.HUMAN_UNLOCK` with:
  - a human actor,
  - `can_unlock = true`,
  - `unlock_confirmed = true` on the proposal.
- Unlock grants are server-side, proposal-bound, scene-revision-bound and single-use.

## 8. Agent boundary

- The Agent tool surface has no approve, unlock, or raw canonical mutation operation.
- `ActorContext` is injected by the host; the Agent cannot declare `is_human`, `can_unlock`, `confirmed`, or `unlock_confirmed` as request parameters.
- The Human Control Plane is a separate authenticated principal.
- CAD bridges hold external representation authority only.

## 9. Implementation invariants

The following are enforced by tests:

- `EXTERNAL_DIRECT_WRITE_FORBIDDEN` for `source_world == external`.
- `LOCK_REQUIRES_EXPLICIT_HUMAN_UNLOCK` for any locked scope without a valid unlock.
- `HUMAN_CONFIRMATION_REQUIRED` when committing a `human_confirm` proposal without human confirmation.
- `HUMAN_UNLOCK_REQUIRED` when a `human_unlock` proposal lacks human actor, capability, or unlock confirmation.
- Preview may contain unconfirmed proposals; canonical commit may not.

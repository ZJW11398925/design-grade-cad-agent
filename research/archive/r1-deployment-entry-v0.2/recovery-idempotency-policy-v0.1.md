# Recovery & Idempotency Policy v0.1

Status: **research policy**.

## Mutating requests

Every Agent-visible mutating operation must carry an idempotency key. The key is bound to the operation name and canonical request payload hash.

- same key + same request -> replay the original successful response;
- same key + different request -> `IDEMPOTENCY_KEY_REUSE_MISMATCH`;
- blocked precondition responses are not persisted as successful idempotent transitions when later state may legitimately unblock them.

## Important exception: transient observations

`claim_next_job -> empty` is not cached. Queue emptiness is temporary; caching it would prevent the same retry from seeing work that becomes eligible later.

## Project-state durability

The research prototype stores one hash-enveloped state snapshot and uses atomic file replacement. On load, payload hash mismatch is a hard failure.

This does not prove power-loss durability across every filesystem and does not replace a production transactional database.

## Concurrent writers

Each runtime instance remembers the payload hash it loaded. Save uses compare-and-swap against the current disk hash.

A mismatch produces `PROJECT_STATE_CONCURRENT_MODIFICATION`. The stale instance must reload; it may not continue as an authority.

## Worker recovery

A job claimed before process loss is requeued on runtime restart. Its old claim-idempotency record is removed and the artifact returns to `stale`.

On the next claim, `attempt` increments. Completion must match both the current worker ID and attempt. Old workers receive `STALE_JOB_CLAIM`.

## Delivery semantics

This establishes an **at-least-once** worker contract. Exactly-once execution is not claimed. Side-effecting domain workers must therefore be idempotent or publish content-addressed outputs before registry promotion.

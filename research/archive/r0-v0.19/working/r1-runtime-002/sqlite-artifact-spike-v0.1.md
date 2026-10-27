# SQLite + Artifact Store Spike v0.1

Purpose: test whether a local sidecar can use SQLite for transactional metadata/state and a content-addressed directory for binary/large artifacts without changing Foundation semantics.

Implemented in this spike:
- SQLite database with `WAL`, `foreign_keys=ON`, `synchronous=FULL`.
- project snapshot rows with deterministic JSON hash and compare-and-swap revision.
- explicit distinction between concurrent modification and payload/hash corruption.
- artifact metadata registry in SQLite.
- content-addressed artifact bytes under SHA-256 paths.
- restart/reopen checks.

Not proven:
- crash power-loss testing;
- multi-machine writers;
- large project performance;
- schema normalization for every runtime record;
- backup/restore/compaction policy;
- network filesystems.

The spike supports SQLite as the R1 local-sidecar candidate, not as a final irreversible choice.

# Development Workflow

## 1. Branches and commits

- `main` is the integration branch; it must stay green.
- Work on a topic branch: `feat/<topic>`, `fix/<topic>`, `test/<topic>`, `docs/<topic>`.
- Commit style: Conventional Commits (`feat:`, `fix:`, `test:`, `docs:`, `refactor:`, `chore:`).
- Keep commits scoped. A contract change and its test belong in the same commit.

## 2. Definition of done

A change is done only when:

1. The behavior is covered by a failing-then-passing test.
2. `python -m pytest -q` is green locally.
3. Contracts (`contracts/*.yaml`) are updated if the interface changed.
4. `CHANGELOG.md` has an entry for user-visible or contract-visible changes.
5. Scope/non-claim statements are updated if the change affects what the project can claim.

## 3. Contract change process

Any change to identity, revision, authority, dependency, lifecycle, auth or bridge semantics requires:

1. a contract YAML diff;
2. a test that fails against the previous behavior;
3. an entry in `CHANGELOG.md`;
4. a note in `docs/status.md` if a gate status changes.

Do not change a contract and its test in the same direction without an independent reason: that makes the test unable to catch the change.

## 4. Research intake

- Raw research stays under `research/archive/` and is historical evidence.
- New research findings go to `research/` (not `src/`) until they produce a testable contract.
- A finding becomes code only through a contract + test.
- Never rewrite archived research documents to match current code; add a new document or an ADR instead.

## 5. Versioning

- `0.y.z` while the project is a research prototype.
- Breaking contract changes bump `y`.
- The package version lives in `pyproject.toml`; changelog entries are dated.
- Research snapshots use their own versions (R0 v0.19, R1 deployment-entry v0.2) and are not the package version.

## 6. Pull requests

PR checklist:

- [ ] Tests added or updated; full suite green.
- [ ] New behavior has at least one negative/adversarial case.
- [ ] Contracts updated.
- [ ] Changelog updated.
- [ ] No secrets, credentials, private paths or proprietary third-party code committed.
- [ ] Scope/non-claim language updated if needed.

## 7. Prohibited shortcuts

- Importing a CAD/BIM library object as the canonical persistence model.
- Using a CAD object handle as the canonical primary key.
- Encoding rules in the Agent prompt.
- Letting an external CAD/BIM file overwrite canonical state.
- Treating `validator_error` as a design failure or a pass.
- Adding numeric design defaults without an authoritative source.
- Committing `_incoming/`, build outputs, or local virtual environments.

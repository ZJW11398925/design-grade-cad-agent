# Contributing

Thanks for considering a contribution. This project is a research-first engineering workspace; correctness and evidence matter more than feature count.

## Before you start

Read:

1. [README.md](README.md) — project scope and non-claims.
2. [docs/architecture/overview.md](docs/architecture/overview.md) — truth model, modules, authority.
3. [docs/development/testing.md](docs/development/testing.md) — test layers and scope rules.
4. [docs/development/workflow.md](docs/development/workflow.md) — branch, commit and PR rules.

## Ground rules

- **Tests before claims.** A new behavior needs an executable test. A research claim without evidence stays a candidate.
- **Unknown is valid.** Never replace `unknown`, `blocked` or `needs_review` with a guessed default.
- **The Agent never writes confirmed design truth.** It proposes; humans and authorized deterministic rules commit.
- **Layered validation.** Do not use one passing layer to imply another (e.g. file audit ≠ design compliance).
- **No vendored third-party code** without a license review and a NOTICE entry.
- **No secrets or private paths** in commits, fixtures or tests.

## Development setup

```bash
python -m venv .venv
# Windows: .venv\Scripts\activate
# Linux/macOS: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m pytest -q
```

Expected: `467 passed`.

## Pull request checklist

- [ ] The change has a test (or an explicit evidence-only justification).
- [ ] `python -m pytest -q` is green.
- [ ] Contracts are updated if an interface changed.
- [ ] `CHANGELOG.md` is updated.
- [ ] Scope/non-claim wording is updated if capability claims changed.
- [ ] No generated caches, virtual environments or `_incoming/` files are included.

## Reporting issues

- Use GitHub Issues for defects, questions and proposals.
- For security issues, follow [SECURITY.md](SECURITY.md), not a public issue.
- For research contributions, state the decision question, sources, evidence level and what the evidence does **not** prove.

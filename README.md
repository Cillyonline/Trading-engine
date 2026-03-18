# Cilly Trading Engine

The Cilly Trading Engine repository contains a deterministic trading-analysis and execution platform with documented API, CLI, UI, runtime, and governance surfaces. This repository is the canonical entrypoint for navigating those materials.

The current repository state supports local runtime, deterministic smoke-run and test workflows, and bounded operator-facing UI and API surfaces. It should not be read as a production-readiness declaration.

## Start Here

Choose the path that matches your role:

### Operators

Use these documents if you need to run, verify, or operate the platform locally.

- Quick local setup (PowerShell and Bash): `docs/quickstart.md`
- Canonical local runtime path (PowerShell and Bash): `docs/local_run.md`
- Owner startup and reset cheatsheet: `docs/OWNER_RUNBOOK.md`
- Working runbook and quality gate expectations: `docs/RUNBOOK.md`
- Runtime and health references: `docs/health.md`, `docs/runtime_status_and_health.md`
- Paper-trading boundary: `docs/paper_trading.md`

### Contributors and Reviewers

Use these documents if you need to understand repository scope, test expectations, interfaces, or roadmap/governance boundaries.

- Documentation index: `docs/index.md`
- Testing entrypoint: `docs/testing.md`
- Getting started path for owners/local access: `docs/GETTING_STARTED.md`
- Public Python API boundary: `docs/api/public_api_boundary.md`
- Authoritative roadmap and phase taxonomy: `docs/roadmap/execution_roadmap.md`
- Strategy configuration references: `docs/strategy-configs.md`
- Snapshot/golden-master guidance: `docs/snapshot-testing.md`

## Canonical Boundaries

- The repository-level documentation index is `docs/index.md`.
- The canonical local runtime path is documented in `docs/local_run.md`.
- The authoritative audited phase taxonomy is `docs/roadmap/execution_roadmap.md`.
- The supported package-level public API for `src/api` is `from api import app`.
- The canonical top-level repository structure is documented in `docs/architecture/repository_root_structure.md`.

## Canonical Repository Structure

The canonical root structure for this repository is defined in
`docs/architecture/repository_root_structure.md`.

For all future repository changes, the allowed top-level directories are:

- `docs/`
- `src/`
- `tests/`
- `scripts/` when repository-owned automation or developer tooling is required
- `frontend/` when a repository-owned frontend surface is required
- `fixtures/` when shared deterministic fixture data is required

Top-level directories outside that set are not canonical destinations for new
work unless a separate repository decision documents and approves them.

This issue does not move, delete, or rename any existing top-level directories.
Current extra root folders remain part of the repository's present state until a
separate cleanup or migration issue addresses them.

## Public API

The Python package-level public API for `src/api` is frozen to a single supported symbol:

- `from api import app`

The full boundary definition is documented in `docs/api/public_api_boundary.md`.

## Verification Paths

- Operators validating a local environment should start with `docs/quickstart.md`, then use `docs/local_run.md` and `docs/OWNER_RUNBOOK.md`. Windows users should follow the PowerShell command blocks in those docs directly.
- Contributors or reviewers validating behavior and change scope should start with `docs/index.md`, then use `docs/testing.md`, `docs/api/public_api_boundary.md`, and `docs/roadmap/execution_roadmap.md`.

## Local CI Check

```bash
python -m pytest -q
```

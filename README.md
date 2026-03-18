# Cilly Trading Engine

The Cilly Trading Engine repository contains a deterministic trading-analysis and execution platform with documented API, CLI, UI, runtime, and governance surfaces. This repository is the canonical entrypoint for navigating those materials.

The current repository state supports local runtime, deterministic smoke-run and test workflows, and bounded operator-facing UI and API surfaces. It should not be read as a production-readiness declaration.

## Documentation Entry Point

`README.md` is an entry point only. It provides navigation into the canonical
documentation structure and does not act as the source of truth for setup,
local run, testing, or architecture topics.

Start from these documents:

- Canonical documentation structure and navigation flow:
  `docs/architecture/documentation_structure.md`
- Repository documentation index: `docs/index.md`
- Setup authority: `docs/GETTING_STARTED.md`
- Local run authority: `docs/local_run.md`
- Testing authority: `docs/testing.md`
- Architecture authority root: `docs/architecture/`

## Canonical Boundaries

- The repository-level documentation index is `docs/index.md`.
- The canonical documentation structure is defined in
  `docs/architecture/documentation_structure.md`.
- The canonical setup path is documented in `docs/GETTING_STARTED.md`.
- The canonical local runtime path is documented in `docs/local_run.md`.
- The canonical testing path is documented in `docs/testing.md`.
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

- Operators validating a local environment should start here, then follow
  `docs/architecture/documentation_structure.md` to the canonical setup and
  local run documents.
- Contributors or reviewers validating behavior and change scope should start
  here, then use `docs/index.md` and
  `docs/architecture/documentation_structure.md` to reach the canonical
  testing and architecture documents.

## Local CI Check

```bash
python -m pytest -q
```

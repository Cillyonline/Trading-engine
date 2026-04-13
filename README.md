# Cilly Trading Engine

The Cilly Trading Engine repository contains a deterministic trading-analysis and execution platform with documented API, CLI, UI, runtime, and governance surfaces. This repository is the canonical entrypoint for navigating those materials.

The current repository state supports local runtime, deterministic smoke-run and test workflows, and bounded operator-facing UI and API surfaces. It should not be read as a production-readiness declaration.

## Documentation Entry Point

`README.md` is an entry point only. It provides navigation into the canonical
documentation structure and does not act as the source of truth for setup,
local run, testing, or architecture topics.
It also does not act as a source of authority for roadmap phase maturity/status.

Start from these documents:

- Canonical documentation structure and navigation flow:
  `docs/architecture/documentation_structure.md`
- Repository documentation index: `docs/index.md`
- Setup authority: `docs/getting-started/getting-started.md`
- Local run authority: `docs/getting-started/local-run.md`
- Testing authority: `docs/testing/index.md`
- Architecture authority root: `docs/architecture/`
- Roadmap phase maturity/status authority: `ROADMAP_MASTER.md`
- Server-ready release governance contract:
  `docs/releases/release_governance_contract.md`

## Verification Paths

- Operators validating a local environment should start here, then follow
  `docs/getting-started/getting-started.md` and `docs/getting-started/local-run.md`.
- Operators validating the bounded staging server deployment path should use
  `docs/operations/runtime/staging-server-deployment.md`.
- Contributors or reviewers validating behavior and change scope should start
  here, then use `docs/testing/index.md` and `docs/architecture/`.

## Public API

The supported package-level public API for `src/api` is documented in
`docs/operations/api/public_api_boundary.md`.
Legacy compatibility path: `docs/api/public_api_boundary.md`.

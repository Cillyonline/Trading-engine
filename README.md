# Cilly Trading Engine

The Cilly Trading Engine repository contains a deterministic trading-analysis
and execution platform with documented API, CLI, UI, runtime, and governance
surfaces.

The current repository state supports local runtime, deterministic smoke-run
and test workflows, and bounded operator-facing UI and API surfaces. It should
not be read as a production-readiness declaration.

## Documentation Roles

`README.md` is the repository entry point only.

- Entry point: `README.md`
- Navigation hub: `docs/index.md`
- Structure and role map:
  `docs/architecture/documentation_structure.md`

## Documentation Navigation Flow

Use the primary navigation path:

1. Start at `README.md`.
2. Open `docs/index.md`.
3. Follow links in `docs/index.md` to the target document.

For canonical ownership rules and structure boundaries, use
`docs/architecture/documentation_structure.md`.

## Destination Shortcuts

- Setup: `docs/getting-started/getting-started.md`
- Local run: `docs/getting-started/local-run.md`
- Testing: `docs/testing/index.md`
- Architecture: `docs/architecture/`
- Document status model: `docs/architecture/governance/document-status-model.md`
- Release governance contract: `docs/releases/release_governance_contract.md`

## Public API

The supported package-level public API for `src/api` is documented in
`docs/operations/api/public_api_boundary.md`.
Legacy compatibility path: `docs/api/public_api_boundary.md`.

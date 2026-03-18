# Non-Core Directory Audit

## Purpose

This document records the repository decision for non-core directories reviewed
under issue `#681`.

It classifies each audited directory as `keep`, `move`, or `remove` and gives
the rationale needed to avoid future ambiguity. This document does not move or
delete any directory.

## Scope

This audit covers:

- repo-tracked top-level directories outside the core `docs/`, `src/`, and
  `tests/` roots
- non-standard nested directories that materially affect future repository
  structure decisions

The canonical root policy remains
`docs/architecture/repository_root_structure.md`.

## Classification Rules

- `keep`: the directory remains in its current location
- `move`: the directory content should be relocated in a follow-up cleanup issue
- `remove`: the directory should stop being repository-tracked in a follow-up
  cleanup issue

## Audited Directories

| Directory | Classification | Future location | Rationale |
| --- | --- | --- | --- |
| `.codex/` | keep | `.codex/` | Repository-scoped Codex workflow metadata is tool-specific, but the path is fixed by the tool and does not duplicate a product code boundary like `src/` or `tests/`. Treat it as repository metadata, not as a product root. |
| `.devcontainer/` | keep | `.devcontainer/` | Devcontainer configuration is repository metadata with a fixed conventional location. It supports contributor setup and should stay outside product/runtime directories. |
| `.github/` | keep | `.github/` | GitHub workflow and template files must remain at the repository root to function. This is a standard governance metadata exception, not application structure drift. |
| `fixtures/` | keep | `fixtures/` | `docs/architecture/repository_root_structure.md` already allows `fixtures/` as the canonical optional root for deterministic shared fixtures. Existing tracked content matches that purpose. |
| `frontend/` | keep | `frontend/` | `frontend/` is already an allowed optional root. The repository contains a tracked UI surface under this directory, so keeping it is aligned with the current root contract. |
| `scripts/` | keep | `scripts/` | `scripts/` is already an allowed optional root for repository-owned helper automation. The tracked snapshot helper script fits that boundary. |
| `data/` | move | `fixtures/phase6_snapshots/` | The tracked contents are deterministic sample snapshot artifacts, not mutable application data. Under the canonical root policy, versioned sample data belongs under `fixtures/`, not under a separate root-level `data/` namespace. |
| `engine/` | move | `src/cilly_trading/` for implementation and `tests/` for embedded tests | Top-level Python implementation does not belong outside `src/`, and test modules do not belong inside an implementation root. This directory also contains generated `__pycache__/` content, which reinforces that it is not a clean long-term repository boundary. |
| `runs/` | remove | none; keep only as local runtime output if still needed by runtime contracts | `runs/` contains generated run artifacts such as `runs/phase6/<run_id>/audit.json`. Generated runtime output is not a canonical repository root and should not be versioned as source-controlled structure. |
| `schemas/` | move | `src/cilly_trading/contracts/schemas/` | The schemas are machine-consumed contract artifacts. They should live with versioned package contracts rather than as a separate root namespace outside `src/`. |
| `strategy/` | move | `src/cilly_trading/strategies/` | The current root only exists to host preset configuration. Strategy-owned runtime configuration should live with the strategy package boundary instead of a separate root-level namespace. |
| `strategy/presets/` | move | `src/cilly_trading/strategies/presets/` | Preset JSON files are strategy configuration assets, not a standalone repository root concern. Moving them under the strategy package removes duplication between strategy configuration ownership and repository layout. |
| `frontend/node_modules/` | remove | none; local install only | This directory is generated dependency output, not repository source. It should remain untracked and recreated from `frontend/package.json` when needed. |
| `engine/**/__pycache__/` | remove | none | Python bytecode caches are generated artifacts and should never be treated as part of the target repository structure. |

## Resulting Future Structure Decisions

- Repository metadata exceptions kept at root: `.codex/`, `.devcontainer/`,
  `.github/`
- Canonical optional roots kept at root: `fixtures/`, `frontend/`, `scripts/`
- Root directories to migrate out of the root namespace: `data/`, `engine/`,
  `schemas/`, `strategy/`
- Root directories to stop tracking as repository structure: `runs/`

## No-Ambiguity Follow-Up Targets

- Snapshot sample artifacts currently under `data/` should migrate to
  `fixtures/phase6_snapshots/`.
- Top-level Python implementation currently under `engine/` should migrate into
  `src/cilly_trading/`.
- Test-like modules currently under `engine/` should migrate into `tests/`.
- JSON schema contracts currently under `schemas/` should migrate into
  `src/cilly_trading/contracts/schemas/`.
- Strategy preset assets currently under `strategy/presets/` should migrate
  into `src/cilly_trading/strategies/presets/`.
- Generated runtime artifacts under `runs/` should be treated as local output,
  not tracked repository content.
- Generated dependency and cache directories such as `frontend/node_modules/`
  and `engine/**/__pycache__/` should be removed from repository tracking if
  they appear in future cleanup scope.

## Acceptance Criteria Mapping

- Each non-core directory has a clear classification. -> Satisfied by the audit
  table above.
- Rationale is documented for each decision. -> Satisfied by the rationale
  column above.
- No ambiguity remains about future structure. -> Satisfied by the explicit
  future-location column and follow-up target list above.

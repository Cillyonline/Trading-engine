# Canonical Repository Root Structure

## Purpose

This document defines the canonical top-level repository structure for the
Cilly Trading Engine repository.

It is the single source of truth for which root directories are allowed for
future changes. It does not move existing files or folders, and it does not
change repository architecture.

## Canonical Allowed Root Directories

The allowed canonical top-level directories are:

- `docs/`
- `src/`
- `tests/`
- `scripts/` as an optional root for repository-owned automation, helper
  scripts, or developer tooling
- `frontend/` as an optional root when the repository includes a frontend
  surface
- `fixtures/` as an optional root for shared deterministic fixtures or test
  data

## Root Placement Rules

- New documentation belongs under `docs/`.
- Production Python implementation code belongs under `src/`.
- Automated tests belong under `tests/`.
- Helper scripts may be added under `scripts/` only when they are part of the
  repository workflow.
- Frontend code may be added under `frontend/` only when the repository owns
  that surface.
- Shared deterministic fixtures may be added under `fixtures/` when they are
  needed by tests, documentation, or bounded local workflows.

No other top-level directory is an allowed default destination for new
repository content.

If future work requires a new root directory outside this list, that change
must be explicitly documented and approved by a separate repository decision
before files are added there.

## Current Repository State

The current repository includes additional top-level directories beyond the
canonical list above.

Those directories are part of the repository's current state, but they are not
the canonical model for future structure decisions. This document does not
delete, rename, move, or normalize them.

## Manual Validation For Issue #680

Manual review for this issue should confirm all of the following:

- this document is reachable from `README.md`
- the canonical allowed root directories are listed exactly once and without
  competing alternatives
- the optional roots are explicitly marked as optional
- the document does not require any immediate folder moves or deletions

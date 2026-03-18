# Canonical Documentation Structure

## Purpose

This document defines the canonical documentation structure for the Cilly
Trading Engine repository.

It establishes exactly one authoritative location for each in-scope topic and
defines how readers should navigate between those documents. It does not move
files, edit existing documentation content, or delete any current documents.

## README Role

`README.md` is the repository entry point only.

- It may introduce the repository and route readers to canonical documents.
- It must not become the source of truth for setup, local run, testing, or
  architecture content.
- Topic-specific instructions belong in their canonical documentation file, not
  in `README.md`.

## Canonical Topic Ownership

The authoritative file or directory for each in-scope topic is:

- Setup: `docs/GETTING_STARTED.md`
- Local run: `docs/local_run.md`
- Testing: `docs/testing.md`
- Architecture: `docs/architecture/`

Within this structure, each topic has exactly one source of truth:

- Setup content is authoritative only in `docs/GETTING_STARTED.md`.
- Local run content is authoritative only in `docs/local_run.md`.
- Testing content is authoritative only in `docs/testing.md`.
- Architecture content is authoritative only under `docs/architecture/`.

If other existing documents mention one of these topics, those documents are
supporting or historical references and must defer to the canonical location
above rather than redefine the topic.

## Navigation Flow

The required navigation flow is:

1. Start at `README.md`.
2. Follow `README.md` to this document for canonical structure and ownership.
3. From this document, navigate to the authoritative topic document:
   `docs/GETTING_STARTED.md`, `docs/local_run.md`, `docs/testing.md`, or
   `docs/architecture/`.
4. From a topic document, follow links only to supporting documents that do not
   replace the topic's canonical source of truth.

## Structure Rules

- New setup documentation must consolidate into `docs/GETTING_STARTED.md`.
- New local run documentation must consolidate into `docs/local_run.md`.
- New testing documentation must consolidate into `docs/testing.md`.
- New architecture documentation must live under `docs/architecture/`.
- `README.md` must continue to function as a navigation entry point only.
- No in-scope topic may have multiple authoritative files.

## Manual Validation For Issue #684

Manual review for this issue should confirm all of the following:

- `README.md` points to this document as the canonical documentation structure.
- `README.md` is positioned as an entry point only, not as a topic authority.
- Setup, local run, testing, and architecture each have exactly one
  authoritative location defined here.
- The navigation flow from `README.md` to the canonical topic documents is
  explicit and unambiguous.

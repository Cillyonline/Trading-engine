# Canonical Documentation Structure

## Purpose

This document defines documentation structure boundaries for the Cilly Trading
Engine repository.

It is the single location that declares documentation roles and canonical topic
ownership.

## Core Document Roles

- `README.md`: repository entry point only.
- `docs/index.md`: documentation navigation only.
- `docs/architecture/documentation_structure.md`: canonical structure and topic
  ownership rules.

`README.md` and `docs/index.md` may route readers to canonical documents, but
they do not define or redefine topic ownership.

## Canonical Topic Ownership

Each in-scope topic has one canonical owner:

- Setup: `docs/getting-started/getting-started.md`
- Local run: `docs/getting-started/local-run.md`
- Testing: `docs/testing/index.md`
- Architecture: `docs/architecture/`

Any other document that mentions one of these topics is a supporting navigation
or reference surface and must defer to the canonical owner listed above.

## Required Navigation Flow

The default path for readers is:

1. Start at `README.md`.
2. Continue to `docs/index.md`.
3. Select the canonical target document from `docs/index.md`.
4. Use topic-local links from that canonical document.

## Structure Rules

- Keep `README.md` as the entry point.
- Keep `docs/index.md` as navigation.
- Keep canonical ownership declarations in this document only.
- Do not assign multiple canonical owners to the same topic.

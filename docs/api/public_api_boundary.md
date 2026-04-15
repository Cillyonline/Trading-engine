# Public API Boundary

## Document Status
- Class: Deprecated
- Canonical Source(s): docs/operations/api/public_api_boundary.md
- Superseded by: docs/operations/api/public_api_boundary.md
- Rationale: Legacy compatibility path retained for older references.

This document is deprecated. Use
`docs/operations/api/public_api_boundary.md` as the active path.

This document freezes the supported Python import surface for `src/api`.

## Public surface (supported)

The only supported package-level import is:

- `from api import app`

This symbol is explicitly exported by `src/api/__init__.py` via `__all__ = ("app",)`.

## Internal surface (not supported)

Everything else under `src/api` is internal implementation detail and must not be treated as stable API, including:

- `api.main`
- request/response models in `api.main`
- helper functions/constants in `api.main`
- `api.config`

These internals may change without compatibility guarantees.

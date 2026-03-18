# Public API Boundary

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

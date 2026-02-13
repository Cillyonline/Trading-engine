# External Contract Surface (CLI/API)

## Purpose
This document defines the supported **external contract surface** from a CLI/API perspective.

It is **documentation-only** and has **no runtime implications**. It does not add, change, or remove commands, endpoints, or runtime behavior.

## Supported Contract Surface
Only the following documented interface layers are part of the external contract:

- **CLI surface**: documented CLI entrypoint(s), documented invocation forms, and documented arguments.
- **API surface**: documented public API entrypoint(s) and documented request/response usage.
- **External client perspective**: integration behavior as described for external client types and boundaries.

Authoritative references:
- `docs/interfaces/cli_contract.md`
- `docs/api/usage_contract.md`
- `docs/api/public_api_boundary.md`
- `docs/external/client_types.md`

## Explicit Exclusions
The following are explicitly **outside** the external contract:

- Internal modules, internal package structure, and internal import paths.
- Internal helper functions, internal classes, and internal constants.
- Internal control flow, orchestration details, and execution paths.
- Incidental or undocumented behavior, even if currently observable.
- Private implementation details behind documented CLI/API surfaces.
- Any behavior not explicitly documented in the referenced interface documents.

## What Is NOT Part of the Contract
The external contract does **not** include:

- Source layout under `src/**` as a stable interface.
- Direct use of non-documented internals as if they were public APIs.
- Undocumented CLI flags, argument combinations, or invocation shapes.
- Undocumented API usage patterns.
- Output formatting details unless explicitly documented as stable.
- Any assumptions derived from implementation rather than interface documentation.

## Interpretation Rule
If a behavior is not documented in the referenced interface documentation, it must be treated as **non-contractual**.

This boundary exists to keep external integrations tied to documented interfaces only, while allowing internal implementation to evolve.

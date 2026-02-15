# Strategy Registry Validation

## Purpose

Strategy registry validation enforces deterministic and schema-safe strategy registrations before any registry write occurs.

## Fail-fast Behavior

`register_strategy(...)` validates key, metadata, factory signature, and factory output before mutating the registry.
If validation fails, registration is rejected and registry state remains unchanged.

## What Is Validated

- Strategy key must be a non-empty string and is normalized to uppercase.
- Metadata must be a dictionary.
- Required metadata fields must exist: `pack_id`, `version`, `deterministic_hash`, `dependencies`.
- Required field types are enforced.
- Required string fields must not be empty.
- `version` must follow SemVer (`MAJOR.MINOR.PATCH`).
- `dependencies` must be deterministic (sorted, non-duplicated, non-empty string entries).
- Factory must be callable.
- Factory must accept no arguments (`no args`, `no *args`, `no **kwargs`).
- Factory must return a strategy-compatible object with stable `name` and callable `generate_signals`.
- Duplicate registration keys are rejected before any write.

## Error Semantics

Validation failures raise `StrategyValidationError` with deterministic, explicit error messages.
Duplicate registration also raises `StrategyValidationError` with message format:
`strategy already registered: <KEY>`.

## Out of Scope

- Performance metrics
- Ranking logic
- Backtesting integration

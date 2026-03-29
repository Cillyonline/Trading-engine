# Strategy Registry Validation

## Purpose

Strategy registry validation enforces deterministic, schema-safe onboarding before any strategy registration is written.

## Fail-fast behavior

`register_strategy(...)` validates key, metadata, factory signature, and factory output before mutating registry state.
If validation fails, registration is rejected and the registry remains unchanged.

## Controlled onboarding metadata

Required metadata fields:

- `pack_id`
- `version`
- `deterministic_hash`
- `dependencies`
- `comparison_group`
- `documentation`
- `test_coverage`

Validation rules:

- Required metadata fields must exist.
- Unsupported metadata fields are rejected.
- Required string fields must be non-empty.
- `version` must follow SemVer (`MAJOR.MINOR.PATCH`).
- `dependencies` must be sorted, unique, and contain non-empty strings.
- `comparison_group` must match `^[a-z0-9][a-z0-9_-]*$`.

## Documentation expectations

`documentation` must include:

- `architecture`: path under `docs/architecture/*.md`
- `operations`: path under `docs/operations/*.md`

## Test expectations

`test_coverage` must include:

- `contract`: path under `tests/*.py`
- `registry`: path under `tests/*.py`
- `negative`: path under `tests/*.py`

All three test paths must be distinct.

## Factory and key validation

- Strategy key must be a non-empty string and is normalized to uppercase.
- Factory must be callable.
- Factory must accept no arguments (`no args`, `no *args`, `no **kwargs`).
- Factory must return a strategy-compatible object with stable `name` and callable `generate_signals`.
- Duplicate keys are rejected before any write.

## Error semantics

Validation failures raise `StrategyValidationError` with explicit deterministic messages.
Duplicate registration uses:

- `strategy already registered: <KEY>`

## Out of scope

- performance benchmarking
- ranking logic
- backtesting integration redesign

## Bounded Score And Ranking Semantics (SIG-P47)

The governed comparison workflow uses explicit semantic boundaries to avoid unsupported confidence claims:

- Signal `score` is strategy-local evidence and is **not** calibrated as cross-strategy confidence.
- Strategy comparison ranking is valid only within a shared `comparison_group`.
- Cross-group ordering exists only as deterministic artifact serialization and is **not** a confidence order.
- Benchmark deltas are only computed for strategies in the benchmark's `comparison_group`; cross-group deltas are `null`.

These boundaries are mandatory for governed strategy surfaces and are enforced by strategy comparison validation/tests.

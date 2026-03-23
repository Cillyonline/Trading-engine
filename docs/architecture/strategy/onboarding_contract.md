# Strategy Onboarding Contract

## Goal

Define one controlled onboarding contract for adding strategies so expansion remains consistent, testable, and comparable.

## Contract Scope

This contract is enforced at strategy registration time in `src/cilly_trading/strategies/validation.py` and applied through `src/cilly_trading/strategies/registry.py`.

Any new strategy must register through `register_strategy(...)` with metadata that satisfies this contract.

## Required Metadata

Every strategy registration must provide all fields below:

- `pack_id` (string)
- `version` (SemVer string: `MAJOR.MINOR.PATCH`)
- `deterministic_hash` (string)
- `dependencies` (sorted, unique list of strings)
- `comparison_group` (string matching `^[a-z0-9][a-z0-9_-]*$`)
- `documentation` (object)
- `test_coverage` (object)

Unknown metadata fields are rejected to keep onboarding bounded.

## Required Documentation Metadata

`documentation` must include:

- `architecture`: path to `docs/architecture/*.md`
- `operations`: path to `docs/operations/*.md`

Both paths are required and must be non-empty strings.

## Required Test Coverage Metadata

`test_coverage` must include:

- `contract`: path to onboarding/contract tests under `tests/*.py`
- `registry`: path to registry/metadata tests under `tests/*.py`
- `negative`: path to negative validation tests under `tests/*.py`

All three paths are required, must be distinct, and must point to `tests/*.py`.

## Registry Alignment

The registry stores validated metadata in each `RegisteredStrategy` entry and exposes deterministic metadata through:

- `get_registered_strategies()`
- `get_registered_strategy_metadata()`

This enables consistent downstream comparison and governance logic without ad hoc conventions.

## Onboarding Checklist

When adding a new strategy:

1. Implement the strategy class.
2. Add a `register_strategy(...)` entry in the registry with full contract metadata.
3. Add/extend contract tests (`contract`, `registry`, `negative`) and reference them in metadata.
4. Add or update architecture/operations docs and reference them in metadata.
5. Run full `pytest` and keep suite green.

# Backtest Execution Contract

## Purpose

This document defines the deterministic execution contract for backtest runs. Implementations MUST produce identical outputs for identical canonical inputs and snapshot bindings.

## Scope

This contract applies to backtest request validation, snapshot binding, strategy instantiation, strategy invocation order, deterministic iteration, signal collection, result serialization, and artifact hashing.

This contract applies to offline backtest execution only. It does not define runtime behavior for live systems.

## Definitions

- **Backtest**: A bounded, offline simulation that executes one or more strategies against historical snapshot data under a declared configuration.
- **Snapshot**: An immutable dataset version identified by `snapshot_id` and `ingestion_run_id`, containing the market data used for execution.
- **Candle / Bar**: A single time-bucketed market data record (for example OHLCV) in a declared `timeframe`.
- **Strategy**: A registered algorithmic component addressed by a stable strategy key and invoked by the backtest engine.
- **Signal**: A deterministic strategy output record produced during execution, identified by a stable key (`signal_id`).
- **Run ID (deterministic identifier)**: A deterministic identifier derived from canonical request + canonical output context using stable serialization and hashing.

## Inputs

The canonical request object is `BacktestRequest`.

```json
{
  "snapshot_id": "string",
  "ingestion_run_id": "string",
  "symbols": ["string"],
  "timeframe": "string",
  "strategies": ["string"],
  "engine_config": {
    "lookback_days": "number",
    "market_type": "string",
    "data_source": "string"
  },
  "strategy_configs": {
    "<strategy_key>": {}
  },
  "created_at": "string (ISO-8601)",
  "schema_version": "string (semver)"
}
```

Field requirements:

- `snapshot_id` MUST be present and MUST be a non-empty string.
- `ingestion_run_id` MUST be present and MUST be a non-empty string.
- `symbols` MUST be present, MUST be an array of strings, and MUST be non-empty.
- `timeframe` MUST be present and MUST be a non-empty string.
- `strategies` MUST be present, MUST be an array of strings, and MUST be non-empty.
- `engine_config` MUST be present and MUST be an object containing at least:
  - `lookback_days`
  - `market_type`
  - `data_source`
- `strategy_configs` MAY be omitted; when present it MUST be an object keyed by strategy key.
- `created_at` MUST be present and MUST be an ISO-8601 string.
- `schema_version` MUST be present and MUST be a semver string.

Deterministic normalization requirements:

- `symbols` MUST be sorted lexicographically before execution.
- `strategies` MUST be sorted lexicographically before execution.
- Any maps/objects used for hashing MUST be serialized with stable key ordering.
- Snapshot binding MUST override external access hints in `engine_config` (including `data_source`); execution MUST use bound snapshot data only.

## Snapshot Binding

- Backtest MUST use only snapshot data referenced by `snapshot_id` and `ingestion_run_id`.
- Backtest MUST NOT fetch external data, including network resources or live endpoints.
- Snapshot selection MUST be explicit and deterministic from request fields.
- Snapshot data outside requested execution needs (including timeframe bounds) MAY be ignored, but ignore behavior MUST be deterministic for identical inputs.

## Strategy Invocation Lifecycle

Backtest execution MUST follow these deterministic steps in order:

1. Validate request.
2. Load snapshot.
3. Normalize and sort inputs.
4. Instantiate strategies from registry.
5. Execute iteration over time in stable ordering.
6. Collect signals.
7. Serialize output artifact.
8. Compute deterministic `run_id` and `artifact_hash`.

Lifecycle constraints:

- Strategy creation MUST occur via a registry only; dynamic discovery MUST NOT be used.
- Strategy invocation order MUST be stable and documented.
- Time iteration order MUST be stable (for example ascending timestamp within each symbol/timeframe partition).

## Deterministic Execution Rules

Implementations MUST satisfy all of the following:

- MUST NOT use system time as an implicit input.
- MUST NOT use randomness.
- MUST NOT access network resources.
- MUST NOT depend on environment variables.
- MUST NOT read filesystem data outside the snapshot boundary when filesystem access is used.
- MUST NOT rely on dictionary/map iteration order unless explicitly sorted.
- MUST use stable serialization (JSON with sorted keys and fixed separators).
- MUST ensure identical outputs for identical canonical inputs across environments.

## Output Artifact

The canonical output object is `BacktestResult`.

```json
{
  "run_id": "string",
  "schema_version": "string",
  "snapshot_id": "string",
  "ingestion_run_id": "string",
  "symbols": ["string"],
  "strategies": ["string"],
  "engine_config": {},
  "strategy_configs": {},
  "signals": [
    {
      "signal_id": "string"
    }
  ],
  "created_at": "string",
  "artifact_hash": "string"
}
```

Field semantics:

- `run_id` MUST be deterministic.
- `schema_version` MUST match the contract version used for serialization.
- `snapshot_id` MUST echo request binding.
- `ingestion_run_id` MUST echo request binding.
- `symbols` MUST be the normalized sorted array.
- `strategies` MUST be the normalized sorted array.
- `engine_config` MUST be the normalized canonical engine config object.
- `strategy_configs` MUST be normalized (or `{}` when omitted).
- `signals` MUST be deterministically ordered.
- `created_at` MUST be explicit from request/contracted input semantics and MUST NOT be sourced from implicit system time.
- `artifact_hash` MUST be the deterministic hash of canonical serialization of the artifact payload.

Signal ordering:

- `signals` MUST be sorted by `signal_id` in ascending lexicographic order.
- If `signal_id` collisions occur, the implementation MUST apply a documented stable secondary sort key and MUST use it consistently.

## Error Semantics

Errors MUST be emitted as stable machine-readable strings.

Required deterministic error codes:

- Missing snapshot: `backtest_snapshot_missing`
- Invalid schema: `backtest_schema_invalid`
- Unknown strategy key: `backtest_strategy_unknown:<KEY>`
- Non-deterministic violation detected: `backtest_nondeterministic_violation`
- Invalid timeframe/symbols/strategies: `backtest_input_invalid`

Error message formats SHOULD be stable and MUST NOT include non-deterministic values unless explicitly part of canonical input.

## Compatibility & Versioning

- Contract changes MUST bump `schema_version` using semver.
- Breaking changes MUST increment MAJOR.
- Additive backward-compatible changes MUST increment MINOR.
- Clarifications or non-behavioral corrections MUST increment PATCH.
- Consumers MUST reject unknown MAJOR versions unless explicitly supported.

## Non-Goals

The following are explicitly out of scope for this contract:

- Performance metrics
- Ranking/optimization
- Walk-forward analysis
- Live trading
- Broker integration
- CI automation enforcement

## Acceptance Criteria Mapping

FILES CHANGED: docs/backtesting/execution_contract.md

Acceptance Criteria Mapping:
- File docs/backtesting/execution_contract.md exists. → satisfied by this file.
- Input contract explicitly defined. → see ## Inputs.
- Output artifact schema defined. → see ## Output Artifact.
- Determinism constraints explicitly stated. → see ## Deterministic Execution Rules.
- No runtime changes. → documentation-only change.

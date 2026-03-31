# Purpose of an Analyst Run
An analyst run is deterministic only when the engine is executed against a fixed snapshot and the snapshot-only path is enforced by the API entrypoints.

# Terminology
- Snapshot: An immutable capture of all input data and configuration required for a run.
- Run: A single execution of the engine using a snapshot.
- Signal: A discrete output emitted by the run that represents the engine’s computed decision data.
- Result: The structured outcome set produced by the run, including signals and their associated metadata.
- Deterministic: The property that the same snapshot produces the same results on every run.

# Preconditions
A snapshot exists and is complete, containing all input data and configuration required for execution. Deterministic behavior is limited to runs that use the snapshot-only path and do not consult external data or time-dependent inputs.

# Snapshot ingestion lifecycle
The authoritative server-side snapshot creation contract lives in
`docs/operations/runtime/snapshot_ingestion_contract.md`.

This workflow remains consumer-side only:

- the API and engine consume snapshots that already exist in SQLite
- the workflow does not define a public ingestion API
- snapshot creation is bounded to server-side creation of `ingestion_runs` and
  `ohlcv_snapshots` for later analysis use

## Snapshot readiness used by the API
For snapshot-only API endpoints, readiness is enforced before analysis:
- `ingestion_run_id` must be a valid UUIDv4 and must exist in `ingestion_runs`
- for each requested symbol, there must be **at least one** row in
  `ohlcv_snapshots` with the matching `ingestion_run_id`, symbol, and timeframe
  (`D1`)

If any symbol/timeframe pair is missing, the API returns
`422 ingestion_run_not_ready`. After readiness checks pass, the engine loads the
snapshot via `load_ohlcv_snapshot` and validates OHLCV structure; missing or
invalid data yields `SnapshotDataError`, surfaced as `422 snapshot_data_invalid`.

# Define Analysis Run
An analysis run is defined by binding the run to a specific snapshot. In the API, snapshot-only execution is enforced by:

- `api.main.analyze_strategy` (POST `/strategy/analyze`) -> `_run_snapshot_analysis` -> `cilly_trading.engine.core.run_watchlist_analysis(snapshot_only=True)`
- `api.main.manual_analysis` (POST `/analysis/run`) -> `_run_snapshot_analysis` -> `cilly_trading.engine.core.run_watchlist_analysis(snapshot_only=True)`
- `api.main.basic_screener` (POST `/screener/basic`) -> `_run_snapshot_analysis` -> `cilly_trading.engine.core.run_watchlist_analysis(snapshot_only=True)`

# Execute Run
When the snapshot-only path is used, the engine loads data via `cilly_trading.engine.data.load_ohlcv_snapshot` and does not consult external sources.

# Fetch Signals
Signals produced by the run are retrieved from the run’s results. When the snapshot-only path is used, the signals reflect deterministic outputs computed from the snapshot.

# Inspect Results
The results are inspected as the authoritative record of the run. They include the signals and any metadata produced by the engine during execution.

# Interpret Missing or Empty Signals
Empty or missing signals do not automatically indicate an error. A strategy may be skipped if its configuration is invalid, and skipped strategies emit no signals. Determinism includes skip behavior: identical invalid configurations result in identical skips across runs.

# Reason About Output
Reasoning about the output is based solely on the snapshot and the deterministic run semantics. Identical snapshots yield identical signals and results, assuming the snapshot-only path is used.

# Guarantees
The API entrypoints listed above guarantee snapshot-only execution and deterministic results for the same snapshot. This guarantee does not apply to direct engine usage that bypasses the API.

# Non-Deterministic Paths
Direct calls to `cilly_trading.engine.core.run_watchlist_analysis` with `snapshot_only=False` (default) and without `ingestion_run_id` load data via `cilly_trading.engine.data.load_ohlcv`, which depends on current time (`_utc_now`) and external data sources (`yfinance` and `ccxt`/Binance). These runs can vary across time or upstream data changes.

# Non-Goals
The workflow does not cover live trading, broker integrations, backtesting, or AI-based decision logic.

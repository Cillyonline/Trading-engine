# Canonical Real-Market Snapshot Ingestion Contract

This document is the single authoritative server-side contract for creating valid
`ingestion_runs` and `ohlcv_snapshots` records from real market data sources for
analysis use.

It is intentionally bounded:

- It governs server-side snapshot creation only.
- It does not define a public API.
- It does not expand into live trading, broker execution, charting, or UI scope.
- It does not change the snapshot-only read contract used by analysis endpoints.

If another document summarizes snapshot ingestion, this document is authoritative
for the ingestion boundary.

## Contract Boundary

The contract covers one bounded write path:

1. Create one immutable `ingestion_runs` record for a real-market snapshot.
2. Persist the matching immutable `ohlcv_snapshots` rows for that run.
3. Expose enough metadata and evidence for the snapshot-only analysis APIs to
   distinguish valid, missing, and invalid snapshots.

The contract does not cover:

- live provider calls during analysis
- public ingestion endpoints
- paper execution
- live trading
- broad market-data refactors

## Supported Scheduling Path

One bounded scheduling path for ingestion is documented and supported in this
repository:

- one single-server cron entry that invokes `scripts/run_snapshot_ingestion.py`
- one canonical `D1` cadence definition for server operation: daily at `06:05`
  UTC
- one lock file guarding one active scheduled run at a time on that server

Out of scope for this contract:

- cloud orchestration
- distributed schedulers
- leader election or cross-host lease coordination
- public alerting or public ingestion triggers

## Valid, Missing, and Invalid Snapshot States

### Valid snapshot

A snapshot is valid for analysis when all of the following are true:

- exactly one `ingestion_runs` record exists for the `ingestion_run_id`
- the `ingestion_runs` record contains the required metadata fields defined below
- the required `ohlcv_snapshots` rows exist for each requested symbol and
  timeframe
- the persisted rows satisfy the row-shape and validity expectations defined
  below
- the snapshot remains immutable after persistence

### Missing snapshot

A snapshot is missing when either of the following is true:

- the `ingestion_runs` record does not exist for the requested `ingestion_run_id`
- the `ingestion_runs` record exists, but one or more required symbol/timeframe
  row sets are absent from `ohlcv_snapshots`

This is the boundary behind read-side failures such as
`ingestion_run_not_found` and `ingestion_run_not_ready`.

### Invalid snapshot

A snapshot is invalid when rows exist but the snapshot must not be trusted for
analysis, including cases where:

- the source metadata is empty, forbidden, or changes for an existing run
- the submitted rows are structurally invalid
- the rows later fail snapshot validation on load

This is the boundary behind validation failures such as
`snapshot_source_forbidden`, `snapshot_source_immutable`,
`snapshot_mixed_sources`, `snapshot_missing_columns`,
`snapshot_invalid_timestamp`, `snapshot_duplicate_rows`,
`snapshot_duplicate_candle`, `snapshot_timestamp_out_of_order`,
`snapshot_ohlc_integrity_invalid`, and read-side `snapshot_data_invalid`.

Invalid data must be replaced by a new snapshot run. It must not be repaired by
mutating existing persisted rows in place.

## `ingestion_runs` Contract

Each snapshot run is anchored by exactly one `ingestion_runs` row with this
required persisted shape:

| Field | Required | Expectation |
| --- | --- | --- |
| `ingestion_run_id` | required | Stable snapshot identifier. Use UUIDv4 for analysis-facing runs. |
| `created_at` | required | Server-generated ISO-8601 UTC timestamp recorded when the run row is created. |
| `source` | required | Non-empty real-market provider identifier. Demo/seed sources are out of contract. |
| `symbols_json` | required | JSON array of symbols covered by the run. |
| `timeframe` | required | Canonical timeframe for the persisted snapshot rows, such as `D1`. |
| `fingerprint_hash` | optional | Deterministic checksum/fingerprint used as evidence metadata when available. |

Required write-time expectations:

- `source` is normalized and immutable for a given `ingestion_run_id`.
- `symbols_json` and `timeframe` describe the bounded snapshot coverage that the
  read side can validate.
- `fingerprint_hash` is evidence metadata only. It does not widen the runtime
  boundary beyond snapshot-only analysis.

## `ohlcv_snapshots` Contract

Each persisted market-data row must use this bounded row shape:

| Field | Required | Expectation |
| --- | --- | --- |
| `ingestion_run_id` | required | Foreign key to the parent `ingestion_runs` row. |
| `symbol` | required | Instrument identifier covered by the snapshot. |
| `timeframe` | required | Timeframe for the row. |
| `ts` | required | Candle timestamp stored as Unix epoch milliseconds. |
| `open` | required | Open price. |
| `high` | required | High price. |
| `low` | required | Low price. |
| `close` | required | Close price. |
| `volume` | required | Volume value stored with the candle. |

The composite key `(ingestion_run_id, symbol, timeframe, ts)` is the immutable
row identity.

### Row-level validity expectations

Before persistence, submitted server-side rows are expected to satisfy all of
the following:

- all rows belong to one real `source`, and the submitted row source matches the
  parent `ingestion_runs.source`
- required market-data fields are present
- timestamps are parseable, ordered ascending, and not duplicated in the
  submitted series
- `(symbol, timeframe, timestamp)` combinations are unique
- OHLC values are structurally valid: `high` is not below `open`, `close`, or
  `low`, and `low` is not above `open` or `close`

The persisted table does not store `source` per row. Source ownership is
anchored once at the parent `ingestion_runs` row and enforced before row
persistence.

## Immutability Boundary

The ingestion boundary is append-only at create time and immutable after
persistence:

- `ohlcv_snapshots` rows must not be updated or deleted in place
- the parent `ingestion_runs.source` must not change for an existing run
- corrections, reloads, or provider changes require a new `ingestion_run_id`
  and a new immutable snapshot

This is the bounded immutability contract relied on by snapshot-only analysis.

## Evidence and Log Output Expectations

Every server-side ingestion execution must leave enough evidence to audit what
was created and why it is trusted for analysis. At minimum, capture or emit:

- `ingestion_run_id`
- `created_at`
- `source`
- `timeframe`
- covered symbols or `symbols_json`
- persisted row count
- validation outcome (`valid`, `missing`, or `invalid`)
- failure code when validation rejects the snapshot
- `fingerprint_hash` when available

When the canonical server runbook path uses `scripts/run_snapshot_ingestion.py`,
the evidence output names are explicit:

- success evidence file: `ingestion-run-<ingestion_run_id>.json`
- failure evidence file: `snapshot-ingestion-failed-YYYYMMDDTHHMMSSZ.json`
- active-run lock file: `snapshot-ingestion.lock`

The success and failure evidence payloads must include:

- `attempted_at`
- `status`
- `requested` schedule inputs
- explicit evidence file path

This evidence is operational. It does not create a new public contract or widen
the repository scope beyond server-side snapshot creation for analysis use.

## Restart and Duplicate-Run Handling

Restart behavior and duplicate-run handling are explicit for the canonical
single-server scheduling path:

- the scheduled wrapper acquires `snapshot-ingestion.lock` before provider fetch
  or repository writes begin
- if another scheduled trigger fires while the lock exists, that later trigger
  fails closed with `snapshot_ingestion_already_running` and writes a failure
  evidence file
- overlapping scheduled runs are not allowed; duplicate-run handling is
  skip-and-log, not parallel execution
- if the server or process restarts mid-run, the remaining lock file is treated
  as an operator-review marker; verify no ingestion process is active, then
  remove the stale lock before the next retry
- a restarted or retried ingestion execution writes a new `ingestion_run_id`
  rather than mutating or reusing partial persisted rows

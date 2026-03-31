# Snapshot Ingestion Job Runbook

`scripts/run_snapshot_ingestion.py` is the bounded server-side snapshot
ingestion entrypoint for issue `#857`.

Scope boundaries:
- non-live snapshot creation only
- bounded to `D1` snapshots
- bounded to one registered provider (`yfinance`) in the default server entrypoint
- no public API trigger surface
- no live streaming ingestion
- no cloud or distributed scheduling

## Command

```powershell
python scripts/run_snapshot_ingestion.py --symbols AAPL,MSFT --timeframe D1 --limit 90 --provider yfinance
```

## Single Supported Scheduling Path

The only supported repeatable scheduling path in this repository is one
single-server cron entry that invokes the script directly.

Canonical cadence definition:
- daily at `06:05` UTC
- one server
- one scheduler entry
- one active run at a time

Exact cron example:

```cron
5 6 * * * cd /srv/apps/trading-engine && /usr/bin/python scripts/run_snapshot_ingestion.py --symbols AAPL,MSFT --timeframe D1 --limit 90 --provider yfinance --db-path /srv/data/trading-engine/cilly_trading.db --schedule-name server-daily-d1 --evidence-dir /srv/data/trading-engine/evidence/snapshot-ingestion
```

This runbook remains bounded to server-side operation only. It does not define
cloud orchestration, distributed scheduling, or public alerting products.

## Reviewable Server Output

The script produces:
- structured engine log events for `snapshot_ingestion.started`, `snapshot_ingestion.completed`, and `snapshot_ingestion.failed`
- a single JSON line on stdout for successful runs
- a single JSON line on stderr for bounded failures
- one success evidence file named `ingestion-run-<ingestion_run_id>.json`
- one failure evidence file named `snapshot-ingestion-failed-YYYYMMDDTHHMMSSZ.json`
- one active-run lock file named `snapshot-ingestion.lock`

Successful output includes:
- `attempted_at`
- `ingestion_run_id`
- `provider_name`
- `timeframe`
- `symbols`
- `inserted_rows`
- `fingerprint_hash`
- per-symbol dataset summaries

Failure output includes:
- `attempted_at`
- `code`
- `detail`
- `provider_name` when available
- `symbol` when available
- requested schedule inputs
- evidence file path

## Restart and Duplicate-Run Handling

The scheduled wrapper is restart-safe by failing closed:
- it creates `snapshot-ingestion.lock` before provider fetch begins
- if a later trigger finds the lock, it exits non-zero with `snapshot_ingestion_already_running`
- the duplicate trigger writes a failure evidence file instead of starting a parallel run
- if the server or process restarts mid-run, inspect the lock, confirm no ingestion process is still active, then remove the stale lock before retrying
- every retry creates a new `ingestion_run_id`; no partial rows are repaired in place

Keep runs bounded by:
- using the default `yfinance` provider only
- using `D1` only
- keeping `--limit` within the enforced maximum

The job writes:
- one row to `ingestion_runs`
- immutable OHLCV rows to `ohlcv_snapshots`

If provider data is empty or invalid, the job fails explicitly and does not write partial snapshot rows.

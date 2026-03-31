# Snapshot Ingestion Job

`scripts/run_snapshot_ingestion.py` runs the bounded server-side snapshot ingestion job for issue `#856`.

Scope boundaries:
- non-live snapshot creation only
- bounded to `D1` snapshots
- bounded to one registered provider (`yfinance`) in the default server entrypoint
- no public API trigger surface
- no live streaming ingestion

## Command

```powershell
python scripts/run_snapshot_ingestion.py --symbols AAPL,MSFT --timeframe D1 --limit 90 --provider yfinance
```

## Reviewable Server Output

The script produces:
- structured engine log events for `snapshot_ingestion.started`, `snapshot_ingestion.completed`, and `snapshot_ingestion.failed`
- a single JSON line on stdout for successful runs
- a single JSON line on stderr for bounded failures

Successful output includes:
- `ingestion_run_id`
- `provider_name`
- `timeframe`
- `symbols`
- `inserted_rows`
- `fingerprint_hash`
- per-symbol dataset summaries

## Scheduling Notes

This job is intended for repeatable server scheduling such as Windows Task Scheduler or cron. Keep runs bounded by:
- using the default `yfinance` provider only
- using `D1` only
- keeping `--limit` within the enforced maximum

The job writes:
- one row to `ingestion_runs`
- immutable OHLCV rows to `ohlcv_snapshots`

If provider data is empty or invalid, the job fails explicitly and does not write partial snapshot rows.

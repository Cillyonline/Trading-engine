# Paper Runtime Evidence Series API

`GET /paper/runtime/evidence-series` is a read-only inspection endpoint for
offline bounded paper-runtime evidence series summaries.

The endpoint only reads saved local JSON run-output artifacts from
`CILLY_PAPER_RUNTIME_EVIDENCE_SERIES_DIR`. It does not trigger paper-runtime runs,
import or execute `scripts/run_daily_bounded_paper_runtime.py`, modify
paper execution behavior, modify signal generation, modify risk logic, modify
score thresholds, modify data ingestion, deploy to a VPS, or write runtime
artifacts.

## States

- `not_configured` - `CILLY_PAPER_RUNTIME_EVIDENCE_SERIES_DIR` is unset.
- `missing` - the configured path is absent or is not a directory.
- `empty` - the configured directory exists but has no matching `run-*.json`
  files.
- `available` - matching saved run-output files were read and summarized.

All states return HTTP 200 with an explicit bounded payload.

## Response Summary

The response includes deterministic aggregate fields:

- run count
- run-quality distribution
- eligible, skipped, and rejected totals
- skip-reason counts
- reconciliation status counts
- total reconciliation mismatches
- per-run mismatch counts
- summary-file references
- run-file references

Ordering is deterministic: files and count maps are sorted by stable string
keys.

## Boundary

This endpoint is inspection-only and non-live. It does not imply trader validation,
production readiness, live-trading readiness, broker readiness, operational
readiness, or profitability.

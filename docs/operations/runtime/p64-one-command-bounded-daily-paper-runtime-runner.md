# OPS-P64: One-Command Bounded Daily Paper Runtime Runner

## Purpose

Provide one bounded operator-facing command that runs the documented OPS-P63
daily paper runtime workflow in one controlled execution path.

## Scope Boundary

In scope:

- one bounded operator-facing daily runtime runner
- one-command execution of the OPS-P63 ordered workflow
- explicit bounded success and failure behavior
- bounded documentation and tests for the runner

Out of scope:

- live trading
- broker integration
- production scheduler automation
- strategy optimization and calibration
- changing the OPS-P63 workflow order

## Required Ordered Execution

The runner executes these steps in this exact order:

1. Snapshot ingestion
2. Analysis and signal generation
3. Bounded paper execution cycle
4. Reconciliation
5. Evidence capture

## Operator Command

Local invocation:

```bash
python scripts/run_daily_bounded_paper_runtime.py \
  --db-path cilly_trading.db \
  --base-url http://127.0.0.1:18000
```

The command orchestrates:

- `scripts/run_snapshot_ingestion.py`
- `POST /analysis/run`
- `scripts/run_paper_execution_cycle.py`
- `scripts/run_post_run_reconciliation.py`
- `scripts/generate_weekly_review.py`

## Explicit Failure Behavior

The runner is fail-fast:

- it stops immediately on the first failed step
- it emits bounded JSON error output to stderr with:
  - `failed_step`
  - `detail`
  - `steps_completed`
  - `step_order`
- it returns step-specific non-zero exit codes

Bounded execution note:

- execution-step exit code `1` from `run_paper_execution_cycle.py` is treated as
  bounded `no_eligible` completion, not a workflow crash
- reconciliation and evidence generation remain strict pass/fail gates

## Bounded Summary Output

On success, the runner emits bounded JSON summary output to stdout with:

- `ingestion_run_id`
- `analysis_run_id`
- `steps_completed`
- `verification_surfaces` evidence file paths
- `summary_file` path

## Verification Surfaces Remain Usable

The runner captures read-only run-record snapshots from existing surfaces:

- `/signals`
- `/paper/trades`
- `/paper/positions`
- `/paper/reconciliation`

## Evidence Path

Default bounded run-record output path:

- `runs/daily-runtime/<YYYY-MM-DD>/`

Summary file pattern:

- `runs/daily-runtime/<YYYY-MM-DD>/daily-runtime-summary-<YYYYMMDDTHHMMSSZ>.json`

## Explicit Claim Boundary

This runner remains bounded and non-live:

- no live orders are placed
- no broker APIs are called
- no real capital is at risk
- no live-readiness claim is made
- no broker-readiness claim is made
- no production-readiness claim is made

## References

- `docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md`
- `scripts/run_daily_bounded_paper_runtime.py`

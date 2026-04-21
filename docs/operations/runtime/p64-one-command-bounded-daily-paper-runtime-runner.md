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

## Base URL by Invocation Context (Critical)

The `--base-url` value depends on where the runner command executes.

Host-context invocation (from host shell; staging bind published on `18000`):

```bash
python scripts/run_daily_bounded_paper_runtime.py \
  --db-path cilly_trading.db \
  --base-url http://127.0.0.1:18000
```

In-container invocation (from `docker compose ... exec api`; target container port `8000`):

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_daily_bounded_paper_runtime.py \
  --db-path /data/db/cilly_trading.db \
  --base-url http://127.0.0.1:8000
```

Warning: do not use `http://127.0.0.1:18000` inside the `api` container. That
host bind is not reachable from container-local loopback and will fail during
`analysis_signal_generation`.

## Explicit Failure Behavior

The runner is fail-fast:

- it stops immediately on the first failed step
- it emits bounded JSON error output to stderr with:
  - `failed_step`
  - `detail`
  - `steps_completed`
  - `step_order`
  - `operator_action_contract_version`
  - `operator_action_contract`
- it returns step-specific non-zero exit codes

Bounded execution note:

- execution-step exit code `1` from `run_paper_execution_cycle.py` is treated as
  bounded `no_eligible` completion, not a workflow crash
- reconciliation and evidence generation remain strict pass/fail gates

## Bounded Summary Output

On success, the runner emits bounded JSON summary output to stdout with:

- `ingestion_run_id`
- `analysis_run_id`
- `run_quality_status`
- `run_quality_classification_version`
- `run_quality_inputs`
- `operator_action_contract_version`
- `operator_action_contract`
- `steps_completed`
- `verification_surfaces` evidence file paths
- `summary_file` path

Deterministic run-quality interpretation:

1. `healthy`
   - execution pass/ok with `eligible > 0`
   - clean reconciliation (`ok: true`, `mismatches == 0` or omitted)
2. `no_eligible`
   - bounded non-error execution no-eligible state (`returncode == 1` or
     execution `status == "no_eligible"`)
   - clean reconciliation (`ok: true`, `mismatches == 0` or omitted)
3. `degraded`
   - reconciliation `ok: false`, or `mismatches > 0`, or
   - inputs do not match healthy/no_eligible conditions

Determinism contract:

- same run summary inputs always produce the same `run_quality_status`
- the same `run_quality_status` always produces the same `operator_action_contract`
- classification is bounded evidence quality only and remains non-live

Deterministic operator action contract:

| `run_quality_status` | `action_category` | Deterministic bounded operator interpretation |
| --- | --- | --- |
| `healthy` | `informational` | Record the bounded daily runtime evidence and continue the next scheduled bounded run. |
| `no_eligible` | `review_required` | Review the bounded no-eligible outcome, confirm skip reasons and inputs, and record the run without retrying solely to force activity. |
| `degraded` | `blocking` | Stop continuation claims for that run, investigate the degraded evidence, and open or update follow-up before the next bounded decision. |

Operator-facing category wording:

- `healthy` is informational
- `no_eligible` is review-required
- `degraded` is blocking

Fail-fast operator action boundary:

- pre-execution failures are retry-required
- execution or post-execution failures are blocking
- pre-execution retry applies only before bounded paper execution starts
- once execution has started, the operator must stop and investigate before any rerun decision
- this bounded action contract does not imply operational readiness

## Verification Surfaces Remain Usable

The runner captures read-only run-record snapshots from existing surfaces:

- `/signals`
- `/paper/trades`
- `/paper/positions`
- `/paper/reconciliation`

## OPS-P65 First Successful Bounded OPS-P64 Staging Run (2026-04-06)

First attempted in-container command (failed due invocation context):

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_daily_bounded_paper_runtime.py \
  --db-path /data/db/cilly_trading.db \
  --base-url http://127.0.0.1:18000
```

Observed failure signature:

- `failed_step: analysis_signal_generation`
- `detail` included `URLError: <urlopen error [Errno 111] Connection refused>`

Interpretation: invocation-context error only (host-vs-container base-url
mismatch), not a runner logic defect.

Successful corrected command:

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_daily_bounded_paper_runtime.py \
  --db-path /data/db/cilly_trading.db \
  --base-url http://127.0.0.1:8000
```

Recorded bounded success evidence:

- `status: ok`
- `run_quality_status: no_eligible`
- `ingestion_run_id: 813b4a13-de3d-4633-8968-1a7fbc0af2f3`
- `analysis_run_id: 89cec8c4d8a92bbecb2c4f6d59eb9d06972b1c4b4f1ed59ee686bca1816787a0`
- `step_order`:
  - `snapshot_ingestion`
  - `analysis_signal_generation`
  - `bounded_paper_execution_cycle`
  - `reconciliation`
  - `evidence_capture`
- `steps_completed` matched full `step_order` (all ordered steps completed)

Bounded execution interpretation from the same summary:

- bounded paper execution cycle completion: `status: no_eligible`
- `eligible: 0`
- `skipped: 12`
- skip reasons observed: `duplicate_entry`, `score_below_threshold`
- these bounded skip outcomes are valid non-error completion states

Read-only verification outcomes captured in the run record:

- `/paper/trades` -> `total: 3`
- `/paper/positions` -> `total: 3`
- `/paper/reconciliation` -> `ok: true`, `mismatches: 0`

Summary and evidence file paths recorded under:

- summary file:
  - `/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary-20260406T144441Z.json`
- verification surfaces:
  - `/data/artifacts/daily-runtime/2026-04-06/signals.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-trades.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-positions.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-reconciliation.json`

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

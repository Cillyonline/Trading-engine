# OPS-P63: Daily Bounded Paper Runtime Workflow

## Purpose

Define one deterministic, repeatable daily operator workflow for bounded paper execution in bounded staging.

The workflow documents and validates the ordered runtime path from ingestion through reconciliation and evidence capture.

## Scope Boundary

In scope:

- bounded staging only
- daily operator runtime workflow definition
- ordered steps from ingestion to evidence capture
- explicit verification points and read-only inspection checks

Out of scope:

- live trading
- broker integration
- production-readiness claims
- strategy optimization
- score or threshold calibration
- UI or dashboard expansion

## Required Daily Workflow Order

1. Snapshot ingestion
2. Analysis and signal generation
3. Bounded paper execution cycle
4. Reconciliation
5. Evidence capture and run record

## Step 1 - Snapshot Ingestion

This step is runnable independently.

### Operator Invocation Paths

Local:

```bash
python scripts/run_snapshot_ingestion.py \
  --symbols AAPL,MSFT,NVDA,GS,WMT,COST \
  --timeframe D1 \
  --limit 90 \
  --provider yfinance \
  --db-path cilly_trading.db \
  --evidence-dir runs/snapshot_ingestion
```

Bounded staging:

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_snapshot_ingestion.py \
  --symbols AAPL,MSFT,NVDA,GS,WMT,COST \
  --timeframe D1 \
  --limit 90 \
  --provider yfinance \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/snapshot_ingestion
```

### Verification Point

- command emits success evidence file `ingestion-run-<ingestion_run_id>.json`
- ingestion output includes `result.ingestion_run_id` used by Step 2

## Step 2 - Analysis and Signal Generation

This step is runnable independently with any valid `ingestion_run_id`.

### Operator Invocation Paths

Authoritative endpoint path: `POST /analysis/run`

```bash
curl -sS -X POST "http://127.0.0.1:18000/analysis/run" \
  -H "Content-Type: application/json" \
  -H "X-Cilly-Role: operator" \
  -d '{
    "ingestion_run_id": "<INGESTION_RUN_ID>",
    "symbol": "AAPL",
    "strategy": "RSI2",
    "market_type": "stock",
    "lookback_days": 200
  }'
```

### Verification Point

Inspect persisted signal state through the read-only surface:

```bash
curl -sS -H "X-Cilly-Role: read_only" \
  "http://127.0.0.1:18000/signals?ingestion_run_id=<INGESTION_RUN_ID>&limit=100"
```

### Base URL Context Mapping (Host vs Container)

When invoking the OPS-P64 daily runner, map `--base-url` to invocation context:

- host shell invocation -> `http://127.0.0.1:18000`
- `docker compose ... exec api` invocation -> `http://127.0.0.1:8000`

Warning: do not use `http://127.0.0.1:18000` from inside the `api` container.
That value is the host-published bind and causes
`analysis_signal_generation` connection-refused failures in container context.

## Step 3 - Bounded Paper Execution Cycle

This step is runnable independently against existing signal state.

### Operator Invocation Paths

Local:

```bash
python scripts/run_paper_execution_cycle.py \
  --db-path cilly_trading.db \
  --evidence-dir runs/paper-execution
```

Bounded staging:

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_paper_execution_cycle.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/paper-execution
```

### Verification Point

Inspect paper state through read-only surfaces:

```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/trades
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/positions
```

## Step 4 - Reconciliation

This step is runnable independently after any execution cycle.

### Operator Invocation Paths

Local:

```bash
python scripts/run_post_run_reconciliation.py \
  --db-path cilly_trading.db \
  --evidence-dir runs/reconciliation
```

Bounded staging:

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_post_run_reconciliation.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/reconciliation
```

### Verification Point

Require reconciliation state:

- `ok: true`
- `mismatches: 0`

Read-only inspection surface:

```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/reconciliation
```

## Step 5 - Evidence Capture and Run Record

This step is runnable independently for daily evidence capture.

### Operator Invocation Paths

Capture deterministic review evidence:

```bash
docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/generate_weekly_review.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/daily-runtime
```

Capture endpoint snapshots for the daily run record:

```bash
RUN_DATE="$(date -u +%F)"
mkdir -p "runs/daily-runtime/${RUN_DATE}"

curl -sS -H "X-Cilly-Role: read_only" \
  "http://127.0.0.1:18000/signals?ingestion_run_id=<INGESTION_RUN_ID>&limit=100" \
  > "runs/daily-runtime/${RUN_DATE}/signals.json"

curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/trades \
  > "runs/daily-runtime/${RUN_DATE}/paper-trades.json"

curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/positions \
  > "runs/daily-runtime/${RUN_DATE}/paper-positions.json"

curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/reconciliation \
  > "runs/daily-runtime/${RUN_DATE}/paper-reconciliation.json"
```

### Deterministic Run-Quality Classification (Daily Summary)

The daily summary artifact includes explicit bounded run-quality fields:

- `run_quality_status`
- `run_quality_classification_version`
- `run_quality_inputs`
- `operator_action_contract_version`
- `operator_action_contract`

Deterministic classification rules use existing runtime summary inputs only:

1. `degraded`
   - reconciliation shows `ok: false`, or
   - reconciliation `mismatches > 0`, or
   - inputs do not match `healthy` or `no_eligible`
2. `no_eligible`
   - execution step indicates bounded no-eligible completion
     (`returncode == 1` or execution `status == "no_eligible"`), and
   - reconciliation is clean (`ok: true` and `mismatches == 0` or omitted)
3. `healthy`
   - execution shows pass/ok completion with eligible executions
     (`returncode == 0`, execution `status in {"pass","ok"}`, `eligible > 0`), and
   - reconciliation is clean (`ok: true` and `mismatches == 0` or omitted)

Bounded interpretation:

- `no_eligible` is valid non-error completion in bounded runtime evidence
- `run_quality_status` is operator-facing evidence quality only
- classification does not widen runtime scope and does not imply live readiness

### Deterministic Operator Action Contract (Daily Summary)

The daily summary artifact records one deterministic next-action contract for
each classified `run_quality_status`.

Recorded action fields:

- `operator_action_contract_version`
- `operator_action_contract.action_category`
- `operator_action_contract.action_code`
- `operator_action_contract.action_summary`
- `operator_action_contract.escalation_boundary`

Deterministic summary-state mapping:

| `run_quality_status` | `action_category` | Deterministic bounded operator interpretation |
| --- | --- | --- |
| `healthy` | `informational` | Record the bounded daily runtime evidence and continue the next scheduled bounded run. |
| `no_eligible` | `review_required` | Review the bounded no-eligible outcome, confirm skip reasons and inputs, and record the run without retrying solely to force activity. |
| `degraded` | `blocking` | Stop continuation claims for that run, investigate the degraded evidence, and open or update follow-up before the next bounded decision. |

Operator-facing category wording:

- `healthy` is informational
- `no_eligible` is review-required
- `degraded` is blocking

Fail-fast bounded runner guidance:

- pre-execution failures are retry-required
- execution or post-execution failures are blocking
- retry-required applies only when the daily command path fails before bounded paper execution starts
- blocking applies once execution starts or when reconciliation/evidence is incomplete, so the operator does not blindly rerun a partially completed daily workflow

Escalation boundary:

- the action contract is bounded operator guidance only
- it does not imply operational readiness
- it does not imply broker readiness
- it does not imply production readiness

## Daily Sequential Command Sequence (Bounded Staging)

The full workflow is runnable sequentially in this order:

```bash
INGEST_OUTPUT="$(docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_snapshot_ingestion.py \
  --symbols AAPL,MSFT,NVDA,GS,WMT,COST \
  --timeframe D1 \
  --limit 90 \
  --provider yfinance \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/snapshot_ingestion)"

INGESTION_RUN_ID="$(printf '%s\n' "${INGEST_OUTPUT}" | python -c "import json,sys; print(json.loads(sys.stdin.readline())['result']['ingestion_run_id'])")"

curl -sS -X POST "http://127.0.0.1:18000/analysis/run" \
  -H "Content-Type: application/json" \
  -H "X-Cilly-Role: operator" \
  -d "{\"ingestion_run_id\":\"${INGESTION_RUN_ID}\",\"symbol\":\"AAPL\",\"strategy\":\"RSI2\",\"market_type\":\"stock\",\"lookback_days\":200}"

docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_paper_execution_cycle.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/paper-execution

docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/run_post_run_reconciliation.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/reconciliation

docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api \
  python /app/scripts/generate_weekly_review.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/daily-runtime
```

## Verification Surfaces (Read-Only)

The workflow verification points use existing surfaces only:

- `/signals`
- `/paper/trades`
- `/paper/positions`
- `/paper/reconciliation`

## Bounded End-to-End Validation Example (2026-04-05)

Bounded staging validation example from the already-validated runtime path:

- ingestion run id observed: `02f4d83e-5842-4216-8ba7-51a12be9ea3b`
- analysis result produced persisted signals (`signals_read: 12`)
- bounded paper execution cycle result:
  - `eligible: 3`
  - `status: pass`
- read-only inspection after execution:
  - `/paper/trades -> total: 3`
  - `/paper/positions -> total: 3`
- reconciliation result:
  - `ok: true`
  - `mismatches: 0`

This example demonstrates the full daily sequence end-to-end in bounded staging. It does not widen runtime scope.

## OPS-P65 Bounded OPS-P64 Staging Evidence (2026-04-06)

First in-container run used the wrong base URL and failed at
`analysis_signal_generation` with
`URLError: <urlopen error [Errno 111] Connection refused>`.
This is an invocation-context issue (host-vs-container base-url mismatch), not
runner logic failure.

Successful in-container command:

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_daily_bounded_paper_runtime.py \
  --db-path /data/db/cilly_trading.db \
  --base-url http://127.0.0.1:8000
```

Recorded summary evidence:

- `status: ok`
- `run_quality_status: no_eligible`
- `ingestion_run_id: 813b4a13-de3d-4633-8968-1a7fbc0af2f3`
- `analysis_run_id: 89cec8c4d8a92bbecb2c4f6d59eb9d06972b1c4b4f1ed59ee686bca1816787a0`
- ordered steps completed:
  - `snapshot_ingestion`
  - `analysis_signal_generation`
  - `bounded_paper_execution_cycle`
  - `reconciliation`
  - `evidence_capture`

Bounded paper execution cycle interpretation for this run:

- `status: no_eligible`
- `eligible: 0`
- `skipped: 12`
- skip reasons: `duplicate_entry`, `score_below_threshold`
- interpretation: bounded-valid non-error completion

Read-only verification outcomes in the same run record:

- `/paper/trades` -> `total: 3`
- `/paper/positions` -> `total: 3`
- `/paper/reconciliation` -> `ok: true`, `mismatches: 0`

Summary and evidence path:

- summary:
  - `/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary-20260406T144441Z.json`
- evidence files:
  - `/data/artifacts/daily-runtime/2026-04-06/signals.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-trades.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-positions.json`
  - `/data/artifacts/daily-runtime/2026-04-06/paper-reconciliation.json`

## Explicit Claim Boundary

This workflow remains bounded and non-live:

- no live orders are placed
- no broker APIs are called
- no real capital is at risk
- no production-readiness claim is made
- no strategy optimization claim is made

## References

- `docs/operations/runtime/snapshot_ingestion_contract.md`
- `docs/operations/runtime/p60-signal-to-paper-operator-path.md`
- `docs/operations/runtime/p53-automated-review-operations.md`
- `docs/operations/runtime/phase-44-paper-operator-workflow.md`

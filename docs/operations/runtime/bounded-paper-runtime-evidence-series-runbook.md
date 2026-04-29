# Bounded Paper Runtime Evidence-Series Runbook

## Purpose

This runbook defines the manual operator procedure for repeated bounded
paper-runtime evidence-series runs in the style required by issue #1060.

The procedure is documentation-only. It does not automate the runner.
It does not trigger paper-runtime runs from a browser.
It does not change runtime behavior.
It does not modify paper execution behavior.
It does not change signal generation.
It does not change risk logic.
It does not change thresholds.
It does not change data ingestion.

## Scope Boundary

In scope:

- manual preflight before each bounded paper-runtime run
- the exact bounded daily runtime runner command
- post-run Docker and read-only health checks
- per-run evidence record format
- local operator log location
- bounded classification of `healthy`, `no_eligible`, and `degraded`
- explicit warning about same-day repeated runs

Out of scope:

- scheduler automation
- browser run triggers
- runner modification
- paper execution behavior changes
- signal generation changes
- risk logic, threshold, or ingestion changes
- new backend endpoints
- new frontend surfaces
- live trading
- broker integration
- readiness or profitability claims

## Manual Evidence-Series Cadence

Use this runbook for 20 to 30 manually executed bounded paper-runtime runs.

Fresh daily runs are traderically more meaningful than repeated same-day runs
because fresh daily runs can observe new market data, changed signals, and new
bounded skip or execution outcomes. Repeated same-day runs are still useful for
operator-process evidence, log discipline, and bounded runtime stability
inspection, but they must not be interpreted as independent market evidence.

## Local Operator Log Location

Store local operator notes and copied command output outside committed
authoritative paths unless a later issue explicitly requires committing them.

Recommended local-only path:

```text
runs/operator-logs/bounded-paper-runtime-evidence-series/<YYYY-MM-DD>/
```

Suggested per-run files:

- `run-<NN>-operator-notes.md`
- `run-<NN>-runner-stdout.json`
- `run-<NN>-runner-stderr.txt`
- `run-<NN>-docker-ps.txt`
- `run-<NN>-health.txt`

## Before Each Run

Complete these preflight steps before every run in the series:

1. Confirm the run number and UTC run date for the evidence table.
2. Confirm the operator is using bounded staging only.
3. Confirm no issue or local edit has changed paper execution behavior,
   signal generation, risk logic, thresholds, or ingestion for this run.
4. Confirm Docker staging services are running:

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  ps
```

5. Confirm the API health endpoint responds from the host:

```bash
curl -sS http://127.0.0.1:18000/health
```

6. Create the local operator log directory:

```bash
RUN_DATE="$(date -u +%F)"
mkdir -p "runs/operator-logs/bounded-paper-runtime-evidence-series/${RUN_DATE}"
```

7. Record the preflight result in the per-run notes before starting the runner.

## Run Command

Execute the runner manually from inside the `api` container:

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_daily_bounded_paper_runtime.py \
  --db-path /data/db/cilly_trading.db \
  --base-url http://127.0.0.1:8000
```

Important invocation boundary:

- use `http://127.0.0.1:8000` when running inside the `api` container
- use `http://127.0.0.1:18000` only for host-side checks
- do not use the host-published `18000` bind from inside the container

Copy stdout and stderr into the local operator log files for the run.

## After Each Run

Run these post-run checks after every runner invocation.

Docker process check:

```bash
docker compose --env-file /root/Trading-engine/.env \
  -f docker/staging/docker-compose.staging.yml \
  ps
```

Host health check:

```bash
curl -sS http://127.0.0.1:18000/health
```

Read-only paper state checks:

```bash
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/trades
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/positions
curl -sS -H "X-Cilly-Role: read_only" http://127.0.0.1:18000/paper/reconciliation
```

Record the summary file path and verification surface paths emitted by the
runner. The expected bounded daily runtime evidence path is:

```text
/data/artifacts/daily-runtime/<YYYY-MM-DD>/
```

## Per-Run Record Format

For each run, append one row to the evidence table and keep the local operator
notes with the copied command output.

Required per-run fields:

- run number
- UTC run timestamp
- operator initials or handle
- runner exit code
- `run_quality_status`
- `ingestion_run_id`
- `analysis_run_id`
- eligible count
- skipped count
- reconciliation `ok`
- reconciliation mismatches
- Docker status check result
- host health check result
- summary file path
- local operator log path
- notes or follow-up

## Evidence Table Template

| Run | UTC timestamp | Operator | Exit code | Classification | Ingestion run ID | Analysis run ID | Eligible | Skipped | Reconciliation ok | Mismatches | Docker ps | Health | Summary file | Local operator log | Notes |
| --- | --- | --- | --- | --- | --- | --- | ---: | ---: | --- | ---: | --- | --- | --- | --- | --- |
| 01 | `<YYYY-MM-DDTHH:MM:SSZ>` | `<operator>` | `<code>` | `healthy/no_eligible/degraded` | `<id>` | `<id>` | `<count>` | `<count>` | `true/false` | `<count>` | `pass/fail` | `pass/fail` | `<path>` | `<path>` | `<notes>` |

## Classification Rules

Classify each run from the runner summary and post-run checks.

`healthy`:

- runner completed successfully
- bounded paper execution reports pass/ok with `eligible > 0`
- reconciliation is clean: `ok: true` and `mismatches: 0`
- Docker and health checks pass after the run

`no_eligible`:

- runner completed as bounded non-error no-eligible execution
- execution reports `eligible: 0` or `status: no_eligible`
- reconciliation is clean: `ok: true` and `mismatches: 0`
- Docker and health checks pass after the run
- do not rerun solely to force eligible activity

`degraded`:

- runner fails after bounded execution has started, or
- reconciliation reports `ok: false`, or
- reconciliation reports `mismatches > 0`, or
- Docker or health checks fail after the run, or
- emitted evidence is incomplete or cannot be matched to the run record

For a degraded run, stop continuation claims for that run, preserve logs, and
open or update follow-up before treating the next run as clean evidence.

## Non-Live Boundary

This runbook is bounded and non-live:

- no live orders are placed
- no broker APIs are called
- no real capital is at risk
- no live-trading-readiness claim is made
- no broker-readiness claim is made
- no production-readiness claim is made
- no operational-readiness claim is made
- no trader-validation claim is made
- no profitability claim is made

## References

- `docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md`
- `docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md`
- `docs/operations/runtime/bounded-paper-runtime-evidence-series-summarizer.md`

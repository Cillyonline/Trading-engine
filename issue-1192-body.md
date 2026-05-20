## Context

#1190 was approved and merged. The server was synced to main at commit 2cf1f2c and the staging API container was rebuilt and healthy.

#1060 post-#1190 validation cannot continue because the bounded daily runtime workflow fails before paper execution.

Initial run failed at analysis_signal_generation with:

```text
URLError: <urlopen error [Errno 111] Connection refused>
```

Diagnosis confirmed:

- Inside the api container, http://127.0.0.1:8000/health/engine with X-Cilly-Role: read_only returns 200.
- Inside the api container, http://127.0.0.1:18000/health/engine fails with Connection refused.
- run_daily_bounded_paper_runtime.py defaults --base-url to http://127.0.0.1:18000.
- The script supports --base-url.

Retry with:

```bash
python /app/scripts/run_daily_bounded_paper_runtime.py --base-url http://127.0.0.1:8000
```

reached the API but failed at analysis_signal_generation with:

```text
HTTPError: HTTP Error 422: Unprocessable Entity
```

API logs confirm:

```text
POST /analysis/run HTTP/1.1 422 Unprocessable Entity
```

The workflow stops after snapshot_ingestion and never reaches bounded_paper_execution_cycle.

## Goal

Fix the bounded daily runtime analysis trigger so run_daily_bounded_paper_runtime.py can successfully complete analysis_signal_generation against the current /analysis/run contract.

## Acceptance Criteria

- Runtime analysis trigger no longer receives HTTP 422 for a valid bounded daily request.
- The fix is covered by deterministic tests.
- The bounded daily runtime can proceed past analysis_signal_generation in a controlled test or documented dry-run fixture.
- #1190 exit-signal behavior is preserved.
- No RSI2/TURTLE strategy logic changes.
- No score, threshold, calibration, risk-default, broker/live, production/VPS paper-state, or stale COST/GS/WMT cleanup changes.
- #1060 remains paused until Codex A approves the fix.

## Out of Scope

- Resuming #1060.
- Manual paper-state cleanup.
- Closing/resetting COST, GS, or WMT.
- Broker/live execution.
- Trader validation.
- Profitability, broker-readiness, live-readiness, or production-readiness claims.

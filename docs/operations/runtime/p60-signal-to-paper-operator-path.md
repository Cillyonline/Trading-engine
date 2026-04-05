# OPS-P60: Bounded Operator Path from Eligible Signals to Paper Execution State

## Purpose

This document defines and validates the authoritative bounded operator path from
eligible analysis signals to canonical paper execution state.

It addresses the gap between:

- non-empty signal state (verified via `/signals`)
- bounded signal-to-paper execution policy (OPS-P52)
- paper execution worker implementation (`paper_execution_worker.py`)
- and a clear, documented operator-facing runtime path that produces non-empty
  paper execution state

## Operator Path Status

### Path exists: YES (bounded, non-live)

A complete bounded path from eligible signals to canonical paper execution state
exists.  The path is implemented, documented, tested, and operationally
invocable via a single operator script.

### Authoritative Components

| Component | File | Status |
| --- | --- | --- |
| Signal source | `SqliteSignalRepository` (`list_signals`) | implemented, tested |
| Execution policy | `signal_to_paper_execution_policy.md` (OPS-P52) | documented, tested |
| Execution worker | `BoundedPaperExecutionWorker` (`paper_execution_worker.py`) | implemented, tested |
| State authority | `SqliteCanonicalExecutionRepository` (`paper_state_authority.py`) | implemented, tested |
| Operator script | `scripts/run_paper_execution_cycle.py` | implemented, documented |
| Inspection surfaces | `/paper/*`, `/trading-core/*` | implemented, tested |
| Reconciliation | `/paper/reconciliation` | implemented, tested |

## Bounded Operator Path (Step-by-Step)

The authoritative operator path is:

1. **Read eligible signals** — from `SqliteSignalRepository` via `list_signals`.
2. **Instantiate worker** — `BoundedPaperExecutionWorker` with
   `SqliteCanonicalExecutionRepository`.
3. **Process signals** — `worker.process_signal(signal)` or
   `worker.process_batch(signals)` applies the 5-step OPS-P52 policy:
   - Eligibility check (required signal fields)
   - Score threshold check (`>= 0.6`)
   - Duplicate-entry check (`(symbol, strategy, direction)`)
   - Cooldown check (`24h` per `(symbol, strategy)`)
   - Exposure and position-limit checks
4. **Persist canonical entities** — eligible signals produce deterministic
   `Order`, `ExecutionEvent`, and `Trade` entities persisted to
   `SqliteCanonicalExecutionRepository`.
5. **Verify via inspection** — operator confirms non-empty paper execution state
   via `/paper/trades`, `/paper/positions`, `/paper/account`, and validates
   consistency via `/paper/reconciliation`.

## Operator Script

The bounded operator script for executing the signal-to-paper path is:

```
scripts/run_paper_execution_cycle.py
```

### Usage

```bash
# Local (repo root)
python scripts/run_paper_execution_cycle.py

# With explicit paths
python scripts/run_paper_execution_cycle.py \
  --db-path /path/to/cilly_trading.db \
  --evidence-dir runs/paper-execution

# Bounded staging
docker compose --env-file .env \
  -f docker/staging/docker-compose.staging.yml \
  exec api python /app/scripts/run_paper_execution_cycle.py \
  --db-path /data/db/cilly_trading.db \
  --evidence-dir /data/artifacts/paper-execution
```

### Inputs

| Input | Source | Description |
| --- | --- | --- |
| `--db-path` | CLI argument | SQLite database containing signal and execution state |
| `--evidence-dir` | CLI argument | Output directory for execution evidence JSON |
| Signals | `SqliteSignalRepository.list_signals()` | All persisted signals from the database |
| Execution state | `SqliteCanonicalExecutionRepository` | Canonical orders, events, trades |

### Policy Gates

Every signal passes through the ordered 5-step OPS-P52 policy evaluation before
any paper entity is created.  The policy gates are:

1. `reject:invalid_signal_fields` — missing or invalid required fields
2. `skip:score_below_threshold` — signal score below `0.6`
3. `skip:duplicate_entry` — open position for `(symbol, strategy, direction)`
4. `skip:cooldown_active` — within `24h` cooldown for `(symbol, strategy)`
5. `reject:position_size_exceeds_limit` — per-position cap exceeded
6. `reject:total_exposure_exceeds_limit` — global exposure cap exceeded
7. `reject:concurrent_position_limit_exceeded` — max concurrent positions exceeded

### Outputs

| Output | Description |
| --- | --- |
| Evidence JSON | Timestamped file with execution results per signal |
| Stdout summary | `PAPER_EXECUTION_CYCLE:PASS` or `PAPER_EXECUTION_CYCLE:COMPLETE` |
| Exit code 0 | At least one signal was eligible and persisted |
| Exit code 1 | No signals were eligible (all skipped/rejected) |
| Exit code 2 | Runtime error |

### Evidence File Structure

```json
{
  "cycle_type": "bounded_paper_execution",
  "db_path": "/path/to/cilly_trading.db",
  "ran_at": "2026-04-05T00:00:00+00:00",
  "signals_read": 5,
  "eligible": 2,
  "skipped": 2,
  "rejected": 1,
  "results": [
    {
      "signal_id": "...",
      "outcome": "eligible",
      "order_id": "ord_...",
      "trade_id": "trd_..."
    },
    {
      "signal_id": "...",
      "outcome": "skip:score_below_threshold",
      "reason": "score=0.4 < min_score_threshold=0.6"
    }
  ],
  "status": "pass"
}
```

## Post-Execution Verification

After running the execution cycle, the operator verifies non-empty paper
execution state using the existing Phase 44 inspection workflow:

1. `GET /paper/trades` — confirm non-empty trade list
2. `GET /paper/positions` — confirm non-empty position list
3. `GET /paper/account` — confirm account reflects execution state
4. `GET /paper/reconciliation` — require `ok: true`, `mismatches: 0`

Alternatively, run the existing P53 post-run reconciliation script:

```bash
python scripts/run_post_run_reconciliation.py --db-path /path/to/cilly_trading.db
```

## Gap Analysis

### Previously Missing (addressed by P60)

- **Operator script**: No operator-facing script existed to invoke
  `BoundedPaperExecutionWorker` with signals from the signal repository.
  This is now provided by `scripts/run_paper_execution_cycle.py`.
- **Documentation**: The end-to-end operator path from signals to paper
  execution state was not clearly documented as a single bounded workflow.
  This is now documented in this file.

### Remaining Boundaries

- The execution cycle script is operator-invoked (manual trigger).  There is
  no automated scheduler or API endpoint that triggers execution cycles.
- The script reads all signals and processes them in batch.  There is no
  incremental or event-driven signal processing.
- These boundaries are intentional for the bounded paper simulation scope.

## Non-Live Boundary

This operator path operates exclusively within the bounded paper simulation:

- No live orders are placed.
- No broker APIs are called.
- No real capital is at risk.
- Completing this path does not imply live-trading readiness.
- This path does not constitute broker execution approval.

## References

- Policy: `docs/operations/runtime/signal_to_paper_execution_policy.md`
- Workflow: `docs/operations/runtime/phase-44-paper-operator-workflow.md`
- Inspection: `docs/api/paper_inspection.md`
- Worker: `src/cilly_trading/engine/paper_execution_worker.py`
- State authority: `src/cilly_trading/portfolio/paper_state_authority.py`
- P53 automation: `docs/operations/runtime/p53-automated-review-operations.md`

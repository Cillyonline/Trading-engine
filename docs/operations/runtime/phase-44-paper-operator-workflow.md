# Phase 44 Bounded Paper Operator Workflow

## Purpose
Define the minimum bounded Phase 44 operator workflow using existing simulator, inspection, and reconciliation surfaces.

This workflow is a runtime inspection and validation claim only. It does not introduce new mutation-heavy workflows, broker integrations, or live-trading behavior.

## Bounded Workflow Claim
Phase 44 is bounded to one operator verification workflow:

1. Confirm deterministic paper lifecycle behavior from canonical simulator artifacts.
2. Inspect canonical trading-core lifecycle entities (orders, execution events, trades, positions).
3. Inspect paper-facing account/trade/position views derived from canonical entities.
4. Reconcile canonical and paper-facing state and require zero mismatches.
5. Treat the result as bounded paper-runtime coherence evidence only.

## Workflow Boundary
This workflow is read-only, operator-facing, and validation-oriented.

In scope:
- deterministic paper lifecycle evidence
- canonical inspection surfaces for order lifecycle state
- paper inspection and reconciliation surfaces derived from canonical entities
- mismatch-based validation for workflow coherence

Out of scope:
- live trading
- broker integrations
- broad dashboard expansion
- production trading operations

## Required Runtime Surfaces

### Simulator and lifecycle evidence surfaces
- `src/cilly_trading/engine/paper_trading.py`
- `src/cilly_trading/engine/paper_order_lifecycle.py`
- `tests/test_paper_trading_simulator.py`
- `tests/cilly_trading/engine/test_paper_order_lifecycle.py`

### Canonical inspection surfaces
- `GET /trading-core/orders`
- `GET /trading-core/execution-events`
- `GET /trading-core/trades`
- `GET /trading-core/positions`

### Paper inspection and reconciliation surfaces
- `GET /paper/workflow`
- `GET /paper/trades`
- `GET /paper/positions`
- `GET /paper/account`
- `GET /paper/reconciliation`

## Explicit Operator Steps
1. Read workflow contract and current validation status from `GET /paper/workflow`.
2. Inspect canonical order lifecycle state via `GET /trading-core/orders`.
3. Inspect canonical execution lifecycle transitions via `GET /trading-core/execution-events`.
4. Inspect canonical trade and position state via `GET /trading-core/trades` and `GET /trading-core/positions`.
5. Inspect paper-facing trade, position, and account projections via `GET /paper/trades`, `GET /paper/positions`, and `GET /paper/account`.
6. Reconcile the workflow state via `GET /paper/reconciliation` and require `ok: true` and `summary.mismatches: 0`.

## Minimum Operator Evidence
The bounded Phase 44 workflow claim requires all of the following evidence:

- Deterministic simulator behavior is passing (`tests/test_paper_trading_simulator.py`).
- Paper inspection and reconciliation contract coverage is passing (`tests/test_api_paper_inspection_read.py`).
- Reconciliation returns `ok: true` and `summary.mismatches: 0` for valid lifecycle data.
- Paper inspection views are derived from canonical trading-core entities, not legacy trade payload authority.
- Full repository regression gate remains green (`python -m pytest`).

## Phase 24 vs Phase 44 Boundary

### Phase 24 (implemented simulator governance boundary)
- Defines and governs deterministic paper-trading simulator capability.
- Enforces non-live and non-broker constraints.
- Does not claim an operator runtime workflow as complete.

### Phase 44 (bounded runtime workflow claim in this phase slice)
- Claims one coherent operator workflow across simulator evidence, canonical inspection, paper inspection, and reconciliation.
- Remains read-only and verification-oriented.
- Does not claim full product workflow completeness or a broad paper-trading dashboard layer.

## Explicit Non-Goals
- Live trading
- Broker integration
- Full paper-trading UI redesign
- Mutation-heavy order-entry workflow
- Unrelated portfolio or strategy refactors

## Long-Run Evaluation Cadence

Run the full bounded operator workflow review after each of the following events:

1. **End of each paper trading session** — confirm reconciliation is clean before stopping.
2. **After process restart** — run `GET /paper/reconciliation` immediately on restart to verify state integrity before resuming evaluation.
3. **Before any strategy change** — capture a pre-change baseline (reconciliation result, account state, trade and position counts).
4. **After any strategy change** — run the full operator workflow review and compare against the pre-change baseline.
5. **Periodic scheduled review** — at minimum once per trading week, execute the full six-step operator inspection path.

Never defer reconciliation past the next session boundary. A deferred reconciliation makes strategy-change comparison unreliable.

## Strategy-Change Comparison Boundary

When evaluating a strategy change during a paper trading run, use the following read-only comparison protocol.

### Pre-Change Baseline Capture

Before applying any strategy change, capture and record:

1. `GET /paper/reconciliation` — full reconciliation state; `ok: true` and `mismatches: 0` required.
2. `GET /paper/account` — account snapshot (`equity`, `realized_pnl`, `unrealized_pnl`, `total_pnl`, `as_of`).
3. `GET /paper/trades` — full trade list (total count and status breakdown).
4. `GET /paper/positions` — full position list (open and closed counts).

The pre-change baseline is invalid if reconciliation is not clean (`ok: false` or `mismatches > 0`). Resolve all mismatches before proceeding.

### Post-Change Comparison

After applying a strategy change and before resuming evaluation:

1. Run the full six-step operator inspection path.
2. Confirm `GET /paper/reconciliation` returns `ok: true` and `mismatches: 0`.
3. Compare account state (`GET /paper/account`) against the pre-change baseline — any delta must be explainable by the lifecycle events that occurred between the two snapshots.
4. The comparison boundary is the reconciliation snapshot: if `ok: true` before and `ok: true` after with `mismatches: 0`, the strategy change did not corrupt canonical state.

### Prohibited Comparison Shortcuts

- Do not compare raw trade payloads across strategy versions. Use canonical entity counts and reconciliation state only.
- Do not use account equity alone as the comparison boundary. `mismatches: 0` is the primary validity signal.
- Do not skip the pre-change baseline capture. A missing baseline makes post-change comparison unverifiable.

## Review Artifact Checklist

Each bounded long-run paper operator review must produce the following artifacts, captured in the order listed:

| # | Artifact | Source endpoint | Required state |
| --- | --- | --- | --- |
| R1 | Reconciliation result | `GET /paper/reconciliation` | `ok: true`, `summary.mismatches: 0` |
| R2 | Account snapshot | `GET /paper/account` | Non-null `as_of`, valid equity equation |
| R3 | Canonical order count | `GET /trading-core/orders` | Readable, `total >= 0` |
| R4 | Canonical execution-event count | `GET /trading-core/execution-events` | Readable, `total >= 0` |
| R5 | Canonical trade count | `GET /trading-core/trades` | `total` matches `GET /paper/trades` `total` |
| R6 | Canonical position count | `GET /trading-core/positions` | `total` matches `GET /paper/positions` `total` |
| R7 | Workflow contract state | `GET /paper/workflow` | `validation.ok: true` |

All R1–R7 artifacts must be captured in the sequence listed above. R1 must be captured and confirmed clean before R2–R7 are treated as valid review evidence.

## Restart and Recovery Review

All paper portfolio and account state is persisted in the canonical SQLite execution repository. On process restart or reload:

1. The repository re-opens the existing database file (`core_orders`, `core_execution_events`, `core_trades`).
2. All derived views (account, positions, portfolio, reconciliation) are recomputed deterministically from persisted entities.
3. No in-memory state is required — the full inspection surface is reconstructable from the database alone.
4. The operator can verify state integrity after restart by running `GET /paper/reconciliation` and requiring `ok: true` with `summary.mismatches: 0`.

### Recovery Verification Steps

After any restart, before resuming long-run evaluation:

1. Run `GET /paper/reconciliation` and require `ok: true` with `summary.mismatches: 0`.
2. Compare account state (`GET /paper/account`) with the pre-restart baseline if one was captured.
3. Confirm canonical entity counts (`GET /trading-core/orders`, `GET /trading-core/execution-events`, `GET /trading-core/trades`, `GET /trading-core/positions`) are consistent with the expected pre-restart counts.
4. If any mismatch is detected, do not resume evaluation until the source of the mismatch is identified and resolved.

## Singular State Authority

The sole source of truth for paper execution state is `SqliteCanonicalExecutionRepository`. No alternative state source, in-memory cache, or legacy table is authoritative. The formal contract is defined in `src/cilly_trading/portfolio/paper_state_authority.py`.

## P53 Automated Review Operations

The manual operator steps defined above are automated by the following scripts introduced in P53:

- **Post-run reconciliation**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation` - runs after each execution cycle to validate reconciliation automatically.
- **Weekly review artifacts (R1-R7)**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review` - produces deterministic weekly review evidence bundles.
- **Restart/recovery evidence**: `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence` and `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json` - captures pre-restart baselines and post-restart verification evidence.

All automation scripts use the same canonical state authority and derivation functions as the paper inspection API. Evidence files are written to `runs/` subdirectories (excluded from version control).

The full automation contract is defined in `docs/operations/runtime/p53-automated-review-operations.md`.

## OPS-P55 Freeze Status (2026-04-03)
The runtime/operator documentation freeze separates status into validated
bounded read-only workflow checks vs pending final evidence automation.

Validated in bounded read-only scope:
- `GET /paper/workflow` returned `validation.ok: true`
- `GET /paper/reconciliation` returned `ok: true`, `summary.mismatches: 0`
- `/paper/*` and `/trading-core/*` inspection surfaces were consistent in empty
  initial state
- bounded staging deployment and localhost-only access posture were validated

Still open before any `paper-install-ready` claim:
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence`
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json`

This freeze note adds documentation clarity only and does not change runtime or
API behavior.

## Session Progress Note (2026-04-03)

For the bounded runtime status verified on 2026-04-03, including:
- validated read-only inspection of `/paper/*` and `/trading-core/*` surfaces in
  empty-state form, and
- pending P53 evidence automation steps required before any
  `paper-install-ready` claim,

see `docs/operations/runtime/staging-paper-progress-2026-04-03.md`.

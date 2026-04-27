# Paper Inspection API

This document defines the read-only paper inspection surface for portfolio-aware paper account state, paper trades, derived paper positions, reconciliation, and bounded operator workflow inspection.

## Singular State Authority

The sole source of truth for all paper portfolio and account state is the **canonical execution repository** (`SqliteCanonicalExecutionRepository`), persisted across the following tables:

- `core_orders` — canonical order entities
- `core_execution_events` — canonical execution lifecycle events
- `core_trades` — canonical trade entities

All derived views (account balance, positions, portfolio aggregation, reconciliation) are computed deterministically from these canonical entities on every read request. No alternative or competing state authority is permitted.

The formal contract is defined in `src/cilly_trading/portfolio/paper_state_authority.py`.

## Restart-Safe Persistence

Because the canonical repository is backed by SQLite, all paper execution state survives process restarts and reloads without loss. On restart the repository re-opens the existing database file and the deterministic derivation functions reproduce identical views from the persisted entities. No in-memory state is required to reconstruct paper inspection views.

## Read-Only Endpoints

All endpoints require `X-Cilly-Role: read_only` (or a higher role).

- `GET /paper/account`
- `GET /paper/workflow`
- `GET /paper/trades`
- `GET /paper/positions`
- `GET /paper/reconciliation`
- `GET /portfolio/positions`

No mutation endpoints are introduced by this surface.

## Authoritative State Ownership

Paper inspection state is authoritative only when derived from the singular canonical execution repository:

- Orders: canonical `Order` entities (`core_orders`)
- Execution lifecycle facts: canonical `ExecutionEvent` entities (`core_execution_events`)
- Trades: canonical `Trade` entities (`core_trades`)
- Positions: derived canonical `Position` entities assembled from canonical trades/orders/execution events

No `/paper/*` runtime endpoint uses legacy `trades` table payloads or any alternative state source as the source of truth. The only permitted environment-variable input is `CILLY_PAPER_ACCOUNT_STARTING_CASH`, which provides the initial cash constant and does not override any execution-derived value.

## Paper Account State

`GET /paper/account` returns one explicit bounded state payload (all monetary fields use 4-decimal precision):

- `starting_cash`
- `cash`
- `equity`
- `realized_pnl`
- `unrealized_pnl`
- `total_pnl`
- `open_positions`
- `open_trades`
- `closed_trades`
- `as_of`

Starting cash defaults to `100000` and can be overridden via `CILLY_PAPER_ACCOUNT_STARTING_CASH` (must be numeric and non-negative).

`GET /paper/account` is derived from canonical Trading Core state:

- `realized_pnl`: sum of canonical `Trade.realized_pnl` (null treated as `0`)
- `unrealized_pnl`: sum of canonical `Trade.unrealized_pnl` (null treated as `0`)
- `open_trades` / `closed_trades`: canonical `Trade.status`
- `open_positions`: derived canonical `Position.status`
- `cash`: `starting_cash + realized_pnl`
- `equity`: `cash + unrealized_pnl`
- `total_pnl`: `realized_pnl + unrealized_pnl`
- `as_of`: max non-null timestamp across canonical trade open/close timestamps

## Trading Core Alignment

- `GET /paper/trades` returns canonical `Trade` entities from Trading Core persistence.
- `GET /paper/positions` returns canonical `Position` entities derived from canonical Trading Core entities.
- Position/trade lifecycle state semantics follow the same canonical model constraints as Trading Core.
- `GET /paper/reconciliation` reads canonical orders, execution events, trades, positions, and derived paper account state from the same runtime source and reports deterministic reconciliation mismatches.

## End-to-End Inspection Path

This is the minimum operator inspection path for paper trading from order intent to account state:

1. Read workflow contract and current validation status from `GET /paper/workflow`.
2. Read order intent and final order state from `GET /trading-core/orders`.
3. Read lifecycle transitions and fills from `GET /trading-core/execution-events` (`created` -> `submitted` -> fill states).
4. Read resulting trade lifecycle from `GET /trading-core/trades`.
5. Read derived position state from `GET /trading-core/positions`.
6. Read portfolio-aware aggregation from `GET /portfolio/positions`.
7. Read paper-facing account state from `GET /paper/account`.
8. Run `GET /paper/reconciliation` and require `ok: true` with `summary.mismatches: 0`.

`GET /paper/reconciliation` fails closed for operational validation: any missing cross-reference or account equation mismatch is returned in `mismatch_items` with deterministic `code`, `entity_type`, and `entity_id` values. The reconciliation validates:

- Every `ExecutionEvent.order_id` references a known canonical `Order`.
- Every `Trade.position_id` references a known canonical `Position`.
- Every `Trade.opening_order_ids` / `closing_order_ids` reference known canonical `Order` entities.
- Every `Trade.execution_event_ids` reference known canonical `ExecutionEvent` entities.
- Every `Position.trade_ids`, `Position.order_ids`, `Position.execution_event_ids` reference known canonical entities.
- Account equations (`cash`, `equity`, `total_pnl`, `realized_pnl`, `unrealized_pnl`) match the sums derived from canonical trades.
- Account counts (`open_trades`, `closed_trades`, `open_positions`) match the canonical entity statuses.

`GET /paper/workflow` is the bounded operator contract surface that makes workflow scope, boundary, required inspection/reconciliation surfaces, validation checks, inspection counts, and deterministic reference-chain continuity explicit.

The workflow response exposes:

- `surfaces.signal_inspection` for `/signals` and `/signals/decision-surface`.
- `surfaces.canonical_inspection` for `/decision-cards` and `/trading-core/*`.
- `surfaces.portfolio_inspection` for `/portfolio/positions`.
- `surfaces.paper_inspection` for `/paper/trades`, `/paper/positions`, and `/paper/account`.
- `surfaces.reconciliation` for `/paper/reconciliation`.
- `reference_chain` for the decision evidence -> portfolio inspection -> paper execution -> reconciliation chain.
- `inspection_summary` for canonical, portfolio, paper, and reconciliation counts derived from the same canonical execution repository.

The workflow is bounded operator inspection only. It does not imply trader validation, live-trading readiness, broker readiness, or operational readiness.

## Signal-to-Portfolio-to-Paper Audit

Each `GET /decision-cards` item includes
`metadata.bounded_signal_portfolio_paper_reconciliation_audit` when rendered by
the inspection API. The audit is read-only and deterministic. It links:

- signal evidence (`signal.signal_id` or deterministic fallback ID)
- decision-card evidence (`decision_card.decision_card_id`)
- portfolio impact (`portfolio_impact.portfolio_impact_id`)
- paper order lifecycle (`paper_order.paper_order_id`, order IDs, execution event IDs)
- paper outcome (`paper_outcome.paper_trade_id`, `paper_outcome.outcome_state`)
- reconciliation (`reconciliation.status`, related mismatch codes)

The explicit paper outcome states are `missing`, `invalid`, `open`, and
`closed`. Portfolio impact is exposed before paper execution through the
portfolio impact reference and `/portfolio/positions`; it is not an execution
approval or mutation endpoint.

This audit does not imply auto-trading, broker execution, live-trading
readiness, paper profitability, trader validation, or operational readiness.

## Deterministic Ordering

- Paper trades are ordered by `opened_at`, then `trade_id`.
- Paper positions are ordered by `opened_at`, then `position_id`.
- Filtering and pagination preserve stable deterministic ordering.

## Query Parameters

### `GET /paper/trades`

- Optional filters: `strategy_id`, `symbol`, `position_id`, `trade_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

### `GET /paper/positions`

- Optional filters: `strategy_id`, `symbol`, `position_id`
- Pagination: `limit` (`1..500`), `offset` (`>=0`)

## Response Shape

### `GET /paper/trades` and `GET /paper/positions`

```json
{
  "items": [],
  "limit": 50,
  "offset": 0,
  "total": 0
}
```

### `GET /paper/reconciliation`

```json
{
  "ok": true,
  "summary": {
    "orders": 0,
    "execution_events": 0,
    "trades": 0,
    "positions": 0,
    "open_trades": 0,
    "closed_trades": 0,
    "open_positions": 0,
    "mismatches": 0
  },
  "account": {
    "starting_cash": "100000",
    "cash": "100000",
    "equity": "100000",
    "realized_pnl": "0",
    "unrealized_pnl": "0",
    "total_pnl": "0",
    "open_positions": 0,
    "open_trades": 0,
    "closed_trades": 0,
    "as_of": null
  },
  "mismatch_items": []
}
```

## Long-Run Evaluation and Review Workflow

The full bounded long-run paper operator review workflow - including evaluation cadence guidance, review artifact checklist (R1-R8 / R1–R8), strategy-change comparison boundary, and restart and recovery verification steps - is defined in:

```
docs/operations/runtime/phase-44-paper-operator-workflow.md
```

This workflow is read-only and review-oriented. It does not introduce mutation endpoints or live-trading behavior.

## Automated Reconciliation and Review

Post-run reconciliation, weekly review artifact generation, and restart/recovery evidence capture are automated by the P53 scripts:

- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/run_post_run_reconciliation.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/reconciliation` - automated post-run reconciliation with evidence output.
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/generate_weekly_review.py --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/weekly-review` - deterministic bounded weekly review bundle generation.
- `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase pre-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence` and `docker compose --env-file .env -f docker/staging/docker-compose.staging.yml exec api python /app/scripts/capture_restart_evidence.py --phase post-restart --db-path /data/db/cilly_trading.db --evidence-dir /data/artifacts/restart-evidence --baseline /data/artifacts/restart-evidence/pre-restart-pass-YYYYMMDDTHHMMSSZ.json` - restart/recovery evidence with baseline comparison.

All automation uses the same canonical state authority and derivation functions as the endpoints documented above. The full automation contract is in `docs/operations/runtime/p53-automated-review-operations.md`.

## Deterministic Evidence

- Integration coverage validates this path with deterministic lifecycle events in:
  - `tests/test_api_paper_inspection_read.py::test_paper_reconciliation_matches_deterministic_lifecycle_outputs`
  - `tests/test_api_paper_inspection_read.py::test_paper_reconciliation_detects_missing_execution_event_reference`
- Reproducible focused test command: `.\.venv\Scripts\python -m pytest tests/test_api_paper_inspection_read.py -q`
- Reproducible full-suite test command: `.\.venv\Scripts\python -m pytest`

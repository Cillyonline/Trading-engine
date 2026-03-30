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

## Restart and Reload Behavior

All paper portfolio and account state is persisted in the canonical SQLite execution repository. On process restart or reload:

1. The repository re-opens the existing database file (`core_orders`, `core_execution_events`, `core_trades`).
2. All derived views (account, positions, portfolio, reconciliation) are recomputed deterministically from persisted entities.
3. No in-memory state is required — the full inspection surface is reconstructable from the database alone.
4. The operator can verify state integrity after restart by running `GET /paper/reconciliation` and requiring `ok: true` with `summary.mismatches: 0`.

## Singular State Authority

The sole source of truth for paper execution state is `SqliteCanonicalExecutionRepository`. No alternative state source, in-memory cache, or legacy table is authoritative. The formal contract is defined in `src/cilly_trading/portfolio/paper_state_authority.py`.

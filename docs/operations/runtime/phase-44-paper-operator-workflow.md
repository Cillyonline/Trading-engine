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
- `GET /paper/trades`
- `GET /paper/positions`
- `GET /paper/account`
- `GET /paper/reconciliation`

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

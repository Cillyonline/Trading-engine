# Phase 43 Portfolio Inspection Contract

This document defines the bounded Phase 43 contract for portfolio/paper inspection surfaces:

- `GET /portfolio/positions`
- `GET /paper/account`
- `GET /paper/reconciliation`

## Scope

- The covered endpoints are read-only inspection surfaces.
- Covered state is derived from canonical simulation artifacts persisted by the trading-core execution repository.
- Covered endpoints do not execute orders, mutate portfolio state, or expose live broker state.

## Source Of Truth

- `src/api/services/paper_inspection_service.py`
- `build_bounded_paper_simulation_state(...)`

The source of truth is one bounded in-memory simulation snapshot built from canonical repository reads (`list_orders`, `list_execution_events`, `list_trades`) and reused for covered inspection derivations.

## Derivation Rules

- Closed exposure (`remaining_quantity <= 0`) is excluded.
- Positions are aggregated by `(strategy_id, symbol)`.
- `size` is the sum of remaining quantities in the aggregate group.
- `average_price` is a weighted entry average over remaining quantity.
- `unrealized_pnl` is the sum of unrealized PnL values (missing values treated as `0`).
- Output ordering is deterministic: `symbol`, `strategy_id`, `size`, `average_price`, `unrealized_pnl`.
- Paper account and reconciliation summaries are derived from the same bounded snapshot used for portfolio inspection output.

## Explicit Non-Claims

- No live broker portfolio sync.
- No mutation workflow for paper-trading state.
- No execution-capability claim beyond deterministic inspection of bounded internal artifacts.

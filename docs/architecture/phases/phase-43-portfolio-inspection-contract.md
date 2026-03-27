# Phase 43 Portfolio Inspection Contract

This document defines the bounded Phase 43 contract for `GET /portfolio/positions`.

## Scope

- The endpoint is a read-only inspection surface.
- Position state is derived from canonical simulation artifacts persisted by the trading-core execution repository.
- The endpoint does not execute orders, mutate portfolio state, or expose live broker state.

## Source Of Truth

- `src/cilly_trading/engine/portfolio/state.py`
- `load_portfolio_state_from_simulation_repository(...)`

The source of truth is the canonical trade stream (`list_trades`) from the internal execution repository. Open exposure is derived from `quantity_opened - quantity_closed`.

## Derivation Rules

- Closed exposure (`remaining_quantity <= 0`) is excluded.
- Positions are aggregated by `(strategy_id, symbol)`.
- `size` is the sum of remaining quantities in the aggregate group.
- `average_price` is a weighted entry average over remaining quantity.
- `unrealized_pnl` is the sum of unrealized PnL values (missing values treated as `0`).
- Output ordering is deterministic: `symbol`, `strategy_id`, `size`, `average_price`, `unrealized_pnl`.

## Explicit Non-Claims

- No live broker portfolio sync.
- No mutation workflow for paper-trading state.
- No execution-capability claim beyond deterministic inspection of bounded internal artifacts.

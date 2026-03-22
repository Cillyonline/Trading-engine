# Backtest Execution Contract (BT-P42B)

## Goal

Define one explicit contract for deterministic backtest execution so runs are reproducible and operational assumptions are visible in the artifact.

## Contract Boundary

The backtest contract is bounded to:

- run configuration validation
- signal-to-order translation
- deterministic order execution assumptions
- reproducibility metadata written into the run artifact

Out of scope:

- portfolio optimization
- paper-trading runtime
- broker integrations
- UI workflows

## Run Configuration Model

Backtests use `BacktestRunContract` with explicit sections:

- `contract_version`: currently `1.0.0`
- `signal_translation`:
  - `signal_collection_field`
  - `signal_id_field`
  - `action_field`
  - `quantity_field`
  - `symbol_field`
  - `action_to_side`
- `execution_assumptions`:
  - `fill_model` = `deterministic_market`
  - `fill_timing` = `next_snapshot` or `same_snapshot`
  - `price_source` = `open_then_price`
  - `slippage_bps` (integer, `>= 0`)
  - `commission_per_order` (decimal, `>= 0`)
  - `partial_fills_allowed` = `false`
- `reproducibility_metadata`:
  - `run_id`
  - `strategy_name`
  - `strategy_params`
  - `engine_name`
  - `engine_version`

## Signal -> Order -> Fill Semantics

Signal translation is deterministic:

1. Snapshots are sorted by `timestamp` / `snapshot_key`, then by `id`.
2. Signals in each snapshot are sorted by `signal_id`, then `symbol`.
3. Each translated order is market-only and receives a deterministic `order_id`.

Execution assumptions are explicit and testable:

- no partial fills
- fill price source is `open`, then fallback `price`
- side-aware slippage:
  - BUY: `price * (1 + bps/10000)`
  - SELL: `price * (1 - bps/10000)`
- fixed commission per filled order
- deterministic decimal quantization

## Reproducibility

For identical snapshots and identical run contract:

- translated orders are identical
- fills and resulting positions are identical
- `backtest-result.json` bytes and hash remain identical

The run artifact now surfaces both the explicit `run_config` contract and realized `orders` / `fills` / `positions`.


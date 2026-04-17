# Deterministic Order Execution Model

## Scope

This document defines the deterministic market-order execution model for backtesting.
The model is intentionally fixed and reproducible for identical inputs.
It is a technical replay model only and does not represent live broker execution.

## 1) Market-order execution semantics

Fill timing mode is configurable as `next_snapshot` or `same_snapshot`.

- For `next_snapshot`, an order created at snapshot `t` is not fillable at snapshot `t`; earliest fill is snapshot `t+1`.
- For `same_snapshot`, an order created at snapshot `t` is fillable at snapshot `t`.
- No partial fills are allowed. If an order is eligible and snapshot price data exists, the full order quantity is filled deterministically.

## 2) Deterministic fill price rule

For each fill snapshot:

1. If `open` is present, base fill price is `snapshot.open`.
2. Else, base fill price is `snapshot.price`.
3. If neither field exists, execution raises a deterministic error.

Price source is fixed to `open_then_price`.

## 3) Deterministic slippage model

`slippage_bps` is a bounded integer config value.

- BUY: `fill_price = base_price * (1 + slippage_bps / 10_000)`
- SELL: `fill_price = base_price * (1 - slippage_bps / 10_000)`

## 4) Deterministic commission model

Commission model is fixed per filled order (`commission_per_order`).

- Every filled order uses the same fixed commission amount from config.
- Formula: `commission = commission_per_order`

## 5) Position lifecycle and transitions

Position fields:

- `quantity`
- `avg_price`

Transitions:

- BUY increases quantity.
- BUY average price updates by weighted average:
  - `new_avg = ((old_avg * old_qty) + (fill_price * buy_qty)) / (old_qty + buy_qty)`
- SELL reduces quantity.
- SELL keeps `avg_price` unchanged while quantity remains positive.
- When quantity reaches zero, `avg_price` is reset to `0`.
- SELL quantity larger than current quantity raises a deterministic error.

## 6) Rounding and numeric determinism

All calculations use `Decimal` with explicit quantization (`ROUND_HALF_UP`):

- Prices quantized to `price_scale` (default `0.00000001`).
- Commission quantized to `money_scale` (default `0.01`).
- Quantities quantized to `quantity_scale` (default `0.00000001`).

Rounding is applied at deterministic steps:

1. Base price extraction.
2. Slippage-adjusted fill price.
3. Commission amount.
4. Position quantity and average price updates.

## 7) Deterministic processing order

Orders are processed in a total deterministic order using:

1. `created_snapshot_key` (ascending)
2. `sequence` (ascending)
3. `id` (ascending)

Snapshot lookup is field-address based (`open`, then `price`) and does not rely on dictionary iteration order.

## 8) Unmodeled realism boundary

The deterministic execution model is intentionally narrower than real execution.

- Market hours and exchange session rules are not modeled.
- Broker routing, rejects, cancels, and venue-specific behavior are not modeled.
- Liquidity, queue position, fill probability, latency, and market impact are not modeled.
- This model is non-live and non-broker by design.

This execution model does not support live-trading readiness claims.
This implementation improves technical realism only and does not constitute trader validation.

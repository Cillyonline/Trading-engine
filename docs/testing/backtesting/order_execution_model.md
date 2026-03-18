# Deterministic Order Execution Model

## Scope

This document defines the deterministic market order execution model for backtesting.
The model is intentionally fixed and reproducible for identical inputs.

## 1) Market order execution semantics

Fill timing mode is **`next_snapshot`**.

- An order created at snapshot `t` is **not** fillable at snapshot `t`.
- The earliest fill opportunity is snapshot `t+1`.
- This enforces no-lookahead behavior.
- No partial fills are allowed. If an order is eligible for a snapshot and snapshot price data exists, the full order quantity is filled deterministically.

## 2) Deterministic fill price rule

For each fill snapshot:

1. If `open` is present, base fill price is `snapshot.open`.
2. Else, base fill price is `snapshot.price`.
3. If neither field exists, execution raises a deterministic error.

## 3) Deterministic slippage model

`slippage_bps` is a fixed integer config value.

- BUY: `fill_price = base_price * (1 + slippage_bps / 10_000)`
- SELL: `fill_price = base_price * (1 - slippage_bps / 10_000)`

## 4) Deterministic commission model

Commission model is fixed **per order** (`commission_per_order`).

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

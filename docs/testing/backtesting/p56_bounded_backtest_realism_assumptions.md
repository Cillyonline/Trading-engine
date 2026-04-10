# P56-BT Bounded Backtest Realism Assumptions

## Goal
Document and validate currently implemented realism-sensitive assumptions in the deterministic backtest path without introducing a new backtesting subsystem.

## Scope Boundary
This contract covers only the current deterministic backtest implementation.
It does not define live-trading behavior, broker behavior, or a market-microstructure simulator.

## Current Implemented Assumptions (Validated)

### Fill assumptions
- Fill model is fixed to `deterministic_market`.
- Fill timing is configurable between `next_snapshot` and `same_snapshot`.
- Price source is fixed to `open_then_price`:
  - use `open` when present
  - otherwise use `price`
- Partial fills are not allowed (`partial_fills_allowed=false`).

### Cost assumptions
- Slippage model is fixed basis points by side:
  - BUY adjusts price upward
  - SELL adjusts price downward
- Commission model is fixed per filled order (`commission_per_order`).

### Execution assumptions
- Signals are translated to deterministic market orders with deterministic ordering.
- Snapshot processing and order processing are deterministic for identical inputs.

## Explicit Realism Gaps (Not Modeled)
- Market hours/session calendars, halts, auctions, and after-hours restrictions.
- Broker routing, venue selection, rejects, cancels, and broker-specific policies.
- Order-book depth, queue position, latency, fill probability, and market impact.

## Evidence Interpretation Boundary
- Backtest output is bounded evidence for deterministic replay under declared assumptions.
- It supports controlled review of what the model did on supplied snapshots under fixed cost/fill rules.

Unsupported claims:
- live-trading readiness or approval
- broker execution realism
- market-hours compliance realism
- liquidity or market microstructure realism
- future profitability or out-of-sample robustness

## Validation Evidence (Current Repository)
- Engine contract tests validate assumptions and deterministic behavior:
  - `tests/cilly_trading/engine/test_backtest_execution_contract.py`
  - `tests/cilly_trading/engine/test_order_execution_model.py`
  - `tests/cilly_trading/engine/test_backtest_realism_assumptions.py`
- Documentation contract tests enforce bounded wording:
  - `tests/test_backtest_evidence_docs.py`
  - `tests/test_p56_bt_backtest_realism_docs.py`

## Status Wording
Classification: technically good, traderically weak.

Rationale:
- technically good: deterministic and test-validated for implemented assumptions
- traderically weak: key market-realism dimensions are intentionally unmodeled

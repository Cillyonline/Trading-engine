# P56-BT Bounded Backtest Realism Assumptions

## Goal
Document and validate currently implemented realism-sensitive assumptions in the deterministic
backtest path, including a bounded deterministic realism sensitivity matrix, without introducing a
new backtesting subsystem.

## Scope Boundary
This contract covers only the current deterministic backtest implementation.
It does not define live-trading behavior, broker behavior, or a market-microstructure simulator.
Trader validation status for this implementation remains `trader_validation_not_started`.

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

## Deterministic Realism Sensitivity Matrix (Bounded)
Backtest evidence now includes one fixed bounded realism-profile matrix computed from the same
snapshot inputs:

- `configured_baseline`: run-config assumptions exactly as declared in `run_config`.
- `cost_free_reference`: same fill timing as baseline with `slippage_bps=0` and `commission_per_order=0`.
- `bounded_cost_stress`: same fill timing with deterministic bounded stress costs
  (`slippage_bps>=25`, `commission_per_order>=2.50`, capped by existing assumption limits).

For each profile the evidence persists:
- profile assumptions
- profile cost-aware summary
- profile cost-aware metrics
- `delta_vs_baseline` for summary and metrics fields

The matrix is deterministic for identical inputs and assumption values.

## Explicit Realism Gaps (Not Modeled)
- Market hours/session calendars, halts, auctions, and after-hours restrictions.
- Broker routing, venue selection, rejects, cancels, and broker-specific policies.
- Order-book depth, queue position, latency, fill probability, and market impact.

## Evidence Interpretation Boundary
- Backtest output is bounded evidence for deterministic replay under declared assumptions.
- It supports controlled review of what the model did on supplied snapshots under fixed cost/fill rules.
- This implementation improves technical realism only; it does not validate trader readiness, live
  tradability, or execution quality in production markets.
- Sensitivity outputs are technical-only comparison evidence and must not be interpreted as live
  readiness, broker-readiness, or trader validation.

Unsupported claims:
- live-trading readiness or approval
- broker execution realism
- market-hours compliance realism
- liquidity or market microstructure realism
- trader validation or trader approval
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
- trader validation status remains `trader_validation_not_started`

# Phase 43 Bounded Portfolio Simulation Acceptance Contract

This document formalizes the bounded acceptance contract for currently implemented
Phase 43 portfolio-simulation primitives, without expanding into broader product
workflow scope.

## Contract Intent

Phase 43 remains **Partially Implemented**.

This contract defines only the deterministic portfolio-simulation primitives that
are currently implemented and test-verified in repository code. It does not claim
paper-trading readiness, live-capital readiness, or broader product workflow
completeness.

## Bounded Acceptance Surface

### Capital Allocation Primitive

- Authority module:
  - `src/cilly_trading/portfolio_framework/capital_allocation_policy.py`
- Contract operation:
  - `assess_capital_allocation(state, rules)`
- Accepted behavior:
  - deterministic global-cap enforcement
  - deterministic strategy-cap enforcement
  - deterministic reason ordering for violations

### Exposure Handling Primitive

- Authority module:
  - `src/cilly_trading/portfolio_framework/exposure_aggregator.py`
- Contract operation:
  - `aggregate_portfolio_exposure(state)`
- Accepted behavior:
  - deterministic strategy/symbol/position exposure aggregation
  - explicit gross/net exposure math
  - explicit zero-equity behavior (`inf`, `-inf`, or `0.0` as implemented)

### Multi-Position Consistency Primitive

- Authority modules:
  - `src/cilly_trading/portfolio_framework/capital_allocation_policy.py`
  - `src/api/services/paper_inspection_service.py`
- Contract operations:
  - `run_portfolio_decision_pipeline(...)`
  - `build_portfolio_positions_from_trades(...)`
  - `build_bounded_paper_simulation_state(...)`
- Accepted behavior:
  - deterministic ranked-signal decisions across competing positions
  - state mutation only for approved outcomes in decision pipeline
  - deterministic `(strategy_id, symbol)` aggregation for inspection positions
  - bounded runtime snapshot validation via `validate_bounded_paper_simulation_state(...)`

## Inspection Surfaces Covered by the Same Bounded State

- `GET /portfolio/positions`
- `GET /paper/account`
- `GET /paper/reconciliation`

Covered endpoints are read-only and derived from one bounded canonical snapshot.
They do not execute orders or mutate portfolio state.

## Implemented Primitives vs Missing Broader Workflow

### Implemented In Scope

- deterministic capital-allocation assessment
- deterministic exposure aggregation and guardrail evaluation inputs
- deterministic ranked portfolio decision pipeline semantics
- deterministic portfolio/paper inspection derivation from canonical execution entities
- bounded runtime validation of simulation snapshot integrity

### Not Implemented In This Phase Scope

- broad portfolio product workflow expansion
- live-capital claims or readiness
- broker integration or broker-state synchronization workflow
- broad execution-system redesign
- complete paper-trading operational lifecycle as a Phase 43 claim

## Explicit Non-Claims

- This contract does **not** upgrade Phase 43 from partial maturity.
- Passing this contract does **not** imply Phase 44 paper readiness by itself.
- Passing this contract does **not** imply any live-trading or broker-readiness claim.

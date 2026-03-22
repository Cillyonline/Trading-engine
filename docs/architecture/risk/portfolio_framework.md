# Portfolio Framework – Architectural Boundary Declaration

## 1. Purpose

The portfolio framework is the deterministic aggregation and capital allocation boundary for portfolio-level controls.

Its purpose is to:
- Aggregate exposures across strategies in a deterministic manner.
- Enforce portfolio-level capital allocation constraints.
- Provide predictable, repeatable outcomes for identical inputs.

## 2. Scope

The portfolio framework scope is explicitly limited to:

- **Exposure aggregation**
  - Deterministic aggregation of exposure inputs across participating strategies and positions.
- **Capital allocation enforcement**
  - Deterministic enforcement of cross-strategy capital limits, caps, and allocation constraints.
- **Deterministic behavior**
  - All outputs are fully determined by provided inputs and configuration.
- **Pure-function constraint**
  - Computation is implemented as pure transformations with no side effects.

## 3. Non-Goals (Out of Scope)

The following areas are explicitly out of scope for the portfolio framework:

- Trading logic
- Broker integration
- Optimization theory
- Execution integration
- Live rebalancing
- RiskEvaluator override

## 4. Architectural Boundary

The portfolio framework boundary is defined as follows:

- The portfolio framework is a standalone module.
- It operates above request-level risk enforcement.
- It does not call execution or broker layers.
- It must remain import-safe and side-effect free.

## 5. Import Direction Rules

Import direction is constrained by the following rules:

- `engine.portfolio_framework` **MAY** import:
  - Python standard library (`stdlib`)
  - `engine.portfolio_framework.*`

- `engine.portfolio_framework` **MUST NOT** import:
  - `engine.execution`
  - `engine.orchestrator`
  - `engine.broker`
  - `src.*`

- Higher layers **MAY** depend on `engine.portfolio_framework`.

## 6. Relationship to Risk Framework

The relationship between frameworks is defined as:

- The risk framework enforces per-request constraints.
- The portfolio framework enforces cross-strategy capital caps.
- No bidirectional dependency is permitted.

## 7. Determinism Guarantees

The portfolio framework must satisfy all determinism guarantees below:

- No global state.
- No IO.
- No time-dependence.
- No randomness.
- Stable ordering guarantees.
- Equal input → equal output.

## 8. Guardrails

The following guardrails are mandatory:

- Pure functions only.
- Immutable contracts.
- Coverage expectations are defined and maintained for framework behavior.
- Enforcement must be test-verified.

## 9. RISK-P43 Bounded Allocation and Prioritization Model

Issue `#729` defines a single bounded model for portfolio allocation and signal prioritization when capital is constrained.

### 9.1 Inputs

- `PortfolioState`
  - Current account equity and open positions.
- `CapitalAllocationRules`
  - Global portfolio cap as percent of equity.
  - Per-strategy cap and deterministic strategy score.
- `SignalAllocationInput[]`
  - `signal_id`, `strategy_id`, `symbol`, `side`, `priority_score`, `requested_notional`.
  - Optional `position_size_cap_notional` as a bounded per-signal sizing hook.
  - Optional `deterministic_tie_breaker` for explicit final ordering key.
- Optional `max_selected_signals`
  - Bounded selected-position count hook.

### 9.2 Outputs

- `SignalAllocationPlan`
  - Deterministic `decisions` for every candidate.
  - `selected_signal_ids` in deterministic processing order.
  - `remaining_global_cap_notional` after all decisions.
- `SignalAllocationDecision` (per candidate)
  - Contains requested and allocated notional, status (`accepted`, `partially_allocated`, `rejected`), rejection reason, and remaining capacities after the decision.

### 9.3 Prioritization and Tie-Breaking Rules

Candidates are sorted with a stable deterministic key:

1. `priority_score` descending
2. `strategy_id` ascending
3. `symbol` ascending
4. `signal_id` ascending
5. `deterministic_tie_breaker` ascending

This ordering is reproducible and independent of input tuple order.

### 9.4 Bounded Sizing Rule

Each candidate receives:

`allocated_notional = min(requested_notional, global_remaining, strategy_remaining, optional position_size_cap_notional)`

Where:
- `global_remaining` is derived from global cap minus current absolute notional usage.
- `strategy_remaining` is derived from strategy effective cap minus current strategy absolute notional.

If the bounded result is:
- equal to requested: `accepted`
- greater than 0 but less than requested: `partially_allocated`
- 0: `rejected` with deterministic reason

If `max_selected_signals` is reached, further signals are rejected with `max_selected_signals_reached`.

### 9.5 Non-Goals Kept Intact

- No optimizer research or objective-function search.
- No execution routing or brokerage integration.
- No rebalancing engine expansion.

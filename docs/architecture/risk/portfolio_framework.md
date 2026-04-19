# Portfolio Framework - Architectural Boundary Declaration

## 1. Purpose

The portfolio framework is the deterministic aggregation and allocation boundary for portfolio-level controls.

Its purpose is to:
- Aggregate exposures across strategies in a deterministic manner.
- Enforce portfolio-level capital allocation constraints.
- Prioritize competing signals and allocate bounded capital deterministically.
- Provide predictable, repeatable outcomes for identical inputs.

## 2. Scope

The portfolio framework scope is explicitly limited to:

- **Exposure aggregation**
  - Deterministic aggregation of exposure inputs across participating strategies and positions.
- **Capital allocation enforcement**
  - Deterministic enforcement of cross-strategy capital limits, caps, and allocation constraints.
- **Signal prioritization and bounded allocation**
  - Deterministic ordering and constrained-capital assignment for competing opportunities.
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
- Risk evaluator override

## 4. Architectural Boundary

The portfolio framework boundary is defined as follows:

- The portfolio framework is a standalone module.
- It operates above request-level risk enforcement.
- It does not call execution or broker layers.
- It must remain import-safe and side-effect free.

## 5. Import Direction Rules

Import direction is constrained by the following rules:

- `cilly_trading.portfolio_framework` MAY import:
  - Python standard library
  - `cilly_trading.portfolio_framework.*`

- `cilly_trading.portfolio_framework` MUST NOT import:
  - `cilly_trading.execution`
  - `cilly_trading.orchestrator`
  - `cilly_trading.broker`

- Higher layers MAY depend on `cilly_trading.portfolio_framework`.

## 6. Relationship to Risk Framework

The relationship between frameworks is defined as:

- The risk framework enforces per-request constraints.
- The portfolio framework enforces cross-strategy capital caps and constrained-capital prioritization.
- No bidirectional dependency is permitted.

## 7. Determinism Guarantees

The portfolio framework must satisfy all determinism guarantees below:

- No global state.
- No IO.
- No time-dependence.
- No randomness.
- Stable ordering guarantees.
- Equal input -> equal output.

## 8. Guardrails

The following guardrails are mandatory:

- Pure functions only.
- Immutable contracts.
- Coverage expectations are defined and maintained for framework behavior.
- Enforcement must be test-verified.

## 9. Consolidated Authority Model (Issue #729)

Issue #729 is implemented in one authority module:

- `src/cilly_trading/portfolio_framework/capital_allocation_policy.py`

No parallel public allocation/prioritization contract is exported for this issue scope.

### 9.1 Inputs

- Candidate signals (`PrioritizedAllocationSignal`):
  - `signal_id`
  - `strategy_id`
  - `symbol`
  - `priority_score`
  - `requested_notional`
  - `signal_timestamp`
  - optional `max_position_notional`
- Allocation configuration (`PrioritizedAllocationConfig`):
  - `available_capital_notional`
  - `max_positions`
  - `default_position_cap_notional`
  - optional `min_allocation_notional`
- Optional bounded position sizing hook:
  - `bounded_position_sizing_hook(signal, proposed_notional) -> float`

### 9.2 Prioritization and Tie-Break Rules

Competing signals are sorted deterministically with this precedence:

1. `priority_score` descending
2. `signal_timestamp` ascending
3. `strategy_id` ascending
4. `symbol` ascending
5. `signal_id` ascending

### 9.3 Constrained-Capital Allocation Rules

Signals are processed in rank order and allocated sequentially:

- Requested notional is bounded by:
  - `max(requested_notional, 0)`
  - and minimum of `default_position_cap_notional` and optional `max_position_notional`
- Allocation is bounded by remaining capital.
- New accepts stop when:
  - capital is exhausted, or
  - `max_positions` is reached.
- Signals below `min_allocation_notional` are rejected deterministically.

### 9.4 Outputs

The model returns (`PrioritizedAllocationResult`):

- Ordered per-signal decisions (`PrioritizedAllocationDecision`) with:
  - `priority_rank`
  - deterministic `tie_break_key`
  - `requested_notional`
  - `bounded_requested_notional`
  - `allocated_notional`
  - `accepted`
  - deterministic `rejection_reason` when not accepted
- `accepted_signal_ids` in deterministic rank order
- `total_allocated_notional`
- `remaining_capital_notional`

### 9.5 Test Coverage Expectations

Coverage includes:

- prioritization tests
- constrained-capital tests
- deterministic ordering and tie-break tests
- regression tests

## 10. Portfolio Guardrail Model (Issue #730)

Portfolio-level aggregate risk guardrails are enforced with a deterministic pure-function policy in:

- `src/cilly_trading/portfolio_framework/guardrails.py`

### 10.1 Guardrail Inputs

- `PortfolioState` (immutable positions + account equity)
- `PortfolioGuardrailLimits` with explicit bounded limits:
  - `max_gross_exposure_pct`
  - `max_abs_net_exposure_pct`
  - `max_offset_exposure_pct`
  - `max_strategy_concentration_pct`
  - `max_symbol_concentration_pct`
  - `max_position_concentration_pct`

### 10.2 Deterministic Exposure Guardrails

- Gross exposure guardrail: `gross_exposure_pct <= max_gross_exposure_pct`
- Absolute net exposure guardrail: `abs(net_exposure_pct) <= max_abs_net_exposure_pct`
- Offsetting/conflicting aggregate risk guardrail:
  - `offset_exposure_pct = gross_exposure_pct - abs(net_exposure_pct)`
  - `offset_exposure_pct <= max_offset_exposure_pct`

The offset guardrail intentionally captures portfolios where gross risk is high but net appears small because exposures offset each other.

### 10.3 Deterministic Concentration Guardrails

Concentration is measured as share of total portfolio gross notional:

- Strategy concentration: `strategy_absolute_notional / total_absolute_notional`
- Symbol concentration: `symbol_absolute_notional / total_absolute_notional`
- Position concentration: `position_absolute_notional / total_absolute_notional`

Guardrails are enforced against the observed maxima for each concentration dimension.

Zero-gross portfolios are explicitly bounded: concentration ratios are defined as `0.0` when denominator is zero.

### 10.4 Assessment Output

`PortfolioGuardrailAssessment` returns:

- approval status (`approved`)
- deterministic ordered violation reasons (`reasons`)
- the underlying deterministic exposure summary (`exposure_summary`)
- derived aggregate metrics (`absolute_net_exposure_pct`, `offset_exposure_pct`)
- observed concentration maxima for strategy/symbol/position

### 10.5 Bounded Scope

This model is intentionally bounded and reusable:

- no correlation-aware risk math
- no broker/live enforcement
- no optimization/re-ranking logic
- pure deterministic transformations suitable for later simulation and execution phases

## 11. Canonical Portfolio Decision Pipeline (Issue #759)

Issue #759 closes the portfolio decision path in one canonical pure-function sequence:

- `src/cilly_trading/portfolio_framework/capital_allocation_policy.py`
- `run_portfolio_decision_pipeline(...)`

The covered path is:

1. Ranked signal input is sorted with the existing deterministic prioritization rules.
2. An explicit `PortfolioDecisionIntent` is created for each ranked signal.
3. If no valid allocation intent can be formed, the signal ends with outcome `rejected`.
4. If an allocation intent exists, a proposed portfolio state is built from that intent.
5. The proposed state is evaluated through both:
   - `assess_capital_allocation(...)`
   - `assess_portfolio_guardrails(...)`
6. Only if both checks approve does the signal end with outcome `approved` and mutate the working portfolio state.
7. If allocation intent exists but either enforcement layer fails, the signal ends with outcome `constraint_hit`, the reasons remain inspectable, and the working portfolio state is unchanged.

### 11.1 Outcome Semantics

`PortfolioDecisionRecord` exposes one explicit final outcome per signal:

- `approved`
- `rejected`
- `constraint_hit`

The record also carries:

- the ranked allocation intent
- any proposed portfolio state used for exposure approval
- the capital-allocation assessment
- the portfolio-guardrail assessment
- deterministic ordered outcome reasons
- `primary_constraint` for the first blocking reason in deterministic order
- `constraint_categories` derived deterministically from the blocking reason set:
  - `capacity`
  - `allocation`
  - `exposure`
  - `concentration`
  - `sizing`

This removes the ambiguous partial path where allocation and exposure enforcement could be reasoned about separately instead of through one inspectable decision sequence.

### 11.2 Competing-Signal Capacity Semantics

When signals compete for constrained portfolio capacity, the pipeline remains strictly rank-ordered and inspectable:

1. Higher-priority approved signals consume capital and position slots first.
2. Lower-priority signals never displace earlier approvals.
3. A capacity rejection is emitted explicitly with:
   - `primary_constraint` of `capital_exhausted` or `position_limit_reached`
   - `constraint_categories=("capacity",)`
   - `intent.higher_priority_approved_signal_ids` listing the approved signals that consumed capacity earlier in the same run

This keeps constrained-capacity behavior deterministic and operator-inspectable without introducing optimization or trader-readiness claims beyond the verified decision semantics.

## 12. Deterministic Trade-Level Risk Allocation (Issue #981)

For bounded paper/simulation entry, deterministic trade-level notional sizing is
computed from:

- `account_equity`
- `max_risk_per_trade_pct`
- bounded trade-risk input (`trade_risk_pct`)

The sizing contract is fail-closed for missing or invalid inputs and emits
stable machine-readable reason codes for equivalent inputs. Portfolio-level
enforcement in the same decision path blocks candidates that would exceed:

- max risk per trade
- max total portfolio exposure
- max strategy exposure
- max symbol exposure
- max concurrent positions

Sizing and cap-evaluation inputs are exposed in non-UI decision artifacts for
deterministic inspection.

Implementation scope note: this issue provides technical implementation
evidence only. It does not imply trader validation, trader-approved thresholds,
live readiness, or broker readiness.

## 13. Professional Non-Live Evaluation Contract (Issue #993)

Portfolio enforcement emits structured cap/boundary violation evidence rows
through
the canonical non-live evaluation contract:

- `src/cilly_trading/non_live_evaluation_contract.py`
- `CapitalAllocationAssessment.policy_evidence`
- `PortfolioGuardrailAssessment.policy_evidence`
- `PortfolioDecisionRecord.policy_evidence`

This aligns strategy/symbol/portfolio cap and boundary outcomes with one
reviewable evidence model while preserving deterministic non-live behavior.

Portfolio pipeline outcomes are `approved`, `rejected`, or `constraint_hit`.
Evidence rows are emitted only for violated cap/boundary outcomes (for example,
`constraint_hit` outcomes from allocation/guardrail enforcement). Fully
approved portfolio outcomes carry an empty evidence tuple.

Canonical contract reference:

- `docs/architecture/risk/non_live_evaluation_contract.md`

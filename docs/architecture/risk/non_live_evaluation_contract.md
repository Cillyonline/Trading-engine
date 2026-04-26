# Professional Non-Live Risk and Exposure Evaluation Contract

## Purpose

Define one deterministic, reviewable contract for non-live risk/exposure
evaluation evidence across:

- trade-level risk checks
- symbol-level exposure checks
- strategy-level exposure checks
- portfolio-level cap and guardrail checks
- risk gate decision emission
- paper execution worker outcomes
- inspection/read normalization surfaces

This contract hardens repository direction from:

- `docs/governance/professional-trading-capability-target.md`

## Scope and Boundary

This contract is technical evidence only.

In scope:

- deterministic reject/cap/boundary semantics
- explicit policy evidence rows emitted by evaluators
- priority/ordering behavior for conflicting policy outcomes

Out of scope:

- live trading enablement
- broker execution integration
- external portfolio optimization subsystems

## Canonical Evidence Model

Module:

- `src/cilly_trading/non_live_evaluation_contract.py`

Evidence row:

- `NonLiveEvaluationEvidence`

Mandatory fields:

- `decision` (`approve` or `reject`)
- `semantic` (`cap` or `boundary`)
- `scope` (`trade`, `symbol`, `strategy`, `portfolio`, `runtime`)
- `rule_code`
- `reason_code`
- `observed_value`
- `limit_value`

Canonical risk rejection reason-code vocabulary (normalized):

- `rejected:risk_framework_kill_switch_enabled`
- `rejected:risk_framework_stop_loss_evidence_missing`
- `rejected:risk_framework_stop_loss_evidence_invalid`
- `rejected:risk_framework_position_size_exceeds_stop_loss_budget`
- `rejected:risk_framework_max_trade_risk_exceeded`
- `rejected:risk_framework_strategy_risk_budget_exceeded`
- `rejected:risk_framework_symbol_risk_budget_exceeded`
- `rejected:risk_framework_portfolio_risk_budget_exceeded`
- `rejected:risk_framework_max_position_size_exceeded`
- `rejected:risk_framework_max_account_exposure_pct_exceeded`
- `rejected:risk_framework_max_strategy_exposure_pct_exceeded`
- `rejected:risk_framework_max_symbol_exposure_pct_exceeded`

Framework reason-code variants (for example `rejected: kill_switch_enabled`)
must be normalized to the canonical vocabulary above before cross-surface
inspection/read comparison.

For issue #993 producer paths, evidence rows are emitted only when a cap or
boundary is violated. For issue #1047 bounded risk-budget paths, approved
outcomes emit deterministic bounded evidence rows for stop-loss position
sizing, trade risk, strategy risk, symbol risk, and portfolio risk when bounded
risk evidence is required.

## Runtime and Portfolio Producers

Risk producer:

- `src/cilly_trading/risk_framework/risk_evaluator.py`
- emits `RiskEvaluationResponse.policy_evidence`

Approval discipline:

- exposure-only approved risk outcomes (`approved: within_risk_limits`) emit no
  evidence rows
- bounded risk-budget approved outcomes emit deterministic approve evidence
  rows for trade, strategy, symbol, and portfolio risk scope
- reject outcomes emit canonical reject/cap/boundary evidence rows

Execution adapter propagation:

- `src/cilly_trading/engine/risk/gate.py`
- normalizes reason codes to canonical vocabulary
- enforces deterministic precedence for multi-violation candidates
- propagates `policy_evidence` into `RiskDecision`
- evaluates covered trade/symbol/strategy/portfolio/runtime evidence through one
  deterministic rejection path
- fails closed when covered required evidence is contradictory or malformed
- preserves bounded compatibility by mapping legacy reason-only rejects to one
  deterministic synthetic evidence row when explicit evidence rows are absent

Portfolio producers:

- `src/cilly_trading/portfolio_framework/capital_allocation_policy.py`
- `src/cilly_trading/portfolio_framework/guardrails.py`
- emit `CapitalAllocationAssessment.policy_evidence`,
  `PortfolioGuardrailAssessment.policy_evidence`, and
  `PortfolioDecisionRecord.policy_evidence`

Portfolio discipline:

- portfolio pipeline outcomes are `approved`, `rejected`, or `constraint_hit`
- policy evidence is emitted only for violated cap/boundary outcomes
- fully approved outcomes carry an empty evidence tuple

## Priority and Conflict Semantics

Deterministic ordering for per-request risk evaluation:

1. runtime boundary (`kill_switch_enabled`)
2. stop-loss evidence missing or invalid
3. bounded stop-loss position sizing
4. per-trade stop-loss risk budget
5. strategy risk budget
6. symbol risk budget
7. portfolio risk budget
8. trade cap (`max_position_size`)
9. portfolio cap (`max_account_exposure_pct`)
10. strategy cap (`max_strategy_exposure_pct`)
11. symbol cap (`max_symbol_exposure_pct`)

Normalized precedence order (canonical reason codes):

- `rejected:risk_framework_kill_switch_enabled`
- `rejected:risk_framework_stop_loss_evidence_missing`
- `rejected:risk_framework_stop_loss_evidence_invalid`
- `rejected:risk_framework_position_size_exceeds_stop_loss_budget`
- `rejected:risk_framework_max_trade_risk_exceeded`
- `rejected:risk_framework_strategy_risk_budget_exceeded`
- `rejected:risk_framework_symbol_risk_budget_exceeded`
- `rejected:risk_framework_portfolio_risk_budget_exceeded`
- `rejected:risk_framework_max_position_size_exceeded`
- `rejected:risk_framework_max_account_exposure_pct_exceeded`
- `rejected:risk_framework_max_strategy_exposure_pct_exceeded`
- `rejected:risk_framework_max_symbol_exposure_pct_exceeded`

Deterministic ordering for portfolio decision pipeline:

1. allocation intent feasibility
2. capital allocation caps
3. portfolio guardrail boundaries

If any cap/boundary rejects the candidate, the signal is not applied to final
state.

Inspection/read normalization:

- `src/api/services/inspection_service.py` read surfaces normalize compatible
  risk reject reason-code variants to `normalized_reason_code` on a best-effort
  basis for bounded non-live cross-surface comparison in bounded non-live
  inspection flows.
- inspection/read normalization does not aggregate multiple compatible reason
  codes from one entry and does not emit a `normalized_reason_codes` contract
  field.

Cross-surface deterministic contract:

- equivalent bounded non-live input state must emit the same canonical reject
  reason code across risk gate and paper execution worker surfaces.
- deterministic precedence is mandatory when multiple constraints are violated.
- contradictory covered evidence for an approved decision is fail-closed.
- contradictory or malformed covered evidence for a rejected decision is
  fail-closed.
- inspection/read surfaces provide best-effort single-field normalization to
  `normalized_reason_code` without multi-reason precedence selection.
- this contract is technical non-live evidence only and is not live-trading or broker-readiness evidence.

## Non-Live Readiness Discipline

Passing this contract means deterministic technical policy consistency only.
It does not imply trader validation, production readiness, live-trading
readiness, or broker go-live approval.

## Bounded Risk-Framework Authority Contract Reference

The canonical bounded risk-framework authority that governs the bounded
non-live risk primitives covered by this evidence contract is:

- `docs/architecture/risk/bounded_risk_framework_authority_contract.md`

The canonical bounded authority id is `risk_framework_bounded_non_live_v1`.
This evidence contract aligns with that authority for canonical reason-code
vocabulary and deterministic precedence.

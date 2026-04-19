# Professional Non-Live Risk and Exposure Evaluation Contract

## Purpose

Define one deterministic, reviewable contract for non-live risk/exposure
evaluation evidence across:

- trade-level risk checks
- symbol-level exposure checks
- strategy-level exposure checks
- portfolio-level cap and guardrail checks

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
- `rejected:risk_framework_max_position_size_exceeded`
- `rejected:risk_framework_max_account_exposure_pct_exceeded`
- `rejected:risk_framework_max_strategy_exposure_pct_exceeded`
- `rejected:risk_framework_max_symbol_exposure_pct_exceeded`

Framework reason-code variants (for example `rejected: kill_switch_enabled`)
must be normalized to the canonical vocabulary above before cross-surface
inspection/read comparison.

For issue #993 producer paths, evidence rows are emitted only when a cap or
boundary is violated. Approved outcomes remain deterministic and carry an empty
evidence tuple.

## Runtime and Portfolio Producers

Risk producer:

- `src/cilly_trading/risk_framework/risk_evaluator.py`
- emits `RiskEvaluationResponse.policy_evidence`

Approval discipline:

- approved risk outcomes (`approved: within_risk_limits`) emit no evidence rows
- reject outcomes emit one canonical reject/cap/boundary evidence row

Execution adapter propagation:

- `src/cilly_trading/engine/risk/gate.py`
- normalizes reason codes to canonical vocabulary
- enforces deterministic precedence for multi-violation candidates
- propagates `policy_evidence` into `RiskDecision`

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
2. trade cap (`max_position_size`)
3. portfolio cap (`max_account_exposure_pct`)
4. strategy cap (`max_strategy_exposure_pct`)
5. symbol cap (`max_symbol_exposure_pct`)

Normalized precedence order (canonical reason codes):

1. `rejected:risk_framework_kill_switch_enabled`
2. `rejected:risk_framework_max_position_size_exceeded`
3. `rejected:risk_framework_max_account_exposure_pct_exceeded`
4. `rejected:risk_framework_max_strategy_exposure_pct_exceeded`
5. `rejected:risk_framework_max_symbol_exposure_pct_exceeded`

Deterministic ordering for portfolio decision pipeline:

1. allocation intent feasibility
2. capital allocation caps
3. portfolio guardrail boundaries

If any cap/boundary rejects the candidate, the signal is not applied to final
state.

Inspection/read normalization:

- `src/api/services/inspection_service.py` read surfaces normalize compatible
  risk reject reason-code variants to the canonical vocabulary above for
  deterministic cross-surface comparison in bounded non-live inspection flows.

## Non-Live Readiness Discipline

Passing this contract means deterministic technical policy consistency only.
It does not imply trader validation, production readiness, live-trading
readiness, or broker go-live approval.

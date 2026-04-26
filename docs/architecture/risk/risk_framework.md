# Risk Framework Architecture Artifact

## 1) Purpose
The Risk Framework is a governance-controlled architectural subsystem that defines and enforces exposure constraints before any execution pathway is considered. Its purpose is to provide deterministic risk validation as an independent control boundary within the trading engine.

## 2) Architectural Boundary
The module root for the Risk Framework is:

`src/cilly_trading/risk_framework/`

This boundary is isolated from the execution layer. The Risk Framework must remain an independent policy and validation subsystem and must not depend on execution implementation details, execution state, or execution-side control flow.

## 3) Scope
The Risk Framework scope is strictly limited to the following architectural responsibilities:

- **RiskEvaluation contract**: Defines the formal interface for evaluating whether requested actions satisfy risk constraints.
- **Exposure model**: Represents and evaluates position and account exposure relevant to risk decisions.
- **Allocation rules**: Applies predefined allocation constraints and threshold policies.
- **Kill-switch**: Provides a hard stop control for immediate risk denial when governance conditions require it.
- **Deterministic enforcement logic**: Enforces constraints through deterministic rules that produce reproducible outcomes for identical inputs.

## 4) Non-Goals
The following capabilities are explicitly out of scope for the Risk Framework:

- Trading logic
- Portfolio optimization
- Broker integration
- Backtesting

## 5) Import Direction Rules
To preserve architectural isolation and control integrity, the following dependency rules are mandatory:

- **Orchestrator -> Risk**: Allowed.
- **Risk -> Execution**: Forbidden.
- **Cyclic imports**: Forbidden across Risk Framework boundaries.

These rules are normative and must be maintained over time.

## 6) Relationship to Strategy Lifecycle
Strategy lifecycle components control strategy activation and deactivation states. The Risk Framework does not manage lifecycle transitions.

The Risk Framework evaluates exposure constraints only. It consumes lifecycle-relevant context as input when provided, but it does not own or mutate lifecycle state.

## 7) Determinism Guarantees
Risk Framework enforcement logic must satisfy the following determinism guarantees:

- **Pure functions** for risk evaluation behavior.
- **Immutable contracts** for inputs and outputs at evaluation boundaries.
- **No IO** within enforcement paths.
- **No global state** influencing decision outcomes.

These guarantees ensure reproducibility, auditability, and governance consistency.

## 8) Non-Live Execution Adapter Boundary
For bounded non-live execution paths, risk-framework evaluation outcomes are
adapted into the execution-layer risk decision contract using one deterministic
mapping path:

- Canonical evaluator source:
  `src/cilly_trading/risk_framework/risk_evaluator.py`
- Execution adapter target:
  `src/cilly_trading/engine/risk/gate.py`

Adapter scope is bounded to non-live operation and maps canonical outcomes for:

- account exposure limit enforcement
- strategy exposure limit enforcement
- symbol exposure limit enforcement
- position-size limit enforcement
- kill-switch rejection

The adapter does not alter risk rules. It only translates deterministic
risk-framework outcomes into deterministic execution decision codes.

## 8.1) Professional Non-Live Evaluation Contract
Risk evaluation outputs also emit structured non-live evidence rows for
reviewable reject/cap/boundary semantics through:

- `src/cilly_trading/non_live_evaluation_contract.py`
- `RiskEvaluationResponse.policy_evidence` in
  `src/cilly_trading/risk_framework/risk_evaluator.py`
- propagated execution evidence in `RiskDecision.policy_evidence` via
  `src/cilly_trading/engine/risk/gate.py`

The canonical cross-framework contract is:

- `docs/architecture/risk/non_live_evaluation_contract.md`

Evidence discipline for this bounded contract:

- risk evaluator outcomes are `approved` or `rejected`
- exposure-only approved outcomes emit an empty evidence tuple
- bounded risk-budget approved outcomes emit deterministic stop-loss
  position-sizing, trade, strategy, symbol, and portfolio evidence rows
- rejected outcomes emit canonical cap/boundary evidence rows

## 8.2) Bounded Risk-Framework Authority Contract
This framework is governed by one canonical bounded risk-framework authority
contract that consolidates the currently implemented bounded risk primitives,
their canonical evidence vocabulary, deterministic validation surfaces, and
non-live wording boundaries:

- `docs/architecture/risk/bounded_risk_framework_authority_contract.md`

The canonical bounded authority id is `risk_framework_bounded_non_live_v1`.
This authority is bounded non-live technical evidence only and is not
live-trading, broker, trader-validation, or operational-readiness evidence.

## 9) MVP Guardrails
For MVP scope control, the Risk Framework shall exclude the following:

- No live trading
- No AI scoring
- No dynamic volatility scaling

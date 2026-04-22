# Bounded Risk-Framework Authority Contract

## Purpose

Define one canonical bounded risk-framework authority contract for the
currently implemented risk primitives in this repository. This contract
reconciles the existing risk primitives, enforcement points, wording
boundaries, and deterministic validation surfaces under one canonical
authority without expanding risk scope.

This contract is bounded technical evidence only. It is not a live-trading
contract, broker-readiness contract, trader-validation contract, or
operational-readiness contract.

## Canonical Authority Identifier

- Canonical authority id: `risk_framework_bounded_non_live_v1`
- Authority classification: canonical for bounded non-live risk-boundary
  evaluation semantics only.
- Roadmap traceability: ROADMAP_MASTER.md Phase 27 (Risk Framework Governance).

This identifier is the single canonical authority handle for the bounded
risk-framework primitives covered by this contract.

## In Scope

- canonical bounded risk-framework authority for currently implemented risk
  primitives
- alignment of governance documentation, risk-evaluator runtime surfaces, and
  risk regression tests under the same bounded risk semantics
- deterministic regression coverage proving identical covered inputs produce
  identical risk-boundary evaluation outputs
- explicit non-live, non-broker, no-readiness-overclaim boundaries

## Out of Scope

- new risk models
- threshold retuning
- strategy changes
- execution-policy redesign
- live trading scope
- broker integration
- readiness or profitability claims
- broad UI expansion

## Authoritative Surfaces

The bounded risk-framework authority is materialized by exactly the following
repository surfaces:

- Risk evaluator (canonical evaluator):
  `src/cilly_trading/risk_framework/risk_evaluator.py`
- Risk evaluation contract:
  `src/cilly_trading/risk_framework/contract.py`
- Allocation rules / limits:
  `src/cilly_trading/risk_framework/allocation_rules.py`
- Kill-switch primitive:
  `src/cilly_trading/risk_framework/kill_switch.py`
- Non-live evaluation evidence contract:
  `src/cilly_trading/non_live_evaluation_contract.py`
- Execution-side risk gate / adapter:
  `src/cilly_trading/engine/risk/gate.py`
- Canonical bounded authority surface:
  `src/cilly_trading/engine/risk/authority.py`

No other module is canonical for bounded risk-framework authority. Surfaces
not listed here may consume the contract but must not redefine its semantics.

## Canonical Evidence Vocabulary

The bounded risk-framework authority emits exactly one canonical reason-code
vocabulary.

Approved outcome reason code:

- `approved:risk_framework_within_limits`

Canonical rejection reason codes (precedence order):

1. `rejected:risk_framework_kill_switch_enabled`
2. `rejected:risk_framework_max_position_size_exceeded`
3. `rejected:risk_framework_max_account_exposure_pct_exceeded`
4. `rejected:risk_framework_max_strategy_exposure_pct_exceeded`
5. `rejected:risk_framework_max_symbol_exposure_pct_exceeded`

The canonical guard-type vocabulary for risk-gate guard triggers is:

- `kill_switch`
- `drawdown`
- `daily_loss`
- `emergency`

These vocabularies are normative and identical to the constants exposed by
`src/cilly_trading/non_live_evaluation_contract.py` and
`src/cilly_trading/engine/risk/gate.py`. The bounded authority surface
re-exports them so consumers reference one canonical handle.

## Deterministic Risk-Boundary Evaluation

The bounded risk-framework authority guarantees the following deterministic
properties for risk-boundary evaluation:

- pure-function evaluation: identical covered inputs produce identical
  risk-boundary evaluation outputs across repeated invocations
- normalized reason-code precedence: when multiple constraints are violated,
  the canonical reason code is selected by the precedence order above
- timezone-aware UTC `evaluated_at` is required; naive timestamps are
  rejected
- approved outcomes carry an empty `policy_evidence` tuple
- rejected outcomes carry exactly one canonical cap/boundary evidence row

Identical covered inputs are defined as the full tuple of:

- `request_id`, `strategy_id`, `symbol`
- `proposed_position_size`, `account_equity`, `current_exposure`
- `strategy_exposure`, `symbol_exposure`
- `limits` (`RiskLimits`), `rule_version`, kill-switch `config`
- `evaluated_at`

Two evaluations sharing this full input tuple must return equal
`RiskDecision` values.

## Fail-Closed Bounded Evidence Discipline

The bounded risk-framework authority enforces fail-closed semantics when
required bounded evidence is incomplete or contradictory:

- missing risk decision at the execution boundary -> raise
  `RiskApprovalMissingError`
- non-`APPROVED` risk decision at the execution boundary -> raise
  `RiskRejectedError`
- risk-framework `approved` flag conflicts with mapped execution decision ->
  raise `ValueError` (contradictory bounded evidence)
- unsupported risk-framework reason code -> raise `ValueError` (incomplete
  bounded evidence)
- non-finite or unbounded threshold / notional inputs at the threshold gate
  -> raise `ValueError`
- naive (non-UTC, non-timezone-aware) `evaluated_at` -> raise `ValueError`

Fail-closed means that absence, ambiguity, or contradiction of bounded
evidence never silently degrades to an APPROVED execution decision.

## Wording Boundaries

Documentation, runtime surfaces, and tests covered by this authority must
preserve the following wording boundaries:

- this authority is bounded non-live technical evidence
- this authority does not authorize live trading
- this authority does not authorize broker integration
- this authority is not trader-validation evidence
- this authority is not operational-readiness evidence
- this authority is not a profitability or edge claim
- this authority does not imply production readiness

These boundaries are identical in spirit to the non-inference rules in
`docs/operations/ui/product-surface-authority-contract.md` and the claim
discipline in `docs/governance/qualification-claim-evidence-discipline.md`,
restated here for the bounded risk-framework scope.

## Alignment References

- `docs/architecture/risk/risk_framework.md`
- `docs/architecture/risk/non_live_evaluation_contract.md`
- `docs/architecture/risk/contract.md`
- `docs/governance/bounded-risk-framework-authority.md`
- `docs/governance/qualification-claim-evidence-discipline.md`
- `ROADMAP_MASTER.md` Phase 27 (Risk Framework Governance)

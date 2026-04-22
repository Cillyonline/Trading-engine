# Qualification Claim Evidence Discipline

## 1. Purpose

This governance contract defines bounded evidence discipline for qualification claims and trader-facing confidence language.
It keeps technical implementation status, trader validation, and operational readiness as separate claim layers.

## 2. Evidence Hierarchy for Qualification Claims

Qualification claims must remain inside this ordered evidence hierarchy:

1. Hard-gate evidence (explicit pass/fail gates with recorded evidence)
2. Bounded component evidence (`signal_quality`, `backtest_quality`, `portfolio_fit`, `risk_alignment`, `execution_readiness`)
3. Bounded aggregate/confidence resolution (`low` | `medium` | `high`)
4. Bounded paper-trading qualification state (`reject` | `watch` | `paper_candidate` | `paper_approved`)

Claiming a higher layer without evidence for lower layers is out of contract.

## 3. Bounded Trader-Facing Confidence Language

Confidence language is evidence-aligned only when it:

- references bounded evidence semantics (aggregate score, component scores, thresholds, explicit evidence)
- remains in paper-trading qualification scope
- avoids certainty or readiness claims outside available evidence

The following claim classes are unsupported in qualification outputs and must be rejected:

- live-trading readiness/approval claims
- production readiness claims
- broker execution readiness claims
- trader-validation claims
- paper profitability or edge claims
- guaranteed/certain outcome claims

## 4. Deterministic Bounded Trader-Relevance Review Contract

Canonical contract id/version:

- `bounded_trader_relevance.paper_review.v1`
- version `1.0.0`
- structured boundary fields contract `bounded_non_inference_boundary_fields.read_only.v1`
- structured boundary fields contract version `1.0.0`

Canonical structured evidence fields (non-inference + claim-boundary semantics):

- `qualification_state`
- `paper_scope_summary`
- `state_explanation_evidence`
- `action`
- `bounded_decision_metrics`
- `action_rule_trace`
- `trader_validation_boundary`
- `paper_profitability_boundary`
- `live_readiness_boundary`

Paper-review cases (deterministic and ordered by case id):

- `qualification_state_relevance`: verify qualification-state output is evidence-explained and explicitly paper-scoped
- `decision_action_relevance`: verify action output is evidence-explained with bounded decision metrics
- `boundary_scope_relevance`: verify explicit structured boundary-field separation for trader_validation, paper profitability, and live-readiness semantics

Case status semantics:

- `aligned`: all required evidence signals for the case are present
- `weak`: some required evidence signals are present, but at least one is missing
- `missing`: no required evidence signals are present

Primary enforcement and fallback rule:

- runtime boundary evaluation is driven by the canonical structured evidence fields above
- wording/phrase matching remains bounded compatibility fallback only when required structured fields are absent
- outputs must include deterministic boundary status and explicit boundary-failure reasons for missing boundary fields

Determinism rule:

- identical inputs must produce identical case classifications and ordering
- classification must be machine-evaluable from explicit output evidence fields only (no manual interpretation)

## 5. Deterministic Bounded Decision-to-Paper Usefulness Audit

Canonical contract id/version:

- `decision_evidence_to_paper_outcome_usefulness.paper_audit.v1`
- version `1.0.0`

Covered cases:

- only decision cards that explicitly declare `metadata.bounded_decision_to_paper_match`
- contract v1 is bounded to covered `entry` decisions only
- the explicit match contract is one exact `paper_trade_id`

Deterministic matching rule:

- resolve the exact `paper_trade_id`
- the matched paper trade must share the same `symbol` and `strategy_id` as the decision card
- the matched paper trade must open at or after `generated_at_utc`
- if any of those checks fail, the usefulness signal is out of contract and must be classified as misleading

Usefulness classification semantics:

- `explanatory`: the covered entry decision matches a subsequent closed paper trade with a favorable bounded outcome
- `weak`: the covered entry decision has no resolved match, remains open, or closes flat
- `misleading`: the covered entry decision matches an invalid or adverse bounded paper outcome

Claim boundary:

- usefulness is bounded to non-live explanatory review only
- it is not trader validation
- it is not profitability forecasting
- it is not live-trading readiness
- it is not operational readiness

## 6. Runtime and Documentation Alignment Rule

Documentation and runtime wording must enforce the same boundary:

- decision-card contract and runtime output use the same canonical structured boundary fields first
- inspection API mirrors the same structured boundary contract and deterministic failure reasons
- qualification outputs explicitly state they do not imply live-trading approval

## 7. Validation Rule

Where claim-boundary enforcement exists in runtime contracts, validation must fail closed for unsupported claim language.
Validation is required for:

- confidence reason text
- qualification summary text
- rationale summary/final explanation text
- structured non-inference boundary fields when surfaced on decision/inspection read payloads

## 8. Non-Goals

This governance contract does not grant:

- live trading approval
- broker execution approval
- operational production approval

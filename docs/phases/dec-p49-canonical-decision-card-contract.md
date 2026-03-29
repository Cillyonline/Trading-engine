# DEC-P49 - Canonical Decision-Card Contract

## Goal

Define the canonical decision-card contract with explicit hard-gate behavior, bounded component-score semantics, and bounded qualification state semantics.

## Canonical Runtime Contract

- Contract implementation: `src/cilly_trading/engine/decision_card_contract.py`
- Inspection read-surface alignment: `docs/api/decision_card_inspection.md`
- Architecture contract reference: `docs/architecture/decision_card_contract.md`

## Contract Boundaries

The contract is canonical and deterministic:

1. hard gates are explicit and independently represented
2. component scores are explicit, category-complete, and bounded
3. qualification state is bounded and deterministically resolved from gate + score semantics

## Hard-Gate Behavior

- hard-gate payload shape is explicit (`gate_id`, `status`, `blocking`, `reason`, `evidence`, `failure_reason`)
- hard-gate IDs are unique
- hard-gate failures require `failure_reason`
- passing hard gates must not provide `failure_reason`
- any blocking hard-gate failure requires `qualification.state=reject` and `qualification.color=red`

## Component-Score Semantics

- required categories are fixed:
  - `signal_quality`
  - `backtest_quality`
  - `portfolio_fit`
  - `risk_alignment`
  - `execution_readiness`
- per-component score range is bounded to `[0, 100]`
- aggregate score range is bounded to `[0, 100]`
- confidence tier is bounded (`low` | `medium` | `high`)
- confidence reason is evidence-bounded and rejects unsupported inflation language

## Qualification-State Semantics

State vocabulary is bounded:

- `reject`
- `watch`
- `paper_candidate`
- `paper_approved`

Deterministic state resolution is contract-enforced:

1. blocking hard-gate failure -> `reject`
2. no blocking failure + (`confidence_tier=low` or `aggregate_score < 60.0`) -> `watch`
3. no blocking failure + (`confidence_tier=high` and `aggregate_score >= 80.0`) -> `paper_approved`
4. otherwise -> `paper_candidate`

State/color mapping is bounded:

- `reject -> red`
- `watch -> yellow`
- `paper_candidate -> yellow`
- `paper_approved -> green`

## Inspection Wording Alignment

Inspection wording aligns with the canonical contract by requiring:

- explicit hard-gate evidence
- bounded component and aggregate scoring language
- bounded paper-trading qualification wording
- explicit non-implication of live-trading approval

## Non-Goals

- live-trading approval
- broker execution
- unrestricted sentiment expansion
- unrelated dashboard growth
- broad strategy-lab expansion

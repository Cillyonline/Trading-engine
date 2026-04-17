# DEC-P49 - Canonical Decision-Card Contract

## Goal

Define the canonical decision-card contract with explicit hard-gate behavior, bounded component-score semantics, bounded expected-value and win-rate semantics, bounded deterministic decision actions, and bounded qualification state semantics.

## Canonical Runtime Contract

- Contract implementation: `src/cilly_trading/engine/decision_card_contract.py`
- Inspection read-surface alignment: `docs/api/decision_card_inspection.md`
- Architecture contract reference: `docs/architecture/decision_card_contract.md`

## Contract Boundaries

The contract is canonical and deterministic:

1. hard gates are explicit and independently represented
2. component scores are explicit, category-complete, and bounded
3. qualification state is bounded and deterministically resolved from gate + score semantics
4. decision action is explicit and deterministically resolved for paper evaluation

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
- win-rate evidence is bounded to `[0, 1]` and derived from deterministic component inputs
- expected-value evidence is bounded to `[-1, 1]` and derived from deterministic component inputs
- documented formulas:
  - `win_rate=((signal_quality*0.60)+(backtest_quality*0.40))/100`
  - `expected_value=(win_rate*bounded_reward_multiplier)-(1-win_rate)`
  - `bounded_reward_multiplier=clamp((risk_alignment+execution_readiness)/100,0.50,1.50)`

## Decision Action Semantics

Action vocabulary is bounded:

- `entry`
- `exit`
- `ignore`

Deterministic action resolution is contract-enforced:

1. blocking hard-gate failure -> `ignore`
2. negative expected value -> `exit` (must not resolve to `entry`)
3. qualified (`paper_candidate`/`paper_approved`) with bounded win-rate `<= 0.50` -> `exit`
4. qualified with bounded win-rate `>= 0.55` and non-negative expected value -> `entry`
5. otherwise -> `ignore`

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
- explicit technical implementation evidence status separate from trader validation status

## Non-Goals

- live-trading approval
- broker execution
- unrestricted sentiment expansion
- unrelated dashboard growth
- broad strategy-lab expansion

# Decision-Card Contract

## Purpose

This document defines the canonical decision-card contract used to qualify or reject opportunities.  
The contract separates:

- hard-gate semantics (blocking policy checks)
- bounded score semantics (component-based scoring)
- explicit confidence tier
- explicit qualification state and color
- explicit rationale requirements

The canonical implementation is `src/cilly_trading/engine/decision_card_contract.py`.

## Canonical Vocabulary

Top-level decision-card fields:

- `contract_version`
- `decision_card_id`
- `generated_at_utc`
- `symbol`
- `strategy_id`
- `hard_gates`
- `score`
- `qualification`
- `rationale`
- `metadata`

## Hard-Gate Semantics

Hard gates are represented by `hard_gates.gates[]` and are evaluated independently from scoring.

Per-gate fields:

- `gate_id`
- `status` (`pass` | `fail`)
- `blocking` (boolean)
- `reason`
- `evidence[]`
- `failure_reason` (required when `status=fail`)

Contract semantics:

- blocking gate failures are terminal for qualification
- a blocking failure requires qualification state `rejected` and color `red`
- gate evidence must be explicit (no opaque gate result)

## Score Semantics

Scores are represented by `score.component_scores[]` and are bounded in `[0, 100]`.

Required component categories (exact coverage required):

- `signal_quality`
- `backtest_quality`
- `portfolio_fit`
- `risk_alignment`
- `execution_readiness`

Additional score fields:

- `aggregate_score` in `[0, 100]`
- `confidence_tier` (`low` | `medium` | `high`)
- `confidence_reason`

Hard-gate outcomes and score outcomes remain separate objects by contract.

## Qualification Output

Qualification is explicit and not inferred from a single score field:

- `state`: `qualified` | `watchlist` | `rejected`
- `color`: `green` | `yellow` | `red`
- `summary`

State-to-color mapping is fixed:

- `qualified -> green`
- `watchlist -> yellow`
- `rejected -> red`

## Rationale Requirements

`rationale` is required and must include:

- `summary`
- `gate_explanations[]`
- `score_explanations[]`
- `final_explanation`

This prevents collapsing gates, evidence, and qualification into an opaque number.

## Deterministic Serialization

Decision cards serialize through deterministic canonical JSON:

- sorted keys
- stable separators
- deterministic ordering of gate and component collections

Deterministic serialization API:

- `validate_decision_card(payload)`
- `serialize_decision_card(card)`
- `DecisionCard.to_canonical_json()`

## Non-Goals

This contract does not introduce:

- sentiment ingestion implementation
- new strategy logic
- live-trading approval workflow
- broker integrations
- UI redesign
- dashboard product scope

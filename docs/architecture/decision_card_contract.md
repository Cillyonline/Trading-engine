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
Deterministic evaluation logic is implemented in `src/cilly_trading/engine/qualification_engine.py`.

## Active Version

- Active contract version: `2.0.0`
- This is a breaking revision from `1.0.0` because qualification action-state vocabulary changed from
  `qualified | watchlist | rejected` to
  `reject | watch | paper_candidate | paper_approved`.

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
- a blocking failure requires qualification state `reject` and color `red`
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

### Subsystem Input Integration

The qualification engine supports explicit subsystem input paths:

- `backtest_evidence` -> bounded `backtest_quality` score contribution
- `portfolio_fit_input` -> bounded `portfolio_fit` score contribution
- `sentiment_overlay` -> bounded aggregate overlay only (not a primary component category)

Integration rules:

- backtest evidence and portfolio-fit inputs are each bounded to `[0, 100]`
- these paths replace their respective component values explicitly for the decision card
- sentiment does not replace component categories and is never treated as primary alpha

## Qualification Output

Qualification is explicit and not inferred from a single score field:

- `state`: `reject` | `watch` | `paper_candidate` | `paper_approved`
- `color`: `green` | `yellow` | `red`
- `summary`

State-to-color mapping is fixed:

- `reject -> red`
- `watch -> yellow`
- `paper_candidate -> yellow`
- `paper_approved -> green`

Deterministic action-state resolution:

1. Any blocking hard-gate failure resolves to `reject` / `red`.
2. If no blocking failure and confidence is `low` (or aggregate score is below the medium threshold), resolve to `watch` / `yellow`.
3. If confidence is `high` and aggregate score is above the high threshold, resolve to `paper_approved` / `green`.
4. Otherwise resolve to `paper_candidate` / `yellow`.

This output is bounded to paper-trading readiness only and does not imply live-trading approval.

## Sentiment Overlay Boundaries

Sentiment is modeled as a bounded overlay to aggregate score, not as an independent qualification source.

- overlay is applied after weighted component aggregation
- overlay score input is bounded to `[-1, 1]`
- overlay points are bounded by a fixed cap and by stronger evidence layers (`backtest_quality`, `portfolio_fit`, `risk_alignment`)
- missing sentiment yields neutral overlay (`0.0` points)
- stale sentiment yields neutral overlay (`0.0` points)
- stale/missing handling is explicit in rationale and metadata; no silent corruption is permitted

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

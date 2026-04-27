# Score Semantics and Cross-Strategy Comparability

## 1. Purpose

This governance contract defines the bounded semantics of decision-card scores and
the explicit limits of cross-strategy score comparison.

It prevents score outputs from being misinterpreted as directly comparable across
strategies from different comparison groups or as precise probability estimates.

## 2. What Cross-Strategy Score Comparison Does and Does Not Mean

Decision-card scores are bounded to within-strategy evaluation for a single opportunity.

**What scores represent:**

- Component scores reflect bounded evidence from a single strategy evaluation against
  one opportunity at one point in time.
- The aggregate score is a weighted composite of the five required component categories
  for that strategy evaluation only.
- The confidence tier is an ordinal classification (low/medium/high) derived from
  bounded aggregate and component thresholds.

**What scores do not represent:**

- Direct cross-strategy comparability: aggregate scores from strategies in different
  comparison groups are not directly comparable by numeric value.
- Precise probability or forecast accuracy: the confidence tier is an ordinal
  classification, not a calibrated probability or statistical confidence interval.
- Cross-opportunity ranking: a score of 80 for strategy RSI2 on symbol AAPL does not
  imply a higher ranking than a score of 75 for strategy TURTLE on the same symbol.
- Live-trading readiness or broker execution approval in any comparison scenario.

## 3. Comparison Group Semantics

The `comparison_group` metadata field in the strategy registry identifies which
strategies share a meaningful comparison scope.

- Strategies within the same comparison group use compatible signal generation
  approaches and may be compared by score in that shared context.
- Strategies in different comparison groups (e.g. `mean-reversion` vs `trend-following`)
  are not directly comparable by decision-card score.

Cross-group score comparison is explicitly out of contract and must not be used to
rank or select strategies against each other.

## 4. Score Precision Boundaries

The aggregate score is a bounded weighted composite and not a high-precision measurement:

- It is expressed as a float in `[0, 100]` for implementation convenience.
- Numeric precision does not imply measurement accuracy beyond the bounded component
  evidence supporting it.
- Differences of a few points should not be interpreted as meaningful signal quality
  distinctions without explicit supporting evidence.

The confidence tier is the primary bounded interpretation:

- `low`: aggregate or component minimum below medium-confidence thresholds
- `medium`: aggregate and component minimum satisfy medium-confidence thresholds
- `high`: aggregate and component minimum satisfy high-confidence thresholds

No stronger claim than these bounded tier definitions is supported.

## 4.1 Comparison-Group Threshold Profile Calibration

Qualification thresholds are calibrated through deterministic threshold profiles keyed
by strategy `comparison_group`.

- Each strategy resolves one bounded threshold profile identifier from registry metadata.
- The applied profile governs confidence/qualification aggregate and minimum-component
  threshold checks for that strategy evaluation.
- Profile calibration does not change cross-group score meaning: strategies in different
  comparison groups remain not directly comparable by score.

Threshold-profile calibration is bounded contract behavior for within-group qualification
consistency only and does not create cross-group ranking authority.

## 4.2 Qualification-Profile Robustness Audit Boundary

Qualification-profile robustness is audited through one fixed deterministic slice set
using existing qualification evidence dimensions only.

- one covered slice reproduces current-evidence qualification output
- bounded failure-envelope slices degrade signal/backtest and risk/execution evidence
  with fixed deterministic deltas
- one regime slice is resolved deterministically from strategy `comparison_group`
- audit output records explicit `stable`, `weak`, and `failing` behavior by slice

This robustness audit does not perform probabilistic regime detection, threshold
recalibration, or scope expansion beyond bounded decision-support review.

Weak or failing slices limit interpretation outside covered conditions. They do not
create live-trading approval, trader_validation completion, or profitability claims.

## 4.3 Per-Strategy MVP Score Calibration Boundary

RSI2 and Turtle MVP aggregate scores are classified as bounded per-strategy
calibration evidence only.

The bounded strategy-score calibration audit relates:

- the covered RSI2 or Turtle aggregate score
- the ordinal `confidence_tier`
- covered backtest-realism evidence where available
- matched paper-trade outcomes where an explicit `paper_trade_id` link exists

The audit emits explicit `stable`, `weak`, `failing`, or `limited` classification:

- `stable`: covered per-strategy score evidence is supported by stable backtest-realism
  coverage and a favorable matched paper outcome
- `weak`: covered evidence is partial, open, flat, or otherwise not strong enough for
  stable interpretation
- `failing`: covered score evidence conflicts with failing realism evidence, invalid
  paper matching, or an adverse matched paper outcome
- `limited`: backtest-realism evidence or matched paper evidence is missing, so the
  score remains bounded per-strategy evidence with limited calibration support

This audit does not rescore strategies, optimize strategy parameters, forecast
profitability, or validate trader judgement. Missing evidence must reduce the
classification to weak or limited and must not inflate confidence claims.

Confidence tier remains ordinal and does not represent a probability. Cross-strategy comparability remains explicitly unsupported unless governed evidence proves otherwise; current RSI2 and Turtle score calibration does not create cross-strategy ranking authority.

## 5. Runtime and Documentation Alignment Rule

All runtime wording and documentation must remain consistent with this governance contract:

- `confidence_reason` text must reference bounded evidence semantics and must not
  claim precise probability, cross-strategy equality, or live-trading readiness.
- qualification evidence must include the applied threshold profile identifier used
  for deterministic confidence and qualification resolution.
- `qualification.summary` text must stay within paper-trading scope.
- `rationale.final_explanation` must explicitly deny live-trading approval implication.

Constants in `src/cilly_trading/engine/decision_card_contract.py` define the bounded
wording templates that runtime qualification uses:

- `CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY`: the bounded non-comparability statement
- `CONFIDENCE_TIER_PRECISION_DISCLAIMER`: the bounded precision statement
- `QUALIFICATION_PROFILE_ROBUSTNESS_INTERPRETATION_BOUNDARY`: the bounded robustness
  interpretation limit for covered versus weak/failing slices
- `STRATEGY_SCORE_CALIBRATION_INTERPRETATION_BOUNDARY`: the bounded per-strategy
  score-calibration limit for RSI2/Turtle MVP score evidence

## 6. Non-Goals

This governance contract does not grant:

- cross-strategy ranking authority
- live trading approval or broker execution approval
- forecast or probability certification
- robustness claims outside covered conditions
- trader_validation completion or profitability forecasting from MVP score calibration

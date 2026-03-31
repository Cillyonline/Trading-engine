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

## 5. Runtime and Documentation Alignment Rule

All runtime wording and documentation must remain consistent with this governance contract:

- `confidence_reason` text must reference bounded evidence semantics and must not
  claim precise probability, cross-strategy equality, or live-trading readiness.
- `qualification.summary` text must stay within paper-trading scope.
- `rationale.final_explanation` must explicitly deny live-trading approval implication.

Constants in `src/cilly_trading/engine/decision_card_contract.py` define the bounded
wording templates that runtime qualification uses:

- `CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY`: the bounded non-comparability statement
- `CONFIDENCE_TIER_PRECISION_DISCLAIMER`: the bounded precision statement

## 6. Non-Goals

This governance contract does not grant:

- cross-strategy ranking authority
- live trading approval or broker execution approval
- forecast or probability certification

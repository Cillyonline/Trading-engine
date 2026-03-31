# SIG-P47 - Score Semantics and Cross-Strategy Comparability

## Goal

Calibrate bounded signal and score semantics across governed strategies so that
multi-strategy ranking and qualification outputs are less misleading.

## Acceptance Criteria

1. The repository explicitly states what cross-strategy score comparison does and does not mean.
2. Governed strategies have aligned score semantics or explicit bounded non-comparability wording.
3. Qualification confidence does not overclaim score precision.
4. Docs and tests align to the calibrated semantics.

## Claim Boundary

Score outputs are bounded to within-strategy evaluation for a single opportunity and must
not be interpreted as:

- direct cross-strategy comparison (different comparison groups are not comparable by score)
- precise probability or forecast accuracy (confidence tier is ordinal only)
- live-trading readiness or broker execution approval

## Bounded Non-Comparability Statement

Decision-card scores are bounded to within-strategy evaluation for a single opportunity.
Cross-strategy score comparison is not supported; aggregate scores and component scores
from strategies in different comparison groups are not directly comparable.

Required evidence order for score interpretation:

1. hard-gate evidence (blocking policy checks)
2. bounded component evidence per the five required categories
3. bounded confidence tier (ordinal classification, not a precise probability)
4. bounded qualification state (paper-trading scope only)

## Enforcement Surfaces

- `docs/governance/score-semantics-cross-strategy.md` defines the cross-strategy score governance rules
- `docs/architecture/decision_card_contract.md` defines contract wording requirements
- `src/cilly_trading/engine/decision_card_contract.py` exposes:
  - `CROSS_STRATEGY_SCORE_COMPARABILITY_BOUNDARY` (explicit non-comparability statement)
  - `CONFIDENCE_TIER_PRECISION_DISCLAIMER` (explicit precision boundary)
- `src/cilly_trading/strategies/registry.py` exposes:
  - `CROSS_STRATEGY_SCORE_NON_COMPARABILITY_NOTE` (registry-level non-comparability statement)
  - strategy metadata `comparison_group` field identifies valid comparison scope

## Validation

SIG-P47 coverage is validated through:

- `tests/test_sig_p47_score_semantics.py`
- `tests/cilly_trading/engine/test_qualification_engine.py`
- `tests/cilly_trading/engine/test_decision_card_contract.py`
- `tests/strategies/test_strategy_registry.py`

## Out-of-Scope Reminder

This issue does not introduce:

- new strategies
- machine-learning ranking
- live trading approval or broker execution approval
- UI redesign or deployment changes

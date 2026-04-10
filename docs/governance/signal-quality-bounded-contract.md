# P56 Signal Quality - Bounded Validation Contract

## Purpose

This contract defines signal-quality validation boundaries for current repository behavior.
It validates deterministic ranking and filtering behavior for decision-support inspection
without expanding strategy scope or changing runtime architecture.

## Scope

In scope:

- deterministic ranking behavior under fixed fixtures
- selectivity behavior via `min_score` filtering where score data is numeric
- bounded handling for weak or low-information cases where current implementation supports it
- wording discipline aligned to available repository evidence only

Out of scope:

- new strategies
- ML scoring
- external data expansion
- broad scoring redesign
- trader-readiness claims

## Bounded Signal-Quality Meaning

Within this repository, "signal quality" is bounded to three implementation-level properties:

1. Deterministic ranking behavior under defined fixtures.
2. Selectivity boundary for low-information candidates.
3. Stability boundary under equivalent fixture content.

This contract evaluates ordering and filtering consistency only. It does not evaluate
market edge, profitability, or production trading outcomes.

## Deterministic Ranking Boundary

For setup-stage candidates that meet the configured score floor, ranking is deterministic:

- primary key: `score` descending
- secondary key: `signal_strength` descending (when present)
- tiebreaker: `symbol` ascending

This boundary is implemented by the ranking key in
`src/api/services/analysis_service.py` (`build_ranked_symbol_results`).

## Selectivity Boundary

Selectivity is bounded to currently supported filtering behavior:

- only `stage == "setup"` is considered
- candidate score must meet `min_score` (inclusive)
- scores that cannot be coerced to numeric are treated as low-information and filtered
  out when `min_score > 0`

The filter is bounded to available signal fields and does not infer missing external context.

## Weak/Low-Information Handling Boundary

Current bounded behavior for weak or low-information signals:

- missing/empty `symbol` is excluded from ranked output
- non-setup stage is excluded from ranked output
- non-numeric or missing scores are not promoted above valid numeric setups

These are implementation boundaries, not trader-value guarantees.

## Stability Boundary

Given equivalent fixture content, ranked output remains stable independent of input list order.
Determinism is asserted through contract tests with permuted fixture ordering.

## Evidence and Claim Boundary

This contract supports only bounded implementation claims. It explicitly supports
"Classification: technically good, traderically weak" for current state.

It does not claim trader readiness, and it provides no live-trading readiness, execution approval, or profitability guarantee.

## Validation Surfaces

- Tests: `tests/test_sig_p56_signal_quality_contract.py`
- Runtime ranking surface: `src/api/services/analysis_service.py`
- Read-model ranking surface: `src/cilly_trading/repositories/signals_sqlite.py`

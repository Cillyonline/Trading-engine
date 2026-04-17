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

## Bounded Win-Rate and Expected-Value Evidence

For paper-evaluation qualification output, bounded signal-quality evidence also includes:

- bounded win-rate formula: `win_rate=((signal_quality*0.60)+(backtest_quality*0.40))/100`
- bounded expected-value formula:
  `expected_value=(win_rate*bounded_reward_multiplier)-(1-win_rate)`
  where `bounded_reward_multiplier=clamp((risk_alignment+execution_readiness)/100,0.50,1.50)`

Both values are deterministic, clamped (`win_rate` in `[0,1]`, `expected_value` in `[-1,1]`), and
derived only from existing bounded component evidence. They are technical evidence fields only.

## Deterministic Action Boundary

The qualification output includes one deterministic paper-evaluation action:

- `entry`
- `exit`
- `ignore`

Deterministic paper-evaluation action is resolved with hard gates plus bounded aggregate,
win-rate, and expected-value evidence:

1. blocking hard-gate failure -> `ignore`
2. negative expected value -> `exit` (never `entry`)
3. qualified (`paper_candidate`/`paper_approved`) with weak bounded win-rate (`<= 0.50`) -> `exit`
4. qualified with bounded win-rate (`>= 0.55`) and non-negative expected value -> `entry`
5. otherwise -> `ignore`

These action semantics are bounded to paper evaluation and must not be interpreted as
live-trading authorization.

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

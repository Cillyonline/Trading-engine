# Bounded Signal-to-Paper Execution Policy Contract (OPS-P52)

This document is the single authoritative bounded policy for determining when a
signal may become a paper trade.

It is intentionally bounded:

- It governs paper trade eligibility only.
- It does not define live order routing or broker API behavior.
- It does not expand into portfolio optimization engines, strategy redesign, or
  UI scope.
- It does not constitute live-trading approval or broker readiness.
- It remains non-live and confined to the bounded paper simulation boundary.

If another document references signal-to-paper execution rules, this document is
authoritative for the execution policy boundary.

## Non-Live Boundary

This policy operates exclusively within the bounded paper simulation boundary:

- No live orders are placed.
- No broker APIs are called.
- No real capital is at risk.
- Paper execution is governed simulation only and does not constitute live trading.
- Passing this policy gate does not imply live-trading readiness or broker
  go-live approval.

## Policy Overview

A signal does not automatically become a paper trade. The following ordered
evaluation sequence is applied to every candidate signal:

1. **Eligibility check** — required signal fields must be present and valid.
2. **Score threshold check** — signal score must meet the minimum threshold.
3. **Duplicate-entry check** — no duplicate open position may exist.
4. **Cooldown check** — minimum cooldown between entries must be satisfied.
5. **Exposure check** — position and exposure limits must not be exceeded.

A signal that fails any step produces an explicit outcome:

- **eligible**: signal passes all checks and may become a paper trade.
- **skip**: signal does not satisfy a soft rule; it is silently bypassed for this
  evaluation cycle.
- **reject**: signal violates a hard rule; it is blocked with an explicit reason
  code that must be logged.

## Eligibility Rules

A signal is ineligible (rejected) if any required field is absent or invalid:

| Field | Requirement |
| --- | --- |
| `symbol` | Non-empty string instrument identifier. |
| `strategy` | Non-empty string key matching a known governed strategy. |
| `direction` | Must be `long` or `short`. |
| `score` | Numeric value; must be present and within `[0.0, 1.0]`. |
| `timestamp` | Parseable ISO-8601 datetime or Unix epoch milliseconds. |
| `stage` | Must be non-empty and a recognized stage value such as `setup`. |

A signal missing any required field, or with a field value outside its allowed
boundary, is **rejected** with outcome code `reject:invalid_signal_fields`.

## Score Threshold Rules

Signals are subject to a minimum score threshold before paper entry is allowed:

- The default minimum score threshold is `0.6` (inclusive) on a `[0.0, 1.0]`
  scale.
- Signals with `score < 0.6` are **skipped** with outcome code
  `skip:score_below_threshold`.
- The threshold is a bounded paper simulation parameter. It is not a
  live-trading entry rule and does not imply broker execution readiness.

Score semantics remain bounded to within-strategy evaluation for a single
opportunity. Cross-strategy score comparison is not used as a threshold input;
see `docs/governance/score-semantics-cross-strategy.md`.

## Duplicate-Entry Prevention

A signal is blocked when an open paper position already exists for the same
`(symbol, strategy, direction)` tuple:

- An open position is any paper position that has not reached a terminal closed
  state.
- A signal that would open a duplicate entry is **skipped** with outcome code
  `skip:duplicate_entry`.
- The duplicate check is deterministic: it uses the canonical execution repository state
  as defined in
  `src/cilly_trading/portfolio/paper_state_authority.py`.
- Only one active issue should be executing per `(symbol, strategy)` scope at
  any time within the bounded paper simulation.

## Cooldown Rules

A minimum cooldown period must elapse between paper entries for the same
`(symbol, strategy)` pair:

- The default cooldown window is `24 hours` between consecutive accepted entry
  signals for the same `(symbol, strategy)` pair.
- The cooldown timer starts at the timestamp of the last accepted entry for that
  pair.
- A signal arriving within the cooldown window is **skipped** with outcome code
  `skip:cooldown_active`.
- Cooldown is tracked within the bounded paper simulation boundary and does not
  affect live trading or broker routing.

## Exposure and Position Limits

Paper entry is blocked when exposure or position limits would be exceeded.

### Per-position exposure limit

- The default maximum position size is `10%` of current account equity per
  individual paper position (`max_position_pct = 0.10`).
- A signal that would create a position exceeding this limit is **rejected**
  with outcome code `reject:position_size_exceeds_limit`.

### Global exposure limit

- The default maximum total paper exposure is `80%` of account equity across
  all open positions combined (`max_total_exposure_pct = 0.80`).
- A signal that would push total exposure beyond this limit is **rejected** with
  outcome code `reject:total_exposure_exceeds_limit`.

### Concurrent position limit

- The default maximum number of concurrent open paper positions is `10`
  (`max_concurrent_positions = 10`).
- A signal that would exceed the concurrent position limit is **rejected** with
  outcome code `reject:concurrent_position_limit_exceeded`.

All exposure and position limits are bounded paper simulation parameters. They
are not live-trading risk controls and do not constitute broker risk management.

## Eligibility, Skip, and Reject Outcome Summary

| Outcome | Code | Trigger |
| --- | --- | --- |
| Eligible | `eligible` | Signal passes all checks and may become a paper trade. |
| Skip | `skip:score_below_threshold` | Signal score is below the minimum threshold. |
| Skip | `skip:duplicate_entry` | Open position already exists for `(symbol, strategy, direction)`. |
| Skip | `skip:cooldown_active` | Cooldown window has not elapsed for `(symbol, strategy)`. |
| Reject | `reject:invalid_signal_fields` | Required signal field is absent or outside its allowed boundary. |
| Reject | `reject:position_size_exceeds_limit` | Proposed position size exceeds per-position cap. |
| Reject | `reject:total_exposure_exceeds_limit` | Proposed position would push total exposure over global cap. |
| Reject | `reject:concurrent_position_limit_exceeded` | Maximum concurrent open positions would be exceeded. |

**Skip** outcomes indicate a valid signal that does not satisfy a soft entry
rule. The signal is not an error; it is silently bypassed for this evaluation
cycle.

**Reject** outcomes indicate a hard policy violation. The signal is blocked with
an explicit reason code. The reason code must be logged for operator review.

## Policy Application Boundary

- This policy applies only within the bounded paper simulation boundary.
- It does not apply to backtesting, live trading, or broker execution.
- It does not configure strategy parameters or analysis engine outputs.
- Policy parameters (`min_score_threshold`, `max_position_pct`,
  `max_total_exposure_pct`, `max_concurrent_positions`, `cooldown_hours`) are
  static bounded defaults for this contract. They are not runtime
  user-configurable.
- This policy is intentionally non-live: passing this policy gate does not imply
  live-trading readiness or broker execution approval.

## Out-of-Scope Reminder

This policy contract does not cover:

- live order routing
- broker APIs or broker execution approval
- portfolio optimization engines
- broad strategy redesign
- UI-driven trade submission workflows
- backtesting or historical simulation outside bounded paper scope

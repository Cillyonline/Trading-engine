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

1. **Eligibility check** - required signal fields must be present and valid.
2. **Score threshold check** - signal score must meet the minimum threshold.
3. **Duplicate-entry check** - no duplicate open position may exist.
4. **Cooldown check** - minimum cooldown between entries must be satisfied.
5. **Exposure check** - position and exposure limits must not be exceeded.
   This step includes deterministic trade-level sizing from account equity,
   max risk per trade, and bounded `trade_risk_pct`.

Step 5 is evaluated through the canonical deterministic risk framework via one
bounded adapter path:

- Evaluator: `src/cilly_trading/risk_framework/risk_evaluator.py`
- Adapter: `src/cilly_trading/engine/risk/gate.py`
- Worker call-site: `src/cilly_trading/engine/paper_execution_worker.py`

This keeps bounded paper decisions aligned with canonical
account/strategy/symbol exposure semantics for equivalent bounded inputs.

A signal that fails any step produces an explicit outcome:

- **eligible**: signal passes all checks and may become a paper trade.
- **skip**: signal does not satisfy a soft rule; it is silently bypassed for this
  evaluation cycle.
- **reject**: signal violates a hard rule; it is blocked with an explicit reason
  code that must be logged.

## Paper Execution Risk Profile Contract (P57-RISK)

Bounded paper execution risk inputs are governed by one canonical validated
contract:

- `src/cilly_trading/engine/paper_execution_risk_profile.py`
- contract id: `paper-execution-risk-profile-v1`

The contract validates all bounded profile inputs fail-closed before execution
begins. Invalid values raise explicit errors (for example, out-of-range
percentages, non-positive limits, or non-finite numeric values), and execution
does not proceed with implicit defaults.

Validated by this contract:

- score threshold bounds (`0.0..100.0`)
- bounded exposure percentages (`(0, 1]`)
- bounded concurrency/cooldown limits
- bounded paper quantity, fallback entry price, and account equity (> `0`)

Not claimed by this contract:

- live-trading readiness
- broker integration readiness
- production-readiness approval

P56 alignment note: this contract hardens paper-execution input governance for
runtime determinism. It does not duplicate the existing P56 adverse-scenario
matrix scope in `docs/architecture/risk/p56-bounded-adverse-scenario-matrix.md`.

## Eligibility Rules

A signal is ineligible (rejected) if any required field is absent or invalid:

| Field | Requirement |
| --- | --- |
| `symbol` | Non-empty string instrument identifier. |
| `strategy` | Non-empty string key matching a known governed strategy. |
| `direction` | Must be `long` or `short`. |
| `score` | Numeric value; must be present and within `[0.0, 100.0]`. |
| `timestamp` | Parseable ISO-8601 datetime string. |
| `stage` | Must be non-empty and a recognized stage value such as `setup`. |

A signal missing any required field, or with a field value outside its allowed
boundary, is **rejected** with outcome code `reject:invalid_signal_fields`.

## Score Threshold Rules

Signals are subject to a minimum score threshold before paper entry is allowed:

- The default minimum score threshold is `60.0` (inclusive) on a `[0.0, 100.0]`
  scale.
- Signals with `score < 60.0` are **skipped** with outcome code
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

### Deterministic trade-level sizing (Issue #981)

Before exposure-cap checks are evaluated, paper-entry sizing is computed in a
fail-closed deterministic function:

- required input: `trade_risk_pct` on the signal candidate
- bounded risk input: `trade_risk_pct` is clamped to
  `[min_trade_risk_pct, max_trade_risk_pct]`
- risk budget: `account_equity * max_risk_per_trade_pct`
- proposed notional: `risk_budget_notional / bounded_trade_risk_pct`
- deterministic rounding: configured notional quantum with `ROUND_HALF_UP`

Fail-closed outcomes:

- missing trade-risk input -> `reject:missing_trade_risk_input`
- invalid trade-risk input -> `reject:invalid_trade_risk_input`
- rounded sizing that breaches max risk per trade ->
  `reject:max_risk_per_trade_exceeded`

Sizing and cap-evaluation inputs are exposed in non-UI worker decision
artifacts (`SignalEvaluationResult.decision_inputs`) for deterministic
inspection.

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
- This outcome maps to the canonical risk-framework account-exposure rule
  (`max_account_exposure_pct`) through the bounded execution adapter.

### Strategy exposure limit

- Strategy aggregate exposure is evaluated by the canonical risk-framework rule
  `max_strategy_exposure_pct`.
- A signal blocked by this rule is **rejected** with outcome code
  `reject:strategy_exposure_exceeds_limit`.

### Symbol exposure limit

- Symbol aggregate exposure is evaluated by the canonical risk-framework rule
  `max_symbol_exposure_pct`.
- A signal blocked by this rule is **rejected** with outcome code
  `reject:symbol_exposure_exceeds_limit`.

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
| Reject | `reject:missing_trade_risk_input` | Required bounded trade-risk input is missing. |
| Reject | `reject:invalid_trade_risk_input` | Required bounded trade-risk input is invalid. |
| Reject | `reject:max_risk_per_trade_exceeded` | Rounded deterministic size breaches max risk per trade. |
| Reject | `reject:total_exposure_exceeds_limit` | Proposed position would push total exposure over global cap. |
| Reject | `reject:strategy_exposure_exceeds_limit` | Proposed position would push strategy exposure over strategy cap. |
| Reject | `reject:symbol_exposure_exceeds_limit` | Proposed position would push symbol exposure over symbol cap. |
| Reject | `reject:concurrent_position_limit_exceeded` | Maximum concurrent open positions would be exceeded. |
| Reject | `reject:risk_kill_switch_enabled` | Canonical risk-framework kill-switch is enabled. |

**Skip** outcomes indicate a valid signal that does not satisfy a soft entry
rule. The signal is not an error; it is silently bypassed for this evaluation
cycle.

**Reject** outcomes indicate a hard policy violation. The signal is blocked with
an explicit reason code. The reason code must be logged for operator review.

Risk decision reason codes are deterministic and adapter-driven (for example
`rejected:risk_framework_max_account_exposure_pct_exceeded`), so equivalent
bounded inputs produce equivalent approve/reject reasons across covered
non-live execution paths.

Issue #981 completion is technical implementation evidence only. It does not
claim trader validation, trader approval of thresholds, live readiness, or
broker readiness.

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

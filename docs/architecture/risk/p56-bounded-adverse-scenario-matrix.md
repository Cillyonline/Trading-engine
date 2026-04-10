# P56-RISK: Bounded Adverse Scenario Matrix (Current Framework Behavior)

## Purpose
This artifact validates currently implemented bounded risk behavior under explicit adverse scenarios.

It does not introduce new risk architecture, does not redesign strategy behavior, and does not claim live-trading readiness.

## Scope of Validation
- Drawdown trigger behavior
- Daily-loss trigger behavior
- Kill-switch enforcement behavior
- Blocked execution path after guard breach
- Recovery/non-recovery behavior exactly as currently implemented

## Bounded Adverse Scenario Matrix

| Scenario ID | Adverse setup | Guard inputs | Expected execution outcome | Expected semantics |
| --- | --- | --- | --- | --- |
| `P56-S1` | Equity drawdown exceeds configured threshold (`peak=100000`, `current=85000`, threshold `0.10`) | `execution.drawdown.max_pct=0.10` | Blocked | `drawdown_shutdown_active`; adapter must not execute |
| `P56-S2` | Daily loss exceeds configured limit (`start_of_day=100000`, `current=98800`, loss `1200`) | `execution.daily_loss.max_abs=1000` | Blocked | `daily_loss_guard_active`; adapter must not execute |
| `P56-S3` | Kill switch active with no drawdown/daily-loss breach | `execution.kill_switch.active=true` | Blocked | `global_kill_switch_active`; adapter must not execute |
| `P56-S4` | Guard breach occurs and execution path is attempted | Any blocking guard active | Blocked | Execution adapter path remains blocked (`adapter_called == false`) |
| `P56-S5` | Drawdown breached then equity recovers below threshold breach | First: breached, then `current=95000` with same peak/threshold | First blocked, then allowed | Drawdown block can recover when current state no longer exceeds threshold |
| `P56-S6` | Daily-loss breached then loss recovers within limit | First: loss breached, then `current=99500` with same day start/limit | First blocked, then allowed | Daily-loss block can recover when current state no longer breaches configured max loss |
| `P56-S7` | Kill switch remains active across repeated attempts | `execution.kill_switch.active=true` | Repeatedly blocked | Non-recovery while switch remains true; recovery only after explicit config switch-off |

## Explicit Expected Outcome Semantics
- A trigger is considered breached only when the implemented guard predicate returns `True`.
- When any guard breach blocks execution, the execution adapter path is not invoked.
- Kill switch enforcement in runtime gate has explicit deterministic block semantics when runtime gate is reached.
- Drawdown and daily-loss behavior are state-driven and can recover when later state no longer breaches configured limits.
- Kill switch behavior is config-driven and remains blocked until switched off.

## What Is Validated
- Deterministic bounded guard behavior for drawdown, daily loss, and kill switch.
- Deterministic blocked execution path after guard breach.
- Recovery/non-recovery behavior only for currently implemented state/config semantics.

## Out of Scope / Not Claimed
- No new risk subsystem or architecture changes.
- No strategy redesign.
- No live trading behavior.
- No broker integration behavior.
- No production-readiness claim.
- No claim of complete risk maturity beyond these bounded scenarios.

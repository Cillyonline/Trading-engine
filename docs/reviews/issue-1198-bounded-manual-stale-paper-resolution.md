# Issue #1198 Bounded Manual Stale Paper Resolution

Active issue: #1198 - [DO NOW][PAPER-RUNTIME][PAPER-STATE] Define bounded manual resolution for stale TURTLE paper trades

## Scope

This artifact records a bounded manual-resolution decision for the stale open TURTLE paper trades before #1060 resumes.

This review is read-only and non-mutating. It does not close, reset, force, mark, or otherwise alter paper state. It does not change thresholds, strategy logic, score semantics, risk defaults, broker/live behavior, or historical #1060 evidence.

## Evidence Reviewed

- Preserved #1060 evidence summarized in `docs/reviews/issue-1186-review-data.md`.
- Trade-cycle lifecycle review in `docs/reviews/issue-1188-trade-cycle-paper-state-lifecycle.md`.
- Read-only local SQLite inspection of `cilly_trading.db` using a read-only connection.
- Read-only inspection of bounded paper inspection and reconciliation code paths:
  - `src/api/services/paper_inspection_service.py`
  - `scripts/run_daily_bounded_paper_runtime.py`
  - `scripts/run_post_run_reconciliation.py`
  - `scripts/run_paper_execution_cycle.py`

## Before-Action Reconciliation Status

Preserved #1060 Run 10 / Run 11 evidence:

```text
reconciliation_ok: true
mismatches: 0
orders: 3
trades: 3
positions: 3
open_trades: 3
open_positions: 3
closed_trades: 0
execution_events: 9
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
duplicate_entry_blocker_count: 3
stale duplicate-entry blockers:
  COST / TURTLE / long
  GS / TURTLE / long
  WMT / TURTLE / long
```

Local read-only database inspection:

```text
db_path: C:\repos\Trading-engine\cilly_trading.db
orders: 0
execution_events: 0
trades: 0
positions: 0
open_trades: 0
open_positions: 0
closed_trades: 0
paper_account.cash: 100000
paper_account.equity: 100000
paper_account.as_of: null
reconciliation_ok: true
mismatches: 0
target_trades_present_locally: false
```

Interpretation: the stale-trade blocker evidence is preserved VPS/runtime evidence from #1060 and related reviews. The current local DB snapshot does not contain the target trades, so it is not used as proof that the VPS stale trades have been resolved.

## Per-Trade Resolution Decision

| Symbol | Strategy | Direction | Preserved evidence state | Decision | Rationale |
| --- | --- | --- | --- | --- | --- |
| COST | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`, stale duplicate-entry blocker, no closed-trade evidence | `deferred_no_mutation` | Reconciliation is clean, but no operator authorization exists for close/reset/mutation. |
| GS | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`, stale duplicate-entry blocker, no closed-trade evidence | `deferred_no_mutation` | Reconciliation is clean, but no operator authorization exists for close/reset/mutation. |
| WMT | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`, stale duplicate-entry blocker, no closed-trade evidence | `deferred_no_mutation` | Reconciliation is clean, but no operator authorization exists for close/reset/mutation. |

## Operator Authorization Status

No explicit operator authorization was provided for a paper-state mutation.

Authorized actions in this issue:

- Create this bounded read-only review artifact.
- Record before-action evidence.
- Record per-trade resolution decisions.
- Record mutation status and #1060 recommendation.
- Run repository tests.

Not authorized:

- Closing any paper trade.
- Resetting paper account, trade, or position state.
- Forcing new paper trades.
- Marking stale positions to market.
- Changing strategy thresholds or strategy logic.
- Changing broker/live behavior.
- Mutating #1060 historical evidence.

## Exact Command If Action Is Proposed

No mutating action is proposed in this artifact.

If an operator later authorizes a mutation, the exact command must be defined in a separate authorized issue or operator instruction after first capturing fresh read-only evidence for:

- target environment
- target database path
- target trade IDs
- current paper account
- current paper trades
- current paper positions
- current reconciliation status
- intended mutation type

No close/reset/force command is inferred from #1198.

## After-Action Reconciliation Status

No action was authorized or executed.

```text
after_action_reconciliation_status: not_applicable_no_action_executed
after_action_reconciliation_ok: not_applicable
after_action_mismatches: not_applicable
```

## Mutation Status

```text
mutates_paper_state: false
paper_trade_closed: false
paper_state_reset: false
forced_trade_created: false
thresholds_changed: false
strategy_logic_changed: false
broker_live_behavior_changed: false
issue_1060_historical_evidence_mutated: false
```

No mutation was performed.

## Recommendation For #1060

Keep #1060 paused until one of the following is completed:

1. A fresh read-only capture from the actual target paper runtime proves the stale `COST`, `GS`, and `WMT` TURTLE long trades are no longer present and reconciliation remains clean.
2. The operator explicitly authorizes a bounded manual paper-state resolution action in a separate instruction or issue with exact target trade IDs, target environment, target DB path, and required before/after reconciliation capture.
3. A bounded lifecycle implementation issue resolves whether exit-stage signals are routed to paper exit handling for matching open paper trades and produces deterministic evidence.

Do not resume #1060 unchanged against the stale duplicate-entry blocker state recorded in the preserved #1060 evidence.

## Explicit No-Change Statement

This issue does not change thresholds, score semantics, strategy logic, risk defaults, broker/live behavior, forced-trade behavior, paper execution defaults, or #1060 historical evidence.

This artifact does not introduce live trading, broker execution, production readiness, trader validation, profitability evidence, auto-close behavior, auto-reset behavior, or forced paper-trade creation.

## Risk Notes

- The current local `cilly_trading.db` does not contain the target stale trades, so it cannot independently prove that the stale VPS/runtime paper state has been resolved.
- Preserved #1060 Run 10/11 evidence remains the durable source for the stale `COST`, `GS`, and `WMT` duplicate-entry blockers.
- Continuing #1060 unchanged risks producing additional technically clean `no_eligible` runs while leaving the same stale paper-state blocker unresolved.
- Manual mutation without explicit operator authorization, target trade IDs, and before/after reconciliation evidence would violate #1198 boundaries.

## Out-Of-Scope Notes

- No source code changes.
- No script changes.
- No test changes.
- No database changes.
- No paper-state cleanup.
- No trade close/reset.
- No forced trade.
- No threshold or strategy adjustment.
- No broker/live behavior change.
- No #1060 historical evidence mutation.

## Follow-Up Issues

Recommended follow-up if the target runtime still contains the stale open paper trades:

```text
[PAPER-STATE][MANUAL] Authorize exact bounded resolution for stale COST/GS/WMT TURTLE paper trades
```

The follow-up should include exact target environment, DB path, trade IDs, intended action, before-action reconciliation evidence, operator authorization, exact command, and mandatory after-action reconciliation evidence.

Recommended follow-up if the owner wants runtime lifecycle closure instead of manual cleanup:

```text
[PAPER-RUNTIME] Wire or explicitly reject bounded exit-signal consumption for open paper trades
```

That follow-up should preserve strategy logic, thresholds, risk defaults, broker/live boundaries, and existing paper state unless an operator separately authorizes a mutation.

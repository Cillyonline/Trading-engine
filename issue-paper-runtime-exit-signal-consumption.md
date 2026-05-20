## Goal

Resolve the bounded paper-runtime lifecycle gap found by #1188 before #1060 is resumed.

Decide whether the bounded paper-runtime cycle should route exit-stage signals to BoundedPaperExecutionWorker.process_exit_signal() for matching open paper trades, or explicitly reject/document that exit-stage signals are not consumed by the bounded paper-runtime cycle.

## Context

This issue follows #1183, #1186, and #1188.

#1183 preserved the baseline-first strategy policy and blocks strategy, threshold, score, risk-default, broker/live, profitability, and trader-validation changes during the baseline evidence window.

#1186 diagnosed the repeated #1060 no_eligible pattern as technically stable but traderically weak.

#1188 confirmed that process_exit_signal() exists as a component-level paper-exit capability, but the active #1060 bounded runtime/batch path is not evidenced to route exit-stage signals into that capability. Exit-stage signals in the active runtime path are classified as skip:exit_signal_not_entry_candidate. Stale open TURTLE long paper trades for COST, GS, and WMT remain stale-and-blocking.

#1060 remains paused until this issue is resolved.

## Scope

Resolve whether bounded paper-runtime exit-stage signal consumption should be wired or explicitly rejected.

Allowed outcome A:
Wire bounded runtime-cycle exit-stage signals to process_exit_signal() for matching open paper trades, with deterministic tests and evidence output.

Allowed outcome B:
Explicitly reject/document exit-stage signal consumption in the bounded runtime cycle and keep #1060 paused until a separate cleanup/operator-review path is authorized.

## Acceptance Criteria

1. Determine whether exit-stage signals in the bounded paper-runtime cycle should be routed to process_exit_signal() or explicitly rejected.
2. If routing is implemented, route only matching open paper trades by strategy, symbol, direction, and open status.
3. If routing is implemented, preserve idempotency so repeated runs do not duplicate closes, orders, or execution events.
4. If routing is implemented, produce deterministic evidence for full exit, partial exit, no matching open position, repeated-run idempotency, and resulting paper-state changes.
5. If routing is rejected, document the bounded runtime contract clearly and keep #1060 paused pending separate cleanup/operator-review authorization.
6. Preserve RSI2 and TURTLE strategy logic, score semantics, thresholds, entry rules, exit strategy rules, risk defaults, broker/live boundaries, and non-profitability boundaries.
7. Do not mutate existing production/VPS paper state during tests or implementation.
8. Do not manually close, reset, or clean stale COST, GS, or WMT paper trades in this issue.
9. Add or update deterministic tests covering the selected decision path.
10. Update operator/runtime documentation only as needed to describe the selected bounded lifecycle behavior.
11. Clearly separate technically implemented, operationally usable, and traderically validated.
12. Do not claim trader validation, profitability, broker readiness, live readiness, or production readiness.

## Files Likely In Scope

- src/cilly_trading/engine/paper_execution_worker.py
- scripts/run_paper_execution_cycle.py
- scripts/run_daily_bounded_paper_runtime.py
- tests/engine/test_paper_execution_worker.py
- tests/test_run_daily_bounded_paper_runtime_script.py
- relevant runtime/operator documentation if needed

## Out of Scope

- strategy optimization
- new strategies
- RSI2/TURTLE strategy logic changes
- score/rating recalibration
- threshold tuning
- risk-profile tuning
- broker integration
- live trading
- manual or automatic cleanup of existing VPS paper state
- profitability claims
- trader-validation claims
- production-readiness claims

## Required Return Package

- SUMMARY
- MODIFIED FILES
- NEW FILES
- DELETED FILES
- FILE CONTENTS
- TEST COMMAND
- FULL TEST OUTPUT
- RISK NOTES
- OUT OF SCOPE
- FOLLOW-UP ISSUES

## Governance

#1060 remains paused while this issue is active.

No PR may be marked Ready for Review and no merge may occur without Codex A APPROVED.

Classification target:
- technically implemented: determined by code/tests/evidence
- operationally usable: determined by bounded runtime/operator behavior
- traderically validated: not claimed by this issue


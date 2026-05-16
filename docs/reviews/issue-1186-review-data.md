# Issue #1186 Review Data

Active issue: #1186 - [DO NOW][VALIDATION][TRADER-QUALITY] Diagnose repeated no-eligible blockers before resuming #1060

Review-data file purpose: durable approval-grade evidence package for Codex A verification.

Read-only boundary: #1186 is diagnostic and governance-bound. This file is the only repository file created for #1186. No source code, strategy logic, threshold/default configuration, broker/live execution code, destructive paper-state mutation/reset code, roadmap/governance file, or #1060 historical evidence was changed.

## Acceptance Criteria Trace

1. Repeated `no_eligible` pattern diagnosed using #1060 run evidence and repository/runtime evidence.
2. Duplicate-entry blockers for `COST`, `GS`, and `WMT` traced to current paper-state evidence.
3. `account_as_of` staleness classified.
4. `exit_signal_not_entry_candidate` dominance explained using signal stage/classification behavior.
5. `score_below_threshold` outcomes summarized without changing thresholds or semantics.
6. Technically implemented, operationally usable, and traderically validated are separated.
7. Recommendation for next active implementation issue is provided.
8. No source-code change made for #1186.
9. No live-trading, broker-readiness, production-readiness, trader-validation, or profitability claim introduced.

## Evidence Reviewed

### GitHub Issues

- #1186 issue body and acceptance criteria.
- #1060 issue body and run comments, especially Run 1, Run 2, Run 10, and Run 11.
- #1168: prior no-eligible investigation.
- #1169: paper state freshness and open-trade lifecycle evidence.
- #1170: stop-distance sizing / risk-input contract alignment.
- #1171: risk-profile activation evidence.
- #1175: bounded stale open paper-trade operator review workflow.
- #1089: explicit RSI2/TURTLE exit logic.
- #1049: bounded per-strategy score calibration evidence.
- #1183: baseline-first strategy improvement decision.

### Repository Evidence

Read-only inspected files and behavior:

- `AGENTS.md`: issue-governance and read-only/allowed-files constraints.
- `src/cilly_trading/engine/paper_execution_worker.py`: stage classification and score-threshold policy ordering.
- `tests/engine/test_paper_execution_worker.py`: tests for score threshold and exit-stage classification.
- `scripts/run_daily_bounded_paper_runtime.py`: evidence builders for risk activation, paper-state freshness, stale-trade workflow, and run-quality classification.
- `scripts/validation/summarize_bounded_paper_runtime_evidence.py`: offline read-only evidence summarizer contract.
- `docs/operations/runtime/p60-signal-to-paper-operator-path.md`: bounded signal-to-paper operator policy.
- `docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md`: `no_eligible` run-quality classification and operator action contract.
- `docs/operations/runtime/bounded-paper-runtime-evidence-series-runbook.md`: run-series classification boundary and non-live claims.

### Local Runtime Evidence

Local SQLite inspection was read-only. Current local `cilly_trading.db` contains the relevant tables but no current rows in `signals`, `core_trades`, `core_orders`, `core_execution_events`, or legacy `trades`. Therefore current blocker diagnosis relies on #1060 VPS runtime evidence and related GitHub issue evidence rather than local DB contents.

Observed local table counts:

```text
core_trades: 0
core_orders: 0
core_execution_events: 0
trades: 0
signals: 0
```

## Exact #1060 Evidence Reviewed

### Run 1 Evidence

From #1060 Run 1 recorded comment:

```text
status: ok
run_quality_status: no_eligible
operator_action: review_required
completed_at: 2026-04-28T18:55:50+00:00
ingestion_run_id: 716e5b67-b5c7-4d99-a192-10c561e3e8b3
analysis_run_id: e04d814e5fd5c9b008745f00fe01cc20bd888c7ff79c07cce47eb0e1a0cb0b6c
signals_read: 12
eligible: 0
skipped: 12
rejected: 0
skip reasons:
  duplicate_entry: 3
  score_below_threshold: 9
reconciliation_ok: true
mismatches: 0
orders: 3
trades: 3
positions: 3
open_trades: 3
open_positions: 3
evidence_capture.all_valid: true
summary_file: /app/runs/daily-runtime/2026-04-28/daily-runtime-summary-20260428T185543Z.json
paper_execution_evidence: /app/runs/paper-execution/paper-execution-no-eligible-20260428T185548Z.json
reconciliation_evidence: /app/runs/reconciliation/reconciliation-pass-20260428T185549Z.json
```

Run 1 classification evidence:

```text
Run 1 is technically valid and operationally useful as bounded evidence. It is not trader validation and not profitability evidence.
```

### Run 2 Evidence

From #1060 Run 2 recorded comment:

```text
status: ok
run_quality_status: no_eligible
operator_action: review_required
completed_at: 2026-04-29T11:35:21+00:00
ingestion_run_id: 3572ee05-a71b-4218-aa7a-3ae8caf57620
analysis_run_id: 442bd26350f73fffb009aa3f3a35c06357d1951358e3fb6f2afef7eb166475e9
signals_read: 12
eligible: 0
skipped: 12
rejected: 0
skip reasons:
  duplicate_entry: 3
  score_below_threshold: 9
reconciliation_ok: true
mismatches: 0
orders: 3
trades: 3
positions: 3
open_trades: 3
open_positions: 3
evidence_capture.all_valid: true
summary_file: /app/runs/daily-runtime/2026-04-29/daily-runtime-summary-20260429T113513Z.json
paper_execution_evidence: /app/runs/paper-execution/paper-execution-no-eligible-20260429T113518Z.json
reconciliation_evidence: /app/runs/reconciliation/reconciliation-pass-20260429T113520Z.json
```

Run 2 pattern note:

```text
Run 1 and Run 2 both produced no_eligible with the same skip distribution: 3 duplicate entries and 9 score-below-threshold outcomes. This is not a failure, but it is a pattern to review after more independent runs.
```

### Run 10 Evidence

From #1060 Run 10 recorded comment:

```text
status: ok
run_quality_status: no_eligible
operator_action: review_required
completed_at: 2026-05-15T20:42:39+00:00
ingestion_run_id: 86b88677-2545-4ad9-8d3b-d18605def6b1
analysis_run_id: 1822b9e281242794ac2b2859407089ef400a4669815fb855c3aa7a48c5820a4a
summary_file: /app/runs/daily-runtime/2026-05-15/daily-runtime-summary-20260515T204231Z.json
dataset_end_timestamp: 2026-05-14T00:00:00+00:00
signals_read: 28
eligible: 0
skipped: 28
rejected: 0
new paper trades created: 0
skip:exit_signal_not_entry_candidate: 16
skip:duplicate_entry: 3
skip:score_below_threshold: 9
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
open_trade_count: 3
duplicate_entry_blocker_count: 3
review_required_count: 3
stale duplicate-entry blockers:
  COST / TURTLE / long
  GS / TURTLE / long
  WMT / TURTLE / long
workflow_id: ops_bounded_stale_open_paper_trade_review
workflow_status: review_required
read_only: true
mutates_paper_state: false
reconciliation_ok: true
mismatches: 0
orders: 3
trades: 3
positions: 3
open_trades: 3
open_positions: 3
closed_trades: 0
execution_events: 9
evidence_capture.all_valid: true
```

Run 10 risk-control activation evidence:

```text
score threshold gate: active, applied 12, blocked 9
duplicate-entry gate: active, applied 3, blocked 3
stop-distance sizing: active/configured, applied 0 because no candidate reached sizing
commission model: active/configured, applied 0 because no fills occurred
slippage model: active/configured, applied 0 because no fills occurred
exposure limits: active/configured, applied 0
max concurrent positions: active/configured, applied 0
correlation gate: inactive because correlation_check_enabled=false
drawdown guard: inactive because drawdown_guard_enabled=false
regime filter: inactive because allowed_regimes is empty
```

Run 10 classification evidence:

```text
Run 10 is a completed bounded paper-runtime cycle.
Classification: technically good, but traderically weak.
It is operationally useful for runtime/reconciliation/stale-state evidence hygiene and confirms the operator-review artifact contract remains stable on VPS. It is not trader validation, not profitability evidence, not broker readiness, not live-readiness, and not production-readiness evidence.
```

### Run 11 Evidence

From #1060 Run 11 recorded comment:

```text
status: ok
run_quality_status: no_eligible
operator_action: review_required
completed_at: 2026-05-16T07:28:06+00:00
ingestion_run_id: 24756425-5baf-4b8a-ba08-1712efd232c6
analysis_run_id: 3c5859e40ca20d099dcbe90ebafde9c262a262c4f24cf38a10a06da11d4270e6
summary_file: /app/runs/daily-runtime/2026-05-16/daily-runtime-summary-20260516T072759Z.json
dataset_end_timestamps: ['2026-05-15T00:00:00+00:00']
target: 2026-05-15T00:00:00+00:00
FRESHNESS_TARGET_MATCH= True
signals_read: 29
eligible: 0
skipped: 29
rejected: 0
new paper trades created: 0
skip:exit_signal_not_entry_candidate: 17
skip:duplicate_entry: 3
skip:score_below_threshold: 9
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
open_trade_count: 3
duplicate_entry_blocker_count: 3
review_required_count: 3
stale duplicate-entry blockers:
  COST / TURTLE / long
  GS / TURTLE / long
  WMT / TURTLE / long
workflow_id: ops_bounded_stale_open_paper_trade_review
workflow_status: review_required
read_only: true
mutates_paper_state: false
reconciliation_ok: true
mismatches: 0
orders: 3
trades: 3
positions: 3
open_trades: 3
open_positions: 3
closed_trades: 0
execution_events: 9
evidence_capture.all_valid: true
```

Run 11 risk-control activation evidence:

```text
score threshold gate: active, applied 12, blocked 9
duplicate-entry gate: active, applied 3, blocked 3
stop-distance sizing: active/configured, applied 0 because no candidate reached sizing
commission model: active/configured, applied 0 because no fills occurred
slippage model: active/configured, applied 0 because no fills occurred
exposure limits: active/configured, applied 0
max concurrent positions: active/configured, applied 0
correlation gate: inactive because correlation_check_enabled=false
drawdown guard: inactive because drawdown_guard_enabled=false
regime filter: inactive because allowed_regimes is empty
```

Run 11 series status evidence:

```text
numbered_attempts: 11
completed_bounded_cycles: 10 / 20 minimum
healthy: 0
no_eligible: 10
degraded: 0
operational degraded attempts recorded separately: Run 5 degraded pre-execution attempt: 1
10/10 completed cycles classified as no_eligible
no new paper trades created
reconciliation stable with mismatches=0
stale paper state unchanged for COST, GS, and WMT
stale duplicate-entry blockers remain stable at 3
score-below-threshold candidates remain stable at 9
exit-stage signals have increased to the dominant skip reason
```

Run 11 classification evidence:

```text
Run 11 is a completed bounded paper-runtime cycle.
Classification: technically good, but traderically weak.
It is operationally useful for runtime/reconciliation/stale-state evidence hygiene and confirms the operator-review artifact contract remains stable on VPS. It is not trader validation, not profitability evidence, not broker readiness, not live-readiness, and not production-readiness evidence.
```

## Exact Related-Issue Evidence Reviewed

### #1169 Paper-State Blockers

#1169 context traced the duplicate-entry blockers to open persisted `TURTLE` trades:

```text
WMT / TURTLE / long / opened_at=2026-04-02T00:00:00+00:00 / status=open
GS  / TURTLE / long / opened_at=2026-04-02T00:00:00+00:00 / status=open
COST / TURTLE / long / opened_at=2026-04-02T00:00:00+00:00 / status=open
```

#1169 classified the behavior as technically valid against DB state but operationally suspicious for validation because account state remains anchored to `as_of=2026-04-02T00:00:00+00:00`, all three trades remain open, and no current mark-to-market or exit-lifecycle evidence is visible in the daily runtime summary.

### #1170 Exit Signal / Risk-Input Contract

#1170 clarified that exit signals are not treated as entry-sizing candidates unless explicitly supported by the paper execution contract. It also clarified missing risk-input classification for stop-distance sizing. Current Run 10/11 evidence no longer shows missing-risk-input as a dominant latest blocker; it shows exit-stage and stale duplicate-entry blockers plus score filtering.

### #1171 Risk Activation

#1171 added explicit risk-control activation evidence. Run 10/11 use that evidence to show score threshold and duplicate-entry gates are active/applied/blocking, while correlation, drawdown, and regime controls are implemented but inactive by configuration.

### #1175 Stale Open Paper-Trade Review Workflow

#1175 added bounded read-only stale open paper-trade review workflow. Run 10/11 confirm the workflow remains non-mutating with `read_only=true` and `mutates_paper_state=false`.

### #1183 Baseline-First Decision

#1183 says to keep RSI2/TURTLE strategy behavior, scoring behavior, paper execution defaults, and risk profile defaults unchanged during the active baseline evidence window unless a true technical blocker is found. #1186 did not find a direct source-code defect requiring changes under the diagnostic issue; it found that continuing #1060 unchanged is trader-evidence weak.

## Signal Stage / Classification Behavior

Repository behavior from `BoundedPaperExecutionWorker._evaluate()`:

```text
Policy order:
1. required signal field validation
2. if stage == "exit", return skip:exit_signal_not_entry_candidate
3. score threshold gate
4. duplicate-entry gate
5. cooldown
6. entry-zone fill
7. regime filter
8. drawdown guard
9. trade sizing
10. exposure, max concurrent, correlation checks
```

Exact exit-stage behavior:

```text
if stage == "exit":
    reason = "exit signal is not an entry-sizing candidate"
    outcome = "skip:exit_signal_not_entry_candidate"
```

Test evidence:

```text
tests/engine/test_paper_execution_worker.py::test_exit_signal_processed_as_entry_candidate_is_classified_before_sizing
assert result.outcome == "skip:exit_signal_not_entry_candidate"
assert result.reason == "exit signal is not an entry-sizing candidate"
```

Conclusion: the dominance of `skip:exit_signal_not_entry_candidate` in Run 10/11 is explained by current signal-stage classification behavior. It is expected contract behavior, not a proven implementation defect.

## Score Filtering Behavior

Repository behavior:

```text
if score < self._risk_profile.min_score_threshold:
    outcome = "skip:score_below_threshold"
    reason = "score=<score> < min_score_threshold=<threshold>"
```

Test evidence:

```text
tests/engine/test_paper_execution_worker.py::test_score_below_threshold_is_skipped
tests/engine/test_paper_execution_worker.py::test_score_exactly_at_threshold_is_eligible
tests/engine/test_paper_execution_worker.py::test_score_above_threshold_is_eligible
tests/engine/test_paper_execution_worker.py::test_midrange_score_is_not_rejected_as_invalid_field
```

Run 10/11 evidence:

```text
skip:score_below_threshold: 9
score threshold gate: active, applied 12, blocked 9
```

Conclusion: score filtering is stable and expected conservative behavior. No threshold or score-semantic change was made or recommended inside #1186.

## Account Freshness Evidence

Run 10/11 evidence:

```text
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
open_trade_count: 3
duplicate_entry_blocker_count: 3
review_required_count: 3
```

Conclusion: account state is stale, operationally visible, and trader-evidence limiting. It is technically handled by the evidence workflow, but it makes continuing #1060 unchanged weak because the same stale paper-state blockers keep suppressing new paper entries.

## Diagnostic Classification

Current blocker pattern includes:

- stale paper state: yes
- duplicate-entry protection: yes
- exit-signal classification: yes
- score threshold filtering: yes
- risk-input contract limitation: not dominant in latest Run 10/11 evidence; prior #1170 addressed this evidence path
- insufficient signal quality: yes, bounded classification only; current entry candidates are score-blocked or duplicate-blocked, while current signal flow is dominated by exit-stage non-entry signals
- expected conservative behavior: yes, technically
- implementation gap: not proven as a current code defect in #1186; the gap is operational/trader-evidence quality and trade-cycle validation

## Technically Implemented / Operationally Usable / Traderically Validated

Technically implemented:

- The bounded daily runner executes.
- Run-quality classification is deterministic.
- `no_eligible` is treated as bounded non-error completion when reconciliation is clean.
- Reconciliation remains clean with `mismatches=0`.
- Stale paper state is visible in evidence.
- Stale open paper-trade review workflow exists and is read-only.
- Risk-control activation evidence distinguishes active/applied/blocking vs inactive controls.
- Exit-stage signals are classified before entry sizing.

Operationally usable:

- Usable for runtime stability evidence.
- Usable for reconciliation hygiene.
- Usable for stale paper-state review.
- Usable for evidence contract verification.
- Weak as a continued unchanged trader-quality evidence series because no new paper trades are created and stale blockers remain unchanged.

Traderically validated:

- No.
- 10/10 completed cycles are `no_eligible`.
- 0 new paper trades were created across the interim series.
- There is no completed trade-cycle evidence from this series.
- The evidence does not prove profitability, trader validation, broker readiness, live readiness, or production readiness.

## Recommendation For #1060

Keep #1060 paused. Do not resume unchanged.

Reason: continuing unchanged is likely to add more technically stable `no_eligible` observations without improving trader-quality insight. The current evidence already establishes the pattern: stale paper-state duplicate blockers remain, score-threshold blockers remain stable, exit-stage signals dominate, and no new paper trades are created.

## Follow-Up Issue Recommendation

Open a narrow trade-cycle validation / paper-state lifecycle issue before resuming #1060.

Recommended follow-up scope:

- Review the three stale open `TURTLE` paper trades for `COST`, `GS`, and `WMT`.
- Determine whether paper execution has a bounded, non-mutating path to consume exit-stage signals against open paper trades, or whether exit-stage signals are only backtest-facing today.
- Produce evidence that stale open trades are lifecycle-valid, externally reviewed, or require a separately authorized manual cleanup issue.
- Preserve thresholds, strategy logic, broker/live behavior, and paper-state mutation boundaries unless a separate authorized implementation issue explicitly permits changes.

If forced to choose one #1186 option, choose:

```text
keep #1060 paused and open a trade-cycle validation issue
```

A paper-state cleanup issue may follow only after lifecycle review proves cleanup is the correct bounded operator action.

## Risk Notes

- Local DB is not sufficient to independently reproduce VPS current blocker state because it has no relevant rows; the durable evidence is in #1060 comments and related issue context.
- Full pytest currently fails in this workspace. Because #1186 made no source-code changes, these failures are recorded as test evidence, not fixed inside this issue.
- The current worktree had pre-existing dirty changes before #1186 work began:
  - `scripts/run_daily_bounded_paper_runtime.py`
  - `tests/test_run_daily_bounded_paper_runtime_script.py`
  These were not modified for #1186.
- A prior `python -m pytest -q` attempt timed out and hit a Windows console `OSError: [Errno 22] Invalid argument`; the durable rerun below used UTF-8 settings and completed with test failure summary.
- Because #1186 is diagnostic/read-only, failure remediation is out of scope unless a narrower implementation issue is authorized.

## Out-of-Scope Notes

Not changed and not recommended inside #1186:

- strategy logic
- entry rules
- exit rules
- thresholds
- score semantics
- score calibration
- strategy optimization
- new strategies
- manual paper-state reset
- automatic paper-state reset
- auto-closing paper trades
- marking positions to market through mutation
- forcing eligible trades
- broker integration
- live trading
- production-readiness claims
- broker-readiness claims
- trader-validation claims
- profitability claims
- #1060 historical evidence

## Modified / New / Deleted Files

Modified files by #1186:

```text
none
```

New files by #1186:

```text
docs/reviews/issue-1186-review-data.md
```

Deleted files by #1186:

```text
none
```

## Exact Test Command

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; python -X utf8 -m pytest -q --tb=short
```

## Test Result Summary

```text
exit code: 1
36 failed, 1543 passed, 1 skipped, 1 warning
```

## Full Exact Test Output

```text
............................................................F........... [  4%]
.F................................................................F..... [  9%]
..........................F..F.F........................................ [ 13%]
........................................................................ [ 18%]
........................................................................ [ 22%]
........................................................................ [ 27%]
........................................................................ [ 31%]
........................................................................ [ 36%]
........................................................................ [ 41%]
........................................................................ [ 45%]
........................................................................ [ 50%]
...................................................................F.F.. [ 54%]
........F.....FFFFF.F....F............F..............F...F.............. [ 59%]
.FFFFFFFFF..FF....F..................................................... [ 63%]
........................................................................ [ 68%]
........................................................................ [ 72%]
.......................................................................s [ 77%]
........................................................................ [ 82%]
........................................................................ [ 86%]
...........FFFF......................................................... [ 91%]
........................................................................ [ 95%]
.............................................F......................     [100%]
================================== FAILURES ===================================
_______ test_operator_can_trigger_analysis_run_and_execution_is_logged ________
src\api\test_operator_analysis_trigger_api.py:78: in test_operator_can_trigger_analysis_run_and_execution_is_logged
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________________ test_system_state_endpoint_is_documented ___________________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\src\api\test_system_state_api.py", line 76, in test_system_state_endpoint_is_documented
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\src\api\test_system_state_api.py", line 76, in test_system_state_endpoint_is_documented
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
src\api\test_system_state_api.py:76: in test_system_state_endpoint_is_documented
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________ test_real_app_returns_request_id_in_validation_error_body __________
tests\api\test_exceptions_request_id.py:262: in test_real_app_returns_request_id_in_validation_error_body
    assert body["detail"] == "invalid_ingestion_run_id"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_________________ test_openapi_endpoint_returns_valid_schema __________________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\api\test_openapi_docs_endpoints.py", line 16, in test_openapi_endpoint_returns_valid_schema
    |     response = client.get("/api/openapi.json")
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\api\test_openapi_docs_endpoints.py", line 16, in test_openapi_endpoint_returns_valid_schema
    response = client.get("/api/openapi.json")
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\api\test_openapi_docs_endpoints.py:16: in test_openapi_endpoint_returns_valid_schema
    response = client.get("/api/openapi.json")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
___________________ test_openapi_export_script_writes_file ____________________
tests\api\test_openapi_docs_endpoints.py:47: in test_openapi_export_script_writes_file
    written = export_openapi(output)
              ^^^^^^^^^^^^^^^^^^^^^^
scripts\export_openapi.py:43: in export_openapi
    schema = app.openapi()
             ^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_________________ test_metrics_recorded_after_normal_request __________________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\api\test_prometheus_metrics.py", line 30, in test_metrics_recorded_after_normal_request
    |     ok = client.get("/api/openapi.json")
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\api\test_prometheus_metrics.py", line 30, in test_metrics_recorded_after_normal_request
    ok = client.get("/api/openapi.json")
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\api\test_prometheus_metrics.py:30: in test_metrics_recorded_after_normal_request
    ok = client.get("/api/openapi.json")
         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
______ test_backtest_entry_read_route_exposes_bounded_non_live_contract _______
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_backtest_entry_read.py", line 59, in test_backtest_entry_read_route_exposes_bounded_non_live_contract
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_backtest_entry_read.py", line 59, in test_backtest_entry_read_route_exposes_bounded_non_live_contract
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_backtest_entry_read.py:59: in test_backtest_entry_read_route_exposes_bounded_non_live_contract
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/backtest/artifacts "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____ test_decision_card_inspection_endpoint_is_exposed_and_schema_valid ______
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_decision_card_inspection_read.py", line 281, in test_decision_card_inspection_endpoint_is_exposed_and_schema_valid
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_decision_card_inspection_read.py", line 281, in test_decision_card_inspection_endpoint_is_exposed_and_schema_valid
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_decision_card_inspection_read.py:281: in test_decision_card_inspection_endpoint_is_exposed_and_schema_valid
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/decision-cards "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________________ test_execution_orders_api_contract ______________________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_execution_orders_read.py", line 54, in test_execution_orders_api_contract
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_execution_orders_read.py", line 54, in test_execution_orders_api_contract
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_execution_orders_read.py:54: in test_execution_orders_api_contract
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/execution/orders?limit=10&offset=0 "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_______________________ test_manual_analysis_idempotent _______________________
tests\test_api_manual_analysis_trigger.py:161: in test_manual_analysis_idempotent
    assert response_first.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________ test_manual_analysis_rejects_invalid_ingestion_run ______________
tests\test_api_manual_analysis_trigger.py:203: in test_manual_analysis_rejects_invalid_ingestion_run
    assert response.json()["detail"] == "invalid_ingestion_run_id"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________________ test_manual_analysis_uses_snapshot ______________________
tests\test_api_manual_analysis_trigger.py:267: in test_manual_analysis_uses_snapshot
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
____________ test_manual_analysis_changes_id_for_different_payload ____________
tests\test_api_manual_analysis_trigger.py:336: in test_manual_analysis_changes_id_for_different_payload
    assert response_first.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
____________ test_manual_analysis_strategy_config_float_idempotent ____________
tests\test_api_manual_analysis_trigger.py:403: in test_manual_analysis_strategy_config_float_idempotent
    assert response_first.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
___ test_manual_analysis_returns_persisted_result_when_duplicate_save_races ___
tests\test_api_manual_analysis_trigger.py:502: in test_manual_analysis_returns_persisted_result_when_duplicate_save_races
    assert first_response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
______________ test_paper_endpoints_are_exposed_and_schema_valid ______________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_paper_inspection_read.py", line 262, in test_paper_endpoints_are_exposed_and_schema_valid
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_paper_inspection_read.py", line 262, in test_paper_endpoints_are_exposed_and_schema_valid
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_paper_inspection_read.py:262: in test_paper_endpoints_are_exposed_and_schema_valid
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/workflow "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/trades "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/positions "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/account "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/reconciliation "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_ test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically _
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_paper_runtime_evidence_series_read.py", line 142, in test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_paper_runtime_evidence_series_read.py", line 142, in test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_paper_runtime_evidence_series_read.py:142: in test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/runtime/evidence-series "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/runtime/evidence-series "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________ test_signal_decision_surface_openapi_contract_is_explicit __________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_signal_decision_surface.py", line 286, in test_signal_decision_surface_openapi_contract_is_explicit
    |     response = client.get("/api/openapi.json")
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_signal_decision_surface.py", line 286, in test_signal_decision_surface_openapi_contract_is_explicit
    response = client.get("/api/openapi.json")
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_signal_decision_surface.py:286: in test_signal_decision_surface_openapi_contract_is_explicit
    response = client.get("/api/openapi.json")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_______ test_read_signals_openapi_exposes_timeframe_not_legacy_filters ________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_signals_read.py", line 95, in test_read_signals_openapi_exposes_timeframe_not_legacy_filters
    |     response = client.get("/api/openapi.json")
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_signals_read.py", line 95, in test_read_signals_openapi_exposes_timeframe_not_legacy_filters
    response = client.get("/api/openapi.json")
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_signals_read.py:95: in test_read_signals_openapi_exposes_timeframe_not_legacy_filters
    response = client.get("/api/openapi.json")
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
____________ test_strategy_analyze_accepts_valid_ingestion_run_id _____________
tests\test_api_snapshot_first_enforcement.py:184: in test_strategy_analyze_accepts_valid_ingestion_run_id
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_______________ test_strategy_analyze_rejects_missing_snapshot ________________
tests\test_api_snapshot_first_enforcement.py:229: in test_strategy_analyze_rejects_missing_snapshot
    assert response.json()["detail"] == "ingestion_run_not_ready"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________ test_strategy_analyze_rejects_invalid_snapshot_rows _____________
tests\test_api_snapshot_first_enforcement.py:278: in test_strategy_analyze_rejects_invalid_snapshot_rows
    assert response.json()["detail"] == "snapshot_data_invalid"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'snapshot_data_invalid'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
________________ test_screener_basic_rejects_partial_snapshots ________________
tests\test_api_snapshot_first_enforcement.py:331: in test_screener_basic_rejects_partial_snapshots
    assert response.json()["detail"] == "ingestion_run_not_ready"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/screener/basic "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_________________ test_screener_basic_accepts_ready_snapshots _________________
tests\test_api_snapshot_first_enforcement.py:384: in test_screener_basic_accepts_ready_snapshots
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/screener/basic "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
________________ test_manual_analysis_rejects_missing_snapshot ________________
tests\test_api_snapshot_first_enforcement.py:418: in test_manual_analysis_rejects_missing_snapshot
    assert response.json()["detail"] == "ingestion_run_not_ready"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________ test_manual_analysis_rejects_invalid_snapshot_rows ______________
tests\test_api_snapshot_first_enforcement.py:467: in test_manual_analysis_rejects_invalid_snapshot_rows
    assert response.json()["detail"] == "snapshot_data_invalid"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'snapshot_data_invalid'
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_________________ test_manual_analysis_accepts_ready_snapshot _________________
tests\test_api_snapshot_first_enforcement.py:519: in test_manual_analysis_accepts_ready_snapshot
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____________ test_strategy_analyze_multi_presets_returns_results _____________
tests\test_api_strategy_analyze_presets.py:140: in test_strategy_analyze_multi_presets_returns_results
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_________________ test_strategy_analyze_deterministic_output __________________
tests\test_api_strategy_analyze_presets.py:208: in test_strategy_analyze_deterministic_output
    assert response_one.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________ test_strategy_analyze_single_preset_backwards_compatible ___________
tests\test_api_strategy_analyze_presets.py:230: in test_strategy_analyze_single_preset_backwards_compatible
    assert response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________ test_trading_core_inspection_endpoints_exposed_read_only ___________
  + Exception Group Traceback (most recent call last):
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 76, in collapse_excgroups
  |     yield
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 177, in __call__
  |     async with anyio.create_task_group() as task_group:
  |                ~~~~~~~~~~~~~~~~~~~~~~~^^
  |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\_backends\_asyncio.py", line 772, in __aexit__
  |     raise BaseExceptionGroup(
  |         "unhandled errors in a TaskGroup", self._exceptions
  |     ) from None
  | ExceptionGroup: unhandled errors in a TaskGroup (1 sub-exception)
  +-+---------------- 1 ----------------
    | Traceback (most recent call last):
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 344, in from_call
    |     result: TResult | None = func()
    |                              ~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 246, in <lambda>
    |     lambda: runtest_hook(item=item, **kwds), when=when, reraise=reraise
    |             ~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\logging.py", line 850, in pytest_runtest_call
    |     yield
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\capture.py", line 900, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 139, in _multicall
    |     teardown.throw(exception)
    |     ~~~~~~~~~~~~~~^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\skipping.py", line 263, in pytest_runtest_call
    |     return (yield)
    |             ^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\runner.py", line 178, in pytest_runtest_call
    |     item.runtest()
    |     ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 1671, in runtest
    |     self.ihook.pytest_pyfunc_call(pyfuncitem=self)
    |     ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_hooks.py", line 512, in __call__
    |     return self._hookexec(self.name, self._hookimpls.copy(), kwargs, firstresult)
    |            ~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_manager.py", line 120, in _hookexec
    |     return self._inner_hookexec(hook_name, methods, kwargs, firstresult)
    |            ~~~~~~~~~~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 167, in _multicall
    |     raise exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pluggy\_callers.py", line 121, in _multicall
    |     res = hook_impl.function(*args)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\_pytest\python.py", line 157, in pytest_pyfunc_call
    |     result = testfunction(**testargs)
    |   File "C:\repos\Trading-engine\tests\test_api_trading_core_inspection_read.py", line 238, in test_trading_core_inspection_endpoints_exposed_read_only
    |     openapi = client.get("/api/openapi.json").json()
    |               ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    |     return super().get(
    |            ~~~~~~~~~~~^
    |         url,
    |         ^^^^
    |     ...<6 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    |     return self.request(
    |            ~~~~~~~~~~~~^
    |         "GET",
    |         ^^^^^^
    |     ...<7 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    |     return super().request(
    |            ~~~~~~~~~~~~~~~^
    |         method,
    |         ^^^^^^^
    |     ...<11 lines>...
    |         extensions=extensions,
    |         ^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    |     return self.send(request, auth=auth, follow_redirects=follow_redirects)
    |            ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    |     response = self._send_handling_auth(
    |         request,
    |     ...<2 lines>...
    |         history=[],
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    |     response = self._send_handling_redirects(
    |         request,
    |         follow_redirects=follow_redirects,
    |         history=history,
    |     )
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    |     response = self._send_single_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    |     response = transport.handle_request(request)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    |     portal.call(self.app, scope, receive, send)
    |     ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    |     return cast(T_Retval, self.start_task_soon(func, *args).result())
    |                           ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    |     return self.__get_result()
    |            ~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    |     raise self._exception
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    |     retval = await retval_or_awaitable
    |              ^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    |     await super().__call__(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    |     response = await call_next(request)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    |     with recv_stream, send_stream, collapse_excgroups():
    |                                    ~~~~~~~~~~~~~~~~~~^^
    |   File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    |     self.gen.throw(value)
    |     ~~~~~~~~~~~~~~^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    |     response = await self.dispatch_func(request, call_next)
    |                ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    |     response: Response = await call_next(request)
    |                          ^^^^^^^^^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    |     raise app_exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    |     await self.app(scope, receive_or_disconnect, send_no_error)
    |   File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    |     await self.app(scope, receive, _send)
    |   File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    |     await self.app(scope, receive, send)
    |   File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    |     await asyncio.wait_for(
    |     ...<2 lines>...
    |     )
    |   File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    |     return await fut
    |            ^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    |     await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    |     await self.middleware_stack(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    |     await route.handle(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    |     await self.app(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    |     await wrap_app_handling_exceptions(app, request)(scope, receive, send)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    |     raise exc
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    |     await app(scope, receive, sender)
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    |     response = await f(request)
    |                ^^^^^^^^^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    |     return JSONResponse(self.openapi())
    |                         ~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    |     self.openapi_schema = get_openapi(
    |                           ~~~~~~~~~~~^
    |         title=self.title,
    |         ^^^^^^^^^^^^^^^^^
    |     ...<11 lines>...
    |         separate_input_output_schemas=self.separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    |     field_mapping, definitions = get_definitions(
    |                                  ~~~~~~~~~~~~~~~^
    |         fields=all_fields,
    |         ^^^^^^^^^^^^^^^^^^
    |     ...<2 lines>...
    |         separate_input_output_schemas=separate_input_output_schemas,
    |         ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    |     field_mapping, definitions = schema_generator.generate_definitions(
    |                                  ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
    |         inputs=inputs
    |         ^^^^^^^^^^^^^
    |     )
    |     ^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    |     self.generate_inner(schema)
    |     ~~~~~~~~~~~~~~~~~~~^^^^^^^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    |     if 'ref' in schema:
    |        ^^^^^^^^^^^^^^^
    |   File "<frozen _collections_abc>", line 817, in __contains__
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    |     return self._get_built().__getitem__(key)
    |            ~~~~~~~~~~~~~~~^^
    |   File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    |     raise PydanticUserError(self._error_message, code=self._code)
    | pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
    | 
    | For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
    +------------------------------------

During handling of the above exception, another exception occurred:

Traceback (most recent call last):
  File "C:\repos\Trading-engine\tests\test_api_trading_core_inspection_read.py", line 238, in test_trading_core_inspection_endpoints_exposed_read_only
    openapi = client.get("/api/openapi.json").json()
              ~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 465, in get
    return super().get(
           ~~~~~~~~~~~^
        url,
        ^^^^
    ...<6 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1041, in get
    return self.request(
           ~~~~~~~~~~~~^
        "GET",
        ^^^^^^
    ...<7 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 437, in request
    return super().request(
           ~~~~~~~~~~~~~~~^
        method,
        ^^^^^^^
    ...<11 lines>...
        extensions=extensions,
        ^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 814, in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 901, in send
    response = self._send_handling_auth(
        request,
    ...<2 lines>...
        history=[],
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 929, in _send_handling_auth
    response = self._send_handling_redirects(
        request,
        follow_redirects=follow_redirects,
        history=history,
    )
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 966, in _send_handling_redirects
    response = self._send_single_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py", line 1002, in _send_single_request
    response = transport.handle_request(request)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 340, in handle_request
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py", line 337, in handle_request
    portal.call(self.app, scope, receive, send)
    ~~~~~~~~~~~^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 290, in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 456, in result
    return self.__get_result()
           ~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\concurrent\futures\_base.py", line 401, in __get_result
    raise self._exception
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py", line 221, in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py", line 112, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 187, in __call__
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py", line 165, in __call__
    await self.app(scope, receive, _send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py", line 85, in __call__
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\metrics.py", line 147, in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 176, in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ~~~~~~~~~~~~~~~~~~^^
  File "C:\Python313\Lib\contextlib.py", line 162, in __exit__
    self.gen.throw(value)
    ~~~~~~~~~~~~~~^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py", line 82, in collapse_excgroups
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 178, in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\repos\Trading-engine\src\api\middleware\request_id.py", line 72, in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 156, in call_next
    raise app_exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py", line 141, in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
  File "C:\repos\Trading-engine\src\api\middleware\deprecation.py", line 81, in __call__
    await self.app(scope, receive, _send)
  File "C:\repos\Trading-engine\src\api\middleware\shutdown.py", line 148, in __call__
    await self.app(scope, receive, send)
  File "C:\repos\Trading-engine\src\api\middleware\timeout.py", line 120, in __call__
    await asyncio.wait_for(
    ...<2 lines>...
    )
  File "C:\Python313\Lib\asyncio\tasks.py", line 507, in wait_for
    return await fut
           ^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py", line 62, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 714, in __call__
    await self.middleware_stack(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 734, in app
    await route.handle(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 288, in handle
    await self.app(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 76, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py", line 73, in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 1009, in openapi
    return JSONResponse(self.openapi())
                        ~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py", line 981, in openapi
    self.openapi_schema = get_openapi(
                          ~~~~~~~~~~~^
        title=self.title,
        ^^^^^^^^^^^^^^^^^
    ...<11 lines>...
        separate_input_output_schemas=self.separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py", line 514, in get_openapi
    field_mapping, definitions = get_definitions(
                                 ~~~~~~~~~~~~~~~^
        fields=all_fields,
        ^^^^^^^^^^^^^^^^^^
    ...<2 lines>...
        separate_input_output_schemas=separate_input_output_schemas,
        ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py", line 232, in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
                                 ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~^
        inputs=inputs
        ^^^^^^^^^^^^^
    )
    ^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 379, in generate_definitions
    self.generate_inner(schema)
    ~~~~~~~~~~~~~~~~~~~^^^^^^^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py", line 459, in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
  File "<frozen _collections_abc>", line 817, in __contains__
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 41, in __getitem__
    return self._get_built().__getitem__(key)
           ~~~~~~~~~~~~~~~^^
  File "C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py", line 58, in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.

For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined

During handling of the above exception, another exception occurred:
tests\test_api_trading_core_inspection_read.py:238: in test_trading_core_inspection_endpoints_exposed_read_only
    openapi = client.get("/api/openapi.json").json()
              ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:465: in get
    return super().get(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1041: in get
    return self.request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:437: in request
    return super().request(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:814: in request
    return self.send(request, auth=auth, follow_redirects=follow_redirects)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:901: in send
    response = self._send_handling_auth(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:929: in _send_handling_auth
    response = self._send_handling_redirects(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:966: in _send_handling_redirects
    response = self._send_single_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\httpx\_client.py:1002: in _send_single_request
    response = transport.handle_request(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:340: in handle_request
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\testclient.py:337: in handle_request
    portal.call(self.app, scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:290: in call
    return cast(T_Retval, self.start_task_soon(func, *args).result())
                          ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:456: in result
    return self.__get_result()
           ^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\concurrent\futures\_base.py:401: in __get_result
    raise self._exception
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\anyio\from_thread.py:221: in _call_func
    retval = await retval_or_awaitable
             ^^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1054: in __call__
    await super().__call__(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\applications.py:112: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:187: in __call__
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\errors.py:165: in __call__
    await self.app(scope, receive, _send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\cors.py:85: in __call__
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\metrics.py:147: in dispatch
    response = await call_next(request)
               ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:176: in __call__
    with recv_stream, send_stream, collapse_excgroups():
                                   ^^^^^^^^^^^^^^^^^^^^
C:\Python313\Lib\contextlib.py:162: in __exit__
    self.gen.throw(value)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_utils.py:82: in collapse_excgroups
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:178: in __call__
    response = await self.dispatch_func(request, call_next)
               ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
src\api\middleware\request_id.py:72: in dispatch
    response: Response = await call_next(request)
                         ^^^^^^^^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:156: in call_next
    raise app_exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\base.py:141: in coro
    await self.app(scope, receive_or_disconnect, send_no_error)
src\api\middleware\deprecation.py:81: in __call__
    await self.app(scope, receive, _send)
src\api\middleware\shutdown.py:148: in __call__
    await self.app(scope, receive, send)
src\api\middleware\timeout.py:120: in __call__
    await asyncio.wait_for(
C:\Python313\Lib\asyncio\tasks.py:507: in wait_for
    return await fut
           ^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\middleware\exceptions.py:62: in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:714: in __call__
    await self.middleware_stack(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:734: in app
    await route.handle(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:288: in handle
    await self.app(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:76: in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:53: in wrapped_app
    raise exc
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\_exception_handler.py:42: in wrapped_app
    await app(scope, receive, sender)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\starlette\routing.py:73: in app
    response = await f(request)
               ^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:1009: in openapi
    return JSONResponse(self.openapi())
                        ^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\applications.py:981: in openapi
    self.openapi_schema = get_openapi(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\openapi\utils.py:514: in get_openapi
    field_mapping, definitions = get_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\fastapi\_compat.py:232: in get_definitions
    field_mapping, definitions = schema_generator.generate_definitions(
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:379: in generate_definitions
    self.generate_inner(schema)
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\json_schema.py:459: in generate_inner
    if 'ref' in schema:
       ^^^^^^^^^^^^^^^
<frozen _collections_abc>:817: in __contains__
    ???
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:41: in __getitem__
    return self._get_built().__getitem__(key)
           ^^^^^^^^^^^^^^^^^
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: in _get_built
    raise PydanticUserError(self._error_message, code=self._code)
E   pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
E   
E   For further information visit https://errors.pydantic.dev/2.12/u/class-not-fully-defined
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/trading-core/orders "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/trading-core/execution-events "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/trading-core/trades "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/trading-core/positions "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
__________ test_engine_requests_are_blocked_when_runtime_not_running __________
tests\test_runtime_lifecycle.py:375: in test_engine_requests_are_blocked_when_runtime_not_running
    assert response.status_code == 503
E   assert 422 == 503
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
___________ test_engine_requests_work_normally_when_runtime_running ___________
tests\test_runtime_lifecycle.py:409: in test_engine_requests_work_normally_when_runtime_running
    assert body["detail"] == "invalid_ingestion_run_id"
E   AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
____________ test_engine_requests_are_blocked_when_runtime_paused _____________
tests\test_runtime_lifecycle.py:443: in test_engine_requests_are_blocked_when_runtime_paused
    assert response.status_code == 503
E   assert 422 == 503
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/strategy/analyze "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
_____ test_pause_during_in_progress_analysis_does_not_interrupt_execution _____
tests\test_runtime_lifecycle.py:516: in test_pause_during_in_progress_analysis_does_not_interrupt_execution
    assert calls["run"] == 1
E   assert 0 == 1
------------------------------ Captured log call ------------------------------
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/runtime/introspection "HTTP/1.1 200 OK"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
___________ test_ui_browser_flow_uses_existing_runtime_api_surface ____________
tests\test_ui_runtime_browser_flow.py:416: in test_ui_browser_flow_uses_existing_runtime_api_surface
    assert analysis_response.status_code == 200
E   assert 422 == 200
E    +  where 422 = <Response [422 Unprocessable Entity]>.status_code
------------------------------ Captured log call ------------------------------
DEBUG    asyncio:proactor_events.py:631 Using proactor: IocpProactor
INFO     api.main:scheduled_analysis_runner.py:192 Scheduled analysis runner disabled: component=api_scheduler
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/ui "HTTP/1.1 307 Temporary Redirect"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/ui/ "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/system/state "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: GET http://testserver/paper/runtime/evidence-series "HTTP/1.1 200 OK"
INFO     httpx:_client.py:1013 HTTP Request: POST http://testserver/analysis/run "HTTP/1.1 422 Unprocessable Entity"
INFO     api.main:runtime_lifecycle.py:70 graceful_shutdown_drain_started
INFO     api.main:runtime_lifecycle.py:75 graceful_shutdown_drain_complete
---------------------------- Captured log teardown ----------------------------
INFO     slowapi:extension.py:360 Storage has been reset and all limits cleared
============================== warnings summary ===============================
src/api/test_auth_api.py::TestJwtAuthUnit::test_wrong_algorithm_raises
  C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\jwt\api_jwt.py:147: InsecureKeyLengthWarning: The HMAC key is 6 bytes long, which is below the minimum recommended length of 32 bytes for SHA256. See RFC 7518 Section 3.2.
    return self._jws.encode(

-- Docs: https://docs.pytest.org/en/stable/how-to/capture-warnings.html
=========================== short test summary info ===========================
FAILED src/api/test_operator_analysis_trigger_api.py::test_operator_can_trigger_analysis_run_and_execution_is_logged
FAILED src/api/test_system_state_api.py::test_system_state_endpoint_is_documented
FAILED tests/api/test_exceptions_request_id.py::test_real_app_returns_request_id_in_validation_error_body
FAILED tests/api/test_openapi_docs_endpoints.py::test_openapi_endpoint_returns_valid_schema
FAILED tests/api/test_openapi_docs_endpoints.py::test_openapi_export_script_writes_file
FAILED tests/api/test_prometheus_metrics.py::test_metrics_recorded_after_normal_request
FAILED tests/test_api_backtest_entry_read.py::test_backtest_entry_read_route_exposes_bounded_non_live_contract
FAILED tests/test_api_decision_card_inspection_read.py::test_decision_card_inspection_endpoint_is_exposed_and_schema_valid
FAILED tests/test_api_execution_orders_read.py::test_execution_orders_api_contract
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_idempotent
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_rejects_invalid_ingestion_run
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_uses_snapshot
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_changes_id_for_different_payload
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_strategy_config_float_idempotent
FAILED tests/test_api_manual_analysis_trigger.py::test_manual_analysis_returns_persisted_result_when_duplicate_save_races
FAILED tests/test_api_paper_inspection_read.py::test_paper_endpoints_are_exposed_and_schema_valid
FAILED tests/test_api_paper_runtime_evidence_series_read.py::test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically
FAILED tests/test_api_signal_decision_surface.py::test_signal_decision_surface_openapi_contract_is_explicit
FAILED tests/test_api_signals_read.py::test_read_signals_openapi_exposes_timeframe_not_legacy_filters
FAILED tests/test_api_snapshot_first_enforcement.py::test_strategy_analyze_accepts_valid_ingestion_run_id
FAILED tests/test_api_snapshot_first_enforcement.py::test_strategy_analyze_rejects_missing_snapshot
FAILED tests/test_api_snapshot_first_enforcement.py::test_strategy_analyze_rejects_invalid_snapshot_rows
FAILED tests/test_api_snapshot_first_enforcement.py::test_screener_basic_rejects_partial_snapshots
FAILED tests/test_api_snapshot_first_enforcement.py::test_screener_basic_accepts_ready_snapshots
FAILED tests/test_api_snapshot_first_enforcement.py::test_manual_analysis_rejects_missing_snapshot
FAILED tests/test_api_snapshot_first_enforcement.py::test_manual_analysis_rejects_invalid_snapshot_rows
FAILED tests/test_api_snapshot_first_enforcement.py::test_manual_analysis_accepts_ready_snapshot
FAILED tests/test_api_strategy_analyze_presets.py::test_strategy_analyze_multi_presets_returns_results
FAILED tests/test_api_strategy_analyze_presets.py::test_strategy_analyze_deterministic_output
FAILED tests/test_api_strategy_analyze_presets.py::test_strategy_analyze_single_preset_backwards_compatible
FAILED tests/test_api_trading_core_inspection_read.py::test_trading_core_inspection_endpoints_exposed_read_only
FAILED tests/test_runtime_lifecycle.py::test_engine_requests_are_blocked_when_runtime_not_running
FAILED tests/test_runtime_lifecycle.py::test_engine_requests_work_normally_when_runtime_running
FAILED tests/test_runtime_lifecycle.py::test_engine_requests_are_blocked_when_runtime_paused
FAILED tests/test_runtime_lifecycle.py::test_pause_during_in_progress_analysis_does_not_interrupt_execution
FAILED tests/test_ui_runtime_browser_flow.py::test_ui_browser_flow_uses_existing_runtime_api_surface
36 failed, 1543 passed, 1 skipped, 1 warning in 149.06s (0:02:29)


```

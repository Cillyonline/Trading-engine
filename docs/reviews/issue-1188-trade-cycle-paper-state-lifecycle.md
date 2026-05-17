# Issue 1188 Trade-Cycle Paper-State Lifecycle Review

Active issue: #1188 - [VALIDATION][PAPER-RUNTIME] Review trade-cycle paper-state lifecycle before resuming #1060

## Scope

This review is bounded, read-only, and non-mutating. It reviews the #1060 interim evidence state, the #1186 diagnostic review-data conclusions, and repository code paths relevant to paper execution exit handling.

Only this review-data file was created or modified. No strategy logic, thresholds, score semantics, risk defaults, broker/live behavior, paper-state mutation or cleanup scripts, source code, #1060 historical evidence, roadmap, or governance files were changed.

## Evidence Reviewed

- #1060 Run 1-11 evidence as summarized and quoted in `docs/reviews/issue-1186-review-data.md`.
- #1183 baseline-first governance decision as quoted in `docs/reviews/issue-1186-review-data.md`.
- #1186 durable conclusions in `docs/reviews/issue-1186-review-data.md`.
- `scripts/run_paper_execution_cycle.py` read-only inspection.
- `scripts/run_daily_bounded_paper_runtime.py` read-only inspection.
- `src/cilly_trading/engine/paper_execution_worker.py` read-only inspection.
- `tests/engine/test_paper_execution_worker.py` read-only inspection.

Local `cilly_trading.db` was not used as primary blocker proof because #1186 recorded that the local database had no relevant current rows in `signals`, `core_trades`, `core_orders`, `core_execution_events`, or legacy `trades`. The blocker evidence comes from #1060 VPS runtime evidence preserved in #1186.

## #1060 Evidence State

#1186 records the #1060 interim state:

- Numbered attempts: 11.
- Completed bounded cycles: 10 / 20 minimum.
- Degraded pre-execution attempts: 1.
- Completed-cycle distribution: 10 `no_eligible`, 0 `healthy`, 0 `degraded`.
- New paper trades created across completed cycles: 0.
- Reconciliation remained stable where recorded, with `mismatches=0`.
- Stable score-below-threshold filtering remained at 9 candidates in later runs.
- `skip:exit_signal_not_entry_candidate` became the dominant and increasing skip reason.

Run 10 and Run 11 latest evidence:

```text
Run 10:
signals_read: 28
eligible: 0
skipped: 28
skip:exit_signal_not_entry_candidate: 16
skip:duplicate_entry: 3
skip:score_below_threshold: 9
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
open_trade_count: 3
duplicate_entry_blocker_count: 3
closed_trades: 0
execution_events: 9
reconciliation_ok: true
mismatches: 0

Run 11:
signals_read: 29
eligible: 0
skipped: 29
skip:exit_signal_not_entry_candidate: 17
skip:duplicate_entry: 3
skip:score_below_threshold: 9
account_as_of: 2026-04-02T00:00:00+00:00
account_freshness: stale
open_trade_count: 3
duplicate_entry_blocker_count: 3
closed_trades: 0
execution_events: 9
reconciliation_ok: true
mismatches: 0
```

This is technically useful runtime/reconciliation evidence. It is not trader validation, profitability evidence, broker readiness, live readiness, or production readiness.

## Stale Open Paper Trades

#1186 traces the repeated duplicate-entry blockers to open persisted TURTLE trades:

| Symbol | Strategy | Direction | Opened/account date evidence | Runtime blocker evidence | Classification |
| --- | --- | --- | --- | --- | --- |
| COST | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`; latest `account_as_of=2026-04-02T00:00:00+00:00` | Run 10/11 stale duplicate-entry blocker; no closed trade evidence | stale-and-blocking |
| GS | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`; latest `account_as_of=2026-04-02T00:00:00+00:00` | Run 10/11 stale duplicate-entry blocker; no closed trade evidence | stale-and-blocking |
| WMT | TURTLE | long | `opened_at=2026-04-02T00:00:00+00:00`, `status=open`; latest `account_as_of=2026-04-02T00:00:00+00:00` | Run 10/11 stale duplicate-entry blocker; no closed trade evidence | stale-and-blocking |

Rationale: the trades are lifecycle-valid enough for duplicate-entry protection to see open positions and block same `(symbol, strategy, direction)` entries. They are stale because current #1060 evidence still reports `account_as_of=2026-04-02T00:00:00+00:00` in mid-May runs. They are blocking because Run 10/11 each report `duplicate_entry_blocker_count: 3` and list COST, GS, and WMT as stale duplicate-entry blockers.

No cleanup, reset, or manual close was performed or recommended inside #1188.

## Code Path Findings

`BoundedPaperExecutionWorker` has a component-level exit mechanism:

- `process_exit_signal()` exists in `src/cilly_trading/engine/paper_execution_worker.py`.
- It validates signal fields, looks up matching trades by `strategy_id`, `symbol`, `status == "open"`, and direction.
- It returns `skip:no_open_position_to_exit` when no matching open trade exists.
- It can return `eligible:partial_exit` or `eligible:full_exit`.
- It persists an exit order, execution event, and updated trade state.
- Tests cover full exit, partial exit, missing open position, two-step exit, and realized PnL.

The active batch/cycle path does not route exit-stage signals into that component-level exit mechanism:

- `BoundedPaperExecutionWorker.process_batch()` returns `[self.process_signal(signal) for signal in signals]`.
- `scripts/run_paper_execution_cycle.py` calls `worker.process_batch(signals)`.
- `process_signal()` calls `_evaluate()` and persists only `outcome == "eligible"` entries.
- `_evaluate()` returns `skip:exit_signal_not_entry_candidate` immediately when `stage == "exit"`.
- The reviewed runtime-cycle path has no call to `process_exit_signal()`.

Therefore the repository has a bounded paper-exit function, but the #1060 bounded paper-runtime cycle is not evidenced to consume exit-stage signals against existing open paper trades.

## Exit-Stage Signal Classification

| Evidence surface | Classification | Evidence |
| --- | --- | --- |
| `process_signal()` / `_evaluate()` entry-candidate path | paper-execution-facing as a skip classification | Exit-stage signals passed through the normal paper execution entry path return `skip:exit_signal_not_entry_candidate` before score, duplicate-entry, or sizing. |
| `process_exit_signal()` component method | paper-execution-facing component capability | It can close or partially close matching open paper trades and persists paper order/event/trade updates. |
| `process_batch()` plus `scripts/run_paper_execution_cycle.py` | backtest-facing or ambiguous for actual exit consumption; insufficiently evidenced as paper-execution exit routing | Batch runtime routes every signal to `process_signal()`, not `process_exit_signal()`. |
| #1060 Run 10/11 observed exit-stage outcomes | paper-execution-facing skip only | Latest evidence records `skip:exit_signal_not_entry_candidate` counts of 16 and 17, not partial/full exit outcomes. |

Bounded answer to the acceptance target: paper execution has a bounded non-mutating path to classify exit-stage signals in the runtime cycle, but the reviewed #1060 runtime path does not have a proven bounded non-mutating path to consume those exit-stage signals against open paper trades. Exit consumption is implemented as a component method, not evidenced as wired into the active bounded paper-runtime cycle.

## Technical / Operational / Trader Separation

Technically implemented:

- Bounded daily runtime completes and records `no_eligible` as a non-error outcome when reconciliation is clean.
- Duplicate-entry protection sees open COST, GS, and WMT TURTLE long trades and blocks duplicate entries.
- Exit-stage signals are deterministically classified as non-entry candidates on the active entry path.
- A separate `process_exit_signal()` component can close matching open paper trades when directly called.

Operationally usable:

- The evidence is usable for runtime stability, reconciliation hygiene, and stale paper-state review.
- The stale open trade workflow is read-only and records review-required state.
- The current #1060 series is weak for continued operator insight because it repeats the same `no_eligible` pattern without new paper entries or closed trade-cycle evidence.

Trader validation:

- Not established.
- No new paper trades were created across the interim series.
- No completed trade-cycle evidence was produced by #1060 Run 1-11.
- No profitability, broker-readiness, live-readiness, or production-readiness claim is supported.

## Recommendation

Continue #1060 paused and open a lifecycle implementation issue.

Reason: resuming #1060 unchanged is likely to produce more technically stable `no_eligible` evidence while leaving the same stale-and-blocking COST, GS, and WMT paper trades unresolved. A cleanup issue is premature because the review does not prove the trades should be manually closed or reset. The narrower missing evidence is lifecycle routing: whether the bounded paper-runtime cycle should route `stage == "exit"` signals to `BoundedPaperExecutionWorker.process_exit_signal()` for matching open paper trades, and under what idempotency/evidence guarantees.

## Modified / New / Deleted Files

Modified files:

- None.

New files:

- `docs/reviews/issue-1188-trade-cycle-paper-state-lifecycle.md`

Deleted files:

- None.

Only new/modified file for #1188:

- `docs/reviews/issue-1188-trade-cycle-paper-state-lifecycle.md`

## Exact Test Command

Repository command attempted:

```powershell
$env:PYTHONIOENCODING='utf-8'; uv run pytest
```

Fallback evidence command used because `uv` is unavailable on PATH:

```powershell
$env:PYTHONIOENCODING='utf-8'; python -m pytest --tb=line -q
```

## Test Result Summary

- Repository command result: not run because `uv` is unavailable on this Windows PATH.
- Fallback command result: failed.
- Fallback summary: 36 failed, 1543 passed, 1 skipped, 1 warning in 298.02s.
- Failure area: pre-existing API/OpenAPI/runtime request-validation failures centered on `StrategyAnalyzeRequest` Pydantic forward-reference handling and related `422` responses.
- #1188 changed only this review-data file; no source or test code was modified to address those out-of-scope failures.

## Full Exact Test Output

```text
uv : Die Benennung "uv" wurde nicht als Name eines Cmdlet, einer Funktion, einer Skriptdatei oder eines ausführbaren
Programms erkannt.

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
C:\repos\Trading-engine\src\api\test_operator_analysis_trigger_api.py:78: assert 422 == 200
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\repos\Trading-engine\tests\api\test_exceptions_request_id.py:262: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:161: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:203: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:267: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:336: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:403: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_manual_analysis_trigger.py:502: assert 422 == 200
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:184: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:229: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:278: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'snapshot_data_invalid'
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:331: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:384: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:418: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'ingestion_run_not_ready'
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:467: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'snapshot_data_invalid'
C:\repos\Trading-engine\tests\test_api_snapshot_first_enforcement.py:519: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_strategy_analyze_presets.py:140: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_strategy_analyze_presets.py:208: assert 422 == 200
C:\repos\Trading-engine\tests\test_api_strategy_analyze_presets.py:230: assert 422 == 200
C:\Users\Serdar Cil\AppData\Roaming\Python\Python313\site-packages\pydantic\_internal\_mock_val_ser.py:58: pydantic.errors.PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
C:\repos\Trading-engine\tests\test_runtime_lifecycle.py:375: assert 422 == 503
C:\repos\Trading-engine\tests\test_runtime_lifecycle.py:409: AssertionError: assert [{'input': None, 'loc': ['query', 'req'], 'msg': 'Field required', 'type': 'missing'}] == 'invalid_ingestion_run_id'
C:\repos\Trading-engine\tests\test_runtime_lifecycle.py:443: assert 422 == 503
C:\repos\Trading-engine\tests\test_runtime_lifecycle.py:516: assert 0 == 1
C:\repos\Trading-engine\tests\test_ui_runtime_browser_flow.py:416: assert 422 == 200
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
36 failed, 1543 passed, 1 skipped, 1 warning in 298.02s (0:04:58)
```

## Follow-Up Issue

Recommended title:

```text
[PAPER-RUNTIME] Wire or explicitly reject bounded exit-signal consumption for open paper trades
```

Recommended scope:

- Preserve strategy logic, thresholds, score semantics, risk defaults, and broker/live boundaries.
- Do not mutate existing paper state as part of issue setup.
- Decide whether the bounded paper-runtime cycle should route `stage == "exit"` signals to `process_exit_signal()`.
- If routing is authorized, add deterministic tests for full exit, partial exit, no matching open position, repeated-run idempotency, and evidence output.
- If routing is rejected, document that exit-stage signals are not paper-execution lifecycle inputs in the bounded runtime cycle and keep #1060 paused until an authorized cleanup/operator-review path exists.

## Out Of Scope

- Paper-state cleanup, resets, manual closes, or trade mutation.
- Strategy, threshold, score, risk-default, entry/exit strategy logic, broker/live, or profitability changes.
- #1060 historical evidence mutation.
- Trader validation, broker readiness, live readiness, or production readiness claims.

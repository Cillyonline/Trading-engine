# Issue #1190 Exit-Signal Consumption Review Data

## SUMMARY

Outcome A was selected. The bounded paper-runtime cycle now routes `stage == "exit"` signals through `BoundedPaperExecutionWorker.process_exit_signal()` when signals are processed by `process_batch()`, which is the worker API used by `scripts/run_paper_execution_cycle.py`.

Direct `process_signal()` entry-candidate behavior is preserved, including `skip:exit_signal_not_entry_candidate` when an exit signal is passed directly to the entry policy. RSI2 and TURTLE strategy logic, score semantics, thresholds, entry rules, exit strategy rules, risk defaults, broker/live boundaries, and non-profitability boundaries were not changed.

## DECISION SELECTED: Outcome A

Wire bounded runtime-cycle exit-stage signals to `BoundedPaperExecutionWorker.process_exit_signal()` for matching open paper trades, with deterministic tests and evidence output.

## RATIONALE

The repository already had a component-level bounded paper-exit capability in `BoundedPaperExecutionWorker.process_exit_signal()`. The missing bounded runtime behavior was the batch/runtime call path: `process_batch()` sent all signals to `process_signal()`, so exit-stage signals were classified as entry-policy skips instead of being consumed as lifecycle exits.

Wiring at `process_batch()` is the narrowest bounded implementation path because the paper execution script already calls `worker.process_batch(signals)`. This keeps direct entry-policy semantics stable while enabling runtime-cycle lifecycle routing.

An idempotency guard was added before any exit mutation. The deterministic exit order ID is resolved from the signal identity and checked with `repository.get_order()`. If the exit order already exists, the worker returns the previously represented exit outcome without changing trade quantities, creating orders, or appending execution events.

## ACCEPTANCE CRITERIA TRACE

1. Exit-stage signals in the bounded paper-runtime cycle are routed to `process_exit_signal()` by `BoundedPaperExecutionWorker.process_batch()`.
2. Routing closes only matching open paper trades because `process_exit_signal()` filters by strategy, symbol, direction, and `status == "open"`.
3. Repeated runs do not duplicate closes, orders, or execution events because existing deterministic exit orders are detected before trade mutation.
4. Deterministic tests cover full exit, partial exit, no matching open position, repeated-run idempotency, and resulting paper-state changes.
5. Rejection-path documentation was not selected because Outcome A was implemented.
6. Tests cover the selected decision path in worker and script coverage.
7. This review-data file was created at `docs/reviews/issue-1190-exit-signal-consumption-review-data.md`.
8. No strategy tuning, threshold tuning, score recalibration, risk-default tuning, broker/live behavior, production/VPS paper-state mutation, cleanup, trader-validation claim, profitability claim, broker-readiness claim, live-readiness claim, or production-readiness claim was introduced.

## TECHNICALLY IMPLEMENTED

- `BoundedPaperExecutionWorker.process_batch()` routes `stage == "exit"` signals to `process_exit_signal()`.
- `process_exit_signal()` computes the deterministic exit order ID before selecting an open trade.
- `process_exit_signal()` returns an existing exit result without mutation when the deterministic exit order already exists.
- Exit trade updates now append the deterministic closing order ID and filled execution event ID to the trade lifecycle fields.
- `run_paper_execution_cycle()` counts all `eligible*` outcomes, including `eligible:partial_exit` and `eligible:full_exit`, as eligible bounded paper execution work.

## OPERATIONALLY USABLE

The existing bounded operator command remains the runtime entrypoint:

```powershell
python scripts/run_paper_execution_cycle.py --db-path <paper-db> --evidence-dir <evidence-dir>
```

When persisted signals include `stage == "exit"` and a matching open paper trade exists in the same bounded paper database, the runtime cycle can now produce `eligible:partial_exit` or `eligible:full_exit` evidence. When no matching open paper trade exists, the result remains `skip:no_open_position_to_exit`.

## TRADERICALLY VALIDATED

No trader-validation claim is made. This change validates only bounded technical lifecycle routing and deterministic persistence behavior.

## MODIFIED FILES

- `src/cilly_trading/engine/paper_execution_worker.py`
- `scripts/run_paper_execution_cycle.py`
- `tests/engine/test_paper_execution_worker.py`
- `tests/test_run_paper_execution_cycle_script.py`
- `docs/operations/runtime/p60-signal-to-paper-operator-path.md`

## NEW FILES

- `docs/reviews/issue-1190-exit-signal-consumption-review-data.md`

## DELETED FILES

None.

## TEST COMMAND

Focused selected-path command:

```powershell
python -m pytest tests/engine/test_paper_execution_worker.py tests/test_run_paper_execution_cycle_script.py tests/test_ops_p60_signal_to_paper_operator_path.py -q
```

Repository command:

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; python -X utf8 -m pytest --import-mode=importlib -q --tb=short
```

## FULL TEST OUTPUT

Focused selected-path output:

```text
........................................................................ [ 65%]
......................................                                   [100%]
110 passed in 13.89s
```

Repository command output:

```text
36 failed, 1548 passed, 1 skipped, 1 warning in 166.72s (0:02:46)
```

Clean baseline command, run from a detached `HEAD` worktree before #1190 changes:

```powershell
$env:PYTHONIOENCODING='utf-8'; $env:PYTHONUTF8='1'; python -X utf8 -m pytest --import-mode=importlib -q --tb=short
```

Clean baseline output:

```text
36 failed, 1543 passed, 1 skipped, 1 warning in 189.41s (0:03:09)
```

The same 36 test names failed on the clean baseline and on the #1190 worktree. The #1190 worktree has five additional passing tests from the new selected-path coverage, which explains the pass-count increase from 1543 to 1548.

Repository failure list:

```text
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
```

Representative repository failure signatures:

```text
assert 422 == 200
assert 422 == 503
PydanticUserError: `TypeAdapter[typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]]` is not fully defined; you should define `typing.Annotated[ForwardRef('StrategyAnalyzeRequest'), Query(PydanticUndefined)]` and all referenced types, then call `.rebuild()` on the instance.
```

## RISK NOTES

- The script-level signal repository currently does not persist `exit_pct`; script-level partial-exit fixture coverage was therefore kept at the worker batch boundary where runtime-cycle routing occurs and where `exit_pct` is available on the signal object.
- If multiple matching open trades exist despite duplicate-entry policy, `process_exit_signal()` preserves existing behavior and consumes the first deterministic repository result.
- Full repository pytest is not green in this workspace due to unrelated API/runtime failures involving request validation and OpenAPI/Pydantic forward-reference errors.

## OUT OF SCOPE

- RSI2 strategy logic changes.
- TURTLE strategy logic changes.
- Score, threshold, calibration, risk default, or strategy configuration changes.
- Broker/live execution changes.
- Production or VPS paper-state mutation.
- Manual cleanup, reset, or closure of stale COST, GS, or WMT paper trades.
- Trader-validation, profitability, broker-readiness, live-readiness, or production-readiness claims.
- Resuming #1060.

## FOLLOW-UP ISSUES

- Consider a separate bounded issue to persist `exit_pct` in the signal repository if operators need script-level partial-exit signals sourced from SQLite.
- Investigate the existing full-suite API/runtime failures around `/analysis/run`, `/strategy/analyze`, and OpenAPI/Pydantic forward references outside #1190.

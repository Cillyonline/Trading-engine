from __future__ import annotations

import hashlib
import importlib.util
import json
import subprocess
import sys
import urllib.error
from copy import deepcopy
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _default_risk_profile() -> dict[str, object]:
    return {
        "allowed_regimes": [],
        "commission_rate": "0.001",
        "correlation_check_enabled": False,
        "correlation_threshold": 0.7,
        "correlation_window": 60,
        "drawdown_guard_enabled": False,
        "max_concurrent_positions": 10,
        "max_correlated_pairs": 2,
        "max_drawdown_pct": "0.10",
        "max_strategy_exposure_pct": "0.80",
        "max_symbol_exposure_pct": "0.80",
        "max_total_exposure_pct": "0.80",
        "min_score_threshold": 60.0,
        "sizing_method": "stop_distance",
        "slippage_rate": "0.0005",
    }


def _load_script_module():
    module_path = REPO_ROOT / "scripts" / "run_daily_bounded_paper_runtime.py"
    spec = importlib.util.spec_from_file_location(
        "test_run_daily_bounded_paper_runtime_script_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_daily_bounded_paper_runtime.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_daily_runner_executes_ops_p63_order_and_writes_run_record(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()

    executed_scripts: list[str] = []
    request_sequence: list[tuple[str, str]] = []

    def _fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        script_name = Path(command[1]).name
        executed_scripts.append(script_name)

        if script_name == "run_snapshot_ingestion.py":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps(
                    {
                        "result": {"ingestion_run_id": "ing-123"},
                        "status": "ok",
                    }
                )
                + "\n",
                stderr="",
            )
        if script_name == "run_paper_execution_cycle.py":
            return subprocess.CompletedProcess(
                command,
                1,
                stdout=json.dumps(
                    {
                        "eligible": 0,
                        "rejected": 0,
                        "results": [{"outcome": "skip:score_below_threshold", "signal_id": "sig-1"}],
                        "risk_profile": _default_risk_profile(),
                        "skipped": 1,
                        "status": "no_eligible",
                    }
                )
                + "\n",
                stderr="",
            )
        if script_name == "run_post_run_reconciliation.py":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"ok": True, "status": "pass"}) + "\n",
                stderr="",
            )
        if script_name == "generate_weekly_review.py":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"all_valid": True, "status": "pass"}) + "\n",
                stderr="",
            )
        raise AssertionError(f"Unexpected script invocation: {script_name}")

    def _fake_request_json(
        url: str,
        *,
        headers: dict[str, str],
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        request_sequence.append((method, url))
        if url.endswith("/analysis/run"):
            assert method == "POST"
            assert headers == {module.ROLE_HEADER_NAME: module.ROLE_OPERATOR}
            assert payload is not None
            assert payload["ingestion_run_id"] == "ing-123"
            return {
                "analysis_run_id": "analysis-123",
                "ingestion_run_id": "ing-123",
                "signals": [],
                "strategy": "RSI2",
                "symbol": "AAPL",
            }

        assert method == "GET"
        assert headers == {module.ROLE_HEADER_NAME: module.ROLE_READ_ONLY}
        if "/signals?" in url:
            return {"items": [], "total": 0}
        if url.endswith("/paper/trades"):
            return {"items": [], "total": 0}
        if url.endswith("/paper/positions"):
            return {"items": [], "total": 0}
        if url.endswith("/paper/account"):
            return {"account": {"as_of": "2026-04-06T12:00:00+00:00"}}
        if url.endswith("/paper/reconciliation"):
            return {"mismatches": 0, "ok": True}
        raise AssertionError(f"Unexpected request URL: {url}")

    monkeypatch.setattr(module, "_run_command", _fake_run_command)
    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(
        module,
        "_utc_now",
        lambda: datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_daily_bounded_paper_runtime.py",
            "--db-path",
            str(tmp_path / "analysis.db"),
            "--snapshot-evidence-dir",
            str(tmp_path / "snapshot"),
            "--execution-evidence-dir",
            str(tmp_path / "execution"),
            "--reconciliation-evidence-dir",
            str(tmp_path / "reconciliation"),
            "--review-evidence-dir",
            str(tmp_path / "review"),
            "--run-record-dir",
            str(tmp_path / "daily-runtime"),
        ],
    )

    exit_code = module.main()

    assert exit_code == module.EXIT_CODE_SUCCESS
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "ok"
    assert payload["run_quality_status"] == "no_eligible"
    assert payload["run_quality_classification_version"] == 1
    assert payload["operator_action_contract_version"] == 1
    assert payload["operator_action_contract"] == {
        "action_category": "review_required",
        "action_code": "review_no_eligible_and_record",
        "action_summary": "Review the bounded no-eligible outcome, confirm skip reasons and inputs, and record the run without retrying solely to force activity.",
        "escalation_boundary": "Escalate only when adjacent bounded evidence is contradictory or the no-eligible pattern is unexpected for the stated inputs. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert payload["run_quality_inputs"] == {
        "execution_eligible": 0,
        "execution_returncode": 1,
        "execution_status": "no_eligible",
        "reconciliation_mismatches": None,
        "reconciliation_ok": True,
    }
    assert payload["step_order"] == list(module.STEP_ORDER)
    assert payload["steps_completed"] == list(module.STEP_ORDER)
    assert payload["analysis_run_id"] == "analysis-123"
    assert payload["ingestion_run_id"] == "ing-123"
    assert Path(payload["summary_file"]).exists()
    assert Path(payload["verification_surfaces"]["signals"]).exists()
    assert Path(payload["verification_surfaces"]["paper-trades"]).exists()
    assert Path(payload["verification_surfaces"]["paper-positions"]).exists()
    assert Path(payload["verification_surfaces"]["paper-account"]).exists()
    assert Path(payload["verification_surfaces"]["paper-reconciliation"]).exists()
    assert payload["paper_state_freshness"] == {
        "account_as_of": "2026-04-06T12:00:00+00:00",
        "account_age_seconds": 0,
        "account_freshness": "fresh",
        "age_seconds": 0,
        "classification_version": 1,
        "duplicate_entry_blocker_count": 0,
        "freshness": "fresh",
        "observed_at": "2026-04-06T12:00:00+00:00",
        "open_trade_count": 0,
        "open_trades": [],
        "operator_review_guidance": (
            "Open paper state is current within the bounded daily freshness window; "
            "record duplicate-entry blocking as technically valid paper-state evidence."
        ),
        "review_required_count": 0,
        "stale_after_seconds": 86400,
    }
    risk_controls = {item["control_id"]: item for item in payload["risk_control_activation"]}
    assert set(risk_controls) == {
        "commission_model",
        "correlation_gate",
        "drawdown_guard",
        "duplicate_entry_gate",
        "exposure_limits",
        "max_concurrent_positions",
        "regime_filter",
        "score_threshold_gate",
        "slippage_model",
        "stop_distance_sizing",
    }
    assert risk_controls["score_threshold_gate"]["active"] is True
    assert risk_controls["score_threshold_gate"]["applied_count"] == 1
    assert risk_controls["score_threshold_gate"]["blocked_count"] == 1
    assert risk_controls["correlation_gate"]["active"] is False
    assert risk_controls["correlation_gate"]["inactive_reason"] == (
        "disabled by config: correlation_check_enabled=false"
    )
    assert "Not validated by this run" in risk_controls["correlation_gate"]["validation_note"]
    assert risk_controls["drawdown_guard"]["active"] is False
    assert risk_controls["regime_filter"]["active"] is False
    assert executed_scripts == [
        "run_snapshot_ingestion.py",
        "run_paper_execution_cycle.py",
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
    ]
    assert request_sequence == [
        ("POST", "http://127.0.0.1:18000/analysis/run"),
        ("GET", "http://127.0.0.1:18000/signals?ingestion_run_id=ing-123&limit=100"),
        ("GET", "http://127.0.0.1:18000/paper/trades"),
        ("GET", "http://127.0.0.1:18000/paper/positions"),
        ("GET", "http://127.0.0.1:18000/paper/account"),
        ("GET", "http://127.0.0.1:18000/paper/reconciliation"),
    ]
    summary_file_payload = json.loads(Path(payload["summary_file"]).read_text(encoding="utf-8"))
    assert summary_file_payload["run_quality_status"] == payload["run_quality_status"]
    assert summary_file_payload["run_quality_classification_version"] == payload["run_quality_classification_version"]
    assert summary_file_payload["operator_action_contract_version"] == payload["operator_action_contract_version"]
    assert summary_file_payload["operator_action_contract"] == payload["operator_action_contract"]
    assert summary_file_payload["run_quality_inputs"] == payload["run_quality_inputs"]
    assert summary_file_payload["paper_state_freshness"] == payload["paper_state_freshness"]
    assert summary_file_payload["risk_control_activation"] == payload["risk_control_activation"]
    operator_review_file = Path(payload["run_record_dir"]) / "operator-review.json"
    operator_review_bytes = operator_review_file.read_bytes()
    operator_review_payload = json.loads(operator_review_bytes.decode("utf-8"))
    assert operator_review_payload == {
        "artifact_id": "operator-review",
        "artifact_version": 1,
        "invalid_count": 0,
        "mutates_paper_state": False,
        "non_inference_statement": (
            "This artifact records bounded paper-runtime observations only. It is not trader validation, "
            "not profitability evidence, and not broker/live readiness evidence."
        ),
        "observed_at": "2026-04-06T12:00:00+00:00",
        "read_only": True,
        "recorded_count": 0,
        "review_outcomes": [],
        "review_required_count": 0,
        "source_daily_runtime_summary": payload["summary_file"],
        "workflow_id": "bounded_daily_paper_runtime",
        "workflow_version": "OPS-P64",
    }
    operator_review_sha_file = operator_review_file.with_suffix(".sha256")
    assert operator_review_sha_file.read_text(encoding="ascii") == (
        f"{hashlib.sha256(operator_review_bytes).hexdigest()}  operator-review.json\n"
    )
    assert not operator_review_file.with_suffix(".json.sha256").exists()
    assert payload["stale_open_paper_trade_review_workflow"]["workflow_id"] == (
        "ops_bounded_stale_open_paper_trade_review"
    )
    assert payload["stale_open_paper_trade_review_workflow"]["mode"] == "bounded_stale_paper_trade_review"
    assert payload["stale_open_paper_trade_review_workflow"]["workflow_status"] == "no_review_required"
    assert payload["stale_open_paper_trade_review_workflow"]["mutates_paper_state"] is False
    assert payload["stale_open_paper_trade_review_workflow"]["stale_open_trades"] == []
    assert (
        summary_file_payload["stale_open_paper_trade_review_workflow"]
        == payload["stale_open_paper_trade_review_workflow"]
    )


def test_risk_control_activation_evidence_reports_required_controls_and_inactive_defaults() -> None:
    module = _load_script_module()

    evidence = module.build_risk_control_activation_evidence(
        execution_payload={
            "results": [],
            "risk_profile": _default_risk_profile(),
        }
    )

    controls = {item["control_id"]: item for item in evidence}
    assert list(controls) == [
        "score_threshold_gate",
        "duplicate_entry_gate",
        "stop_distance_sizing",
        "commission_model",
        "slippage_model",
        "exposure_limits",
        "max_concurrent_positions",
        "correlation_gate",
        "drawdown_guard",
        "regime_filter",
    ]
    assert controls["score_threshold_gate"]["implemented"] is True
    assert controls["score_threshold_gate"]["configured"] is True
    assert controls["score_threshold_gate"]["active"] is True
    assert controls["duplicate_entry_gate"]["active"] is True
    assert controls["stop_distance_sizing"]["active"] is True
    assert controls["commission_model"]["active"] is True
    assert controls["slippage_model"]["active"] is True
    assert controls["exposure_limits"]["active"] is True
    assert controls["max_concurrent_positions"]["active"] is True
    assert controls["correlation_gate"]["configured"] is True
    assert controls["correlation_gate"]["active"] is False
    assert controls["correlation_gate"]["inactive_reason"] == (
        "disabled by config: correlation_check_enabled=false"
    )
    assert controls["drawdown_guard"]["active"] is False
    assert controls["drawdown_guard"]["inactive_reason"] == (
        "disabled by config: drawdown_guard_enabled=false"
    )
    assert controls["regime_filter"]["active"] is False
    assert controls["regime_filter"]["inactive_reason"] == (
        "no allowed regimes configured: allowed_regimes is empty"
    )
    assert all("Not validated by this run" in controls[item]["validation_note"] for item in (
        "correlation_gate",
        "drawdown_guard",
        "regime_filter",
    ))


def test_daily_runner_emits_non_empty_operator_review_artifact_for_stale_duplicate_blockers(
    monkeypatch,
    tmp_path: Path,
) -> None:
    module = _load_script_module()
    request_sequence: list[tuple[str, str]] = []

    def _fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        script_name = Path(command[1]).name
        if script_name == "run_snapshot_ingestion.py":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"result": {"ingestion_run_id": "ing-dup"}}) + "\n", stderr="")
        if script_name == "run_paper_execution_cycle.py":
            return subprocess.CompletedProcess(
                command,
                1,
                stdout=json.dumps(
                    {
                        "eligible": 0,
                        "results": [
                            {
                                "outcome": "skip:duplicate_entry",
                                "reason": "open trade exists for (COST, TURTLE, long)",
                            },
                            {
                                "outcome": "skip:duplicate_entry",
                                "reason": "open trade exists for (WMT, TURTLE, long)",
                            },
                            {
                                "outcome": "skip:duplicate_entry",
                                "reason": "open trade exists for (GS, TURTLE, long)",
                            },
                        ],
                        "risk_profile": _default_risk_profile(),
                        "status": "no_eligible",
                    }
                )
                + "\n",
                stderr="",
            )
        if script_name == "run_post_run_reconciliation.py":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"ok": True, "status": "pass"}) + "\n", stderr="")
        if script_name == "generate_weekly_review.py":
            return subprocess.CompletedProcess(command, 0, stdout=json.dumps({"all_valid": True, "status": "pass"}) + "\n", stderr="")
        raise AssertionError(f"Unexpected script invocation: {script_name}")

    def _fake_request_json(
        url: str,
        *,
        headers: dict[str, str],
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        request_sequence.append((method, url))
        if url.endswith("/analysis/run"):
            return {"analysis_run_id": "analysis-dup", "ingestion_run_id": "ing-dup", "signals": []}
        assert method == "GET"
        assert headers == {module.ROLE_HEADER_NAME: module.ROLE_READ_ONLY}
        if "/signals?" in url:
            return {"items": [], "total": 0}
        if url.endswith("/paper/trades"):
            return {
                "items": [
                    {
                        "direction": "long",
                        "opened_at": "2026-05-06T11:00:00+00:00",
                        "position_id": "pos-aapl",
                        "quantity_closed": "0",
                        "quantity_opened": "1",
                        "status": "open",
                        "strategy_id": "TURTLE",
                        "symbol": "AAPL",
                        "trade_id": "trade-aapl",
                    },
                    {
                        "direction": "long",
                        "opened_at": None,
                        "position_id": "pos-cost",
                        "quantity_closed": "0",
                        "quantity_opened": "1",
                        "status": "open",
                        "strategy_id": "TURTLE",
                        "symbol": "COST",
                        "trade_id": "trade-cost",
                    },
                    {
                        "direction": "long",
                        "opened_at": "2026-04-02T00:00:00+00:00",
                        "position_id": "pos-wmt",
                        "quantity_closed": "0",
                        "quantity_opened": "1",
                        "status": "open",
                        "strategy_id": "TURTLE",
                        "symbol": "WMT",
                        "trade_id": "trade-wmt",
                    },
                    {
                        "direction": "long",
                        "opened_at": "2026-04-02T00:00:00+00:00",
                        "position_id": "pos-gs",
                        "quantity_closed": "0",
                        "quantity_opened": "1",
                        "status": "open",
                        "strategy_id": "TURTLE",
                        "symbol": "GS",
                        "trade_id": "trade-gs",
                    },
                ],
                "total": 4,
            }
        if url.endswith("/paper/positions"):
            return {
                "items": [
                    {"position_id": "pos-aapl", "status": "open"},
                    {"position_id": "pos-cost", "status": "open"},
                    {"position_id": "pos-wmt", "status": "open"},
                    {"position_id": "pos-gs", "status": "open"},
                ],
                "total": 4,
            }
        if url.endswith("/paper/account"):
            return {"account": {"as_of": "2026-05-06T12:00:00+00:00"}}
        if url.endswith("/paper/reconciliation"):
            return {"mismatches": 0, "ok": True}
        raise AssertionError(f"Unexpected request URL: {url}")

    monkeypatch.setattr(module, "_run_command", _fake_run_command)
    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(module, "_utc_now", lambda: datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc))

    payload = module.run_daily_bounded_paper_runtime(
        db_path=str(tmp_path / "analysis.db"),
        base_url="http://127.0.0.1:18000",
        symbols="AAPL",
        timeframe="1d",
        limit=100,
        provider="test",
        analysis_symbol="AAPL",
        analysis_strategy="RSI2",
        analysis_market_type="equity",
        analysis_lookback_days=30,
        snapshot_evidence_dir=str(tmp_path / "snapshot"),
        execution_evidence_dir=str(tmp_path / "execution"),
        reconciliation_evidence_dir=str(tmp_path / "reconciliation"),
        review_evidence_dir=str(tmp_path / "review"),
        run_record_dir=str(tmp_path / "daily-runtime"),
        signals_limit=100,
        run_command=module._run_command,
        request_json=module._request_json,
        now_fn=module._utc_now,
    )

    operator_review_file = Path(payload["run_record_dir"]) / "operator-review.json"
    operator_review_bytes = operator_review_file.read_bytes()
    artifact = json.loads(operator_review_bytes.decode("utf-8"))
    assert artifact["read_only"] is True
    assert artifact["mutates_paper_state"] is False
    assert artifact["source_daily_runtime_summary"] == payload["summary_file"]
    assert artifact["review_required_count"] == 3
    assert artifact["recorded_count"] == 3
    assert artifact["invalid_count"] == 0
    assert len(artifact["review_outcomes"]) == artifact["recorded_count"]
    assert [item["trade_id"] for item in artifact["review_outcomes"]] == [
        "trade-cost",
        "trade-gs",
        "trade-wmt",
    ]
    assert {item["classification"] for item in artifact["review_outcomes"]} == {
        "stale_open_trade_review_required",
        "unknown_freshness_review_required",
    }
    assert "trade-aapl" not in {item["trade_id"] for item in artifact["review_outcomes"]}
    assert all(item["mutates_paper_state"] is False for item in artifact["review_outcomes"])
    assert all(item["operator_decision"] == "pending_operator_review" for item in artifact["review_outcomes"])
    assert all(item["decision_validity"] == "valid_review_required_evidence" for item in artifact["review_outcomes"])
    assert all(
        item["duplicate_entry_blocker_reason"].startswith("open trade exists for")
        for item in artifact["review_outcomes"]
    )
    assert operator_review_file.with_suffix(".sha256").read_text(encoding="ascii") == (
        f"{hashlib.sha256(operator_review_bytes).hexdigest()}  operator-review.json\n"
    )
    assert not operator_review_file.with_suffix(".json.sha256").exists()
    assert [item for item in request_sequence if "/paper/" in item[1]] == [
        ("GET", "http://127.0.0.1:18000/paper/trades"),
        ("GET", "http://127.0.0.1:18000/paper/positions"),
        ("GET", "http://127.0.0.1:18000/paper/account"),
        ("GET", "http://127.0.0.1:18000/paper/reconciliation"),
    ]
def test_risk_control_activation_reports_all_configurable_controls_inactive() -> None:
    module = _load_script_module()

    evidence = module.build_risk_control_activation_evidence(
        execution_payload={
            "results": [
                {"outcome": "eligible", "signal_id": "sig-ok"},
                {"outcome": "skip:score_below_threshold", "signal_id": "sig-score"},
                {"outcome": "skip:duplicate_entry", "signal_id": "sig-dup"},
            ],
            "risk_profile": {},
        }
    )
    controls = {item["control_id"]: item for item in evidence}

    assert controls["score_threshold_gate"]["active"] is False
    assert controls["score_threshold_gate"]["inactive_reason"] == "min_score_threshold not configured"
    assert controls["score_threshold_gate"]["applied_count"] == 0

    assert controls["duplicate_entry_gate"]["implemented"] is True
    assert controls["duplicate_entry_gate"]["configured"] is True
    assert controls["duplicate_entry_gate"]["active"] is True

    assert controls["stop_distance_sizing"]["active"] is False
    assert controls["stop_distance_sizing"]["inactive_reason"] == "sizing_method is not stop_distance"
    assert controls["stop_distance_sizing"]["applied_count"] == 0

    assert controls["commission_model"]["active"] is False
    assert controls["commission_model"]["inactive_reason"] == (
        "commission_rate is not configured as a numeric value"
    )
    assert controls["commission_model"]["applied_count"] == 0

    assert controls["slippage_model"]["active"] is False
    assert controls["slippage_model"]["inactive_reason"] == (
        "slippage_rate is not configured as a numeric value"
    )
    assert controls["slippage_model"]["applied_count"] == 0

    assert controls["exposure_limits"]["active"] is False
    assert controls["exposure_limits"]["inactive_reason"] == (
        "one or more exposure limit fields are not configured"
    )
    assert controls["exposure_limits"]["applied_count"] == 0

    assert controls["max_concurrent_positions"]["active"] is False
    assert controls["max_concurrent_positions"]["inactive_reason"] == (
        "max_concurrent_positions is not configured"
    )
    assert controls["max_concurrent_positions"]["applied_count"] == 0

    assert controls["correlation_gate"]["active"] is False
    assert controls["correlation_gate"]["inactive_reason"] == (
        "disabled by config: correlation_check_enabled=false"
    )
    assert controls["correlation_gate"]["validation_note"].startswith("Not validated by this run")

    assert controls["drawdown_guard"]["active"] is False
    assert controls["drawdown_guard"]["inactive_reason"] == (
        "disabled by config: drawdown_guard_enabled=false"
    )
    assert controls["drawdown_guard"]["validation_note"].startswith("Not validated by this run")

    assert controls["regime_filter"]["active"] is False
    assert controls["regime_filter"]["inactive_reason"] == (
        "no allowed regimes configured: allowed_regimes is empty"
    )
    assert controls["regime_filter"]["validation_note"].startswith("Not validated by this run")


def test_risk_control_activation_counts_active_applied_and_blocking_outcomes() -> None:
    module = _load_script_module()

    evidence = module.build_risk_control_activation_evidence(
        execution_payload={
            "results": [
                {"outcome": "eligible", "signal_id": "sig-ok"},
                {"outcome": "skip:score_below_threshold", "signal_id": "sig-score"},
                {"outcome": "skip:duplicate_entry", "signal_id": "sig-dup"},
                {"outcome": "reject:missing_trade_risk_input", "signal_id": "sig-risk"},
            ],
            "risk_profile": _default_risk_profile(),
        }
    )
    controls = {item["control_id"]: item for item in evidence}

    assert controls["score_threshold_gate"]["applied_count"] == 4
    assert controls["score_threshold_gate"]["blocked_count"] == 1
    assert controls["duplicate_entry_gate"]["applied_count"] == 3
    assert controls["duplicate_entry_gate"]["blocked_count"] == 1
    assert controls["stop_distance_sizing"]["applied_count"] == 2
    assert controls["stop_distance_sizing"]["blocked_count"] == 1
    assert controls["commission_model"]["applied_count"] == 1
    assert controls["slippage_model"]["applied_count"] == 1


def test_risk_control_activation_reports_active_controls_not_reached() -> None:
    module = _load_script_module()

    evidence = module.build_risk_control_activation_evidence(
        execution_payload={
            "results": [
                {"outcome": "skip:score_below_threshold", "signal_id": "sig-score"},
                {"outcome": "skip:duplicate_entry", "signal_id": "sig-dup"},
            ],
            "risk_profile": _default_risk_profile(),
        }
    )
    controls = {item["control_id"]: item for item in evidence}

    assert controls["stop_distance_sizing"]["active"] is True
    assert controls["stop_distance_sizing"]["applied_count"] == 0
    assert controls["stop_distance_sizing"]["skipped_count"] == 2
    assert "candidates reaching sizing" in controls["stop_distance_sizing"]["validation_note"]
    assert controls["exposure_limits"]["active"] is True
    assert controls["exposure_limits"]["applied_count"] == 0
    assert controls["exposure_limits"]["skipped_count"] == 2


def test_risk_control_activation_reports_implemented_control_inactive_due_to_config() -> None:
    module = _load_script_module()
    risk_profile = {**_default_risk_profile(), "sizing_method": "fixed"}

    evidence = module.build_risk_control_activation_evidence(
        execution_payload={
            "results": [{"outcome": "eligible", "signal_id": "sig-ok"}],
            "risk_profile": risk_profile,
        }
    )
    controls = {item["control_id"]: item for item in evidence}

    assert controls["stop_distance_sizing"]["implemented"] is True
    assert controls["stop_distance_sizing"]["configured"] is False
    assert controls["stop_distance_sizing"]["active"] is False
    assert controls["stop_distance_sizing"]["inactive_reason"] == "sizing_method is not stop_distance"
    assert controls["stop_distance_sizing"]["applied_count"] == 0
    assert "Not validated by this run" in controls["stop_distance_sizing"]["validation_note"]


def test_risk_control_activation_preserves_execution_and_reconciliation_inputs() -> None:
    module = _load_script_module()
    execution_step = {
        "returncode": 1,
        "payload": {
            "eligible": 0,
            "results": [{"outcome": "skip:score_below_threshold"}],
            "risk_profile": _default_risk_profile(),
            "status": "no_eligible",
        },
    }
    reconciliation_step = {"payload": {"ok": True, "mismatches": 0}}

    before_run_quality = module._classify_run_quality(
        execution_step=execution_step,
        reconciliation_step=reconciliation_step,
    )
    evidence = module.build_risk_control_activation_evidence(
        execution_payload=execution_step["payload"],
    )
    after_run_quality = module._classify_run_quality(
        execution_step=execution_step,
        reconciliation_step=reconciliation_step,
    )

    assert before_run_quality == after_run_quality
    assert before_run_quality["run_quality_status"] == "no_eligible"
    assert before_run_quality["run_quality_inputs"]["reconciliation_ok"] is True
    assert execution_step["payload"]["results"] == [{"outcome": "skip:score_below_threshold"}]
    assert evidence[0]["control_id"] == "score_threshold_gate"


def test_paper_state_freshness_evidence_handles_no_open_trades() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={"items": [], "total": 0},
        positions_payload={"items": [], "total": 0},
        account_payload={"account": {"as_of": "2026-04-06T12:00:00+00:00"}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["freshness"] == "fresh"
    assert evidence["account_freshness"] == "fresh"
    assert evidence["account_age_seconds"] == 0
    assert evidence["open_trade_count"] == 0
    assert evidence["duplicate_entry_blocker_count"] == 0
    assert evidence["review_required_count"] == 0
    assert evidence["open_trades"] == []


def test_paper_state_freshness_evidence_classifies_fresh_open_trade_blocker() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-04-06T10:00:00+00:00",
                    "position_id": "pos-1",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-1",
                }
            ],
            "total": 1,
        },
        positions_payload={"items": [{"position_id": "pos-1", "status": "open"}], "total": 1},
        account_payload={"account": {"as_of": "2026-04-06T11:30:00+00:00"}},
        execution_payload={
            "results": [{"outcome": "skip:duplicate_entry", "signal_id": "sig-1"}]
        },
        signals_payload={
            "items": [
                {
                    "direction": "long",
                    "signal_id": "sig-1",
                    "strategy": "TURTLE",
                    "symbol": "WMT",
                }
            ]
        },
        observed_at=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["freshness"] == "fresh"
    assert evidence["duplicate_entry_blocker_count"] == 1
    assert evidence["review_required_count"] == 0
    assert evidence["open_trades"][0]["classification"] == "fresh_open_trade_blocker"
    assert evidence["open_trades"][0]["duplicate_entry_blocker"] is True
    assert evidence["open_trades"][0]["position_id"] == "pos-1"
    assert evidence["open_trades"][0]["account_age_seconds"] == 1800
    assert evidence["open_trades"][0]["trade_age_seconds"] == 7200
    assert evidence["open_trades"][0]["account_freshness"] == "fresh"
    assert evidence["open_trades"][0]["trade_freshness"] == "fresh"


def test_paper_state_freshness_evidence_classifies_old_open_trade_blocker_for_review() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "425",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-gs",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "GS",
                    "trade_id": "trade-gs",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-gs", "status": "open"}]},
        account_payload={"account": {"as_of": "2026-04-02T00:00:00+00:00"}},
        execution_payload={
            "results": [
                {
                    "direction": "long",
                    "outcome": "skip:duplicate_entry",
                    "strategy": "TURTLE",
                    "symbol": "GS",
                }
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["freshness"] == "stale"
    assert evidence["age_seconds"] == 2980800
    assert evidence["account_freshness"] == "stale"
    assert evidence["account_age_seconds"] == 2980800
    assert evidence["duplicate_entry_blocker_count"] == 1
    assert evidence["review_required_count"] == 1
    assert evidence["open_trades"][0]["classification"] == "stale_open_trade_review_required"
    assert evidence["open_trades"][0]["trade_age_seconds"] == 2980800
    assert evidence["open_trades"][0]["trade_freshness"] == "stale"
    assert "operator must review lifecycle evidence" in evidence["open_trades"][0]["operator_review_guidance"]


def test_paper_state_freshness_evidence_classifies_unknown_metadata_for_review() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "900",
                    "direction": "long",
                    "opened_at": None,
                    "position_id": "pos-cost",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "COST",
                    "trade_id": "trade-cost",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-cost", "status": "open"}]},
        account_payload={"account": {"as_of": None}},
        execution_payload={
            "results": [
                {
                    "direction": "long",
                    "outcome": "skip:duplicate_entry",
                    "strategy": "TURTLE",
                    "symbol": "COST",
                }
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["freshness"] == "unknown"
    assert evidence["age_seconds"] is None
    assert evidence["account_freshness"] == "unknown"
    assert evidence["account_age_seconds"] is None
    assert evidence["duplicate_entry_blocker_count"] == 1
    assert evidence["review_required_count"] == 1
    assert evidence["open_trades"][0]["classification"] == "unknown_freshness_review_required"
    assert evidence["open_trades"][0]["trade_age_seconds"] is None
    assert evidence["open_trades"][0]["trade_freshness"] == "unknown"
    assert "freshness cannot be established" in evidence["operator_review_guidance"]


def test_paper_state_freshness_evidence_parses_duplicate_entry_reason_strings() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-05-06T11:00:00+00:00",
                    "position_id": "pos-wmt",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-wmt",
                },
                {
                    "average_entry_price": "425",
                    "direction": "long",
                    "opened_at": "2026-05-06T11:00:00+00:00",
                    "position_id": "pos-gs",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "GS",
                    "trade_id": "trade-gs",
                },
                {
                    "average_entry_price": "900",
                    "direction": "long",
                    "opened_at": "2026-05-06T11:00:00+00:00",
                    "position_id": "pos-cost",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "COST",
                    "trade_id": "trade-cost",
                },
            ]
        },
        positions_payload={
            "items": [
                {"position_id": "pos-wmt", "status": "open"},
                {"position_id": "pos-gs", "status": "open"},
                {"position_id": "pos-cost", "status": "open"},
            ]
        },
        account_payload={"account": {"as_of": "2026-05-06T12:00:00+00:00"}},
        execution_payload={
            "results": [
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (WMT, TURTLE, long)",
                },
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (GS, TURTLE, long)",
                },
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (COST, TURTLE, long)",
                },
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["duplicate_entry_blocker_count"] == 3
    assert [item["symbol"] for item in evidence["open_trades"]] == ["COST", "GS", "WMT"]
    assert {item["classification"] for item in evidence["open_trades"]} == {"fresh_open_trade_blocker"}
    assert all(item["duplicate_entry_blocker"] is True for item in evidence["open_trades"])


def test_paper_state_freshness_evidence_separates_fresh_account_from_old_trade_age() -> None:
    module = _load_script_module()

    evidence = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-wmt",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-wmt",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-wmt", "status": "open"}]},
        account_payload={"account": {"as_of": "2026-05-06T12:00:00+00:00"}},
        execution_payload={
            "results": [
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (WMT, TURTLE, long)",
                }
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert evidence["account_freshness"] == "fresh"
    assert evidence["account_age_seconds"] == 0
    assert evidence["open_trades"][0]["account_freshness"] == "fresh"
    assert evidence["open_trades"][0]["account_age_seconds"] == 0
    assert evidence["open_trades"][0]["trade_freshness"] == "stale"
    assert evidence["open_trades"][0]["trade_age_seconds"] == 2980800
    assert evidence["open_trades"][0]["classification"] == "stale_open_trade_review_required"


def test_operator_review_artifact_records_each_stale_duplicate_entry_blocker() -> None:
    module = _load_script_module()

    paper_state_freshness = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "190",
                    "direction": "long",
                    "opened_at": "2026-05-06T11:00:00+00:00",
                    "position_id": "pos-aapl",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "AAPL",
                    "trade_id": "trade-aapl",
                },
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-wmt",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-wmt",
                },
                {
                    "average_entry_price": "425",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-gs",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "GS",
                    "trade_id": "trade-gs",
                },
                {
                    "average_entry_price": "900",
                    "direction": "long",
                    "opened_at": None,
                    "position_id": "pos-cost",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "COST",
                    "trade_id": "trade-cost",
                },
            ]
        },
        positions_payload={
            "items": [
                {"position_id": "pos-aapl", "status": "open"},
                {"position_id": "pos-wmt", "status": "open"},
                {"position_id": "pos-gs", "status": "open"},
                {"position_id": "pos-cost", "status": "open"},
            ]
        },
        account_payload={"account": {"as_of": "2026-05-06T12:00:00+00:00"}},
        execution_payload={
            "results": [
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (WMT, TURTLE, long)",
                },
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (GS, TURTLE, long)",
                },
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (COST, TURTLE, long)",
                },
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    artifact = module.build_operator_review_outcome_artifact(
        paper_state_freshness=paper_state_freshness,
        source_daily_runtime_summary="runs/daily-runtime/2026-05-06/daily-runtime-summary.json",
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    duplicate_artifact = module.build_operator_review_outcome_artifact(
        paper_state_freshness=paper_state_freshness,
        source_daily_runtime_summary="runs/daily-runtime/2026-05-06/daily-runtime-summary.json",
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact == duplicate_artifact
    assert module._json_file_bytes(artifact) == module._json_file_bytes(duplicate_artifact)
    assert artifact["workflow_id"] == "bounded_daily_paper_runtime"
    assert artifact["workflow_version"] == "OPS-P64"
    assert artifact["artifact_id"] == "operator-review"
    assert artifact["artifact_version"] == 1
    assert artifact["read_only"] is True
    assert artifact["mutates_paper_state"] is False
    assert artifact["source_daily_runtime_summary"] == "runs/daily-runtime/2026-05-06/daily-runtime-summary.json"
    assert artifact["observed_at"] == "2026-05-06T12:00:00+00:00"
    assert artifact["review_required_count"] == 3
    assert artifact["recorded_count"] == 3
    assert artifact["invalid_count"] == 0
    assert "not trader validation" in artifact["non_inference_statement"]
    assert "not profitability evidence" in artifact["non_inference_statement"]
    assert "not broker/live readiness" in artifact["non_inference_statement"]
    assert len(artifact["review_outcomes"]) == artifact["recorded_count"]
    assert [item["trade_id"] for item in artifact["review_outcomes"]] == [
        "trade-cost",
        "trade-gs",
        "trade-wmt",
    ]
    assert {item["classification"] for item in artifact["review_outcomes"]} == {
        "stale_open_trade_review_required",
        "unknown_freshness_review_required",
    }
    assert "trade-aapl" not in {item["trade_id"] for item in artifact["review_outcomes"]}
    required_outcome_fields = {
        "account_as_of",
        "account_freshness",
        "decision_validity",
        "direction",
        "duplicate_entry_blocker",
        "duplicate_entry_blocker_reason",
        "mutates_paper_state",
        "opened_at",
        "operator_decision",
        "operator_rationale",
        "position_id",
        "status",
        "strategy",
        "symbol",
        "trade_freshness",
        "trade_id",
    }
    assert all(required_outcome_fields <= set(item) for item in artifact["review_outcomes"])
    assert all(item["duplicate_entry_blocker"] is True for item in artifact["review_outcomes"])
    assert all(item["mutates_paper_state"] is False for item in artifact["review_outcomes"])
    assert all(item["operator_decision"] == "pending_operator_review" for item in artifact["review_outcomes"])
    assert all(item["operator_rationale"] for item in artifact["review_outcomes"])
    assert all(item["decision_validity"] == "valid_review_required_evidence" for item in artifact["review_outcomes"])


def test_run_quality_classification_state_transitions_are_deterministic() -> None:
    module = _load_script_module()

    healthy = module._classify_run_quality(
        execution_step={"returncode": 0, "payload": {"status": "pass", "eligible": 3}},
        reconciliation_step={"payload": {"ok": True, "mismatches": 0}},
    )
    no_eligible = module._classify_run_quality(
        execution_step={"returncode": 1, "payload": {"status": "no_eligible", "eligible": 0}},
        reconciliation_step={"payload": {"ok": True, "mismatches": 0}},
    )
    degraded = module._classify_run_quality(
        execution_step={"returncode": 0, "payload": {"status": "pass", "eligible": 3}},
        reconciliation_step={"payload": {"ok": False, "mismatches": 2}},
    )
    degraded_repeat = module._classify_run_quality(
        execution_step={"returncode": 0, "payload": {"status": "pass", "eligible": 3}},
        reconciliation_step={"payload": {"ok": False, "mismatches": 2}},
    )
    healthy_repeat = module._classify_run_quality(
        execution_step={"returncode": 0, "payload": {"status": "pass", "eligible": 3}},
        reconciliation_step={"payload": {"ok": True, "mismatches": 0}},
    )

    assert healthy["run_quality_status"] == "healthy"
    assert healthy["operator_action_contract_version"] == 1
    assert healthy["operator_action_contract"] == {
        "action_category": "informational",
        "action_code": "record_and_continue",
        "action_summary": "Record the bounded daily runtime evidence and continue the next scheduled bounded run.",
        "escalation_boundary": "No escalation from this state alone. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert no_eligible["run_quality_status"] == "no_eligible"
    assert no_eligible["operator_action_contract"] == {
        "action_category": "review_required",
        "action_code": "review_no_eligible_and_record",
        "action_summary": "Review the bounded no-eligible outcome, confirm skip reasons and inputs, and record the run without retrying solely to force activity.",
        "escalation_boundary": "Escalate only when adjacent bounded evidence is contradictory or the no-eligible pattern is unexpected for the stated inputs. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert degraded["run_quality_status"] == "degraded"
    assert degraded["operator_action_contract"] == {
        "action_category": "blocking",
        "action_code": "stop_and_open_follow_up",
        "action_summary": "Treat the bounded run as blocked for continuation claims, investigate the degraded evidence, and open or update follow-up before the next bounded decision.",
        "escalation_boundary": "Do not continue staged evaluation claims from this run until the degraded cause is resolved. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert healthy == healthy_repeat
    assert degraded == degraded_repeat


def test_daily_runner_stops_after_analysis_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()

    executed_scripts: list[str] = []

    def _fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        script_name = Path(command[1]).name
        executed_scripts.append(script_name)
        if script_name == "run_snapshot_ingestion.py":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"result": {"ingestion_run_id": "ing-456"}}) + "\n",
                stderr="",
            )
        raise AssertionError(f"Unexpected script invocation after analysis failure: {script_name}")

    def _fake_request_json(
        url: str,
        *,
        headers: dict[str, str],
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        assert url.endswith("/analysis/run")
        raise urllib.error.URLError("connection-refused")

    monkeypatch.setattr(module, "_run_command", _fake_run_command)
    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(
        module,
        "_utc_now",
        lambda: datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_daily_bounded_paper_runtime.py",
            "--db-path",
            str(tmp_path / "analysis.db"),
        ],
    )

    exit_code = module.main()

    assert exit_code == module.EXIT_CODE_ANALYSIS_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "failed"
    assert payload["failed_step"] == "analysis_signal_generation"
    assert payload["operator_action_contract_version"] == 1
    assert payload["operator_action_contract"] == {
        "action_category": "retry_required",
        "action_code": "fix_pre_execution_failure_and_rerun",
        "action_summary": "Correct the pre-execution failure cause and rerun the bounded daily workflow.",
        "escalation_boundary": "Retry is bounded to failures before paper execution starts. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert payload["steps_completed"] == ["snapshot_ingestion"]
    assert executed_scripts == ["run_snapshot_ingestion.py"]


def test_daily_runner_stops_after_execution_failure(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()

    executed_scripts: list[str] = []

    def _fake_run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        script_name = Path(command[1]).name
        executed_scripts.append(script_name)
        if script_name == "run_snapshot_ingestion.py":
            return subprocess.CompletedProcess(
                command,
                0,
                stdout=json.dumps({"result": {"ingestion_run_id": "ing-789"}}) + "\n",
                stderr="",
            )
        if script_name == "run_paper_execution_cycle.py":
            return subprocess.CompletedProcess(
                command,
                2,
                stdout="",
                stderr=json.dumps({"code": "paper_execution_cycle_runtime_error"}) + "\n",
            )
        raise AssertionError(f"Unexpected script invocation after execution failure: {script_name}")

    def _fake_request_json(
        url: str,
        *,
        headers: dict[str, str],
        method: str = "GET",
        payload: dict[str, object] | None = None,
    ) -> dict[str, object]:
        assert url.endswith("/analysis/run")
        return {
            "analysis_run_id": "analysis-789",
            "ingestion_run_id": "ing-789",
            "signals": [],
            "strategy": "RSI2",
            "symbol": "AAPL",
        }

    monkeypatch.setattr(module, "_run_command", _fake_run_command)
    monkeypatch.setattr(module, "_request_json", _fake_request_json)
    monkeypatch.setattr(
        module,
        "_utc_now",
        lambda: datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_daily_bounded_paper_runtime.py",
            "--db-path",
            str(tmp_path / "analysis.db"),
        ],
    )

    exit_code = module.main()

    assert exit_code == module.EXIT_CODE_EXECUTION_FAILED
    payload = json.loads(capsys.readouterr().err)
    assert payload["status"] == "failed"
    assert payload["failed_step"] == "bounded_paper_execution_cycle"
    assert payload["operator_action_contract_version"] == 1
    assert payload["operator_action_contract"] == {
        "action_category": "blocking",
        "action_code": "stop_and_investigate_before_rerun",
        "action_summary": "Stop and investigate the bounded execution failure before any rerun decision.",
        "escalation_boundary": "Do not rerun the full workflow blindly after execution has started. Do not treat bounded paper evidence as live, broker, or production readiness.",
    }
    assert payload["steps_completed"] == [
        "snapshot_ingestion",
        "analysis_signal_generation",
    ]
    assert executed_scripts == [
        "run_snapshot_ingestion.py",
        "run_paper_execution_cycle.py",
    ]


def _stale_paper_state_freshness_evidence(module) -> dict[str, object]:
    return module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "425",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-gs",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "GS",
                    "trade_id": "trade-gs",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-gs", "status": "open"}]},
        account_payload={"account": {"as_of": "2026-04-02T00:00:00+00:00"}},
        execution_payload={
            "results": [
                {
                    "outcome": "skip:duplicate_entry",
                    "reason": "open trade exists for (GS, TURTLE, long)",
                }
            ]
        },
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )


def test_stale_open_paper_trade_review_workflow_no_stale_trades_returns_no_review_required() -> None:
    module = _load_script_module()

    freshness = module.build_paper_state_freshness_evidence(
        trades_payload={"items": []},
        positions_payload={"items": []},
        account_payload={"account": {"as_of": "2026-04-06T12:00:00+00:00"}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    assert workflow["workflow_id"] == "ops_bounded_stale_open_paper_trade_review"
    assert workflow["mode"] == "bounded_stale_paper_trade_review"
    assert workflow["read_only"] is True
    assert workflow["mutates_paper_state"] is False
    assert workflow["workflow_status"] == "no_review_required"
    assert workflow["review_required_count"] == 0
    assert workflow["duplicate_entry_blocker_review_count"] == 0
    assert workflow["non_duplicate_entry_blocker_review_count"] == 0
    assert workflow["unknown_freshness_review_count"] == 0
    assert workflow["stale_open_trades"] == []
    assert "no operator review action is required" in workflow["review_guidance"]


def test_stale_open_paper_trade_review_workflow_lists_stale_trades_with_duplicate_entry_blockers() -> None:
    module = _load_script_module()

    freshness = _stale_paper_state_freshness_evidence(module)
    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    assert workflow["workflow_status"] == "review_required"
    assert workflow["review_required_count"] == 1
    assert workflow["duplicate_entry_blocker_review_count"] == 1
    assert workflow["non_duplicate_entry_blocker_review_count"] == 0
    assert workflow["unknown_freshness_review_count"] == 0
    assert len(workflow["stale_open_trades"]) == 1

    entry = workflow["stale_open_trades"][0]
    assert entry["trade_id"] == "trade-gs"
    assert entry["position_id"] == "pos-gs"
    assert entry["symbol"] == "GS"
    assert entry["strategy"] == "TURTLE"
    assert entry["direction"] == "long"
    assert entry["status"] == "open"
    assert entry["opened_at"] == "2026-04-02T00:00:00+00:00"
    assert entry["account_as_of"] == "2026-04-02T00:00:00+00:00"
    assert entry["trade_age_seconds"] == 2980800
    assert entry["account_age_seconds"] == 2980800
    assert entry["trade_freshness"] == "stale"
    assert entry["account_freshness"] == "stale"
    assert entry["freshness"] == "stale"
    assert entry["duplicate_entry_blocker"] is True
    assert entry["duplicate_entry_blocker_reason"] == "open trade exists for (GS, TURTLE, long)"
    assert entry["classification"] == "stale_open_trade_review_required"
    assert entry["review_classification"] == "stale_open_trade_review_required"
    assert "operator must review lifecycle evidence" in entry["operator_review_guidance"]


def test_stale_open_paper_trade_review_workflow_lists_stale_trades_without_duplicate_entry_blockers() -> None:
    module = _load_script_module()

    freshness = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-wmt",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-wmt",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-wmt", "status": "open"}]},
        account_payload={"account": {"as_of": "2026-04-02T00:00:00+00:00"}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    assert workflow["workflow_status"] == "review_required"
    assert workflow["review_required_count"] == 1
    assert workflow["duplicate_entry_blocker_review_count"] == 0
    assert workflow["non_duplicate_entry_blocker_review_count"] == 1
    assert workflow["unknown_freshness_review_count"] == 0
    entry = workflow["stale_open_trades"][0]
    assert entry["symbol"] == "WMT"
    assert entry["duplicate_entry_blocker"] is False
    assert entry["duplicate_entry_blocker_reason"] is None
    assert entry["review_classification"] == "stale_open_trade_review_required"


def test_stale_open_paper_trade_review_workflow_handles_unknown_freshness() -> None:
    module = _load_script_module()

    freshness = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "900",
                    "direction": "long",
                    "opened_at": None,
                    "position_id": "pos-cost",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "COST",
                    "trade_id": "trade-cost",
                }
            ]
        },
        positions_payload={"items": [{"position_id": "pos-cost", "status": "open"}]},
        account_payload={"account": {"as_of": None}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )

    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    assert workflow["workflow_status"] == "review_required"
    assert workflow["review_required_count"] == 1
    assert workflow["unknown_freshness_review_count"] == 1
    entry = workflow["stale_open_trades"][0]
    assert entry["trade_freshness"] == "unknown"
    assert entry["account_freshness"] == "unknown"
    assert entry["freshness"] == "unknown"
    assert entry["review_classification"] == "unknown_freshness_review_required"
    assert entry["trade_age_seconds"] is None
    assert entry["account_age_seconds"] is None


def test_stale_open_paper_trade_review_workflow_includes_prohibited_actions_and_non_inference_statement() -> None:
    module = _load_script_module()

    freshness = _stale_paper_state_freshness_evidence(module)
    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    allowed_codes = {action["action_code"] for action in workflow["allowed_actions"]}
    prohibited_codes = {action["action_code"] for action in workflow["prohibited_actions"]}

    assert allowed_codes == {
        "inspect_trade_lifecycle_evidence",
        "compare_with_paper_inspection_surfaces",
        "record_review_outcome_externally",
    }
    assert prohibited_codes == {
        "auto_close_trade",
        "reset_paper_state",
        "mark_to_market",
        "force_eligible_trade_creation",
        "lower_thresholds_to_bypass_stale_blockers",
        "infer_trader_validation_or_profitability",
    }
    assert workflow["read_only"] is True
    assert workflow["mutates_paper_state"] is False
    assert "not trader validation" in workflow["non_inference_statement"]
    assert "not profitability evidence" in workflow["non_inference_statement"]


def test_stale_open_paper_trade_review_workflow_does_not_mutate_paper_state_inputs() -> None:
    module = _load_script_module()

    trades_payload = {
        "items": [
            {
                "average_entry_price": "425",
                "direction": "long",
                "opened_at": "2026-04-02T00:00:00+00:00",
                "position_id": "pos-gs",
                "quantity_closed": "0",
                "quantity_opened": "1",
                "status": "open",
                "strategy_id": "TURTLE",
                "symbol": "GS",
                "trade_id": "trade-gs",
            }
        ]
    }
    positions_payload = {"items": [{"position_id": "pos-gs", "status": "open"}]}
    account_payload = {"account": {"as_of": "2026-04-02T00:00:00+00:00"}}
    execution_payload = {
        "results": [
            {
                "outcome": "skip:duplicate_entry",
                "reason": "open trade exists for (GS, TURTLE, long)",
            }
        ]
    }
    signals_payload = {"items": []}

    expected_trades = deepcopy(trades_payload)
    expected_positions = deepcopy(positions_payload)
    expected_account = deepcopy(account_payload)
    expected_execution = deepcopy(execution_payload)
    expected_signals = deepcopy(signals_payload)

    freshness = module.build_paper_state_freshness_evidence(
        trades_payload=trades_payload,
        positions_payload=positions_payload,
        account_payload=account_payload,
        execution_payload=execution_payload,
        signals_payload=signals_payload,
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    expected_freshness = deepcopy(freshness)

    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    assert workflow["workflow_status"] == "review_required"
    assert workflow["mutates_paper_state"] is False
    assert trades_payload == expected_trades
    assert positions_payload == expected_positions
    assert account_payload == expected_account
    assert execution_payload == expected_execution
    assert signals_payload == expected_signals
    assert freshness == expected_freshness


def _empty_review_workflow(module) -> dict[str, object]:
    freshness = module.build_paper_state_freshness_evidence(
        trades_payload={"items": []},
        positions_payload={"items": []},
        account_payload={"account": {"as_of": "2026-04-06T12:00:00+00:00"}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 4, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    return module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )


def _stale_review_workflow(module) -> dict[str, object]:
    freshness = _stale_paper_state_freshness_evidence(module)
    return module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )


def test_review_outcome_artifact_no_stale_trades_returns_no_review_required() -> None:
    module = _load_script_module()

    workflow = _empty_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={"reviewer_id": "ops_alice", "decisions": []},
        observed_at=datetime(2026, 5, 7, 0, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["artifact_id"] == "ops_bounded_stale_open_paper_trade_review_outcome"
    assert artifact["artifact_version"] == 1
    assert artifact["workflow_id"] == "ops_bounded_stale_open_paper_trade_review"
    assert artifact["mode"] == "bounded_stale_paper_trade_review"
    assert artifact["review_outcome_status"] == "no_review_required"
    assert artifact["reviewed_trade_count"] == 0
    assert artifact["reviewed_stale_open_trades"] == []
    assert artifact["reviewer_id"] == "ops_alice"
    assert artifact["mutates_paper_state"] is False
    assert artifact["read_only"] is True
    assert artifact["observed_at"] == "2026-05-07T00:00:00+00:00"


def test_review_outcome_artifact_records_valid_decision_for_stale_duplicate_blocker() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={
            "reviewer_id": "ops_bob",
            "decisions": [
                {
                    "trade_id": "trade-gs",
                    "decision": "acknowledged_no_action",
                    "rationale": "Duplicate-entry blocker is technically valid; awaiting next snapshot.",
                }
            ],
        },
        observed_at=datetime(2026, 5, 7, 1, 0, 0, tzinfo=timezone.utc),
        source_summary_reference="runs/daily-runtime/2026-05-06/daily-runtime-summary-20260506T120000Z.json",
    )

    assert artifact["review_outcome_status"] == "recorded"
    assert artifact["reviewer_id"] == "ops_bob"
    assert artifact["reviewed_trade_count"] == 1
    assert artifact["valid_decision_count"] == 1
    assert artifact["invalid_decision_count"] == 0
    assert artifact["missing_decision_count"] == 0
    assert artifact["prohibited_decision_count"] == 0
    assert artifact["duplicate_payload_decision_count"] == 0
    assert artifact["unmatched_payload_decision_trade_ids"] == []
    assert artifact["source_summary_reference"] == (
        "runs/daily-runtime/2026-05-06/daily-runtime-summary-20260506T120000Z.json"
    )

    entry = artifact["reviewed_stale_open_trades"][0]
    assert entry["trade_id"] == "trade-gs"
    assert entry["position_id"] == "pos-gs"
    assert entry["symbol"] == "GS"
    assert entry["strategy"] == "TURTLE"
    assert entry["direction"] == "long"
    assert entry["opened_at"] == "2026-04-02T00:00:00+00:00"
    assert entry["account_as_of"] == "2026-04-02T00:00:00+00:00"
    assert entry["trade_freshness"] == "stale"
    assert entry["account_freshness"] == "stale"
    assert entry["duplicate_entry_blocker"] is True
    assert entry["duplicate_entry_blocker_reason"] == "open trade exists for (GS, TURTLE, long)"
    assert entry["review_classification"] == "stale_open_trade_review_required"
    assert entry["operator_decision"] == "acknowledged_no_action"
    assert entry["operator_rationale"].startswith("Duplicate-entry blocker is technically valid")
    assert entry["decision_validity"] == "valid"


def test_review_outcome_artifact_reviewer_id_defaults_to_not_provided() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={
            "decisions": [
                {
                    "trade_id": "trade-gs",
                    "decision": "needs_followup",
                    "rationale": "Open external follow-up to inspect lifecycle evidence.",
                }
            ],
        },
        observed_at=datetime(2026, 5, 7, 2, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["reviewer_id"] == "not_provided"
    assert artifact["review_outcome_status"] == "recorded"
    assert artifact["source_summary_reference"] is None


def test_review_outcome_artifact_classifies_invalid_payload_without_mutating_inputs() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    expected_workflow = deepcopy(workflow)
    review_payload = {
        "reviewer_id": "  ",
        "decisions": [
            {"trade_id": "trade-gs", "decision": "auto_close_trade", "rationale": "force close"},
            {"trade_id": "trade-unknown", "decision": "acknowledged_no_action", "rationale": "n/a"},
        ],
    }
    expected_payload = deepcopy(review_payload)

    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload=review_payload,
        observed_at=datetime(2026, 5, 7, 3, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["review_outcome_status"] == "invalid_payload"
    assert artifact["reviewer_id"] == "not_provided"
    assert artifact["reviewed_trade_count"] == 1
    assert artifact["valid_decision_count"] == 0
    assert artifact["invalid_decision_count"] == 1
    assert artifact["prohibited_decision_count"] == 1
    assert artifact["unmatched_payload_decision_trade_ids"] == ["trade-unknown"]

    entry = artifact["reviewed_stale_open_trades"][0]
    assert entry["operator_decision"] == "auto_close_trade"
    assert entry["decision_validity"] == "prohibited_decision"
    assert artifact["mutates_paper_state"] is False

    # Inputs must remain untouched.
    assert workflow == expected_workflow
    assert review_payload == expected_payload


def test_review_outcome_artifact_classifies_missing_decision_and_missing_rationale() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={"decisions": [{"trade_id": "trade-gs", "decision": "needs_followup"}]},
        observed_at=datetime(2026, 5, 7, 4, 0, 0, tzinfo=timezone.utc),
    )

    entry = artifact["reviewed_stale_open_trades"][0]
    assert entry["decision_validity"] == "missing_rationale"
    assert artifact["review_outcome_status"] == "invalid_payload"
    assert artifact["valid_decision_count"] == 0
    assert artifact["invalid_decision_count"] == 1

    artifact_no_decision = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={"decisions": []},
        observed_at=datetime(2026, 5, 7, 4, 30, 0, tzinfo=timezone.utc),
    )
    entry_no_decision = artifact_no_decision["reviewed_stale_open_trades"][0]
    assert entry_no_decision["decision_validity"] == "missing_decision"
    assert entry_no_decision["operator_decision"] is None
    assert entry_no_decision["operator_rationale"] is None
    assert artifact_no_decision["missing_decision_count"] == 1
    assert artifact_no_decision["review_outcome_status"] == "invalid_payload"


def test_review_outcome_artifact_includes_prohibited_actions_and_non_inference_statement() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={
            "reviewer_id": "ops_carol",
            "decisions": [
                {
                    "trade_id": "trade-gs",
                    "decision": "acknowledged_no_action",
                    "rationale": "ok",
                }
            ],
        },
        observed_at=datetime(2026, 5, 7, 5, 0, 0, tzinfo=timezone.utc),
    )

    prohibited_action_codes = {item["action_code"] for item in artifact["prohibited_actions"]}
    assert prohibited_action_codes == {
        "auto_close_trade",
        "reset_paper_state",
        "mark_to_market",
        "force_eligible_trade_creation",
        "lower_thresholds_to_bypass_stale_blockers",
        "infer_trader_validation_or_profitability",
    }
    assert set(artifact["prohibited_decisions"]) == prohibited_action_codes
    assert "acknowledged_no_action" in artifact["allowed_decisions"]
    assert "needs_followup" in artifact["allowed_decisions"]
    assert artifact["mutates_paper_state"] is False
    assert artifact["read_only"] is True
    assert "not trader validation" in artifact["non_inference_statement"]
    assert "not profitability evidence" in artifact["non_inference_statement"]


def test_review_outcome_artifact_partially_recorded_when_some_decisions_invalid() -> None:
    module = _load_script_module()

    # Build a freshness evidence with two stale open trades.
    freshness = module.build_paper_state_freshness_evidence(
        trades_payload={
            "items": [
                {
                    "average_entry_price": "425",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-gs",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "GS",
                    "trade_id": "trade-gs",
                },
                {
                    "average_entry_price": "100",
                    "direction": "long",
                    "opened_at": "2026-04-02T00:00:00+00:00",
                    "position_id": "pos-wmt",
                    "quantity_closed": "0",
                    "quantity_opened": "1",
                    "status": "open",
                    "strategy_id": "TURTLE",
                    "symbol": "WMT",
                    "trade_id": "trade-wmt",
                },
            ]
        },
        positions_payload={"items": []},
        account_payload={"account": {"as_of": "2026-04-02T00:00:00+00:00"}},
        execution_payload={"results": []},
        signals_payload={"items": []},
        observed_at=datetime(2026, 5, 6, 12, 0, 0, tzinfo=timezone.utc),
    )
    workflow = module.build_stale_open_paper_trade_review_workflow(
        paper_state_freshness=freshness,
    )

    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={
            "reviewer_id": "ops_dave",
            "decisions": [
                {
                    "trade_id": "trade-gs",
                    "decision": "acknowledged_no_action",
                    "rationale": "Lifecycle evidence inspected.",
                },
                {"trade_id": "trade-wmt", "decision": "reset_paper_state", "rationale": "no"},
            ],
        },
        observed_at=datetime(2026, 5, 7, 6, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["review_outcome_status"] == "partially_recorded"
    assert artifact["reviewed_trade_count"] == 2
    assert artifact["valid_decision_count"] == 1
    assert artifact["invalid_decision_count"] == 1
    assert artifact["prohibited_decision_count"] == 1
    # Sorted by symbol so GS comes first.
    assert [entry["symbol"] for entry in artifact["reviewed_stale_open_trades"]] == ["GS", "WMT"]
    assert artifact["reviewed_stale_open_trades"][0]["decision_validity"] == "valid"
    assert artifact["reviewed_stale_open_trades"][1]["decision_validity"] == "prohibited_decision"


def test_review_outcome_artifact_is_deterministic_for_identical_inputs() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    payload = {
        "reviewer_id": "ops_eve",
        "decisions": [
            {
                "trade_id": "trade-gs",
                "decision": "acknowledged_no_action",
                "rationale": "ok",
            }
        ],
    }
    observed_at = datetime(2026, 5, 7, 7, 0, 0, tzinfo=timezone.utc)

    first = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload=payload,
        observed_at=observed_at,
    )
    second = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=deepcopy(workflow),
        review_payload=deepcopy(payload),
        observed_at=observed_at,
    )

    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)


def test_review_outcome_artifact_handles_invalid_workflow_and_payload_types() -> None:
    module = _load_script_module()

    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=None,
        review_payload=None,
        observed_at=datetime(2026, 5, 7, 8, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["workflow_id"] == "ops_bounded_stale_open_paper_trade_review"
    assert artifact["workflow_version"] == 1
    assert artifact["mode"] == "bounded_stale_paper_trade_review"
    assert artifact["reviewed_stale_open_trades"] == []
    assert artifact["review_outcome_status"] == "no_review_required"
    assert artifact["reviewer_id"] == "not_provided"
    assert artifact["mutates_paper_state"] is False


def test_review_outcome_artifact_counts_duplicate_payload_decisions() -> None:
    module = _load_script_module()

    workflow = _stale_review_workflow(module)
    artifact = module.build_stale_open_paper_trade_review_outcome_artifact(
        stale_open_paper_trade_review_workflow=workflow,
        review_payload={
            "decisions": [
                {
                    "trade_id": "trade-gs",
                    "decision": "acknowledged_no_action",
                    "rationale": "first",
                },
                {
                    "trade_id": "trade-gs",
                    "decision": "needs_followup",
                    "rationale": "duplicate-second",
                },
            ]
        },
        observed_at=datetime(2026, 5, 7, 9, 0, 0, tzinfo=timezone.utc),
    )

    assert artifact["duplicate_payload_decision_count"] == 1
    # First decision wins; trade entry uses the initial decision deterministically.
    entry = artifact["reviewed_stale_open_trades"][0]
    assert entry["operator_decision"] == "acknowledged_no_action"
    assert entry["operator_rationale"] == "first"
    assert entry["decision_validity"] == "valid"

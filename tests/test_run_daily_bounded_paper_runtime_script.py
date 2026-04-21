from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
import urllib.error
from datetime import datetime, timezone
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


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
                stdout=json.dumps({"eligible": 0, "status": "no_eligible"}) + "\n",
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
    assert Path(payload["verification_surfaces"]["paper-reconciliation"]).exists()
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
        ("GET", "http://127.0.0.1:18000/paper/reconciliation"),
    ]
    summary_file_payload = json.loads(Path(payload["summary_file"]).read_text(encoding="utf-8"))
    assert summary_file_payload["run_quality_status"] == payload["run_quality_status"]
    assert summary_file_payload["run_quality_classification_version"] == payload["run_quality_classification_version"]
    assert summary_file_payload["operator_action_contract_version"] == payload["operator_action_contract_version"]
    assert summary_file_payload["operator_action_contract"] == payload["operator_action_contract"]
    assert summary_file_payload["run_quality_inputs"] == payload["run_quality_inputs"]


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

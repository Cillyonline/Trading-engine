from __future__ import annotations

import json
import sys
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _patch_runtime_lifecycle(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_paper_runtime_evidence_series_returns_not_configured_state(monkeypatch) -> None:
    _patch_runtime_lifecycle(monkeypatch)
    monkeypatch.setattr(api_main, "PAPER_RUNTIME_EVIDENCE_SERIES_DIR", None)

    with TestClient(api_main.app) as client:
        response = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["state"] == "not_configured"
    assert payload["run_count"] == 0
    assert payload["source"]["directory"] is None
    assert payload["boundary"]["mode"] == "paper_runtime_evidence_series_inspection_only"
    assert "does not trigger paper-runtime execution" in payload["boundary"]["non_live_statement"]


def test_paper_runtime_evidence_series_returns_missing_and_empty_states(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_lifecycle(monkeypatch)
    missing_dir = tmp_path / "missing"
    monkeypatch.setattr(api_main, "PAPER_RUNTIME_EVIDENCE_SERIES_DIR", missing_dir)

    with TestClient(api_main.app) as client:
        missing = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)

    assert missing.status_code == 200
    assert missing.json()["state"] == "missing"

    empty_dir = tmp_path / "empty"
    empty_dir.mkdir()
    monkeypatch.setattr(api_main, "PAPER_RUNTIME_EVIDENCE_SERIES_DIR", empty_dir)

    with TestClient(api_main.app) as client:
        empty = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)

    assert empty.status_code == 200
    assert empty.json()["state"] == "empty"
    assert empty.json()["run_files"] == []


def test_paper_runtime_evidence_series_summarizes_fixture_inputs_deterministically(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_lifecycle(monkeypatch)
    _write_json(
        tmp_path / "2026-04-07" / "run-002.json",
        {
            "run_quality_status": "no_eligible",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 0,
                        "rejected": 1,
                        "results": [
                            {"outcome": "skip:score_below_threshold", "signal_id": "sig-3"},
                            {"outcome": "reject:invalid_quantity", "signal_id": "sig-4"},
                        ],
                        "skipped": 1,
                    }
                },
                "reconciliation": {
                    "payload": {"mismatches": 0, "ok": True, "status": "pass"}
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-07/daily-runtime-summary.json",
        },
    )
    _write_json(
        tmp_path / "2026-04-06" / "run-001.json",
        {
            "run_quality_status": "healthy",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 2,
                        "rejected": 0,
                        "results": [{"outcome": "skip:duplicate_entry", "signal_id": "sig-2"}],
                        "skipped": 1,
                    }
                },
                "reconciliation": {
                    "payload": {"mismatches": 0, "ok": True, "status": "pass"}
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary.json",
        },
    )
    _write_json(
        tmp_path / "2026-04-08" / "run-003.json",
        {
            "run_quality_status": "degraded",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 1,
                        "rejected": 0,
                        "results": [{"outcome": "skip:duplicate_entry", "signal_id": "sig-5"}],
                        "skipped": 1,
                    }
                },
                "reconciliation": {
                    "payload": {"mismatches": 2, "ok": False, "status": "fail"}
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json",
        },
    )
    monkeypatch.setattr(api_main, "PAPER_RUNTIME_EVIDENCE_SERIES_DIR", tmp_path)

    with TestClient(api_main.app) as client:
        first = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)
        second = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    payload = first.json()
    assert payload["state"] == "available"
    assert payload["run_count"] == 3
    assert payload["run_files"] == [
        "2026-04-06/run-001.json",
        "2026-04-07/run-002.json",
        "2026-04-08/run-003.json",
    ]
    assert payload["run_quality_distribution"] == {
        "degraded": 1,
        "healthy": 1,
        "no_eligible": 1,
    }
    assert payload["eligible_skipped_rejected_totals"] == {
        "eligible": 3,
        "skipped": 3,
        "rejected": 1,
    }
    assert payload["skip_reason_counts"] == {
        "duplicate_entry": 2,
        "score_below_threshold": 1,
    }
    assert payload["reconciliation"] == {
        "mismatch_total": 2,
        "status_counts": {"fail": 1, "pass": 2},
    }
    assert payload["mismatch_counts"] == {"2026-04-08/run-003.json": 2}
    assert payload["summary_files"] == [
        "/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary.json",
        "/data/artifacts/daily-runtime/2026-04-07/daily-runtime-summary.json",
        "/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json",
    ]
    assert "/paper/runtime/evidence-series" in openapi["paths"]
    assert set(openapi["paths"]["/paper/runtime/evidence-series"].keys()) == {"get"}


def test_paper_runtime_evidence_series_endpoint_does_not_import_runner(
    tmp_path: Path,
    monkeypatch,
) -> None:
    _patch_runtime_lifecycle(monkeypatch)
    _write_json(
        tmp_path / "run-001.json",
        {
            "run_quality_status": "healthy",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {"eligible": 1, "rejected": 0, "results": [], "skipped": 0}
                },
                "reconciliation": {"payload": {"mismatches": 0, "ok": True}},
            },
        },
    )
    monkeypatch.setattr(api_main, "PAPER_RUNTIME_EVIDENCE_SERIES_DIR", tmp_path)
    runner_module = "scripts.run_daily_bounded_paper_runtime"
    previous_module = sys.modules.pop(runner_module, None)
    try:
        with TestClient(api_main.app) as client:
            response = client.get("/paper/runtime/evidence-series", headers=READ_ONLY_HEADERS)

        assert response.status_code == 200
        assert runner_module not in sys.modules
    finally:
        if previous_module is not None:
            sys.modules[runner_module] = previous_module

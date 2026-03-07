from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main


def _write_artifact(root: Path, run_id: str, artifact_name: str, payload: object) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def test_journal_artifacts_endpoint_lists_available_artifacts(monkeypatch, tmp_path: Path) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-1",
        artifact_name="audit.json",
        payload={"run_id": "run-1", "status": "ok"},
    )

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)

    with TestClient(api_main.app) as client:
        response = client.get("/journal/artifacts")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["run_id"] == "run-1"
    assert payload["items"][0]["artifact_name"] == "audit.json"


def test_decision_trace_endpoint_returns_trace_entries_from_artifact(
    monkeypatch,
    tmp_path: Path,
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-trace",
        artifact_name="decision_trace.json",
        payload={
            "trace_id": "trace-123",
            "decision_trace": {
                "entries": [
                    {"step": "risk_check", "reason": "limits_ok"},
                    {"step": "allocation", "reason": "approved"},
                ]
            },
        },
    )

    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)

    with TestClient(api_main.app) as client:
        response = client.get(
            "/journal/decision-trace",
            params={"run_id": "run-trace", "artifact_name": "decision_trace.json"},
        )

    assert response.status_code == 200
    payload = response.json()
    assert payload["run_id"] == "run-trace"
    assert payload["trace_id"] == "trace-123"
    assert payload["total_entries"] == 2
    assert payload["entries"][0]["step"] == "risk_check"
    assert payload["entries"][1]["reason"] == "approved"


from __future__ import annotations

import json
import shutil
import uuid
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from api.services import inspection_service
from cilly_trading.engine.backtest_handoff_contract import (
    build_professional_review_contract,
)

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _make_isolated_tmp_path() -> Path:
    base_dir = Path.cwd() / "tests" / "pytest_tmp"
    base_dir.mkdir(parents=True, exist_ok=True)
    path = base_dir / f"backtest-entry-read-{uuid.uuid4().hex}"
    path.mkdir(parents=True, exist_ok=False)
    return path


def _write_json_artifact(root: Path, run_id: str, artifact_name: str, payload: object) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def _write_text_artifact(root: Path, run_id: str, artifact_name: str, payload: str) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(payload, encoding="utf-8")


def test_backtest_entry_read_route_exposes_bounded_non_live_contract(
    monkeypatch,
) -> None:
    tmp_path = _make_isolated_tmp_path()
    try:
        artifacts_root = tmp_path / "runs" / "phase6"
        _write_json_artifact(
            artifacts_root,
            run_id="bt-run-1",
            artifact_name="backtest-result.json",
            payload={"run": {"run_id": "bt-run-1"}, "summary": {"total_trades": 3}},
        )
        _write_json_artifact(
            artifacts_root,
            run_id="bt-run-1",
            artifact_name="audit.json",
            payload={"trace_id": "ignored"},
        )

        monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)

        with TestClient(api_main.app) as client:
            response = client.get("/backtest/artifacts", headers=READ_ONLY_HEADERS)
            openapi = client.get("/openapi.json").json()

        assert response.status_code == 200
        payload = response.json()
        review_contract = build_professional_review_contract()
        assert payload["workflow_id"] == "ui_bounded_backtest_entry_read"
        assert payload["boundary"]["mode"] == "non_live_backtest_read_only"
        assert payload["boundary"]["review_contract_id"] == review_contract["contract_id"]
        assert payload["boundary"]["review_contract_version"] == review_contract["contract_version"]
        assert payload["boundary"]["review_required_evidence"] == review_contract["required_visible_evidence"]
        assert payload["boundary"]["review_comparison_axes"] == review_contract["comparison_axes"]
        assert payload["boundary"]["decision_relevance_statement"] == review_contract["decision_relevance_statement"]
        assert (
            payload["boundary"]["readiness_non_inference_statement"]
            == review_contract["readiness_non_inference_statement"]
        )
        assert "technical availability" in payload["boundary"]["technical_availability_statement"]
        assert "not trader validation" in payload["boundary"]["trader_validation_statement"]
        assert "not operational readiness" in payload["boundary"]["operational_readiness_statement"]
        evidence = payload["boundary"]["strategy_readiness_evidence"]
        assert "bounded API/UI evidence surfacing scope" in evidence["bounded_scope"]
        assert evidence["technical"]["gate"] == "technical_implementation"
        assert evidence["technical"]["status"] == "technical_in_progress"
        assert evidence["trader_validation"]["gate"] == "trader_validation"
        assert evidence["trader_validation"]["status"] == "trader_validation_not_started"
        assert evidence["operational_readiness"]["gate"] == "operational_readiness"
        assert evidence["operational_readiness"]["status"] == "operational_not_started"
        assert evidence["inferred_readiness_claim"] == "prohibited"
        assert payload["total"] == 1
        assert payload["items"][0]["run_id"] == "bt-run-1"
        assert payload["items"][0]["artifact_name"] == "backtest-result.json"
        assert "/backtest/artifacts" in openapi["paths"]
        assert "/backtest/artifacts/{run_id}/{artifact_name}" in openapi["paths"]
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_backtest_entry_read_route_derives_review_boundary_from_canonical_constructor(
    monkeypatch,
) -> None:
    tmp_path = _make_isolated_tmp_path()
    try:
        artifacts_root = tmp_path / "runs" / "phase6"
        _write_json_artifact(
            artifacts_root,
            run_id="bt-run-sentinel",
            artifact_name="backtest-result.json",
            payload={"run": {"run_id": "bt-run-sentinel"}},
        )

        canonical_contract = build_professional_review_contract()
        sentinel_contract = {
            "contract_id": canonical_contract["contract_id"],
            "contract_version": canonical_contract["contract_version"],
            "review_context": "sentinel.review.context",
            "required_visible_evidence": ["sentinel.required.field"],
            "comparison_axes": ["sentinel axis"],
            "decision_relevance_statement": "sentinel decision relevance",
            "readiness_non_inference_statement": "sentinel non inference",
            "unsupported_inference_claims": ["sentinel unsupported claim"],
        }
        call_count = {"count": 0}

        def _build_sentinel_contract() -> dict[str, object]:
            call_count["count"] += 1
            return sentinel_contract

        monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)
        monkeypatch.setattr(
            inspection_service,
            "build_professional_review_contract",
            _build_sentinel_contract,
        )

        with TestClient(api_main.app) as client:
            response = client.get("/backtest/artifacts", headers=READ_ONLY_HEADERS)

        assert response.status_code == 200
        assert call_count["count"] >= 1
        boundary = response.json()["boundary"]
        assert boundary["review_contract_id"] == sentinel_contract["contract_id"]
        assert boundary["review_contract_version"] == sentinel_contract["contract_version"]
        assert boundary["review_required_evidence"] == sentinel_contract["required_visible_evidence"]
        assert boundary["review_comparison_axes"] == sentinel_contract["comparison_axes"]
        assert (
            boundary["decision_relevance_statement"]
            == sentinel_contract["decision_relevance_statement"]
        )
        assert (
            boundary["readiness_non_inference_statement"]
            == sentinel_contract["readiness_non_inference_statement"]
        )
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)


def test_backtest_entry_read_route_handles_empty_filter_content_and_failure(
    monkeypatch,
) -> None:
    tmp_path = _make_isolated_tmp_path()
    try:
        artifacts_root = tmp_path / "runs" / "phase6"
        artifacts_root.mkdir(parents=True, exist_ok=True)
        _write_json_artifact(
            artifacts_root,
            run_id="bt-run-2",
            artifact_name="metrics-result.json",
            payload={"metrics": {"returns": {"total_return": 0.12}}},
        )
        _write_text_artifact(
            artifacts_root,
            run_id="bt-run-2",
            artifact_name="backtest-result.sha256",
            payload="abc123\n",
        )
        _write_json_artifact(
            artifacts_root,
            run_id="bt-run-2",
            artifact_name="audit.json",
            payload={"trace_id": "ignored"},
        )

        monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)

        with TestClient(api_main.app) as client:
            empty = client.get(
                "/backtest/artifacts",
                headers=READ_ONLY_HEADERS,
                params={"run_id": "does-not-exist"},
            )
            filtered = client.get(
                "/backtest/artifacts",
                headers=READ_ONLY_HEADERS,
                params={"run_id": "bt-run-2"},
            )
            content = client.get(
                "/backtest/artifacts/bt-run-2/metrics-result.json",
                headers=READ_ONLY_HEADERS,
            )
            hash_content = client.get(
                "/backtest/artifacts/bt-run-2/backtest-result.sha256",
                headers=READ_ONLY_HEADERS,
            )
            invalid_name = client.get(
                "/backtest/artifacts/bt-run-2/audit.json",
                headers=READ_ONLY_HEADERS,
            )
            unauthorized = client.get("/backtest/artifacts")

        assert empty.status_code == 200
        assert empty.json()["items"] == []
        assert empty.json()["total"] == 0

        assert filtered.status_code == 200
        filtered_payload = filtered.json()
        assert filtered_payload["total"] == 2
        assert {item["artifact_name"] for item in filtered_payload["items"]} == {
            "metrics-result.json",
            "backtest-result.sha256",
        }

        assert content.status_code == 200
        content_payload = content.json()
        assert content_payload["artifact_name"] == "metrics-result.json"
        assert content_payload["content_type"] == "json"
        assert content_payload["content"]["metrics"]["returns"]["total_return"] == 0.12

        assert hash_content.status_code == 200
        hash_payload = hash_content.json()
        assert hash_payload["artifact_name"] == "backtest-result.sha256"
        assert hash_payload["content_type"] == "text"
        assert hash_payload["content"] == "abc123\n"

        assert invalid_name.status_code == 404
        assert invalid_name.json() == {"detail": "backtest_artifact_not_found"}

        assert unauthorized.status_code == 401
        assert unauthorized.json() == {"detail": "unauthorized"}
    finally:
        shutil.rmtree(tmp_path, ignore_errors=True)

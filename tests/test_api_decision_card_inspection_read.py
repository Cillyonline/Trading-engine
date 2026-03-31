from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.decision_card_contract import REQUIRED_COMPONENT_CATEGORIES
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _write_artifact(root: Path, run_id: str, artifact_name: str, payload: Any) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def _decision_card_payload(
    *,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    qualification_state: str,
) -> dict[str, Any]:
    color_by_state = {
        "reject": "red",
        "watch": "yellow",
        "paper_candidate": "yellow",
        "paper_approved": "green",
    }
    gates = [
        {
            "gate_id": "drawdown_safety",
            "status": "pass",
            "blocking": True,
            "reason": "Drawdown remains within threshold",
            "evidence": ["max_dd=0.08", "threshold=0.12"],
            "failure_reason": None,
        },
        {
            "gate_id": "portfolio_exposure_cap",
            "status": "pass",
            "blocking": True,
            "reason": "Exposure remains within policy bounds",
            "evidence": ["gross_exposure=0.41", "cap=0.60"],
            "failure_reason": None,
        },
    ]
    if qualification_state == "reject":
        gates[0] = {
            "gate_id": "drawdown_safety",
            "status": "fail",
            "blocking": True,
            "reason": "Drawdown guard failed",
            "evidence": ["max_dd=0.15", "threshold=0.12"],
            "failure_reason": "Max drawdown breached policy threshold",
        }
    confidence_tier = "high"
    confidence_reason = "Aggregate and minimum component scores satisfy high thresholds."
    aggregate_score = 84.15
    if qualification_state == "watch":
        confidence_tier = "low"
        confidence_reason = (
            "Aggregate score or component threshold evidence is below medium-confidence thresholds."
        )
        aggregate_score = 55.0
    elif qualification_state == "paper_candidate":
        confidence_tier = "medium"
        confidence_reason = (
            "Aggregate score and component threshold evidence satisfy medium-confidence thresholds."
        )
        aggregate_score = 72.0

    qualification_summary = "Opportunity requires further evidence before paper-trading qualification."
    if qualification_state == "reject":
        qualification_summary = "Opportunity is rejected for paper-trading because a blocking gate failed."
    elif qualification_state == "paper_approved":
        qualification_summary = "Opportunity is approved for bounded paper-trading only."

    return {
        "contract_version": "2.0.0",
        "decision_card_id": decision_card_id,
        "generated_at_utc": generated_at_utc,
        "symbol": symbol,
        "strategy_id": strategy_id,
        "hard_gates": {
            "policy_version": "hard-gates.v1",
            "gates": gates,
        },
        "score": {
            "component_scores": [
                {
                    "category": "signal_quality",
                    "score": 88.0,
                    "rationale": "Signal quality remains stable across the review window",
                    "evidence": ["hit_rate=0.64", "window=120d"],
                },
                {
                    "category": "backtest_quality",
                    "score": 84.0,
                    "rationale": "Backtest quality remains bounded and reproducible",
                    "evidence": ["sharpe=1.40", "profit_factor=1.60"],
                },
                {
                    "category": "portfolio_fit",
                    "score": 79.0,
                    "rationale": "Portfolio fit remains inside concentration limits",
                    "evidence": ["sector=0.17", "corr_cluster=0.42"],
                },
                {
                    "category": "risk_alignment",
                    "score": 86.0,
                    "rationale": "Risk alignment is within configured guardrail bounds",
                    "evidence": ["risk_trade=0.005", "max_dd=0.10"],
                },
                {
                    "category": "execution_readiness",
                    "score": 77.0,
                    "rationale": "Execution readiness remains consistent with assumptions",
                    "evidence": ["slippage_bps=9", "commission=1.00"],
                },
            ],
            "confidence_tier": confidence_tier,
            "confidence_reason": confidence_reason,
            "aggregate_score": aggregate_score,
        },
        "qualification": {
            "state": qualification_state,
            "color": color_by_state[qualification_state],
            "summary": qualification_summary,
        },
        "rationale": {
            "summary": "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules.",
            "gate_explanations": [
                "Gate drawdown_safety was evaluated with explicit threshold evidence.",
                "Gate portfolio_exposure_cap was evaluated with explicit exposure evidence.",
            ],
            "score_explanations": [
                "Component scores are integrated by deterministic category ordering.",
                "Aggregate score uses fixed weights and bounded confidence tiers.",
            ],
            "final_explanation": "Action state is deterministic and does not imply live-trading approval.",
        },
        "metadata": {
            "analysis_run_id": "run-abc",
            "source": "qualification_engine",
        },
    }


def _client(monkeypatch, artifacts_root: Path) -> TestClient:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)
    return TestClient(api_main.app)


def test_decision_card_inspection_endpoint_is_exposed_and_schema_valid(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-1",
        artifact_name="decision_card.json",
        payload=_decision_card_payload(
            decision_card_id="dc-001",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
        ),
    )

    with _client(monkeypatch, artifacts_root) as client:
        response = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        openapi = client.get("/openapi.json").json()

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["decision_card_id"] == "dc-001"
    assert payload["items"][0]["hard_gates"]
    assert payload["items"][0]["component_scores"]
    assert {item["category"] for item in payload["items"][0]["component_scores"]} == set(
        REQUIRED_COMPONENT_CATEGORIES
    )
    assert payload["items"][0]["qualification_summary"] == "Opportunity is approved for bounded paper-trading only."
    assert (
        payload["items"][0]["rationale_summary"]
        == "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules."
    )
    assert payload["items"][0]["gate_explanations"]
    assert payload["items"][0]["score_explanations"]
    assert payload["items"][0]["final_explanation"] == (
        "Action state is deterministic and does not imply live-trading approval."
    )
    assert "/decision-cards" in openapi["paths"]
    get_spec = openapi["paths"]["/decision-cards"]["get"]
    assert set(openapi["paths"]["/decision-cards"].keys()) == {"get"}
    assert "Read-only decision inspection surface aligned to the canonical decision contract" in (
        get_spec["description"]
    )

    errors = validate_json_schema(payload, api_main.DecisionCardInspectionResponse.model_json_schema())
    assert errors == []


def test_decision_card_inspection_ordering_and_filtering_are_deterministic(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-a",
        artifact_name="dc-1.json",
        payload=_decision_card_payload(
            decision_card_id="dc-001",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-a",
        artifact_name="dc-2.json",
        payload=_decision_card_payload(
            decision_card_id="dc-002",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="reject",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-b",
        artifact_name="dc-3.json",
        payload=_decision_card_payload(
            decision_card_id="dc-003",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="AAPL",
            strategy_id="TURTLE",
            qualification_state="paper_candidate",
        ),
    )

    with _client(monkeypatch, artifacts_root) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        aapl = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"symbol": "AAPL"},
        )
        rejected = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"qualification_state": "reject"},
        )
        approved = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "approved"},
        )
        ranked = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "ranked"},
        )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert [item["decision_card_id"] for item in first.json()["items"]] == [
        "dc-002",
        "dc-003",
        "dc-001",
    ]

    assert [item["decision_card_id"] for item in aapl.json()["items"]] == ["dc-003", "dc-001"]
    assert [item["decision_card_id"] for item in rejected.json()["items"]] == ["dc-002"]
    assert [item["decision_card_id"] for item in approved.json()["items"]] == ["dc-001"]
    assert [item["decision_card_id"] for item in ranked.json()["items"]] == ["dc-003", "dc-001"]


def test_decision_card_inspection_empty_and_error_cases(monkeypatch, tmp_path: Path) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"

    with _client(monkeypatch, artifacts_root) as client:
        empty = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        unauthorized = client.get("/decision-cards")
        invalid_limit = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"limit": 0},
        )
        invalid_review_state = client.get(
            "/decision-cards",
            headers=READ_ONLY_HEADERS,
            params={"review_state": "unknown"},
        )

    assert empty.status_code == 200
    assert empty.json() == {"items": [], "limit": 50, "offset": 0, "total": 0}
    assert unauthorized.status_code == 401
    assert unauthorized.json() == {"detail": "unauthorized"}
    assert invalid_limit.status_code == 422
    assert invalid_review_state.status_code == 422


def test_decision_card_inspection_regression_ignores_non_contract_artifacts(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="run-1",
        artifact_name="invalid.json",
        payload={"decision_card": {"decision_card_id": "missing-fields"}},
    )
    (artifacts_root / "run-1" / "notes.txt").write_text("not json", encoding="utf-8")
    _write_artifact(
        artifacts_root,
        run_id="run-2",
        artifact_name="valid.json",
        payload={
            "decision_cards": [
                _decision_card_payload(
                    decision_card_id="dc-010",
                    generated_at_utc="2026-03-24T11:00:00Z",
                    symbol="NVDA",
                    strategy_id="TURTLE",
                    qualification_state="watch",
                )
            ]
        },
    )

    with _client(monkeypatch, artifacts_root) as client:
        response = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["decision_card_id"] for item in payload["items"]] == ["dc-010"]

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.models import Trade
from cilly_trading.engine.decision_card_contract import REQUIRED_COMPONENT_CATEGORIES
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from tests.utils.json_schema_validator import validate_json_schema

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _write_artifact(root: Path, run_id: str, artifact_name: str, payload: Any) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def _repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "decision-card-inspection.db")


def _trade(
    trade_id: str,
    *,
    strategy_id: str,
    symbol: str,
    status: str,
    opened_at: str,
    closed_at: str | None,
    realized_pnl: str | None,
    unrealized_pnl: str | None,
) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": f"pos-{trade_id}",
            "strategy_id": strategy_id,
            "symbol": symbol,
            "direction": "long",
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1") if status == "closed" else Decimal("0"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("101") if status == "closed" else None,
            "realized_pnl": Decimal(realized_pnl) if realized_pnl is not None else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": [f"ord-{trade_id}"],
            "closing_order_ids": [f"ord-{trade_id}"] if status == "closed" else [],
            "execution_event_ids": [f"evt-{trade_id}"],
        }
    )


def _decision_card_payload(
    *,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    qualification_state: str,
    paper_trade_id: str | None = None,
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

    payload = {
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
    if paper_trade_id is not None:
        payload["metadata"]["bounded_decision_to_paper_match"] = {
            "match_mode": "paper_trade_id",
            "paper_trade_id": paper_trade_id,
        }
    return payload


def _client(
    monkeypatch,
    artifacts_root: Path,
    repo: SqliteCanonicalExecutionRepository | None = None,
) -> TestClient:
    if repo is None:
        repo = _repo(artifacts_root.parent)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)
    monkeypatch.setattr(api_main, "canonical_execution_repo", repo)
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
    assert payload["items"][0]["action"] == "entry"
    assert payload["items"][0]["win_rate"] == 0.864
    assert payload["items"][0]["expected_value"] == 1.0
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


def test_decision_card_inspection_persists_deterministic_bounded_usefulness_audit(
    monkeypatch, tmp_path: Path
) -> None:
    artifacts_root = tmp_path / "runs" / "phase6"
    repo = _repo(tmp_path)
    repo.save_trade(
        _trade(
            "trade-exp",
            strategy_id="RSI2",
            symbol="AAPL",
            status="closed",
            opened_at="2026-03-24T08:05:00Z",
            closed_at="2026-03-24T08:45:00Z",
            realized_pnl="1.50",
            unrealized_pnl=None,
        )
    )
    repo.save_trade(
        _trade(
            "trade-weak",
            strategy_id="RSI2",
            symbol="MSFT",
            status="open",
            opened_at="2026-03-24T09:05:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="0.25",
        )
    )
    repo.save_trade(
        _trade(
            "trade-misleading",
            strategy_id="TURTLE",
            symbol="NVDA",
            status="closed",
            opened_at="2026-03-24T10:05:00Z",
            closed_at="2026-03-24T10:35:00Z",
            realized_pnl="-2.00",
            unrealized_pnl=None,
        )
    )

    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-exp.json",
        payload=_decision_card_payload(
            decision_card_id="dc-exp",
            generated_at_utc="2026-03-24T08:00:00Z",
            symbol="AAPL",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-exp",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-weak.json",
        payload=_decision_card_payload(
            decision_card_id="dc-weak",
            generated_at_utc="2026-03-24T09:00:00Z",
            symbol="MSFT",
            strategy_id="RSI2",
            qualification_state="paper_approved",
            paper_trade_id="trade-weak",
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="run-usefulness",
        artifact_name="dc-misleading.json",
        payload=_decision_card_payload(
            decision_card_id="dc-misleading",
            generated_at_utc="2026-03-24T10:00:00Z",
            symbol="NVDA",
            strategy_id="TURTLE",
            qualification_state="paper_approved",
            paper_trade_id="trade-misleading",
        ),
    )

    with _client(monkeypatch, artifacts_root, repo=repo) as client:
        first = client.get("/decision-cards", headers=READ_ONLY_HEADERS)
        second = client.get("/decision-cards", headers=READ_ONLY_HEADERS)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()

    by_id = {item["decision_card_id"]: item for item in first.json()["items"]}

    explanatory_audit = by_id["dc-exp"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert explanatory_audit["contract_id"] == "decision_evidence_to_paper_outcome_usefulness.paper_audit.v1"
    assert explanatory_audit["match_reference"] == {
        "match_mode": "paper_trade_id",
        "paper_trade_id": "trade-exp",
    }
    assert explanatory_audit["match_status"] == "matched"
    assert explanatory_audit["usefulness_classification"] == "explanatory"
    assert explanatory_audit["matched_outcome"]["outcome_direction"] == "favorable"
    assert "non-live" in explanatory_audit["interpretation_limit"]

    weak_audit = by_id["dc-weak"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert weak_audit["match_status"] == "open"
    assert weak_audit["usefulness_classification"] == "weak"
    assert weak_audit["matched_outcome"]["outcome_direction"] == "open"

    misleading_audit = by_id["dc-misleading"]["metadata"]["bounded_decision_to_paper_usefulness_audit"]
    assert misleading_audit["match_status"] == "matched"
    assert misleading_audit["usefulness_classification"] == "misleading"
    assert misleading_audit["matched_outcome"]["outcome_direction"] == "adverse"

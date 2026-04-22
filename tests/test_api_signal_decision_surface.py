from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "signal_decision_surface.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "ingestion_run_id": "test-run-001",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 55.0,
        "timestamp": "2026-01-01T00:00:00+00:00",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
        "confirmation_rule": "rsi_cross_up",
        "entry_zone": {"from_": 101.0, "to": 104.0},
    }
    base.update(overrides)
    return base


def _write_artifact(root: Path, run_id: str, artifact_name: str, payload: Any) -> None:
    run_dir = root / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / artifact_name).write_text(json.dumps(payload), encoding="utf-8")


def _tier_for_score(score: float) -> str:
    if score >= 80.0:
        return "high"
    if score >= 60.0:
        return "medium"
    return "low"


def _decision_card_payload_for_parity(
    *,
    decision_card_id: str,
    generated_at_utc: str,
    symbol: str,
    strategy_id: str,
    score: float,
    qualification_state: str,
    has_blocking_failure: bool,
) -> dict[str, Any]:
    gate_status = "fail" if has_blocking_failure else "pass"
    gates = [
        {
            "gate_id": "drawdown_safety",
            "status": gate_status,
            "blocking": True,
            "reason": "Drawdown gate result for deterministic parity check.",
            "evidence": ["max_dd=0.10", "threshold=0.12"],
            "failure_reason": "Drawdown breached threshold." if has_blocking_failure else None,
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
    color_by_state = {
        "reject": "red",
        "watch": "yellow",
        "paper_candidate": "yellow",
        "paper_approved": "green",
    }
    component_scores = [
        {
            "category": "signal_quality",
            "score": score,
            "rationale": "Signal-quality score for parity.",
            "evidence": [f"score={score:.2f}"],
        },
        {
            "category": "backtest_quality",
            "score": score,
            "rationale": "Backtest-quality score for parity.",
            "evidence": [f"score={score:.2f}"],
        },
        {
            "category": "portfolio_fit",
            "score": score,
            "rationale": "Portfolio-fit score for parity.",
            "evidence": [f"score={score:.2f}"],
        },
        {
            "category": "risk_alignment",
            "score": score,
            "rationale": "Risk-alignment score for parity.",
            "evidence": [f"score={score:.2f}"],
        },
        {
            "category": "execution_readiness",
            "score": score,
            "rationale": "Execution-readiness score for parity.",
            "evidence": [f"score={score:.2f}"],
        },
    ]
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
            "component_scores": component_scores,
            "confidence_tier": _tier_for_score(score),
            "confidence_reason": (
                "Aggregate/component/threshold evidence is bounded and deterministic for parity."
            ),
            "aggregate_score": score,
        },
        "qualification": {
            "state": qualification_state,
            "color": color_by_state[qualification_state],
            "summary": "Qualification output remains bounded to paper-trading scope.",
        },
        "rationale": {
            "summary": "Qualification is resolved from deterministic bounded evidence.",
            "gate_explanations": ["Hard-gate outcome is explicit and deterministic."],
            "score_explanations": ["Score evidence is explicit and deterministic."],
            "final_explanation": "Action state is deterministic and does not imply live-trading approval.",
        },
        "metadata": {
            "analysis_run_id": "parity-run",
            "source": "parity-test",
        },
    }


def test_signal_decision_surface_returns_bounded_technical_states(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="BLOCK", score=20.0, stage="setup", timestamp="2026-01-03T00:00:00+00:00"),
            _base_signal(symbol="WATCH", score=60.0, stage="setup", timestamp="2026-01-02T00:00:00+00:00"),
            _base_signal(
                symbol="CANDIDATE",
                score=88.0,
                stage="entry_confirmed",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        ]
    )
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals/decision-surface", headers=READ_ONLY_HEADERS)
    assert response.status_code == 200
    payload = response.json()

    assert payload["workflow_id"] == "ui_signal_decision_surface_v1"
    assert payload["boundary"]["mode"] == "non_live_signal_decision_surface"
    assert payload["boundary"]["non_inference_boundary_contract"] == {
        "contract_id": "bounded_non_inference_boundary_fields.read_only.v1",
        "contract_version": "1.0.0",
        "evaluation_mode": "structured_primary_with_wording_fallback",
    }
    assert payload["boundary"]["strategy_readiness_evidence"]["inferred_readiness_claim"] == "prohibited"
    assert payload["total"] == 3
    assert [item["decision_state"] for item in payload["items"]] == [
        "blocked",
        "watch",
        "paper_candidate",
    ]
    assert all(
        item["qualification_policy_version"] == "professional_non_live_signal_qualification.v1"
        for item in payload["items"]
    )
    assert payload["items"][0]["blocking_conditions"]
    assert payload["items"][1]["missing_criteria"]
    assert payload["items"][2]["missing_criteria"] == []
    assert payload["items"][2]["qualification_evidence"]
    assert payload["items"][0]["qualification_state"] == "reject"
    assert payload["items"][1]["qualification_state"] == "watch"
    assert payload["items"][2]["qualification_state"] == "paper_approved"
    assert payload["items"][0]["action"] == "ignore"
    assert payload["items"][1]["action"] == "ignore"
    assert payload["items"][2]["action"] == "entry"
    assert payload["items"][0]["win_rate"] == 0.2
    assert payload["items"][2]["win_rate"] == 0.88
    assert payload["items"][0]["expected_value"] == -0.7
    assert payload["items"][2]["expected_value"] == 1.0
    assert "score" in payload["items"][2]["score_contribution"].lower()
    assert "stage" in payload["items"][1]["stage_assessment"].lower()
    assert any(
        "bounded trader-relevance case review" in entry.lower()
        for entry in payload["items"][2]["qualification_evidence"]
    )
    assert any(
        "boundary evidence" in entry.lower()
        and "not trader_validation evidence" in entry.lower()
        and "not paper profitability evidence" in entry.lower()
        for entry in payload["items"][2]["qualification_evidence"]
    )


def test_signal_decision_surface_covers_threshold_and_entry_zone_edge_cases(
    tmp_path: Path,
    monkeypatch,
) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(
                symbol="EDGE_CANDIDATE",
                score=70.0,
                stage="entry_confirmed",
                timestamp="2026-01-04T00:00:00+00:00",
            ),
            _base_signal(
                symbol="EDGE_BLOCK",
                score=40.0,
                stage="entry_confirmed",
                confirmation_rule="",
                timestamp="2026-01-03T00:00:00+00:00",
            ),
            _base_signal(
                symbol="INVALID_ZONE",
                score=85.0,
                stage="entry_confirmed",
                entry_zone={"from_": 110.0, "to": 105.0},
                timestamp="2026-01-02T00:00:00+00:00",
            ),
        ]
    )
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals/decision-surface", headers=READ_ONLY_HEADERS)
    assert response.status_code == 200
    payload = response.json()
    by_symbol = {item["symbol"]: item for item in payload["items"]}

    assert by_symbol["EDGE_CANDIDATE"]["decision_state"] == "paper_candidate"
    assert by_symbol["EDGE_CANDIDATE"]["qualification_state"] == "paper_candidate"
    assert by_symbol["EDGE_CANDIDATE"]["action"] == "entry"
    assert by_symbol["EDGE_CANDIDATE"]["missing_criteria"] == []
    assert by_symbol["EDGE_CANDIDATE"]["blocking_conditions"] == []
    assert by_symbol["EDGE_CANDIDATE"]["qualification_evidence"]
    edge_candidate_review = next(
        entry
        for entry in by_symbol["EDGE_CANDIDATE"]["qualification_evidence"]
        if "Bounded trader-relevance case review" in entry
    )
    assert "decision_action_relevance=aligned" in edge_candidate_review
    assert "qualification_state_relevance=aligned" in edge_candidate_review

    assert by_symbol["EDGE_BLOCK"]["decision_state"] == "watch"
    assert by_symbol["EDGE_BLOCK"]["qualification_state"] == "watch"
    assert by_symbol["EDGE_BLOCK"]["action"] == "exit"
    assert by_symbol["EDGE_BLOCK"]["blocking_conditions"] == []
    assert any("confirmation-rule" in entry.lower() for entry in by_symbol["EDGE_BLOCK"]["missing_criteria"])

    assert by_symbol["INVALID_ZONE"]["decision_state"] == "blocked"
    assert by_symbol["INVALID_ZONE"]["qualification_state"] == "reject"
    assert by_symbol["INVALID_ZONE"]["action"] == "ignore"
    assert any("entry_zone" in entry.lower() for entry in by_symbol["INVALID_ZONE"]["blocking_conditions"])


def test_signal_decision_surface_openapi_contract_is_explicit(monkeypatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/openapi.json")
    assert response.status_code == 200
    openapi = response.json()

    assert "/signals/decision-surface" in openapi["paths"]
    get_spec = openapi["paths"]["/signals/decision-surface"]["get"]
    assert "bounded non-live technical decision states" in get_spec["description"]
    assert "qualification_state, action, win_rate, expected_value" in get_spec["description"]
    assert "does not imply trader validation or operational readiness" in get_spec["description"]


def test_signal_decision_surface_requires_read_only_role(monkeypatch, tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get("/signals/decision-surface")
    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_signal_decision_surface_parity_with_canonical_decision_review_output(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="PARITY_BLOCK", score=20.0, stage="setup", timestamp="2026-01-03T00:00:00+00:00"),
            _base_signal(symbol="PARITY_WATCH", score=55.0, stage="entry_confirmed", timestamp="2026-01-02T00:00:00+00:00"),
            _base_signal(
                symbol="PARITY_APPROVED",
                score=88.0,
                stage="entry_confirmed",
                timestamp="2026-01-01T00:00:00+00:00",
            ),
        ]
    )
    artifacts_root = tmp_path / "runs" / "phase6"
    _write_artifact(
        artifacts_root,
        run_id="parity-1",
        artifact_name="dc-block.json",
        payload=_decision_card_payload_for_parity(
            decision_card_id="dc-parity-block",
            generated_at_utc="2026-01-03T00:00:00Z",
            symbol="PARITY_BLOCK",
            strategy_id="RSI2",
            score=20.0,
            qualification_state="reject",
            has_blocking_failure=True,
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="parity-1",
        artifact_name="dc-watch.json",
        payload=_decision_card_payload_for_parity(
            decision_card_id="dc-parity-watch",
            generated_at_utc="2026-01-02T00:00:00Z",
            symbol="PARITY_WATCH",
            strategy_id="RSI2",
            score=55.0,
            qualification_state="watch",
            has_blocking_failure=False,
        ),
    )
    _write_artifact(
        artifacts_root,
        run_id="parity-1",
        artifact_name="dc-approved.json",
        payload=_decision_card_payload_for_parity(
            decision_card_id="dc-parity-approved",
            generated_at_utc="2026-01-01T00:00:00Z",
            symbol="PARITY_APPROVED",
            strategy_id="RSI2",
            score=88.0,
            qualification_state="paper_approved",
            has_blocking_failure=False,
        ),
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "JOURNAL_ARTIFACTS_ROOT", artifacts_root)

    with TestClient(api_main.app) as client:
        decision_surface_response = client.get("/signals/decision-surface", headers=READ_ONLY_HEADERS)
        decision_review_response = client.get("/decision-review", headers=READ_ONLY_HEADERS)

    assert decision_surface_response.status_code == 200
    assert decision_review_response.status_code == 200

    decision_surface_by_symbol = {
        item["symbol"]: item for item in decision_surface_response.json()["items"]
    }
    decision_review_payload = decision_review_response.json()
    assert decision_review_payload["workflow_id"] == "ui_decision_review_surface_v1"
    assert decision_review_payload["boundary"]["mode"] == "non_live_decision_review_surface"
    assert [item["surface"] for item in decision_review_payload["boundary"]["legacy_surface_mappings"]] == [
        "/decision-cards",
        "/signals/decision-surface",
    ]
    decision_review_by_symbol = {
        item["symbol"]: item for item in decision_review_payload["items"]
    }
    for symbol in ("PARITY_BLOCK", "PARITY_WATCH", "PARITY_APPROVED"):
        assert (
            decision_surface_by_symbol[symbol]["qualification_state"]
            == decision_review_by_symbol[symbol]["qualification_state"]
        )
        assert decision_surface_by_symbol[symbol]["action"] == decision_review_by_symbol[symbol]["action"]
        assert decision_surface_by_symbol[symbol]["win_rate"] == decision_review_by_symbol[symbol]["win_rate"]
        assert (
            decision_surface_by_symbol[symbol]["expected_value"]
            == decision_review_by_symbol[symbol]["expected_value"]
        )

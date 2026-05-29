"""Focused evidence tests for bounded paper execution cycle serialization."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import scripts.run_paper_execution_cycle as cycle
from cilly_trading.engine.paper_execution_worker import SignalEvaluationResult


class _FakeSignalRepository:
    signals: list[dict[str, Any]] = []

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path

    def list_signals(
        self,
        limit: int,
        *,
        analysis_run_id: str | None = None,
        ingestion_run_id: str | None = None,
        latest_per_identity: bool = False,
    ) -> list[dict[str, Any]]:
        del analysis_run_id, ingestion_run_id, latest_per_identity
        return self.signals[:limit]


class _FakeExecutionRepository:
    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path


class _FakeWorker:
    results: list[SignalEvaluationResult] = []

    def __init__(self, repository: _FakeExecutionRepository, risk_profile: Any) -> None:
        self.repository = repository
        self.risk_profile = risk_profile

    def process_batch(self, signals: list[dict[str, Any]]) -> list[SignalEvaluationResult]:
        return self.results


def test_paper_execution_cycle_evidence_includes_diagnostics_and_decision_inputs(
    tmp_path: Path,
    monkeypatch: Any,
) -> None:
    _FakeSignalRepository.signals = [
        {
            "signal_id": "sig-exit-no-open",
            "symbol": "AAPL",
            "strategy": "s",
            "stage": "exit",
            "direction": "long",
        },
        {
            "signal_id": "sig-score-low",
            "symbol": "MSFT",
            "strategy": "s",
            "stage": "setup",
            "direction": "long",
        },
        {
            "signal_id": "sig-risk-missing",
            "symbol": "TSLA",
            "strategy": "s",
            "stage": "setup",
            "direction": "long",
        },
    ]
    missing_risk_evidence = {
        "signal_id": "sig-risk-missing",
        "symbol": "TSLA",
        "strategy": "s",
        "stage": "setup",
        "direction": "long",
        "outcome": "reject:missing_trade_risk_input",
        "reason": "trade_risk_pct or stop_loss is required for deterministic sizing",
        "missing_fields": ["stop_loss", "trade_risk_pct"],
        "required_any_of": ["stop_loss", "trade_risk_pct"],
        "sizing_method": "stop_distance",
        "risk_profile_contract_id": "paper-execution-risk-profile.v1",
    }
    _FakeWorker.results = [
        SignalEvaluationResult(
            outcome="skip:no_open_position_to_exit",
            signal_id="sig-exit-no-open",
            reason="no open position found for exit signal",
        ),
        SignalEvaluationResult(
            outcome="skip:score_below_threshold",
            signal_id="sig-score-low",
            reason="score=59.0 < min_score_threshold=60.0",
        ),
        SignalEvaluationResult(
            outcome="reject:missing_trade_risk_input",
            signal_id="sig-risk-missing",
            reason="trade_risk_pct or stop_loss is required for deterministic sizing",
            decision_inputs=missing_risk_evidence,
        ),
    ]

    monkeypatch.setattr(cycle, "SqliteSignalRepository", _FakeSignalRepository)
    monkeypatch.setattr(cycle, "SqliteCanonicalExecutionRepository", _FakeExecutionRepository)
    monkeypatch.setattr(cycle, "BoundedPaperExecutionWorker", _FakeWorker)

    exit_code = cycle.run_paper_execution_cycle(
        db_path=str(tmp_path / "paper.db"),
        evidence_dir=str(tmp_path),
        ran_at=datetime(2026, 5, 28, 12, 0, 0, tzinfo=timezone.utc),
    )

    assert exit_code == cycle.EXIT_CYCLE_NO_ELIGIBLE
    evidence_file = tmp_path / "paper-execution-no-eligible-20260528T120000Z.json"
    payload = json.loads(evidence_file.read_text(encoding="utf-8"))

    assert payload["cycle_type"] == "bounded_paper_execution"
    assert payload["eligible"] == 0
    assert payload["skipped"] == 2
    assert payload["rejected"] == 1
    assert payload["signals_read"] == 3
    assert payload["status"] == "no_eligible"

    assert "decision_inputs" not in payload["results"][0]
    assert "decision_inputs" not in payload["results"][1]
    assert payload["results"][2]["decision_inputs"] == missing_risk_evidence

    assert payload["diagnostics_summary"] == {
        "signals_read": 3,
        "entry_candidate_count": 2,
        "exit_candidate_count": 1,
        "eligible_entry_count": 0,
        "eligible_exit_count": 0,
        "skipped_exits_without_open_position": 1,
        "score_filtered_entries": 1,
        "risk_input_rejected_entries": 1,
        "missing_trade_risk_input_count": 1,
        "missing_trade_risk_input_rejections": [missing_risk_evidence],
    }
    assert payload["signal_scope"] == {
        "analysis_run_id": None,
        "fallback_reason": "current_run_scope_unavailable",
        "ingestion_run_id": None,
        "scope_filters": [],
        "selection_mode": "latest_per_identity_fallback",
        "signals_read": 3,
    }

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.paper_execution_risk_profile import PaperExecutionRiskProfile
from cilly_trading.engine.paper_execution_worker import BoundedPaperExecutionWorker
from cilly_trading.engine.risk import evaluate_risk_framework_execution_decision
from cilly_trading.models import Signal
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository
from cilly_trading.risk_framework.allocation_rules import RiskLimits


@pytest.fixture
def repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "paper_execution_risk_alignment.db")


def _signal(
    *,
    symbol: str,
    strategy: str,
    signal_id: str,
    timestamp: str = "2026-01-01T00:00:00Z",
) -> Signal:
    return {
        "symbol": symbol,
        "strategy": strategy,
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 90.0,
        "timestamp": timestamp,
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.2,
        "signal_id": signal_id,
    }


def test_paper_execution_account_exposure_rejection_uses_canonical_reason(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_total_exposure_pct=Decimal("0.80"),
            max_strategy_exposure_pct=Decimal("1.00"),
            max_symbol_exposure_pct=Decimal("1.00"),
            max_concurrent_positions=20,
        ),
    )

    for index in range(8):
        accepted = worker.process_signal(
            _signal(
                symbol=f"SYM{index}",
                strategy="strategy-a",
                signal_id=f"sig-account-{index}",
            )
        )
        assert accepted.outcome == "eligible"

    rejected = worker.process_signal(
        _signal(symbol="SYM9", strategy="strategy-a", signal_id="sig-account-reject")
    )
    assert rejected.outcome == "reject:total_exposure_exceeds_limit"
    assert rejected.reason == "rejected:risk_framework_max_account_exposure_pct_exceeded"


def test_paper_execution_strategy_exposure_rejection_uses_canonical_reason(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_total_exposure_pct=Decimal("1.00"),
            max_strategy_exposure_pct=Decimal("0.20"),
            max_symbol_exposure_pct=Decimal("1.00"),
            max_concurrent_positions=20,
        ),
    )

    first = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-a", signal_id="sig-s-1"))
    second = worker.process_signal(_signal(symbol="MSFT", strategy="strategy-a", signal_id="sig-s-2"))
    rejected = worker.process_signal(_signal(symbol="NVDA", strategy="strategy-a", signal_id="sig-s-3"))

    assert first.outcome == "eligible"
    assert second.outcome == "eligible"
    assert rejected.outcome == "reject:strategy_exposure_exceeds_limit"
    assert rejected.reason == "rejected:risk_framework_max_strategy_exposure_pct_exceeded"


def test_paper_execution_symbol_exposure_rejection_uses_canonical_reason(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_total_exposure_pct=Decimal("1.00"),
            max_strategy_exposure_pct=Decimal("1.00"),
            max_symbol_exposure_pct=Decimal("0.20"),
            max_concurrent_positions=20,
        ),
    )

    first = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-a", signal_id="sig-y-1"))
    second = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-b", signal_id="sig-y-2"))
    rejected = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-c", signal_id="sig-y-3"))

    assert first.outcome == "eligible"
    assert second.outcome == "eligible"
    assert rejected.outcome == "reject:symbol_exposure_exceeds_limit"
    assert rejected.reason == "rejected:risk_framework_max_symbol_exposure_pct_exceeded"


def test_paper_execution_multi_violation_precedence_prefers_account_before_strategy(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_total_exposure_pct=Decimal("0.25"),
            max_strategy_exposure_pct=Decimal("0.20"),
            max_symbol_exposure_pct=Decimal("1.00"),
            max_concurrent_positions=20,
        ),
    )

    first = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-a", signal_id="sig-p-1"))
    second = worker.process_signal(_signal(symbol="MSFT", strategy="strategy-a", signal_id="sig-p-2"))
    rejected = worker.process_signal(_signal(symbol="NVDA", strategy="strategy-a", signal_id="sig-p-3"))

    assert first.outcome == "eligible"
    assert second.outcome == "eligible"
    assert rejected.outcome == "reject:total_exposure_exceeds_limit"
    assert rejected.reason == "rejected:risk_framework_max_account_exposure_pct_exceeded"


def test_paper_execution_and_gate_share_canonical_reason_for_equivalent_state(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.02"),
            max_total_exposure_pct=Decimal("0.80"),
            max_strategy_exposure_pct=Decimal("0.20"),
            max_symbol_exposure_pct=Decimal("1.00"),
            max_concurrent_positions=20,
        ),
    )

    first = worker.process_signal(_signal(symbol="AAPL", strategy="strategy-a", signal_id="sig-eq-1"))
    second = worker.process_signal(_signal(symbol="MSFT", strategy="strategy-a", signal_id="sig-eq-2"))
    rejected = worker.process_signal(_signal(symbol="NVDA", strategy="strategy-a", signal_id="sig-eq-3"))

    assert first.outcome == "eligible"
    assert second.outcome == "eligible"
    assert rejected.reason is not None
    assert rejected.decision_inputs is not None

    gate_decision = evaluate_risk_framework_execution_decision(
        request_id="req-eq-state",
        strategy_id="strategy-a",
        symbol="NVDA",
        proposed_position_size=float(rejected.decision_inputs["proposed_position_notional"]),
        account_equity=1000.0,
        current_exposure=200.0,
        strategy_exposure=200.0,
        symbol_exposure=0.0,
        limits=RiskLimits(
            max_account_exposure_pct=0.80,
            max_position_size=200.0,
            max_strategy_exposure_pct=0.20,
            max_symbol_exposure_pct=1.00,
        ),
        rule_version="paper-risk-framework-v1",
    )

    assert gate_decision.decision == "REJECTED"
    assert gate_decision.reason == rejected.reason

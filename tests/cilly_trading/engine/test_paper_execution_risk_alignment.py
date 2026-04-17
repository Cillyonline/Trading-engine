from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.paper_execution_risk_profile import PaperExecutionRiskProfile
from cilly_trading.engine.paper_execution_worker import BoundedPaperExecutionWorker
from cilly_trading.models import Signal
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository


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

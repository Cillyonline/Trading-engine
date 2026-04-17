from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.paper_execution_risk_profile import (
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE,
    PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID,
    PaperExecutionRiskProfile,
)
from cilly_trading.engine.paper_execution_worker import BoundedPaperExecutionWorker
from cilly_trading.models import Signal
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository


def _signal(*, signal_id: str, score: float = 90.0) -> Signal:
    return {
        "symbol": "AAPL",
        "strategy": "rsi2",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": score,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.02,
        "signal_id": signal_id,
    }


def test_default_profile_uses_canonical_contract_id() -> None:
    assert (
        DEFAULT_PAPER_EXECUTION_RISK_PROFILE.contract_id
        == PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID
    )


def test_invalid_profile_values_fail_closed() -> None:
    with pytest.raises(ValueError, match="max_position_pct must be in range"):
        PaperExecutionRiskProfile(max_position_pct=Decimal("1.50"))

    with pytest.raises(ValueError, match="max_concurrent_positions must be > 0"):
        PaperExecutionRiskProfile(max_concurrent_positions=0)

    with pytest.raises(ValueError, match="min_score_threshold must be in range"):
        PaperExecutionRiskProfile(min_score_threshold=101.0)
    with pytest.raises(ValueError, match="max_risk_per_trade_pct must be in range"):
        PaperExecutionRiskProfile(max_risk_per_trade_pct=Decimal("0"))
    with pytest.raises(ValueError, match="min_trade_risk_pct must be <= max_trade_risk_pct"):
        PaperExecutionRiskProfile(
            min_trade_risk_pct=Decimal("0.21"),
            max_trade_risk_pct=Decimal("0.20"),
        )


def test_same_profile_and_same_input_produce_same_outcome(tmp_path: Path) -> None:
    profile = PaperExecutionRiskProfile(min_score_threshold=95.0)
    signal = _signal(signal_id="sig-same-profile-input", score=90.0)

    repo_a = SqliteCanonicalExecutionRepository(db_path=tmp_path / "profile-a.db")
    repo_b = SqliteCanonicalExecutionRepository(db_path=tmp_path / "profile-b.db")

    worker_a = BoundedPaperExecutionWorker(repository=repo_a, risk_profile=profile)
    worker_b = BoundedPaperExecutionWorker(repository=repo_b, risk_profile=profile)

    result_a = worker_a.process_signal(signal)
    result_b = worker_b.process_signal(signal)

    assert result_a.outcome == "skip:score_below_threshold"
    assert result_b.outcome == "skip:score_below_threshold"
    assert result_a.reason == result_b.reason

"""Tests for P2-trading issues: performance metrics, attribution, regime filter.

Covers:
    #1149 — PaperPerformanceSummary computed from closed trades
    #1150 — PaperPerformanceAttribution per strategy/symbol
    #1151 — Regime classifier (ADX, realized-vol, classify_regime) + worker gate
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.paper_execution_risk_profile import PaperExecutionRiskProfile
from cilly_trading.engine.paper_execution_worker import BoundedPaperExecutionWorker
from cilly_trading.engine.paper_performance import (
    compute_paper_performance_attribution,
    compute_paper_performance_summary,
)
from cilly_trading.engine.regime_classifier import (
    RegimeState,
    classify_regime,
    compute_adx,
    compute_realized_vol,
)
from cilly_trading.models import Signal, Trade
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _closed_trade(
    trade_id: str,
    *,
    strategy: str = "s",
    symbol: str = "AAPL",
    pnl: Decimal,
    exit_price: Decimal,
    closed_at: str = "2026-01-01T12:00:00Z",
) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": f"pos-{trade_id}",
            "strategy_id": strategy,
            "symbol": symbol,
            "direction": "long",
            "status": "closed",
            "opened_at": "2026-01-01T00:00:00Z",
            "closed_at": closed_at,
            "quantity_opened": Decimal("10"),
            "quantity_closed": Decimal("10"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": exit_price,
            "exposure_notional": Decimal("0"),
            "realized_pnl": pnl,
            "opening_order_ids": [],
            "execution_event_ids": [],
        }
    )


def _base_profile(**kwargs) -> PaperExecutionRiskProfile:
    return PaperExecutionRiskProfile(
        account_equity=Decimal("100000"),
        max_risk_per_trade_pct=Decimal("0.01"),
        min_trade_risk_pct=Decimal("0.005"),
        max_trade_risk_pct=Decimal("0.50"),
        max_total_exposure_pct=Decimal("1.00"),
        max_strategy_exposure_pct=Decimal("1.00"),
        max_symbol_exposure_pct=Decimal("1.00"),
        max_concurrent_positions=20,
        commission_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        cooldown_hours=0,
        sizing_method="fixed",
        **kwargs,
    )


# ---------------------------------------------------------------------------
# #1149: PaperPerformanceSummary
# ---------------------------------------------------------------------------


def test_performance_summary_empty_returns_zeros() -> None:
    summary = compute_paper_performance_summary([], initial_equity=Decimal("100000"))
    assert summary.trade_count == 0
    assert summary.win_rate == Decimal("0")
    assert summary.expectancy == Decimal("0")


def test_performance_summary_win_rate_correct() -> None:
    trades = [
        _closed_trade("t1", pnl=Decimal("100"), exit_price=Decimal("110")),
        _closed_trade("t2", pnl=Decimal("50"), exit_price=Decimal("105")),
        _closed_trade("t3", pnl=Decimal("-80"), exit_price=Decimal("92")),
        _closed_trade("t4", pnl=Decimal("-20"), exit_price=Decimal("98")),
    ]
    summary = compute_paper_performance_summary(trades, initial_equity=Decimal("100000"))
    assert summary.trade_count == 4
    assert summary.win_count == 2
    assert summary.loss_count == 2
    assert summary.win_rate == Decimal("0.5")


def test_performance_summary_expectancy_positive_for_winning_strategy() -> None:
    trades = [
        _closed_trade("w1", pnl=Decimal("200"), exit_price=Decimal("120")),
        _closed_trade("w2", pnl=Decimal("200"), exit_price=Decimal("120")),
        _closed_trade("w3", pnl=Decimal("200"), exit_price=Decimal("120")),
        _closed_trade("l1", pnl=Decimal("-50"), exit_price=Decimal("95")),
    ]
    summary = compute_paper_performance_summary(trades, initial_equity=Decimal("100000"))
    assert summary.expectancy > Decimal("0")
    assert summary.profit_factor > Decimal("1")


def test_performance_summary_consecutive_streaks() -> None:
    trades = [
        _closed_trade("a1", pnl=Decimal("10"), exit_price=Decimal("101"), closed_at="2026-01-01T00:00:00Z"),
        _closed_trade("a2", pnl=Decimal("10"), exit_price=Decimal("101"), closed_at="2026-01-02T00:00:00Z"),
        _closed_trade("a3", pnl=Decimal("10"), exit_price=Decimal("101"), closed_at="2026-01-03T00:00:00Z"),
        _closed_trade("b1", pnl=Decimal("-5"), exit_price=Decimal("99.5"), closed_at="2026-01-04T00:00:00Z"),
        _closed_trade("b2", pnl=Decimal("-5"), exit_price=Decimal("99.5"), closed_at="2026-01-05T00:00:00Z"),
    ]
    summary = compute_paper_performance_summary(trades, initial_equity=Decimal("100000"))
    assert summary.max_consecutive_wins == 3
    assert summary.max_consecutive_losses == 2


def test_performance_summary_max_drawdown_computed_from_equity_curve() -> None:
    # Equity: 100000 → 100100 (win) → 100200 (win) → 100050 (loss) → 100100 (win)
    # Peak after trade 2 = 100200; trough = 100050; dd = 150/100200 ≈ 0.15%
    trades = [
        _closed_trade("d1", pnl=Decimal("100"), exit_price=Decimal("110"), closed_at="2026-01-01T00:00:00Z"),
        _closed_trade("d2", pnl=Decimal("100"), exit_price=Decimal("110"), closed_at="2026-01-02T00:00:00Z"),
        _closed_trade("d3", pnl=Decimal("-150"), exit_price=Decimal("85"), closed_at="2026-01-03T00:00:00Z"),
        _closed_trade("d4", pnl=Decimal("50"), exit_price=Decimal("105"), closed_at="2026-01-04T00:00:00Z"),
    ]
    summary = compute_paper_performance_summary(trades, initial_equity=Decimal("100000"))
    assert summary.max_drawdown_pct > Decimal("0")
    # dd = 150 / 100200 ≈ 0.001497
    assert summary.max_drawdown_pct < Decimal("0.01")


def test_performance_summary_recovery_factor_positive_when_net_profitable() -> None:
    trades = [
        _closed_trade("rf1", pnl=Decimal("500"), exit_price=Decimal("150"), closed_at="2026-01-01T00:00:00Z"),
        _closed_trade("rf2", pnl=Decimal("-100"), exit_price=Decimal("90"), closed_at="2026-01-02T00:00:00Z"),
        _closed_trade("rf3", pnl=Decimal("300"), exit_price=Decimal("130"), closed_at="2026-01-03T00:00:00Z"),
    ]
    summary = compute_paper_performance_summary(trades, initial_equity=Decimal("100000"))
    assert summary.net_pnl > Decimal("0")
    assert summary.recovery_factor > Decimal("0")


def test_worker_get_performance_summary_integrates_with_repo(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "perf.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_base_profile())

    repo.save_trade(_closed_trade("pt1", pnl=Decimal("200"), exit_price=Decimal("120")))
    repo.save_trade(_closed_trade("pt2", pnl=Decimal("-50"), exit_price=Decimal("95")))

    summary = worker.get_performance_summary()
    assert summary.trade_count == 2
    assert summary.win_count == 1


# ---------------------------------------------------------------------------
# #1150: PaperPerformanceAttribution
# ---------------------------------------------------------------------------


def test_attribution_groups_by_strategy() -> None:
    trades = [
        _closed_trade("s1", strategy="alpha", symbol="AAPL", pnl=Decimal("100"), exit_price=Decimal("110")),
        _closed_trade("s2", strategy="alpha", symbol="MSFT", pnl=Decimal("-50"), exit_price=Decimal("95")),
        _closed_trade("s3", strategy="beta", symbol="AAPL", pnl=Decimal("200"), exit_price=Decimal("120")),
    ]
    attr = compute_paper_performance_attribution(trades)
    assert "alpha" in attr.by_strategy
    assert "beta" in attr.by_strategy
    assert attr.by_strategy["alpha"].trade_count == 2
    assert attr.by_strategy["beta"].trade_count == 1


def test_attribution_groups_by_symbol() -> None:
    trades = [
        _closed_trade("y1", strategy="s", symbol="AAPL", pnl=Decimal("100"), exit_price=Decimal("110")),
        _closed_trade("y2", strategy="s", symbol="AAPL", pnl=Decimal("50"), exit_price=Decimal("105")),
        _closed_trade("y3", strategy="s", symbol="MSFT", pnl=Decimal("-30"), exit_price=Decimal("97")),
    ]
    attr = compute_paper_performance_attribution(trades)
    assert attr.by_symbol["AAPL"].trade_count == 2
    assert attr.by_symbol["MSFT"].trade_count == 1
    assert attr.by_symbol["AAPL"].win_rate == Decimal("1")


def test_attribution_groups_by_strategy_symbol_pair() -> None:
    trades = [
        _closed_trade("p1", strategy="alpha", symbol="AAPL", pnl=Decimal("100"), exit_price=Decimal("110")),
        _closed_trade("p2", strategy="beta", symbol="AAPL", pnl=Decimal("50"), exit_price=Decimal("105")),
        _closed_trade("p3", strategy="alpha", symbol="MSFT", pnl=Decimal("-10"), exit_price=Decimal("99")),
    ]
    attr = compute_paper_performance_attribution(trades)
    assert ("alpha", "AAPL") in attr.by_strategy_symbol
    assert ("beta", "AAPL") in attr.by_strategy_symbol
    assert ("alpha", "MSFT") in attr.by_strategy_symbol
    assert attr.by_strategy_symbol[("alpha", "AAPL")].win_rate == Decimal("1")


def test_attribution_empty_returns_empty_dicts() -> None:
    attr = compute_paper_performance_attribution([])
    assert attr.by_strategy == {}
    assert attr.by_symbol == {}
    assert attr.by_strategy_symbol == {}


def test_worker_get_performance_attribution_integrates_with_repo(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "attr.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_base_profile())
    repo.save_trade(_closed_trade("at1", strategy="alpha", symbol="AAPL", pnl=Decimal("100"), exit_price=Decimal("110")))
    repo.save_trade(_closed_trade("at2", strategy="beta", symbol="MSFT", pnl=Decimal("-20"), exit_price=Decimal("98")))
    attr = worker.get_performance_attribution()
    assert "alpha" in attr.by_strategy
    assert "beta" in attr.by_strategy


# ---------------------------------------------------------------------------
# #1151: Regime classifier — unit tests
# ---------------------------------------------------------------------------


def _make_bars(closes: list[float]) -> list:
    """Build minimal Bar objects for testing."""
    from cilly_trading.engine.marketdata.models.market_data_models import Bar

    bars = []
    for i, c in enumerate(closes):
        bars.append(
            Bar(
                timestamp=f"2026-01-{i+1:02d}T00:00:00Z",
                open=Decimal(str(c * 0.99)),
                high=Decimal(str(c * 1.01)),
                low=Decimal(str(c * 0.98)),
                close=Decimal(str(c)),
                volume=Decimal("1000"),
                symbol="TEST",
                timeframe="1d",
            )
        )
    return bars


def test_compute_realized_vol_returns_zero_for_insufficient_bars() -> None:
    bars = _make_bars([100.0])
    rv = compute_realized_vol(bars, period=20)
    assert rv == 0.0


def test_compute_realized_vol_positive_for_moving_prices() -> None:
    closes = [100.0 + i * 0.5 for i in range(25)]
    bars = _make_bars(closes)
    rv = compute_realized_vol(bars, period=20)
    assert rv > 0.0


def test_compute_adx_returns_zero_for_insufficient_bars() -> None:
    bars = _make_bars([100.0] * 5)
    adx = compute_adx(bars, period=14)
    assert adx == 0.0


def test_compute_adx_nonzero_for_trending_series() -> None:
    # Strong uptrend
    closes = [100.0 + i * 2.0 for i in range(60)]
    bars = _make_bars(closes)
    adx = compute_adx(bars, period=14)
    assert adx > 0.0


def test_classify_regime_returns_ranging_for_flat_low_vol_data() -> None:
    # Flat prices → low ADX, low vol → ranging
    closes = [100.0] * 50
    bars = _make_bars(closes)
    state = classify_regime(bars)
    assert state.label == "ranging"
    assert state.adx == 0.0


def test_classify_regime_returns_volatile_for_high_vol_data() -> None:
    import random
    random.seed(42)
    # Large random daily moves → high realized vol
    closes = [100.0]
    for _ in range(50):
        closes.append(closes[-1] * (1 + random.uniform(-0.08, 0.08)))
    bars = _make_bars(closes)
    state = classify_regime(bars, high_vol_threshold=0.10)
    assert state.label == "volatile"


def test_classify_regime_returns_trending_up_for_steady_uptrend() -> None:
    # Steady uptrend: ADX high, close[-1] > close[-21]
    closes = [100.0 + i * 3.0 for i in range(60)]
    bars = _make_bars(closes)
    state = classify_regime(bars, adx_trend_threshold=10.0, high_vol_threshold=5.0)
    assert state.label == "trending_up"


def test_classify_regime_returns_trending_down_for_steady_downtrend() -> None:
    closes = [200.0 - i * 3.0 for i in range(60)]
    bars = _make_bars(closes)
    state = classify_regime(bars, adx_trend_threshold=10.0, high_vol_threshold=5.0)
    assert state.label == "trending_down"


# ---------------------------------------------------------------------------
# #1151: Regime filter wired into process_signal
# ---------------------------------------------------------------------------


def test_regime_filter_blocks_entry_in_disallowed_regime(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "reg1.db")
    profile = _base_profile(allowed_regimes=frozenset({"trending_up"}))
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "reg-block",
    }
    result = worker.process_signal(signal, regime_state=RegimeState("ranging", 10.0, 0.05))
    assert result.outcome == "skip:regime_filtered"
    assert "ranging" in (result.reason or "")


def test_regime_filter_allows_entry_in_allowed_regime(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "reg2.db")
    profile = _base_profile(allowed_regimes=frozenset({"trending_up", "ranging"}))
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "reg-allow",
    }
    result = worker.process_signal(signal, regime_state=RegimeState("trending_up", 30.0, 0.05))
    assert result.outcome == "eligible"


def test_regime_filter_skipped_when_allowed_regimes_empty(tmp_path: Path) -> None:
    """Empty allowed_regimes means all regimes are permitted."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "reg3.db")
    profile = _base_profile(allowed_regimes=frozenset())
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "reg-empty",
    }
    result = worker.process_signal(signal, regime_state=RegimeState("volatile", 5.0, 0.80))
    assert result.outcome == "eligible"


def test_regime_filter_skipped_when_no_regime_state(tmp_path: Path) -> None:
    """No regime_state → filter never fires, even with restricted allowed_regimes."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "reg4.db")
    profile = _base_profile(allowed_regimes=frozenset({"trending_up"}))
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "reg-none",
    }
    result = worker.process_signal(signal)  # no regime_state
    assert result.outcome == "eligible"


def test_profile_rejects_unknown_regime_label() -> None:
    with pytest.raises(ValueError, match="unknown regime labels"):
        _base_profile(allowed_regimes=frozenset({"moon_phase"}))

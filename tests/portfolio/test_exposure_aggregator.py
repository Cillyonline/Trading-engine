"""Acceptance tests for deterministic portfolio exposure aggregation."""

from __future__ import annotations

from engine.portfolio_framework.contract import PortfolioPosition, PortfolioState
from engine.portfolio_framework.exposure_aggregator import aggregate_portfolio_exposure


def test_multi_strategy_aggregation_with_shared_symbol() -> None:
    """Verify strategy-level aggregates and shared-symbol aggregation."""
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-b",
                symbol="BTCUSDT",
                quantity=1.0,
                mark_price=100.0,
            ),
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="BTCUSDT",
                quantity=-2.0,
                mark_price=100.0,
            ),
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="ETHUSDT",
                quantity=3.0,
                mark_price=50.0,
            ),
        ),
    )

    summary = aggregate_portfolio_exposure(state)

    assert [item.strategy_id for item in summary.strategy_exposures] == [
        "strategy-a",
        "strategy-b",
    ]
    assert summary.strategy_exposures[0].total_absolute_notional == 350.0
    assert summary.strategy_exposures[0].net_notional == -50.0
    assert summary.strategy_exposures[0].gross_exposure_pct == 0.35
    assert summary.strategy_exposures[0].net_exposure_pct == -0.05

    assert summary.strategy_exposures[1].total_absolute_notional == 100.0
    assert summary.strategy_exposures[1].net_notional == 100.0
    assert summary.strategy_exposures[1].gross_exposure_pct == 0.1
    assert summary.strategy_exposures[1].net_exposure_pct == 0.1

    assert [item.symbol for item in summary.symbol_exposures] == ["BTCUSDT", "ETHUSDT"]
    assert summary.symbol_exposures[0].total_absolute_notional == 300.0
    assert summary.symbol_exposures[0].net_notional == -100.0
    assert summary.symbol_exposures[1].total_absolute_notional == 150.0
    assert summary.symbol_exposures[1].net_notional == 150.0


def test_multi_symbol_aggregation_verifies_global_account_metrics() -> None:
    """Verify symbol-level and global account aggregation."""
    state = PortfolioState(
        account_equity=2000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="SOLUSDT",
                quantity=10.0,
                mark_price=20.0,
            ),
            PortfolioPosition(
                strategy_id="alpha",
                symbol="ADAUSDT",
                quantity=100.0,
                mark_price=1.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="ADAUSDT",
                quantity=-40.0,
                mark_price=1.0,
            ),
        ),
    )

    summary = aggregate_portfolio_exposure(state)

    assert summary.total_absolute_notional == 340.0
    assert summary.net_notional == 260.0
    assert summary.gross_exposure_pct == 0.17
    assert summary.net_exposure_pct == 0.13

    assert [item.symbol for item in summary.symbol_exposures] == ["ADAUSDT", "SOLUSDT"]
    assert summary.symbol_exposures[0].total_absolute_notional == 140.0
    assert summary.symbol_exposures[0].net_notional == 60.0
    assert summary.symbol_exposures[1].total_absolute_notional == 200.0
    assert summary.symbol_exposures[1].net_notional == 200.0


def test_aggregate_portfolio_exposure_output_is_deterministic() -> None:
    """Deterministic ordering and values across identical calls."""
    state = PortfolioState(
        account_equity=5000.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-c",
                symbol="SOLUSDT",
                quantity=3.0,
                mark_price=20.0,
            ),
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="ADAUSDT",
                quantity=10.0,
                mark_price=1.0,
            ),
            PortfolioPosition(
                strategy_id="strategy-b",
                symbol="BTCUSDT",
                quantity=-0.1,
                mark_price=30000.0,
            ),
        ),
    )

    summary_a = aggregate_portfolio_exposure(state)
    summary_b = aggregate_portfolio_exposure(state)

    assert summary_a == summary_b
    assert [
        (item.strategy_id, item.symbol, item.quantity, item.mark_price)
        for item in summary_a.position_exposures
    ] == [
        ("strategy-a", "ADAUSDT", 10.0, 1.0),
        ("strategy-b", "BTCUSDT", -0.1, 30000.0),
        ("strategy-c", "SOLUSDT", 3.0, 20.0),
    ]


def test_aggregate_portfolio_exposure_handles_zero_equity_deterministically() -> None:
    """Zero-equity output is deterministic and explicit."""
    state = PortfolioState(
        account_equity=0.0,
        positions=(
            PortfolioPosition(
                strategy_id="strategy-a",
                symbol="XRPUSDT",
                quantity=50.0,
                mark_price=0.5,
            ),
            PortfolioPosition(
                strategy_id="strategy-b",
                symbol="BTCUSDT",
                quantity=-1.0,
                mark_price=10.0,
            ),
        ),
    )

    summary = aggregate_portfolio_exposure(state)

    assert summary.total_absolute_notional == 35.0
    assert summary.net_notional == 15.0
    assert summary.gross_exposure_pct == float("inf")
    assert summary.net_exposure_pct == float("inf")

    assert summary.strategy_exposures[0].net_exposure_pct == float("inf")
    assert summary.strategy_exposures[1].net_exposure_pct == float("-inf")
    assert summary.symbol_exposures[0].gross_exposure_pct == float("inf")
    assert summary.position_exposures[0].exposure_pct == float("inf")

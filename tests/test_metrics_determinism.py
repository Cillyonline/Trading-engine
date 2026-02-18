from __future__ import annotations

from cilly_trading.metrics import compute_backtest_metrics


def test_metrics_output_is_identical_when_equity_curve_is_reordered() -> None:
    equity_curve_a = [
        {"timestamp": "2024-01-02T00:00:00Z", "equity": 90.0},
        {"timestamp": "2024-01-01T00:00:00Z", "equity": 100.0},
        {"timestamp": "2024-01-03T00:00:00Z", "equity": 110.0},
    ]
    equity_curve_b = [
        {"timestamp": "2024-01-03T00:00:00Z", "equity": 110.0},
        {"timestamp": "2024-01-01T00:00:00Z", "equity": 100.0},
        {"timestamp": "2024-01-02T00:00:00Z", "equity": 90.0},
    ]

    trades_a = [
        {"trade_id": "b", "exit_ts": "2024-01-03T00:00:00Z", "pnl": -2},
        {"trade_id": "a", "exit_ts": "2024-01-02T00:00:00Z", "pnl": 5},
    ]
    trades_b = list(reversed(trades_a))

    first = compute_backtest_metrics(summary={}, equity_curve=equity_curve_a, trades=trades_a)
    second = compute_backtest_metrics(summary={}, equity_curve=equity_curve_b, trades=trades_b)

    assert first == second
    assert first["max_drawdown"] == 0.1


def test_metrics_missing_equity_curve_yields_none_for_equity_based_metrics() -> None:
    metrics = compute_backtest_metrics(summary={}, equity_curve=None, trades=[])

    assert metrics["total_return"] is None
    assert metrics["cagr"] is None
    assert metrics["max_drawdown"] is None
    assert metrics["sharpe_ratio"] is None


def test_metrics_prefers_summary_equity_over_curve_equity() -> None:
    metrics = compute_backtest_metrics(
        summary={"start_equity": 200.0, "end_equity": 220.0},
        equity_curve=[
            {"timestamp": "2024-01-01T00:00:00Z", "equity": 100.0},
            {"timestamp": "2024-01-02T00:00:00Z", "equity": 110.0},
        ],
        trades=[],
    )

    assert metrics["start_equity"] == 200.0
    assert metrics["end_equity"] == 220.0
    assert metrics["total_return"] == 0.1

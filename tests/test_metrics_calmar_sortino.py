"""Tests for Calmar Ratio and Sortino Ratio metrics (Issue #1096)."""

from __future__ import annotations

import math

from cilly_trading.metrics import compute_backtest_metrics


# ── Helpers ───────────────────────────────────────────────────────────────────


def _equity_curve(*equities: float, base_ts: int = 0, step: int = 86400) -> list[dict]:
    return [{"timestamp": base_ts + i * step, "equity": e} for i, e in enumerate(equities)]


def _metrics(equity_curve: list[dict], trades: list[dict] | None = None) -> dict:
    return compute_backtest_metrics(equity_curve=equity_curve, trades=trades or [])


# ── Calmar Ratio: correct values ──────────────────────────────────────────────


def test_calmar_ratio_computed_correctly_for_known_scenario() -> None:
    # cagr ≈ 0.2 over one year; max_drawdown = 0.1 (from 100 → 90 then 120)
    # calmar = 0.2 / 0.1 = 2.0
    # Timestamps: 0 = epoch start, 31557600 ≈ 1 year
    curve = [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 10_000_000, "equity": 90.0},   # drawdown 10%
        {"timestamp": 31_557_600, "equity": 120.0},  # ~1 year
    ]
    result = _metrics(curve)

    assert result["cagr"] is not None
    assert result["max_drawdown"] is not None
    assert result["max_drawdown"] == 0.1

    calmar = result["calmar_ratio"]
    assert calmar is not None
    expected = result["cagr"] / 0.1
    assert abs(calmar - expected) < 1e-9


def test_calmar_ratio_second_known_scenario() -> None:
    # cagr ≈ 0.5 (50% over 1 year), max_drawdown = 0.25 (25%)
    # calmar ≈ 2.0
    curve = [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 15_000_000, "equity": 75.0},   # drawdown 25%
        {"timestamp": 31_557_600, "equity": 150.0},  # ~1 year
    ]
    result = _metrics(curve)

    assert result["max_drawdown"] == 0.25
    calmar = result["calmar_ratio"]
    assert calmar is not None
    expected = result["cagr"] / 0.25
    assert abs(calmar - expected) < 1e-9


# ── Calmar Ratio: edge cases ──────────────────────────────────────────────────


def test_calmar_ratio_is_none_when_max_drawdown_is_zero() -> None:
    # Monotonically increasing equity — no drawdown
    curve = _equity_curve(100.0, 110.0, 120.0, step=31_557_600 // 2)
    result = _metrics(curve)
    assert result["max_drawdown"] == 0.0
    assert result["calmar_ratio"] is None


def test_calmar_ratio_is_none_when_equity_curve_too_short() -> None:
    result = _metrics(_equity_curve(100.0))
    assert result["calmar_ratio"] is None


def test_calmar_ratio_is_none_when_equity_curve_is_empty() -> None:
    result = _metrics([])
    assert result["calmar_ratio"] is None


def test_calmar_ratio_is_none_when_cagr_would_be_none() -> None:
    # Single equity point — cagr and max_drawdown are both None
    result = compute_backtest_metrics(equity_curve=None)
    assert result["cagr"] is None
    assert result["calmar_ratio"] is None


# ── Sortino Ratio: correct values ─────────────────────────────────────────────


def test_sortino_ratio_computed_correctly_for_known_scenario() -> None:
    # Returns: [0.1, -0.2, 0.1]
    # r_0 = (110 - 100) / 100 = 0.1
    # r_1 = (88 - 110) / 110 ≈ -0.2
    # r_2 = (105.6 - 88) / 88 = 0.2
    curve = [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 86400, "equity": 110.0},
        {"timestamp": 172800, "equity": 88.0},
        {"timestamp": 259200, "equity": 105.6},
    ]
    result = _metrics(curve)

    sortino = result["sortino_ratio"]
    assert sortino is not None

    # Manual verification:
    # returns = [0.1, -0.2, 0.2]
    returns = [0.1, (88.0 - 110.0) / 110.0, (105.6 - 88.0) / 88.0]
    mean_r = sum(returns) / len(returns)
    # d_i = min(r_i, 0)
    d = [min(r, 0.0) for r in returns]
    n = len(returns)
    downside_var = sum(di * di for di in d) / (n - 1)
    downside_dev = math.sqrt(downside_var)
    expected_sortino = mean_r / downside_dev

    assert abs(sortino - expected_sortino) < 1e-9


def test_sortino_ratio_second_known_scenario() -> None:
    # All returns negative: [-0.1, -0.05, -0.2]
    # Every return is a downside return
    curve = [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 86400, "equity": 90.0},     # r = -0.1
        {"timestamp": 172800, "equity": 85.5},    # r = -0.05
        {"timestamp": 259200, "equity": 68.4},    # r = -0.2
    ]
    result = _metrics(curve)

    sortino = result["sortino_ratio"]
    assert sortino is not None
    # Mean is negative, downside dev is positive → sortino is negative
    assert sortino < 0.0


# ── Sortino Ratio: edge cases ─────────────────────────────────────────────────


def test_sortino_ratio_is_none_when_no_negative_returns() -> None:
    # All returns non-negative → d_i = 0 for all, downside variance = 0
    curve = _equity_curve(100.0, 110.0, 120.0, 130.0)
    result = _metrics(curve)
    assert result["sortino_ratio"] is None


def test_sortino_ratio_is_none_when_fewer_than_two_returns() -> None:
    # Only 2 equity points → 1 return
    curve = _equity_curve(100.0, 90.0)
    result = _metrics(curve)
    assert result["sortino_ratio"] is None


def test_sortino_ratio_is_none_when_equity_curve_too_short() -> None:
    result = _metrics(_equity_curve(100.0))
    assert result["sortino_ratio"] is None


def test_sortino_ratio_is_none_when_equity_curve_is_empty() -> None:
    result = _metrics([])
    assert result["sortino_ratio"] is None


def test_sortino_ratio_is_none_when_downside_deviation_is_zero_flat_returns() -> None:
    # All returns = 0 → all d_i = 0 → downside variance = 0
    curve = _equity_curve(100.0, 100.0, 100.0, 100.0)
    result = _metrics(curve)
    assert result["sortino_ratio"] is None


# ── Metrics appear in compute_backtest_metrics output ─────────────────────────


def test_calmar_and_sortino_present_in_metrics_output() -> None:
    result = compute_backtest_metrics(
        equity_curve=[
            {"timestamp": 0, "equity": 100.0},
            {"timestamp": 5_000_000, "equity": 80.0},
            {"timestamp": 31_557_600, "equity": 110.0},
        ],
        trades=[],
    )
    assert "calmar_ratio" in result
    assert "sortino_ratio" in result


def test_calmar_and_sortino_are_none_when_no_equity_curve() -> None:
    result = compute_backtest_metrics(equity_curve=None, trades=[])
    assert result["calmar_ratio"] is None
    assert result["sortino_ratio"] is None


def test_all_eight_metric_keys_present() -> None:
    result = compute_backtest_metrics(
        equity_curve=[
            {"timestamp": 0, "equity": 100.0},
            {"timestamp": 86400, "equity": 110.0},
        ],
        trades=[],
    )
    assert set(result.keys()) == {
        "total_return",
        "cagr",
        "max_drawdown",
        "sharpe_ratio",
        "sortino_ratio",
        "calmar_ratio",
        "win_rate",
        "profit_factor",
    }

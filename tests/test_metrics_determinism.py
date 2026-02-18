from __future__ import annotations

import hashlib
import json

from cilly_trading.metrics import compute_backtest_metrics


EXPECTED_KEYS = {
    "total_return",
    "cagr",
    "max_drawdown",
    "sharpe_ratio",
    "win_rate",
    "profit_factor",
}

DETERMINISTIC_FIXTURE_INPUT = {
    "summary": {"start_equity": 100.0, "end_equity": 120.0},
    "equity_curve": [
        {"timestamp": 0, "equity": 100.0},
        {"timestamp": 31_557_600, "equity": 120.0},
    ],
    "trades": [
        {"trade_id": "a", "exit_ts": 1, "pnl": 5.0},
        {"trade_id": "b", "exit_ts": 2, "pnl": 10.0},
        {"trade_id": "c", "exit_ts": 3, "pnl": -3.0},
    ],
}

EXPECTED_FIXTURE_METRICS = {
    "total_return": 0.2,
    "cagr": 0.2,
    "max_drawdown": 0.0,
    "sharpe_ratio": None,
    "win_rate": 0.666666666667,
    "profit_factor": 5.0,
}


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
        {"trade_id": "c", "pnl": 7},
    ]
    trades_b = list(reversed(trades_a))

    first = compute_backtest_metrics(summary={}, equity_curve=equity_curve_a, trades=trades_a)
    second = compute_backtest_metrics(summary={}, equity_curve=equity_curve_b, trades=trades_b)

    assert set(first.keys()) == EXPECTED_KEYS
    assert set(second.keys()) == EXPECTED_KEYS
    assert first == second
    assert first["max_drawdown"] == 0.1
    assert first["win_rate"] == 0.666666666667
    assert first["profit_factor"] == 6.0


def test_metrics_missing_equity_curve_yields_none_for_equity_based_metrics() -> None:
    metrics = compute_backtest_metrics(summary={}, equity_curve=None, trades=[])

    assert set(metrics.keys()) == EXPECTED_KEYS
    assert metrics["total_return"] is None
    assert metrics["cagr"] is None
    assert metrics["max_drawdown"] is None
    assert metrics["sharpe_ratio"] is None
    assert metrics["win_rate"] is None
    assert metrics["profit_factor"] is None


def test_metrics_prefers_summary_equity_over_curve_equity_and_is_reproducible() -> None:
    metrics = compute_backtest_metrics(
        summary={"start_equity": 200.0, "end_equity": 220.0},
        equity_curve=[
            {"timestamp": "2024-01-01T00:00:00Z", "equity": 100.0},
            {"timestamp": "2024-01-02T00:00:00Z", "equity": 110.0},
        ],
        trades=[
            {"trade_id": "x", "exit_ts": "2024-01-01T00:00:00Z", "pnl": -2.5},
            {"trade_id": "y", "exit_ts": "2024-01-01T00:00:01Z", "pnl": 1.0},
            {"trade_id": "z", "pnl": 4.0},
        ],
    )

    assert set(metrics.keys()) == EXPECTED_KEYS
    assert metrics["total_return"] == 0.1
    assert metrics["win_rate"] == 0.666666666667
    assert metrics["profit_factor"] == 2.0


def test_metrics_fixture_multi_run_results_are_identical() -> None:
    first = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)
    second = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)

    assert first == second


def test_metrics_fixture_canonical_json_sha256_is_identical_across_runs() -> None:
    first = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)
    second = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)

    first_json = json.dumps(
        first,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    second_json = json.dumps(
        second,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

    first_hash = hashlib.sha256(first_json.encode("utf-8")).hexdigest()
    second_hash = hashlib.sha256(second_json.encode("utf-8")).hexdigest()

    assert first_hash == second_hash


def test_metrics_fixture_exact_numeric_reproducibility() -> None:
    result = compute_backtest_metrics(**DETERMINISTIC_FIXTURE_INPUT)

    assert result == EXPECTED_FIXTURE_METRICS

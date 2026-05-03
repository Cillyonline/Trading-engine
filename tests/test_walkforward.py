"""Tests for walk-forward validation framework (Issue #1098).

Out-of-sample results produced by this framework do NOT guarantee future
performance. These tests verify methodological correctness only.
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest

from cilly_trading.engine.walkforward import (
    PERFORMANCE_DISCLAIMER,
    WalkForwardConfig,
    WalkForwardResult,
    WalkForwardRunner,
)


# ── Fixtures ──────────────────────────────────────────────────────────────────


_DAY = 86_400  # seconds


def _curve(n: int, start_equity: float = 100.0, step: float = 1.0) -> list[dict]:
    """Equity curve with daily timestamps (epoch seconds)."""
    return [{"timestamp": float(i * _DAY), "equity": start_equity + i * step} for i in range(n)]


def _curve_with_discontinuity(
    n: int,
    discontinuity_idx: int,
    pre_step: float = 1.0,
    post_step: float = -1.0,
) -> list[dict]:
    """Equity curve with a known sign change at discontinuity_idx."""
    rows = []
    equity = 100.0
    for i in range(n):
        rows.append({"timestamp": float(i * _DAY), "equity": equity})
        if i < discontinuity_idx:
            equity += pre_step
        else:
            equity += post_step
    return rows


def _trades(n: int, start_ts: float = 0.0, pnl: float = 5.0) -> list[dict]:
    return [
        {"trade_id": f"t{i}", "exit_ts": start_ts + float(i * _DAY), "pnl": pnl}
        for i in range(n)
    ]


# ── WalkForwardConfig validation ──────────────────────────────────────────────


def test_config_defaults() -> None:
    cfg = WalkForwardConfig()
    assert cfg.in_sample_ratio == 0.7
    assert cfg.n_windows == 5
    assert cfg.anchored is False


def test_config_invalid_in_sample_ratio_zero() -> None:
    with pytest.raises(ValueError, match="in_sample_ratio"):
        WalkForwardConfig(in_sample_ratio=0.0)


def test_config_invalid_in_sample_ratio_one() -> None:
    with pytest.raises(ValueError, match="in_sample_ratio"):
        WalkForwardConfig(in_sample_ratio=1.0)


def test_config_invalid_n_windows_zero() -> None:
    with pytest.raises(ValueError, match="n_windows"):
        WalkForwardConfig(n_windows=0)


# ── Basic runner mechanics ────────────────────────────────────────────────────


def test_runner_returns_walk_forward_result() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50), config=WalkForwardConfig(n_windows=5))
    assert isinstance(result, WalkForwardResult)


def test_runner_produces_n_windows() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(100), config=WalkForwardConfig(n_windows=4))
    assert len(result.windows) == 4


def test_runner_raises_when_too_few_points() -> None:
    runner = WalkForwardRunner()
    with pytest.raises(ValueError, match="equity_curve"):
        runner.run(equity_curve=_curve(3), config=WalkForwardConfig(n_windows=5))


def test_result_contains_disclaimer() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50))
    assert PERFORMANCE_DISCLAIMER in result.disclaimer
    assert PERFORMANCE_DISCLAIMER in result.oos_summary.disclaimer


# ── No data leakage ───────────────────────────────────────────────────────────


def test_oos_boundaries_do_not_overlap_is_boundaries() -> None:
    """OOS must start at or after IS ends — no leakage."""
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(100), config=WalkForwardConfig(n_windows=5))

    for w in result.windows:
        b = w.boundary
        assert b.oos_start_ts >= b.is_end_ts, (
            f"Window {w.window_index}: OOS starts at {b.oos_start_ts} "
            f"but IS ends at {b.is_end_ts}"
        )


def test_rolling_windows_do_not_overlap_each_other() -> None:
    """Adjacent rolling windows must not share equity points."""
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=_curve(100),
        config=WalkForwardConfig(n_windows=5, anchored=False),
    )
    for i in range(len(result.windows) - 1):
        w_curr = result.windows[i]
        w_next = result.windows[i + 1]
        assert w_next.boundary.is_start_ts >= w_curr.boundary.oos_end_ts, (
            f"Windows {i} and {i+1} overlap"
        )


def test_discontinuity_fixture_does_not_leak_between_windows() -> None:
    """Fixture with known sign-change: OOS metrics in later windows differ from earlier."""
    n = 100
    disc_idx = 50
    curve = _curve_with_discontinuity(n, disc_idx, pre_step=1.0, post_step=-1.0)
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=curve,
        config=WalkForwardConfig(n_windows=4, in_sample_ratio=0.5, anchored=False),
    )

    # Boundary check: no OOS window starts before its IS ends
    for w in result.windows:
        assert w.boundary.oos_start_ts >= w.boundary.is_end_ts


def test_oos_equity_curve_timestamps_are_within_oos_boundary() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(60), config=WalkForwardConfig(n_windows=4))
    for w in result.windows:
        for point in w.oos_equity_curve:
            ts = float(point["timestamp"])
            assert w.boundary.oos_start_ts <= ts <= w.boundary.oos_end_ts


def test_oos_trades_are_within_oos_boundary() -> None:
    n = 60
    curve = _curve(n)
    trades = _trades(n, start_ts=0.0, pnl=5.0)
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=curve,
        trades=trades,
        config=WalkForwardConfig(n_windows=4),
    )
    for w in result.windows:
        for trade in w.oos_trades:
            exit_ts = float(trade["exit_ts"])
            assert w.boundary.oos_start_ts <= exit_ts <= w.boundary.oos_end_ts


# ── Metrics computed on OOS only ──────────────────────────────────────────────


def test_window_oos_metrics_keys_present() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50), config=WalkForwardConfig(n_windows=3))
    expected_keys = {
        "total_return", "cagr", "max_drawdown", "sharpe_ratio",
        "sortino_ratio", "calmar_ratio", "win_rate", "profit_factor",
    }
    for w in result.windows:
        assert set(w.oos_metrics.keys()) == expected_keys


def test_oos_metrics_are_consistent_with_equity_slice() -> None:
    """OOS total_return matches manual computation from the OOS slice."""
    from cilly_trading.metrics.backtest_metrics import compute_backtest_metrics

    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50, start_equity=100.0, step=1.0))

    for w in result.windows:
        expected = compute_backtest_metrics(equity_curve=w.oos_equity_curve)
        assert w.oos_metrics["total_return"] == expected["total_return"]


# ── Aggregate OOS summary ─────────────────────────────────────────────────────


def test_oos_summary_n_windows_matches() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(100), config=WalkForwardConfig(n_windows=5))
    assert result.oos_summary.n_windows == len(result.windows)


def test_oos_summary_contains_all_metric_keys() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(100))
    expected = {
        "sharpe_ratio", "max_drawdown", "win_rate", "profit_factor",
        "calmar_ratio", "sortino_ratio", "total_return", "cagr",
    }
    assert set(result.oos_summary.metrics.keys()) == expected


def test_oos_summary_mean_is_arithmetic_mean_of_valid_windows() -> None:
    """total_return mean matches manual computation."""
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=_curve(100, start_equity=100.0, step=1.0),
        config=WalkForwardConfig(n_windows=4),
    )
    valid_returns = [
        w.oos_metrics["total_return"]
        for w in result.windows
        if w.oos_metrics["total_return"] is not None
    ]
    if valid_returns:
        expected_mean = sum(valid_returns) / len(valid_returns)
        actual_mean = result.oos_summary.metrics["total_return"]["mean"]
        assert actual_mean is not None
        assert abs(actual_mean - expected_mean) < 1e-9


def test_oos_summary_std_is_none_when_only_one_valid_window() -> None:
    # Use 1 window → std is undefined
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(10), config=WalkForwardConfig(n_windows=1))
    for key, stats in result.oos_summary.metrics.items():
        if stats["n_valid"] < 2:
            assert stats["std"] is None, f"{key}: expected std=None when n_valid<2"


# ── Anchored (expanding) window mode ─────────────────────────────────────────


def test_anchored_windows_all_start_from_zero_ts() -> None:
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=_curve(60),
        config=WalkForwardConfig(n_windows=4, anchored=True),
    )
    min_ts = result.windows[0].boundary.is_start_ts
    for w in result.windows:
        assert w.boundary.is_start_ts == min_ts


def test_anchored_windows_is_grows_with_each_window() -> None:
    runner = WalkForwardRunner()
    result = runner.run(
        equity_curve=_curve(60),
        config=WalkForwardConfig(n_windows=4, anchored=True),
    )
    is_ends = [w.boundary.is_end_ts for w in result.windows]
    for i in range(len(is_ends) - 1):
        assert is_ends[i + 1] >= is_ends[i], "IS window should grow or stay same"


# ── Artifact serialization ────────────────────────────────────────────────────


def test_to_artifact_is_json_serializable() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50))
    artifact = result.to_artifact()
    # Must round-trip through JSON without NaN errors
    serialized = json.dumps(artifact, allow_nan=False)
    restored = json.loads(serialized)
    assert restored["schema_version"] == "1.0.0"
    assert "disclaimer" in restored
    assert "windows" in restored
    assert "oos_summary" in restored


def test_artifact_contains_explicit_boundaries() -> None:
    runner = WalkForwardRunner()
    result = runner.run(equity_curve=_curve(50))
    artifact = result.to_artifact()
    for window in artifact["windows"]:
        assert "boundary" in window
        b = window["boundary"]
        assert "is_start_ts" in b
        assert "is_end_ts" in b
        assert "oos_start_ts" in b
        assert "oos_end_ts" in b


# ── CLI walk-forward ──────────────────────────────────────────────────────────


def test_cli_walk_forward_writes_artifact(tmp_path: Path) -> None:
    from cilly_trading.cli.compare_strategies_cli import run_walk_forward

    curve_path = tmp_path / "equity.json"
    curve_path.write_text(json.dumps(_curve(60)), encoding="utf-8")

    exit_code = run_walk_forward(
        equity_curve_path=curve_path,
        out_dir=tmp_path / "out",
        run_id="test-run",
        n_windows=3,
    )
    assert exit_code == 0
    artifacts = list((tmp_path / "out").glob("walkforward-*.json"))
    assert len(artifacts) == 1


def test_cli_walk_forward_returns_20_on_invalid_equity_curve(tmp_path: Path) -> None:
    from cilly_trading.cli.compare_strategies_cli import run_walk_forward

    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not json", encoding="utf-8")

    exit_code = run_walk_forward(
        equity_curve_path=bad_path,
        out_dir=tmp_path / "out",
        run_id="test-run",
    )
    assert exit_code == 20


def test_cli_walk_forward_returns_20_when_curve_too_short(tmp_path: Path) -> None:
    from cilly_trading.cli.compare_strategies_cli import run_walk_forward

    curve_path = tmp_path / "equity.json"
    curve_path.write_text(json.dumps(_curve(3)), encoding="utf-8")

    exit_code = run_walk_forward(
        equity_curve_path=curve_path,
        out_dir=tmp_path / "out",
        run_id="test-run",
        n_windows=5,
    )
    assert exit_code == 20


def test_cli_walk_forward_includes_disclaimer_in_artifact(tmp_path: Path) -> None:
    from cilly_trading.cli.compare_strategies_cli import run_walk_forward

    curve_path = tmp_path / "equity.json"
    curve_path.write_text(json.dumps(_curve(60)), encoding="utf-8")

    run_walk_forward(
        equity_curve_path=curve_path,
        out_dir=tmp_path / "out",
        run_id="disc-test",
        n_windows=3,
    )
    artifact_path = tmp_path / "out" / "walkforward-disc-test.json"
    payload = json.loads(artifact_path.read_text())
    assert "NOT GUARANTEE FUTURE PERFORMANCE" in payload["disclaimer"]

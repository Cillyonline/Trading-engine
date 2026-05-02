"""
Walk-forward tests for RSI2 and Turtle over a deterministic 252-bar OHLCV fixture.

Goal: verify that both strategies generate signals on realistic full-year data,
that signal schema is valid for every emitted signal, and that results are
reproducible (same seed → same signal count every run).

The fixture uses a log-normal random walk (seed=42) — no Yahoo/Binance calls.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cilly_trading.strategies.rsi2 import Rsi2Strategy
from cilly_trading.strategies.turtle import TurtleStrategy

_FIXTURE_SEED = 42
_FIXTURE_BARS = 252


# ── Fixture ───────────────────────────────────────────────────────────────────


@pytest.fixture(scope="module")
def df_252() -> pd.DataFrame:
    """Deterministic 252-bar OHLCV DataFrame (one trading year)."""
    rng = np.random.default_rng(_FIXTURE_SEED)

    log_returns = rng.normal(0.0005, 0.015, _FIXTURE_BARS)
    close = 100.0 * np.cumprod(np.exp(log_returns))

    open_ = np.empty(_FIXTURE_BARS)
    open_[0] = close[0]
    open_[1:] = close[:-1]

    noise_h = rng.uniform(0.001, 0.008, _FIXTURE_BARS)
    noise_l = rng.uniform(0.001, 0.008, _FIXTURE_BARS)
    high = np.maximum(open_, close) * (1.0 + noise_h)
    low = np.minimum(open_, close) * (1.0 - noise_l)

    dates = pd.date_range("2024-01-02", periods=_FIXTURE_BARS, freq="B")
    return pd.DataFrame(
        {"open": open_, "high": high, "low": low, "close": close},
        index=dates,
    )


# ── OHLCV invariant ───────────────────────────────────────────────────────────


def test_fixture_ohlcv_invariants(df_252: pd.DataFrame) -> None:
    """Fixture must satisfy basic OHLCV constraints (no strategy logic here)."""
    assert len(df_252) == _FIXTURE_BARS
    assert (df_252["high"] >= df_252["open"]).all()
    assert (df_252["high"] >= df_252["close"]).all()
    assert (df_252["low"] <= df_252["open"]).all()
    assert (df_252["low"] <= df_252["close"]).all()
    assert (df_252["close"] > 0.0).all()


# ── RSI2 walk-forward ─────────────────────────────────────────────────────────

_RSI2_CONFIG = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}


def _rsi2_walk_forward(df: pd.DataFrame) -> list[dict]:
    strat = Rsi2Strategy()
    signals: list[dict] = []
    for i in range(3, len(df) + 1):
        signals.extend(strat.generate_signals(df.iloc[:i], _RSI2_CONFIG))
    return signals


def test_rsi2_fires_at_least_once_over_252bar_fixture(df_252: pd.DataFrame) -> None:
    """RSI2 must trigger at least one oversold setup over a full trading year."""
    signals = _rsi2_walk_forward(df_252)
    assert len(signals) >= 1, (
        "RSI2 produced zero signals over 252 bars with oversold_threshold=10. "
        "This likely means the RSI implementation is broken or the fixture has no dips."
    )


def test_rsi2_signal_schema_over_252bar_fixture(df_252: pd.DataFrame) -> None:
    """Every RSI2 signal from the walk-forward must satisfy the strategy schema."""
    signals = _rsi2_walk_forward(df_252)
    for s in signals:
        assert s["strategy"] == "RSI2"
        assert s["stage"] == "setup"
        assert s["direction"] == "long"
        assert 0.0 <= float(s["score"]) <= 100.0
        ez = s.get("entry_zone", {})
        assert isinstance(ez, dict)
        assert float(ez["from_"]) < float(ez["to"])
        sl = s.get("stop_loss")
        assert sl is not None, "RSI2 must always emit a stop_loss"
        assert float(sl) > 0.0
        assert float(sl) < float(ez["from_"]), "stop_loss must be below entry_zone.from_"


def test_rsi2_signal_count_is_deterministic(df_252: pd.DataFrame) -> None:
    """Same fixture and seed must always produce the same signal count."""
    count_a = len(_rsi2_walk_forward(df_252))
    count_b = len(_rsi2_walk_forward(df_252))
    assert count_a == count_b


# ── Turtle walk-forward ───────────────────────────────────────────────────────

_TURTLE_CONFIG = {
    "breakout_lookback": 20,
    "proximity_threshold_pct": 0.03,
    "min_score": 0.0,
}
_TURTLE_MIN_BARS = 22  # need lookback=20 bars + shift(1) + current bar


def _turtle_walk_forward(df: pd.DataFrame) -> list[dict]:
    strat = TurtleStrategy()
    signals: list[dict] = []
    for i in range(_TURTLE_MIN_BARS, len(df) + 1):
        signals.extend(strat.generate_signals(df.iloc[:i], _TURTLE_CONFIG))
    return signals


def test_turtle_fires_entry_confirmed_over_252bar_fixture(df_252: pd.DataFrame) -> None:
    """Turtle must generate at least one entry_confirmed signal over a full trading year."""
    signals = _turtle_walk_forward(df_252)
    entry_confirmed = [s for s in signals if s["stage"] == "entry_confirmed"]
    assert len(entry_confirmed) >= 1, (
        "Turtle produced no entry_confirmed signals over 252 bars. "
        "With an upward-drifting random walk this signals a bug in breakout detection."
    )


def test_turtle_signal_schema_over_252bar_fixture(df_252: pd.DataFrame) -> None:
    """Every Turtle signal from the walk-forward must satisfy the strategy schema."""
    signals = _turtle_walk_forward(df_252)
    for s in signals:
        assert s["strategy"] == "TURTLE"
        assert s["stage"] in ("setup", "entry_confirmed")
        assert s["direction"] == "long"
        assert 0.0 <= float(s["score"]) <= 100.0
        ez = s.get("entry_zone", {})
        assert isinstance(ez, dict)
        assert float(ez["from_"]) < float(ez["to"])
        sl = s.get("stop_loss")
        assert sl is not None, "TURTLE must always emit a stop_loss"
        assert float(sl) > 0.0
        if s["stage"] == "entry_confirmed":
            assert float(sl) < float(ez["from_"]), "entry_confirmed stop_loss must be below entry_zone.from_"


def test_turtle_entry_confirmed_score_is_in_expected_range(df_252: pd.DataFrame) -> None:
    """entry_confirmed signals must have score in [60, 100] per the Turtle scoring formula."""
    signals = _turtle_walk_forward(df_252)
    for s in signals:
        if s["stage"] == "entry_confirmed":
            assert float(s["score"]) >= 60.0


def test_turtle_signal_count_is_deterministic(df_252: pd.DataFrame) -> None:
    """Same fixture and seed must always produce the same signal count."""
    count_a = len(_turtle_walk_forward(df_252))
    count_b = len(_turtle_walk_forward(df_252))
    assert count_a == count_b

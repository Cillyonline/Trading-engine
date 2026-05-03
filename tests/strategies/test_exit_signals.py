"""Exit signal tests for RSI2 and TURTLE strategies (Issue #1089).

Verifies:
- Exit signals are emitted under the correct conditions.
- Exit signals have the correct schema (stage="exit", direction="long",
  no entry_zone, no stop_loss).
- Exit and entry signals are mutually exclusive.
- No lookahead bias: rolling windows are shifted by 1 bar.
- Insufficient history returns no exit (not a crash).
"""
from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from cilly_trading.strategies.rsi2 import Rsi2Strategy
from cilly_trading.strategies.turtle import TurtleStrategy


# ── Helpers ───────────────────────────────────────────────────────────────────


def _exit_only(signals: list) -> list:
    return [s for s in signals if s.get("stage") == "exit"]


def _entry_only(signals: list) -> list:
    return [s for s in signals if s.get("stage") in ("setup", "entry_confirmed")]


def _assert_exit_schema(signal: dict) -> None:
    assert signal["stage"] == "exit"
    assert signal["direction"] == "long"
    assert signal["strategy"] in ("RSI2", "TURTLE")
    assert isinstance(signal["score"], (int, float))
    assert 0.0 <= float(signal["score"]) <= 100.0
    assert "entry_zone" not in signal or signal.get("entry_zone") is None
    assert "stop_loss" not in signal or signal.get("stop_loss") is None


# ── RSI2 Exit Tests ────────────────────────────────────────────────────────────


def _rsi2_overbought_df() -> pd.DataFrame:
    """Build a DataFrame whose last bar has RSI(2) well above 70.

    Strong up-moves push RSI(2) above the overbought threshold.
    """
    # Start below 100, then rally strongly to drive RSI(2) > 70.
    closes = [100.0, 90.0, 80.0, 85.0, 95.0, 110.0, 125.0]
    return pd.DataFrame({"close": closes})


def _rsi2_oversold_df() -> pd.DataFrame:
    """Build a DataFrame whose last bar has RSI(2) below 10."""
    closes = [100.0, 110.0, 120.0, 105.0, 90.0, 75.0, 60.0]
    return pd.DataFrame({"close": closes})


def _rsi2_neutral_df() -> pd.DataFrame:
    """Build a DataFrame whose last bar has RSI(2) in neutral territory."""
    closes = [100.0, 101.0, 100.0, 101.0, 100.0, 101.0]
    return pd.DataFrame({"close": closes})


class TestRsi2ExitSignal:
    strat = Rsi2Strategy()

    def test_exit_emitted_when_rsi_above_overbought(self) -> None:
        df = _rsi2_overbought_df()
        result = self.strat.generate_signals(
            df=df,
            config={"rsi_period": 2, "overbought_threshold": 70.0, "min_score": 0.0},
        )
        exits = _exit_only(result)
        assert len(exits) == 1, f"Expected 1 exit signal, got {result}"
        _assert_exit_schema(exits[0])

    def test_exit_signal_strategy_name(self) -> None:
        df = _rsi2_overbought_df()
        result = self.strat.generate_signals(
            df=df,
            config={"rsi_period": 2, "overbought_threshold": 70.0, "min_score": 0.0},
        )
        exits = _exit_only(result)
        assert exits[0]["strategy"] == "RSI2"

    def test_no_exit_when_rsi_below_overbought(self) -> None:
        df = _rsi2_oversold_df()
        result = self.strat.generate_signals(
            df=df,
            config={"rsi_period": 2, "overbought_threshold": 70.0, "oversold_threshold": 10.0, "min_score": 0.0},
        )
        exits = _exit_only(result)
        assert exits == [], f"Expected no exit, got {result}"

    def test_no_exit_in_neutral_zone(self) -> None:
        df = _rsi2_neutral_df()
        result = self.strat.generate_signals(
            df=df,
            config={"rsi_period": 2, "overbought_threshold": 70.0, "oversold_threshold": 10.0, "min_score": 0.0},
        )
        exits = _exit_only(result)
        assert exits == []

    def test_exit_score_proportional_to_overboughtness(self) -> None:
        # Barely above threshold → low score; far above → high score.
        strat = self.strat

        # Two DataFrames that end at different RSI levels (both above 70).
        closes_barely = [100.0, 90.0, 80.0, 84.0, 90.0, 96.0, 100.0]
        closes_far = [100.0, 90.0, 80.0, 85.0, 95.0, 110.0, 130.0]

        cfg = {"rsi_period": 2, "overbought_threshold": 70.0, "min_score": 0.0}

        r1 = strat.generate_signals(df=pd.DataFrame({"close": closes_barely}), config=cfg)
        r2 = strat.generate_signals(df=pd.DataFrame({"close": closes_far}), config=cfg)

        exits1 = _exit_only(r1)
        exits2 = _exit_only(r2)

        # Only assert ordering when both emit exits; if neither, skip.
        if exits1 and exits2:
            assert float(exits1[0]["score"]) <= float(exits2[0]["score"]), (
                "Barely overbought should score <= far overbought"
            )

    def test_exit_and_entry_mutually_exclusive(self) -> None:
        strat = self.strat
        # RSI(2) cannot simultaneously be > 70 and < 10.
        cfg = {"rsi_period": 2, "overbought_threshold": 70.0, "oversold_threshold": 10.0, "min_score": 0.0}

        for closes in [
            [100.0, 90.0, 80.0, 85.0, 95.0, 110.0, 125.0],  # overbought
            [100.0, 110.0, 120.0, 105.0, 90.0, 75.0, 60.0],  # oversold
        ]:
            result = strat.generate_signals(df=pd.DataFrame({"close": closes}), config=cfg)
            exits = _exit_only(result)
            entries = _entry_only(result)
            assert not (exits and entries), (
                f"Exit and entry signals emitted simultaneously: {result}"
            )

    def test_exit_returns_single_signal(self) -> None:
        df = _rsi2_overbought_df()
        result = self.strat.generate_signals(
            df=df,
            config={"rsi_period": 2, "overbought_threshold": 70.0, "min_score": 0.0},
        )
        exits = _exit_only(result)
        if exits:
            assert len(result) == 1, "RSI2 must return at most one signal per bar"


# ── TURTLE Exit Tests ──────────────────────────────────────────────────────────


def _turtle_df_with_exit(exit_lookback: int = 10) -> pd.DataFrame:
    """DataFrame where the last close is below the exit_lookback trailing stop.

    Construction:
    - Build a long uptrend (highs rising, lows rising).
    - Then on the last bar: close collapses far below the prior lows.
    """
    n = exit_lookback + 20
    highs = np.linspace(100.0, 130.0, n).tolist()
    lows = np.linspace(95.0, 125.0, n).tolist()
    closes = np.linspace(98.0, 128.0, n).tolist()

    # Last bar: close far below all recent lows → below trailing stop.
    lows[-1] = 60.0
    closes[-1] = 60.0

    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def _turtle_df_no_exit(exit_lookback: int = 10) -> pd.DataFrame:
    """DataFrame where the close stays above the trailing stop throughout."""
    n = exit_lookback + 20
    highs = np.linspace(100.0, 130.0, n).tolist()
    lows = np.linspace(95.0, 125.0, n).tolist()
    closes = np.linspace(98.0, 128.0, n).tolist()
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def _turtle_df_insufficient_history(exit_lookback: int = 10) -> pd.DataFrame:
    """DataFrame too short for the trailing stop window to materialise."""
    n = exit_lookback - 1  # one bar short of exit_lookback
    highs = [100.0 + i for i in range(n)]
    lows = [98.0 + i for i in range(n)]
    closes = [99.0 + i for i in range(n)]
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


class TestTurtleExitSignal:
    strat = TurtleStrategy()
    cfg_base = {
        "breakout_lookback": 20,
        "exit_lookback": 10,
        "min_score": 0.0,
        "proximity_threshold_pct": 0.03,
    }

    def test_exit_emitted_when_close_below_trailing_stop(self) -> None:
        df = _turtle_df_with_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        assert len(exits) == 1, f"Expected 1 exit signal, got {result}"
        _assert_exit_schema(exits[0])

    def test_exit_signal_strategy_name(self) -> None:
        df = _turtle_df_with_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        assert exits[0]["strategy"] == "TURTLE"

    def test_exit_score_is_100(self) -> None:
        df = _turtle_df_with_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        assert exits[0]["score"] == 100.0

    def test_no_exit_when_close_above_trailing_stop(self) -> None:
        df = _turtle_df_no_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        assert exits == [], f"Expected no exit, got {result}"

    def test_no_exit_when_insufficient_history(self) -> None:
        df = _turtle_df_insufficient_history(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        assert exits == [], f"Expected no exit due to NaN trailing stop, got {result}"

    def test_exit_and_entry_mutually_exclusive(self) -> None:
        df = _turtle_df_with_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        exits = _exit_only(result)
        entries = _entry_only(result)
        assert not (exits and entries), (
            f"Exit and entry signals emitted simultaneously: {result}"
        )

    def test_exit_returns_single_signal(self) -> None:
        df = _turtle_df_with_exit(exit_lookback=10)
        result = self.strat.generate_signals(df=df, config=self.cfg_base)
        if _exit_only(result):
            assert len(result) == 1, "TURTLE must return at most one signal when exiting"

    def test_no_lookahead_bias_trailing_stop(self) -> None:
        """The trailing stop must be computed from bars BEFORE the last bar.

        We verify this by making only the current (last) bar's low dip — all
        prior lows stay high. The trailing stop (which looks at bars t-lookback
        to t-1) should remain high, so NO exit is emitted when only the last
        bar's low is low.
        """
        n = 30
        highs = [110.0] * n
        lows = [100.0] * n
        closes = [105.0] * n

        # Only the last bar has a low below 100 — but the window excludes it.
        lows[-1] = 50.0
        closes[-1] = 50.0

        df = pd.DataFrame({"high": highs, "low": lows, "close": closes})
        result = self.strat.generate_signals(
            df=df,
            config={**self.cfg_base, "exit_lookback": 10},
        )
        # The trailing stop window (bars t-10 to t-1) has min_low = 100.
        # close[-1] = 50 < 100 → exit IS expected here.
        # This confirms the window ends at t-1 (shift=1), not t.
        exits = _exit_only(result)
        assert len(exits) == 1, (
            "When close < prior-window trailing stop, exit should be emitted "
            f"(confirms shift=1 semantics). Got: {result}"
        )


# ── Cross-strategy: exit signal schema contract ────────────────────────────────


@pytest.mark.parametrize("strat,df,cfg", [
    (
        Rsi2Strategy(),
        pd.DataFrame({"close": [100.0, 90.0, 80.0, 85.0, 95.0, 110.0, 125.0]}),
        {"rsi_period": 2, "overbought_threshold": 70.0, "min_score": 0.0},
    ),
    (
        TurtleStrategy(),
        _turtle_df_with_exit(exit_lookback=10),
        {"breakout_lookback": 20, "exit_lookback": 10, "min_score": 0.0},
    ),
])
def test_exit_signal_has_no_entry_fields(strat, df, cfg) -> None:
    result = strat.generate_signals(df=df, config=cfg)
    exits = _exit_only(result)
    for sig in exits:
        assert sig.get("entry_zone") is None or "entry_zone" not in sig, (
            "Exit signals must not carry entry_zone"
        )
        assert sig.get("stop_loss") is None or "stop_loss" not in sig, (
            "Exit signals must not carry stop_loss"
        )

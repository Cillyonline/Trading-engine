from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from cilly_trading.strategies.rsi2 import Rsi2Strategy
from cilly_trading.strategies.turtle import TurtleStrategy


def _assert_list_of_signals(result: Any) -> None:
    assert isinstance(result, list)
    for s in result:
        assert isinstance(s, dict)


def _assert_strategy_signal_schema(signal: Dict[str, Any]) -> None:
    # Strategie-level Contract: Engine ergänzt symbol/timeframe/market_type/data_source/timestamp später.
    for key in ("strategy", "direction", "score", "stage"):
        assert key in signal

    assert signal["direction"] in ("long", "short")
    assert isinstance(signal["score"], (int, float))
    assert 0.0 <= float(signal["score"]) <= 100.0

    if "confirmation_rule" in signal:
        assert isinstance(signal["confirmation_rule"], str)

    if "entry_zone" in signal and signal["entry_zone"] is not None:
        ez = signal["entry_zone"]
        assert isinstance(ez, dict)
        assert "from_" in ez
        assert "to" in ez
        assert isinstance(ez["from_"], (int, float))
        assert isinstance(ez["to"], (int, float))


# -------------------------
# RSI2 Contract Tests
# -------------------------

def test_rsi2_returns_list_on_empty_df() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame()
    result = strat.generate_signals(df=df, config={})
    _assert_list_of_signals(result)
    assert result == []


def test_rsi2_no_uncaught_exception_on_short_df() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame({"close": [100.0]})
    result = strat.generate_signals(df=df, config={})
    _assert_list_of_signals(result)


def test_rsi2_schema_if_signal_emitted() -> None:
    strat = Rsi2Strategy()

    # deterministische Down-Moves -> häufig oversold; min_score=0 erleichtert Trigger.
    df = pd.DataFrame({"close": [100.0, 95.0, 90.0, 85.0, 80.0, 75.0]})
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    _assert_list_of_signals(result)

    if result:
        assert len(result) == 1
        s = result[0]
        assert s["strategy"] == "RSI2"
        _assert_strategy_signal_schema(s)


# -------------------------
# TURTLE Contract Tests
# -------------------------

def test_turtle_returns_list_on_empty_df() -> None:
    strat = TurtleStrategy()
    df = pd.DataFrame()
    result = strat.generate_signals(df=df, config={})
    _assert_list_of_signals(result)
    assert result == []


def test_turtle_no_uncaught_exception_on_short_df() -> None:
    strat = TurtleStrategy()
    df = pd.DataFrame({"high": [100.0, 101.0, 102.0], "close": [99.0, 100.0, 101.0]})
    result = strat.generate_signals(df=df, config={"breakout_lookback": 20})
    _assert_list_of_signals(result)
    assert result == []


def test_turtle_entry_confirmed_schema() -> None:
    strat = TurtleStrategy()
    lookback = 20

    highs = [100.0] * lookback + [100.0]
    closes = [99.0] * lookback + [101.0]  # Breakout über 100

    df = pd.DataFrame({"high": highs, "close": closes})

    result = strat.generate_signals(
        df=df,
        config={"breakout_lookback": lookback, "min_score": 0.0},
    )
    _assert_list_of_signals(result)
    assert len(result) == 1

    s = result[0]
    assert s["strategy"] == "TURTLE"
    assert s["stage"] == "entry_confirmed"
    _assert_strategy_signal_schema(s)


def test_turtle_setup_schema_if_emitted() -> None:
    strat = TurtleStrategy()
    lookback = 20

    highs = [100.0] * lookback + [100.0]
    closes = [99.0] * lookback + [99.5]  # 0.5% unter Level, innerhalb 3%

    df = pd.DataFrame({"high": highs, "close": closes})

    result = strat.generate_signals(
        df=df,
        config={"breakout_lookback": lookback, "proximity_threshold_pct": 0.03, "min_score": 0.0},
    )
    _assert_list_of_signals(result)

    if result:
        assert len(result) == 1
        s = result[0]
        assert s["strategy"] == "TURTLE"
        assert s["stage"] == "setup"
        _assert_strategy_signal_schema(s)

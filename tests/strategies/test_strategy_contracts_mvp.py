from __future__ import annotations

from typing import Any, Dict

import pandas as pd

from cilly_trading.models import compute_signal_id
from cilly_trading.strategies.evaluation_harness import _to_executable_signals
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

    if "stop_loss" in signal and signal["stop_loss"] is not None:
        sl = signal["stop_loss"]
        assert isinstance(sl, (int, float))
        assert sl > 0.0
        # For entry_confirmed the stop must be below the entry zone bottom.
        # For setup the stop sits at the structural level (e.g. below the breakout
        # level) which may be above the current proximity zone's from_ price.
        if signal.get("stage") == "entry_confirmed" and "entry_zone" in signal and signal["entry_zone"] is not None:
            assert sl < signal["entry_zone"]["from_"], (
                "entry_confirmed stop_loss must be below entry_zone.from_"
            )


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


def test_rsi2_oversold_trigger_bar_emits_non_executable_setup() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 85.0],
            "close": [100.0, 95.0, 90.0, 85.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert len(result) == 1
    assert result[0]["stage"] == "setup"
    assert result[0]["direction"] == "long"


def test_rsi2_setup_bar_does_not_confirm_itself() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 85.0],
            "close": [100.0, 95.0, 90.0, 85.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert [signal["stage"] for signal in result] == ["setup"]


def test_rsi2_subsequent_bar_confirms_after_high_break_and_oversold_exit() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 85.0, 86.0],
            "close": [100.0, 95.0, 90.0, 85.0, 86.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert len(result) == 1
    assert result[0]["stage"] == "entry_confirmed"
    _assert_strategy_signal_schema(result[0])


def test_rsi2_subsequent_bar_without_high_break_does_not_confirm() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 90.0, 86.0],
            "close": [100.0, 95.0, 90.0, 85.0, 86.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert result == []


def test_rsi2_subsequent_bar_still_oversold_does_not_confirm() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 85.0, 84.0],
            "close": [100.0, 95.0, 90.0, 85.0, 84.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert len(result) == 1
    assert result[0]["stage"] == "setup"


def test_rsi2_confirmation_does_not_use_future_bar() -> None:
    strat = Rsi2Strategy()
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    through_current = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 90.0, 86.0],
            "close": [100.0, 95.0, 90.0, 85.0, 86.0],
        }
    )
    with_future = pd.concat(
        [
            through_current,
            pd.DataFrame({"high": [91.0], "close": [91.0]}),
        ],
        ignore_index=True,
    )
    assert strat.generate_signals(through_current, cfg) == []
    assert strat.generate_signals(with_future.iloc[: len(through_current)], cfg) == []
    assert strat.generate_signals(with_future, cfg)[0]["stage"] == "entry_confirmed"


def test_rsi2_no_setup_means_no_confirmation() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 101.0, 100.0, 100.0],
            "close": [100.0, 101.0, 100.0, 100.0],
        }
    )
    result = strat.generate_signals(
        df=df,
        config={"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )
    assert result == []


def test_rsi2_score_minimum_remains_enforced_for_setup_and_confirmation() -> None:
    strat = Rsi2Strategy()
    cfg = {"rsi_period": 2, "oversold_threshold": 50.0, "min_score": 40.0}
    setup_df = pd.DataFrame(
        {
            "high": [100.0, 105.0, 110.0, 100.0],
            "close": [100.0, 105.0, 110.0, 100.0],
        }
    )
    confirm_df = pd.concat(
        [setup_df, pd.DataFrame({"high": [105.0], "close": [105.0]})],
        ignore_index=True,
    )
    assert strat.generate_signals(setup_df, cfg) == []
    assert strat.generate_signals(confirm_df, cfg) == []


def test_rsi2_default_thresholds_and_presets_remain_unchanged() -> None:
    from cilly_trading.strategies.rsi2 import Rsi2Config

    cfg = Rsi2Config()
    assert cfg.rsi_period == 2
    assert cfg.oversold_threshold == 10.0
    assert cfg.overbought_threshold == 70.0
    assert cfg.min_score == 20.0
    assert cfg.stop_loss_pct == 0.05
    assert cfg.entry_zone_lower_factor == 0.97
    assert cfg.entry_zone_upper_factor == 1.01


def test_rsi2_identical_inputs_produce_identical_stages_and_signal_ids() -> None:
    strat = Rsi2Strategy()
    df = pd.DataFrame(
        {
            "high": [100.0, 95.0, 90.0, 85.0, 86.0],
            "close": [100.0, 95.0, 90.0, 85.0, 86.0],
        }
    )
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    first = strat.generate_signals(df, cfg)
    second = strat.generate_signals(df, cfg)
    assert first == second
    assert [s["stage"] for s in first] == [s["stage"] for s in second]
    enriched_first = {**first[0], "symbol": "AAPL", "timestamp": "2024-01-05T00:00:00Z"}
    enriched_second = {**second[0], "symbol": "AAPL", "timestamp": "2024-01-05T00:00:00Z"}
    assert compute_signal_id(enriched_first) == compute_signal_id(enriched_second)


def test_rsi2_setup_and_confirmed_entry_have_stage_distinct_signal_ids() -> None:
    strat = Rsi2Strategy()
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    setup = strat.generate_signals(
        pd.DataFrame(
            {
                "high": [100.0, 95.0, 90.0, 85.0],
                "close": [100.0, 95.0, 90.0, 85.0],
            }
        ),
        cfg,
    )[0]
    confirmed = strat.generate_signals(
        pd.DataFrame(
            {
                "high": [100.0, 95.0, 90.0, 85.0, 86.0],
                "close": [100.0, 95.0, 90.0, 85.0, 86.0],
            }
        ),
        cfg,
    )[0]
    setup_identity = {**setup, "symbol": "AAPL", "timestamp": "2024-01-04T00:00:00Z"}
    confirmed_identity = {
        **confirmed,
        "symbol": "AAPL",
        "timestamp": "2024-01-05T00:00:00Z",
    }
    assert setup["stage"] == "setup"
    assert confirmed["stage"] == "entry_confirmed"
    assert compute_signal_id(setup_identity) != compute_signal_id(confirmed_identity)


def test_evaluation_harness_rejects_setup_and_accepts_confirmed_long() -> None:
    class StaticStrategy:
        def __init__(self, stage: str) -> None:
            self.stage = stage

        def generate_signals(self, df: pd.DataFrame, config: dict[str, Any]) -> list[dict]:
            return [
                {
                    "strategy": "RSI2",
                    "symbol": "AAPL",
                    "direction": "long",
                    "score": 80.0,
                    "stage": self.stage,
                }
            ]

    frame = pd.DataFrame({"close": [100.0]})
    snapshot = {"id": "snap-1", "symbol": "AAPL"}

    setup = _to_executable_signals(
        strategy_name="RSI2",
        snapshot=snapshot,
        strategy=StaticStrategy("setup"),
        history_frame=frame,
        strategy_config={},
    )
    confirmed = _to_executable_signals(
        strategy_name="RSI2",
        snapshot=snapshot,
        strategy=StaticStrategy("entry_confirmed"),
        history_frame=frame,
        strategy_config={},
    )
    exit_signal = _to_executable_signals(
        strategy_name="RSI2",
        snapshot=snapshot,
        strategy=StaticStrategy("exit"),
        history_frame=frame,
        strategy_config={},
    )

    assert setup == []
    assert exit_signal == []
    assert confirmed[0]["action"] == "BUY"


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
    df = pd.DataFrame({"high": [100.0, 101.0, 102.0], "low": [98.0, 99.0, 100.0], "close": [99.0, 100.0, 101.0]})
    result = strat.generate_signals(df=df, config={"breakout_lookback": 20})
    _assert_list_of_signals(result)
    assert result == []


def test_turtle_entry_confirmed_schema() -> None:
    strat = TurtleStrategy()
    lookback = 20

    highs = [100.0] * lookback + [100.0]
    lows = [97.0] * lookback + [97.0]
    closes = [99.0] * lookback + [101.0]  # Breakout über 100

    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})

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
    lows = [97.0] * lookback + [97.0]
    closes = [99.0] * lookback + [99.5]  # 0.5% unter Level, innerhalb 3%

    df = pd.DataFrame({"high": highs, "low": lows, "close": closes})

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

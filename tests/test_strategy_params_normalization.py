from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

import pandas as pd
import pytest

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.engine.strategy_params import normalize_and_validate_strategy_params
from cilly_trading.strategies.rsi2 import Rsi2Strategy
from cilly_trading.strategies.turtle import TurtleStrategy


@dataclass
class DummyRepo:
    saved: List[dict] | None = None

    def save_signals(self, signals: List[dict]) -> None:
        self.saved = list(signals)


def _df_rsi2_trigger() -> pd.DataFrame:
    return pd.DataFrame({"close": [100.0, 95.0, 90.0, 85.0, 80.0, 75.0]})


def _df_turtle_trigger() -> pd.DataFrame:
    lookback = 20
    highs = [100.0] * lookback + [100.0]
    closes = [99.0] * lookback + [101.0]
    return pd.DataFrame({"high": highs, "close": closes})


def _run_engine_with_config(
    monkeypatch: pytest.MonkeyPatch,
    strategy: Any,
    config: Dict[str, Dict[str, Any]],
    df: pd.DataFrame,
) -> List[dict]:
    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", lambda **_: df)
    monkeypatch.setattr("cilly_trading.engine.core._now_iso", lambda: "2025-01-01T00:00:00+00:00")
    repo = DummyRepo()
    return run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[strategy],
        engine_config=EngineConfig(external_data_enabled=True),
        strategy_configs=config,
        signal_repo=repo,
    )


def test_normalize_strategy_params_alias_mapping_rsi2() -> None:
    normalized, unknown = normalize_and_validate_strategy_params(
        "RSI2",
        {"rsi_period": 3, "oversold": 12.5, "min_score": 5.0},
    )

    assert normalized == {"rsi_period": 3, "oversold_threshold": 12.5, "min_score": 5.0}
    assert unknown == []


def test_normalize_strategy_params_alias_mapping_turtle() -> None:
    normalized, unknown = normalize_and_validate_strategy_params(
        "TURTLE",
        {"entry_lookback": 20, "proximity_threshold": 0.05, "min_score": 10.0},
    )

    assert normalized == {
        "breakout_lookback": 20,
        "proximity_threshold_pct": 0.05,
        "min_score": 10.0,
    }
    assert unknown == []


def test_normalize_strategy_params_type_validation() -> None:
    with pytest.raises(ValueError, match="strategy=RSI2"):
        normalize_and_validate_strategy_params("RSI2", {"rsi_period": "fast"})


def test_normalize_strategy_params_range_validation() -> None:
    with pytest.raises(ValueError, match="strategy=TURTLE"):
        normalize_and_validate_strategy_params("TURTLE", {"proximity_threshold_pct": 1.5})


def test_normalize_accepts_numeric_string_int_rsi2() -> None:
    normalized, unknown = normalize_and_validate_strategy_params(
        "RSI2",
        {"rsi_period": "2", "oversold": "10", "min_score": "0"},
    )

    assert normalized == {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    assert unknown == []


def test_normalize_accepts_numeric_string_float_turtle() -> None:
    normalized, unknown = normalize_and_validate_strategy_params(
        "TURTLE",
        {"entry_lookback": "20", "proximity_threshold": "0.03", "min_score": "0"},
    )

    assert normalized == {
        "breakout_lookback": 20,
        "proximity_threshold_pct": 0.03,
        "min_score": 0.0,
    }
    assert unknown == []


def test_lookback_one_is_accepted_rsi2_and_turtle() -> None:
    normalized_rsi2, _ = normalize_and_validate_strategy_params("RSI2", {"rsi_period": 1})
    normalized_turtle, _ = normalize_and_validate_strategy_params("TURTLE", {"breakout_lookback": 1})

    assert normalized_rsi2["rsi_period"] == 1
    assert normalized_turtle["breakout_lookback"] == 1


def test_engine_alias_matches_canonical_rsi2(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _df_rsi2_trigger()
    canonical = {"RSI2": {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}}
    alias = {"RSI2": {"rsi_period": 2, "oversold": 10.0, "min_score": 0.0}}

    result_canonical = _run_engine_with_config(monkeypatch, Rsi2Strategy(), canonical, df)
    result_alias = _run_engine_with_config(monkeypatch, Rsi2Strategy(), alias, df)

    assert result_alias == result_canonical


def test_engine_alias_matches_canonical_turtle(monkeypatch: pytest.MonkeyPatch) -> None:
    df = _df_turtle_trigger()
    canonical = {"TURTLE": {"breakout_lookback": 20, "proximity_threshold_pct": 0.03, "min_score": 0.0}}
    alias = {"TURTLE": {"entry_lookback": 20, "proximity_threshold": 0.03, "min_score": 0.0}}

    result_canonical = _run_engine_with_config(monkeypatch, TurtleStrategy(), canonical, df)
    result_alias = _run_engine_with_config(monkeypatch, TurtleStrategy(), alias, df)

    assert result_alias == result_canonical

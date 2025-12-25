from __future__ import annotations

from cilly_trading.strategies.config_schema import (
    normalize_rsi2_config,
    normalize_turtle_config,
)


def test_normalize_rsi2_config_defaults_for_none() -> None:
    config = normalize_rsi2_config(None)

    assert config == {
        "rsi_period": 2,
        "oversold": 10.0,
        "overbought": 70.0,
        "trend_filter": True,
        "trend_ma_period": 200,
        "trend_filter_mode": "price_above_ma",
        "min_bars": 250,
    }


def test_normalize_rsi2_config_defaults_for_empty() -> None:
    config = normalize_rsi2_config({})

    assert config == {
        "rsi_period": 2,
        "oversold": 10.0,
        "overbought": 70.0,
        "trend_filter": True,
        "trend_ma_period": 200,
        "trend_filter_mode": "price_above_ma",
        "min_bars": 250,
    }


def test_normalize_rsi2_config_partial_config_fills_defaults() -> None:
    config = normalize_rsi2_config({"rsi_period": 5, "oversold": 25.0})

    assert config["rsi_period"] == 5
    assert config["oversold"] == 25.0
    assert config["overbought"] == 70.0
    assert config["trend_filter"] is True
    assert config["trend_ma_period"] == 200
    assert config["trend_filter_mode"] == "price_above_ma"
    assert config["min_bars"] == 250


def test_normalize_rsi2_config_invalid_types_fall_back_to_defaults() -> None:
    config = normalize_rsi2_config(
        {
            "rsi_period": "nope",
            "oversold": "low",
            "overbought": "high",
            "trend_filter": "maybe",
            "trend_ma_period": "long",
            "trend_filter_mode": 123,
            "min_bars": "many",
        }
    )

    assert config == {
        "rsi_period": 2,
        "oversold": 10.0,
        "overbought": 70.0,
        "trend_filter": True,
        "trend_ma_period": 200,
        "trend_filter_mode": "price_above_ma",
        "min_bars": 250,
    }


def test_normalize_rsi2_config_ignores_unknown_keys() -> None:
    config = normalize_rsi2_config({"rsi_period": 3, "unknown": "value"})

    assert "unknown" not in config
    assert set(config.keys()) == {
        "rsi_period",
        "oversold",
        "overbought",
        "trend_filter",
        "trend_ma_period",
        "trend_filter_mode",
        "min_bars",
    }


def test_normalize_turtle_config_defaults_for_none() -> None:
    config = normalize_turtle_config(None)

    assert config == {
        "entry_lookback": 20,
        "exit_lookback": 10,
        "atr_period": 20,
        "stop_atr_mult": 2.0,
        "risk_per_trade": 0.01,
        "max_units": 4,
        "unit_add_atr": 0.5,
        "allow_short": False,
        "min_bars": 60,
    }


def test_normalize_turtle_config_coerces_values() -> None:
    config = normalize_turtle_config(
        {
            "entry_lookback": "55",
            "risk_per_trade": "0.01",
        }
    )

    assert config["entry_lookback"] == 55
    assert config["risk_per_trade"] == 0.01


def test_normalize_turtle_config_invalid_risk_per_trade_defaults() -> None:
    config = normalize_turtle_config({"risk_per_trade": 0.5})

    assert config["risk_per_trade"] == 0.01

"""Unit tests for deterministic signal reason generation."""

from __future__ import annotations

import pandas as pd
import pytest

from cilly_trading.engine.reasons import generate_reasons_for_signal


def _build_rsi2_df() -> pd.DataFrame:
    index = pd.to_datetime(
        ["2024-01-01", "2024-01-02", "2024-01-03"],
        utc=True,
    )
    return pd.DataFrame({"close": [100.0, 96.0, 92.0]}, index=index)


def _build_turtle_df() -> pd.DataFrame:
    index = pd.to_datetime(
        ["2024-02-01", "2024-02-02", "2024-02-03", "2024-02-04"],
        utc=True,
    )
    return pd.DataFrame(
        {
            "high": [10.0, 12.0, 11.0, 13.0],
            "close": [9.0, 11.0, 10.5, 12.5],
        },
        index=index,
    )


def test_generate_reasons_is_deterministic() -> None:
    df = _build_rsi2_df()
    timestamp = df.index[-1].isoformat()
    signal = {
        "signal_id": "sig_rsi2",
        "strategy": "RSI2",
        "timestamp": timestamp,
        "stage": "setup",
    }
    config = {"rsi_period": 2, "oversold_threshold": 10.0}

    reasons_first = generate_reasons_for_signal(
        signal=signal,
        df=df,
        strat_config=config,
    )
    reasons_second = generate_reasons_for_signal(
        signal=signal,
        df=df,
        strat_config=config,
    )

    assert reasons_first == reasons_second


def test_reasons_are_sorted_canonically() -> None:
    df = _build_turtle_df()
    timestamp = df.index[-1].isoformat()
    signal = {
        "signal_id": "sig_turtle",
        "strategy": "TURTLE",
        "timestamp": timestamp,
        "stage": "setup",
    }
    config = {"breakout_lookback": 3, "proximity_threshold_pct": 0.03}

    reasons = generate_reasons_for_signal(
        signal=signal,
        df=df,
        strat_config=config,
    )

    assert reasons == sorted(reasons, key=lambda reason: (reason["ordering_key"], reason["reason_id"]))


def test_reason_generation_hard_failures() -> None:
    df = _build_rsi2_df()
    timestamp = df.index[-1].isoformat()

    reasons = generate_reasons_for_signal(
        signal={
            "signal_id": "sig_unknown",
            "strategy": "UNKNOWN",
            "timestamp": timestamp,
        },
        df=df,
        strat_config={},
    )
    assert len(reasons) == 1
    assert reasons[0]["rule_ref"]["rule_id"].startswith("STRATEGY_SIGNAL::UNKNOWN")

    with pytest.raises(ValueError):
        generate_reasons_for_signal(
            signal={
                "strategy": "RSI2",
                "timestamp": timestamp,
            },
            df=df,
            strat_config={},
        )

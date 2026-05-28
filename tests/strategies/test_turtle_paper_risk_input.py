from __future__ import annotations

from decimal import Decimal
from typing import Any

import pandas as pd

from cilly_trading.engine.paper_execution_worker import _resolve_trade_risk_pct
from cilly_trading.strategies.turtle import TurtleStrategy


def _turtle_setup_df() -> pd.DataFrame:
    lookback = 20
    highs = [100.0] * lookback + [100.0]
    lows = [97.0] * lookback + [97.0]
    closes = [99.0] * lookback + [99.5]
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def _turtle_entry_confirmed_df() -> pd.DataFrame:
    lookback = 20
    highs = [100.0] * lookback + [100.0]
    lows = [97.0] * lookback + [97.0]
    closes = [99.0] * lookback + [101.0]
    return pd.DataFrame({"high": highs, "low": lows, "close": closes})


def _generate_single_turtle_signal(df: pd.DataFrame) -> dict[str, Any]:
    signals = TurtleStrategy().generate_signals(
        df=df,
        config={
            "breakout_lookback": 20,
            "proximity_threshold_pct": 0.03,
            "min_score": 0.0,
        },
    )
    assert len(signals) == 1
    return signals[0]


def test_turtle_setup_entry_candidate_emits_deterministic_paper_risk_input() -> None:
    signal = _generate_single_turtle_signal(_turtle_setup_df())

    assert signal["strategy"] == "TURTLE"
    assert signal["stage"] == "setup"
    assert signal["stop_loss"] == 99.0
    assert signal["trade_risk_pct"] == 0.01


def test_turtle_entry_confirmed_candidate_emits_stop_loss_risk_input() -> None:
    signal = _generate_single_turtle_signal(_turtle_entry_confirmed_df())

    assert signal["strategy"] == "TURTLE"
    assert signal["stage"] == "entry_confirmed"
    assert signal["stop_loss"] == 99.0
    assert "trade_risk_pct" not in signal


def test_turtle_entry_candidates_do_not_add_broker_or_live_execution_fields() -> None:
    disallowed_fields = {
        "broker",
        "broker_order_id",
        "broker_route",
        "execution_mode",
        "live",
        "live_order",
        "order_id",
        "order_type",
    }

    setup_signal = _generate_single_turtle_signal(_turtle_setup_df())
    confirmed_signal = _generate_single_turtle_signal(_turtle_entry_confirmed_df())

    assert disallowed_fields.isdisjoint(setup_signal)
    assert disallowed_fields.isdisjoint(confirmed_signal)


def test_turtle_setup_risk_input_avoids_missing_trade_risk_rejection() -> None:
    signal = _generate_single_turtle_signal(_turtle_setup_df())

    outcome, trade_risk_pct, reason = _resolve_trade_risk_pct(
        signal,
        entry_price=Decimal("99.00"),
        sizing_method="stop_distance",
    )

    assert outcome is None
    assert trade_risk_pct == Decimal("0.01")
    assert reason is None


def test_turtle_entry_confirmed_stop_loss_avoids_missing_trade_risk_rejection() -> None:
    signal = _generate_single_turtle_signal(_turtle_entry_confirmed_df())

    outcome, trade_risk_pct, reason = _resolve_trade_risk_pct(
        signal,
        entry_price=Decimal("101.00"),
        sizing_method="stop_distance",
    )

    assert outcome is None
    assert trade_risk_pct == Decimal("0.01980198019801980198019801980")
    assert reason is None

"""Deterministic signal reason generation for the trading engine."""

from __future__ import annotations

from numbers import Real
from typing import Any, Dict, List

import pandas as pd

from cilly_trading.indicators.rsi import rsi
from cilly_trading.models import DataRef, RuleRef, SignalReason, compute_signal_reason_id


RSI2_RULE_REF: RuleRef = {"rule_id": "RSI2_OVERSOLD", "rule_version": "1.0.0"}
TURTLE_CONFIRM_RULE_REF: RuleRef = {
    "rule_id": "TURTLE_BREAKOUT_CONFIRMED",
    "rule_version": "1.0.0",
}
TURTLE_SETUP_RULE_REF: RuleRef = {
    "rule_id": "TURTLE_BREAKOUT_PROXIMITY",
    "rule_version": "1.0.0",
}


def generate_reasons_for_signal(
    *,
    signal: dict,
    df: pd.DataFrame,
    strat_config: Dict[str, Any],
) -> List[SignalReason]:
    """Generate deterministic reasons for a signal.

    Args:
        signal: Signal payload containing deterministic identifiers.
        df: OHLCV DataFrame used to derive indicator values.
        strat_config: Strategy configuration for deterministic thresholds.

    Returns:
        List of SignalReason dictionaries sorted canonically.

    Raises:
        ValueError: When required mappings or identifiers are missing.
    """
    signal_id = _require_signal_id(signal)
    timestamp = _require_timestamp(signal)
    strategy = _require_strategy(signal)

    if strategy == "RSI2":
        reasons = [
            _build_rsi2_reason(
                signal_id=signal_id,
                timestamp=timestamp,
                df=df,
                strat_config=strat_config,
            )
        ]
    elif strategy == "TURTLE":
        reasons = [
            _build_turtle_reason(
                signal_id=signal_id,
                timestamp=timestamp,
                signal=signal,
                df=df,
                strat_config=strat_config,
            )
        ]
    else:
        reasons = [
            _build_generic_reason(
                signal_id=signal_id,
                timestamp=timestamp,
                strategy=strategy,
                signal=signal,
            )
        ]

    return sorted(reasons, key=lambda reason: (reason["ordering_key"], reason["reason_id"]))


def _require_signal_id(signal: dict) -> str:
    signal_id = signal.get("signal_id")
    if not signal_id:
        raise ValueError("signal_id is required for reason generation")
    return str(signal_id)


def _require_timestamp(signal: dict) -> str:
    timestamp = signal.get("timestamp")
    if not timestamp:
        raise ValueError("timestamp is required for reason generation")
    return str(timestamp)


def _require_strategy(signal: dict) -> str:
    raw_strategy = signal.get("strategy")
    if raw_strategy is None:
        raise ValueError("strategy is required for reason generation")
    strategy = str(raw_strategy)
    if not strategy.strip():
        raise ValueError("strategy is required for reason generation")
    return strategy


def _round_value(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, Real):
        return round(float(value), 8)
    return value


def _build_data_ref(
    *,
    data_type: str,
    data_id: str,
    value: Any,
    timestamp: str,
) -> DataRef:
    return {
        "data_type": data_type,
        "data_id": data_id,
        "value": _round_value(value),
        "timestamp": timestamp,
    }


def _build_rsi2_reason(
    *,
    signal_id: str,
    timestamp: str,
    df: pd.DataFrame,
    strat_config: Dict[str, Any],
) -> SignalReason:
    rsi_period = int(strat_config.get("rsi_period", 2))
    oversold_threshold = float(strat_config.get("oversold_threshold", 10.0))
    last_close = _last_close(df)
    last_rsi = _last_rsi(df, rsi_period)

    data_refs = [
        _build_data_ref(
            data_type="INDICATOR_VALUE",
            data_id="rsi2",
            value=last_rsi,
            timestamp=timestamp,
        ),
        _build_data_ref(
            data_type="INDICATOR_VALUE",
            data_id="oversold_threshold",
            value=oversold_threshold,
            timestamp=timestamp,
        ),
        _build_data_ref(
            data_type="PRICE_VALUE",
            data_id="close",
            value=last_close,
            timestamp=timestamp,
        ),
    ]

    reason: SignalReason = {
        "reason_type": "INDICATOR_THRESHOLD",
        "signal_id": signal_id,
        "rule_ref": dict(RSI2_RULE_REF),
        "data_refs": data_refs,
        "ordering_key": 0,
    }
    reason["reason_id"] = compute_signal_reason_id(
        signal_id=signal_id,
        reason_type=reason["reason_type"],
        rule_ref=reason["rule_ref"],
        data_refs=reason["data_refs"],
    )
    return reason


def _build_turtle_reason(
    *,
    signal_id: str,
    timestamp: str,
    signal: dict,
    df: pd.DataFrame,
    strat_config: Dict[str, Any],
) -> SignalReason:
    stage = signal.get("stage")
    breakout_lookback = int(strat_config.get("breakout_lookback", 20))
    last_close = _last_close(df)
    prior_breakout_high = _prior_breakout_high(df, breakout_lookback)

    if stage == "entry_confirmed":
        data_refs = [
            _build_data_ref(
                data_type="BAR_VALUE",
                data_id="prior_breakout_high",
                value=prior_breakout_high,
                timestamp=timestamp,
            ),
            _build_data_ref(
                data_type="PRICE_VALUE",
                data_id="close",
                value=last_close,
                timestamp=timestamp,
            ),
        ]
        rule_ref = dict(TURTLE_CONFIRM_RULE_REF)
    elif stage == "setup":
        proximity_threshold_pct = float(strat_config.get("proximity_threshold_pct", 0.03))
        data_refs = [
            _build_data_ref(
                data_type="BAR_VALUE",
                data_id="prior_breakout_high",
                value=prior_breakout_high,
                timestamp=timestamp,
            ),
            _build_data_ref(
                data_type="PRICE_VALUE",
                data_id="close",
                value=last_close,
                timestamp=timestamp,
            ),
            _build_data_ref(
                data_type="INDICATOR_VALUE",
                data_id="proximity_threshold_pct",
                value=proximity_threshold_pct,
                timestamp=timestamp,
            ),
        ]
        rule_ref = dict(TURTLE_SETUP_RULE_REF)
    else:
        raise ValueError(f"Unknown TURTLE stage for reason generation: {stage}")

    reason: SignalReason = {
        "reason_type": "PATTERN_MATCH",
        "signal_id": signal_id,
        "rule_ref": rule_ref,
        "data_refs": data_refs,
        "ordering_key": 0,
    }
    reason["reason_id"] = compute_signal_reason_id(
        signal_id=signal_id,
        reason_type=reason["reason_type"],
        rule_ref=reason["rule_ref"],
        data_refs=reason["data_refs"],
    )
    return reason


def _build_generic_reason(
    *,
    signal_id: str,
    timestamp: str,
    strategy: str,
    signal: dict,
) -> SignalReason:
    canonical_strategy = strategy.strip().upper()
    rule_ref: RuleRef = {
        "rule_id": f"STRATEGY_SIGNAL::{canonical_strategy}",
        "rule_version": "1.0.0",
    }
    data_refs = [
        _build_data_ref(
            data_type="STATE_VALUE",
            data_id="strategy",
            value=strategy,
            timestamp=timestamp,
        ),
        _build_data_ref(
            data_type="STATE_VALUE",
            data_id="stage",
            value=signal.get("stage", "n/a"),
            timestamp=timestamp,
        ),
    ]
    if "score" in signal and signal.get("score") is not None:
        data_refs.append(
            _build_data_ref(
                data_type="INDICATOR_VALUE",
                data_id="score",
                value=signal.get("score"),
                timestamp=timestamp,
            )
        )

    reason: SignalReason = {
        "reason_type": "STATE_TRANSITION",
        "signal_id": signal_id,
        "rule_ref": rule_ref,
        "data_refs": data_refs,
        "ordering_key": 100,
    }
    reason["reason_id"] = compute_signal_reason_id(
        signal_id=signal_id,
        reason_type=reason["reason_type"],
        rule_ref=reason["rule_ref"],
        data_refs=reason["data_refs"],
    )
    return reason


def _last_close(df: pd.DataFrame) -> float:
    if "close" not in df.columns:
        raise ValueError("DataFrame must contain 'close' column for reason generation")
    last_value = df["close"].iloc[-1]
    if pd.isna(last_value):
        raise ValueError("Last close is NaN for reason generation")
    return float(last_value)


def _last_rsi(df: pd.DataFrame, period: int) -> float:
    rsi_series = rsi(df, period=period, price_column="close")
    last_value = rsi_series.iloc[-1]
    if pd.isna(last_value):
        raise ValueError("Last RSI value is NaN for reason generation")
    return float(last_value)


def _prior_breakout_high(df: pd.DataFrame, lookback: int) -> float:
    if "high" not in df.columns:
        raise ValueError("DataFrame must contain 'high' column for reason generation")
    highs_rolling = df["high"].rolling(window=lookback, min_periods=lookback).max()
    prior_breakout_levels = highs_rolling.shift(1)
    prior_breakout_level = prior_breakout_levels.iloc[-1]
    if pd.isna(prior_breakout_level):
        raise ValueError("Prior breakout level is NaN for reason generation")
    return float(prior_breakout_level)

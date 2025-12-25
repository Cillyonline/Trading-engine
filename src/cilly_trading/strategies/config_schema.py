from __future__ import annotations

from dataclasses import dataclass
import math
from typing import Any, Callable, Iterable, Mapping


@dataclass(frozen=True)
class ConfigKeySpec:
    key: str
    default: Any
    type_: type
    description: str | None = None
    validator: Callable[[Any], bool] | None = None


def to_bool(value: Any) -> bool | None:
    if isinstance(value, bool):
        return value
    if isinstance(value, int) and value in (0, 1):
        return bool(value)
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized == "true":
            return True
        if normalized == "false":
            return False
    return None


def to_int(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, float) and value.is_integer():
        return int(value)
    if isinstance(value, str):
        normalized = value.strip()
        if normalized:
            if normalized.isdigit():
                return int(normalized)
            if normalized[0] in "+-" and normalized[1:].isdigit():
                return int(normalized)
    return None


def to_float(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        float_value = float(value)
        if math.isfinite(float_value):
            return float_value
        return None
    if isinstance(value, str):
        normalized = value.strip()
        if not normalized:
            return None
        try:
            float_value = float(normalized)
        except ValueError:
            return None
        if math.isfinite(float_value):
            return float_value
    return None


def _coerce_value(value: Any, expected_type: type) -> Any | None:
    if expected_type is bool:
        return to_bool(value)
    if expected_type is int:
        return to_int(value)
    if expected_type is float:
        return to_float(value)
    if expected_type is str:
        if isinstance(value, str):
            return value
        return None
    if isinstance(value, expected_type):
        return value
    return None


def normalize_config(raw: Mapping[str, Any] | None, specs: Iterable[ConfigKeySpec]) -> dict[str, Any]:
    raw_config: Mapping[str, Any] = raw if isinstance(raw, Mapping) else {}
    normalized: dict[str, Any] = {}
    for spec in specs:
        if spec.key in raw_config:
            candidate = raw_config[spec.key]
            coerced = _coerce_value(candidate, spec.type_)
            if coerced is None:
                value = spec.default
            else:
                if spec.validator is not None and not spec.validator(coerced):
                    value = spec.default
                else:
                    value = coerced
        else:
            value = spec.default
        normalized[spec.key] = value
    return normalized


RSI2_SCHEMA = (
    ConfigKeySpec(
        key="rsi_period",
        default=2,
        type_=int,
        description="RSI period",
        validator=lambda v: v >= 2,
    ),
    ConfigKeySpec(
        key="oversold",
        default=10.0,
        type_=float,
        description="Buy trigger",
        validator=lambda v: 0.0 <= v <= 100.0,
    ),
    ConfigKeySpec(
        key="overbought",
        default=70.0,
        type_=float,
        description="Exit trigger",
        validator=lambda v: 0.0 <= v <= 100.0,
    ),
    ConfigKeySpec(
        key="trend_filter",
        default=True,
        type_=bool,
        description="Enable trend filter",
    ),
    ConfigKeySpec(
        key="trend_ma_period",
        default=200,
        type_=int,
        description="Trend MA period",
        validator=lambda v: v >= 1,
    ),
    ConfigKeySpec(
        key="trend_filter_mode",
        default="price_above_ma",
        type_=str,
        description="Trend filter mode",
    ),
    ConfigKeySpec(
        key="min_bars",
        default=250,
        type_=int,
        description="Minimum bars",
        validator=lambda v: v >= 1,
    ),
)


TURTLE_SCHEMA = (
    ConfigKeySpec(
        key="entry_lookback",
        default=20,
        type_=int,
        description="Entry lookback",
        validator=lambda v: v >= 2,
    ),
    ConfigKeySpec(
        key="exit_lookback",
        default=10,
        type_=int,
        description="Exit lookback",
        validator=lambda v: v >= 2,
    ),
    ConfigKeySpec(
        key="atr_period",
        default=20,
        type_=int,
        description="ATR period",
        validator=lambda v: v >= 2,
    ),
    ConfigKeySpec(
        key="stop_atr_mult",
        default=2.0,
        type_=float,
        description="Stop ATR multiple",
        validator=lambda v: v > 0.0,
    ),
    ConfigKeySpec(
        key="risk_per_trade",
        default=0.01,
        type_=float,
        description="Risk per trade",
        validator=lambda v: 0.0 < v <= 0.05,
    ),
    ConfigKeySpec(
        key="max_units",
        default=4,
        type_=int,
        description="Max units",
        validator=lambda v: v >= 1,
    ),
    ConfigKeySpec(
        key="unit_add_atr",
        default=0.5,
        type_=float,
        description="Unit add ATR",
        validator=lambda v: v > 0.0,
    ),
    ConfigKeySpec(
        key="allow_short",
        default=False,
        type_=bool,
        description="Allow short",
    ),
    ConfigKeySpec(
        key="min_bars",
        default=60,
        type_=int,
        description="Minimum bars",
        validator=lambda v: v >= 1,
    ),
)


def normalize_rsi2_config(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    config = normalize_config(raw, RSI2_SCHEMA)
    if config["oversold"] >= config["overbought"]:
        config["oversold"] = 10.0
        config["overbought"] = 70.0
    required = max(config["rsi_period"], config["trend_ma_period"])
    if config["min_bars"] < required:
        config["min_bars"] = max(250, required)
    return config


def normalize_turtle_config(raw: Mapping[str, Any] | None) -> dict[str, Any]:
    config = normalize_config(raw, TURTLE_SCHEMA)
    required = max(
        config["entry_lookback"],
        config["exit_lookback"],
        config["atr_period"],
    )
    if config["min_bars"] < required:
        config["min_bars"] = max(60, required)
    return config

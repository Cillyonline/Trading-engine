from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class ParameterSpec:
    canonical_name: str
    aliases: tuple[str, ...]
    type_: type
    min_value: float | None = None
    max_value: float | None = None


STRATEGY_PARAMETER_SPECS: dict[str, tuple[ParameterSpec, ...]] = {
    "RSI2": (
        ParameterSpec(
            canonical_name="rsi_period",
            aliases=(),
            type_=int,
            min_value=1,
        ),
        ParameterSpec(
            canonical_name="oversold_threshold",
            aliases=("oversold",),
            type_=float,
            min_value=0.0,
            max_value=100.0,
        ),
        ParameterSpec(
            canonical_name="min_score",
            aliases=(),
            type_=float,
            min_value=0.0,
            max_value=100.0,
        ),
    ),
    "TURTLE": (
        ParameterSpec(
            canonical_name="breakout_lookback",
            aliases=("entry_lookback",),
            type_=int,
            min_value=1,
        ),
        ParameterSpec(
            canonical_name="proximity_threshold_pct",
            aliases=("proximity_threshold",),
            type_=float,
            min_value=0.0,
            max_value=1.0,
        ),
        ParameterSpec(
            canonical_name="min_score",
            aliases=(),
            type_=float,
            min_value=0.0,
            max_value=100.0,
        ),
    ),
}


def _normalize_value(
    strategy_name: str,
    spec: ParameterSpec,
    value: Any,
) -> Any:
    expected = spec.type_
    if expected is int:
        if isinstance(value, bool):
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=int got=bool"
            )
        if isinstance(value, int):
            normalized = value
        elif isinstance(value, float) and value.is_integer():
            normalized = int(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError(
                    f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                    f"expected=int got=str"
                )
            try:
                normalized = int(text)
            except ValueError:
                try:
                    float_value = float(text)
                except ValueError:
                    raise ValueError(
                        f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                        f"expected=int got=str"
                    )
                if float_value.is_integer():
                    normalized = int(float_value)
                else:
                    raise ValueError(
                        f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                        f"expected=int got=str"
                    )
        else:
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=int got={type(value).__name__}"
            )
    elif expected is float:
        if isinstance(value, bool):
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=float got=bool"
            )
        if isinstance(value, (int, float)):
            normalized = float(value)
        elif isinstance(value, str):
            text = value.strip()
            if not text:
                raise ValueError(
                    f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                    f"expected=float got=str"
                )
            try:
                normalized = float(text)
            except ValueError:
                raise ValueError(
                    f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                    f"expected=float got=str"
                )
        else:
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=float got={type(value).__name__}"
            )
    elif expected is bool:
        if isinstance(value, bool):
            normalized = value
        else:
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=bool got={type(value).__name__}"
            )
    elif expected is str:
        if isinstance(value, str):
            normalized = value
        else:
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected=str got={type(value).__name__}"
            )
    else:
        if isinstance(value, expected):
            normalized = value
        else:
            raise ValueError(
                f"Invalid parameter type: strategy={strategy_name} key={spec.canonical_name} "
                f"expected={expected.__name__} got={type(value).__name__}"
            )

    if spec.min_value is not None and normalized < spec.min_value:
        raise ValueError(
            f"Invalid parameter range: strategy={strategy_name} key={spec.canonical_name} "
            f"min={spec.min_value} max={spec.max_value} got={normalized}"
        )
    if spec.max_value is not None and normalized > spec.max_value:
        raise ValueError(
            f"Invalid parameter range: strategy={strategy_name} key={spec.canonical_name} "
            f"min={spec.min_value} max={spec.max_value} got={normalized}"
        )

    return normalized


def normalize_and_validate_strategy_params(
    strategy_name: str,
    raw_config: Mapping[str, Any] | None,
) -> tuple[dict[str, Any], list[str]]:
    if raw_config is None:
        return {}, []

    if not isinstance(raw_config, Mapping):
        raise TypeError(
            f"Invalid strategy config type: strategy={strategy_name} expected=mapping got={type(raw_config).__name__}"
        )

    specs = STRATEGY_PARAMETER_SPECS.get(strategy_name)
    if not specs:
        return dict(raw_config), []

    spec_by_name = {spec.canonical_name: spec for spec in specs}
    alias_map: dict[str, str] = {}
    for spec in specs:
        for alias in spec.aliases:
            alias_map[alias] = spec.canonical_name

    normalized: dict[str, Any] = {}
    unknown_keys: list[str] = []
    sources: dict[str, str] = {}

    for key, value in raw_config.items():
        if key in spec_by_name:
            canonical = key
        elif key in alias_map:
            canonical = alias_map[key]
        else:
            unknown_keys.append(key)
            continue

        if canonical in normalized:
            prior_key = sources[canonical]
            raise ValueError(
                f"Conflicting parameters: strategy={strategy_name} key={canonical} "
                f"provided_by={prior_key},{key}"
            )

        normalized_value = _normalize_value(strategy_name, spec_by_name[canonical], value)
        normalized[canonical] = normalized_value
        sources[canonical] = key

    return normalized, sorted(unknown_keys)

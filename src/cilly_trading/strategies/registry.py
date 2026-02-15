"""Deterministic central strategy registry.

This module is the only supported strategy loading mechanism. Strategies are
registered explicitly via :func:`register_strategy` and resolved via
:func:`create_strategy` / :func:`get_registered_strategies`.

Deterministic ordering rule:
    Registered strategies are returned sorted by stable strategy key.

Out of scope by design:
    - dynamic plugin loading
    - reflection/module auto-discovery
    - external strategy packages
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cilly_trading.engine.core import BaseStrategy
from cilly_trading.strategies.validation import validate_before_registration, validate_strategy_key


class DuplicateStrategyRegistrationError(ValueError):
    """Raised when a strategy key is registered more than once."""


class StrategyNotRegisteredError(KeyError):
    """Raised when an unknown strategy key is requested."""


StrategyFactory = Callable[[], BaseStrategy]


@dataclass(frozen=True)
class RegisteredStrategy:
    """Registry entry for one strategy.

    Attributes:
        key: Stable strategy key (uppercase).
        factory: Zero-argument factory creating a strategy instance.
    """

    key: str
    factory: StrategyFactory


_REGISTRY: dict[str, StrategyFactory] = {}


def _normalize_key(strategy_key: str) -> str:
    return validate_strategy_key(strategy_key)


def register_strategy(
    strategy_key: str,
    factory: StrategyFactory,
    metadata: dict | None = None,
) -> None:
    """Register one strategy factory explicitly.

    Args:
        strategy_key: Stable strategy identifier.
        factory: Factory that returns a strategy instance.

    Raises:
        ValueError: If key/factory/metadata are invalid.
    """

    normalized_key, _ = validate_before_registration(
        strategy_key,
        factory,
        metadata,
        registry_keys=set(_REGISTRY.keys()),
    )

    _REGISTRY[normalized_key] = factory


def get_registered_strategies() -> list[RegisteredStrategy]:
    """Return registered strategies in deterministic order.

    Determinism is guaranteed by sorting by strategy key before returning.

    Returns:
        List of registered strategies sorted by key.
    """

    return [
        RegisteredStrategy(key=key, factory=_REGISTRY[key]) for key in sorted(_REGISTRY.keys())
    ]


def create_strategy(strategy_key: str) -> BaseStrategy:
    """Create a strategy instance for a registered key."""

    normalized_key = _normalize_key(strategy_key)
    factory = _REGISTRY.get(normalized_key)
    if factory is None:
        raise StrategyNotRegisteredError(f"strategy not registered: {normalized_key}")
    return factory()


def create_registered_strategies() -> list[BaseStrategy]:
    """Create all registered strategies in deterministic order."""

    return [entry.factory() for entry in get_registered_strategies()]


def reset_registry() -> None:
    """Reset registry state.

    Intended for unit tests only.
    """

    _REGISTRY.clear()


def initialize_default_registry() -> None:
    """Initialize built-in strategy registrations exactly once."""

    if _REGISTRY:
        return

    from cilly_trading.strategies.rsi2 import Rsi2Strategy
    from cilly_trading.strategies.turtle import TurtleStrategy

    register_strategy(
        "RSI2",
        lambda: Rsi2Strategy(),
        metadata={
            "pack_id": "core-default",
            "version": "1.0.0",
            "deterministic_hash": "rsi2-default-pack-hash",
            "dependencies": [],
        },
    )
    register_strategy(
        "TURTLE",
        lambda: TurtleStrategy(),
        metadata={
            "pack_id": "core-default",
            "version": "1.0.0",
            "deterministic_hash": "turtle-default-pack-hash",
            "dependencies": [],
        },
    )


def run_registry_smoke() -> list[str]:
    """Return deterministic registered strategy keys for smoke tests."""

    initialize_default_registry()
    return [entry.key for entry in get_registered_strategies()]

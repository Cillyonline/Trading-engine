from __future__ import annotations

import pytest

from cilly_trading.strategies.registry import (
    DuplicateStrategyRegistrationError,
    create_registered_strategies,
    create_strategy,
    get_registered_strategies,
    initialize_default_registry,
    register_strategy,
    reset_registry,
    run_registry_smoke,
)


class _StrategyA:
    name = "A"

    def generate_signals(self, df, config):
        return []


class _StrategyB:
    name = "B"

    def generate_signals(self, df, config):
        return []


def setup_function() -> None:
    reset_registry()


def test_registration_succeeds() -> None:
    register_strategy("alpha", _StrategyA)

    strategy = create_strategy("ALPHA")

    assert strategy.name == "A"


def test_duplicate_registration_raises_specific_error() -> None:
    register_strategy("alpha", _StrategyA)

    with pytest.raises(
        DuplicateStrategyRegistrationError,
        match="strategy already registered: ALPHA",
    ):
        register_strategy("ALPHA", _StrategyB)


def test_registered_strategies_are_returned_in_stable_sorted_order() -> None:
    register_strategy("zeta", _StrategyA)
    register_strategy("beta", _StrategyB)

    keys = [entry.key for entry in get_registered_strategies()]

    assert keys == ["BETA", "ZETA"]


def test_smoke_run_is_deterministic_and_uses_registry_only() -> None:
    first = run_registry_smoke()
    second = run_registry_smoke()

    assert first == ["RSI2", "TURTLE"]
    assert second == ["RSI2", "TURTLE"]

    strategy_names = [strategy.name for strategy in create_registered_strategies()]
    assert strategy_names == ["RSI2", "TURTLE"]


def test_initialize_default_registry_idempotent() -> None:
    initialize_default_registry()
    initialize_default_registry()

    assert [entry.key for entry in get_registered_strategies()] == ["RSI2", "TURTLE"]

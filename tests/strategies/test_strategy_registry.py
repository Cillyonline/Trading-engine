from __future__ import annotations

import pytest

from cilly_trading.strategies.registry import (
    create_registered_strategies,
    create_strategy,
    get_registered_strategies,
    initialize_default_registry,
    register_strategy,
    reset_registry,
    run_registry_smoke,
)
from cilly_trading.strategies.validation import StrategyValidationError


class _StrategyA:
    name = "A"

    def generate_signals(self, df, config):
        return []


class _StrategyB:
    name = "B"

    def generate_signals(self, df, config):
        return []


def _metadata(pack_id: str) -> dict:
    return {
        "pack_id": pack_id,
        "version": "1.0.0",
        "deterministic_hash": f"{pack_id}-hash",
        "dependencies": [],
    }


def setup_function() -> None:
    reset_registry()


def test_registration_succeeds() -> None:
    register_strategy("alpha", _StrategyA, metadata=_metadata("pack-a"))

    strategy = create_strategy("ALPHA")

    assert strategy.name == "A"


def test_duplicate_registration_raises_specific_error() -> None:
    register_strategy("alpha", _StrategyA, metadata=_metadata("pack-a"))

    with pytest.raises(
        StrategyValidationError,
        match="strategy already registered: ALPHA",
    ):
        register_strategy("ALPHA", _StrategyB, metadata=_metadata("pack-b"))


def test_registered_strategies_are_returned_in_stable_sorted_order() -> None:
    register_strategy("zeta", _StrategyA, metadata=_metadata("pack-z"))
    register_strategy("beta", _StrategyB, metadata=_metadata("pack-b"))

    keys = [entry.key for entry in get_registered_strategies()]

    assert keys == ["BETA", "ZETA"]


def test_smoke_run_is_deterministic_and_uses_registry_only() -> None:
    first = run_registry_smoke()
    second = run_registry_smoke()

    assert first == ["REFERENCE", "RSI2", "TURTLE"]
    assert second == ["REFERENCE", "RSI2", "TURTLE"]

    strategy_names = [strategy.name for strategy in create_registered_strategies()]
    assert strategy_names == ["REFERENCE", "RSI2", "TURTLE"]


def test_initialize_default_registry_idempotent() -> None:
    initialize_default_registry()
    initialize_default_registry()

    assert [entry.key for entry in get_registered_strategies()] == ["REFERENCE", "RSI2", "TURTLE"]

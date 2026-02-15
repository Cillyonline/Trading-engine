from __future__ import annotations

import pytest

from cilly_trading.strategies.registry import (
    get_registered_strategies,
    register_strategy,
    reset_registry,
    run_registry_smoke,
)
from cilly_trading.strategies.validation import StrategyValidationError


class _ValidStrategy:
    name = "VALID"

    def generate_signals(self, df, config):
        return []


class _InvalidStrategy:
    pass


def _metadata(**overrides):
    payload = {
        "pack_id": "pack-alpha",
        "version": "1.2.3",
        "deterministic_hash": "abc123",
        "dependencies": [],
    }
    payload.update(overrides)
    return payload


def setup_function() -> None:
    reset_registry()


def test_missing_metadata_fields_raises_strategy_validation_error() -> None:
    with pytest.raises(
        StrategyValidationError,
        match="metadata missing required fields: deterministic_hash",
    ):
        register_strategy(
            "alpha",
            _ValidStrategy,
            metadata={"pack_id": "pack-alpha", "version": "1.2.3", "dependencies": []},
        )


def test_invalid_semver_raises_strategy_validation_error() -> None:
    with pytest.raises(
        StrategyValidationError,
        match="metadata field 'version' must be valid semver",
    ):
        register_strategy("alpha", _ValidStrategy, metadata=_metadata(version="1.2"))


def test_non_callable_factory_raises_strategy_validation_error() -> None:
    with pytest.raises(StrategyValidationError, match="factory must be callable"):
        register_strategy("alpha", "not-callable", metadata=_metadata())


def test_factory_returning_wrong_type_raises_strategy_validation_error() -> None:
    with pytest.raises(
        StrategyValidationError,
        match="factory must return an instance of BaseStrategy",
    ):
        register_strategy("alpha", _InvalidStrategy, metadata=_metadata())


def test_duplicate_registration_raises_validation_error() -> None:
    register_strategy("alpha", _ValidStrategy, metadata=_metadata())

    with pytest.raises(StrategyValidationError, match="strategy already registered: ALPHA"):
        register_strategy("ALPHA", _ValidStrategy, metadata=_metadata())


def test_successful_registration_passes_validation() -> None:
    register_strategy("alpha", _ValidStrategy, metadata=_metadata())

    assert [entry.key for entry in get_registered_strategies()] == ["ALPHA"]


def test_validation_preserves_registry_ordering_and_smoke_stability() -> None:
    register_strategy("zeta", _ValidStrategy, metadata=_metadata(pack_id="pack-z"))
    register_strategy("beta", _ValidStrategy, metadata=_metadata(pack_id="pack-b"))

    assert [entry.key for entry in get_registered_strategies()] == ["BETA", "ZETA"]
    assert run_registry_smoke() == ["BETA", "ZETA"]

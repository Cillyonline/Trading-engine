from __future__ import annotations

import pytest

from cilly_trading.engine.strategy_lifecycle import StrategyLifecycleState, TERMINAL_STATES, is_terminal_state


def test_strategy_lifecycle_state_values_are_canonical() -> None:
    assert StrategyLifecycleState.DRAFT.value == "DRAFT"
    assert StrategyLifecycleState.EVALUATION.value == "EVALUATION"
    assert StrategyLifecycleState.PRODUCTION.value == "PRODUCTION"
    assert StrategyLifecycleState.DEPRECATED.value == "DEPRECATED"


def test_terminal_state_definition_is_deterministic() -> None:
    assert TERMINAL_STATES == frozenset({StrategyLifecycleState.DEPRECATED})
    assert is_terminal_state(StrategyLifecycleState.DEPRECATED)
    assert not is_terminal_state(StrategyLifecycleState.DRAFT)
    assert not is_terminal_state(StrategyLifecycleState.EVALUATION)
    assert not is_terminal_state(StrategyLifecycleState.PRODUCTION)


def test_state_representation_is_immutable() -> None:
    with pytest.raises(AttributeError):
        StrategyLifecycleState.DRAFT.value = "OTHER"  # type: ignore[misc]

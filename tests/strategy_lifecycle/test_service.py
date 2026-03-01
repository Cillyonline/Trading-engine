from __future__ import annotations

import pytest

from cilly_trading.engine.strategy_lifecycle import (
    StrategyLifecycleState,
    StrategyLifecycleTransitionError,
    deprecate,
    promote_to_evaluation,
    promote_to_production,
)


@pytest.mark.parametrize(
    ("operation", "current", "expected"),
    [
        (promote_to_evaluation, StrategyLifecycleState.DRAFT, StrategyLifecycleState.EVALUATION),
        (promote_to_production, StrategyLifecycleState.EVALUATION, StrategyLifecycleState.PRODUCTION),
        (deprecate, StrategyLifecycleState.DRAFT, StrategyLifecycleState.DEPRECATED),
        (deprecate, StrategyLifecycleState.EVALUATION, StrategyLifecycleState.DEPRECATED),
        (deprecate, StrategyLifecycleState.PRODUCTION, StrategyLifecycleState.DEPRECATED),
    ],
)
def test_promotion_service_valid_transitions(operation, current: StrategyLifecycleState, expected: StrategyLifecycleState) -> None:
    assert operation(current) == expected


@pytest.mark.parametrize(
    ("operation", "current", "expected_error"),
    [
        (
            promote_to_evaluation,
            StrategyLifecycleState.EVALUATION,
            "Illegal lifecycle transition: EVALUATION -> EVALUATION",
        ),
        (
            promote_to_production,
            StrategyLifecycleState.PRODUCTION,
            "Illegal lifecycle transition: PRODUCTION -> PRODUCTION",
        ),
        (
            promote_to_evaluation,
            StrategyLifecycleState.DEPRECATED,
            "Illegal lifecycle transition: DEPRECATED is terminal",
        ),
        (
            promote_to_production,
            StrategyLifecycleState.DRAFT,
            "Illegal lifecycle transition: DRAFT -> PRODUCTION",
        ),
    ],
)
def test_promotion_service_invalid_transitions_raise_deterministic_errors(
    operation,
    current: StrategyLifecycleState,
    expected_error: str,
) -> None:
    with pytest.raises(StrategyLifecycleTransitionError) as error:
        operation(current)

    assert str(error.value) == expected_error


@pytest.mark.parametrize(
    ("operation", "current"),
    [
        (promote_to_evaluation, StrategyLifecycleState.DRAFT),
        (promote_to_production, StrategyLifecycleState.EVALUATION),
        (deprecate, StrategyLifecycleState.PRODUCTION),
    ],
)
def test_promotion_service_deterministic_success(operation, current: StrategyLifecycleState) -> None:
    assert operation(current) == operation(current)


@pytest.mark.parametrize(
    ("operation", "current", "expected_error"),
    [
        (
            promote_to_evaluation,
            StrategyLifecycleState.DEPRECATED,
            "Illegal lifecycle transition: DEPRECATED is terminal",
        ),
        (
            promote_to_production,
            StrategyLifecycleState.DRAFT,
            "Illegal lifecycle transition: DRAFT -> PRODUCTION",
        ),
    ],
)
def test_promotion_service_deterministic_errors(operation, current: StrategyLifecycleState, expected_error: str) -> None:
    errors: list[str] = []

    for _ in range(2):
        with pytest.raises(StrategyLifecycleTransitionError) as error:
            operation(current)
        errors.append(str(error.value))

    assert errors == [expected_error, expected_error]

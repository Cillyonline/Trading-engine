from __future__ import annotations

import itertools

import pytest

from cilly_trading.engine.strategy_lifecycle import (
    ALLOWED_TRANSITIONS,
    StrategyLifecycleState,
    StrategyLifecycleTransitionError,
    get_allowed_transitions,
    transition_state,
    validate_transition,
)


VALID_TRANSITIONS = {
    (StrategyLifecycleState.DRAFT, StrategyLifecycleState.EVALUATION),
    (StrategyLifecycleState.EVALUATION, StrategyLifecycleState.PRODUCTION),
    (StrategyLifecycleState.PRODUCTION, StrategyLifecycleState.DEPRECATED),
    (StrategyLifecycleState.EVALUATION, StrategyLifecycleState.DEPRECATED),
    (StrategyLifecycleState.DRAFT, StrategyLifecycleState.DEPRECATED),
}


@pytest.mark.parametrize(("current", "target"), sorted(VALID_TRANSITIONS, key=lambda t: (t[0].value, t[1].value)))
def test_valid_transitions_succeed(current: StrategyLifecycleState, target: StrategyLifecycleState) -> None:
    validate_transition(current_state=current, target_state=target)
    assert transition_state(current_state=current, target_state=target) == target


def test_all_invalid_transitions_fail_deterministically() -> None:
    all_pairs = set(itertools.product(StrategyLifecycleState, repeat=2))
    invalid_pairs = sorted(all_pairs - VALID_TRANSITIONS, key=lambda t: (t[0].value, t[1].value))

    for current, target in invalid_pairs:
        with pytest.raises(StrategyLifecycleTransitionError) as error:
            validate_transition(current_state=current, target_state=target)

        if current == target:
            assert str(error.value) == f"Illegal lifecycle transition: {current.value} -> {target.value}"
        elif current == StrategyLifecycleState.DEPRECATED:
            assert str(error.value) == f"Illegal lifecycle transition: {current.value} is terminal"
        else:
            assert str(error.value) == f"Illegal lifecycle transition: {current.value} -> {target.value}"


def test_explicit_transition_matrix_matches_specification() -> None:
    assert get_allowed_transitions(StrategyLifecycleState.DRAFT) == frozenset(
        {StrategyLifecycleState.EVALUATION, StrategyLifecycleState.DEPRECATED}
    )
    assert get_allowed_transitions(StrategyLifecycleState.EVALUATION) == frozenset(
        {StrategyLifecycleState.PRODUCTION, StrategyLifecycleState.DEPRECATED}
    )
    assert get_allowed_transitions(StrategyLifecycleState.PRODUCTION) == frozenset(
        {StrategyLifecycleState.DEPRECATED}
    )
    assert get_allowed_transitions(StrategyLifecycleState.DEPRECATED) == frozenset()


def test_transition_matrix_is_immutable() -> None:
    with pytest.raises(TypeError):
        ALLOWED_TRANSITIONS[StrategyLifecycleState.DRAFT] = frozenset()  # type: ignore[index]

    with pytest.raises(AttributeError):
        get_allowed_transitions(StrategyLifecycleState.DRAFT).add(StrategyLifecycleState.PRODUCTION)  # type: ignore[attr-defined]

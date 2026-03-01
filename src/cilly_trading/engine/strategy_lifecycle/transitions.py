"""Deterministic transition rules for the strategy lifecycle model."""

from __future__ import annotations

from types import MappingProxyType

from .model import StrategyLifecycleState, is_terminal_state


class StrategyLifecycleTransitionError(ValueError):
    """Raised when a lifecycle transition is not explicitly allowed."""


_ALLOWED_TRANSITIONS_MUTABLE: dict[StrategyLifecycleState, frozenset[StrategyLifecycleState]] = {
    StrategyLifecycleState.DRAFT: frozenset(
        {
            StrategyLifecycleState.EVALUATION,
            StrategyLifecycleState.DEPRECATED,
        }
    ),
    StrategyLifecycleState.EVALUATION: frozenset(
        {
            StrategyLifecycleState.PRODUCTION,
            StrategyLifecycleState.DEPRECATED,
        }
    ),
    StrategyLifecycleState.PRODUCTION: frozenset({StrategyLifecycleState.DEPRECATED}),
    StrategyLifecycleState.DEPRECATED: frozenset(),
}

ALLOWED_TRANSITIONS = MappingProxyType(_ALLOWED_TRANSITIONS_MUTABLE)


def get_allowed_transitions(state: StrategyLifecycleState) -> frozenset[StrategyLifecycleState]:
    """Return the explicit set of allowed outbound transitions for a state."""

    return ALLOWED_TRANSITIONS[state]


def validate_transition(
    current_state: StrategyLifecycleState,
    target_state: StrategyLifecycleState,
) -> None:
    """Validate one lifecycle transition.

    Raises:
        StrategyLifecycleTransitionError: If the transition is not explicitly allowed.
    """

    if current_state == target_state:
        raise StrategyLifecycleTransitionError(
            f"Illegal lifecycle transition: {current_state.value} -> {target_state.value}"
        )

    allowed_targets = get_allowed_transitions(current_state)
    if target_state in allowed_targets:
        return

    if is_terminal_state(current_state):
        raise StrategyLifecycleTransitionError(
            f"Illegal lifecycle transition: {current_state.value} is terminal"
        )

    raise StrategyLifecycleTransitionError(
        f"Illegal lifecycle transition: {current_state.value} -> {target_state.value}"
    )


def transition_state(
    current_state: StrategyLifecycleState,
    target_state: StrategyLifecycleState,
) -> StrategyLifecycleState:
    """Validate and return the deterministic next state."""

    validate_transition(current_state=current_state, target_state=target_state)
    return target_state

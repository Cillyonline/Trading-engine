"""Promotion service API for deterministic strategy lifecycle transitions."""

from __future__ import annotations

from typing import Protocol

from .model import StrategyLifecycleState
from .transitions import transition_state


class StrategyLifecycleStore(Protocol):
    """Persistence hook interface for strategy lifecycle state access."""

    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        """Return the current lifecycle state for a strategy identifier."""

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        """Persist a lifecycle state for a strategy identifier."""


def promote_to_evaluation(current_state: StrategyLifecycleState) -> StrategyLifecycleState:
    """Promote a strategy into EVALUATION when transition rules allow it."""

    return transition_state(
        current_state=current_state,
        target_state=StrategyLifecycleState.EVALUATION,
    )


def promote_to_production(current_state: StrategyLifecycleState) -> StrategyLifecycleState:
    """Promote a strategy into PRODUCTION when transition rules allow it."""

    return transition_state(
        current_state=current_state,
        target_state=StrategyLifecycleState.PRODUCTION,
    )


def deprecate(current_state: StrategyLifecycleState) -> StrategyLifecycleState:
    """Transition a strategy into DEPRECATED when transition rules allow it."""

    return transition_state(
        current_state=current_state,
        target_state=StrategyLifecycleState.DEPRECATED,
    )

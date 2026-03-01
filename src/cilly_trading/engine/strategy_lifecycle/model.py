"""Strategy lifecycle state model definitions."""

from __future__ import annotations

from enum import Enum


class StrategyLifecycleState(str, Enum):
    """Canonical lifecycle states for a strategy."""

    DRAFT = "DRAFT"
    EVALUATION = "EVALUATION"
    PRODUCTION = "PRODUCTION"
    DEPRECATED = "DEPRECATED"


TERMINAL_STATES: frozenset[StrategyLifecycleState] = frozenset(
    {StrategyLifecycleState.DEPRECATED}
)


def is_terminal_state(state: StrategyLifecycleState) -> bool:
    """Return True when the state is terminal and cannot transition further."""

    return state in TERMINAL_STATES

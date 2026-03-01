"""Public API for strategy lifecycle modeling and transition validation."""

from .model import StrategyLifecycleState, TERMINAL_STATES, is_terminal_state
from .transitions import (
    ALLOWED_TRANSITIONS,
    StrategyLifecycleTransitionError,
    get_allowed_transitions,
    transition_state,
    validate_transition,
)

__all__ = [
    "ALLOWED_TRANSITIONS",
    "StrategyLifecycleState",
    "StrategyLifecycleTransitionError",
    "TERMINAL_STATES",
    "get_allowed_transitions",
    "is_terminal_state",
    "transition_state",
    "validate_transition",
]

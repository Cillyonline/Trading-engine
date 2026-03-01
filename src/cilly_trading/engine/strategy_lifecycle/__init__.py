"""Public API for strategy lifecycle modeling and transition validation."""

from .model import StrategyLifecycleState, TERMINAL_STATES, is_terminal_state
from .service import StrategyLifecycleStore, deprecate, promote_to_evaluation, promote_to_production
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
    "StrategyLifecycleStore",
    "StrategyLifecycleTransitionError",
    "TERMINAL_STATES",
    "deprecate",
    "get_allowed_transitions",
    "is_terminal_state",
    "promote_to_evaluation",
    "promote_to_production",
    "transition_state",
    "validate_transition",
]

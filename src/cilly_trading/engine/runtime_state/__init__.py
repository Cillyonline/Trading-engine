"""Runtime state read model for operator-facing API endpoints."""

from .system_state import SystemStatePayload, get_system_state_payload

__all__ = ("SystemStatePayload", "get_system_state_payload")

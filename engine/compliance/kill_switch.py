"""Deterministic global kill switch state utilities."""

from __future__ import annotations


_KILL_SWITCH_KEY = "execution.kill_switch.active"


def is_kill_switch_active(*, config: dict[str, object] | None = None) -> bool:
    """Return deterministic global kill switch state.

    Args:
        config: Optional in-process configuration dictionary.

    Returns:
        bool: True only when the explicit kill-switch key is set to ``True``.
    """

    if config is None:
        return False

    return config.get(_KILL_SWITCH_KEY) is True

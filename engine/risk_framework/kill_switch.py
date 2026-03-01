"""Kill switch utilities for global risk controls."""

from __future__ import annotations


def is_kill_switch_enabled(*, config: dict[str, object] | None) -> bool:
    """Return whether the global risk kill switch is enabled."""
    if config is None:
        return False

    enabled = config.get("risk.kill_switch.enabled")
    return enabled is True

"""Deterministic emergency execution block guard utilities."""

from __future__ import annotations


_EMERGENCY_BLOCK_KEY = "execution.emergency_block.active"


def is_emergency_block_active(*, config: dict[str, object] | None = None) -> bool:
    """Return deterministic emergency block state.

    Args:
        config: Optional in-process configuration dictionary.

    Returns:
        bool: True only when the explicit emergency-block key is set to ``True``.
    """

    if config is None:
        return False

    return config.get(_EMERGENCY_BLOCK_KEY) is True

"""Determinism guard for backtest validation."""

from __future__ import annotations

import datetime
import random
import secrets
import socket
import time
from typing import Any, Callable


__all__ = [
    "DeterminismViolationError",
    "install_guard",
    "uninstall_guard",
]


class DeterminismViolationError(RuntimeError):
    """Raised when a forbidden non-deterministic API is accessed."""


_ORIGINALS: dict[tuple[Any, str], Any] = {}
_INSTALLED = False


def _raise_violation(message: str) -> None:
    raise DeterminismViolationError(message)


def _blocked_callable(message: str) -> Callable[..., Any]:
    def _blocked(*_args: Any, **_kwargs: Any) -> Any:
        _raise_violation(message)

    return _blocked


def _patch(target: Any, attr: str, replacement: Any) -> None:
    key = (target, attr)
    if key in _ORIGINALS:
        return
    _ORIGINALS[key] = getattr(target, attr)
    setattr(target, attr, replacement)


def install_guard() -> None:
    """Install deterministic validation guard by monkeypatching forbidden APIs."""

    global _INSTALLED
    if _INSTALLED:
        return

    # System time access.
    _patch(time, "time", _blocked_callable("Determinism violation: system time access (time.time)"))
    _patch(time, "time_ns", _blocked_callable("Determinism violation: system time access (time.time_ns)"))

    class _DeterministicDatetime(datetime.datetime):
        @classmethod
        def now(cls, tz: datetime.tzinfo | None = None) -> datetime.datetime:
            _raise_violation("Determinism violation: system time access (datetime.datetime.now)")

        @classmethod
        def utcnow(cls) -> datetime.datetime:
            _raise_violation("Determinism violation: system time access (datetime.datetime.utcnow)")

    _patch(datetime, "datetime", _DeterministicDatetime)

    # Randomness access.
    _patch(random, "random", _blocked_callable("Determinism violation: randomness access (random.random)"))
    _patch(random, "randint", _blocked_callable("Determinism violation: randomness access (random.randint)"))
    _patch(random, "choice", _blocked_callable("Determinism violation: randomness access (random.choice)"))
    _patch(random, "randrange", _blocked_callable("Determinism violation: randomness access (random.randrange)"))
    _patch(secrets, "token_bytes", _blocked_callable("Determinism violation: randomness access (secrets.token_bytes)"))
    _patch(secrets, "token_hex", _blocked_callable("Determinism violation: randomness access (secrets.token_hex)"))
    _patch(secrets, "choice", _blocked_callable("Determinism violation: randomness access (secrets.choice)"))

    # Network access.
    _patch(socket.socket, "connect", _blocked_callable("Determinism violation: network access (socket.socket.connect)"))
    _patch(socket, "create_connection", _blocked_callable("Determinism violation: network access (socket.create_connection)"))
    _patch(socket, "getaddrinfo", _blocked_callable("Determinism violation: network access (socket.getaddrinfo)"))

    _INSTALLED = True


def uninstall_guard() -> None:
    """Restore all patched callables and remove the deterministic guard."""

    global _INSTALLED
    if not _INSTALLED and not _ORIGINALS:
        return

    for (target, attr), original in reversed(list(_ORIGINALS.items())):
        setattr(target, attr, original)

    _ORIGINALS.clear()
    _INSTALLED = False


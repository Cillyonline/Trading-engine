"""Determinism guard utilities for offline analysis runs."""

from __future__ import annotations

from contextlib import AbstractContextManager
import datetime as datetime_module
import os
import secrets
import socket
import time
import types
import urllib.request
import uuid
from typing import Any, Callable, Dict, List, Tuple


class DeterminismViolationError(RuntimeError):
    """Raised when a non-deterministic operation is attempted."""


def _raise_violation(action: str) -> None:
    raise DeterminismViolationError(f"determinism_guard_violation:{action}")


def _blocked_callable(action: str) -> Callable[..., Any]:
    def _blocked(*_args: Any, **_kwargs: Any) -> Any:
        _raise_violation(action)

    return _blocked


class _PatchedDatetime(datetime_module.datetime):
    @classmethod
    def now(cls, tz: datetime_module.tzinfo | None = None) -> datetime_module.datetime:
        _raise_violation("time.now")

    @classmethod
    def utcnow(cls) -> datetime_module.datetime:
        _raise_violation("time.utcnow")

    @classmethod
    def today(cls) -> datetime_module.datetime:
        _raise_violation("time.today")


class DeterminismGuard(AbstractContextManager["DeterminismGuard"]):
    """Context manager that blocks time, randomness, and network usage."""

    def __init__(self) -> None:
        self._patches: List[Tuple[Any, str, Any]] = []

    def _patch(self, target: Any, attr: str, replacement: Any) -> None:
        original = getattr(target, attr)
        self._patches.append((target, attr, original))
        setattr(target, attr, replacement)

    def _patch_module_datetime(self, module: types.ModuleType) -> None:
        if hasattr(module, "datetime"):
            self._patch(module, "datetime", _PatchedDatetime)

    def _patch_time(self) -> None:
        self._patch(time, "time", _blocked_callable("time.time"))
        self._patch(time, "time_ns", _blocked_callable("time.time_ns"))
        self._patch(time, "monotonic", _blocked_callable("time.monotonic"))
        self._patch(time, "perf_counter", _blocked_callable("time.perf_counter"))

    def _patch_random(self) -> None:
        import random

        self._patch(random, "random", _blocked_callable("random.random"))
        self._patch(random, "randrange", _blocked_callable("random.randrange"))
        self._patch(random, "randint", _blocked_callable("random.randint"))
        self._patch(random, "choice", _blocked_callable("random.choice"))
        self._patch(random, "shuffle", _blocked_callable("random.shuffle"))
        self._patch(random, "uniform", _blocked_callable("random.uniform"))
        self._patch(random, "gauss", _blocked_callable("random.gauss"))
        self._patch(uuid, "uuid4", _blocked_callable("uuid.uuid4"))

        try:
            import numpy as np
        except Exception:
            return

        self._patch(np.random, "random", _blocked_callable("numpy.random.random"))
        self._patch(np.random, "rand", _blocked_callable("numpy.random.rand"))
        self._patch(np.random, "randint", _blocked_callable("numpy.random.randint"))
        self._patch(np.random, "normal", _blocked_callable("numpy.random.normal"))
        self._patch(np.random, "default_rng", _blocked_callable("numpy.random.default_rng"))

    def _patch_os_secrets(self) -> None:
        self._patch(os, "urandom", _blocked_callable("os.urandom"))
        self._patch(secrets, "token_bytes", _blocked_callable("secrets.token_bytes"))
        self._patch(secrets, "token_hex", _blocked_callable("secrets.token_hex"))
        self._patch(secrets, "token_urlsafe", _blocked_callable("secrets.token_urlsafe"))
        self._patch(secrets, "choice", _blocked_callable("secrets.choice"))

    def _patch_network(self) -> None:
        self._patch(socket, "socket", _blocked_callable("socket.socket"))
        self._patch(socket, "create_connection", _blocked_callable("socket.create_connection"))
        self._patch(
            urllib.request,
            "urlopen",
            _blocked_callable("urllib.request.urlopen"),
        )

        try:
            import requests
        except Exception:
            requests = None
        if requests is not None:
            self._patch(
                requests.sessions.Session,
                "request",
                _blocked_callable("requests.request"),
            )

        try:
            import httpx
        except Exception:
            httpx = None
        if httpx is not None:
            self._patch(httpx.Client, "request", _blocked_callable("httpx.Client.request"))
            self._patch(
                httpx.AsyncClient,
                "request",
                _blocked_callable("httpx.AsyncClient.request"),
            )

    def __enter__(self) -> "DeterminismGuard":
        from cilly_trading.engine import core as engine_core
        from cilly_trading.engine import data as engine_data

        self._patch_time()
        self._patch_random()
        self._patch_os_secrets()
        self._patch_network()
        self._patch_module_datetime(engine_core)
        self._patch_module_datetime(engine_data)
        self._patch_module_datetime(datetime_module)
        return self

    def __exit__(self, exc_type, exc, tb) -> bool:
        for target, attr, original in reversed(self._patches):
            setattr(target, attr, original)
        self._patches.clear()
        return False


def determinism_guard() -> DeterminismGuard:
    """Return a determinism guard context manager."""
    return DeterminismGuard()

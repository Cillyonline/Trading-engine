from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable, Optional

from fastapi import FastAPI

from ..middleware import DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S, InFlightRequestTracker


@dataclass
class RuntimeLifecycleDependencies:
    logger: logging.Logger
    start_runtime: Callable[[], str]
    shutdown_runtime: Callable[[], str]
    start_scheduled_analysis_runner: Callable[[], str]
    shutdown_scheduled_analysis_runner: Callable[[], str]
    set_runtime_guard_active: Callable[[bool], None]
    lifecycle_transition_error: type[Exception]


def _resolve_drain_timeout() -> float:
    raw = os.getenv("CILLY_SHUTDOWN_DRAIN_TIMEOUT_S")
    if raw is None:
        return DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S
    try:
        value = float(raw)
    except (TypeError, ValueError):
        return DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S
    if value <= 0:
        return DEFAULT_SHUTDOWN_DRAIN_TIMEOUT_S
    return value


def register_runtime_lifecycle(
    *,
    app: FastAPI,
    deps: RuntimeLifecycleDependencies,
) -> tuple[Callable[[], None], Callable[[], None]]:
    def _startup_runtime() -> None:
        deps.start_runtime()
        deps.set_runtime_guard_active(True)
        deps.start_scheduled_analysis_runner()

    def _shutdown_runtime() -> None:
        deps.shutdown_scheduled_analysis_runner()
        deps.set_runtime_guard_active(False)
        try:
            deps.shutdown_runtime()
        except deps.lifecycle_transition_error:
            deps.logger.exception("Engine runtime shutdown failed")

    async def _drain_inflight_requests() -> None:
        # Signal "shutting down" via app.state so the middleware can
        # reject new traffic while we wait for in-flight requests. We
        # always reset the flag at the end so subsequent test harnesses
        # constructing a fresh ``TestClient`` without re-entering the
        # lifespan don't inherit a stale shutdown state.
        app.state.shutdown_started = True
        try:
            tracker: Optional[InFlightRequestTracker] = getattr(
                app.state, "inflight_tracker", None
            )
            if tracker is None:
                return
            timeout_s = _resolve_drain_timeout()
            deps.logger.info(
                "graceful_shutdown_drain_started",
                extra={"in_flight": tracker.in_flight, "timeout_s": timeout_s},
            )
            drained = await tracker.drain(timeout_s=timeout_s)
            deps.logger.info(
                "graceful_shutdown_drain_complete",
                extra={"drained": drained, "in_flight": tracker.in_flight},
            )
        finally:
            app.state.shutdown_started = False

    @asynccontextmanager
    async def _runtime_lifespan(_: FastAPI) -> AsyncIterator[None]:
        # Reset the in-flight tracker + shutdown flag on every lifespan
        # entry so that repeated TestClient contexts (and process
        # restarts) start clean even if a previous lifespan already
        # marked the app as shutting down.
        app.state.shutdown_started = False
        tracker: Optional[InFlightRequestTracker] = getattr(
            app.state, "inflight_tracker", None
        )
        if tracker is not None:
            tracker.reset()
        _startup_runtime()
        try:
            yield
        finally:
            # Stop accepting new requests and wait for in-flight ones to
            # finish before tearing down the engine runtime. This prevents
            # SQLite writes mid-request from being abandoned during a
            # SIGTERM-driven rolling update (issue #1133).
            await _drain_inflight_requests()
            _shutdown_runtime()

    app.router.lifespan_context = _runtime_lifespan

    return _startup_runtime, _shutdown_runtime

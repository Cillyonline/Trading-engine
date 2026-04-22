from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import AsyncIterator, Callable

from fastapi import FastAPI


@dataclass
class RuntimeLifecycleDependencies:
    logger: logging.Logger
    start_runtime: Callable[[], str]
    shutdown_runtime: Callable[[], str]
    start_scheduled_analysis_runner: Callable[[], str]
    shutdown_scheduled_analysis_runner: Callable[[], str]
    set_runtime_guard_active: Callable[[bool], None]
    lifecycle_transition_error: type[Exception]


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

    @asynccontextmanager
    async def _runtime_lifespan(_: FastAPI) -> AsyncIterator[None]:
        _startup_runtime()
        try:
            yield
        finally:
            _shutdown_runtime()

    app.router.lifespan_context = _runtime_lifespan

    return _startup_runtime, _shutdown_runtime

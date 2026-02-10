from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from time import sleep

from cilly_trading.engine.observability_extensions import (
    ObservabilityContext,
    RuntimeObservabilityRegistry,
)


def _context() -> ObservabilityContext:
    now = datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc)
    return ObservabilityContext(
        runtime_id="runtime-1",
        mode="running",
        started_at=now - timedelta(minutes=10),
        updated_at=now,
        now=now,
    )


def test_extension_points_return_dto_only_payloads() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "status",
        name="status_dto",
        extension=lambda context: {
            "runtime_id": context.runtime_id,
            "mode": context.mode,
            "uptime_seconds": 600,
        },
    )
    registry.register(
        "health",
        name="health_dto",
        extension=lambda context: {
            "level": "healthy",
            "checks": [{"name": "runtime", "status": "ok"}],
        },
    )
    registry.register(
        "introspection",
        name="introspection_dto",
        extension=lambda context: {
            "schema_version": context.schema_version,
            "ownership": {"owner_tag": "engine"},
        },
    )

    status_result = registry.execute("status", context=_context())
    health_result = registry.execute("health", context=_context())
    introspection_result = registry.execute("introspection", context=_context())

    assert status_result.executions[0].error is None
    assert status_result.executions[0].payload["runtime_id"] == "runtime-1"
    assert health_result.executions[0].error is None
    assert health_result.executions[0].payload["level"] == "healthy"
    assert introspection_result.executions[0].error is None
    assert introspection_result.executions[0].payload["schema_version"] == "v1"


def test_observability_context_is_read_only() -> None:
    context = _context()

    try:
        context.mode = "stopped"  # type: ignore[misc]
    except FrozenInstanceError:
        pass
    else:
        raise AssertionError("ObservabilityContext must be immutable")


def test_engine_stability_when_extension_raises() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "health",
        name="boom",
        extension=lambda _context: (_ for _ in ()).throw(RuntimeError("boom")),
    )
    registry.register(
        "health",
        name="safe",
        extension=lambda _context: {"level": "degraded"},
    )

    result = registry.execute("health", context=_context())

    assert len(result.executions) == 2
    assert result.executions[0].error == "extension_failed:RuntimeError"
    assert result.executions[1].error is None
    assert result.executions[1].payload["level"] == "degraded"


def test_budget_is_enforced() -> None:
    registry = RuntimeObservabilityRegistry()

    def slow_extension(_context: ObservabilityContext) -> dict[str, str]:
        sleep(0.02)
        return {"status": "ok"}

    registry.register("status", name="slow", extension=slow_extension)

    result = registry.execute("status", context=_context(), budget_seconds=0.001)

    assert result.executions[0].error is not None
    assert result.executions[0].error.startswith("budget_exceeded:")
    assert result.executions[0].payload == {}

from __future__ import annotations

from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta, timezone
from threading import Event

import pytest

from cilly_trading.engine.observability_extensions import (
    ObservabilityContext,
    RuntimeObservabilityRegistry,
    build_observability_context,
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

    assert status_result.executions[0].error_code is None
    assert status_result.executions[0].error_detail is None
    assert status_result.executions[0].payload["runtime_id"] == "runtime-1"

    assert health_result.executions[0].error_code is None
    assert health_result.executions[0].error_detail is None
    assert health_result.executions[0].payload["level"] == "healthy"

    assert introspection_result.executions[0].error_code is None
    assert introspection_result.executions[0].error_detail is None
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
    assert result.executions[0].error_code == "extension_failed"
    assert result.executions[0].error_detail == "RuntimeError"
    assert result.executions[0].failure_type == "exception"
    assert result.executions[0].failure_count == 1
    assert result.executions[1].error_code is None
    assert result.executions[1].error_detail is None
    assert result.executions[1].payload["level"] == "degraded"
    assert result.executions[1].failure_type == "none"


def test_budget_is_enforced_with_timeout_guard() -> None:
    registry = RuntimeObservabilityRegistry()
    blocker = Event()

    def blocking_extension(_context: ObservabilityContext) -> dict[str, str]:
        blocker.wait(timeout=0.5)
        return {"status": "ok"}

    registry.register("status", name="slow", extension=blocking_extension)

    result = registry.execute("status", context=_context(), budget_seconds=0.001)

    assert result.executions[0].error_code == "budget_exceeded"
    assert result.executions[0].error_detail == "execution_timeout"
    assert result.executions[0].failure_type == "timeout"
    assert result.executions[0].failure_count == 1
    assert result.executions[0].payload == {}


def test_non_serializable_payload_is_rejected_as_invalid_output() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "status",
        name="bad_datetime",
        extension=lambda _context: {"updated_at": datetime.now(timezone.utc)},  # type: ignore[return-value]
    )

    result = registry.execute("status", context=_context())

    assert result.executions[0].payload == {}
    assert result.executions[0].error_code == "extension_failed"
    assert result.executions[0].error_detail == "invalid_output"
    assert result.executions[0].failure_type == "invalid_output"
    assert result.executions[0].failure_count == 1


def test_non_dto_payload_is_rejected_as_invalid_output() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "introspection",
        name="bad_object",
        extension=lambda _context: {"value": object()},  # type: ignore[return-value]
    )

    result = registry.execute("introspection", context=_context())

    assert result.executions[0].payload == {}
    assert result.executions[0].error_code == "extension_failed"
    assert result.executions[0].error_detail == "invalid_output"
    assert result.executions[0].failure_type == "invalid_output"
    assert result.executions[0].failure_count == 1


def test_duplicate_extension_name_rejected() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register("status", name="dup", extension=lambda _context: {"ok": True})

    with pytest.raises(ValueError):
        registry.register("status", name="dup", extension=lambda _context: {"ok": False})


def test_build_observability_context_uses_provided_now() -> None:
    now = datetime(2026, 2, 10, 12, 34, 56, tzinfo=timezone.utc)
    started_at = datetime(2026, 2, 10, 10, 0, 0)

    context = build_observability_context(
        runtime_id="runtime-2",
        mode="running",
        started_at=started_at,
        now=now,
    )

    assert context.runtime_id == "runtime-2"
    assert context.started_at == datetime(2026, 2, 10, 10, 0, 0, tzinfo=timezone.utc)
    assert context.updated_at == now
    assert context.now == now


def test_failure_then_success_resets_execution_failure_count() -> None:
    registry = RuntimeObservabilityRegistry()
    state = {"should_fail": True}

    def flappy(_context: ObservabilityContext) -> dict[str, str]:
        if state["should_fail"]:
            raise RuntimeError("boom")
        return {"status": "ok"}

    registry.register("status", name="flappy", extension=flappy)

    first = registry.execute("status", context=_context())
    assert first.executions[0].failure_type != "none"
    assert first.executions[0].failure_count == 1

    state["should_fail"] = False
    second = registry.execute("status", context=_context())
    assert second.executions[0].failure_type == "none"
    assert second.executions[0].failure_count == 0


def test_failure_snapshot_exposes_last_failure_and_counter() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "status",
        name="unstable",
        extension=lambda _context: (_ for _ in ()).throw(RuntimeError("boom")),
    )

    registry.execute("status", context=_context())
    registry.execute("status", context=_context())

    assert registry.get_extension_failure_snapshot() == {
        "status:unstable": {
            "failure_count": 2,
            "last_failure_type": "exception",
        }
    }


def test_failure_handling_is_deterministic_for_same_inputs() -> None:
    blocker = Event()

    def build_registry() -> RuntimeObservabilityRegistry:
        registry = RuntimeObservabilityRegistry()
        registry.register(
            "status",
            name="exception_case",
            extension=lambda _context: (_ for _ in ()).throw(RuntimeError("boom")),
        )
        registry.register(
            "status",
            name="timeout_case",
            extension=lambda _context: blocker.wait(timeout=0.5) or {"status": "ok"},
        )
        registry.register(
            "status",
            name="invalid_case",
            extension=lambda _context: {"value": object()},  # type: ignore[return-value]
        )
        registry.register(
            "status",
            name="safe_case",
            extension=lambda _context: {"status": "ok"},
        )
        return registry

    first_registry = build_registry()
    first = first_registry.execute("status", context=_context(), budget_seconds=0.001)
    first_snapshot = first_registry.get_extension_failure_snapshot()

    second_registry = build_registry()
    second = second_registry.execute("status", context=_context(), budget_seconds=0.001)
    second_snapshot = second_registry.get_extension_failure_snapshot()

    assert first == second
    assert first_snapshot == second_snapshot


def test_list_extensions_metadata_is_sorted_and_includes_disabled() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register("status", name="zeta", extension=lambda _context: {"ok": True})
    registry.register(
        "health",
        name="alpha",
        extension=lambda _context: {"ok": True},
        enabled=False,
        source="extension",
    )
    registry.register(
        "status",
        name="core.status",
        extension=lambda _context: {"ok": True},
        source="core",
    )

    assert registry.list_extensions_metadata() == (
        registry.list_extensions_metadata()[0],
        registry.list_extensions_metadata()[1],
        registry.list_extensions_metadata()[2],
    )
    assert [
        (entry.point, entry.name, entry.enabled, entry.source)
        for entry in registry.list_extensions_metadata()
    ] == [
        ("health", "alpha", False, "extension"),
        ("status", "core.status", True, "core"),
        ("status", "zeta", True, "extension"),
    ]


def test_disabled_extension_does_not_execute() -> None:
    registry = RuntimeObservabilityRegistry()
    registry.register(
        "status",
        name="disabled_boom",
        extension=lambda _context: (_ for _ in ()).throw(RuntimeError("must_not_run")),
        enabled=False,
    )
    registry.register(
        "status",
        name="safe",
        extension=lambda _context: {"status": "ok"},
    )

    result = registry.execute("status", context=_context())

    assert len(result.executions) == 1
    assert result.executions[0].extension_name == "safe"
    assert all(execution.extension_name != "disabled_boom" for execution in result.executions)

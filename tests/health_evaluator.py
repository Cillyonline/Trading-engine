from __future__ import annotations

from datetime import datetime, timedelta, timezone

from cilly_trading.engine.health.evaluator import evaluate_runtime_health


def test_health_evaluator_reports_healthy_at_degraded_boundary() -> None:
    now = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
    snapshot = {
        "mode": "running",
        "updated_at": now - timedelta(seconds=30),
    }

    result = evaluate_runtime_health(snapshot, now=now)

    assert result.status == "healthy"
    assert result.reason == "runtime_running_fresh"


def test_health_evaluator_reports_degraded_at_unavailable_boundary() -> None:
    now = datetime(2026, 1, 1, 12, 2, 0, tzinfo=timezone.utc)
    snapshot = {
        "mode": "running",
        "updated_at": now - timedelta(seconds=120),
    }

    result = evaluate_runtime_health(snapshot, now=now)

    assert result.status == "degraded"
    assert result.reason == "runtime_running_stale"


def test_health_evaluator_reports_unavailable_after_timeout() -> None:
    now = datetime(2026, 1, 1, 12, 2, 1, tzinfo=timezone.utc)
    snapshot = {
        "mode": "running",
        "updated_at": now - timedelta(seconds=121),
    }

    result = evaluate_runtime_health(snapshot, now=now)

    assert result.status == "unavailable"
    assert result.reason == "runtime_running_timeout"


def test_health_evaluator_reports_degraded_for_ready_mode() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    snapshot = {
        "mode": "ready",
        "updated_at": now,
    }

    result = evaluate_runtime_health(snapshot, now=now)

    assert result.status == "degraded"
    assert result.reason == "runtime_not_started"


def test_health_evaluator_reports_unavailable_for_non_running_modes() -> None:
    now = datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)
    snapshot = {
        "mode": "stopped",
        "updated_at": now,
    }

    result = evaluate_runtime_health(snapshot, now=now)

    assert result.status == "unavailable"
    assert result.reason == "runtime_not_available"

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Literal, TypedDict

HealthStatus = Literal["healthy", "degraded", "unavailable"]


class RuntimeHealthSnapshot(TypedDict):
    mode: str
    updated_at: datetime


@dataclass(frozen=True)
class RuntimeHealthResult:
    status: HealthStatus
    reason: str


def evaluate_runtime_health(
    snapshot: RuntimeHealthSnapshot,
    *,
    now: datetime,
    degraded_after: timedelta = timedelta(seconds=30),
    unavailable_after: timedelta = timedelta(seconds=120),
) -> RuntimeHealthResult:
    """Deterministically evaluate runtime health from an immutable snapshot.

    The evaluation is pure: callers provide both runtime snapshot and the
    reference timestamp (``now``), so tests can fully control outcomes.
    """

    normalized_now = _as_utc(now)
    updated_at = _as_utc(snapshot["updated_at"])
    lag = normalized_now - updated_at
    mode = snapshot["mode"]

    if mode == "running":
        if lag <= degraded_after:
            return RuntimeHealthResult(status="healthy", reason="runtime_running_fresh")
        if lag <= unavailable_after:
            return RuntimeHealthResult(status="degraded", reason="runtime_running_stale")
        return RuntimeHealthResult(status="unavailable", reason="runtime_running_timeout")

    if mode == "ready":
        return RuntimeHealthResult(status="degraded", reason="runtime_not_started")

    return RuntimeHealthResult(status="unavailable", reason="runtime_not_available")


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)

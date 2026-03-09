"""Deterministic runtime metrics registry for core engine activity."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import dataclass, field
from threading import Lock
from typing import Iterator, Mapping


ENGINE_METRIC_NAMES: tuple[str, ...] = (
    "analysis_runs",
    "signals_generated",
    "orders_submitted",
    "guard_triggers",
    "provider_failovers",
)

_EVENT_TO_METRIC: Mapping[str, str] = {
    "analysis_run.started": "analysis_runs",
    "signal.generated": "signals_generated",
    "order_submission.attempt": "orders_submitted",
    "guard.triggered": "guard_triggers",
    "provider_failover.recovered": "provider_failovers",
    "provider_failover.exhausted": "provider_failovers",
}


@dataclass
class EngineMetricsRegistry:
    """In-memory deterministic counter registry for runtime events."""

    _counters: dict[str, int] = field(
        default_factory=lambda: {metric_name: 0 for metric_name in ENGINE_METRIC_NAMES}
    )
    _lock: Lock = field(default_factory=Lock, repr=False)

    def increment(self, metric_name: str, value: int = 1) -> None:
        if metric_name not in self._counters:
            raise KeyError(f"unknown engine metric: {metric_name}")
        if not isinstance(value, int) or value < 0:
            raise ValueError("metric increment value must be a non-negative integer")
        if value == 0:
            return
        with self._lock:
            self._counters[metric_name] += value

    def increment_for_event(self, event: str) -> None:
        metric_name = _EVENT_TO_METRIC.get(event)
        if metric_name is None:
            return
        self.increment(metric_name)

    def reset(self) -> None:
        with self._lock:
            for metric_name in ENGINE_METRIC_NAMES:
                self._counters[metric_name] = 0

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            return {metric_name: self._counters[metric_name] for metric_name in ENGINE_METRIC_NAMES}


_GLOBAL_REGISTRY = EngineMetricsRegistry()


def get_engine_metrics_registry() -> EngineMetricsRegistry:
    """Return the process-local runtime metrics registry."""

    return _GLOBAL_REGISTRY


def get_engine_metrics_snapshot() -> dict[str, int]:
    """Return a deterministic snapshot of all runtime metric counters."""

    return _GLOBAL_REGISTRY.snapshot()


def reset_engine_metrics_registry() -> None:
    """Reset all runtime metric counters to zero."""

    _GLOBAL_REGISTRY.reset()


def record_runtime_event_metric(event: str) -> None:
    """Increment the matching runtime metric counter for an emitted event."""

    _GLOBAL_REGISTRY.increment_for_event(event)


@contextmanager
def engine_metrics_registry_context(
    registry: EngineMetricsRegistry,
) -> Iterator[EngineMetricsRegistry]:
    """Temporarily swap metric values for deterministic isolated runs/tests."""

    if not isinstance(registry, EngineMetricsRegistry):
        raise TypeError("registry must be an EngineMetricsRegistry")

    prior_snapshot = _GLOBAL_REGISTRY.snapshot()
    _GLOBAL_REGISTRY.reset()
    for metric_name, value in registry.snapshot().items():
        _GLOBAL_REGISTRY.increment(metric_name, value)
    try:
        yield _GLOBAL_REGISTRY
    finally:
        _GLOBAL_REGISTRY.reset()
        for metric_name, value in prior_snapshot.items():
            _GLOBAL_REGISTRY.increment(metric_name, value)

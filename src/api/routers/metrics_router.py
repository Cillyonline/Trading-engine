"""Prometheus-compatible metrics endpoint (Issue #1103).

Exports key operational and trading system health indicators in Prometheus
text exposition format (v0.0.4).

Requires ``prometheus-client`` as an optional dependency.  When the package
is not installed the ``/metrics`` endpoint returns HTTP 503 with an
explanatory message rather than crashing the server.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import APIRouter
from fastapi.responses import PlainTextResponse


@dataclass
class MetricsRouterDependencies:
    """Injected callables that supply current operational state for metrics.

    All callables are invoked on each scrape request so values are always
    fresh.  No caching is applied at this layer.
    """

    get_engine_healthy: Callable[[], bool]
    """Return True when the engine is in a healthy/running state."""

    get_daily_loss_current: Callable[[], float]
    """Return current daily loss as a non-negative absolute value."""

    get_daily_loss_limit: Callable[[], float | None]
    """Return configured daily loss limit, or None when unconfigured."""

    get_kill_switch_active: Callable[[], bool]
    """Return True when the global kill switch is active."""

    get_paper_positions_open: Callable[[], int]
    """Return count of currently open paper trading positions."""

    get_signals_by_strategy: Callable[[], dict[str, int]]
    """Return mapping of strategy name → total signals generated."""

    get_orders_rejected_by_reason: Callable[[], dict[str, int]]
    """Return mapping of rejection reason → total orders rejected."""


def build_metrics_router(*, deps: MetricsRouterDependencies) -> APIRouter:
    """Return an APIRouter exposing ``GET /metrics`` in Prometheus format.

    Args:
        deps: Injected callables that supply live operational state.

    Returns:
        Configured APIRouter.  Mount this on the FastAPI app as-is.
    """
    router = APIRouter()

    @router.get("/metrics", include_in_schema=False)
    def metrics_handler() -> PlainTextResponse:
        try:
            from prometheus_client import CollectorRegistry, generate_latest
            from prometheus_client import CONTENT_TYPE_LATEST
            from prometheus_client.metrics_core import (
                GaugeMetricFamily,
                CounterMetricFamily,
                HistogramMetricFamily,
            )
        except ImportError:
            return PlainTextResponse(
                content=(
                    "prometheus-client package is not installed; "
                    "install it to enable /metrics scraping"
                ),
                status_code=503,
                media_type="text/plain; charset=utf-8",
            )

        class _CillyCollector:
            """Snapshot collector — populates metrics from injected callables."""

            def describe(self):  # type: ignore[override]
                return []

            def collect(self):  # type: ignore[override]
                # ── engine health ──────────────────────────────────────────
                g = GaugeMetricFamily(
                    "cilly_engine_status",
                    "Engine health status (1=healthy, 0=degraded)",
                )
                g.add_metric([], 1.0 if deps.get_engine_healthy() else 0.0)
                yield g

                # ── daily loss ─────────────────────────────────────────────
                dl_cur = GaugeMetricFamily(
                    "cilly_daily_loss_current",
                    "Current daily loss (absolute portfolio currency)",
                )
                dl_cur.add_metric([], float(deps.get_daily_loss_current()))
                yield dl_cur

                limit = deps.get_daily_loss_limit()
                dl_lim = GaugeMetricFamily(
                    "cilly_daily_loss_limit",
                    "Configured daily loss limit (absolute); NaN when unconfigured",
                )
                dl_lim.add_metric(
                    [], float(limit) if limit is not None else float("nan")
                )
                yield dl_lim

                # ── kill switch ────────────────────────────────────────────
                ks = GaugeMetricFamily(
                    "cilly_kill_switch_active",
                    "Kill switch state (1=active, 0=inactive)",
                )
                ks.add_metric([], 1.0 if deps.get_kill_switch_active() else 0.0)
                yield ks

                # ── paper positions ────────────────────────────────────────
                pos = GaugeMetricFamily(
                    "cilly_paper_positions_open",
                    "Number of open paper trading positions",
                )
                pos.add_metric([], float(deps.get_paper_positions_open()))
                yield pos

                # ── signals generated (counter) ────────────────────────────
                sig = CounterMetricFamily(
                    "cilly_signals_generated_total",
                    "Total signals generated, labeled by strategy",
                    labels=["strategy"],
                )
                for strategy, count in deps.get_signals_by_strategy().items():
                    sig.add_metric([strategy], float(count))
                yield sig

                # ── orders rejected (counter) ──────────────────────────────
                rej = CounterMetricFamily(
                    "cilly_orders_rejected_total",
                    "Total orders rejected, labeled by rejection reason",
                    labels=["reason"],
                )
                for reason, count in deps.get_orders_rejected_by_reason().items():
                    rej.add_metric([reason], float(count))
                yield rej

                # ── db query duration (histogram placeholder) ──────────────
                _DEFAULT_BUCKETS = [
                    "0.005", "0.01", "0.025", "0.05", "0.1", "0.25", "0.5",
                    "1.0", "2.5", "5.0", "10.0", "+Inf",
                ]
                hist = HistogramMetricFamily(
                    "cilly_db_query_duration_seconds",
                    "Duration of repository-layer database queries in seconds",
                )
                hist.add_metric(
                    [],
                    buckets=[(b, 0) for b in _DEFAULT_BUCKETS],
                    sum_value=0.0,
                )
                yield hist

        registry = CollectorRegistry()
        registry.register(_CillyCollector())
        content = generate_latest(registry).decode("utf-8")

        return PlainTextResponse(content=content, media_type=CONTENT_TYPE_LATEST)

    return router

"""Bounded Prometheus HTTP metrics for the FastAPI application (issue #1139).

This module exposes a :class:`PrometheusMetricsMiddleware` and a
:func:`metrics_endpoint_response` that together provide:

  * ``cilly_api_http_requests_total``   – Counter, labels: method, route, status_class
  * ``cilly_api_http_request_duration_seconds`` – Histogram, labels: method, route
  * ``cilly_api_http_requests_in_progress`` – Gauge, labels: method, route

Label cardinality is intentionally kept **bounded**:

  * ``method`` – HTTP method (small fixed set).
  * ``route`` – the FastAPI route *template* (``/v1/items/{item_id}``) when a
    request matched a route, or ``"unmatched"`` for 404s. Raw URL paths,
    symbols, request IDs, account IDs, and other user-controlled values are
    deliberately **never** used as label values.
  * ``status_class`` – grouping such as ``"2xx"``, ``"4xx"``. The full status
    code is intentionally not used to keep cardinality bounded.

The middleware is fully self-contained: it owns its own
:class:`prometheus_client.CollectorRegistry`, so test isolation is not
affected by importing this module multiple times.
"""

from __future__ import annotations

import time
from typing import Callable, Optional

from fastapi import Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    CollectorRegistry,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.routing import Match
from starlette.types import ASGIApp


_DEFAULT_BUCKETS = (
    0.005,
    0.01,
    0.025,
    0.05,
    0.1,
    0.25,
    0.5,
    1.0,
    2.5,
    5.0,
    10.0,
)


def _status_class(status_code: int) -> str:
    if 200 <= status_code < 300:
        return "2xx"
    if 300 <= status_code < 400:
        return "3xx"
    if 400 <= status_code < 500:
        return "4xx"
    if 500 <= status_code < 600:
        return "5xx"
    return "other"


def _resolve_route_template(request: Request) -> str:
    """Return the matched route template, or ``"unmatched"`` if none.

    Using the route *template* (e.g. ``/v1/items/{item_id}``) keeps the label
    cardinality bounded and avoids leaking high-cardinality user-controlled
    values such as raw paths, symbols, or IDs.
    """

    router = request.scope.get("router")
    if router is None:
        return "unmatched"
    for route in getattr(router, "routes", []):
        try:
            match, _ = route.matches(request.scope)
        except Exception:  # pragma: no cover - defensive fallback
            continue
        if match == Match.FULL:
            template = getattr(route, "path", None)
            if isinstance(template, str) and template:
                return template
    return "unmatched"


class PrometheusMetrics:
    """Holds the Prometheus collectors used by the HTTP metrics middleware."""

    def __init__(self, registry: Optional[CollectorRegistry] = None) -> None:
        self.registry: CollectorRegistry = registry or CollectorRegistry()
        self.requests_total: Counter = Counter(
            "cilly_api_http_requests_total",
            "Total number of HTTP requests processed by the API.",
            labelnames=("method", "route", "status_class"),
            registry=self.registry,
        )
        self.request_duration_seconds: Histogram = Histogram(
            "cilly_api_http_request_duration_seconds",
            "HTTP request duration in seconds.",
            labelnames=("method", "route"),
            registry=self.registry,
            buckets=_DEFAULT_BUCKETS,
        )
        self.requests_in_progress: Gauge = Gauge(
            "cilly_api_http_requests_in_progress",
            "Number of HTTP requests currently being processed.",
            labelnames=("method", "route"),
            registry=self.registry,
        )


class PrometheusMetricsMiddleware(BaseHTTPMiddleware):
    """ASGI middleware that records bounded HTTP metrics."""

    def __init__(self, app: ASGIApp, metrics: PrometheusMetrics) -> None:
        super().__init__(app)
        self._metrics = metrics

    async def dispatch(
        self,
        request: Request,
        call_next: Callable,
    ) -> Response:
        # Never measure the metrics endpoint itself, so scraping does not
        # appear as request traffic.
        if request.url.path == "/metrics":
            return await call_next(request)

        method = request.method.upper()
        route = _resolve_route_template(request)
        in_progress = self._metrics.requests_in_progress.labels(
            method=method, route=route
        )
        in_progress.inc()
        start = time.perf_counter()
        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        finally:
            elapsed = time.perf_counter() - start
            self._metrics.request_duration_seconds.labels(
                method=method, route=route
            ).observe(elapsed)
            self._metrics.requests_total.labels(
                method=method,
                route=route,
                status_class=_status_class(status_code),
            ).inc()
            in_progress.dec()


def metrics_endpoint_response(metrics: PrometheusMetrics) -> Response:
    """Render the current Prometheus metrics as a text response."""

    payload = generate_latest(metrics.registry)
    return Response(content=payload, media_type=CONTENT_TYPE_LATEST)

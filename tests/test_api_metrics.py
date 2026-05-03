"""Tests for Prometheus metrics endpoint (Issue #1103)."""

from __future__ import annotations

import sys

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

pytest.importorskip("prometheus_client", reason="prometheus-client not installed")

from api.routers.metrics_router import MetricsRouterDependencies, build_metrics_router


# ── helpers ───────────────────────────────────────────────────────────────────


def _make_app(
    engine_healthy: bool = True,
    daily_loss_current: float = 50.0,
    daily_loss_limit: float | None = 1000.0,
    kill_switch_active: bool = False,
    paper_positions_open: int = 3,
    signals_by_strategy: dict[str, int] | None = None,
    orders_rejected_by_reason: dict[str, int] | None = None,
) -> FastAPI:
    app = FastAPI()
    deps = MetricsRouterDependencies(
        get_engine_healthy=lambda: engine_healthy,
        get_daily_loss_current=lambda: daily_loss_current,
        get_daily_loss_limit=lambda: daily_loss_limit,
        get_kill_switch_active=lambda: kill_switch_active,
        get_paper_positions_open=lambda: paper_positions_open,
        get_signals_by_strategy=lambda: (signals_by_strategy or {}),
        get_orders_rejected_by_reason=lambda: (orders_rejected_by_reason or {}),
    )
    app.include_router(build_metrics_router(deps=deps))
    return app


# ── basic endpoint behaviour ───────────────────────────────────────────────────


def test_metrics_endpoint_returns_200() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert resp.status_code == 200


def test_metrics_content_type_is_text_plain() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "text/plain" in resp.headers["content-type"]


def test_metrics_no_authentication_required() -> None:
    """GET /metrics must not require any auth headers."""
    resp = TestClient(_make_app()).get("/metrics")
    assert resp.status_code == 200


# ── metric presence ───────────────────────────────────────────────────────────


def test_metrics_contains_engine_status() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_engine_status" in resp.text


def test_metrics_contains_daily_loss_current() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_daily_loss_current" in resp.text


def test_metrics_contains_daily_loss_limit() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_daily_loss_limit" in resp.text


def test_metrics_contains_kill_switch() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_kill_switch_active" in resp.text


def test_metrics_contains_paper_positions() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_paper_positions_open" in resp.text


def test_metrics_contains_signals_counter() -> None:
    resp = TestClient(_make_app(signals_by_strategy={"RSI2": 10})).get("/metrics")
    assert "cilly_signals_generated_total" in resp.text


def test_metrics_contains_orders_rejected_counter() -> None:
    resp = TestClient(_make_app(orders_rejected_by_reason={"kill_switch": 3})).get("/metrics")
    assert "cilly_orders_rejected_total" in resp.text


def test_metrics_contains_db_query_histogram() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "cilly_db_query_duration_seconds" in resp.text


# ── gauge values ──────────────────────────────────────────────────────────────


def _metric_lines(text: str, prefix: str) -> list[str]:
    return [l for l in text.splitlines() if l.startswith(prefix) and not l.startswith("#")]


def test_engine_status_is_1_when_healthy() -> None:
    resp = TestClient(_make_app(engine_healthy=True)).get("/metrics")
    lines = _metric_lines(resp.text, "cilly_engine_status")
    assert any("1.0" in l for l in lines)


def test_engine_status_is_0_when_degraded() -> None:
    resp = TestClient(_make_app(engine_healthy=False)).get("/metrics")
    lines = _metric_lines(resp.text, "cilly_engine_status")
    assert any("0.0" in l for l in lines)


def test_kill_switch_is_1_when_active() -> None:
    resp = TestClient(_make_app(kill_switch_active=True)).get("/metrics")
    lines = _metric_lines(resp.text, "cilly_kill_switch_active")
    assert any("1.0" in l for l in lines)


def test_kill_switch_is_0_when_inactive() -> None:
    resp = TestClient(_make_app(kill_switch_active=False)).get("/metrics")
    lines = _metric_lines(resp.text, "cilly_kill_switch_active")
    assert any("0.0" in l for l in lines)


def test_paper_positions_value_matches() -> None:
    resp = TestClient(_make_app(paper_positions_open=7)).get("/metrics")
    lines = _metric_lines(resp.text, "cilly_paper_positions_open")
    assert any("7.0" in l for l in lines)


# ── counter labels ────────────────────────────────────────────────────────────


def test_signals_counter_has_strategy_label() -> None:
    resp = TestClient(_make_app(signals_by_strategy={"RSI2": 10})).get("/metrics")
    assert 'strategy="RSI2"' in resp.text


def test_signals_counter_multiple_strategies() -> None:
    resp = TestClient(_make_app(signals_by_strategy={"RSI2": 10, "TURTLE": 5})).get("/metrics")
    assert 'strategy="RSI2"' in resp.text
    assert 'strategy="TURTLE"' in resp.text


def test_orders_rejected_has_reason_label() -> None:
    resp = TestClient(_make_app(orders_rejected_by_reason={"kill_switch": 3, "daily_loss": 1})).get("/metrics")
    assert 'reason="kill_switch"' in resp.text
    assert 'reason="daily_loss"' in resp.text


# ── type and help declarations ────────────────────────────────────────────────


def test_engine_status_type_is_gauge() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "# TYPE cilly_engine_status gauge" in resp.text


def test_kill_switch_type_is_gauge() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "# TYPE cilly_kill_switch_active gauge" in resp.text


def test_signals_counter_type_is_counter() -> None:
    resp = TestClient(_make_app(signals_by_strategy={"RSI2": 1})).get("/metrics")
    assert "# TYPE cilly_signals_generated_total counter" in resp.text


def test_db_histogram_type_is_histogram() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "# TYPE cilly_db_query_duration_seconds histogram" in resp.text


def test_help_declarations_present() -> None:
    resp = TestClient(_make_app()).get("/metrics")
    assert "# HELP cilly_engine_status" in resp.text
    assert "# HELP cilly_daily_loss_current" in resp.text
    assert "# HELP cilly_kill_switch_active" in resp.text


# ── graceful degradation when prometheus-client absent ────────────────────────


def test_metrics_returns_503_when_prometheus_client_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """When prometheus-client is not importable, /metrics must return 503."""
    monkeypatch.setitem(sys.modules, "prometheus_client", None)  # type: ignore[arg-type]
    # Also clear sub-modules so the nested import fails cleanly
    for key in list(sys.modules):
        if key.startswith("prometheus_client."):
            monkeypatch.setitem(sys.modules, key, None)  # type: ignore[arg-type]

    client = TestClient(_make_app())
    resp = client.get("/metrics")
    assert resp.status_code == 503
    assert "prometheus-client" in resp.text.lower()

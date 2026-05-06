"""Tests for the bounded Prometheus HTTP metrics middleware (issue #1139)."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def _client() -> TestClient:
    return TestClient(api_main.app)


def _metrics_text() -> str:
    client = _client()
    response = client.get("/metrics")
    assert response.status_code == 200
    assert "text/plain" in response.headers.get("content-type", "")
    return response.text


def test_metrics_endpoint_exposes_prometheus_text() -> None:
    text = _metrics_text()
    assert "cilly_api_http_requests_total" in text
    assert "cilly_api_http_request_duration_seconds" in text


def test_metrics_recorded_after_normal_request() -> None:
    client = _client()
    ok = client.get("/api/openapi.json")
    assert ok.status_code == 200
    metrics_response = client.get("/metrics")
    assert metrics_response.status_code == 200
    body = metrics_response.text
    assert 'cilly_api_http_requests_total{' in body
    assert 'status_class="2xx"' in body
    assert 'cilly_api_http_request_duration_seconds_count{' in body


def test_metrics_records_error_status_class_for_unmatched_route() -> None:
    client = _client()
    not_found = client.get("/this/path/does/not/exist/abc123")
    assert not_found.status_code == 404
    metrics_response = client.get("/metrics")
    body = metrics_response.text
    assert 'status_class="4xx"' in body
    # The raw URL must NOT appear as a label value (cardinality safety).
    assert "/this/path/does/not/exist/abc123" not in body


def test_metrics_endpoint_itself_is_not_counted() -> None:
    client = _client()
    client.get("/metrics")
    body = client.get("/metrics").text
    assert 'route="/metrics"' not in body

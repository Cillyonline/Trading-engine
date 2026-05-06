"""Tests for FastAPI documentation endpoints (issue #1138)."""

from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def _client() -> TestClient:
    return TestClient(api_main.app)


def test_openapi_endpoint_returns_valid_schema() -> None:
    client = _client()
    response = client.get("/api/openapi.json")
    assert response.status_code == 200
    payload = response.json()
    assert payload.get("openapi", "").startswith("3."), payload
    info = payload.get("info", {})
    assert info.get("title") == "Cilly Trading Engine API"
    assert info.get("version") == "0.1.0"
    assert isinstance(payload.get("paths"), dict) and payload["paths"]


def test_swagger_ui_docs_endpoint_returns_html() -> None:
    client = _client()
    response = client.get("/api/docs")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "swagger" in response.text.lower()


def test_redoc_docs_endpoint_returns_html() -> None:
    client = _client()
    response = client.get("/api/redoc")
    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")
    assert "redoc" in response.text.lower()


def test_openapi_export_script_writes_file(tmp_path) -> None:
    # Reproducible export path used by CI/operators.
    from scripts.export_openapi import export_openapi

    output = tmp_path / "openapi.json"
    written = export_openapi(output)
    assert written == output
    assert output.exists()

    import json

    schema = json.loads(output.read_text(encoding="utf-8"))
    assert schema["info"]["title"] == "Cilly Trading Engine API"
    assert schema["info"]["version"] == "0.1.0"

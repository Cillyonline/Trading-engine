from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_operator_workbench_ui_surface_is_reachable(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "text/html" in response.headers.get("content-type", "")


def test_operator_workbench_ui_surface_has_base_navigation(monkeypatch) -> None:
    def _start() -> str:
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app) as client:
        response = client.get("/ui")

    assert response.status_code == 200
    assert "Operator Workbench" in response.text
    assert "Workbench navigation" in response.text
    assert "Overview" in response.text
    assert "Runtime Status" in response.text
    assert "Analysis Runs" in response.text
    assert "Audit Trail" in response.text
    assert "<script" not in response.text

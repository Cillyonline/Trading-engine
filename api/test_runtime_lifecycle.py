from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


def test_runtime_is_started_on_api_startup(monkeypatch) -> None:
    calls: list[str] = []

    def _start() -> str:
        calls.append("start")
        return "running"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)

    with TestClient(api_main.app):
        assert calls == ["start"]


def test_runtime_is_shutdown_on_api_shutdown(monkeypatch) -> None:
    calls: list[str] = []

    def _start() -> str:
        return "running"

    def _shutdown() -> str:
        calls.append("shutdown")
        return "stopped"

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", _shutdown)

    with TestClient(api_main.app):
        pass

    assert calls == ["shutdown"]

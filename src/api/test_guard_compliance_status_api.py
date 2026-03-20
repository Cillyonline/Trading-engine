from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main

READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def test_compliance_guard_status_endpoint_is_reachable(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/compliance/guards/status", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200


def test_compliance_guard_status_response_structure_default_allowing(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        payload = client.get("/compliance/guards/status", headers=READ_ONLY_HEADERS).json()

    assert payload["compliance"] == {
        "blocking": False,
        "decision": "allowing",
    }
    assert payload["guards"]["drawdown_guard"] == {
        "enabled": False,
        "blocking": False,
        "decision": "allowing",
        "threshold_pct": None,
        "current_drawdown_pct": 0.0,
    }
    assert payload["guards"]["daily_loss_guard"] == {
        "enabled": False,
        "blocking": False,
        "decision": "allowing",
        "max_daily_loss_abs": None,
        "current_daily_loss_abs": 0.0,
    }
    assert payload["guards"]["kill_switch"] == {
        "active": False,
        "blocking": False,
        "decision": "allowing",
    }


def test_compliance_guard_status_is_deterministic_and_reports_blocking(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setenv("CILLY_PORTFOLIO_PEAK_EQUITY", "100000.0")
    monkeypatch.setenv("CILLY_PORTFOLIO_CURRENT_EQUITY", "85000.0")
    monkeypatch.setenv("CILLY_PORTFOLIO_START_OF_DAY_EQUITY", "100000.0")
    monkeypatch.setenv("CILLY_EXECUTION_DRAWDOWN_MAX_PCT", "0.10")
    monkeypatch.setenv("CILLY_EXECUTION_DAILY_LOSS_MAX_ABS", "1000.0")
    monkeypatch.setenv("CILLY_EXECUTION_KILL_SWITCH_ACTIVE", "true")

    with TestClient(api_main.app) as client:
        first = client.get("/compliance/guards/status", headers=READ_ONLY_HEADERS).json()
        second = client.get("/compliance/guards/status", headers=READ_ONLY_HEADERS).json()

    assert first == second
    assert first["compliance"] == {
        "blocking": True,
        "decision": "blocking",
    }
    assert first["guards"]["drawdown_guard"]["enabled"] is True
    assert first["guards"]["drawdown_guard"]["blocking"] is True
    assert first["guards"]["daily_loss_guard"]["enabled"] is True
    assert first["guards"]["daily_loss_guard"]["blocking"] is True
    assert first["guards"]["kill_switch"] == {
        "active": True,
        "blocking": True,
        "decision": "blocking",
    }


def test_compliance_guard_status_endpoint_requires_authenticated_role(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/compliance/guards/status")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_compliance_guard_status_endpoint_rejects_invalid_role(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get(
            "/compliance/guards/status",
            headers={api_main.ROLE_HEADER_NAME: "auditor"},
        )

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}

from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main


OPERATOR_HEADERS = {"X-Cilly-Role": "operator"}
READ_ONLY_HEADERS = {"X-Cilly-Role": "read_only"}


def _create_payload(alert_id: str = "drawdown-warning") -> dict[str, object]:
    return {
        "alert_id": alert_id,
        "name": "Drawdown Warning",
        "description": "Warn when drawdown breaches threshold.",
        "source": "risk",
        "metric": "drawdown_pct",
        "operator": "gte",
        "threshold": 5.0,
        "severity": "warning",
        "enabled": True,
        "tags": ["risk", "drawdown"],
    }


def test_alert_configuration_crud_and_listing(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_configuration_store = {}

    with TestClient(api_main.app) as client:
        create_response = client.post(
            "/alerts/configurations",
            json=_create_payload(),
            headers=OPERATOR_HEADERS,
        )
        assert create_response.status_code == 201
        assert create_response.json() == _create_payload()

        read_response = client.get(
            "/alerts/configurations/drawdown-warning",
            headers=READ_ONLY_HEADERS,
        )
        assert read_response.status_code == 200
        assert read_response.json() == _create_payload()

        update_response = client.put(
            "/alerts/configurations/drawdown-warning",
            json={
                "name": "Drawdown Critical",
                "description": "Escalate when drawdown is severe.",
                "source": "risk",
                "metric": "drawdown_pct",
                "operator": "gte",
                "threshold": 8.5,
                "severity": "critical",
                "enabled": False,
                "tags": ["risk", "critical"],
            },
            headers=OPERATOR_HEADERS,
        )
        assert update_response.status_code == 200
        assert update_response.json() == {
            "alert_id": "drawdown-warning",
            "name": "Drawdown Critical",
            "description": "Escalate when drawdown is severe.",
            "source": "risk",
            "metric": "drawdown_pct",
            "operator": "gte",
            "threshold": 8.5,
            "severity": "critical",
            "enabled": False,
            "tags": ["risk", "critical"],
        }

        configuration_list_response = client.get(
            "/alerts/configurations",
            headers=READ_ONLY_HEADERS,
        )
        assert configuration_list_response.status_code == 200
        assert configuration_list_response.json() == {
            "items": [
                {
                    "alert_id": "drawdown-warning",
                    "name": "Drawdown Critical",
                    "description": "Escalate when drawdown is severe.",
                    "source": "risk",
                    "metric": "drawdown_pct",
                    "operator": "gte",
                    "threshold": 8.5,
                    "severity": "critical",
                    "enabled": False,
                    "tags": ["risk", "critical"],
                }
            ],
            "total": 1,
        }

        alerts_list_response = client.get("/alerts", headers=READ_ONLY_HEADERS)
        assert alerts_list_response.status_code == 200
        assert alerts_list_response.json() == {
            "items": [
                {
                    "alert_id": "drawdown-warning",
                    "name": "Drawdown Critical",
                    "severity": "critical",
                    "enabled": False,
                    "source": "risk",
                    "metric": "drawdown_pct",
                    "operator": "gte",
                    "threshold": 8.5,
                }
            ],
            "total": 1,
        }

        delete_response = client.delete(
            "/alerts/configurations/drawdown-warning",
            headers=OPERATOR_HEADERS,
        )
        assert delete_response.status_code == 200
        assert delete_response.json() == {
            "alert_id": "drawdown-warning",
            "deleted": True,
        }

        missing_after_delete = client.get(
            "/alerts/configurations/drawdown-warning",
            headers=READ_ONLY_HEADERS,
        )
        assert missing_after_delete.status_code == 404
        assert missing_after_delete.json() == {"detail": "alert_configuration_not_found"}


def test_alert_configuration_validation_rejects_invalid_payload(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_configuration_store = {}

    with TestClient(api_main.app) as client:
        invalid_operator_response = client.post(
            "/alerts/configurations",
            json={
                "alert_id": "invalid-alert",
                "name": "Invalid",
                "source": "risk",
                "metric": "drawdown_pct",
                "operator": "invalid",
                "threshold": 2.0,
                "severity": "warning",
                "enabled": True,
                "tags": ["risk", "risk"],
            },
            headers=OPERATOR_HEADERS,
        )

        duplicate_tags_response = client.post(
            "/alerts/configurations",
            json={
                "alert_id": "duplicate-tags-alert",
                "name": "Duplicate Tags",
                "source": "risk",
                "metric": "drawdown_pct",
                "operator": "gte",
                "threshold": 2.0,
                "severity": "warning",
                "enabled": True,
                "tags": ["risk", "risk"],
            },
            headers=OPERATOR_HEADERS,
        )

    assert invalid_operator_response.status_code == 422
    invalid_operator_detail = invalid_operator_response.json()["detail"]
    assert any(item["loc"][-1] == "operator" for item in invalid_operator_detail)

    assert duplicate_tags_response.status_code == 422
    duplicate_tags_detail = duplicate_tags_response.json()["detail"]
    assert any("tags must be unique" in item["msg"] for item in duplicate_tags_detail)


def test_alert_listing_is_sorted_and_read_only_accessible(monkeypatch) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    api_main.app.state.alert_configuration_store = {}

    with TestClient(api_main.app) as client:
        first = _create_payload("zeta-alert")
        second = _create_payload("alpha-alert")
        second["name"] = "Alpha Alert"
        second["metric"] = "latency_ms"
        second["threshold"] = 250.0

        assert client.post(
            "/alerts/configurations",
            json=first,
            headers=OPERATOR_HEADERS,
        ).status_code == 201
        assert client.post(
            "/alerts/configurations",
            json=second,
            headers=OPERATOR_HEADERS,
        ).status_code == 201

        response = client.get("/alerts", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json()["items"] == [
        {
            "alert_id": "alpha-alert",
            "name": "Alpha Alert",
            "severity": "warning",
            "enabled": True,
            "source": "risk",
            "metric": "latency_ms",
            "operator": "gte",
            "threshold": 250.0,
        },
        {
            "alert_id": "zeta-alert",
            "name": "Drawdown Warning",
            "severity": "warning",
            "enabled": True,
            "source": "risk",
            "metric": "drawdown_pct",
            "operator": "gte",
            "threshold": 5.0,
        },
    ]

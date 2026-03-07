from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


def test_execution_pause_endpoint_pauses_runtime_and_updates_state_views() -> None:
    with TestClient(api_main.app) as client:
        pause_response = client.post('/execution/pause')
        introspection_response = client.get('/runtime/introspection')
        system_state_response = client.get('/system/state')

    assert pause_response.status_code == 200
    assert pause_response.json() == {'state': 'paused'}
    assert introspection_response.status_code == 200
    assert introspection_response.json()['mode'] == 'paused'
    assert system_state_response.status_code == 200
    assert system_state_response.json()['status'] == 'paused'


def test_execution_resume_endpoint_resumes_runtime() -> None:
    with TestClient(api_main.app) as client:
        client.post('/execution/pause')
        resume_response = client.post('/execution/resume')

    assert resume_response.status_code == 200
    assert resume_response.json() == {'state': 'running'}


def test_execution_pause_endpoint_returns_conflict_when_runtime_not_running(monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'start_engine_runtime', lambda: 'ready')

    with TestClient(api_main.app) as client:
        response = client.post('/execution/pause')

    assert response.status_code == 409
    assert "Cannot pause_execution()" in response.json()['detail']

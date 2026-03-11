from __future__ import annotations

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests

OWNER_HEADERS = {api_main.ROLE_HEADER_NAME: "owner"}
OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


def test_execution_pause_endpoint_pauses_runtime_and_updates_state_views() -> None:
    with TestClient(api_main.app) as client:
        pause_response = client.post('/execution/pause', headers=OWNER_HEADERS)
        introspection_response = client.get('/runtime/introspection')
        system_state_response = client.get('/system/state', headers=READ_ONLY_HEADERS)

    assert pause_response.status_code == 200
    assert pause_response.json() == {'state': 'paused'}
    assert introspection_response.status_code == 200
    assert introspection_response.json()['mode'] == 'paused'
    assert system_state_response.status_code == 200
    assert system_state_response.json()['status'] == 'paused'


def test_execution_resume_endpoint_resumes_runtime() -> None:
    with TestClient(api_main.app) as client:
        client.post('/execution/pause', headers=OWNER_HEADERS)
        resume_response = client.post('/execution/resume', headers=OWNER_HEADERS)

    assert resume_response.status_code == 200
    assert resume_response.json() == {'state': 'running'}


def test_execution_start_endpoint_returns_running_when_runtime_is_ready(monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'start_engine_runtime', lambda: 'running')

    with TestClient(api_main.app) as client:
        response = client.post('/execution/start', headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {'state': 'running'}


def test_execution_start_endpoint_returns_conflict_for_paused_runtime(monkeypatch) -> None:
    def _start() -> str:
        raise api_main.LifecycleTransitionError(
            "Cannot ensure running runtime from state 'paused'."
        )

    with TestClient(api_main.app) as client:
        monkeypatch.setattr(api_main, 'start_engine_runtime', _start)
        response = client.post('/execution/start', headers=OWNER_HEADERS)

    assert response.status_code == 409
    assert response.json() == {
        'detail': "Cannot ensure running runtime from state 'paused'."
    }


def test_execution_stop_endpoint_returns_stopped_when_runtime_is_running(monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'shutdown_engine_runtime', lambda: 'stopped')

    with TestClient(api_main.app) as client:
        response = client.post('/execution/stop', headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {'state': 'stopped'}


def test_execution_stop_endpoint_returns_ready_for_pre_running_no_op(monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'shutdown_engine_runtime', lambda: 'ready')

    with TestClient(api_main.app) as client:
        response = client.post('/execution/stop', headers=OWNER_HEADERS)

    assert response.status_code == 200
    assert response.json() == {'state': 'ready'}


def test_execution_pause_endpoint_returns_conflict_when_runtime_not_running(monkeypatch) -> None:
    monkeypatch.setattr(api_main, 'start_engine_runtime', lambda: 'ready')

    with TestClient(api_main.app) as client:
        response = client.post('/execution/pause', headers=OWNER_HEADERS)

    assert response.status_code == 409
    assert "Cannot pause_execution()" in response.json()['detail']


def test_execution_pause_endpoint_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/pause')

    assert response.status_code == 401
    assert response.json() == {'detail': 'unauthorized'}


def test_execution_start_endpoint_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/start')

    assert response.status_code == 401
    assert response.json() == {'detail': 'unauthorized'}


def test_execution_stop_endpoint_requires_authenticated_role() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/stop')

    assert response.status_code == 401
    assert response.json() == {'detail': 'unauthorized'}


def test_execution_pause_endpoint_forbids_operator_role_without_side_effect() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/pause', headers=OPERATOR_HEADERS)
        introspection_response = client.get('/runtime/introspection')
        system_state_response = client.get('/system/state', headers=READ_ONLY_HEADERS)

    assert response.status_code == 403
    assert response.json() == {'detail': 'forbidden'}
    assert introspection_response.status_code == 200
    assert introspection_response.json()['mode'] == 'running'
    assert system_state_response.status_code == 200
    assert system_state_response.json()['status'] == 'running'


def test_execution_start_endpoint_forbids_operator_role_without_side_effect() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/start', headers=OPERATOR_HEADERS)
        introspection_response = client.get('/runtime/introspection')
        system_state_response = client.get('/system/state', headers=READ_ONLY_HEADERS)

    assert response.status_code == 403
    assert response.json() == {'detail': 'forbidden'}
    assert introspection_response.status_code == 200
    assert introspection_response.json()['mode'] == 'running'
    assert system_state_response.status_code == 200
    assert system_state_response.json()['status'] == 'running'


def test_execution_stop_endpoint_forbids_operator_role_without_side_effect() -> None:
    with TestClient(api_main.app) as client:
        response = client.post('/execution/stop', headers=OPERATOR_HEADERS)
        introspection_response = client.get('/runtime/introspection')
        system_state_response = client.get('/system/state', headers=READ_ONLY_HEADERS)

    assert response.status_code == 403
    assert response.json() == {'detail': 'forbidden'}
    assert introspection_response.status_code == 200
    assert introspection_response.json()['mode'] == 'running'
    assert system_state_response.status_code == 200
    assert system_state_response.json()['status'] == 'running'

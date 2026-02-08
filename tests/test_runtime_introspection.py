from __future__ import annotations

import importlib.machinery
import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient

_SRC_PATH = Path(__file__).resolve().parents[1] / "src"

_api_spec = importlib.machinery.PathFinder.find_spec("api", [str(_SRC_PATH)])
if _api_spec is None or _api_spec.loader is None:
    raise RuntimeError("Unable to resolve package 'api' under src/")
_api_module = importlib.util.module_from_spec(_api_spec)
sys.modules[_api_spec.name] = _api_module
_api_spec.loader.exec_module(_api_module)

_main_spec = importlib.machinery.PathFinder.find_spec("api.main", _api_module.__path__)
if _main_spec is None or _main_spec.loader is None:
    raise RuntimeError("Unable to resolve module 'api.main' under src/")
api_main = importlib.util.module_from_spec(_main_spec)
sys.modules[_main_spec.name] = api_main
_main_spec.loader.exec_module(api_main)


class _RuntimeStateStub:
    def __init__(self, state: str) -> None:
        self.state = state


def test_runtime_introspection_contract_is_explicit_and_stable(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")

    def _start() -> str:
        return "running"

    def _runtime() -> _RuntimeStateStub:
        return runtime

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)

    with TestClient(api_main.app) as client:
        first = client.get("/runtime/introspection")
        second = client.get("/runtime/introspection")

    assert first.status_code == 200
    assert second.status_code == 200

    first_payload = first.json()
    second_payload = second.json()

    assert set(first_payload.keys()) == {
        "schema_version",
        "runtime_id",
        "mode",
        "timestamps",
        "ownership",
    }
    assert set(first_payload["timestamps"].keys()) == {"started_at", "updated_at"}
    assert set(first_payload["ownership"].keys()) == {"owner_tag"}
    assert first_payload["schema_version"] == "v1"
    assert first_payload == second_payload
    assert runtime.state == "running"


def test_runtime_introspection_triggers_no_persistence_writes(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")

    def _start() -> str:
        return "running"

    def _runtime() -> _RuntimeStateStub:
        return runtime

    def _unexpected_save_run(*args, **kwargs):
        raise AssertionError("analysis_run_repo.save_run must not be called")

    def _unexpected_save_signals(*args, **kwargs):
        raise AssertionError("signal_repo.save_signals must not be called")

    monkeypatch.setattr(api_main, "start_engine_runtime", _start)
    monkeypatch.setattr(api_main, "get_runtime_controller", _runtime)
    monkeypatch.setattr(api_main.analysis_run_repo, "save_run", _unexpected_save_run)
    monkeypatch.setattr(api_main.signal_repo, "save_signals", _unexpected_save_signals)

    with TestClient(api_main.app) as client:
        response = client.get("/runtime/introspection")

    assert response.status_code == 200

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable

import pytest
from fastapi.testclient import TestClient

import api.main as api_main


@dataclass
class _RuntimeStateStub:
    state: str


class Phase13SideEffectDetector:
    def __init__(self, monkeypatch: pytest.MonkeyPatch) -> None:
        self._monkeypatch = monkeypatch
        self._write_calls = 0
        self._emit_calls = 0
        self._transition_calls = 0
        self._runtime = _RuntimeStateStub("running")
        self._before_snapshot: dict[str, Any] = {}

    def install(self) -> None:
        self._monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
        self._monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
        self._monkeypatch.setattr(api_main, "_health_now", self._fixed_now)
        self._monkeypatch.setattr(
            api_main,
            "get_runtime_introspection_payload",
            self._introspection_payload,
        )

        self._monkeypatch.setattr(api_main, "get_runtime_controller", self._unexpected_transition)
        self._monkeypatch.setattr(api_main.analysis_run_repo, "save_run", self._unexpected_write)
        self._monkeypatch.setattr(api_main.signal_repo, "save_signals", self._unexpected_write)

    def capture_before(self) -> None:
        self._before_snapshot = {
            "engine_runtime_guard_active": api_main.ENGINE_RUNTIME_GUARD_ACTIVE,
            "runtime_state": self._runtime.state,
        }

    def assert_no_side_effects(self) -> None:
        after_snapshot = {
            "engine_runtime_guard_active": api_main.ENGINE_RUNTIME_GUARD_ACTIVE,
            "runtime_state": self._runtime.state,
        }

        assert self._before_snapshot == after_snapshot
        assert self._write_calls == 0
        assert self._emit_calls == 0
        assert self._transition_calls == 0

    def inject_forced_violation(self) -> None:
        self._write_calls += 1

    def _fixed_now(self) -> datetime:
        return datetime(2026, 1, 1, 12, 0, 0, tzinfo=timezone.utc)

    def _introspection_payload(self) -> dict[str, object]:
        return {
            "schema_version": "v1",
            "runtime_id": "engine-runtime-123",
            "mode": "running",
            "timestamps": {
                "started_at": "2026-01-01T12:00:00+00:00",
                "updated_at": "2026-01-01T12:00:00+00:00",
            },
            "ownership": {"owner_tag": "engine"},
        }

    def _unexpected_transition(self) -> _RuntimeStateStub:
        self._transition_calls += 1
        raise AssertionError("Phase-13 endpoint must not trigger runtime transitions")

    def _unexpected_write(self, *args: Any, **kwargs: Any) -> None:
        self._write_calls += 1
        raise AssertionError("Phase-13 endpoint must not write to persistence")


@pytest.mark.parametrize("path", ["/health", "/runtime/introspection"])
def test_phase13_endpoints_are_side_effect_free(path: str, monkeypatch: pytest.MonkeyPatch) -> None:
    detector = Phase13SideEffectDetector(monkeypatch)
    detector.install()
    detector.capture_before()

    with TestClient(api_main.app) as client:
        response = client.get(path)

    assert response.status_code == 200
    detector.assert_no_side_effects()


def test_side_effect_detector_fails_deterministically_on_violation(monkeypatch: pytest.MonkeyPatch) -> None:
    detector = Phase13SideEffectDetector(monkeypatch)
    detector.install()
    detector.capture_before()
    detector.inject_forced_violation()

    with pytest.raises(AssertionError):
        detector.assert_no_side_effects()


def test_phase13_read_only_endpoint_registry_is_explicit() -> None:
    assert api_main.PHASE_13_READ_ONLY_ENDPOINTS == frozenset({"/health", "/runtime/introspection"})

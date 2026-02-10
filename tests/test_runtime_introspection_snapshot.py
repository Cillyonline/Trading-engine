from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
import cilly_trading.engine.runtime_introspection as runtime_introspection
from cilly_trading.engine.observability_extensions import RuntimeObservabilityRegistry


class _RuntimeStateStub:
    def __init__(self, state: str) -> None:
        self.state = state


def _registry() -> RuntimeObservabilityRegistry:
    registry = RuntimeObservabilityRegistry()
    registry.register("status", name="core.status", extension=lambda _context: {}, source="core")
    registry.register("health", name="ext.disabled", extension=lambda _context: {}, enabled=False)
    registry.register("introspection", name="ext.enabled", extension=lambda _context: {}, enabled=True)
    return registry


def test_runtime_introspection_snapshot_with_extensions(monkeypatch) -> None:
    runtime = _RuntimeStateStub("running")
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "get_runtime_controller", lambda: runtime)
    monkeypatch.setattr(runtime_introspection, "_RUNTIME_OBSERVABILITY_REGISTRY", _registry())
    monkeypatch.setattr(
        runtime_introspection,
        "_RUNTIME_INTROSPECTION_STARTED_AT",
        datetime(2026, 2, 10, 12, 0, 0, tzinfo=timezone.utc),
    )

    with TestClient(api_main.app) as client:
        payload = client.get("/runtime/introspection").json()

    snapshot_path = Path(__file__).parent / "fixtures" / "runtime_introspection_snapshot.json"
    expected = json.loads(snapshot_path.read_text())
    payload["runtime_id"] = "<runtime_id>"
    assert payload == expected

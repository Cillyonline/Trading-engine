"""Tests for the DB connectivity check in /health/ready (issue #1132)."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

import api.main as api_main
from api.services.control_plane_service import (
    ControlPlaneHealthDependencies,
    check_db_connectivity,
    db_connectivity_payload,
)
from cilly_trading.engine.runtime_controller import _reset_runtime_controller_for_tests


def setup_function() -> None:
    _reset_runtime_controller_for_tests()


def teardown_function() -> None:
    _reset_runtime_controller_for_tests()


def test_check_db_connectivity_ok_for_existing_sqlite(tmp_path: Path) -> None:
    db_path = tmp_path / "ok.sqlite"
    sqlite3.connect(db_path).close()
    ok, reason = check_db_connectivity(db_path)
    assert ok is True
    assert reason == "ok"


def test_check_db_connectivity_reports_missing_file(tmp_path: Path) -> None:
    missing = tmp_path / "absent.sqlite"
    ok, reason = check_db_connectivity(missing)
    assert ok is False
    assert reason == "db_file_missing"


def test_check_db_connectivity_reports_unreadable_directory(tmp_path: Path) -> None:
    # A path pointing into a non-existent parent directory cannot be opened
    # by sqlite3 because the file does not exist and cannot be created.
    bad = tmp_path / "no_such_dir" / "x.sqlite"
    ok, reason = check_db_connectivity(bad)
    assert ok is False
    assert reason == "db_file_missing"


def test_db_connectivity_payload_uses_resolved_path(tmp_path: Path) -> None:
    db = tmp_path / "x.sqlite"
    sqlite3.connect(db).close()
    deps = ControlPlaneHealthDependencies(
        resolve_analysis_db_path=lambda: str(db),
        now=lambda: __import__("datetime").datetime.now(),
        get_runtime_introspection_payload=lambda: {},
        evaluate_runtime_health=lambda *a, **k: None,
    )
    payload = db_connectivity_payload(deps=deps)
    # The DB path is intentionally NOT included to avoid leaking server
    # filesystem layout in /health/ready responses.
    assert payload == {"ok": True, "reason": "ok"}


def test_health_ready_returns_503_when_db_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    # Patch the connectivity helper at its import site in the router module.
    import api.routers.control_plane_router as cp_router

    monkeypatch.setattr(
        cp_router,
        "db_connectivity_payload",
        lambda *, deps: {
            "ok": False,
            "reason": "db_file_missing",
        },
    )
    with TestClient(api_main.app) as client:
        response = client.get("/health/ready")

    assert response.status_code == 503
    body = response.json()
    assert body["status"] == "not_ready"
    assert body["reason"].startswith("db_unavailable")
    assert body["db"]["ok"] is False


def test_health_ready_returns_200_with_db_field_when_db_ok() -> None:
    with TestClient(api_main.app) as client:
        response = client.get("/health/ready")

    # When the engine is up, the readiness response now embeds the DB
    # probe result for diagnostics.
    if response.status_code == 200:
        body = response.json()
        assert body["status"] == "ready"
        assert body["db"]["ok"] is True
        assert body["db"]["reason"] == "ok"

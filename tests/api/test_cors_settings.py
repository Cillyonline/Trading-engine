from __future__ import annotations

import pytest

from api.composition.runtime_settings import _read_cors_origins


def test_read_cors_origins_returns_default_when_env_not_set(monkeypatch) -> None:
    monkeypatch.delenv("CILLY_CORS_ORIGINS", raising=False)
    origins = _read_cors_origins()
    assert origins == ["http://localhost:5173"]


def test_read_cors_origins_parses_single_explicit_origin(monkeypatch) -> None:
    monkeypatch.setenv("CILLY_CORS_ORIGINS", "https://app.example.com")
    origins = _read_cors_origins()
    assert origins == ["https://app.example.com"]


def test_read_cors_origins_parses_multiple_explicit_origins(monkeypatch) -> None:
    monkeypatch.setenv(
        "CILLY_CORS_ORIGINS", "https://app.example.com, https://admin.example.com"
    )
    origins = _read_cors_origins()
    assert origins == ["https://app.example.com", "https://admin.example.com"]


def test_read_cors_origins_rejects_wildcard(monkeypatch) -> None:
    monkeypatch.setenv("CILLY_CORS_ORIGINS", "*")
    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        _read_cors_origins()


def test_read_cors_origins_rejects_wildcard_in_list(monkeypatch) -> None:
    monkeypatch.setenv(
        "CILLY_CORS_ORIGINS", "https://app.example.com, *"
    )
    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        _read_cors_origins()


def test_read_cors_origins_strips_whitespace(monkeypatch) -> None:
    monkeypatch.setenv("CILLY_CORS_ORIGINS", "  https://app.example.com  ")
    origins = _read_cors_origins()
    assert origins == ["https://app.example.com"]


def test_read_cors_origins_ignores_empty_entries(monkeypatch) -> None:
    monkeypatch.setenv("CILLY_CORS_ORIGINS", "https://app.example.com,,")
    origins = _read_cors_origins()
    assert origins == ["https://app.example.com"]

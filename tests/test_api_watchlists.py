from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository


READ_ONLY_HEADERS = {api_main.ROLE_HEADER_NAME: "read_only"}
OPERATOR_HEADERS = {api_main.ROLE_HEADER_NAME: "operator"}
OWNER_HEADERS = {api_main.ROLE_HEADER_NAME: "owner"}


def _make_repo(tmp_path: Path) -> SqliteWatchlistRepository:
    return SqliteWatchlistRepository(db_path=tmp_path / "watchlists.db")


def test_watchlist_create_endpoint_persists_and_reads_back(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        create_response = client.post(
            "/watchlists",
            headers=OPERATOR_HEADERS,
            json={
                "watchlist_id": "tech-growth",
                "name": "Tech Growth",
                "symbols": ["NVDA", "MSFT", "AAPL"],
            },
        )
        read_response = client.get(
            "/watchlists/tech-growth",
            headers=READ_ONLY_HEADERS,
        )

    assert create_response.status_code == 200
    assert create_response.json() == {
        "watchlist_id": "tech-growth",
        "name": "Tech Growth",
        "symbols": ["NVDA", "MSFT", "AAPL"],
    }

    assert read_response.status_code == 200
    assert read_response.json() == create_response.json()


def test_watchlist_list_endpoint_is_deterministic(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="beta-list",
        name="Beta",
        symbols=["TSLA", "META"],
    )
    repo.create_watchlist(
        watchlist_id="alpha-list",
        name="Alpha",
        symbols=["MSFT", "AAPL"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/watchlists", headers=READ_ONLY_HEADERS)

    assert response.status_code == 200
    assert response.json() == {
        "items": [
            {
                "watchlist_id": "alpha-list",
                "name": "Alpha",
                "symbols": ["MSFT", "AAPL"],
            },
            {
                "watchlist_id": "beta-list",
                "name": "Beta",
                "symbols": ["TSLA", "META"],
            },
        ],
        "total": 2,
    }


def test_watchlist_update_endpoint_allows_owner_and_replaces_membership(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="swing-core",
        name="Swing Core",
        symbols=["AAPL", "MSFT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.put(
            "/watchlists/swing-core",
            headers=OWNER_HEADERS,
            json={
                "name": "Swing Updated",
                "symbols": ["NVDA", "AMD", "AAPL"],
            },
        )

    assert response.status_code == 200
    assert response.json() == {
        "watchlist_id": "swing-core",
        "name": "Swing Updated",
        "symbols": ["NVDA", "AMD", "AAPL"],
    }


def test_watchlist_delete_endpoint_removes_watchlist(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="to-delete",
        name="Delete Me",
        symbols=["BTC/USDT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        delete_response = client.delete(
            "/watchlists/to-delete",
            headers=OPERATOR_HEADERS,
        )
        read_response = client.get(
            "/watchlists/to-delete",
            headers=READ_ONLY_HEADERS,
        )

    assert delete_response.status_code == 200
    assert delete_response.json() == {
        "watchlist_id": "to-delete",
        "deleted": True,
    }
    assert read_response.status_code == 404
    assert read_response.json() == {"detail": "watchlist_not_found"}


def test_watchlist_create_rejects_invalid_payload_without_persisting(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists",
            headers=OPERATOR_HEADERS,
            json={
                "watchlist_id": "broken-list",
                "name": "Broken",
                "symbols": ["AAPL", " "],
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "watchlist symbols must not contain empty values"}
    assert repo.get_watchlist("broken-list") is None
    assert repo.list_watchlists() == []


def test_watchlist_update_rejects_invalid_payload_without_partial_persistence(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="core-list",
        name="Core",
        symbols=["AAPL", "MSFT"],
    )
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.put(
            "/watchlists/core-list",
            headers=OPERATOR_HEADERS,
            json={
                "name": "Core",
                "symbols": ["NVDA", "NVDA"],
            },
        )

    assert response.status_code == 422
    assert response.json() == {"detail": "watchlist name and symbols must remain unique"}

    stored = repo.get_watchlist("core-list")
    assert stored is not None
    assert stored.name == "Core"
    assert stored.symbols == ("AAPL", "MSFT")


def test_watchlist_endpoints_require_authenticated_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.get("/watchlists")

    assert response.status_code == 401
    assert response.json() == {"detail": "unauthorized"}


def test_watchlist_mutations_forbid_read_only_role(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    monkeypatch.setattr(api_main, "watchlist_repo", repo)
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")

    with TestClient(api_main.app) as client:
        response = client.post(
            "/watchlists",
            headers=READ_ONLY_HEADERS,
            json={
                "watchlist_id": "read-only-write",
                "name": "Read Only",
                "symbols": ["AAPL"],
            },
        )

    assert response.status_code == 403
    assert response.json() == {"detail": "forbidden"}
    assert repo.list_watchlists() == []

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from cilly_trading.repositories import Watchlist
from cilly_trading.repositories.watchlists_sqlite import SqliteWatchlistRepository


def _make_repo(tmp_path: Path) -> SqliteWatchlistRepository:
    db_path = tmp_path / "test_watchlists.db"
    return SqliteWatchlistRepository(db_path=db_path)


def test_create_and_get_watchlist_preserves_symbol_order(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    created = repo.create_watchlist(
        watchlist_id="wl-tech",
        name="Tech Leaders",
        symbols=["MSFT", "AAPL", "NVDA"],
    )

    assert created == Watchlist(
        watchlist_id="wl-tech",
        name="Tech Leaders",
        symbols=("MSFT", "AAPL", "NVDA"),
    )
    assert repo.get_watchlist("wl-tech") == created


def test_list_watchlists_is_deterministically_sorted(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.create_watchlist(watchlist_id="wl-z", name="Zulu", symbols=["ZBRA"])
    repo.create_watchlist(watchlist_id="wl-b", name="Bravo", symbols=["AMD"])
    repo.create_watchlist(watchlist_id="wl-a", name="Alpha", symbols=["AAPL"])

    items = repo.list_watchlists()

    assert [(item.watchlist_id, item.name) for item in items] == [
        ("wl-a", "Alpha"),
        ("wl-b", "Bravo"),
        ("wl-z", "Zulu"),
    ]


def test_update_watchlist_replaces_name_and_symbols(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-growth",
        name="Growth",
        symbols=["SHOP", "MELI"],
    )

    updated = repo.update_watchlist(
        watchlist_id="wl-growth",
        name="Growth Updated",
        symbols=["TSLA", "AMZN", "META"],
    )

    assert updated == Watchlist(
        watchlist_id="wl-growth",
        name="Growth Updated",
        symbols=("TSLA", "AMZN", "META"),
    )
    assert repo.get_watchlist("wl-growth") == updated


def test_delete_watchlist_removes_watchlist_and_symbols(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-delete",
        name="Delete Me",
        symbols=["IBM", "ORCL"],
    )

    assert repo.delete_watchlist("wl-delete") is True
    assert repo.delete_watchlist("wl-delete") is False
    assert repo.get_watchlist("wl-delete") is None
    assert repo.list_watchlists() == []


def test_create_watchlist_rejects_duplicate_identifier(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-dup",
        name="Primary",
        symbols=["AAPL"],
    )

    with pytest.raises(ValueError, match="unique"):
        repo.create_watchlist(
            watchlist_id="wl-dup",
            name="Secondary",
            symbols=["MSFT"],
        )

    assert repo.list_watchlists() == [
        Watchlist(watchlist_id="wl-dup", name="Primary", symbols=("AAPL",))
    ]


def test_create_watchlist_rejects_duplicate_name(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-first",
        name="Shared Name",
        symbols=["AAPL"],
    )

    with pytest.raises(ValueError, match="unique"):
        repo.create_watchlist(
            watchlist_id="wl-second",
            name="Shared Name",
            symbols=["MSFT"],
        )

    assert repo.get_watchlist("wl-second") is None


def test_update_watchlist_rejects_duplicate_name_without_partial_persist(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-one",
        name="One",
        symbols=["AAPL", "MSFT"],
    )
    repo.create_watchlist(
        watchlist_id="wl-two",
        name="Two",
        symbols=["NVDA"],
    )

    with pytest.raises(ValueError, match="unique"):
        repo.update_watchlist(
            watchlist_id="wl-two",
            name="One",
            symbols=["TSLA", "AMZN"],
        )

    assert repo.get_watchlist("wl-two") == Watchlist(
        watchlist_id="wl-two",
        name="Two",
        symbols=("NVDA",),
    )


def test_create_watchlist_rejects_empty_symbols_without_persisting_header(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    with pytest.raises(ValueError, match="must not be empty"):
        repo.create_watchlist(
            watchlist_id="wl-empty",
            name="Empty",
            symbols=[],
        )

    assert repo.get_watchlist("wl-empty") is None
    assert repo.list_watchlists() == []


def test_update_watchlist_rejects_empty_symbols_without_partial_persist(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    original = repo.create_watchlist(
        watchlist_id="wl-keep",
        name="Keep",
        symbols=["QQQ", "SPY"],
    )

    with pytest.raises(ValueError, match="must not be empty"):
        repo.update_watchlist(
            watchlist_id="wl-keep",
            name="Keep Changed",
            symbols=[],
        )

    assert repo.get_watchlist("wl-keep") == original


def test_create_watchlist_rollback_clears_header_on_symbol_membership_failure(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    with pytest.raises(ValueError, match="unique"):
        repo.create_watchlist(
            watchlist_id="wl-bad-membership",
            name="Bad Membership",
            symbols=["AAPL", "AAPL"],
        )

    assert repo.get_watchlist("wl-bad-membership") is None
    assert repo.list_watchlists() == []


def test_update_missing_watchlist_raises_keyerror(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    with pytest.raises(KeyError, match="watchlist not found"):
        repo.update_watchlist(
            watchlist_id="wl-missing",
            name="Missing",
            symbols=["AAPL"],
        )


def test_storage_uses_order_positions_for_symbol_reload(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.create_watchlist(
        watchlist_id="wl-order",
        name="Ordering",
        symbols=["MSFT", "AAPL", "NVDA"],
    )

    db_path = tmp_path / "test_watchlists.db"
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            """
            SELECT position, symbol
            FROM watchlist_symbols
            WHERE watchlist_id = ?
            ORDER BY position ASC;
            """,
            ("wl-order",),
        ).fetchall()
    finally:
        conn.close()

    assert rows == [(0, "MSFT"), (1, "AAPL"), (2, "NVDA")]

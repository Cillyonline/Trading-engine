from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "test_signals.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 0.9,
        "timestamp": "2025-01-01T00:00:00Z",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    base.update(overrides)
    return base


def test_save_signals_empty_list_is_noop(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals([])
    assert repo.list_signals() == []


def test_roundtrip_minimal_signal(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals([_base_signal(symbol="MSFT")])

    rows = repo.list_signals(limit=10)
    assert len(rows) == 1

    s = rows[0]
    assert s["symbol"] == "MSFT"
    assert s["strategy"] == "RSI2"
    assert s["direction"] == "long"
    assert s["score"] == 0.9
    assert s["timestamp"] == "2025-01-01T00:00:00Z"
    assert s["stage"] == "setup"
    assert s["timeframe"] == "D1"
    assert s["market_type"] == "stock"
    assert s["data_source"] == "yahoo"
    assert "confirmation_rule" not in s
    assert "entry_zone" not in s


def test_roundtrip_with_confirmation_rule(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals([_base_signal(confirmation_rule="close_above_ma")])

    s = repo.list_signals(limit=1)[0]
    assert s["confirmation_rule"] == "close_above_ma"


def test_roundtrip_with_entry_zone(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals(
        [
            _base_signal(
                entry_zone={"from_": 100.0, "to": 110.0},
            )
        ]
    )

    s = repo.list_signals(limit=1)[0]
    assert s["entry_zone"]["from_"] == 100.0
    assert s["entry_zone"]["to"] == 110.0


def test_list_signals_orders_by_newest_first(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals([_base_signal(symbol="FIRST")])
    repo.save_signals([_base_signal(symbol="SECOND")])

    rows = repo.list_signals(limit=10)
    assert [r["symbol"] for r in rows] == ["SECOND", "FIRST"]


def test_list_signals_respects_limit(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals([_base_signal(symbol="S1")])
    repo.save_signals([_base_signal(symbol="S2")])

    rows = repo.list_signals(limit=1)
    assert len(rows) == 1
    assert rows[0]["symbol"] == "S2"


def test_list_signals_limit_zero_returns_empty(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    repo.save_signals([_base_signal(symbol="X")])

    assert repo.list_signals(limit=0) == []


def test_save_signals_missing_required_key_raises_keyerror(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    invalid = _base_signal()
    invalid.pop("symbol")

    with pytest.raises(KeyError):
        repo.save_signals([invalid])


def test_read_signals_filters_and_sorting(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(
                symbol="AAA",
                strategy="RSI2",
                timeframe="D1",
                timestamp="2025-01-01T00:00:00+00:00",
            ),
            _base_signal(
                symbol="BBB",
                strategy="RSI2",
                timeframe="H1",
                timestamp="2025-01-02T00:00:00+00:00",
            ),
            _base_signal(
                symbol="CCC",
                strategy="TURTLE",
                timeframe="H1",
                timestamp="2025-01-03T00:00:00+00:00",
            ),
        ]
    )

    items, total = repo.read_signals(strategy="RSI2", preset="H1")
    assert total == 1
    assert items[0]["symbol"] == "BBB"

    items_start, total_start = repo.read_signals(from_=datetime.fromisoformat("2025-01-02T00:00:00+00:00"))
    assert total_start == 2
    assert [item["symbol"] for item in items_start] == ["CCC", "BBB"]

    items_end, total_end = repo.read_signals(to=datetime.fromisoformat("2025-01-02T00:00:00+00:00"))
    assert total_end == 2
    assert [item["symbol"] for item in items_end] == ["BBB", "AAA"]

    items_asc, total_asc = repo.read_signals(sort="created_at_asc", limit=10)
    assert total_asc == 3
    assert [item["symbol"] for item in items_asc] == ["AAA", "BBB", "CCC"]

from __future__ import annotations

from pathlib import Path

import pytest

from api.order_events_sqlite import SqliteOrderEventRepository as ApiCompatOrderEventRepository
from cilly_trading.repositories.order_events_sqlite import SqliteOrderEventRepository


def _make_repo(tmp_path: Path) -> SqliteOrderEventRepository:
    return SqliteOrderEventRepository(db_path=tmp_path / "order_events.db")


def _event(**overrides):
    base = {
        "run_id": "run-1",
        "order_id": "ord-1",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "state": "created",
        "event_timestamp": "2025-01-01T00:00:00+00:00",
        "event_sequence": 1,
        "metadata": {"source": "test"},
    }
    base.update(overrides)
    return base


def test_repository_persists_and_reads_order_events(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_events(
        [
            _event(order_id="ord-1", event_sequence=2, metadata={"b": 2, "a": 1}),
            _event(order_id="ord-1", event_sequence=1, metadata=None),
            _event(order_id="ord-2", symbol="MSFT", event_sequence=1),
        ]
    )

    items, total = repo.read_order_events(symbol="AAPL", limit=10, offset=0)

    assert total == 2
    assert [item["event_sequence"] for item in items] == [1, 2]
    assert items[0]["metadata"] is None
    assert items[1]["metadata"] == {"a": 1, "b": 2}


def test_repository_rejects_unknown_order_lifecycle_state(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    with pytest.raises(ValueError, match="invalid_order_lifecycle_state"):
        repo.save_events([_event(state="unknown")])

    assert repo.read_order_events()[1] == 0


def test_api_order_event_repository_import_remains_compatible() -> None:
    assert ApiCompatOrderEventRepository is SqliteOrderEventRepository

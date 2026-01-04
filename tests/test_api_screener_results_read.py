from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

import api.main as api_main
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "screener_results.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 50.0,
        "timestamp": "2025-01-01T00:00:00+00:00",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    base.update(overrides)
    return base


def test_read_screener_results_ordering_and_min_score(tmp_path: Path, monkeypatch) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="BBB", score=50.0, timestamp="2025-01-02T00:00:00+00:00"),
            _base_signal(symbol="AAA", score=50.0, timestamp="2025-01-03T00:00:00+00:00"),
            _base_signal(symbol="CCC", score=60.0, timestamp="2025-01-04T00:00:00+00:00"),
            _base_signal(symbol="DDD", score=40.0, timestamp="2025-01-05T00:00:00+00:00"),
            _base_signal(symbol="EEE", strategy="TURTLE", score=70.0),
            _base_signal(symbol="FFF", timeframe="H1", score=80.0),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get(
        "/screener/v2/results",
        params={
            "strategy": "RSI2",
            "timeframe": "D1",
            "min_score": 45.0,
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 3
    assert [item["symbol"] for item in payload["items"]] == ["CCC", "AAA", "BBB"]

    for item in payload["items"]:
        assert set(["symbol", "score", "strategy", "timeframe", "market_type", "created_at"]).issubset(
            item.keys()
        )


def test_read_screener_results_filters_strategy_and_timeframe(
    tmp_path: Path, monkeypatch
) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="AAA", strategy="TURTLE", timeframe="H1", score=10.0),
            _base_signal(symbol="BBB", strategy="TURTLE", timeframe="H1", score=20.0),
            _base_signal(symbol="AAC", strategy="TURTLE", timeframe="H1", score=20.0),
            _base_signal(symbol="DDD", strategy="RSI2", timeframe="H1", score=90.0),
            _base_signal(symbol="EEE", strategy="TURTLE", timeframe="D1", score=30.0),
        ]
    )

    monkeypatch.setattr(api_main, "signal_repo", repo)
    client = TestClient(api_main.app)

    response = client.get(
        "/screener/v2/results",
        params={
            "strategy": "TURTLE",
            "timeframe": "H1",
        },
    )
    assert response.status_code == 200
    payload = response.json()

    assert payload["total"] == 3
    assert [item["symbol"] for item in payload["items"]] == ["AAC", "BBB", "AAA"]

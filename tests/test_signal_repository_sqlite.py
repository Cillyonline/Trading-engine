from __future__ import annotations

import sqlite3
from datetime import datetime
from pathlib import Path

import pytest

from cilly_trading.models import compute_signal_id
from cilly_trading.db import init_db
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "test_signals.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "ingestion_run_id": "test-run-001",
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
    signal = _base_signal(symbol="MSFT")

    repo.save_signals([signal])

    rows = repo.list_signals(limit=10)
    assert len(rows) == 1

    s = rows[0]
    assert s["signal_id"] == compute_signal_id(signal)
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


def test_save_signals_missing_ingestion_run_id_raises(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)

    invalid = _base_signal()
    invalid.pop("ingestion_run_id")

    with pytest.raises(ValueError, match="ingestion_run_id is required"):
        repo.save_signals([invalid])

    assert repo.list_signals(limit=10) == []


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

    items, total = repo.read_signals(strategy="RSI2", timeframe="H1")
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


def test_read_screener_results_respects_bounds(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    repo.save_signals(
        [
            _base_signal(symbol="AAA", score=40.0, timestamp="2025-01-01T00:00:00+00:00"),
            _base_signal(symbol="BBB", score=60.0, timestamp="2025-01-02T00:00:00+00:00"),
            _base_signal(symbol="CCC", score=60.0, timestamp="2025-01-03T00:00:00+00:00"),
            _base_signal(symbol="DDD", score=80.0, timestamp="2025-01-04T00:00:00+00:00"),
        ]
    )

    items, total = repo.read_screener_results(
        strategy="RSI2",
        timeframe="D1",
        limit=2,
        offset=1,
    )

    assert total == 4
    assert [item["symbol"] for item in items] == ["BBB", "CCC"]


def test_save_signals_deduplicates_same_analysis_run_and_signal_id(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    signal = _base_signal(
        analysis_run_id="analysis-run-1",
        signal_id="signal-001",
    )

    repo.save_signals([signal])
    repo.save_signals([signal])

    rows = repo.list_signals(limit=10)
    assert len(rows) == 1
    assert rows[0]["signal_id"] == "signal-001"

    conn = sqlite3.connect(tmp_path / "test_signals.db")
    try:
        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE analysis_run_id = ? AND signal_id = ?;
            """,
            ("analysis-run-1", "signal-001"),
        ).fetchone()[0]
    finally:
        conn.close()

    assert row_count == 1


def test_save_signals_deduplicates_same_ingestion_run_and_signal_id_across_analysis_runs(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    first = _base_signal(
        ingestion_run_id="ing-dup-001",
        analysis_run_id="analysis-run-manual",
        signal_id="signal-dup-001",
        symbol="AMD",
        timestamp="2025-01-03T00:00:00+00:00",
    )
    second = _base_signal(
        ingestion_run_id="ing-dup-001",
        analysis_run_id="analysis-run-watchlist",
        signal_id="signal-dup-001",
        symbol="AMD",
        timestamp="2025-01-03T00:00:00+00:00",
    )

    repo.save_signals([first])
    repo.save_signals([second])

    rows = repo.list_signals(limit=10)
    assert len(rows) == 1
    assert rows[0]["signal_id"] == "signal-dup-001"

    conn = sqlite3.connect(tmp_path / "test_signals.db")
    try:
        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE ingestion_run_id = ? AND signal_id = ?;
            """,
            ("ing-dup-001", "signal-dup-001"),
        ).fetchone()[0]
    finally:
        conn.close()

    assert row_count == 1


def test_read_signals_unfiltered_deduplicates_same_signal_across_ingestion_runs(
    tmp_path: Path,
) -> None:
    repo = _make_repo(tmp_path)
    first = _base_signal(
        ingestion_run_id="ing-run-001",
        analysis_run_id="analysis-run-001",
        symbol="AAPL",
        timestamp="2025-01-03T00:00:00+00:00",
    )
    second = _base_signal(
        ingestion_run_id="ing-run-002",
        analysis_run_id="analysis-run-002",
        symbol="AAPL",
        timestamp="2025-01-03T00:00:00+00:00",
    )

    repo.save_signals([first])
    repo.save_signals([second])

    all_items, all_total = repo.read_signals(limit=20, offset=0)
    run_one_items, run_one_total = repo.read_signals(
        ingestion_run_id="ing-run-001",
        limit=20,
        offset=0,
    )
    run_two_items, run_two_total = repo.read_signals(
        ingestion_run_id="ing-run-002",
        limit=20,
        offset=0,
    )

    assert all_total == 1
    assert len(all_items) == 1
    assert all_items[0]["signal_id"] == compute_signal_id(first)

    assert run_one_total == 1
    assert run_two_total == 1
    assert run_one_items[0]["signal_id"] == compute_signal_id(first)
    assert run_two_items[0]["signal_id"] == compute_signal_id(second)

    conn = sqlite3.connect(tmp_path / "test_signals.db")
    try:
        signal_id = compute_signal_id(first)
        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE signal_id = ?;
            """,
            (signal_id,),
        ).fetchone()[0]
        ingestion_count = conn.execute(
            """
            SELECT COUNT(DISTINCT ingestion_run_id)
            FROM signals
            WHERE signal_id = ?;
            """,
            (signal_id,),
        ).fetchone()[0]
    finally:
        conn.close()

    assert row_count == 2
    assert ingestion_count == 2


def test_repo_init_migrates_legacy_duplicate_ingestion_run_signal_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "legacy_dirty_signals.db"
    init_db(db_path)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            INSERT INTO signals (
                signal_id,
                analysis_run_id,
                ingestion_run_id,
                symbol,
                strategy,
                direction,
                score,
                timestamp,
                stage,
                timeframe,
                market_type,
                data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "sig-legacy-001",
                "analysis-run-manual",
                "ing-legacy-001",
                "AAPL",
                "RSI2",
                "long",
                100.0,
                "2025-01-03T00:00:00+00:00",
                "setup",
                "D1",
                "stock",
                "yahoo",
            ),
        )
        conn.execute(
            """
            INSERT INTO signals (
                signal_id,
                analysis_run_id,
                ingestion_run_id,
                symbol,
                strategy,
                direction,
                score,
                timestamp,
                stage,
                timeframe,
                market_type,
                data_source
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                "sig-legacy-001",
                "analysis-run-watchlist",
                "ing-legacy-001",
                "AAPL",
                "RSI2",
                "long",
                100.0,
                "2025-01-03T00:00:00+00:00",
                "setup",
                "D1",
                "stock",
                "yahoo",
            ),
        )
        conn.commit()
    finally:
        conn.close()

    repo = SqliteSignalRepository(db_path=db_path)

    items, total = repo.read_signals(ingestion_run_id="ing-legacy-001", limit=20, offset=0)
    assert total == 1
    assert len(items) == 1
    assert items[0]["signal_id"] == "sig-legacy-001"

    conn = sqlite3.connect(db_path)
    try:
        row_count = conn.execute(
            """
            SELECT COUNT(*)
            FROM signals
            WHERE ingestion_run_id = ? AND signal_id = ?;
            """,
            ("ing-legacy-001", "sig-legacy-001"),
        ).fetchone()[0]
    finally:
        conn.close()

    assert row_count == 1

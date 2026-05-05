"""Concurrency tests for SQLite-backed repositories (issue #1134).

Verifies that race conditions in `save_signals` are guarded by the
unique index on ``(ingestion_run_id, signal_id)`` so multiple writers
producing the same signal end up with exactly one row, rather than
duplicates or corrupted partial rows.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import pytest

from cilly_trading.models import Signal, compute_signal_id
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


def _make_signal(*, ingestion_run_id: str = "ingest-1") -> Signal:
    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "stage": "setup",
        "timestamp": "2026-05-04T10:00:00+00:00",
        "ingestion_run_id": ingestion_run_id,
        "analysis_run_id": "run-1",
        "score": 0.42,
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    signal["signal_id"] = compute_signal_id(signal)
    return signal


def test_concurrent_identical_signal_writes_dedup_to_one_row(tmp_path: Path) -> None:
    """Many threads racing to write the same signal must produce one row."""

    repo = SqliteSignalRepository(db_path=tmp_path / "signals.sqlite")
    signal = _make_signal()

    def _writer() -> None:
        repo.save_signals([signal])

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_writer) for _ in range(32)]
        for f in as_completed(futures):
            f.result()  # surface any exception

    rows = repo.list_signals(limit=1000)
    matching = [
        r
        for r in rows
        if r.get("signal_id") == signal["signal_id"]
        and r.get("ingestion_run_id") == signal["ingestion_run_id"]
    ]
    assert len(matching) == 1, f"expected exactly 1 signal row, got {len(matching)}"


def test_concurrent_distinct_signal_writes_all_persist(tmp_path: Path) -> None:
    """Distinct signals from many writers must all be persisted."""

    repo = SqliteSignalRepository(db_path=tmp_path / "signals.sqlite")

    signals: list[Signal] = []
    for idx in range(16):
        signal: Signal = {
            "symbol": f"SYM{idx:02d}",
            "strategy": "RSI2",
            "direction": "long",
            "stage": "setup",
            "timestamp": "2026-05-04T10:00:00+00:00",
            "ingestion_run_id": "ingest-distinct",
            "analysis_run_id": "run-1",
            "score": 0.42,
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        }
        signal["signal_id"] = compute_signal_id(signal)
        signals.append(signal)

    def _writer(s: Signal) -> None:
        repo.save_signals([s])

    with ThreadPoolExecutor(max_workers=8) as pool:
        futures = [pool.submit(_writer, s) for s in signals]
        for f in as_completed(futures):
            f.result()

    rows = repo.list_signals(limit=1000)
    persisted_ids = {
        r.get("signal_id")
        for r in rows
        if r.get("ingestion_run_id") == "ingest-distinct"
    }
    expected_ids = {s["signal_id"] for s in signals}
    assert persisted_ids == expected_ids


def test_concurrent_mixed_dedup_and_distinct_behaves_correctly(tmp_path: Path) -> None:
    """Workload mixing duplicates and unique signals respects the unique index."""

    repo = SqliteSignalRepository(db_path=tmp_path / "signals.sqlite")
    duplicate = _make_signal(ingestion_run_id="ingest-mixed")

    distinct: list[Signal] = []
    for idx in range(5):
        s: Signal = {
            "symbol": f"X{idx:02d}",
            "strategy": "RSI2",
            "direction": "long",
            "stage": "setup",
            "timestamp": "2026-05-04T10:00:00+00:00",
            "ingestion_run_id": "ingest-mixed",
            "analysis_run_id": "run-1",
            "score": 0.42,
            "timeframe": "D1",
            "market_type": "stock",
            "data_source": "yahoo",
        }
        s["signal_id"] = compute_signal_id(s)
        distinct.append(s)

    def _writer_duplicate() -> None:
        repo.save_signals([duplicate])

    def _writer_distinct(s: Signal) -> None:
        repo.save_signals([s])

    with ThreadPoolExecutor(max_workers=6) as pool:
        futures = []
        for _ in range(12):
            futures.append(pool.submit(_writer_duplicate))
        for s in distinct:
            futures.append(pool.submit(_writer_distinct, s))
        for f in as_completed(futures):
            f.result()

    rows = [
        r
        for r in repo.list_signals(limit=1000)
        if r.get("ingestion_run_id") == "ingest-mixed"
    ]
    persisted_ids = {r.get("signal_id") for r in rows}
    expected_ids = {duplicate["signal_id"]} | {s["signal_id"] for s in distinct}
    assert persisted_ids == expected_ids
    assert len(rows) == len(expected_ids)

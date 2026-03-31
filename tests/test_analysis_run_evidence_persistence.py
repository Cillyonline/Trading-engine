from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    created_at: str,
    symbols: list[str],
    timeframe: str = "D1",
    source: str = "test",
    fingerprint_hash: str | None = None,
) -> None:
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO ingestion_runs (
            ingestion_run_id,
            created_at,
            source,
            symbols_json,
            timeframe,
            fingerprint_hash
        )
        VALUES (?, ?, ?, ?, ?, ?);
        """,
        (
            ingestion_run_id,
            created_at,
            source,
            json.dumps(symbols),
            timeframe,
            fingerprint_hash,
        ),
    )
    conn.commit()
    conn.close()


def test_analysis_run_repository_writes_deterministic_evidence_bundle(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence_dir = tmp_path / "evidence"
    monkeypatch.setenv("CILLY_ANALYSIS_EVIDENCE_DIR", str(evidence_dir))

    db_path = tmp_path / "analysis.db"
    repo = SqliteAnalysisRunRepository(db_path=db_path)
    _insert_ingestion_run(
        db_path,
        "ingestion-001",
        created_at="2026-03-31T06:05:00+00:00",
        symbols=["AAPL"],
        fingerprint_hash="snapshot-fingerprint-001",
    )

    saved = repo.save_run(
        analysis_run_id="run-001",
        ingestion_run_id="ingestion-001",
        request_payload={
            "ingestion_run_id": "ingestion-001",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "market_type": "stock",
            "lookback_days": 200,
        },
        result_payload={
            "analysis_run_id": "run-001",
            "ingestion_run_id": "ingestion-001",
            "symbol": "AAPL",
            "strategy": "RSI2",
            "signals": [],
        },
    )

    evidence = saved["evidence"]
    assert evidence["review_week"] == "2026-W14"

    artifact_dir = Path(evidence["artifact_dir"])
    assert artifact_dir == evidence_dir / "2026-W14" / "run-001"

    evidence_payload = json.loads(Path(evidence["evidence_file"]).read_text(encoding="utf-8"))
    assert evidence_payload["artifact"] == "analysis_run_evidence"
    assert evidence_payload["workflow"]["endpoint"] == "POST /analysis/run"
    assert evidence_payload["workflow"]["kind"] == "single_symbol_analysis"
    assert evidence_payload["workflow"]["outcome_classification"] == "empty_success"
    assert evidence_payload["workflow"]["scope"] == {
        "symbol": "AAPL",
        "strategy": "RSI2",
    }
    assert evidence_payload["snapshot"]["ingestion_run_id"] == "ingestion-001"
    assert evidence_payload["snapshot"]["fingerprint_hash"] == "snapshot-fingerprint-001"
    assert evidence_payload["snapshot"]["symbols"] == ["AAPL"]
    assert evidence_payload["comparison"]["comparison_scope"] == "analysis:AAPL:RSI2"
    assert evidence_payload["comparison"]["request_sha256"]
    assert evidence_payload["comparison"]["result_sha256"]

    operator_review_payload = json.loads(
        Path(evidence["operator_review_file"]).read_text(encoding="utf-8")
    )
    assert operator_review_payload["artifact"] == "operator_review"
    assert operator_review_payload["workflow_kind"] == "single_symbol_analysis"
    assert operator_review_payload["outcome_classification"] == "empty_success"
    assert operator_review_payload["counts"] == {"signals": 0}
    assert operator_review_payload["comparison"]["review_week"] == "2026-W14"

    assert Path(evidence["evidence_sha256_file"]).read_text(encoding="utf-8").strip()
    assert Path(evidence["operator_review_sha256_file"]).read_text(encoding="utf-8").strip()


def test_analysis_run_repository_duplicate_save_reuses_same_evidence_artifacts(
    tmp_path: Path,
    monkeypatch,
) -> None:
    evidence_dir = tmp_path / "evidence"
    monkeypatch.setenv("CILLY_ANALYSIS_EVIDENCE_DIR", str(evidence_dir))

    db_path = tmp_path / "analysis.db"
    repo = SqliteAnalysisRunRepository(db_path=db_path)
    _insert_ingestion_run(
        db_path,
        "ingestion-001",
        created_at="2026-03-31T06:05:00+00:00",
        symbols=["AAPL", "MSFT"],
        fingerprint_hash="snapshot-fingerprint-001",
    )

    request_payload = {
        "workflow": "watchlist_execution",
        "ingestion_run_id": "ingestion-001",
        "watchlist_id": "core-tech",
        "symbols": ["AAPL", "MSFT"],
        "strategies": ["RSI2", "TURTLE"],
        "market_type": "stock",
        "lookback_days": 200,
        "min_score": "30",
    }
    result_payload = {
        "analysis_run_id": "run-002",
        "ingestion_run_id": "ingestion-001",
        "watchlist_id": "core-tech",
        "watchlist_name": "Core Tech",
        "market_type": "stock",
        "ranked_results": [
            {
                "rank": 1,
                "symbol": "AAPL",
                "score": 88.0,
                "signal_strength": 0.9,
                "setups": [],
            }
        ],
        "failures": [
            {
                "symbol": "MSFT",
                "code": "snapshot_data_invalid",
                "detail": "snapshot data unavailable or invalid for symbol",
            }
        ],
    }

    first = repo.save_run(
        analysis_run_id="run-002",
        ingestion_run_id="ingestion-001",
        request_payload=request_payload,
        result_payload=result_payload,
    )
    second = repo.save_run(
        analysis_run_id="run-002",
        ingestion_run_id="ingestion-001",
        request_payload=request_payload,
        result_payload=result_payload,
    )

    assert first["evidence"] == second["evidence"]
    evidence_path = Path(first["evidence"]["evidence_file"])
    review_path = Path(first["evidence"]["operator_review_file"])
    evidence_hash_path = Path(first["evidence"]["evidence_sha256_file"])
    review_hash_path = Path(first["evidence"]["operator_review_sha256_file"])

    first_evidence_mtime = evidence_path.stat().st_mtime_ns
    first_review_mtime = review_path.stat().st_mtime_ns
    first_evidence_hash_mtime = evidence_hash_path.stat().st_mtime_ns
    first_review_hash_mtime = review_hash_path.stat().st_mtime_ns
    first_evidence_bytes = evidence_path.read_bytes()
    first_review_bytes = review_path.read_bytes()
    first_evidence_hash_bytes = evidence_hash_path.read_bytes()
    first_review_hash_bytes = review_hash_path.read_bytes()

    reloaded_once = repo.get_run("run-002")
    reloaded_twice = repo.get_run("run-002")

    assert reloaded_once is not None
    assert reloaded_twice is not None
    assert reloaded_once["evidence"] == first["evidence"]
    assert reloaded_twice["evidence"] == first["evidence"]
    assert evidence_path.stat().st_mtime_ns == first_evidence_mtime
    assert review_path.stat().st_mtime_ns == first_review_mtime
    assert evidence_hash_path.stat().st_mtime_ns == first_evidence_hash_mtime
    assert review_hash_path.stat().st_mtime_ns == first_review_hash_mtime
    assert evidence_path.read_bytes() == first_evidence_bytes
    assert review_path.read_bytes() == first_review_bytes
    assert evidence_hash_path.read_bytes() == first_evidence_hash_bytes
    assert review_hash_path.read_bytes() == first_review_hash_bytes

    evidence_payload = json.loads(
        Path(first["evidence"]["evidence_file"]).read_text(encoding="utf-8")
    )
    operator_review_payload = json.loads(
        Path(first["evidence"]["operator_review_file"]).read_text(encoding="utf-8")
    )

    assert evidence_payload["workflow"]["kind"] == "watchlist_execution"
    assert evidence_payload["workflow"]["outcome_classification"] == "isolated_symbol_failure"
    assert evidence_payload["workflow"]["scope"] == {
        "watchlist_id": "core-tech",
        "watchlist_name": "Core Tech",
    }
    assert evidence_payload["comparison"]["comparison_scope"] == "watchlist:core-tech"

    assert operator_review_payload["workflow_kind"] == "watchlist_execution"
    assert operator_review_payload["outcome_classification"] == "isolated_symbol_failure"
    assert operator_review_payload["counts"] == {
        "ranked_results": 1,
        "failures": 1,
    }

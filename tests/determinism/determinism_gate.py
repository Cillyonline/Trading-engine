from __future__ import annotations

import hashlib
import json
import sqlite3
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Sequence

from cilly_trading.engine.core import EngineConfig, add_signal_ids, compute_analysis_run_id, run_watchlist_analysis
from cilly_trading.repositories.analysis_runs_sqlite import SqliteAnalysisRunRepository
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies.rsi2 import Rsi2Strategy


@dataclass(frozen=True)
class GateResult:
    passed: bool
    run_hashes: Sequence[str]
    artifact_paths: Sequence[Path]
    artifact_contents: Sequence[bytes]
    db_check_status: str
    deviations: Sequence[Dict[str, Any]]
    deviation_file: Path | None


def stable_json_dumps(payload: Any) -> str:
    return json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _insert_ingestion_run(
    db_path: Path,
    ingestion_run_id: str,
    *,
    symbols: list[str],
    timeframe: str = "D1",
    source: str = "determinism_gate",
    created_at: str = "2025-01-01T00:00:00+00:00",
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
            json.dumps(symbols, separators=(",", ":"), ensure_ascii=False),
            timeframe,
            None,
        ),
    )
    conn.commit()
    conn.close()


def _insert_snapshot_rows(
    db_path: Path,
    ingestion_run_id: str,
    symbol: str,
    timeframe: str,
    rows: list[tuple[int, float, float, float, float, float]],
) -> None:
    conn = sqlite3.connect(db_path)
    conn.executemany(
        """
        INSERT INTO ohlcv_snapshots (
            ingestion_run_id,
            symbol,
            timeframe,
            ts,
            open,
            high,
            low,
            close,
            volume
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        [
            (
                ingestion_run_id,
                symbol,
                timeframe,
                ts,
                open_,
                high,
                low,
                close,
                volume,
            )
            for ts, open_, high, low, close, volume in rows
        ],
    )
    conn.commit()
    conn.close()


def _prepare_snapshot_db(db_path: Path, ingestion_run_id: str) -> None:
    _insert_ingestion_run(db_path, ingestion_run_id, symbols=["AAPL"], timeframe="D1")
    rows = [
        (1735689600000, 102.0, 103.0, 100.0, 100.0, 1000.0),
        (1735776000000, 100.0, 101.0, 90.0, 90.0, 1000.0),
        (1735862400000, 90.0, 91.0, 80.0, 80.0, 1000.0),
        (1735948800000, 80.0, 81.0, 70.0, 70.0, 1000.0),
    ]
    _insert_snapshot_rows(db_path, ingestion_run_id, "AAPL", "D1", rows)


def _build_run_payload(ingestion_run_id: str) -> Dict[str, Any]:
    return {
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "market_type": "stock",
        "lookback_days": 200,
    }


def _run_analysis_once(db_path: Path, ingestion_run_id: str) -> Dict[str, Any]:
    signal_repo = SqliteSignalRepository(db_path=db_path)
    engine_config = EngineConfig(
        timeframe="D1",
        lookback_days=200,
        market_type="stock",
        data_source="yahoo",
    )
    strategy = Rsi2Strategy()
    strategy_configs = {"RSI2": {}}

    signals = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[strategy],
        engine_config=engine_config,
        strategy_configs=strategy_configs,
        signal_repo=signal_repo,
        ingestion_run_id=ingestion_run_id,
        db_path=db_path,
        snapshot_only=True,
    )

    filtered_signals = [
        s for s in signals if s.get("symbol") == "AAPL" and s.get("strategy") == "RSI2"
    ]
    enriched_signals = add_signal_ids(filtered_signals)

    run_request_payload = _build_run_payload(ingestion_run_id)
    analysis_run_id = compute_analysis_run_id(run_request_payload)

    return {
        "analysis_run_id": analysis_run_id,
        "ingestion_run_id": ingestion_run_id,
        "symbol": "AAPL",
        "strategy": "RSI2",
        "signals": enriched_signals,
    }


def run_gate(*, artifact_dir: Path, runs: int = 3) -> GateResult:
    if runs < 3:
        raise ValueError("runs must be >= 3")

    artifact_dir.mkdir(parents=True, exist_ok=True)

    run_hashes: List[str] = []
    artifact_paths: List[Path] = []
    artifact_contents: List[bytes] = []
    deviations: List[Dict[str, Any]] = []
    db_check_status = "PASS"

    for run_index in range(1, runs + 1):
        analysis_db_path = artifact_dir / f"analysis_run_{run_index}.db"
        analysis_repo = SqliteAnalysisRunRepository(db_path=analysis_db_path)

        ingestion_run_id = "determinism-ingestion-0001"
        _prepare_snapshot_db(analysis_db_path, ingestion_run_id)

        response_payload = _run_analysis_once(analysis_db_path, ingestion_run_id)
        run_request_payload = _build_run_payload(ingestion_run_id)
        analysis_run_id = response_payload["analysis_run_id"]

        analysis_repo.save_run(
            analysis_run_id=analysis_run_id,
            ingestion_run_id=ingestion_run_id,
            request_payload=run_request_payload,
            result_payload=response_payload,
        )

        reloaded = analysis_repo.get_run(analysis_run_id)
        if reloaded is None:
            db_check_status = "FAIL"
            deviations.append(
                {
                    "type": "db_reload_missing",
                    "run": run_index,
                    "analysis_run_id": analysis_run_id,
                }
            )
        else:
            original_json = stable_json_dumps(response_payload)
            reloaded_json = stable_json_dumps(reloaded["result"])
            if original_json != reloaded_json:
                db_check_status = "FAIL"
                deviations.append(
                    {
                        "type": "db_reload_mismatch",
                        "run": run_index,
                        "analysis_run_id": analysis_run_id,
                        "original_sha256": _sha256_text(original_json),
                        "reloaded_sha256": _sha256_text(reloaded_json),
                    }
                )

        output_json = stable_json_dumps(response_payload)
        artifact_path = artifact_dir / f"analysis_output_run_{run_index}.json"
        artifact_path.write_text(output_json, encoding="utf-8")
        output_bytes = artifact_path.read_bytes()
        artifact_paths.append(artifact_path)
        artifact_contents.append(output_bytes)
        run_hashes.append(_sha256_text(output_json))

    baseline_bytes = artifact_contents[0]
    baseline_hash = run_hashes[0]
    for idx, (run_hash, run_bytes) in enumerate(
        zip(run_hashes[1:], artifact_contents[1:], strict=True),
        start=2,
    ):
        if run_bytes != baseline_bytes:
            mismatch_index = next(
                (
                    i
                    for i, (left, right) in enumerate(
                        zip(baseline_bytes, run_bytes, strict=False)
                    )
                    if left != right
                ),
                None,
            )
            if mismatch_index is None and len(run_bytes) != len(baseline_bytes):
                mismatch_index = min(len(run_bytes), len(baseline_bytes))

            context_window = None
            if mismatch_index is not None:
                start = max(0, mismatch_index - 12)
                end = min(max(len(run_bytes), len(baseline_bytes)), mismatch_index + 12)
                context_window = {
                    "offset": mismatch_index,
                    "baseline_context": baseline_bytes[start:end].hex(),
                    "actual_context": run_bytes[start:end].hex(),
                }

            deviations.append(
                {
                    "type": "output_mismatch",
                    "run": idx,
                    "expected_sha256": baseline_hash,
                    "actual_sha256": run_hash,
                    "artifact": str(artifact_paths[idx - 1]),
                    "byte_mismatch": context_window,
                }
            )

    deviation_file: Path | None = None
    if deviations:
        deviation_file = artifact_dir / "determinism_deviations.json"
        deviation_file.write_text(
            stable_json_dumps(
                {
                    "runs": runs,
                    "db_check_status": db_check_status,
                    "deviations": deviations,
                }
            ),
            encoding="utf-8",
        )

    passed = not deviations
    return GateResult(
        passed=passed,
        run_hashes=run_hashes,
        artifact_paths=artifact_paths,
        artifact_contents=artifact_contents,
        db_check_status=db_check_status,
        deviations=deviations,
        deviation_file=deviation_file,
    )


def main() -> int:
    artifact_dir = Path("tests/determinism/artifacts")
    result = run_gate(artifact_dir=artifact_dir, runs=3)

    if result.passed:
        print("DETERMINISM_GATE: PASS (runs=3)")
        return 0

    print("DETERMINISM_GATE: FAIL (runs=3)")
    if result.deviation_file is not None:
        print(f"DETERMINISM_GATE: deviations={result.deviation_file}")
    return 1


if __name__ == "__main__":
    sys.exit(main())

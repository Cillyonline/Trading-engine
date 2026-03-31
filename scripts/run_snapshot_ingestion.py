from __future__ import annotations

import argparse
import importlib.util
import json
import os
import sys
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cilly_trading.repositories.snapshot_ingestion_sqlite import (  # noqa: E402
    SqliteSnapshotIngestionRepository,
)


def _load_snapshot_job_module():
    module_path = (
        ROOT
        / "src"
        / "cilly_trading"
        / "engine"
        / "data"
        / "snapshot_ingestion_job.py"
    )
    spec = importlib.util.spec_from_file_location("snapshot_ingestion_job_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load snapshot_ingestion_job module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_job_module = _load_snapshot_job_module()
MAX_SNAPSHOT_CANDLES_PER_SYMBOL = _job_module.MAX_SNAPSHOT_CANDLES_PER_SYMBOL
SnapshotIngestionJob = _job_module.SnapshotIngestionJob
SnapshotIngestionJobError = _job_module.SnapshotIngestionJobError
SnapshotIngestionJobRequest = _job_module.SnapshotIngestionJobRequest
build_default_snapshot_provider_registry = (
    _job_module.build_default_snapshot_provider_registry
)
DEFAULT_EVIDENCE_DIR = ROOT / "runs" / "snapshot_ingestion"
DEFAULT_LOCK_FILE_NAME = "snapshot-ingestion.lock"
DEFAULT_SCHEDULE_NAME = "server-daily-d1"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run the bounded server-side snapshot ingestion job. "
            "This job is limited to non-live D1 snapshot creation."
        )
    )
    parser.add_argument(
        "--symbols",
        required=True,
        help="Comma-separated symbol list, for example AAPL,MSFT.",
    )
    parser.add_argument(
        "--timeframe",
        default="D1",
        help="Snapshot timeframe. Only D1 is supported.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=90,
        help=(
            "Maximum candles to ingest per symbol. "
            f"Must be between 1 and {MAX_SNAPSHOT_CANDLES_PER_SYMBOL}."
        ),
    )
    parser.add_argument(
        "--provider",
        default="yfinance",
        help="Bounded provider name. Default: yfinance.",
    )
    parser.add_argument(
        "--db-path",
        default=str(ROOT / "cilly_trading.db"),
        help="SQLite database path.",
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(DEFAULT_EVIDENCE_DIR),
        help=(
            "Directory for per-run success/failure evidence JSON files. "
            "Default: runs/snapshot_ingestion."
        ),
    )
    parser.add_argument(
        "--lock-file",
        default=None,
        help=(
            "Exclusive lock file used to prevent overlapping scheduled runs. "
            "Defaults to <evidence-dir>/snapshot-ingestion.lock."
        ),
    )
    parser.add_argument(
        "--schedule-name",
        default=DEFAULT_SCHEDULE_NAME,
        help=(
            "Server-side schedule label recorded in evidence output. "
            f"Default: {DEFAULT_SCHEDULE_NAME}."
        ),
    )
    return parser.parse_args()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _build_requested_payload(args: argparse.Namespace, *, symbols: tuple[str, ...]) -> dict[str, Any]:
    return {
        "db_path": str(Path(args.db_path)),
        "limit": args.limit,
        "provider_name": args.provider,
        "schedule_name": args.schedule_name,
        "symbols": list(symbols),
        "timeframe": args.timeframe,
    }


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_json_stream(stream, payload: dict[str, Any]) -> None:
    stream.write(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n")


def _failure_evidence_path(evidence_dir: Path, attempted_at: datetime) -> Path:
    stamp = attempted_at.strftime("%Y%m%dT%H%M%SZ")
    return evidence_dir / f"snapshot-ingestion-failed-{stamp}.json"


def _success_evidence_path(evidence_dir: Path, ingestion_run_id: str) -> Path:
    return evidence_dir / f"ingestion-run-{ingestion_run_id}.json"


def _acquire_lock(lock_path: Path, payload: dict[str, Any]) -> bool:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        descriptor = os.open(
            str(lock_path),
            os.O_CREAT | os.O_EXCL | os.O_WRONLY,
        )
    except FileExistsError:
        return False

    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n")
    return True


def _release_lock(lock_path: Path) -> None:
    try:
        lock_path.unlink()
    except FileNotFoundError:
        return


def main() -> int:
    args = _parse_args()
    attempted_at = _utc_now()
    evidence_dir = Path(args.evidence_dir)
    lock_path = Path(args.lock_file) if args.lock_file else evidence_dir / DEFAULT_LOCK_FILE_NAME
    symbols = tuple(part.strip() for part in args.symbols.split(",") if part.strip())
    requested = _build_requested_payload(args, symbols=symbols)

    lock_created = _acquire_lock(
        lock_path,
        {
            "attempted_at": attempted_at.isoformat(),
            "lock_file": str(lock_path),
            "pid": os.getpid(),
            "requested": requested,
            "status": "running",
        },
    )
    if not lock_created:
        payload = {
            "attempted_at": attempted_at.isoformat(),
            "code": "snapshot_ingestion_already_running",
            "detail": "another scheduled ingestion run is already holding the lock",
            "lock_file": str(lock_path),
            "requested": requested,
            "status": "failed",
        }
        evidence_file = _failure_evidence_path(evidence_dir, attempted_at)
        payload["evidence_file"] = str(evidence_file)
        _write_json_file(evidence_file, payload)
        _write_json_stream(sys.stderr, payload)
        return 1

    request = SnapshotIngestionJobRequest(
        symbols=symbols,
        timeframe=args.timeframe,
        limit=args.limit,
        provider_name=args.provider,
    )
    job = SnapshotIngestionJob(
        repository=SqliteSnapshotIngestionRepository(db_path=Path(args.db_path)),
        provider_registry=build_default_snapshot_provider_registry(),
    )
    failure_payload: dict[str, Any] | None = None

    try:
        result = job.run(request)
    except SnapshotIngestionJobError as exc:
        failure_payload = {
            "attempted_at": attempted_at.isoformat(),
            "code": exc.code,
            "detail": exc.detail,
            "lock_file": str(lock_path),
            "provider_name": exc.provider_name,
            "requested": requested,
            "status": "failed",
            "symbol": exc.symbol,
        }
    except Exception as exc:
        failure_payload = {
            "attempted_at": attempted_at.isoformat(),
            "code": "snapshot_ingestion_unhandled_error",
            "detail": f"{type(exc).__name__}: {exc}",
            "lock_file": str(lock_path),
            "requested": requested,
            "status": "failed",
        }
    finally:
        if lock_created:
            _release_lock(lock_path)

    if failure_payload is not None:
        evidence_file = _failure_evidence_path(evidence_dir, attempted_at)
        failure_payload["evidence_file"] = str(evidence_file)
        _write_json_file(evidence_file, failure_payload)
        _write_json_stream(sys.stderr, failure_payload)
        return 1

    success_payload = {
        "attempted_at": attempted_at.isoformat(),
        "requested": requested,
        "result": asdict(result),
        "status": "ok",
    }
    evidence_file = _success_evidence_path(
        evidence_dir,
        result.ingestion_run_id,
    )
    success_payload["evidence_file"] = str(evidence_file)
    _write_json_file(evidence_file, success_payload)
    _write_json_stream(sys.stdout, success_payload)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

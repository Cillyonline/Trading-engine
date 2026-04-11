"""Bounded paper execution cycle (OPS-P60).

Reads eligible signals from the signal repository, processes them through the
BoundedPaperExecutionWorker (OPS-P52 policy), and writes a timestamped
execution evidence JSON file.

Usage::

    python scripts/run_paper_execution_cycle.py
    python scripts/run_paper_execution_cycle.py --db-path /path/to/cilly_trading.db
    python scripts/run_paper_execution_cycle.py --evidence-dir runs/paper-execution

Exit codes:
    0  At least one signal was eligible and persisted.
    1  No signals were eligible (all skipped or rejected).
    2  Runtime error prevented the execution cycle from completing.

Non-live boundary:
    This script operates exclusively within the bounded paper simulation.
    No live orders are placed, no broker APIs are called, and no real capital
    is at risk.  Running this script does not imply live-trading readiness.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cilly_trading.engine.paper_execution_worker import (  # noqa: E402
    BoundedPaperExecutionWorker,
    DEFAULT_PAPER_EXECUTION_RISK_PROFILE,
    SignalEvaluationResult,
)
from cilly_trading.repositories.execution_core_sqlite import (  # noqa: E402
    SqliteCanonicalExecutionRepository,
)
from cilly_trading.repositories.signals_sqlite import (  # noqa: E402
    SqliteSignalRepository,
)

DEFAULT_EVIDENCE_DIR = ROOT / "runs" / "paper-execution"
DEFAULT_DB_PATH = ROOT / "cilly_trading.db"

EXIT_CYCLE_PASS = 0
EXIT_CYCLE_NO_ELIGIBLE = 1
EXIT_RUNTIME_ERROR = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded paper execution cycle.  Reads eligible signals, "
            "processes them through the OPS-P52 policy, and writes execution "
            "evidence."
        ),
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path.  Default: cilly_trading.db in repo root.",
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(DEFAULT_EVIDENCE_DIR),
        help=(
            "Directory for execution evidence JSON files.  "
            "Default: runs/paper-execution."
        ),
    )
    parser.add_argument(
        "--signal-limit",
        type=int,
        default=500,
        help="Maximum number of signals to read.  Default: 500.",
    )
    return parser.parse_args()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


class _DecimalEncoder(json.JSONEncoder):
    """JSON encoder that serialises Decimal as string for precision."""

    def default(self, o: object) -> object:
        if isinstance(o, Decimal):
            return str(o)
        return super().default(o)


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True, cls=_DecimalEncoder) + "\n",
        encoding="utf-8",
    )


def _write_json_stream(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(
        json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True, cls=_DecimalEncoder) + "\n",
    )


def _result_to_dict(result: SignalEvaluationResult) -> dict[str, Any]:
    """Serialise a SignalEvaluationResult to a JSON-safe dict."""
    d: dict[str, Any] = {"outcome": result.outcome}
    if result.signal_id is not None:
        d["signal_id"] = result.signal_id
    if result.order_id is not None:
        d["order_id"] = result.order_id
    if result.trade_id is not None:
        d["trade_id"] = result.trade_id
    if result.reason is not None:
        d["reason"] = result.reason
    return d


def run_paper_execution_cycle(
    *,
    db_path: str,
    evidence_dir: str,
    signal_limit: int = 500,
    ran_at: datetime | None = None,
) -> int:
    """Execute bounded paper execution cycle.  Returns exit code."""
    ran_at = ran_at or _utc_now()
    evidence_path = Path(evidence_dir)
    stamp = ran_at.strftime("%Y%m%dT%H%M%SZ")

    try:
        signal_repo = SqliteSignalRepository(db_path=Path(db_path))
        execution_repo = SqliteCanonicalExecutionRepository(db_path=Path(db_path))

        signals = signal_repo.list_signals(limit=signal_limit)

        risk_profile = DEFAULT_PAPER_EXECUTION_RISK_PROFILE
        worker = BoundedPaperExecutionWorker(
            repository=execution_repo,
            risk_profile=risk_profile,
        )
        results = worker.process_batch(signals)
    except Exception as exc:
        error_payload: dict[str, Any] = {
            "code": "paper_execution_cycle_runtime_error",
            "cycle_type": "bounded_paper_execution",
            "db_path": db_path,
            "detail": f"{type(exc).__name__}: {exc}",
            "ran_at": ran_at.isoformat(),
            "status": "error",
        }
        error_file = evidence_path / f"paper-execution-error-{stamp}.json"
        _write_json_file(error_file, error_payload)
        error_payload["evidence_file"] = str(error_file)
        _write_json_stream(sys.stderr, error_payload)
        print(f"PAPER_EXECUTION_CYCLE:ERROR:{type(exc).__name__}")
        return EXIT_RUNTIME_ERROR

    eligible = [r for r in results if r.outcome == "eligible"]
    skipped = [r for r in results if r.outcome.startswith("skip:")]
    rejected = [r for r in results if r.outcome.startswith("reject:")]

    result_payload: dict[str, Any] = {
        "cycle_type": "bounded_paper_execution",
        "db_path": db_path,
        "eligible": len(eligible),
        "ran_at": ran_at.isoformat(),
        "rejected": len(rejected),
        "results": [_result_to_dict(r) for r in results],
        "risk_profile": risk_profile.to_payload(),
        "signals_read": len(signals),
        "skipped": len(skipped),
        "status": "pass" if eligible else "no_eligible",
    }

    tag = "pass" if eligible else "no-eligible"
    evidence_file = evidence_path / f"paper-execution-{tag}-{stamp}.json"
    _write_json_file(evidence_file, result_payload)
    result_payload["evidence_file"] = str(evidence_file)
    _write_json_stream(sys.stdout, result_payload)

    if eligible:
        print(f"PAPER_EXECUTION_CYCLE:PASS:{len(eligible)}_eligible_of_{len(signals)}_signals")
        return EXIT_CYCLE_PASS
    else:
        print(f"PAPER_EXECUTION_CYCLE:COMPLETE:0_eligible_of_{len(signals)}_signals")
        return EXIT_CYCLE_NO_ELIGIBLE


def main() -> int:
    args = _parse_args()
    return run_paper_execution_cycle(
        db_path=args.db_path,
        evidence_dir=args.evidence_dir,
        signal_limit=args.signal_limit,
    )


if __name__ == "__main__":
    raise SystemExit(main())

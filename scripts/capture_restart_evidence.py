"""Restart/recovery evidence capture.

Captures a deterministic evidence snapshot after a process restart or
reload.  Reads canonical state from the SQLite execution repository and
validates reconciliation consistency, then writes a timestamped evidence
JSON file that can be compared against a pre-restart baseline.

Usage::

    python scripts/capture_restart_evidence.py
    python scripts/capture_restart_evidence.py --db-path /path/to/cilly_trading.db
    python scripts/capture_restart_evidence.py --evidence-dir runs/restart-evidence
    python scripts/capture_restart_evidence.py --baseline runs/restart-evidence/pre-restart-*.json

Exit codes:
    0  Restart evidence captured and reconciliation passed.
    1  Restart evidence captured but reconciliation failed or baseline mismatch.
    2  Runtime error prevented evidence capture.
"""

from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cilly_trading.repositories.execution_core_sqlite import (  # noqa: E402
    SqliteCanonicalExecutionRepository,
)
from api.services.paper_inspection_service import (  # noqa: E402
    build_paper_account_state,
    build_paper_reconciliation_mismatches,
    build_trading_core_positions,
)

DEFAULT_EVIDENCE_DIR = ROOT / "runs" / "restart-evidence"
DEFAULT_DB_PATH = ROOT / "cilly_trading.db"

EXIT_CAPTURE_PASS = 0
EXIT_CAPTURE_FAIL = 1
EXIT_RUNTIME_ERROR = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Capture restart/recovery evidence. "
            "Reads canonical state, validates reconciliation, and optionally "
            "compares against a pre-restart baseline."
        ),
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path. Default: cilly_trading.db in repo root.",
    )
    parser.add_argument(
        "--evidence-dir",
        default=str(DEFAULT_EVIDENCE_DIR),
        help=(
            "Directory for restart evidence JSON files. "
            "Default: runs/restart-evidence."
        ),
    )
    parser.add_argument(
        "--baseline",
        default=None,
        help=(
            "Path to a pre-restart evidence JSON file. "
            "When provided, the script compares entity counts and "
            "reconciliation state against this baseline."
        ),
    )
    parser.add_argument(
        "--phase",
        choices=["pre-restart", "post-restart"],
        default="post-restart",
        help=(
            "Evidence capture phase. Use 'pre-restart' to record a baseline "
            "before stopping, 'post-restart' (default) to verify after restart."
        ),
    )
    return parser.parse_args()


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _write_json_stream(stream: Any, payload: dict[str, Any]) -> None:
    stream.write(
        json.dumps(payload, sort_keys=True, default=str, ensure_ascii=True) + "\n",
    )


def _load_baseline(baseline_path: str) -> Optional[dict[str, Any]]:
    path = Path(baseline_path)
    if not path.exists():
        return None
    return json.loads(path.read_text(encoding="utf-8"))


def _compare_baseline(
    current: dict[str, Any],
    baseline: dict[str, Any],
) -> list[dict[str, str]]:
    """Compare current entity counts against a baseline.  Returns deltas."""
    deltas: list[dict[str, str]] = []
    current_summary = current.get("summary", {})
    baseline_summary = baseline.get("summary", {})
    for key in ("orders", "execution_events", "trades", "positions"):
        cur_val = current_summary.get(key)
        base_val = baseline_summary.get(key)
        if cur_val != base_val:
            deltas.append({
                "field": key,
                "baseline": str(base_val),
                "current": str(cur_val),
            })
    return deltas


def capture_restart_evidence(
    *,
    db_path: str,
    evidence_dir: str,
    baseline_path: Optional[str],
    phase: str,
) -> int:
    """Capture restart evidence and write to file.  Returns exit code."""
    ran_at = _utc_now()
    evidence_path = Path(evidence_dir)
    stamp = ran_at.strftime("%Y%m%dT%H%M%SZ")

    try:
        repo = SqliteCanonicalExecutionRepository(db_path=Path(db_path))
        orders = repo.list_orders(limit=1_000_000, offset=0)
        execution_events = repo.list_execution_events(limit=1_000_000, offset=0)
        trades = repo.list_trades(limit=1_000_000, offset=0)
        positions = build_trading_core_positions(
            canonical_execution_repo=repo,
            trades=trades,
            orders=orders,
            events=execution_events,
        )
        account = build_paper_account_state(
            paper_trades=trades,
            paper_positions=positions,
        )
        mismatches = build_paper_reconciliation_mismatches(
            orders=orders,
            execution_events=execution_events,
            trades=trades,
            positions=positions,
            account=account,
        )
    except Exception as exc:
        error_payload: dict[str, Any] = {
            "code": "restart_evidence_runtime_error",
            "db_path": db_path,
            "detail": f"{type(exc).__name__}: {exc}",
            "phase": phase,
            "ran_at": ran_at.isoformat(),
            "status": "error",
        }
        error_file = evidence_path / f"{phase}-error-{stamp}.json"
        error_payload["evidence_file"] = str(error_file)
        _write_json_file(error_file, error_payload)
        _write_json_stream(sys.stderr, error_payload)
        print(f"RESTART_EVIDENCE:ERROR:{type(exc).__name__}")
        return EXIT_RUNTIME_ERROR

    reconciliation_ok = len(mismatches) == 0
    summary = {
        "closed_trades": int(account.get("closed_trades", 0)),
        "execution_events": len(execution_events),
        "mismatches": len(mismatches),
        "open_positions": int(account.get("open_positions", 0)),
        "open_trades": int(account.get("open_trades", 0)),
        "orders": len(orders),
        "positions": len(positions),
        "trades": len(trades),
    }

    result_payload: dict[str, Any] = {
        "account": {k: str(v) for k, v in account.items()},
        "db_path": db_path,
        "mismatch_items": [dict(m) for m in mismatches],
        "ok": reconciliation_ok,
        "phase": phase,
        "ran_at": ran_at.isoformat(),
        "summary": summary,
    }

    # Baseline comparison (post-restart only)
    baseline_comparison: Optional[dict[str, Any]] = None
    if baseline_path and phase == "post-restart":
        baseline = _load_baseline(baseline_path)
        if baseline is not None:
            deltas = _compare_baseline(result_payload, baseline)
            baseline_comparison = {
                "baseline_file": baseline_path,
                "deltas": deltas,
                "entity_counts_match": len(deltas) == 0,
            }
            result_payload["baseline_comparison"] = baseline_comparison

    all_ok = reconciliation_ok
    if baseline_comparison and not baseline_comparison["entity_counts_match"]:
        all_ok = False

    result_payload["status"] = "pass" if all_ok else "fail"

    evidence_file = evidence_path / f"{phase}-{'pass' if all_ok else 'fail'}-{stamp}.json"
    result_payload["evidence_file"] = str(evidence_file)
    _write_json_file(evidence_file, result_payload)
    _write_json_stream(sys.stdout, result_payload)

    if all_ok:
        print(f"RESTART_EVIDENCE:{phase.upper().replace('-', '_')}:PASS")
        return EXIT_CAPTURE_PASS
    else:
        print(f"RESTART_EVIDENCE:{phase.upper().replace('-', '_')}:FAIL")
        return EXIT_CAPTURE_FAIL


def main() -> int:
    args = _parse_args()
    return capture_restart_evidence(
        db_path=args.db_path,
        evidence_dir=args.evidence_dir,
        baseline_path=args.baseline,
        phase=args.phase,
    )


if __name__ == "__main__":
    raise SystemExit(main())

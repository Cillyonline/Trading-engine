"""Post-run reconciliation job.

Automates the Phase 44 reconciliation step after each execution cycle.
Loads canonical entities from the SQLite execution repository, derives
positions and account state, runs the deterministic mismatch check,
and writes a timestamped evidence JSON file.

Usage::

    python scripts/run_post_run_reconciliation.py
    python scripts/run_post_run_reconciliation.py --db-path /path/to/cilly_trading.db
    python scripts/run_post_run_reconciliation.py --evidence-dir runs/reconciliation

Exit codes:
    0  Reconciliation passed (ok: true, mismatches: 0).
    1  Reconciliation failed (mismatches detected).
    2  Runtime error prevented reconciliation from completing.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from cilly_trading.repositories.execution_core_sqlite import (  # noqa: E402
    SqliteCanonicalExecutionRepository,
)


def _load_paper_inspection_service_module():
    module_path = ROOT / "src" / "api" / "services" / "paper_inspection_service.py"
    spec = importlib.util.spec_from_file_location("paper_inspection_service_script", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load paper_inspection_service module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_paper_inspection_module = _load_paper_inspection_service_module()
build_paper_account_state = _paper_inspection_module.build_paper_account_state
build_paper_reconciliation_mismatches = _paper_inspection_module.build_paper_reconciliation_mismatches
build_trading_core_positions = _paper_inspection_module.build_trading_core_positions

DEFAULT_EVIDENCE_DIR = ROOT / "runs" / "reconciliation"
DEFAULT_DB_PATH = ROOT / "cilly_trading.db"

EXIT_RECONCILIATION_PASS = 0
EXIT_RECONCILIATION_FAIL = 1
EXIT_RUNTIME_ERROR = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Run bounded post-run reconciliation. "
            "Loads canonical entities, derives positions and account state, "
            "and validates cross-entity and account-equation consistency."
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
            "Directory for reconciliation evidence JSON files. "
            "Default: runs/reconciliation."
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


def run_reconciliation(
    *,
    db_path: str,
    evidence_dir: str,
    ran_at: datetime | None = None,
) -> int:
    """Execute reconciliation and write evidence.  Returns exit code."""
    ran_at = ran_at or _utc_now()
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
            "code": "reconciliation_runtime_error",
            "db_path": db_path,
            "detail": f"{type(exc).__name__}: {exc}",
            "ran_at": ran_at.isoformat(),
            "status": "error",
        }
        error_file = evidence_path / f"reconciliation-error-{stamp}.json"
        error_payload["evidence_file"] = str(error_file)
        _write_json_file(error_file, error_payload)
        _write_json_stream(sys.stderr, error_payload)
        print(f"RECONCILIATION:ERROR:{type(exc).__name__}")
        return EXIT_RUNTIME_ERROR

    ok = len(mismatches) == 0
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
        "db_path": db_path,
        "mismatch_items": [dict(m) for m in mismatches],
        "ok": ok,
        "ran_at": ran_at.isoformat(),
        "status": "pass" if ok else "fail",
        "summary": summary,
    }

    tag = "pass" if ok else "fail"
    evidence_file = evidence_path / f"reconciliation-{tag}-{stamp}.json"
    result_payload["evidence_file"] = str(evidence_file)
    _write_json_file(evidence_file, result_payload)
    _write_json_stream(sys.stdout, result_payload)

    if ok:
        print("RECONCILIATION:PASS")
        return EXIT_RECONCILIATION_PASS
    else:
        print("RECONCILIATION:FAIL")
        return EXIT_RECONCILIATION_FAIL


def main() -> int:
    args = _parse_args()
    return run_reconciliation(db_path=args.db_path, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())

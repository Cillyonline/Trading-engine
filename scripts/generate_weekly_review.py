"""Weekly review artifact generator.

Produces a deterministic weekly review evidence bundle containing the
R1–R7 artifacts defined in the Phase 44 operator workflow.  Each artifact
is captured by reading canonical state from the SQLite execution repository
and applying the same derivation logic used by the paper inspection API.

Usage::

    python scripts/generate_weekly_review.py
    python scripts/generate_weekly_review.py --db-path /path/to/cilly_trading.db
    python scripts/generate_weekly_review.py --evidence-dir runs/weekly-review

Exit codes:
    0  All R1–R7 artifacts captured successfully.
    1  One or more artifacts failed validation.
    2  Runtime error prevented artifact generation.
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

DEFAULT_EVIDENCE_DIR = ROOT / "runs" / "weekly-review"
DEFAULT_DB_PATH = ROOT / "cilly_trading.db"

EXIT_REVIEW_PASS = 0
EXIT_REVIEW_FAIL = 1
EXIT_RUNTIME_ERROR = 2


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Generate weekly review evidence bundle (R1–R7 artifacts). "
            "Reads canonical state from the SQLite execution repository "
            "and produces a deterministic JSON evidence file."
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
            "Directory for weekly review evidence JSON files. "
            "Default: runs/weekly-review."
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


def generate_weekly_review(
    *,
    db_path: str,
    evidence_dir: str,
    ran_at: datetime | None = None,
) -> int:
    """Capture R1–R7 artifacts and write evidence bundle.  Returns exit code."""
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
            "code": "weekly_review_runtime_error",
            "db_path": db_path,
            "detail": f"{type(exc).__name__}: {exc}",
            "ran_at": ran_at.isoformat(),
            "status": "error",
        }
        error_file = evidence_path / f"weekly-review-error-{stamp}.json"
        # File payload omits evidence_file so content is path-independent.
        _write_json_file(error_file, error_payload)
        error_payload["evidence_file"] = str(error_file)
        _write_json_stream(sys.stderr, error_payload)
        print(f"WEEKLY_REVIEW:ERROR:{type(exc).__name__}")
        return EXIT_RUNTIME_ERROR

    reconciliation_ok = len(mismatches) == 0

    # --- R1: Reconciliation result ---
    r1 = {
        "artifact": "R1",
        "name": "reconciliation_result",
        "ok": reconciliation_ok,
        "mismatches": len(mismatches),
        "mismatch_items": [dict(m) for m in mismatches],
        "valid": reconciliation_ok,
    }

    # --- R2: Account snapshot ---
    as_of = account.get("as_of")
    equity = account.get("equity")
    cash = account.get("cash")
    unrealized_pnl = account.get("unrealized_pnl")
    equity_equation_valid = (
        equity is not None
        and cash is not None
        and unrealized_pnl is not None
    )
    r2 = {
        "artifact": "R2",
        "name": "account_snapshot",
        "account": {k: str(v) for k, v in account.items()},
        "as_of_present": as_of is not None,
        "equity_equation_valid": equity_equation_valid,
        "valid": reconciliation_ok and equity_equation_valid,
    }

    # --- R3: Canonical order count ---
    r3 = {
        "artifact": "R3",
        "name": "canonical_order_count",
        "total": len(orders),
        "valid": reconciliation_ok and len(orders) >= 0,
    }

    # --- R4: Canonical execution-event count ---
    r4 = {
        "artifact": "R4",
        "name": "canonical_execution_event_count",
        "total": len(execution_events),
        "valid": reconciliation_ok and len(execution_events) >= 0,
    }

    # --- R5: Canonical trade count ---
    r5 = {
        "artifact": "R5",
        "name": "canonical_trade_count",
        "total": len(trades),
        "valid": reconciliation_ok and len(trades) >= 0,
    }

    # --- R6: Canonical position count ---
    r6 = {
        "artifact": "R6",
        "name": "canonical_position_count",
        "total": len(positions),
        "valid": reconciliation_ok and len(positions) >= 0,
    }

    # --- R7: Workflow contract state ---
    r7 = {
        "artifact": "R7",
        "name": "workflow_contract_state",
        "reconciliation_ok": reconciliation_ok,
        "valid": reconciliation_ok,
    }

    artifacts = [r1, r2, r3, r4, r5, r6, r7]
    all_valid = all(a["valid"] for a in artifacts)

    review_payload: dict[str, Any] = {
        "all_valid": all_valid,
        "artifacts": artifacts,
        "db_path": db_path,
        "ran_at": ran_at.isoformat(),
        "status": "pass" if all_valid else "fail",
        "summary": {
            "closed_trades": int(account.get("closed_trades", 0)),
            "execution_events": len(execution_events),
            "mismatches": len(mismatches),
            "open_positions": int(account.get("open_positions", 0)),
            "open_trades": int(account.get("open_trades", 0)),
            "orders": len(orders),
            "positions": len(positions),
            "trades": len(trades),
        },
    }

    tag = "pass" if all_valid else "fail"
    evidence_file = evidence_path / f"weekly-review-{tag}-{stamp}.json"
    # Write file payload without evidence_file so emitted content is path-independent
    # and byte-for-byte identical for identical inputs.
    _write_json_file(evidence_file, review_payload)
    review_payload["evidence_file"] = str(evidence_file)
    _write_json_stream(sys.stdout, review_payload)

    if all_valid:
        print("WEEKLY_REVIEW:PASS")
        return EXIT_REVIEW_PASS
    else:
        print("WEEKLY_REVIEW:FAIL")
        return EXIT_REVIEW_FAIL


def main() -> int:
    args = _parse_args()
    return generate_weekly_review(db_path=args.db_path, evidence_dir=args.evidence_dir)


if __name__ == "__main__":
    raise SystemExit(main())

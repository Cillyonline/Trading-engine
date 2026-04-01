"""Tests for P53 automated review operations.

Validates that documentation, scripts, and checklist align to the
automated reconciliation, weekly review, and restart/recovery workflow
defined in OPS-P53.
"""

from __future__ import annotations

import json
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from cilly_trading.models import ExecutionEvent, Order, Trade
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT / "scripts") not in sys.path:
    sys.path.insert(0, str(REPO_ROOT / "scripts"))

from capture_restart_evidence import capture_restart_evidence
from generate_weekly_review import generate_weekly_review
from run_post_run_reconciliation import run_reconciliation


# ---------------------------------------------------------------------------
# P53 automation doc tests
# ---------------------------------------------------------------------------


def test_p53_automation_doc_exists_and_defines_scope() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# P53 Automated Review Operations")
    assert "## Purpose" in content
    assert "## Scope Boundary" in content
    assert "post-run reconciliation" in content.lower()
    assert "weekly review" in content.lower()
    assert "restart" in content.lower()


def test_p53_automation_doc_defines_post_run_reconciliation_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Post-Run Reconciliation" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "RECONCILIATION:PASS" in content
    assert "RECONCILIATION:FAIL" in content
    assert "runs/reconciliation/" in content


def test_p53_automation_doc_defines_weekly_review_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Weekly Review Artifact Generation" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "WEEKLY_REVIEW:PASS" in content
    assert "WEEKLY_REVIEW:FAIL" in content
    assert "R1" in content
    assert "R7" in content
    assert "runs/weekly-review/" in content


def test_p53_automation_doc_defines_restart_evidence_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Restart/Recovery Evidence Capture" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "pre-restart" in content
    assert "post-restart" in content
    assert "RESTART_EVIDENCE" in content
    assert "runs/restart-evidence/" in content


def test_p53_automation_doc_defines_evidence_file_format() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Evidence File Format" in content
    assert "ran_at" in content
    assert "db_path" in content
    assert "status" in content
    assert "evidence_file" in content
    assert "summary" in content


def test_p53_automation_doc_maps_to_phase44_workflow() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Integration with Phase 44 Operator Workflow" in content
    assert "End-of-session reconciliation" in content
    assert "Periodic weekly review" in content
    assert "Pre-restart baseline" in content
    assert "Post-restart recovery verification" in content


def test_p53_automation_doc_maps_to_operator_checklist() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Operator Checklist Integration" in content
    assert "E1" in content
    assert "E2" in content
    assert "E3" in content
    assert "E4" in content


def test_p53_automation_doc_references_state_authority() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Singular State Authority" in content
    assert "SqliteCanonicalExecutionRepository" in content
    assert "paper_state_authority.py" in content


# ---------------------------------------------------------------------------
# Phase 44 workflow doc references P53
# ---------------------------------------------------------------------------


def test_phase44_workflow_doc_references_p53_automation() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## P53 Automated Review Operations" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Paper inspection API doc references P53
# ---------------------------------------------------------------------------


def test_paper_inspection_api_doc_references_p53_automation() -> None:
    content = (REPO_ROOT / "docs" / "api" / "paper_inspection.md").read_text(encoding="utf-8")

    assert "## Automated Reconciliation and Review" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Operator checklist references automation
# ---------------------------------------------------------------------------


def test_operator_checklist_references_automated_review_commands() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "paper-deployment-operator-checklist.md"
    ).read_text(encoding="utf-8")

    assert "### Automated Review Evidence Commands" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Docs index links P53
# ---------------------------------------------------------------------------


def test_docs_index_links_p53_automation() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "### P53 Reference Materials" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Script files exist
# ---------------------------------------------------------------------------


def test_post_run_reconciliation_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "run_post_run_reconciliation.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "run_reconciliation" in content
    assert "RECONCILIATION:PASS" in content
    assert "RECONCILIATION:FAIL" in content
    assert "evidence_file" in content


def test_weekly_review_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "generate_weekly_review.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "generate_weekly_review" in content
    assert "WEEKLY_REVIEW:PASS" in content
    assert "WEEKLY_REVIEW:FAIL" in content
    assert "R1" in content
    assert "R7" in content


def test_restart_evidence_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "capture_restart_evidence.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "capture_restart_evidence" in content
    assert "RESTART_EVIDENCE" in content
    assert "pre-restart" in content
    assert "post-restart" in content
    assert "baseline" in content


# ---------------------------------------------------------------------------
# Script contract consistency
# ---------------------------------------------------------------------------


def test_all_scripts_use_canonical_state_authority() -> None:
    """All P53 scripts must import from the canonical execution repository."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "SqliteCanonicalExecutionRepository" in content, (
            f"{script_name} must use SqliteCanonicalExecutionRepository"
        )
        assert "build_paper_reconciliation_mismatches" in content, (
            f"{script_name} must use build_paper_reconciliation_mismatches"
        )


def test_all_scripts_write_evidence_files() -> None:
    """All P53 scripts must produce evidence JSON output."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "evidence_file" in content, (
            f"{script_name} must reference evidence_file"
        )
        assert ".json" in content, (
            f"{script_name} must produce JSON evidence"
        )
        assert "evidence_dir" in content or "evidence-dir" in content, (
            f"{script_name} must accept evidence directory"
        )


def test_all_scripts_define_exit_codes() -> None:
    """All P53 scripts must define bounded exit codes."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "EXIT_" in content, (
            f"{script_name} must define explicit exit codes"
        )
        assert "def main()" in content, (
            f"{script_name} must define main()"
        )
        assert '__name__ == "__main__"' in content, (
            f"{script_name} must have __main__ guard"
        )


def _repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "p53-deterministic.db")


def _order(
    order_id: str,
    *,
    sequence: int,
    created_at: str,
    position_id: str,
    trade_id: str,
) -> Order:
    return Order.model_validate(
        {
            "order_id": order_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "sequence": sequence,
            "side": "BUY",
            "order_type": "market",
            "time_in_force": "day",
            "status": "filled",
            "quantity": Decimal("1"),
            "filled_quantity": Decimal("1"),
            "created_at": created_at,
            "submitted_at": created_at,
            "average_fill_price": Decimal("100"),
            "last_execution_event_id": f"evt-{sequence}",
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _event(
    event_id: str,
    order_id: str,
    *,
    occurred_at: str,
    sequence: int,
    position_id: str,
    trade_id: str,
) -> ExecutionEvent:
    return ExecutionEvent.model_validate(
        {
            "event_id": event_id,
            "order_id": order_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "side": "BUY",
            "event_type": "filled",
            "occurred_at": occurred_at,
            "sequence": sequence,
            "execution_quantity": Decimal("1"),
            "execution_price": Decimal("100"),
            "commission": Decimal("0"),
            "position_id": position_id,
            "trade_id": trade_id,
        }
    )


def _trade(
    trade_id: str,
    *,
    position_id: str,
    status: str,
    opened_at: str,
    closed_at: str | None,
    realized_pnl: str | None,
    unrealized_pnl: str | None,
    order_id: str,
    event_id: str,
) -> Trade:
    return Trade.model_validate(
        {
            "trade_id": trade_id,
            "position_id": position_id,
            "strategy_id": "paper-strategy",
            "symbol": "AAPL",
            "direction": "long",
            "status": status,
            "opened_at": opened_at,
            "closed_at": closed_at,
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1") if status == "closed" else Decimal("0"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("101") if status == "closed" else None,
            "realized_pnl": Decimal(realized_pnl) if realized_pnl is not None else None,
            "unrealized_pnl": Decimal(unrealized_pnl) if unrealized_pnl is not None else None,
            "opening_order_ids": [order_id],
            "closing_order_ids": [order_id] if status == "closed" else [],
            "execution_event_ids": [event_id],
        }
    )


def _seed_core_data(repo: SqliteCanonicalExecutionRepository) -> None:
    repo.save_order(
        _order(
            "ord-1",
            sequence=1,
            created_at="2025-01-01T09:00:00Z",
            position_id="pos-1",
            trade_id="trade-1",
        )
    )
    repo.save_order(
        _order(
            "ord-2",
            sequence=2,
            created_at="2025-01-01T09:02:00Z",
            position_id="pos-2",
            trade_id="trade-2",
        )
    )
    repo.save_execution_events(
        [
            _event(
                "evt-1",
                "ord-1",
                occurred_at="2025-01-01T09:01:00Z",
                sequence=1,
                position_id="pos-1",
                trade_id="trade-1",
            ),
            _event(
                "evt-2",
                "ord-2",
                occurred_at="2025-01-01T09:03:00Z",
                sequence=2,
                position_id="pos-2",
                trade_id="trade-2",
            ),
        ]
    )
    repo.save_trade(
        _trade(
            "trade-1",
            position_id="pos-1",
            status="closed",
            opened_at="2025-01-01T09:00:00Z",
            closed_at="2025-01-01T09:10:00Z",
            realized_pnl="1.5",
            unrealized_pnl=None,
            order_id="ord-1",
            event_id="evt-1",
        )
    )
    repo.save_trade(
        _trade(
            "trade-2",
            position_id="pos-2",
            status="open",
            opened_at="2025-01-01T09:02:00Z",
            closed_at=None,
            realized_pnl=None,
            unrealized_pnl="2.25",
            order_id="ord-2",
            event_id="evt-2",
        )
    )


def _read_single_json(evidence_dir: Path, pattern: str) -> dict[str, object]:
    files = sorted(evidence_dir.glob(pattern))
    assert len(files) == 1, f"expected exactly one file for {pattern}, got {len(files)}"
    return json.loads(files[0].read_text(encoding="utf-8"))


def _canonicalize_payload_for_compare(payload: dict[str, object]) -> dict[str, object]:
    canonical = dict(payload)
    canonical["evidence_file"] = "<normalized>"
    return canonical


def test_reconciliation_evidence_is_byte_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
    db_path = tmp_path / "p53-deterministic.db"
    fixed_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    evidence_a = tmp_path / "evidence-a"
    evidence_b = tmp_path / "evidence-b"

    assert run_reconciliation(
        db_path=str(db_path),
        evidence_dir=str(evidence_a),
        ran_at=fixed_time,
    ) == 0
    assert run_reconciliation(
        db_path=str(db_path),
        evidence_dir=str(evidence_b),
        ran_at=fixed_time,
    ) == 0

    payload_a = _read_single_json(evidence_a, "reconciliation-pass-*.json")
    payload_b = _read_single_json(evidence_b, "reconciliation-pass-*.json")

    assert _canonicalize_payload_for_compare(payload_a) == _canonicalize_payload_for_compare(payload_b)


def test_weekly_review_evidence_is_byte_deterministic_for_identical_inputs(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
    db_path = tmp_path / "p53-deterministic.db"
    fixed_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    evidence_a = tmp_path / "weekly-a"
    evidence_b = tmp_path / "weekly-b"

    assert generate_weekly_review(
        db_path=str(db_path),
        evidence_dir=str(evidence_a),
        ran_at=fixed_time,
    ) == 0
    assert generate_weekly_review(
        db_path=str(db_path),
        evidence_dir=str(evidence_b),
        ran_at=fixed_time,
    ) == 0

    payload_a = _read_single_json(evidence_a, "weekly-review-pass-*.json")
    payload_b = _read_single_json(evidence_b, "weekly-review-pass-*.json")

    assert _canonicalize_payload_for_compare(payload_a) == _canonicalize_payload_for_compare(payload_b)


def test_restart_baseline_comparison_fails_on_controlled_mismatch(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)
    db_path = tmp_path / "p53-deterministic.db"
    fixed_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)
    evidence_dir = tmp_path / "restart-evidence"

    assert capture_restart_evidence(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        baseline_path=None,
        phase="pre-restart",
        ran_at=fixed_time,
    ) == 0
    baseline_payload = _read_single_json(evidence_dir, "pre-restart-pass-*.json")

    controlled_mismatch_baseline = dict(baseline_payload)
    controlled_mismatch_summary = dict(controlled_mismatch_baseline.get("summary", {}))
    controlled_mismatch_summary["orders"] = int(controlled_mismatch_summary.get("orders", 0)) + 1
    controlled_mismatch_baseline["summary"] = controlled_mismatch_summary
    controlled_baseline_path = tmp_path / "controlled-baseline.json"
    controlled_baseline_path.write_text(
        json.dumps(controlled_mismatch_baseline, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    assert capture_restart_evidence(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        baseline_path=str(controlled_baseline_path),
        phase="post-restart",
        ran_at=fixed_time,
    ) == 1

    post_payload = _read_single_json(evidence_dir, "post-restart-fail-*.json")
    comparison = post_payload.get("baseline_comparison")
    assert isinstance(comparison, dict)
    assert comparison["entity_counts_match"] is False
    deltas = comparison["deltas"]
    assert isinstance(deltas, list)
    assert any(delta.get("field") == "orders" for delta in deltas)


def test_reconciliation_uses_real_repository_state_and_detects_missing_order_reference(tmp_path: Path) -> None:
    repo = _repo(tmp_path)
    _seed_core_data(repo)

    repo.save_execution_events(
        [
            _event(
                "evt-missing-order",
                "ord-does-not-exist",
                occurred_at="2025-01-01T09:04:00Z",
                sequence=3,
                position_id="pos-2",
                trade_id="trade-2",
            )
        ]
    )

    db_path = tmp_path / "p53-deterministic.db"
    evidence_dir = tmp_path / "reconciliation-real-state"
    fixed_time = datetime(2026, 1, 15, 10, 30, 0, tzinfo=timezone.utc)

    assert run_reconciliation(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        ran_at=fixed_time,
    ) == 1

    payload = _read_single_json(evidence_dir, "reconciliation-fail-*.json")
    assert payload["ok"] is False
    summary = payload["summary"]
    assert isinstance(summary, dict)
    assert summary["mismatches"] > 0
    mismatch_items = payload["mismatch_items"]
    assert isinstance(mismatch_items, list)
    assert any(item.get("code") == "execution_event_order_missing" for item in mismatch_items)

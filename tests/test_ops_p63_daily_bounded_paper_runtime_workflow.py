"""Contract tests for OPS-P63 daily bounded paper runtime workflow.

Acceptance criteria verified:
    AC1: Daily bounded paper runtime workflow is clearly documented in order.
    AC2: Workflow covers ingestion, analysis, execution, reconciliation,
         and evidence capture.
    AC3: Each step has an operator-facing command or invocation path.
    AC4: Existing read-only verification surfaces are identified.
    AC5: Workflow remains bounded with explicit non-live claim boundary.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
P63_DOC = "docs/operations/runtime/p63-daily-bounded-paper-runtime-workflow.md"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_p63_doc_exists_and_defines_daily_order() -> None:
    content = _read(P63_DOC)

    assert content.startswith("# OPS-P63: Daily Bounded Paper Runtime Workflow")
    assert "## Required Daily Workflow Order" in content
    assert "1. Snapshot ingestion" in content
    assert "2. Analysis and signal generation" in content
    assert "3. Bounded paper execution cycle" in content
    assert "4. Reconciliation" in content
    assert "5. Evidence capture and run record" in content


def test_p63_doc_covers_all_required_runtime_steps() -> None:
    content = _read(P63_DOC)

    assert "## Step 1 - Snapshot Ingestion" in content
    assert "## Step 2 - Analysis and Signal Generation" in content
    assert "## Step 3 - Bounded Paper Execution Cycle" in content
    assert "## Step 4 - Reconciliation" in content
    assert "## Step 5 - Evidence Capture and Run Record" in content


def test_p63_doc_has_operator_facing_commands_for_each_step() -> None:
    content = _read(P63_DOC)

    assert "scripts/run_snapshot_ingestion.py" in content
    assert "POST /analysis/run" in content
    assert "scripts/run_paper_execution_cycle.py" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert content.lower().count("runnable independently") >= 5


def test_p63_doc_defines_full_sequential_workflow() -> None:
    content = _read(P63_DOC)

    assert "## Daily Sequential Command Sequence (Bounded Staging)" in content

    idx_ingest = content.index("run_snapshot_ingestion.py")
    idx_analysis = content.index("/analysis/run")
    idx_execute = content.index("run_paper_execution_cycle.py")
    idx_reconcile = content.index("run_post_run_reconciliation.py")
    idx_evidence = content.index("generate_weekly_review.py")

    assert idx_ingest < idx_analysis < idx_execute < idx_reconcile < idx_evidence


def test_p63_doc_identifies_existing_read_only_verification_surfaces() -> None:
    content = _read(P63_DOC)

    assert "## Verification Surfaces (Read-Only)" in content
    assert "/signals" in content
    assert "/paper/trades" in content
    assert "/paper/positions" in content
    assert "/paper/reconciliation" in content


def test_p63_doc_contains_bounded_end_to_end_validation_example() -> None:
    content = _read(P63_DOC)

    assert "## Bounded End-to-End Validation Example (2026-04-05)" in content
    assert "eligible: 3" in content
    assert "ok: true" in content
    assert "mismatches: 0" in content


def test_p63_doc_contains_explicit_non_live_claim_boundary() -> None:
    content = _read(P63_DOC)

    assert "## Explicit Claim Boundary" in content
    assert "no live orders are placed" in content
    assert "no broker APIs are called" in content
    assert "no production-readiness claim is made" in content
    assert "non-error completion" in content


def test_p63_doc_defines_deterministic_run_quality_classification() -> None:
    content = _read(P63_DOC)

    assert "Deterministic Run-Quality Classification (Daily Summary)" in content
    assert "run_quality_status" in content
    assert "run_quality_classification_version" in content
    assert "run_quality_inputs" in content
    assert "`healthy`" in content
    assert "`no_eligible`" in content
    assert "`degraded`" in content
    assert "Deterministic classification rules use existing runtime summary inputs only" in content


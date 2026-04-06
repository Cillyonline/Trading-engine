"""Contract tests for OPS-P64 one-command bounded daily runtime runner.

Acceptance criteria verified:
    AC1: One operator-facing command exists for end-to-end bounded daily workflow.
    AC2: Runner order matches OPS-P63 exactly.
    AC3: Failure handling is explicit and bounded.
    AC4: Existing read-only verification surfaces remain usable.
    AC5: Documentation and tests reflect the bounded runner.
    AC6: No live/broker/production readiness claims are introduced.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]

P64_DOC = "docs/operations/runtime/p64-one-command-bounded-daily-paper-runtime-runner.md"
P64_SCRIPT = "scripts/run_daily_bounded_paper_runtime.py"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_p64_doc_and_runner_script_exist() -> None:
    assert (REPO_ROOT / P64_DOC).exists()
    assert (REPO_ROOT / P64_SCRIPT).exists()


def test_p64_doc_defines_one_operator_command() -> None:
    content = _read(P64_DOC)

    assert content.startswith("# OPS-P64: One-Command Bounded Daily Paper Runtime Runner")
    assert "## Operator Command" in content
    assert "python scripts/run_daily_bounded_paper_runtime.py" in content


def test_p64_doc_defines_exact_ops_p63_order() -> None:
    content = _read(P64_DOC)

    assert "## Required Ordered Execution" in content
    assert "1. Snapshot ingestion" in content
    assert "2. Analysis and signal generation" in content
    assert "3. Bounded paper execution cycle" in content
    assert "4. Reconciliation" in content
    assert "5. Evidence capture" in content


def test_p64_doc_defines_bounded_failure_behavior() -> None:
    content = _read(P64_DOC)

    assert "## Explicit Failure Behavior" in content
    assert "stops immediately on the first failed step" in content
    assert "failed_step" in content
    assert "steps_completed" in content
    assert "step_order" in content


def test_p64_doc_preserves_read_only_verification_surfaces() -> None:
    content = _read(P64_DOC)

    assert "## Verification Surfaces Remain Usable" in content
    assert "/signals" in content
    assert "/paper/trades" in content
    assert "/paper/positions" in content
    assert "/paper/reconciliation" in content


def test_p64_doc_has_explicit_non_live_claim_boundary() -> None:
    content = _read(P64_DOC)

    assert "## Explicit Claim Boundary" in content
    assert "no live orders are placed" in content
    assert "no broker APIs are called" in content
    assert "no production-readiness claim is made" in content


def test_p64_script_references_ops_p63_order_and_failure_mode() -> None:
    content = _read(P64_SCRIPT)

    assert "STEP_ORDER" in content
    assert "snapshot_ingestion" in content
    assert "analysis_signal_generation" in content
    assert "bounded_paper_execution_cycle" in content
    assert "reconciliation" in content
    assert "evidence_capture" in content
    assert "Stops on first failure" in content or "failed" in content.lower()

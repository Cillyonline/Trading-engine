from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_phase44_workflow_doc_defines_bounded_operator_flow_and_surfaces() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# Phase 44 Bounded Paper Operator Workflow")
    assert "## Bounded Workflow Claim" in content
    assert "## Required Runtime Surfaces" in content
    assert "GET /trading-core/orders" in content
    assert "GET /trading-core/execution-events" in content
    assert "GET /trading-core/trades" in content
    assert "GET /trading-core/positions" in content
    assert "GET /paper/trades" in content
    assert "GET /paper/positions" in content
    assert "GET /paper/account" in content
    assert "GET /paper/reconciliation" in content
    assert "GET /paper/workflow" in content
    assert "## Explicit Operator Steps" in content
    assert "## Workflow Boundary" in content
    assert "## Minimum Operator Evidence" in content
    assert "tests/test_api_paper_inspection_read.py" in content
    assert "python -m pytest" in content


def test_phase44_workflow_doc_preserves_phase24_boundary_and_non_goals() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## Phase 24 vs Phase 44 Boundary" in content
    assert "Phase 24 (implemented simulator governance boundary)" in content
    assert "Phase 44 (bounded runtime workflow claim in this phase slice)" in content
    assert "## Explicit Non-Goals" in content
    assert "Live trading" in content
    assert "Broker integration" in content
    assert "Mutation-heavy order-entry workflow" in content


def test_docs_index_links_phase44_workflow_contract() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "operations/runtime/phase-44-paper-operator-workflow.md" in content
    assert "### Phase 44 Reference Materials" in content


def test_phase44_workflow_doc_defines_long_run_evaluation_cadence() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## Long-Run Evaluation Cadence" in content
    assert "strategy change" in content.lower()
    assert "process restart" in content.lower()
    assert "periodic" in content.lower()


def test_phase44_workflow_doc_defines_strategy_change_comparison_boundary() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## Strategy-Change Comparison Boundary" in content
    assert "Pre-Change Baseline Capture" in content
    assert "Post-Change Comparison" in content
    assert "Prohibited Comparison Shortcuts" in content
    assert "mismatches: 0" in content


def test_phase44_workflow_doc_defines_review_artifact_checklist() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## Review Artifact Checklist" in content
    assert "| R1 |" in content
    assert "| R7 |" in content
    assert "`GET /paper/reconciliation`" in content
    assert "`GET /paper/workflow`" in content
    assert "R1–R7" in content


def test_phase44_workflow_doc_defines_restart_and_recovery_review() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## Restart and Recovery Review" in content
    assert "Recovery Verification Steps" in content
    assert "ok: true" in content
    assert "mismatches: 0" in content


def test_phase44_operator_checklist_includes_long_run_review_section() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "paper-deployment-operator-checklist.md"
    ).read_text(encoding="utf-8")

    assert "## E) Long-Run Paper Review Evidence" in content
    assert "R1–R7" in content
    assert "strategy-change comparison baseline" in content.lower()
    assert "post-restart recovery verification" in content.lower()
    assert "EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT" in content
    assert "EVIDENCE_COMPLETED_OPERATOR_CHECKLIST" in content


def test_paper_inspection_api_doc_cross_references_long_run_workflow() -> None:
    content = (REPO_ROOT / "docs" / "api" / "paper_inspection.md").read_text(encoding="utf-8")

    assert "## Long-Run Evaluation and Review Workflow" in content
    assert "phase-44-paper-operator-workflow.md" in content
    assert "R1–R7" in content

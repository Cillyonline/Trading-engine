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

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE23_STATUS_DOC = "docs/architecture/phases/phase-23-status.md"
PHASE23_CONTRACT_DOC = "docs/operations/ui/phase-23-research-dashboard-contract.md"
DOCS_INDEX = "docs/index.md"
ROADMAP_MASTER = "ROADMAP_MASTER.md"
RESEARCH_UI_FILE = "src/ui/research_dashboard/index.html"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_phase23_contract_defines_single_bounded_research_surface() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert content.startswith("# Phase 23 Research Dashboard Minimum Contract")
    assert "Surface name: `Research Dashboard`" in content
    assert "Runtime entrypoint: `/research-dashboard`" in content
    assert "src/ui/research_dashboard/index.html" in content
    assert "src/api/main.py" in content


def test_phase23_contract_explicitly_separates_from_operator_shell_and_ops_p56_log_issue() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert "separate from the shared operator shell at `/ui`" in content
    assert "OPS-P56: Start bounded staged paper-trading runbook and evidence log #914" in content
    assert "remains the single operational run log issue" in content


def test_phase23_contract_has_explicit_non_readiness_non_claims() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert "live trading" in content
    assert "execution automation" in content
    assert "trader-readiness claims" in content
    assert "production-readiness claims" in content
    assert "technically good, but traderically weak" in content


def test_phase23_status_reflects_bounded_partial_implementation() -> None:
    content = _read(PHASE23_STATUS_DOC)

    assert "## Status" in content
    assert "PARTIALLY IMPLEMENTED" in content
    assert "src/ui/research_dashboard/index.html" in content
    assert "src/api/test_research_dashboard_surface.py" in content
    assert "tests/test_phase23_research_dashboard_contract.py" in content
    assert "remains the single operational run log issue" in content
    assert "trader readiness" in content
    assert "production readiness" in content


def test_research_ui_surface_contains_identifiable_marker_and_boundaries() -> None:
    content = _read(RESEARCH_UI_FILE)

    assert 'id="phase23-research-dashboard-surface"' in content
    assert "/research-dashboard" in content
    assert "/ui" in content
    assert "#914" in content
    assert "Research Dashboard" in content
    assert "Operator Workbench" not in content


def test_index_includes_phase23_minimum_contract_reference() -> None:
    index_content = _read(DOCS_INDEX)

    assert "phase-23-research-dashboard-contract.md" in index_content
    assert "Phase 23 | `Research Dashboard`" in index_content
    assert "PARTIALLY IMPLEMENTED" in index_content


def test_roadmap_master_phase23_status_and_boundaries_align_with_phase23_docs() -> None:
    roadmap_content = _read(ROADMAP_MASTER)

    assert "| 23 | Research Dashboard | Partially Implemented |" in roadmap_content
    assert "## Phase 23 - Research Dashboard" in roadmap_content
    assert "**Status:** Partially Implemented" in roadmap_content
    assert "bounded minimum evidence contract" in roadmap_content
    assert "non-trader-ready" in roadmap_content
    assert "non-production-ready" in roadmap_content

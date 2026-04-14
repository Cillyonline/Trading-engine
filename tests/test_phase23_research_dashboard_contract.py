from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE23_STATUS_DOC = "docs/architecture/phases/phase-23-status.md"
PHASE23_CONTRACT_DOC = "docs/operations/ui/phase-23-research-dashboard-contract.md"
DOCS_INDEX = "docs/index.md"
UI_FILE = "src/ui/index.html"
API_MAIN_FILE = "src/api/main.py"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_phase23_contract_defines_single_canonical_ui_workflow_shell() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert content.startswith("# Phase 23 /ui Website-Facing Workflow Consolidation Contract")
    assert "Surface name: `Canonical /ui Workflow Shell`" in content
    assert "Runtime entrypoint: `/ui`" in content
    assert "src/ui/index.html" in content
    assert "src/api/main.py" in content
    assert "only canonical website-facing workflow entrypoint" in content


def test_phase23_contract_defines_navigation_and_non_live_boundaries() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert "Workflow: Run Analysis" in content
    assert "Workflow: Manage Watchlists" in content
    assert "Workflow: Review Ranked Watchlist Results" in content
    assert "Workflow: Inspect Runtime Data" in content
    assert "Workflow: Review Run Evidence" in content
    assert "live trading" in content
    assert "broker execution" in content
    assert "trader validation" in content
    assert "operational-readiness claims" in content
    assert "production-readiness claims" in content


def test_phase23_contract_retains_ops_p56_non_interference_boundary() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert "OPS-P56: Start bounded staged paper-trading runbook and evidence log #914" in content
    assert "remains the single operational run log issue" in content


def test_phase23_status_reflects_bounded_ui_consolidation() -> None:
    content = _read(PHASE23_STATUS_DOC)

    assert "## Status" in content
    assert "PARTIALLY IMPLEMENTED" in content
    assert "canonical `/ui` workflow shell" in content
    assert "src/ui/index.html" in content
    assert "src/api/main.py" in content
    assert "trader-readiness" in content
    assert "production-readiness" in content


def test_ui_surface_contains_canonical_navigation_and_boundary_markers() -> None:
    content = _read(UI_FILE)

    assert "Bounded Website-Facing Workflow Shell" in content
    assert 'id="ui-primary-navigation-contract"' in content
    assert 'id="ui-workflow-boundary-marker"' in content
    assert "single canonical website-facing workflow entrypoint" in content
    assert "No live trading" in content


def test_api_main_mounts_ui_and_does_not_mount_research_dashboard_route() -> None:
    content = _read(API_MAIN_FILE)

    assert 'app.mount("/ui"' in content
    assert '"/research-dashboard"' not in content


def test_index_includes_phase23_consolidation_contract_reference() -> None:
    index_content = _read(DOCS_INDEX)

    assert "phase-23-research-dashboard-contract.md" in index_content
    assert "Phase 23 /ui workflow consolidation contract" in index_content
    assert "Phase 23 | `Canonical /ui Workflow Shell` | PARTIALLY IMPLEMENTED" in index_content

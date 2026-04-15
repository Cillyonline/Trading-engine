from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
PHASE23_STATUS_DOC = "docs/architecture/phases/phase-23-status.md"
PHASE23_CONTRACT_DOC = "docs/operations/ui/phase-23-research-dashboard-contract.md"
PRODUCT_SURFACE_CONTRACT_DOC = "docs/operations/ui/product-surface-authority-contract.md"
DOCS_INDEX = "docs/index.md"
README_FILE = "README.md"
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
    assert "product-surface-authority-contract.md" in content
    assert "frontend/` remains non-authoritative unless governance promotion is explicitly documented" in content
    assert "Roadmap track alignment:" in content
    assert "Product Surface Track" in content
    assert "Strategy Readiness Track" in content


def test_phase23_contract_defines_navigation_and_non_live_boundaries() -> None:
    content = _read(PHASE23_CONTRACT_DOC)

    assert "Signal Review Workflow Step 1: Run Analysis" in content
    assert "Signal Review Workflow Step 2: Configure Watchlist Scope" in content
    assert "Signal Review Workflow Step 3: Evaluate Ranked Signals" in content
    assert "Signal Review Workflow Step 4: Inspect Backtest Artifacts" in content
    assert "Signal Review Workflow Step 5: Inspect Runtime Data" in content
    assert "Signal Review Workflow Step 6: Review Run Evidence" in content
    assert "live trading" in content
    assert "broker execution" in content
    assert "trader validation" in content
    assert "operational-readiness claims" in content
    assert "production-readiness claims" in content
    assert "technical backtest availability" in content
    assert "technical signal visibility" in content
    assert "trader validation status as a substitute for operational readiness status" in content


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
    assert 'id="ui-signal-review-workflow-contract"' in content
    assert "single canonical website-facing workflow entrypoint" in content
    assert "one bounded non-live signal review and trade-evaluation workflow" in content
    assert "Signal Review Workflow Step 3: Evaluate Ranked Signals" in content
    assert "Technical signal visibility is explicitly separate from trader validation and operational readiness decisions." in content
    assert "No live trading" in content
    assert "Backtest Entry/Read Panel" in content


def test_api_main_mounts_ui_and_does_not_mount_research_dashboard_route() -> None:
    content = _read(API_MAIN_FILE)

    assert 'app.mount("/ui"' in content
    assert '"/research-dashboard"' not in content


def test_index_includes_phase23_consolidation_contract_reference() -> None:
    index_content = _read(DOCS_INDEX)

    assert "phase-23-research-dashboard-contract.md" in index_content
    assert "product-surface-authority-contract.md" in index_content
    assert "Canonical /ui product-surface authority contract" in index_content
    assert "Phase 23 /ui workflow consolidation contract" in index_content
    assert "Phase 23 | `Canonical /ui Workflow Shell` | PARTIALLY IMPLEMENTED" in index_content
    assert "Roadmap track alignment:" in index_content
    assert "Product Surface Track: `/ui` is the canonical website-facing authority." in index_content
    assert "Strategy Readiness Track: readiness claims are governed separately" in index_content


def test_product_surface_contract_defines_canonical_authority_and_non_inference() -> None:
    content = _read(PRODUCT_SURFACE_CONTRACT_DOC)

    assert content.startswith("# Canonical /ui Product-Surface Authority Contract")
    assert "only canonical website-facing product-surface authority" in content
    assert "frontend/` is non-authoritative" in content
    assert "through explicit governance promotion documented in repository governance artifacts" in content
    assert "Technical Implementation Status" in content
    assert "Trader Validation Status" in content
    assert "Operational Readiness Status" in content
    assert "Roadmap Track Alignment" in content
    assert "Product Surface Track authority is owned by canonical `/ui`" in content
    assert "Strategy Readiness Track is a separate governance track" in content
    assert "Evidence in one class must not be inferred as evidence in another class." in content
    assert "live trading readiness" in content
    assert "broker execution readiness" in content
    assert "production readiness" in content


def test_readme_references_canonical_ui_product_surface_contract() -> None:
    content = _read(README_FILE)

    assert "product-surface-authority-contract.md" in content
    assert "Canonical /ui product-surface authority contract" in content
    assert "Product Surface Track authority: `/ui` is the canonical website-facing authority;" in content
    assert "frontend/` remains interim non-authoritative unless governance promotion is explicit." in content
    assert "Strategy Readiness Track boundary: readiness semantics are governed separately" in content
    assert "not be read as a production-readiness declaration." in content


def test_aligned_docs_do_not_state_readiness_inference_claims() -> None:
    aligned_docs = [
        README_FILE,
        DOCS_INDEX,
        PHASE23_CONTRACT_DOC,
        PRODUCT_SURFACE_CONTRACT_DOC,
    ]
    prohibited_phrases = [
        "implies live trading readiness",
        "implies broker execution readiness",
        "implies production readiness",
        "confers operational readiness",
        "is production ready",
    ]

    for path in aligned_docs:
        content = _read(path).lower()
        for phrase in prohibited_phrases:
            assert phrase not in content, f"{phrase!r} must not appear in {path}"

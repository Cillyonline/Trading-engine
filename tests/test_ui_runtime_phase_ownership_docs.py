from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_ui_runtime_phase_ownership_boundary_doc_maps_shared_ui_sections() -> None:
    content = (
        REPO_ROOT / "docs" / "architecture" / "ui-runtime-phase-ownership-boundary.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# /ui Runtime Phase Ownership Boundary")
    assert "Run Analysis / Analysis Results" in content
    assert "Watchlist Management / Saved Watchlists" in content
    assert "Recent Alerts card" in content
    assert "Shared-shell read-only inspection boundary" in content
    assert "does not prove" in content


def test_ui_runtime_phase_ownership_doc_defines_phase_non_inference_for_36_37_39_40_41() -> None:
    content = (
        REPO_ROOT / "docs" / "architecture" / "ui-runtime-phase-ownership-boundary.md"
    ).read_text(encoding="utf-8")

    assert "### Phase 36" in content
    assert "### Phase 37" in content
    assert "### Phase 39" in content
    assert "### Phase 40" in content
    assert "### Phase 41" in content
    assert "section adjacency" in content
    assert "not sufficient evidence" in content or "does not prove" in content


def test_index_and_phase41_docs_reference_shared_shell_boundary() -> None:
    index_content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")
    phase41_content = (
        REPO_ROOT / "docs" / "architecture" / "phases" / "phase-41-alerts.md"
    ).read_text(encoding="utf-8")

    assert "architecture/ui-runtime-phase-ownership-boundary.md" in index_content
    assert "Status: Planned" in phase41_content
    assert "shared-shell read-only inspection boundary" in phase41_content


def test_phase36_and_phase23_docs_define_canonical_ui_entrypoint_and_non_live_boundary() -> None:
    phase36_content = (
        REPO_ROOT / "docs" / "operations" / "ui" / "phase-36-web-activation-contract.md"
    ).read_text(encoding="utf-8")
    phase23_content = (
        REPO_ROOT / "docs" / "operations" / "ui" / "phase-23-research-dashboard-contract.md"
    ).read_text(encoding="utf-8")

    assert "only canonical workflow entrypoint" in phase36_content
    assert "does not imply trader validation, operational readiness, or production readiness" in phase36_content
    assert "only canonical website-facing workflow entrypoint" in phase23_content
    assert "live trading" in phase23_content
    assert "broker execution" in phase23_content
    assert "operational-readiness claims" in phase23_content

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_phase38_status_doc_defines_bounded_contract_and_evidence_classes() -> None:
    content = (
        REPO_ROOT / "docs" / "architecture" / "phases" / "phase-38-status.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# Phase 38 - Market Data Integration Status")
    assert "_load_stock_yahoo" in content
    assert "_load_crypto_binance" in content
    assert "Deterministic snapshot workflow boundary" in content
    assert "Runtime-safe usage boundary" in content
    assert "Evidence Requirements For Repository-Safe Market-Data Claims" in content
    assert "Remaining Unimplemented Scope After Status Correction" in content
    assert "does not claim" not in content.lower()


def test_phase38_master_roadmap_section_no_longer_claims_missing_direct_provider_integration() -> None:
    content = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "roadmap"
        / "cilly_trading_execution_roadmap_updated.md"
    ).read_text(encoding="utf-8")

    assert "## Phase 38 - Market Data Integration" in content
    assert "Direct provider loaders are repo-verifiable" in content
    assert "No repo-verifiable direct Yahoo Finance, Binance, or CCXT production integration module was confirmed." not in content


def test_execution_roadmap_and_usage_contract_reference_phase38_boundary() -> None:
    execution_content = (
        REPO_ROOT / "docs" / "architecture" / "roadmap" / "execution_roadmap.md"
    ).read_text(encoding="utf-8")
    usage_content = (
        REPO_ROOT / "docs" / "operations" / "api" / "usage_contract.md"
    ).read_text(encoding="utf-8")

    assert "Phase 38 | Market Data Integration" in execution_content
    assert "docs/architecture/phases/phase-38-status.md" in execution_content
    assert "Direct provider adapter status vs runtime-safe usage claims" in usage_content
    assert "The snapshot-only API contract remains the authoritative deterministic runtime boundary." in usage_content

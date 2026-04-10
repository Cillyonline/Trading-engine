"""Contract tests for P56 bounded adverse scenario matrix documentation."""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
P56_DOC = "docs/architecture/risk/p56-bounded-adverse-scenario-matrix.md"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_p56_doc_exists_and_has_required_sections() -> None:
    content = _read(P56_DOC)

    assert content.startswith("# P56-RISK: Bounded Adverse Scenario Matrix")
    assert "## Scope of Validation" in content
    assert "## Bounded Adverse Scenario Matrix" in content
    assert "## Explicit Expected Outcome Semantics" in content
    assert "## What Is Validated" in content
    assert "## Out of Scope / Not Claimed" in content


def test_p56_doc_covers_required_scenario_categories() -> None:
    content = _read(P56_DOC)

    assert "`P56-S1`" in content
    assert "`P56-S2`" in content
    assert "`P56-S3`" in content
    assert "`P56-S4`" in content
    assert "`P56-S5`" in content
    assert "`P56-S6`" in content
    assert "`P56-S7`" in content


def test_p56_doc_defines_explicit_non_claim_boundaries() -> None:
    content = _read(P56_DOC)

    assert "No live trading behavior." in content
    assert "No broker integration behavior." in content
    assert "No production-readiness claim." in content
    assert "No claim of complete risk maturity beyond these bounded scenarios." in content


def test_docs_index_links_p56_reference() -> None:
    content = _read("docs/index.md")

    assert "### P56-RISK Reference Materials" in content
    assert "architecture/risk/p56-bounded-adverse-scenario-matrix.md" in content

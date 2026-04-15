from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ARCHIVE_STANDARD = REPO_ROOT / "docs" / "archive" / "archive-deprecation-standard.md"
LEGACY_REGISTER = REPO_ROOT / "docs" / "deprecated" / "legacy-transition-register.md"
DOCS_INDEX = REPO_ROOT / "docs" / "index.md"
DEPRECATED_LEGACY_PATHS = [
    REPO_ROOT / "docs" / "api" / "public_api_boundary.md",
    REPO_ROOT / "docs" / "api" / "runtime_chart_data_contract.md",
    REPO_ROOT / "docs" / "ui" / "phase-39-test-plan.md",
]


def test_archive_deprecation_standard_closes_mandatory_header_code_fence() -> None:
    content = ARCHIVE_STANDARD.read_text(encoding="utf-8")

    assert "## Mandatory Header For Deprecated/Archived Documents" in content
    assert content.count("```md") == 1
    assert content.count("```") == 2
    assert (
        "```\n\n"
        "If no safe successor exists yet"
    ) in content


def test_archive_deprecation_standard_defines_required_terms_and_guardrails() -> None:
    content = ARCHIVE_STANDARD.read_text(encoding="utf-8")

    assert "`Deprecated`" in content
    assert "`Archived`" in content
    assert "`Superseded by`" in content
    assert "## Successor Chain Rule" in content
    assert "Successor chains must be finite and end on a non-archived document." in content
    assert "## Navigation And Canonical Guardrails" in content
    assert "must prefer active paths" in content
    assert "must not primarily reference `docs/archive/**`" in content
    assert "## Deprecation Flow" in content
    assert "## Archive Flow" in content
    assert "## Successor Chain Rule" in content
    assert "## Navigation And Canonical Guardrails" in content
    assert "## Review Checklist" in content


def test_legacy_transition_register_lists_expected_deprecated_paths_and_successors() -> None:
    content = LEGACY_REGISTER.read_text(encoding="utf-8")

    assert "`docs/api/public_api_boundary.md`" in content
    assert "`docs/operations/api/public_api_boundary.md`" in content
    assert "`docs/api/runtime_chart_data_contract.md`" in content
    assert "`docs/operations/api/runtime_chart_data_contract.md`" in content
    assert "`docs/ui/phase-39-test-plan.md`" in content
    assert "`docs/operations/ui/phase-39-test-plan.md`" in content


def test_docs_index_does_not_link_archive_or_deprecated_directories() -> None:
    content = DOCS_INDEX.read_text(encoding="utf-8")

    assert "docs/archive/" not in content
    assert "docs/deprecated/" not in content
    assert "archive/" not in content
    assert "deprecated/" not in content


def test_deprecated_legacy_files_include_required_status_metadata() -> None:
    for path in DEPRECATED_LEGACY_PATHS:
        content = path.read_text(encoding="utf-8")
        assert "- Class: Deprecated" in content, f"missing deprecated class in {path}"
        assert "- Superseded by:" in content, f"missing successor in {path}"

from __future__ import annotations

import pytest

from tests.utils.consumer_contract_helpers import (
    REPO_ROOT,
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


PHASE44_DOC = "docs/operations/runtime/phase-44-paper-operator-workflow.md"
DOCS_INDEX = "docs/index.md"
OPERATOR_CHECKLIST = "docs/operations/runtime/paper-deployment-operator-checklist.md"
PAPER_INSPECTION_API_DOC = "docs/api/paper_inspection.md"


def test_phase44_workflow_doc_defines_bounded_operator_flow_and_surfaces() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert_starts_with(content, "# Phase 44 Bounded Paper Operator Workflow")
    assert_contains_all(
        content,
        "## Bounded Workflow Claim",
        "## Required Runtime Surfaces",
        "GET /trading-core/orders",
        "GET /trading-core/execution-events",
        "GET /trading-core/trades",
        "GET /trading-core/positions",
        "GET /paper/trades",
        "GET /paper/positions",
        "GET /paper/account",
        "GET /paper/reconciliation",
        "GET /paper/workflow",
        "## Explicit Operator Steps",
        "## Workflow Boundary",
        "## Minimum Operator Evidence",
        "tests/test_api_paper_inspection_read.py",
        "python -m pytest",
    )


def test_phase44_workflow_doc_preserves_phase24_boundary_and_non_goals() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert_contains_all(
        content,
        "## Phase 24 vs Phase 44 Boundary",
        "Phase 24 (implemented simulator governance boundary)",
        "Phase 44 (bounded runtime workflow claim in this phase slice)",
        "## Explicit Non-Goals",
        "Live trading",
        "Broker integration",
        "Mutation-heavy order-entry workflow",
    )


def test_docs_index_links_phase44_workflow_contract() -> None:
    content = read_repo_text(DOCS_INDEX)

    assert_contains_all(
        content,
        "operations/runtime/phase-44-paper-operator-workflow.md",
        "### Phase 44 Reference Materials",
    )


def test_phase44_workflow_doc_defines_long_run_evaluation_cadence() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert "## Long-Run Evaluation Cadence" in content
    assert "strategy change" in content.lower()
    assert "process restart" in content.lower()
    assert "periodic" in content.lower()


def test_phase44_workflow_doc_defines_strategy_change_comparison_boundary() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert_contains_all(
        content,
        "## Strategy-Change Comparison Boundary",
        "Pre-Change Baseline Capture",
        "Post-Change Comparison",
        "Prohibited Comparison Shortcuts",
        "mismatches: 0",
    )


def test_phase44_workflow_doc_defines_review_artifact_checklist() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert_contains_all(
        content,
        "## Review Artifact Checklist",
        "| R1 |",
        "| R7 |",
        "`GET /paper/reconciliation`",
        "`GET /paper/workflow`",
        "R1–R7",
    )


def test_phase44_workflow_doc_defines_restart_and_recovery_review() -> None:
    content = read_repo_text(PHASE44_DOC)

    assert_contains_all(
        content,
        "## Restart and Recovery Review",
        "Recovery Verification Steps",
        "ok: true",
        "mismatches: 0",
    )


def test_phase44_operator_checklist_includes_long_run_review_section() -> None:
    content = read_repo_text(OPERATOR_CHECKLIST)

    assert_contains_all(
        content,
        "## E) Long-Run Paper Review Evidence",
        "R1–R7",
        "EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT",
        "EVIDENCE_COMPLETED_OPERATOR_CHECKLIST",
    )
    assert "strategy-change comparison baseline" in content.lower()
    assert "post-restart recovery verification" in content.lower()


def test_paper_inspection_api_doc_cross_references_long_run_workflow() -> None:
    content = read_repo_text(PAPER_INSPECTION_API_DOC)

    assert_contains_all(
        content,
        "## Long-Run Evaluation and Review Workflow",
        "phase-44-paper-operator-workflow.md",
        "R1–R7",
    )


# ---------------------------------------------------------------------------
# Unit tests for the canonical bounded contract-test helpers
# ---------------------------------------------------------------------------
#
# These tests cover the shared helpers defined in
# ``tests.utils.consumer_contract_helpers`` and exposed via
# ``tests/conftest.py``. They confirm:
#   * deterministic, read-only behavior of ``read_repo_text``
#   * deterministic pass/fail equivalence of ``assert_contains_all`` and
#     ``assert_starts_with`` relative to the expanded forms they replace
#   * fixture wrappers produce the same callables/values
# Helpers do not infer runtime behavior or imply live-trading readiness.


def test_helper_repo_root_points_to_repository_root() -> None:
    # The repo root must contain pytest.ini and a tests directory; this
    # is a deterministic check that does not depend on runtime state.
    assert (REPO_ROOT / "pytest.ini").is_file()
    assert (REPO_ROOT / "tests").is_dir()


def test_helper_read_repo_text_reads_known_file_as_utf8() -> None:
    pytest_ini = read_repo_text("pytest.ini")
    assert isinstance(pytest_ini, str)
    assert "[pytest]" in pytest_ini


def test_helper_assert_contains_all_passes_when_all_substrings_present() -> None:
    content = "alpha beta gamma"
    assert_contains_all(content, "alpha", "gamma")


def test_helper_assert_contains_all_raises_on_first_missing_substring() -> None:
    with pytest.raises(AssertionError) as excinfo:
        assert_contains_all("alpha beta", "alpha", "delta", "gamma")
    assert "delta" in str(excinfo.value)


def test_helper_assert_starts_with_matches_string_startswith() -> None:
    assert_starts_with("# heading", "# heading")
    with pytest.raises(AssertionError):
        assert_starts_with("# heading", "## heading")


def test_helper_fixtures_expose_canonical_helpers(
    repo_root,
    read_repo_doc,
    doc_assert_contains_all,
    doc_assert_starts_with,
) -> None:
    assert repo_root == REPO_ROOT
    assert read_repo_doc("pytest.ini") == read_repo_text("pytest.ini")
    doc_assert_contains_all("alpha beta gamma", "alpha", "gamma")
    doc_assert_starts_with("# heading", "# heading")

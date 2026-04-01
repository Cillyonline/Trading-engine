"""Tests for P53 automated review operations.

Validates that documentation, scripts, and checklist align to the
automated reconciliation, weekly review, and restart/recovery workflow
defined in OPS-P53.
"""

from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


# ---------------------------------------------------------------------------
# P53 automation doc tests
# ---------------------------------------------------------------------------


def test_p53_automation_doc_exists_and_defines_scope() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert content.startswith("# P53 Automated Review Operations")
    assert "## Purpose" in content
    assert "## Scope Boundary" in content
    assert "post-run reconciliation" in content.lower()
    assert "weekly review" in content.lower()
    assert "restart" in content.lower()


def test_p53_automation_doc_defines_post_run_reconciliation_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Post-Run Reconciliation" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "RECONCILIATION:PASS" in content
    assert "RECONCILIATION:FAIL" in content
    assert "runs/reconciliation/" in content


def test_p53_automation_doc_defines_weekly_review_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Weekly Review Artifact Generation" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "WEEKLY_REVIEW:PASS" in content
    assert "WEEKLY_REVIEW:FAIL" in content
    assert "R1" in content
    assert "R7" in content
    assert "runs/weekly-review/" in content


def test_p53_automation_doc_defines_restart_evidence_script() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "### Restart/Recovery Evidence Capture" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "pre-restart" in content
    assert "post-restart" in content
    assert "RESTART_EVIDENCE" in content
    assert "runs/restart-evidence/" in content


def test_p53_automation_doc_defines_evidence_file_format() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Evidence File Format" in content
    assert "ran_at" in content
    assert "db_path" in content
    assert "status" in content
    assert "evidence_file" in content
    assert "summary" in content


def test_p53_automation_doc_maps_to_phase44_workflow() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Integration with Phase 44 Operator Workflow" in content
    assert "End-of-session reconciliation" in content
    assert "Periodic weekly review" in content
    assert "Pre-restart baseline" in content
    assert "Post-restart recovery verification" in content


def test_p53_automation_doc_maps_to_operator_checklist() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Operator Checklist Integration" in content
    assert "E1" in content
    assert "E2" in content
    assert "E3" in content
    assert "E4" in content


def test_p53_automation_doc_references_state_authority() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "p53-automated-review-operations.md"
    ).read_text(encoding="utf-8")

    assert "## Singular State Authority" in content
    assert "SqliteCanonicalExecutionRepository" in content
    assert "paper_state_authority.py" in content


# ---------------------------------------------------------------------------
# Phase 44 workflow doc references P53
# ---------------------------------------------------------------------------


def test_phase44_workflow_doc_references_p53_automation() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
    ).read_text(encoding="utf-8")

    assert "## P53 Automated Review Operations" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Paper inspection API doc references P53
# ---------------------------------------------------------------------------


def test_paper_inspection_api_doc_references_p53_automation() -> None:
    content = (REPO_ROOT / "docs" / "api" / "paper_inspection.md").read_text(encoding="utf-8")

    assert "## Automated Reconciliation and Review" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Operator checklist references automation
# ---------------------------------------------------------------------------


def test_operator_checklist_references_automated_review_commands() -> None:
    content = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "paper-deployment-operator-checklist.md"
    ).read_text(encoding="utf-8")

    assert "### Automated Review Evidence Commands" in content
    assert "scripts/run_post_run_reconciliation.py" in content
    assert "scripts/generate_weekly_review.py" in content
    assert "scripts/capture_restart_evidence.py" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Docs index links P53
# ---------------------------------------------------------------------------


def test_docs_index_links_p53_automation() -> None:
    content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "### P53 Reference Materials" in content
    assert "p53-automated-review-operations.md" in content


# ---------------------------------------------------------------------------
# Script files exist
# ---------------------------------------------------------------------------


def test_post_run_reconciliation_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "run_post_run_reconciliation.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "run_reconciliation" in content
    assert "RECONCILIATION:PASS" in content
    assert "RECONCILIATION:FAIL" in content
    assert "evidence_file" in content


def test_weekly_review_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "generate_weekly_review.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "generate_weekly_review" in content
    assert "WEEKLY_REVIEW:PASS" in content
    assert "WEEKLY_REVIEW:FAIL" in content
    assert "R1" in content
    assert "R7" in content


def test_restart_evidence_script_exists() -> None:
    script = REPO_ROOT / "scripts" / "capture_restart_evidence.py"
    assert script.exists(), f"Expected script at {script}"
    content = script.read_text(encoding="utf-8")
    assert "capture_restart_evidence" in content
    assert "RESTART_EVIDENCE" in content
    assert "pre-restart" in content
    assert "post-restart" in content
    assert "baseline" in content


# ---------------------------------------------------------------------------
# Script contract consistency
# ---------------------------------------------------------------------------


def test_all_scripts_use_canonical_state_authority() -> None:
    """All P53 scripts must import from the canonical execution repository."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "SqliteCanonicalExecutionRepository" in content, (
            f"{script_name} must use SqliteCanonicalExecutionRepository"
        )
        assert "build_paper_reconciliation_mismatches" in content, (
            f"{script_name} must use build_paper_reconciliation_mismatches"
        )


def test_all_scripts_write_evidence_files() -> None:
    """All P53 scripts must produce evidence JSON output."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "evidence_file" in content, (
            f"{script_name} must reference evidence_file"
        )
        assert ".json" in content, (
            f"{script_name} must produce JSON evidence"
        )
        assert "evidence_dir" in content or "evidence-dir" in content, (
            f"{script_name} must accept evidence directory"
        )


def test_all_scripts_define_exit_codes() -> None:
    """All P53 scripts must define bounded exit codes."""
    for script_name in (
        "run_post_run_reconciliation.py",
        "generate_weekly_review.py",
        "capture_restart_evidence.py",
    ):
        content = (REPO_ROOT / "scripts" / script_name).read_text(encoding="utf-8")
        assert "EXIT_" in content, (
            f"{script_name} must define explicit exit codes"
        )
        assert "def main()" in content, (
            f"{script_name} must define main()"
        )
        assert '__name__ == "__main__"' in content, (
            f"{script_name} must have __main__ guard"
        )

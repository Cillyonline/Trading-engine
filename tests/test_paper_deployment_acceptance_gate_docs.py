from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_paper_acceptance_gate_doc_defines_bounded_binary_sequence() -> None:
    content = (
        REPO_ROOT
        / "docs"
        / "operations"
        / "runtime"
        / "paper-deployment-acceptance-gate.md"
    ).read_text(encoding="utf-8")

    assert content.startswith(
        "# Paper Deployment Acceptance Gate (Staging -> Paper-Install-Ready)"
    )
    assert "`repository-runs-locally`" in content
    assert "`server-ready (staging)`" in content
    assert "`paper-install-ready`" in content
    assert "## Bounded Acceptance Sequence (Canonical and Reproducible)" in content
    assert "### Step 1 - Staging deployment validation" in content
    assert "### Step 2 - Explicit health/readiness evidence capture" in content
    assert "### Step 3 - Paper consistency contract tests" in content
    assert "### Step 4 - Full repository regression gate" in content
    assert "### Step 5 - Operator checklist completion" in content


def test_paper_acceptance_gate_doc_names_required_evidence_outputs_and_markers() -> None:
    content = (
        REPO_ROOT
        / "docs"
        / "operations"
        / "runtime"
        / "paper-deployment-acceptance-gate.md"
    ).read_text(encoding="utf-8")

    assert "STAGING_VALIDATE:CONFIG_OK" in content
    assert "STAGING_VALIDATE:UP_OK" in content
    assert "STAGING_VALIDATE:HEALTH_OK" in content
    assert "STAGING_VALIDATE:RESTART_OK" in content
    assert "STAGING_VALIDATE:POST_RESTART_HEALTH_OK" in content
    assert "STAGING_VALIDATE:SUCCESS" in content
    assert "EVIDENCE_STAGING_VALIDATION_LOG" in content
    assert "EVIDENCE_STAGING_HEALTH_SNAPSHOTS" in content
    assert "EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT" in content
    assert "EVIDENCE_FULL_PYTEST_OUTPUT" in content
    assert "EVIDENCE_COMPLETED_OPERATOR_CHECKLIST" in content
    assert "## Required Evidence Outputs (Exact Set)" in content
    assert "## Pass/Fail Criteria (Binary)" in content
    assert "ACCEPTED: PAPER_INSTALL_READY" in content
    assert "NOT ACCEPTED: REMAIN STAGING" in content


def test_operator_checklist_matches_acceptance_gate_wording_and_evidence_contract() -> None:
    checklist = (
        REPO_ROOT
        / "docs"
        / "operations"
        / "runtime"
        / "paper-deployment-operator-checklist.md"
    ).read_text(encoding="utf-8")
    staging_doc = (
        REPO_ROOT / "docs" / "operations" / "runtime" / "staging-server-deployment.md"
    ).read_text(encoding="utf-8")
    gate_doc = (
        REPO_ROOT
        / "docs"
        / "operations"
        / "runtime"
        / "paper-deployment-acceptance-gate.md"
    ).read_text(encoding="utf-8")

    for evidence_name in (
        "EVIDENCE_STAGING_VALIDATION_LOG",
        "EVIDENCE_STAGING_HEALTH_SNAPSHOTS",
        "EVIDENCE_PAPER_CONSISTENCY_TEST_OUTPUT",
        "EVIDENCE_FULL_PYTEST_OUTPUT",
        "EVIDENCE_COMPLETED_OPERATOR_CHECKLIST",
    ):
        assert evidence_name in checklist
        assert evidence_name in gate_doc

    assert "ACCEPTED: PAPER_INSTALL_READY" in checklist
    assert "NOT ACCEPTED: REMAIN STAGING" in checklist
    assert "`server-ready (staging)`" in staging_doc
    assert "`paper-install-ready`" in staging_doc

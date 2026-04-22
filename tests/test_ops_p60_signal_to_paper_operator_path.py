"""Contract tests for OPS-P60: bounded operator path from signals to paper execution.

Acceptance criteria verified:
    AC1: It is clearly documented whether an authoritative bounded path from
         eligible signals to canonical paper execution state exists.
    AC2: If the path exists, the authoritative inputs, policy gates, and
         minimal operator/runtime path are clearly described.
    AC3: If the path is not fully documented, the remaining gap is named
         without overclaim.
    AC4: Changes remain bounded and minimal.
    AC5: No live/broker/production-readiness claims are introduced.
"""

from __future__ import annotations

from tests.utils.consumer_contract_helpers import (
    REPO_ROOT,
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


P60_DOC_PATH = "docs/operations/runtime/p60-signal-to-paper-operator-path.md"
P60_SCRIPT_PATH = "scripts/run_paper_execution_cycle.py"
POLICY_DOC_PATH = "docs/operations/runtime/signal_to_paper_execution_policy.md"
WORKFLOW_DOC_PATH = "docs/operations/runtime/phase-44-paper-operator-workflow.md"


# ---------------------------------------------------------------------------
# AC1: Authoritative bounded path is documented
# ---------------------------------------------------------------------------


def test_p60_document_exists_with_required_header() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_starts_with(
        content,
        "# OPS-P60: Bounded Operator Path from Eligible Signals to Paper Execution State",
    )


def test_p60_path_status_is_explicitly_stated() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Operator Path Status",
        "Path exists: YES",
    )


def test_p60_authoritative_components_table_exists() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "### Authoritative Components",
        "| Signal source |",
        "| Execution policy |",
        "| Execution worker |",
        "| State authority |",
        "| Operator script |",
        "| Inspection surfaces |",
        "| Reconciliation |",
    )


# ---------------------------------------------------------------------------
# AC2: Inputs, policy gates, and operator path are described
# ---------------------------------------------------------------------------


def test_p60_operator_path_steps_are_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Bounded Operator Path (Step-by-Step)",
        "Read eligible signals",
        "Instantiate worker",
        "Process signals",
        "Persist canonical entities",
        "Verify via inspection",
    )


def test_p60_policy_gates_are_listed() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "### Policy Gates",
        "`reject:invalid_signal_fields`",
        "`skip:score_below_threshold`",
        "`skip:duplicate_entry`",
        "`skip:cooldown_active`",
        "`reject:position_size_exceeds_limit`",
        "`reject:total_exposure_exceeds_limit`",
        "`reject:concurrent_position_limit_exceeded`",
    )


def test_p60_operator_script_is_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Operator Script",
        "run_paper_execution_cycle.py",
        "### Usage",
        "### Inputs",
        "### Outputs",
    )


def test_p60_operator_script_file_exists() -> None:
    assert (REPO_ROOT / P60_SCRIPT_PATH).exists()


def test_p60_post_execution_verification_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Post-Execution Verification",
        "/paper/trades",
        "/paper/positions",
        "/paper/account",
        "/paper/reconciliation",
    )


def test_p60_decision_usefulness_audit_is_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)

    assert_contains_all(
        content,
        "## Decision Evidence Usefulness Audit",
        "metadata.bounded_decision_to_paper_match",
        "metadata.bounded_decision_to_paper_usefulness_audit",
        "paper_trade_id",
        "`explanatory`",
        "`weak`",
        "`misleading`",
    )


# ---------------------------------------------------------------------------
# AC3: Gap analysis is explicit without overclaim
# ---------------------------------------------------------------------------


def test_p60_gap_analysis_is_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Gap Analysis",
        "### Previously Missing",
        "### Remaining Boundaries",
    )


def test_p60_remaining_boundaries_are_honest() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert "operator-invoked" in content
    assert "no automated scheduler" in content.lower() or "No automated scheduler" in content


# ---------------------------------------------------------------------------
# AC4: Changes are bounded and minimal
# ---------------------------------------------------------------------------


def test_p60_references_existing_policy_and_components() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "signal_to_paper_execution_policy.md",
        "paper_execution_worker.py",
        "paper_state_authority.py",
        "phase-44-paper-operator-workflow.md",
    )


def test_p60_references_section_exists() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert "## References" in content


# ---------------------------------------------------------------------------
# AC5: Non-live boundary — no live/broker/production claims
# ---------------------------------------------------------------------------


def test_p60_non_live_boundary_is_explicit() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## Non-Live Boundary",
        "No live orders are placed.",
        "No broker APIs are called.",
        "No real capital is at risk.",
        "does not imply live-trading readiness",
    )


def test_p60_usefulness_audit_keeps_claim_boundary_explicit() -> None:
    content = read_repo_text(P60_DOC_PATH)

    assert_contains_all(
        content,
        "This audit is bounded to non-live usefulness only.",
        "does not imply trader",
        "profitability forecasting",
        "operational",
    )


def test_p60_script_contains_non_live_boundary() -> None:
    content = read_repo_text(P60_SCRIPT_PATH)
    assert "non-live" in content.lower() or "Non-live" in content
    assert "No live orders" in content or "no live orders" in content.lower()
    assert "no broker APIs" in content.lower() or "No broker APIs" in content or "no broker apis" in content.lower()


# ---------------------------------------------------------------------------
# AC1+AC2: Operator script structure matches P53 pattern
# ---------------------------------------------------------------------------


def test_p60_script_defines_exit_codes() -> None:
    content = read_repo_text(P60_SCRIPT_PATH)
    assert_contains_all(
        content,
        "EXIT_CYCLE_PASS",
        "EXIT_CYCLE_NO_ELIGIBLE",
        "EXIT_RUNTIME_ERROR",
    )


def test_p60_script_uses_canonical_worker_and_repo() -> None:
    content = read_repo_text(P60_SCRIPT_PATH)
    assert_contains_all(
        content,
        "BoundedPaperExecutionWorker",
        "SqliteCanonicalExecutionRepository",
        "SqliteSignalRepository",
    )


def test_p60_script_writes_evidence() -> None:
    content = read_repo_text(P60_SCRIPT_PATH)
    assert "evidence" in content.lower()
    assert "json" in content.lower()


# ---------------------------------------------------------------------------
# AC2: Workflow doc references P60
# ---------------------------------------------------------------------------


def test_workflow_doc_references_p60() -> None:
    content = read_repo_text(WORKFLOW_DOC_PATH)
    assert "P60" in content or "p60" in content


# ---------------------------------------------------------------------------
# AC1+AC2: End-to-end traceability chain is documented
# ---------------------------------------------------------------------------


def test_p60_end_to_end_traceability_chain_is_documented() -> None:
    content = read_repo_text(P60_DOC_PATH)
    assert_contains_all(
        content,
        "## End-to-End Traceability Chain",
        "signal_to_paper_reconciliation_traceability.paper_audit.v1",
        "`signal_analysis`",
        "`decision_card`",
        "`paper_trade`",
        "`reconciliation`",
        "`matched`",
        "`open`",
        "`missing`",
        "`invalid`",
    )
    assert "non-live" in content.lower()


def test_workflow_doc_references_traceability_chain() -> None:
    content = read_repo_text(WORKFLOW_DOC_PATH)
    assert_contains_all(
        content,
        "## End-to-End Traceability Chain",
        "traceability_chain",
        "signal_to_paper_reconciliation_traceability.paper_audit.v1",
        "`matched`",
        "`open`",
        "`missing`",
        "`invalid`",
    )

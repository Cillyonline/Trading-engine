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

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]

P60_DOC_PATH = "docs/operations/runtime/p60-signal-to-paper-operator-path.md"
P60_SCRIPT_PATH = "scripts/run_paper_execution_cycle.py"
POLICY_DOC_PATH = "docs/operations/runtime/signal_to_paper_execution_policy.md"
WORKFLOW_DOC_PATH = "docs/operations/runtime/phase-44-paper-operator-workflow.md"


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# AC1: Authoritative bounded path is documented
# ---------------------------------------------------------------------------


def test_p60_document_exists_with_required_header() -> None:
    content = _read(P60_DOC_PATH)
    assert content.startswith(
        "# OPS-P60: Bounded Operator Path from Eligible Signals to Paper Execution State"
    )


def test_p60_path_status_is_explicitly_stated() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Operator Path Status" in content
    assert "Path exists: YES" in content


def test_p60_authoritative_components_table_exists() -> None:
    content = _read(P60_DOC_PATH)
    assert "### Authoritative Components" in content
    assert "| Signal source |" in content
    assert "| Execution policy |" in content
    assert "| Execution worker |" in content
    assert "| State authority |" in content
    assert "| Operator script |" in content
    assert "| Inspection surfaces |" in content
    assert "| Reconciliation |" in content


# ---------------------------------------------------------------------------
# AC2: Inputs, policy gates, and operator path are described
# ---------------------------------------------------------------------------


def test_p60_operator_path_steps_are_documented() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Bounded Operator Path (Step-by-Step)" in content
    assert "Read eligible signals" in content
    assert "Instantiate worker" in content
    assert "Process signals" in content
    assert "Persist canonical entities" in content
    assert "Verify via inspection" in content


def test_p60_policy_gates_are_listed() -> None:
    content = _read(P60_DOC_PATH)
    assert "### Policy Gates" in content
    assert "`reject:invalid_signal_fields`" in content
    assert "`skip:score_below_threshold`" in content
    assert "`skip:duplicate_entry`" in content
    assert "`skip:cooldown_active`" in content
    assert "`reject:position_size_exceeds_limit`" in content
    assert "`reject:total_exposure_exceeds_limit`" in content
    assert "`reject:concurrent_position_limit_exceeded`" in content


def test_p60_operator_script_is_documented() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Operator Script" in content
    assert "run_paper_execution_cycle.py" in content
    assert "### Usage" in content
    assert "### Inputs" in content
    assert "### Outputs" in content


def test_p60_operator_script_file_exists() -> None:
    assert (REPO_ROOT / P60_SCRIPT_PATH).exists()


def test_p60_post_execution_verification_documented() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Post-Execution Verification" in content
    assert "/paper/trades" in content
    assert "/paper/positions" in content
    assert "/paper/account" in content
    assert "/paper/reconciliation" in content


def test_p60_decision_usefulness_audit_is_documented() -> None:
    content = _read(P60_DOC_PATH)

    assert "## Decision Evidence Usefulness Audit" in content
    assert "metadata.bounded_decision_to_paper_match" in content
    assert "metadata.bounded_decision_to_paper_usefulness_audit" in content
    assert "paper_trade_id" in content
    assert "`explanatory`" in content
    assert "`weak`" in content
    assert "`misleading`" in content


# ---------------------------------------------------------------------------
# AC3: Gap analysis is explicit without overclaim
# ---------------------------------------------------------------------------


def test_p60_gap_analysis_is_documented() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Gap Analysis" in content
    assert "### Previously Missing" in content
    assert "### Remaining Boundaries" in content


def test_p60_remaining_boundaries_are_honest() -> None:
    content = _read(P60_DOC_PATH)
    assert "operator-invoked" in content
    assert "no automated scheduler" in content.lower() or "No automated scheduler" in content


# ---------------------------------------------------------------------------
# AC4: Changes are bounded and minimal
# ---------------------------------------------------------------------------


def test_p60_references_existing_policy_and_components() -> None:
    content = _read(P60_DOC_PATH)
    assert "signal_to_paper_execution_policy.md" in content
    assert "paper_execution_worker.py" in content
    assert "paper_state_authority.py" in content
    assert "phase-44-paper-operator-workflow.md" in content


def test_p60_references_section_exists() -> None:
    content = _read(P60_DOC_PATH)
    assert "## References" in content


# ---------------------------------------------------------------------------
# AC5: Non-live boundary — no live/broker/production claims
# ---------------------------------------------------------------------------


def test_p60_non_live_boundary_is_explicit() -> None:
    content = _read(P60_DOC_PATH)
    assert "## Non-Live Boundary" in content
    assert "No live orders are placed." in content
    assert "No broker APIs are called." in content
    assert "No real capital is at risk." in content
    assert "does not imply live-trading readiness" in content


def test_p60_usefulness_audit_keeps_claim_boundary_explicit() -> None:
    content = _read(P60_DOC_PATH)

    assert "This audit is bounded to non-live usefulness only." in content
    assert "does not imply trader" in content
    assert "profitability forecasting" in content
    assert "operational" in content


def test_p60_script_contains_non_live_boundary() -> None:
    content = _read(P60_SCRIPT_PATH)
    assert "non-live" in content.lower() or "Non-live" in content
    assert "No live orders" in content or "no live orders" in content.lower()
    assert "no broker APIs" in content.lower() or "No broker APIs" in content or "no broker apis" in content.lower()


# ---------------------------------------------------------------------------
# AC1+AC2: Operator script structure matches P53 pattern
# ---------------------------------------------------------------------------


def test_p60_script_defines_exit_codes() -> None:
    content = _read(P60_SCRIPT_PATH)
    assert "EXIT_CYCLE_PASS" in content
    assert "EXIT_CYCLE_NO_ELIGIBLE" in content
    assert "EXIT_RUNTIME_ERROR" in content


def test_p60_script_uses_canonical_worker_and_repo() -> None:
    content = _read(P60_SCRIPT_PATH)
    assert "BoundedPaperExecutionWorker" in content
    assert "SqliteCanonicalExecutionRepository" in content
    assert "SqliteSignalRepository" in content


def test_p60_script_writes_evidence() -> None:
    content = _read(P60_SCRIPT_PATH)
    assert "evidence" in content.lower()
    assert "json" in content.lower()


# ---------------------------------------------------------------------------
# AC2: Workflow doc references P60
# ---------------------------------------------------------------------------


def test_workflow_doc_references_p60() -> None:
    content = _read(WORKFLOW_DOC_PATH)
    assert "P60" in content or "p60" in content


# ---------------------------------------------------------------------------
# AC1+AC2: End-to-end traceability chain is documented
# ---------------------------------------------------------------------------


def test_p60_end_to_end_traceability_chain_is_documented() -> None:
    content = _read(P60_DOC_PATH)
    assert "## End-to-End Traceability Chain" in content
    assert "signal_to_paper_reconciliation_traceability.paper_audit.v1" in content
    assert "`signal_analysis`" in content
    assert "`decision_card`" in content
    assert "`paper_trade`" in content
    assert "`reconciliation`" in content
    for status in ("`matched`", "`open`", "`missing`", "`invalid`"):
        assert status in content
    assert "non-live" in content.lower()


def test_workflow_doc_references_traceability_chain() -> None:
    content = _read(WORKFLOW_DOC_PATH)
    assert "## End-to-End Traceability Chain" in content
    assert "traceability_chain" in content
    assert "signal_to_paper_reconciliation_traceability.paper_audit.v1" in content
    for status in ("`matched`", "`open`", "`missing`", "`invalid`"):
        assert status in content

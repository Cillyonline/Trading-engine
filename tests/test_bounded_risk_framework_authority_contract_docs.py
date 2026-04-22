"""Docs contract tests for the bounded risk-framework authority contract.

Asserts the canonical bounded risk-framework authority contract document
defines the canonical authority id, the canonical reason-code vocabulary,
deterministic precedence, fail-closed bounded evidence discipline, and the
required non-live / non-readiness wording boundaries.

Also asserts that risk-governance documentation cross-references the
canonical authority contract.

This is bounded non-live technical evidence only and is not live-trading,
broker, trader-validation, or operational-readiness evidence.
"""

from __future__ import annotations

from cilly_trading.engine.risk import (
    APPROVED_RISK_FRAMEWORK_REASON_CODE,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
)
from cilly_trading.non_live_evaluation_contract import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
)

from tests.utils.consumer_contract_helpers import (
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


AUTHORITY_DOC = BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC
GOVERNANCE_OVERLAY_DOC = "docs/governance/bounded-risk-framework-authority.md"
RISK_FRAMEWORK_DOC = "docs/architecture/risk/risk_framework.md"
NON_LIVE_CONTRACT_DOC = "docs/architecture/risk/non_live_evaluation_contract.md"


def test_authority_doc_starts_with_canonical_heading() -> None:
    assert_starts_with(
        read_repo_text(AUTHORITY_DOC),
        "# Bounded Risk-Framework Authority Contract",
    )


def test_authority_doc_declares_canonical_authority_id() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert_contains_all(
        content,
        "Canonical authority id:",
        BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
        "ROADMAP_MASTER.md Phase 27",
    )


def test_authority_doc_declares_canonical_reason_vocabulary() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert APPROVED_RISK_FRAMEWORK_REASON_CODE in content
    for code in CANONICAL_RISK_REJECTION_REASON_CODES:
        assert code in content, code


def test_authority_doc_documents_deterministic_precedence_and_evaluation() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert_contains_all(
        content,
        "Deterministic Risk-Boundary Evaluation",
        "identical covered inputs produce identical",
        "precedence",
        "evaluated_at",
        "policy_evidence",
    )


def test_authority_doc_documents_fail_closed_bounded_evidence_discipline() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert_contains_all(
        content,
        "Fail-Closed Bounded Evidence Discipline",
        "RiskApprovalMissingError",
        "RiskRejectedError",
        "approved` flag conflicts",
        "unsupported risk-framework reason",
        "never silently degrades to an APPROVED",
    )


def test_authority_doc_keeps_non_live_and_non_readiness_wording_boundaries() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert_contains_all(
        content,
        "bounded non-live technical evidence",
        "does not authorize live trading",
        "does not authorize broker integration",
        "is not trader-validation evidence",
        "is not operational-readiness evidence",
        "is not a profitability or edge claim",
        "does not imply production readiness",
    )

    lowered = content.lower()
    forbidden_phrases = (
        "live-trading ready",
        "production ready",
        "profitability guarantee",
        "broker go-live",
    )
    for phrase in forbidden_phrases:
        assert phrase not in lowered, phrase


def test_authority_doc_lists_canonical_authoritative_surfaces() -> None:
    content = read_repo_text(AUTHORITY_DOC)

    assert_contains_all(
        content,
        "src/cilly_trading/risk_framework/risk_evaluator.py",
        "src/cilly_trading/risk_framework/contract.py",
        "src/cilly_trading/risk_framework/allocation_rules.py",
        "src/cilly_trading/risk_framework/kill_switch.py",
        "src/cilly_trading/non_live_evaluation_contract.py",
        "src/cilly_trading/engine/risk/gate.py",
        "src/cilly_trading/engine/risk/authority.py",
    )


def test_governance_overlay_doc_references_canonical_authority_contract() -> None:
    content = read_repo_text(GOVERNANCE_OVERLAY_DOC)

    assert_starts_with(content, "# Bounded Risk-Framework Authority (Governance Overlay)")
    assert_contains_all(
        content,
        AUTHORITY_DOC,
        BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
        "ROADMAP_MASTER.md` Phase 27",
        "it is not live-trading authorization",
        "it is not broker-execution authorization",
        "it is not trader validation",
        "it is not operational readiness",
        "it is not production readiness",
        "it is not a profitability or edge claim",
    )


def test_risk_governance_docs_reference_canonical_authority_contract() -> None:
    risk_framework_content = read_repo_text(RISK_FRAMEWORK_DOC)
    non_live_content = read_repo_text(NON_LIVE_CONTRACT_DOC)

    for content in (risk_framework_content, non_live_content):
        assert_contains_all(
            content,
            "bounded_risk_framework_authority_contract.md",
            BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
        )

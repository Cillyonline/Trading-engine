from __future__ import annotations

from cilly_trading.non_live_evaluation_contract import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
    RISK_REJECTION_REASON_PRECEDENCE,
)

from tests.utils.consumer_contract_helpers import (
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


CONTRACT_DOC = "docs/architecture/risk/non_live_evaluation_contract.md"
GOVERNANCE_DOC = "docs/governance/qualification-claim-evidence-discipline.md"
PHASE44_DOC = "docs/operations/runtime/phase-44-paper-operator-workflow.md"


def _extract_bullet_codes_after_heading(content: str, heading: str) -> list[str]:
    lines = content.splitlines()
    for index, line in enumerate(lines):
        if line.strip() != heading:
            continue
        codes: list[str] = []
        for candidate in lines[index + 1 :]:
            stripped = candidate.strip()
            if not stripped:
                if codes:
                    break
                continue
            code: str | None = None
            if stripped.startswith("- `") and stripped.endswith("`"):
                code = stripped[3:-1]
            else:
                for index in range(1, 10):
                    prefix = f"{index}. `"
                    if stripped.startswith(prefix) and stripped.endswith("`"):
                        code = stripped[len(prefix) : -1]
                        break
            if code is None:
                if codes:
                    break
                continue
            codes.append(code)
        return codes
    return []


def test_non_live_evaluation_contract_doc_defines_canonical_semantics() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_starts_with(content, "# Professional Non-Live Risk and Exposure Evaluation Contract")
    assert_contains_all(
        content,
        "NonLiveEvaluationEvidence",
        "decision",
        "semantic",
        "scope",
        "reject/cap/boundary semantics",
        "Canonical risk rejection reason-code vocabulary (normalized):",
        "rejected:risk_framework_kill_switch_enabled",
        "rejected:risk_framework_max_position_size_exceeded",
        "rejected:risk_framework_max_account_exposure_pct_exceeded",
        "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
        "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
    )


def test_non_live_contract_doc_locks_portfolio_constraint_hit_terminology() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_contains_all(
        content,
        "portfolio pipeline outcomes are `approved`, `rejected`, or `constraint_hit`",
        "evidence rows are emitted only when a cap or",
        "boundary is violated",
    )
    assert "reject edges only" not in content.lower()


def test_non_live_evaluation_contract_doc_keeps_non_live_boundaries_explicit() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_contains_all(
        content,
        "Out of scope:",
        "live trading enablement",
        "broker execution integration",
        "external portfolio optimization subsystems",
    )


def test_non_live_evaluation_contract_doc_defines_reason_precedence_and_inspection_normalization() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_contains_all(
        content,
        "Normalized precedence order (canonical reason codes):",
        "rejected:risk_framework_kill_switch_enabled",
        "rejected:risk_framework_max_position_size_exceeded",
        "rejected:risk_framework_max_account_exposure_pct_exceeded",
        "rejected:risk_framework_max_strategy_exposure_pct_exceeded",
        "rejected:risk_framework_max_symbol_exposure_pct_exceeded",
        "Inspection/read normalization:",
        "inspection flows",
        "best-effort",
    )


def test_non_live_contract_doc_reason_vocabulary_matches_runtime_contract_constants() -> None:
    content = read_repo_text(CONTRACT_DOC)

    documented_codes = _extract_bullet_codes_after_heading(
        content,
        "Canonical risk rejection reason-code vocabulary (normalized):",
    )
    assert tuple(documented_codes) == CANONICAL_RISK_REJECTION_REASON_CODES


def test_non_live_contract_doc_precedence_order_matches_runtime_contract_constants() -> None:
    content = read_repo_text(CONTRACT_DOC)

    documented_precedence = _extract_bullet_codes_after_heading(
        content,
        "Normalized precedence order (canonical reason codes):",
    )
    expected_precedence = [
        code
        for code, _ in sorted(RISK_REJECTION_REASON_PRECEDENCE.items(), key=lambda item: item[1])
    ]
    assert documented_precedence == expected_precedence


def test_non_live_contract_doc_explicitly_locks_cross_surface_determinism_boundary() -> None:
    content = read_repo_text(CONTRACT_DOC)

    assert_contains_all(
        content,
        "risk gate and paper execution worker surfaces",
        "equivalent bounded non-live input state must emit the same canonical reject",
        "deterministic precedence is mandatory when multiple constraints are violated",
        "best-effort single-field normalization to",
        "`normalized_reason_code` without multi-reason precedence selection",
        "not live-trading or broker-readiness evidence",
        "normalized_reason_codes",
        "does not aggregate multiple compatible reason",
    )


def test_non_live_contract_doc_locks_fail_closed_evidence_discipline_and_legacy_mapping() -> None:
    content = _read(CONTRACT_DOC)

    assert "deterministic rejection path" in content
    assert "fails closed when covered required evidence is contradictory or malformed" in content
    assert "legacy reason-only rejects" in content
    assert "deterministic synthetic evidence row" in content
    assert "technical non-live evidence only" in content
    assert "not live-trading or broker-readiness evidence" in content


def test_risk_and_portfolio_docs_reference_canonical_non_live_contract() -> None:
    risk_framework = read_repo_text("docs/architecture/risk/risk_framework.md")
    portfolio_framework = read_repo_text("docs/architecture/risk/portfolio_framework.md")

    assert_contains_all(
        risk_framework,
        "non_live_evaluation_contract.md",
        "policy_evidence",
        "risk evaluator outcomes are `approved` or `rejected`",
    )
    assert_contains_all(
        portfolio_framework,
        "non_live_evaluation_contract.md",
        "policy_evidence",
        "approved`, `rejected`, or `constraint_hit`",
    )
    assert "reject edges only" not in portfolio_framework.lower()


def test_ops_policy_doc_references_structured_non_live_evidence_surface() -> None:
    policy_doc = read_repo_text(
        "docs/operations/runtime/signal_to_paper_execution_policy.md"
    )

    assert_contains_all(
        policy_doc,
        "RiskEvaluationResponse.policy_evidence",
        "CapitalAllocationAssessment.policy_evidence",
        "PortfolioGuardrailAssessment.policy_evidence",
        "non_live_evaluation_contract.md",
        "approved`, `rejected`, or `constraint_hit`",
        "approved outcomes emit an empty evidence tuple",
    )
    assert "reject edges only" not in policy_doc.lower()


def test_usefulness_governance_doc_defines_exact_non_live_decision_to_paper_contract() -> None:
    content = read_repo_text(GOVERNANCE_DOC)

    assert_contains_all(
        content,
        "Deterministic Bounded Decision-to-Paper Usefulness Audit",
        "decision_evidence_to_paper_outcome_usefulness.paper_audit.v1",
        "metadata.bounded_decision_to_paper_match",
        "paper_trade_id",
        "`explanatory`",
        "`weak`",
        "`misleading`",
    )


def test_signal_quality_stability_governance_doc_defines_bounded_audit_contract() -> None:
    content = read_repo_text(GOVERNANCE_DOC)

    assert_contains_all(
        content,
        "Deterministic Bounded Signal-Quality Stability Audit",
        "bounded_signal_quality_stability.paper_audit.v1",
        "metadata.bounded_signal_quality_stability_audit",
        "metadata.bounded_decision_to_paper_match",
        "`stable`",
        "`weak`",
        "`failing`",
        "it is not trader validation",
        "it is not profitability forecasting",
        "it is not live-trading readiness",
        "it is not operational readiness",
    )


def test_usefulness_docs_keep_non_live_claim_boundaries_explicit() -> None:
    governance = read_repo_text(GOVERNANCE_DOC)
    phase44 = read_repo_text(PHASE44_DOC)

    assert_contains_all(
        governance,
        "it is not trader validation",
        "it is not profitability forecasting",
        "it is not live-trading readiness",
        "it is not operational readiness",
    )
    assert_contains_all(
        phase44,
        "metadata.bounded_decision_to_paper_usefulness_audit",
        "non-live explanatory review",
        "exact paper-trade matches only",
    )

from __future__ import annotations

from pathlib import Path

from cilly_trading.non_live_evaluation_contract import (
    CANONICAL_RISK_REJECTION_REASON_CODES,
    RISK_REJECTION_REASON_PRECEDENCE,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = (
    REPO_ROOT / "docs" / "architecture" / "risk" / "non_live_evaluation_contract.md"
)
GOVERNANCE_DOC = (
    REPO_ROOT / "docs" / "governance" / "qualification-claim-evidence-discipline.md"
)
PHASE44_DOC = (
    REPO_ROOT / "docs" / "operations" / "runtime" / "phase-44-paper-operator-workflow.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    content = _read(CONTRACT_DOC)

    assert content.startswith("# Professional Non-Live Risk and Exposure Evaluation Contract")
    assert "NonLiveEvaluationEvidence" in content
    assert "decision" in content
    assert "semantic" in content
    assert "scope" in content
    assert "reject/cap/boundary semantics" in content
    assert "Canonical risk rejection reason-code vocabulary (normalized):" in content
    assert "rejected:risk_framework_kill_switch_enabled" in content
    assert "rejected:risk_framework_max_position_size_exceeded" in content
    assert "rejected:risk_framework_max_account_exposure_pct_exceeded" in content
    assert "rejected:risk_framework_max_strategy_exposure_pct_exceeded" in content
    assert "rejected:risk_framework_max_symbol_exposure_pct_exceeded" in content


def test_non_live_contract_doc_locks_portfolio_constraint_hit_terminology() -> None:
    content = _read(CONTRACT_DOC)

    assert "portfolio pipeline outcomes are `approved`, `rejected`, or `constraint_hit`" in content
    assert "evidence rows are emitted only when a cap or" in content
    assert "boundary is violated" in content
    assert "reject edges only" not in content.lower()


def test_non_live_evaluation_contract_doc_keeps_non_live_boundaries_explicit() -> None:
    content = _read(CONTRACT_DOC)

    assert "Out of scope:" in content
    assert "live trading enablement" in content
    assert "broker execution integration" in content
    assert "external portfolio optimization subsystems" in content


def test_non_live_evaluation_contract_doc_defines_reason_precedence_and_inspection_normalization() -> None:
    content = _read(CONTRACT_DOC)

    assert "Normalized precedence order (canonical reason codes):" in content
    assert "rejected:risk_framework_kill_switch_enabled" in content
    assert "rejected:risk_framework_max_position_size_exceeded" in content
    assert "rejected:risk_framework_max_account_exposure_pct_exceeded" in content
    assert "rejected:risk_framework_max_strategy_exposure_pct_exceeded" in content
    assert "rejected:risk_framework_max_symbol_exposure_pct_exceeded" in content
    assert "Inspection/read normalization:" in content
    assert "inspection flows" in content
    assert "best-effort" in content


def test_non_live_contract_doc_reason_vocabulary_matches_runtime_contract_constants() -> None:
    content = _read(CONTRACT_DOC)

    documented_codes = _extract_bullet_codes_after_heading(
        content,
        "Canonical risk rejection reason-code vocabulary (normalized):",
    )
    assert tuple(documented_codes) == CANONICAL_RISK_REJECTION_REASON_CODES


def test_non_live_contract_doc_precedence_order_matches_runtime_contract_constants() -> None:
    content = _read(CONTRACT_DOC)

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
    content = _read(CONTRACT_DOC)

    assert "risk gate and paper execution worker surfaces" in content
    assert "equivalent bounded non-live input state must emit the same canonical reject" in content
    assert "deterministic precedence is mandatory when multiple constraints are violated" in content
    assert "best-effort single-field normalization to" in content
    assert "`normalized_reason_code` without multi-reason precedence selection" in content
    assert "not live-trading or broker-readiness evidence" in content
    assert "normalized_reason_codes" in content
    assert "does not aggregate multiple compatible reason" in content


def test_risk_and_portfolio_docs_reference_canonical_non_live_contract() -> None:
    risk_framework = _read(REPO_ROOT / "docs" / "architecture" / "risk" / "risk_framework.md")
    portfolio_framework = _read(REPO_ROOT / "docs" / "architecture" / "risk" / "portfolio_framework.md")

    assert "non_live_evaluation_contract.md" in risk_framework
    assert "policy_evidence" in risk_framework
    assert "risk evaluator outcomes are `approved` or `rejected`" in risk_framework
    assert "non_live_evaluation_contract.md" in portfolio_framework
    assert "policy_evidence" in portfolio_framework
    assert "approved`, `rejected`, or `constraint_hit`" in portfolio_framework
    assert "reject edges only" not in portfolio_framework.lower()


def test_ops_policy_doc_references_structured_non_live_evidence_surface() -> None:
    policy_doc = _read(
        REPO_ROOT
        / "docs"
        / "operations"
        / "runtime"
        / "signal_to_paper_execution_policy.md"
    )

    assert "RiskEvaluationResponse.policy_evidence" in policy_doc
    assert "CapitalAllocationAssessment.policy_evidence" in policy_doc
    assert "PortfolioGuardrailAssessment.policy_evidence" in policy_doc
    assert "non_live_evaluation_contract.md" in policy_doc
    assert "approved`, `rejected`, or `constraint_hit`" in policy_doc
    assert "approved outcomes emit an empty evidence tuple" in policy_doc
    assert "reject edges only" not in policy_doc.lower()


def test_usefulness_governance_doc_defines_exact_non_live_decision_to_paper_contract() -> None:
    content = _read(GOVERNANCE_DOC)

    assert "Deterministic Bounded Decision-to-Paper Usefulness Audit" in content
    assert "decision_evidence_to_paper_outcome_usefulness.paper_audit.v1" in content
    assert "metadata.bounded_decision_to_paper_match" in content
    assert "paper_trade_id" in content
    assert "`explanatory`" in content
    assert "`weak`" in content
    assert "`misleading`" in content


def test_usefulness_docs_keep_non_live_claim_boundaries_explicit() -> None:
    governance = _read(GOVERNANCE_DOC)
    phase44 = _read(PHASE44_DOC)

    assert "it is not trader validation" in governance
    assert "it is not profitability forecasting" in governance
    assert "it is not live-trading readiness" in governance
    assert "it is not operational readiness" in governance
    assert "metadata.bounded_decision_to_paper_usefulness_audit" in phase44
    assert "non-live explanatory review" in phase44
    assert "exact paper-trade matches only" in phase44

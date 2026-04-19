from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
CONTRACT_DOC = (
    REPO_ROOT / "docs" / "architecture" / "risk" / "non_live_evaluation_contract.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


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
    assert "bounded non-live inspection flows" in content


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

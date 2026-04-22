from __future__ import annotations

from tests.utils.consumer_contract_helpers import (
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


GOVERNANCE_DOC = "docs/governance/qualification-claim-evidence-discipline.md"
ARCHITECTURE_DOC = "docs/architecture/decision_card_contract.md"
INSPECTION_DOC = "docs/api/decision_card_inspection.md"
PHASE_DOC = "docs/phases/dec-p47-qualification-claim-boundary.md"
PHASE_P49_DOC = "docs/phases/dec-p49-qualification-engine-hard-gates-confidence.md"


def test_governance_doc_defines_evidence_hierarchy_and_forbidden_claim_classes() -> None:
    content = read_repo_text(GOVERNANCE_DOC)

    assert_starts_with(content, "# Qualification Claim Evidence Discipline")
    assert_contains_all(
        content,
        "## 2. Evidence Hierarchy for Qualification Claims",
        "Hard-gate evidence",
        "Bounded component evidence",
        "Bounded aggregate/confidence resolution",
        "Bounded paper-trading qualification state",
        "must be rejected",
        "live-trading readiness/approval claims",
        "broker execution readiness claims",
        "trader-validation claims",
        "paper profitability or edge claims",
        "guaranteed/certain outcome claims",
    )


def test_governance_doc_defines_deterministic_bounded_trader_relevance_contract() -> None:
    content = read_repo_text(GOVERNANCE_DOC)

    assert_contains_all(
        content,
        "Deterministic Bounded Trader-Relevance Review Contract",
        "bounded_trader_relevance.paper_review.v1",
        "qualification_state_relevance",
        "decision_action_relevance",
        "boundary_scope_relevance",
        "aligned",
        "weak",
        "missing",
    )


def test_decision_card_contract_doc_declares_claim_boundary_wording_requirements() -> None:
    content = read_repo_text(ARCHITECTURE_DOC)

    assert_contains_all(
        content,
        "Confidence language is claim-bounded:",
        "must reference bounded evidence semantics",
        "must not claim live-trading readiness",
        "Qualification summary language is claim-bounded:",
        "must remain explicitly paper-trading scoped",
        "rationale.final_explanation",
        "does not imply live-trading approval",
    )


def test_decision_card_inspection_doc_matches_claim_boundary_runtime_wording() -> None:
    content = read_repo_text(INSPECTION_DOC)

    assert_contains_all(
        content,
        "Claim boundary discipline for this surface:",
        "confidence language is evidence-aligned only",
        "must not imply live-trading approval",
        "rejects unsupported confidence inflation language",
        "confidence is explicitly bounded by upstream evidence quality",
        "limited upstream evidence limits the achievable confidence tier",
    )


def test_dec_p47_phase_doc_links_governance_contract_and_runtime_enforcement() -> None:
    content = read_repo_text(PHASE_DOC)

    assert_starts_with(content, "# DEC-P47 - Qualification Claim Boundary")
    assert_contains_all(
        content,
        "Required evidence order:",
        "src/cilly_trading/engine/decision_card_contract.py",
        "does not imply",
    )


def test_dec_p49_phase_doc_covers_bounded_qualification_engine_and_decision_output() -> None:
    content = read_repo_text(PHASE_P49_DOC)

    assert_starts_with(content, "# DEC-P49 - Decision-Layer Integration")
    assert_contains_all(
        content,
        "hard-gate behavior is deterministic",
        "confidence tiers are explicit and bounded",
        "traffic-light output is deterministic and inspectable",
        "bounded backtest evidence integration",
        "bounded portfolio-fit input integration",
        "bounded sentiment overlay impact",
        "src/cilly_trading/engine/qualification_engine.py",
        "src/cilly_trading/engine/decision_card_contract.py",
        "tests/cilly_trading/engine/test_qualification_engine.py",
        "tests/decision/test_decision_integration_layer.py",
        "confidence is explicitly bounded by upstream evidence quality",
        "limited upstream evidence limits confidence regardless of thresholds",
    )

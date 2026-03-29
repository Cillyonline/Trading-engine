from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOC = REPO_ROOT / "docs" / "governance" / "qualification-claim-evidence-discipline.md"
ARCHITECTURE_DOC = REPO_ROOT / "docs" / "architecture" / "decision_card_contract.md"
INSPECTION_DOC = REPO_ROOT / "docs" / "api" / "decision_card_inspection.md"
PHASE_DOC = REPO_ROOT / "docs" / "phases" / "dec-p47-qualification-claim-boundary.md"
DEC_P49_DOC = REPO_ROOT / "docs" / "phases" / "dec-p49-canonical-decision-card-contract.md"


def test_governance_doc_defines_evidence_hierarchy_and_forbidden_claim_classes() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert content.startswith("# Qualification Claim Evidence Discipline")
    assert "## 2. Evidence Hierarchy for Qualification Claims" in content
    assert "Hard-gate evidence" in content
    assert "Bounded component evidence" in content
    assert "Bounded aggregate/confidence resolution" in content
    assert "Bounded paper-trading qualification state" in content
    assert "must be rejected" in content
    assert "live-trading readiness/approval claims" in content
    assert "broker execution readiness claims" in content
    assert "trader-validation claims" in content
    assert "guaranteed/certain outcome claims" in content


def test_decision_card_contract_doc_declares_claim_boundary_wording_requirements() -> None:
    content = ARCHITECTURE_DOC.read_text(encoding="utf-8")

    assert "Confidence language is claim-bounded:" in content
    assert "must reference bounded evidence semantics" in content
    assert "must not claim live-trading readiness" in content
    assert "Qualification summary language is claim-bounded:" in content
    assert "must remain explicitly paper-trading scoped" in content
    assert "rationale.final_explanation" in content
    assert "does not imply live-trading approval" in content
    assert "State assignment is validated by the canonical contract" in content


def test_decision_card_inspection_doc_matches_claim_boundary_runtime_wording() -> None:
    content = INSPECTION_DOC.read_text(encoding="utf-8")

    assert "Claim boundary discipline for this surface:" in content
    assert "confidence language is evidence-aligned only" in content
    assert "qualification state is contract-bounded" in content
    assert "must not imply live-trading approval" in content
    assert "rejects unsupported confidence inflation language" in content


def test_dec_p47_phase_doc_links_governance_contract_and_runtime_enforcement() -> None:
    content = PHASE_DOC.read_text(encoding="utf-8")

    assert content.startswith("# DEC-P47 - Qualification Claim Boundary")
    assert "Required evidence order:" in content
    assert "src/cilly_trading/engine/decision_card_contract.py" in content
    assert "does not imply" in content


def test_dec_p49_phase_doc_defines_canonical_contract_and_bounded_state_rules() -> None:
    content = DEC_P49_DOC.read_text(encoding="utf-8")

    assert content.startswith("# DEC-P49 - Canonical Decision-Card Contract")
    assert "src/cilly_trading/engine/decision_card_contract.py" in content
    assert "hard-gate payload shape is explicit" in content
    assert "required categories are fixed" in content
    assert "aggregate_score < 60.0" in content
    assert "aggregate_score >= 80.0" in content
    assert "inspection wording aligns with the canonical contract" in content.casefold()

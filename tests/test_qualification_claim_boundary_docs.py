from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOC = REPO_ROOT / "docs" / "governance" / "qualification-claim-evidence-discipline.md"
ARCHITECTURE_DOC = REPO_ROOT / "docs" / "architecture" / "decision_card_contract.md"
INSPECTION_DOC = REPO_ROOT / "docs" / "api" / "decision_card_inspection.md"
PHASE_DOC = REPO_ROOT / "docs" / "phases" / "dec-p47-qualification-claim-boundary.md"
PHASE_P49_DOC = REPO_ROOT / "docs" / "phases" / "dec-p49-qualification-engine-hard-gates-confidence.md"


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
    assert "paper profitability or edge claims" in content
    assert "guaranteed/certain outcome claims" in content


def test_governance_doc_defines_deterministic_bounded_trader_relevance_contract() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "Deterministic Bounded Trader-Relevance Review Contract" in content
    assert "bounded_trader_relevance.paper_review.v1" in content
    assert "bounded_non_inference_boundary_fields.read_only.v1" in content
    assert "structured boundary fields contract version `1.0.0`" in content
    assert "qualification_state_relevance" in content
    assert "decision_action_relevance" in content
    assert "boundary_scope_relevance" in content
    assert "trader_validation_boundary" in content
    assert "paper_profitability_boundary" in content
    assert "live_readiness_boundary" in content
    assert "runtime boundary evaluation is driven by the canonical structured evidence fields" in content
    assert "wording/phrase matching remains bounded compatibility fallback only" in content
    assert "aligned" in content
    assert "weak" in content
    assert "missing" in content


def test_decision_card_contract_doc_declares_claim_boundary_wording_requirements() -> None:
    content = ARCHITECTURE_DOC.read_text(encoding="utf-8")

    assert "Confidence language is claim-bounded:" in content
    assert "must reference bounded evidence semantics" in content
    assert "must not claim live-trading readiness" in content
    assert "Qualification summary language is claim-bounded:" in content
    assert "must remain explicitly paper-trading scoped" in content
    assert "rationale.final_explanation" in content
    assert "does not imply live-trading approval" in content


def test_decision_card_inspection_doc_matches_claim_boundary_runtime_wording() -> None:
    content = INSPECTION_DOC.read_text(encoding="utf-8")

    assert "Claim boundary discipline for this surface:" in content
    assert "confidence language is evidence-aligned only" in content
    assert "must not imply live-trading approval" in content
    assert "Structured non-inference boundary fields contract for decision/inspection payloads" in content
    assert "`bounded_non_inference_boundary_fields.read_only.v1`" in content
    assert "`evaluation_mode`: `structured_primary_with_wording_fallback`" in content
    assert "failure_reasons" in content
    assert "structured boundary semantics first and keeps wording checks as bounded compatibility fallback" in content
    assert "confidence is explicitly bounded by upstream evidence quality" in content
    assert "limited upstream evidence limits the achievable confidence tier" in content


def test_dec_p47_phase_doc_links_governance_contract_and_runtime_enforcement() -> None:
    content = PHASE_DOC.read_text(encoding="utf-8")

    assert content.startswith("# DEC-P47 - Qualification Claim Boundary")
    assert "Required evidence order:" in content
    assert "src/cilly_trading/engine/decision_card_contract.py" in content
    assert "does not imply" in content


def test_dec_p49_phase_doc_covers_bounded_qualification_engine_and_decision_output() -> None:
    content = PHASE_P49_DOC.read_text(encoding="utf-8")

    assert content.startswith("# DEC-P49 - Decision-Layer Integration")
    assert "hard-gate behavior is deterministic" in content
    assert "confidence tiers are explicit and bounded" in content
    assert "traffic-light output is deterministic and inspectable" in content
    assert "bounded backtest evidence integration" in content
    assert "bounded portfolio-fit input integration" in content
    assert "bounded sentiment overlay impact" in content
    assert "src/cilly_trading/engine/qualification_engine.py" in content
    assert "src/cilly_trading/engine/decision_card_contract.py" in content
    assert "tests/cilly_trading/engine/test_qualification_engine.py" in content
    assert "tests/decision/test_decision_integration_layer.py" in content
    assert "confidence is explicitly bounded by upstream evidence quality" in content
    assert "limited upstream evidence limits confidence regardless of thresholds" in content

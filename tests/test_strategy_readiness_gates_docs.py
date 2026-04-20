from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
GATES_DOC = REPO_ROOT / "docs" / "governance" / "strategy-readiness-gates.md"


def test_strategy_readiness_gates_define_three_independent_gate_classes() -> None:
    content = GATES_DOC.read_text(encoding="utf-8")

    assert content.lstrip("\ufeff").startswith("# Strategy Readiness Governance Gates")
    assert "Technical Implementation Gate" in content
    assert "Trader Validation Gate" in content
    assert "Operational Readiness Gate" in content
    assert "independent" in content
    assert "must not be inferred as evidence in another gate" in content


def test_strategy_readiness_gates_define_bounded_status_semantics_and_transitions() -> None:
    content = GATES_DOC.read_text(encoding="utf-8")

    assert "technical_not_started" in content
    assert "technical_in_progress" in content
    assert "technical_gate_passed" in content
    assert "trader_validation_not_started" in content
    assert "trader_validation_in_progress" in content
    assert "trader_validation_gate_passed" in content
    assert "operational_not_started" in content
    assert "operational_in_progress" in content
    assert "operational_gate_passed" in content
    assert "Gate Transitions and Required Evidence Types" in content
    assert "No implicit transition is allowed" in content
    assert "Required evidence types" in content


def test_strategy_readiness_gates_prohibit_trader_ready_inference_from_technical_artifacts() -> None:
    content = GATES_DOC.read_text(encoding="utf-8")

    assert "claiming trader-ready status from technical artifacts alone" in content
    assert "claiming operational-readiness status from technical artifacts alone" in content
    assert "does not enable live trading" in content
    assert "does not authorize broker execution" in content
    assert "does not declare production trading readiness" in content


def test_strategy_readiness_gates_define_bounded_api_ui_evidence_surface_scope() -> None:
    content = GATES_DOC.read_text(encoding="utf-8")

    assert "Bounded API/UI Evidence Surfacing Scope" in content
    assert "strategy_readiness_api_ui_evidence_surface_v1" in content
    assert "GET /backtest/artifacts" in content
    assert "GET /backtest/artifacts/{run_id}/{artifact_name}" in content
    assert "must not collapse these states into a single inferred readiness claim" in content
    assert "no live-trading readiness or authorization claim" in content
    assert "no paper profitability or edge claim" in content
    assert "no production-readiness claim" in content
    assert "bounded trader-relevance validation" in content


def test_docs_index_references_strategy_readiness_gates_contract() -> None:
    index_content = (REPO_ROOT / "docs" / "index.md").read_text(encoding="utf-8")

    assert "governance/strategy-readiness-gates.md" in index_content

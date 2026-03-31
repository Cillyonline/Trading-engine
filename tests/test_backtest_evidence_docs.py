from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_backtest_cli_doc_defines_reproducible_evidence_fields() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Reproducible Evidence Fields" in content
    assert "`run.run_id`" in content
    assert "`run_config.execution_assumptions`" in content
    assert "`realism_boundary.modeled_assumptions`" in content
    assert "`realism_boundary.unmodeled_assumptions`" in content
    assert "`run_config.reproducibility_metadata`" in content
    assert "`metrics_baseline.assumptions`" in content
    assert "MUST match" in content


def test_backtest_cli_doc_defines_realism_boundary_and_unsupported_claims() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Realism Boundary" in content
    assert "Modeled assumptions:" in content
    assert "Unmodeled assumptions:" in content
    assert "Market hours are not modeled." in content
    assert "Unsupported claims that MUST remain excluded:" in content
    assert "live-trading readiness or approval" in content
    assert "Qualification and decision docs must treat backtest output as bounded evidence only." in content


def test_backtest_cli_doc_defines_trader_interpretation_boundary() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Trader Interpretation Boundary" in content
    assert "does **not** prove" in content
    assert "Live trading readiness." in content
    assert "Future performance" in content


def test_backtest_cli_doc_defines_phase_handoff_contract_and_gate_distinction() -> None:
    content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "backtest_cli.md").read_text(
        encoding="utf-8"
    )

    assert "## Phase 42b -> 43 -> 44 Handoff Contract" in content
    assert "phase_handoff.required_evidence.phase_43_portfolio_simulation" in content
    assert "phase_handoff.required_evidence.phase_44_paper_trading_readiness" in content
    assert "phase_handoff.artifact_lineage" in content
    assert "phase_handoff.canonical_handoffs.backtest_to_portfolio" in content
    assert "phase_handoff.canonical_handoffs.portfolio_to_paper" in content
    assert "technically valid artifact is not automatically Phase 43/44 readiness evidence" in content


def test_backtest_architecture_doc_defines_canonical_handoff() -> None:
    content = (REPO_ROOT / "docs" / "architecture" / "backtest_execution_contract.md").read_text(
        encoding="utf-8"
    )

    assert "## Canonical Handoff (Phase 42b -> Phase 43 -> Phase 44)" in content
    assert "phase_handoff.acceptance_gates.technically_valid_backtest_artifact" in content
    assert "phase_handoff.acceptance_gates.phase_43_portfolio_simulation_ready" in content
    assert "phase_handoff.acceptance_gates.phase_44_paper_trading_readiness_evidence_ready" in content
    assert "realism_boundary" in content
    assert "phase_handoff.artifact_lineage" in content
    assert "phase_handoff.canonical_handoffs.backtest_to_portfolio" in content
    assert "phase_handoff.canonical_handoffs.portfolio_to_paper" in content
    assert "bounded backtest evidence only" in content


def test_backtest_schema_and_execution_docs_define_realism_disclosures() -> None:
    schema_content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "result_artifact_schema.md").read_text(
        encoding="utf-8"
    )
    execution_content = (REPO_ROOT / "docs" / "testing" / "backtesting" / "order_execution_model.md").read_text(
        encoding="utf-8"
    )

    assert "`realism_boundary`" in schema_content
    assert "modeled assumptions" in schema_content
    assert "unmodeled assumptions" in schema_content
    assert "Unsupported realism claims" in schema_content
    assert "`artifact_lineage`" in schema_content
    assert "`canonical_handoffs`" in schema_content
    assert "## 8) Unmodeled realism boundary" in execution_content
    assert "Market hours and exchange session rules are not modeled." in execution_content
    assert "does not support live-trading readiness claims" in execution_content

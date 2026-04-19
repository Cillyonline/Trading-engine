from __future__ import annotations

from copy import deepcopy
from typing import Any

from cilly_trading.engine.backtest_handoff_contract import (
    build_professional_review_contract,
    build_phase_handoff_contract,
)


def _base_payload() -> dict[str, Any]:
    run_assumptions = {
        "fill_model": "deterministic_market",
        "fill_timing": "next_snapshot",
        "price_source": "open_then_price",
        "slippage_bps": 0,
        "commission_per_order": "0",
        "partial_fills_allowed": False,
    }
    baseline_assumptions = dict(run_assumptions)
    return {
        "artifact_version": "1",
        "run": {"run_id": "run-1", "deterministic": True, "created_at": None},
        "snapshot_linkage": {
            "mode": "timestamp",
            "start": "2024-01-01T00:00:00Z",
            "end": "2024-01-02T00:00:00Z",
            "count": 2,
        },
        "strategy": {"name": "REFERENCE", "version": None, "params": {}},
        "run_config": {
            "contract_version": "1.0.0",
            "execution_assumptions": run_assumptions,
            "reproducibility_metadata": {
                "run_id": "run-1",
                "strategy_name": "REFERENCE",
                "strategy_params": {},
                "engine_name": "cilly_trading_engine",
                "engine_version": None,
            },
        },
        "realism_boundary": {
            "boundary_version": "1.0.0",
            "modeled_assumptions": {
                "fees": {"commission_model": "fixed_per_filled_order", "commission_per_order": "0"},
                "slippage": {"slippage_bps": 0, "slippage_model": "fixed_basis_points_by_side"},
                "fills": {
                    "fill_model": "deterministic_market",
                    "fill_timing": "next_snapshot",
                    "partial_fills_allowed": False,
                    "price_source": "open_then_price",
                },
            },
            "unmodeled_assumptions": {
                "market_hours": "Not modeled.",
                "broker_behavior": "Not modeled.",
                "liquidity_and_microstructure": "Not modeled.",
            },
            "evidence_boundary": {
                "supported_interpretation": [
                    "Deterministic replay of supplied snapshots under the declared fill, slippage, and fee assumptions."
                ],
                "unsupported_claims": [
                    "broker execution realism",
                    "market-hours compliance realism",
                    "liquidity or market microstructure realism",
                    "live-trading readiness or approval",
                    "future profitability or out-of-sample robustness",
                ],
                "qualification_constraint": "Backtest evidence is bounded.",
                "decision_use_constraint": "Qualification and decision documents must treat this artifact as bounded backtest evidence only.",
            },
        },
        "summary": {"start_equity": 100000.0, "end_equity": 100001.0},
        "equity_curve": [{"timestamp": "2024-01-01T00:00:00Z", "equity": 100000.0}],
        "orders": [],
        "fills": [],
        "positions": [],
        "metrics_baseline": {
            "assumptions": baseline_assumptions,
            "summary": {
                "starting_equity": 100000.0,
                "ending_equity_cost_free": 100001.0,
                "ending_equity_cost_aware": 100001.0,
                "total_transaction_cost": 0.0,
                "total_commission": 0.0,
                "total_slippage_cost": 0.0,
                "fill_count": 0,
            },
            "metrics": {
                "cost_free": {"total_return": 0.00001},
                "cost_aware": {"total_return": 0.00001},
                "deltas": {"total_return": 0.0},
            },
            "trades": [],
        },
    }


def test_build_professional_review_contract_returns_canonical_payload() -> None:
    review_contract = build_professional_review_contract()

    assert review_contract == {
        "contract_id": "bounded_backtest_evidence_professional_review.v1",
        "contract_version": "1.0.0",
        "review_context": "professional_non_live_evidence_review",
        "required_visible_evidence": [
            "run.run_id",
            "snapshot_linkage.mode",
            "snapshot_linkage.start",
            "snapshot_linkage.end",
            "snapshot_linkage.count",
            "strategy.name",
            "strategy.params",
            "run_config.execution_assumptions",
            "realism_boundary.modeled_assumptions",
            "realism_boundary.unmodeled_assumptions",
            "realism_boundary.evidence_boundary.unsupported_claims",
            "summary.start_equity",
            "summary.end_equity",
            "metrics_baseline.summary",
            "metrics_baseline.metrics.cost_aware",
            "phase_handoff.acceptance_gates.technically_valid_backtest_artifact",
            "phase_handoff.acceptance_gates.phase_43_portfolio_simulation_ready",
            "phase_handoff.acceptance_gates.phase_44_paper_trading_readiness_evidence_ready",
        ],
        "comparison_axes": [
            "snapshot window and count",
            "strategy identity and params",
            "execution assumptions and baseline assumption alignment",
            "modeled vs unmodeled realism boundary",
            "cost-aware outcome summary and deltas",
            "phase handoff gate outcomes",
        ],
        "decision_relevance_statement": (
            "Backtest evidence is exposed for bounded professional non-live review where explicit "
            "comparability is required for decision support."
        ),
        "readiness_non_inference_statement": (
            "Technical implementation evidence must remain separated from trader validation and "
            "operational readiness."
        ),
        "unsupported_inference_claims": [
            "trader validation inferred from technical artifact availability",
            "operational readiness inferred from backtest evidence alone",
            "live-trading readiness or broker execution approval",
        ],
    }


def test_phase_handoff_contract_reports_passed_gates_for_complete_payload() -> None:
    handoff = build_phase_handoff_contract(_base_payload())
    gates = handoff["acceptance_gates"]
    artifact_lineage = handoff["artifact_lineage"]
    review_contract = handoff["review_contract"]
    canonical_review_contract = build_professional_review_contract()
    backtest_to_portfolio = handoff["canonical_handoffs"]["backtest_to_portfolio"]
    portfolio_to_paper = handoff["canonical_handoffs"]["portfolio_to_paper"]

    assert handoff["source_phase"] == "42b"
    assert handoff["target_phases"] == ["43", "44"]
    assert review_contract["contract_id"] == "bounded_backtest_evidence_professional_review.v1"
    assert review_contract["contract_version"] == "1.0.0"
    assert review_contract["review_context"] == "professional_non_live_evidence_review"
    assert review_contract == canonical_review_contract
    assert "run.run_id" in review_contract["required_visible_evidence"]
    assert "metrics_baseline.metrics.cost_aware" in review_contract["required_visible_evidence"]
    assert "phase handoff gate outcomes" in review_contract["comparison_axes"]
    assert "must remain separated" in review_contract["readiness_non_inference_statement"]
    assert (
        "live-trading readiness or broker execution approval"
        in review_contract["unsupported_inference_claims"]
    )
    assert "realism_boundary" in handoff["authoritative_outputs"]["trader_interpretation"]
    assert artifact_lineage["complete"] is True
    assert "run.run_id" in artifact_lineage["required_fields"]
    assert "realism_boundary.modeled_assumptions" in backtest_to_portfolio["required_inputs"]
    assert "realism_boundary" in handoff["authoritative_outputs"]["trader_interpretation"]
    assert backtest_to_portfolio["handoff_id"] == "phase_42b_backtest_to_phase_43_portfolio"
    assert backtest_to_portfolio["artifact_lineage_complete"] is True
    assert backtest_to_portfolio["prerequisite_gates"] == ["technically_valid_backtest_artifact"]
    assert portfolio_to_paper["handoff_id"] == "phase_43_portfolio_to_phase_44_paper"
    assert portfolio_to_paper["artifact_lineage_complete"] is True
    assert portfolio_to_paper["prerequisite_gates"] == ["phase_43_portfolio_simulation_ready"]
    assert gates["technically_valid_backtest_artifact"]["passed"] is True
    assert gates["phase_43_portfolio_simulation_ready"]["passed"] is True
    assert gates["phase_44_paper_trading_readiness_evidence_ready"]["passed"] is True
    assert handoff["artifact_lineage"] == {
        "complete": True,
        "required_fields": [
            "run.run_id",
            "snapshot_linkage.mode",
            "snapshot_linkage.start",
            "snapshot_linkage.end",
            "snapshot_linkage.count",
            "strategy.name",
            "strategy.params",
            "run_config.contract_version",
            "run_config.execution_assumptions",
            "run_config.reproducibility_metadata",
        ],
        "missing_fields": [],
    }
    assert (
        handoff["assumption_alignment"][
            "run_config_execution_assumptions_match_metrics_baseline_assumptions"
        ]
        is True
    )
    assert backtest_to_portfolio == {
        "handoff_id": "phase_42b_backtest_to_phase_43_portfolio",
        "producer_phase": "42b",
        "consumer_phase": "43",
        "readiness_gate": "phase_43_portfolio_simulation_ready",
        "prerequisite_gates": ["technically_valid_backtest_artifact"],
        "required_inputs": [
            "artifact_version",
            "run.run_id",
            "run.deterministic",
            "snapshot_linkage.mode",
            "snapshot_linkage.start",
            "snapshot_linkage.end",
            "snapshot_linkage.count",
            "strategy.name",
            "strategy.params",
            "run_config.contract_version",
            "run_config.execution_assumptions",
            "run_config.reproducibility_metadata",
            "realism_boundary.modeled_assumptions",
            "realism_boundary.unmodeled_assumptions",
            "realism_boundary.evidence_boundary.supported_interpretation",
            "realism_boundary.evidence_boundary.unsupported_claims",
            "realism_boundary.evidence_boundary.qualification_constraint",
            "realism_boundary.evidence_boundary.decision_use_constraint",
            "summary.start_equity",
            "summary.end_equity",
            "equity_curve",
            "metrics_baseline.assumptions",
            "metrics_baseline.summary",
            "metrics_baseline.metrics.cost_aware",
        ],
        "artifact_lineage_complete": True,
        "artifact_lineage_required_fields": handoff["artifact_lineage"]["required_fields"],
        "artifact_lineage_missing_fields": [],
        "readiness_boundary": (
            "Portfolio simulation may consume only explicit backtest evidence inputs and artifact lineage "
            "carried by this contract."
        ),
        "unsupported_claims": [
            "portfolio-readiness inferred from technical artifact validity alone",
            "paper-readiness inferred without a passed portfolio boundary",
            "live-trading readiness or approval",
            "broker execution readiness or approval",
            "guaranteed or certain outcome claims",
        ],
        "gate_status": gates["phase_43_portfolio_simulation_ready"],
    }
    assert portfolio_to_paper == {
        "handoff_id": "phase_43_portfolio_to_phase_44_paper",
        "producer_phase": "43",
        "consumer_phase": "44",
        "readiness_gate": "phase_44_paper_trading_readiness_evidence_ready",
        "prerequisite_gates": ["phase_43_portfolio_simulation_ready"],
        "required_inputs": [
            "artifact_version",
            "run.run_id",
            "run.deterministic",
            "snapshot_linkage.mode",
            "snapshot_linkage.start",
            "snapshot_linkage.end",
            "snapshot_linkage.count",
            "strategy.name",
            "strategy.params",
            "run_config.contract_version",
            "run_config.execution_assumptions",
            "run_config.reproducibility_metadata",
            "realism_boundary.modeled_assumptions",
            "realism_boundary.unmodeled_assumptions",
            "realism_boundary.evidence_boundary.supported_interpretation",
            "realism_boundary.evidence_boundary.unsupported_claims",
            "realism_boundary.evidence_boundary.qualification_constraint",
            "realism_boundary.evidence_boundary.decision_use_constraint",
            "summary.start_equity",
            "summary.end_equity",
            "equity_curve",
            "metrics_baseline.assumptions",
            "metrics_baseline.summary",
            "metrics_baseline.metrics.cost_aware",
            "orders",
            "fills",
            "positions",
            "metrics_baseline.trades",
        ],
        "artifact_lineage_complete": True,
        "artifact_lineage_required_fields": handoff["artifact_lineage"]["required_fields"],
        "artifact_lineage_missing_fields": [],
        "readiness_boundary": (
            "Paper readiness may consume only explicit portfolio-ready evidence and canonical execution "
            "artifacts carried by this contract."
        ),
        "unsupported_claims": [
            "paper-readiness inferred from vague or implicit portfolio evidence",
            "live-trading readiness or approval",
            "production readiness or approval",
            "broker execution readiness or approval",
            "trader-validation or guaranteed outcome claims",
        ],
        "gate_status": gates["phase_44_paper_trading_readiness_evidence_ready"],
    }


def test_phase_handoff_contract_marks_phase_43_gate_failed_when_required_fields_missing() -> None:
    payload = _base_payload()
    del payload["run_config"]

    handoff = build_phase_handoff_contract(payload)
    phase_43_gate = handoff["acceptance_gates"]["phase_43_portfolio_simulation_ready"]
    phase_44_gate = handoff["acceptance_gates"]["phase_44_paper_trading_readiness_evidence_ready"]
    artifact_lineage = handoff["artifact_lineage"]
    backtest_to_portfolio = handoff["canonical_handoffs"]["backtest_to_portfolio"]

    assert phase_43_gate["passed"] is False
    assert "run_config.contract_version" in phase_43_gate["missing_fields"]
    assert "missing_phase_43_required_fields" in phase_43_gate["reasons"]
    assert "portfolio_simulation_requires_explicit_backtest_evidence" in phase_43_gate["reasons"]
    assert phase_44_gate["passed"] is False
    assert "phase_43_gate_not_passed" in phase_44_gate["reasons"]
    assert "paper_readiness_requires_portfolio_ready_evidence" in phase_44_gate["reasons"]
    assert artifact_lineage["complete"] is False
    assert artifact_lineage["missing_fields"] == [
        "run_config.contract_version",
        "run_config.execution_assumptions",
        "run_config.reproducibility_metadata",
    ]
    assert backtest_to_portfolio["artifact_lineage_complete"] is False
    assert backtest_to_portfolio["artifact_lineage_missing_fields"] == [
        "run_config.contract_version",
        "run_config.execution_assumptions",
        "run_config.reproducibility_metadata",
    ]


def test_phase_handoff_contract_marks_realism_boundary_missing_as_not_ready() -> None:
    payload = _base_payload()
    del payload["realism_boundary"]

    handoff = build_phase_handoff_contract(payload)
    technical_gate = handoff["acceptance_gates"]["technically_valid_backtest_artifact"]
    phase_43_gate = handoff["acceptance_gates"]["phase_43_portfolio_simulation_ready"]
    backtest_to_portfolio = handoff["canonical_handoffs"]["backtest_to_portfolio"]

    assert technical_gate["passed"] is False
    assert "realism_boundary" in technical_gate["missing_fields"]
    assert phase_43_gate["passed"] is False
    assert "realism_boundary.modeled_assumptions" in phase_43_gate["missing_fields"]
    assert "realism_boundary.modeled_assumptions" in backtest_to_portfolio["required_inputs"]


def test_phase_handoff_contract_marks_assumption_mismatch_as_not_ready() -> None:
    payload = deepcopy(_base_payload())
    payload["metrics_baseline"]["assumptions"]["slippage_bps"] = 9

    handoff = build_phase_handoff_contract(payload)
    phase_43_gate = handoff["acceptance_gates"]["phase_43_portfolio_simulation_ready"]
    phase_44_gate = handoff["acceptance_gates"]["phase_44_paper_trading_readiness_evidence_ready"]

    assert (
        handoff["assumption_alignment"][
            "run_config_execution_assumptions_match_metrics_baseline_assumptions"
        ]
        is False
    )
    assert phase_43_gate["passed"] is False
    assert "run_config_and_metrics_baseline_assumptions_mismatch" in phase_43_gate["reasons"]
    assert "portfolio_simulation_requires_aligned_execution_assumptions" in phase_43_gate["reasons"]
    assert phase_44_gate["passed"] is False
    assert "paper_readiness_requires_portfolio_ready_evidence" in phase_44_gate["reasons"]

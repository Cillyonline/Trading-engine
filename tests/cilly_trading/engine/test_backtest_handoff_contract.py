from __future__ import annotations

from copy import deepcopy
from typing import Any

from cilly_trading.engine.backtest_handoff_contract import build_phase_handoff_contract


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


def test_phase_handoff_contract_reports_passed_gates_for_complete_payload() -> None:
    handoff = build_phase_handoff_contract(_base_payload())
    gates = handoff["acceptance_gates"]

    assert handoff["source_phase"] == "42b"
    assert handoff["target_phases"] == ["43", "44"]
    assert gates["technically_valid_backtest_artifact"]["passed"] is True
    assert gates["phase_43_portfolio_simulation_ready"]["passed"] is True
    assert gates["phase_44_paper_trading_readiness_evidence_ready"]["passed"] is True
    assert (
        handoff["assumption_alignment"][
            "run_config_execution_assumptions_match_metrics_baseline_assumptions"
        ]
        is True
    )


def test_phase_handoff_contract_marks_phase_43_gate_failed_when_required_fields_missing() -> None:
    payload = _base_payload()
    del payload["run_config"]

    handoff = build_phase_handoff_contract(payload)
    phase_43_gate = handoff["acceptance_gates"]["phase_43_portfolio_simulation_ready"]
    phase_44_gate = handoff["acceptance_gates"]["phase_44_paper_trading_readiness_evidence_ready"]

    assert phase_43_gate["passed"] is False
    assert "run_config.contract_version" in phase_43_gate["missing_fields"]
    assert "missing_phase_43_required_fields" in phase_43_gate["reasons"]
    assert phase_44_gate["passed"] is False
    assert "phase_43_gate_not_passed" in phase_44_gate["reasons"]


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
    assert phase_44_gate["passed"] is False

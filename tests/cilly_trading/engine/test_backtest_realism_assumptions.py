from __future__ import annotations

from decimal import Decimal

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    BacktestRunContract,
    build_cost_slippage_metrics_baseline,
    build_realism_sensitivity_matrix,
    simulate_execution_flow,
    sort_snapshots,
)


def _assumptions() -> BacktestExecutionAssumptions:
    return BacktestExecutionAssumptions(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing="next_snapshot",
    )


def _approved_risk_evidence() -> dict[str, str]:
    return {
        "decision": "APPROVED",
        "score": "1",
        "max_allowed": "10",
        "reason": "deterministic_risk_within_bounds",
        "rule_version": "test-risk-v1",
    }


def test_p56_bt_fill_timing_and_price_source_are_bounded_to_current_model() -> None:
    snapshots = [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": "100",
            "signals": [
                {
                    "signal_id": "sig-buy",
                    "action": "BUY",
                    "quantity": "1",
                    "symbol": "AAPL",
                    "risk_evidence": _approved_risk_evidence(),
                }
            ],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "price": "101",
            "signals": [
                {
                    "signal_id": "sig-sell",
                    "action": "SELL",
                    "quantity": "1",
                    "symbol": "AAPL",
                    "risk_evidence": _approved_risk_evidence(),
                }
            ],
        },
        {
            "id": "s3",
            "timestamp": "2024-01-03T00:00:00Z",
            "symbol": "AAPL",
            "open": "105",
        },
    ]
    run_contract = BacktestRunContract(execution_assumptions=_assumptions())

    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="p56-bt-flow",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert len(flow.fills) == 2
    assert [fill.occurred_at for fill in flow.fills] == ["2024-01-02T00:00:00Z", "2024-01-03T00:00:00Z"]
    assert flow.fills[0].execution_price == Decimal("101.10100000")
    assert flow.fills[1].execution_price == Decimal("104.89500000")


def test_p56_bt_cost_assumptions_are_fixed_per_order_and_side_aware() -> None:
    snapshots = sort_snapshots(
        [
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [
                    {
                        "signal_id": "sig-buy",
                        "action": "BUY",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [
                    {
                        "signal_id": "sig-sell",
                        "action": "SELL",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {
                "id": "s3",
                "timestamp": "2024-01-03T00:00:00Z",
                "symbol": "AAPL",
                "open": "102",
            },
        ]
    )
    assumptions = _assumptions()
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="p56-bt-cost",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=assumptions,
    )

    assert [fill.commission for fill in flow.fills] == [Decimal("1.25"), Decimal("1.25")]
    assert baseline["assumptions"] == assumptions.to_payload()
    assert baseline["summary"]["total_commission"] == 2.5
    assert baseline["summary"]["total_slippage_cost"] == 0.2
    assert baseline["summary"]["total_transaction_cost"] == 2.7


def test_p56_bt_replay_is_deterministic_and_cost_sensitive_to_assumptions() -> None:
    snapshots = sort_snapshots(
        [
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [
                    {
                        "signal_id": "sig-buy",
                        "action": "BUY",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [
                    {
                        "signal_id": "sig-sell",
                        "action": "SELL",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {"id": "s3", "timestamp": "2024-01-03T00:00:00Z", "symbol": "AAPL", "open": "102"},
        ]
    )
    assumptions = BacktestExecutionAssumptions(slippage_bps=10, commission_per_order=Decimal("1.25"))
    run_contract = BacktestRunContract(execution_assumptions=assumptions)

    first = simulate_execution_flow(
        snapshots=snapshots,
        run_id="p56-bt-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    second = simulate_execution_flow(
        snapshots=snapshots,
        run_id="p56-bt-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    baseline_first = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=first.fills,
        execution_assumptions=assumptions,
    )
    baseline_second = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=second.fills,
        execution_assumptions=assumptions,
    )
    higher_cost_assumptions = BacktestExecutionAssumptions(
        slippage_bps=20,
        commission_per_order=Decimal("2.50"),
    )
    higher_cost_flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="p56-bt-repro",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(execution_assumptions=higher_cost_assumptions),
    )
    higher_cost_baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=higher_cost_flow.fills,
        execution_assumptions=higher_cost_assumptions,
    )

    assert baseline_first == baseline_second
    assert (
        higher_cost_baseline["summary"]["ending_equity_cost_aware"]
        < baseline_first["summary"]["ending_equity_cost_aware"]
    )


def test_p56_bt_realism_profile_matrix_is_deterministic_and_replay_stable() -> None:
    snapshots = sort_snapshots(
        [
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [
                    {
                        "signal_id": "sig-buy",
                        "action": "BUY",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [
                    {
                        "signal_id": "sig-sell",
                        "action": "SELL",
                        "quantity": "1",
                        "symbol": "AAPL",
                        "risk_evidence": _approved_risk_evidence(),
                    }
                ],
            },
            {"id": "s3", "timestamp": "2024-01-03T00:00:00Z", "symbol": "AAPL", "open": "102"},
        ]
    )
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.25"),
            fill_timing="next_snapshot",
        )
    )

    first = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="p56-bt-matrix",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    second = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="p56-bt-matrix",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert first == second
    assert first["profile_order"] == [
        "configured_baseline",
        "cost_free_reference",
        "bounded_cost_stress",
    ]
    profiles = {profile["profile_id"]: profile for profile in first["profiles"]}
    assert profiles["configured_baseline"]["delta_vs_baseline"]["summary"]["total_transaction_cost"] == 0.0
    assert profiles["cost_free_reference"]["summary"]["total_transaction_cost"] == 0.0
    assert profiles["bounded_cost_stress"]["summary"]["total_transaction_cost"] >= (
        profiles["configured_baseline"]["summary"]["total_transaction_cost"]
    )

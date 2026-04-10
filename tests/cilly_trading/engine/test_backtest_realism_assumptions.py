from __future__ import annotations

from decimal import Decimal

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    BacktestRunContract,
    build_cost_slippage_metrics_baseline,
    simulate_execution_flow,
    sort_snapshots,
)


def _assumptions() -> BacktestExecutionAssumptions:
    return BacktestExecutionAssumptions(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing="next_snapshot",
    )


def test_p56_bt_fill_timing_and_price_source_are_bounded_to_current_model() -> None:
    snapshots = [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": "100",
            "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "price": "101",
            "signals": [{"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"}],
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
                "signals": [{"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"}],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [{"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"}],
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


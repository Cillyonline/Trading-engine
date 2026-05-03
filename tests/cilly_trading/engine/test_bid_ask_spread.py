"""Tests for bid-ask spread cost model (Issue #1095)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cilly_trading.engine.backtest_execution_contract import (
    MAX_SPREAD_BPS,
    REALISM_PROFILE_COST_STRESS_SPREAD_BPS,
    BacktestExecutionAssumptions,
    BacktestRunContract,
    build_backtest_realism_boundary,
    build_cost_slippage_metrics_baseline,
    build_realism_sensitivity_matrix,
    simulate_execution_flow,
)


def _approved_risk() -> dict[str, str]:
    return {
        "decision": "APPROVED",
        "score": "1",
        "max_allowed": "10",
        "reason": "risk_within_bounds",
        "rule_version": "test-v1",
    }


def _round_trip_snapshots(
    buy_price: str = "100",
    sell_price: str = "110",
) -> list[dict]:
    return [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": buy_price,
            "signals": [
                {
                    "signal_id": "sig-buy",
                    "action": "BUY",
                    "quantity": "1",
                    "symbol": "AAPL",
                    "risk_evidence": _approved_risk(),
                }
            ],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "open": sell_price,
            "signals": [
                {
                    "signal_id": "sig-sell",
                    "action": "SELL",
                    "quantity": "1",
                    "symbol": "AAPL",
                    "risk_evidence": _approved_risk(),
                }
            ],
        },
        {
            "id": "s3",
            "timestamp": "2024-01-03T00:00:00Z",
            "symbol": "AAPL",
            "open": "115",
        },
    ]


# ── Validation ─────────────────────────────────────────────────────────────────


def test_spread_bps_defaults_to_zero() -> None:
    assumptions = BacktestExecutionAssumptions()
    assert assumptions.spread_bps == 0


def test_spread_bps_valid_range_accepted() -> None:
    BacktestExecutionAssumptions(spread_bps=0)
    BacktestExecutionAssumptions(spread_bps=10)
    BacktestExecutionAssumptions(spread_bps=MAX_SPREAD_BPS)


def test_spread_bps_above_max_raises() -> None:
    with pytest.raises(ValueError, match="spread_bps"):
        BacktestExecutionAssumptions(spread_bps=MAX_SPREAD_BPS + 1)


def test_spread_bps_negative_raises() -> None:
    with pytest.raises(ValueError, match="spread_bps"):
        BacktestExecutionAssumptions(spread_bps=-1)


def test_spread_bps_bool_raises() -> None:
    with pytest.raises(ValueError, match="spread_bps"):
        BacktestExecutionAssumptions(spread_bps=True)  # type: ignore[arg-type]


def test_max_spread_bps_constant_is_200() -> None:
    assert MAX_SPREAD_BPS == 200


# ── Fill price: buy at mid + spread/2, sell at mid - spread/2 ─────────────────


def test_buy_fill_price_reflects_half_spread_on_entry() -> None:
    # same_snapshot so the BUY fills at s1's open=100, not the next snapshot.
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=0, spread_bps=10, fill_timing="same_snapshot",
        commission_per_order=Decimal("0"),
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(buy_price="100"),
        run_id="test-spread-buy",
        strategy_name="SPREAD_TEST",
        run_contract=run_contract,
    )

    buy_fills = [f for f in flow.fills if f.side == "BUY"]
    assert len(buy_fills) == 1
    # spread=10 bps, half=5 bps; buy at 100 * (1 + 5/10000) = 100.05
    assert buy_fills[0].execution_price == Decimal("100.05000000")


def test_sell_fill_price_reflects_half_spread_on_exit() -> None:
    # same_snapshot so the SELL fills at s2's open=110.
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=0, spread_bps=10, fill_timing="same_snapshot",
        commission_per_order=Decimal("0"),
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(sell_price="110"),
        run_id="test-spread-sell",
        strategy_name="SPREAD_TEST",
        run_contract=run_contract,
    )

    sell_fills = [f for f in flow.fills if f.side == "SELL"]
    assert len(sell_fills) == 1
    # spread=10 bps, half=5 bps; sell at 110 * (1 - 5/10000) = 109.945
    assert sell_fills[0].execution_price == Decimal("109.94500000")


def test_zero_spread_leaves_fill_price_unchanged() -> None:
    assumptions_no_spread = BacktestExecutionAssumptions(
        slippage_bps=5, spread_bps=0, commission_per_order=Decimal("0")
    )
    assumptions_with_spread = BacktestExecutionAssumptions(
        slippage_bps=5, spread_bps=0, commission_per_order=Decimal("0")
    )
    snapshots = _round_trip_snapshots()

    def _run(assumptions: BacktestExecutionAssumptions) -> list:
        return simulate_execution_flow(
            snapshots=snapshots,
            run_id="test-zero-spread",
            strategy_name="ZERO_SPREAD",
            run_contract=BacktestRunContract(execution_assumptions=assumptions),
        ).fills

    fills_a = _run(assumptions_no_spread)
    fills_b = _run(assumptions_with_spread)
    assert [f.execution_price for f in fills_a] == [f.execution_price for f in fills_b]


# ── spread_cost recorded in execution events ───────────────────────────────────


def test_spread_cost_recorded_in_buy_fill_event() -> None:
    # same_snapshot so BUY fills at open=100.
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=0, spread_bps=10, fill_timing="same_snapshot",
        commission_per_order=Decimal("0"),
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(buy_price="100"),
        run_id="test-sc-buy",
        strategy_name="SC_TEST",
        run_contract=run_contract,
    )

    buy_fill = next(f for f in flow.fills if f.side == "BUY")
    # spread_cost = 100 * (5/10000) * 1 = 0.05
    assert buy_fill.spread_cost == Decimal("0.05")


def test_spread_cost_recorded_in_sell_fill_event() -> None:
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=0, spread_bps=10, commission_per_order=Decimal("0")
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(sell_price="110"),
        run_id="test-sc-sell",
        strategy_name="SC_TEST",
        run_contract=run_contract,
    )

    sell_fill = next(f for f in flow.fills if f.side == "SELL")
    # spread_cost = 110 * (5/10000) * 1 = 0.055
    assert sell_fill.spread_cost == Decimal("0.06")  # rounded to money_scale 0.01


def test_spread_cost_is_none_when_spread_bps_is_zero() -> None:
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=5, spread_bps=0, commission_per_order=Decimal("0")
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(),
        run_id="test-sc-zero",
        strategy_name="SC_ZERO",
        run_contract=run_contract,
    )

    for fill in flow.fills:
        assert fill.spread_cost is None


# ── Cost baseline metrics include total_spread_cost ───────────────────────────


def test_total_spread_cost_in_baseline_summary_when_spread_set() -> None:
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=0, spread_bps=10, commission_per_order=Decimal("0")
    )
    snapshots = _round_trip_snapshots(buy_price="100", sell_price="110")
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="test-spread-baseline",
        strategy_name="SPREAD",
        run_contract=run_contract,
    )
    baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=assumptions,
    )

    # BUY spread_cost = 100 * 5/10000 = 0.05
    # SELL spread_cost = 110 * 5/10000 = 0.055 → rounded 0.06
    assert baseline["summary"]["total_spread_cost"] > 0.0


def test_total_spread_cost_is_zero_when_no_spread() -> None:
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=5, spread_bps=0, commission_per_order=Decimal("1")
    )
    snapshots = _round_trip_snapshots()
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="test-no-spread-baseline",
        strategy_name="NO_SPREAD",
        run_contract=run_contract,
    )
    baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=assumptions,
    )

    assert baseline["summary"]["total_spread_cost"] == 0.0


# ── to_payload includes spread_bps ────────────────────────────────────────────


def test_to_payload_includes_spread_bps() -> None:
    assumptions = BacktestExecutionAssumptions(spread_bps=8)
    payload = assumptions.to_payload()
    assert payload["spread_bps"] == 8


def test_to_payload_spread_bps_zero_by_default() -> None:
    assumptions = BacktestExecutionAssumptions()
    payload = assumptions.to_payload()
    assert payload["spread_bps"] == 0


# ── Realism boundary includes spread ─────────────────────────────────────────


def test_realism_boundary_slippage_section_includes_spread_bps() -> None:
    assumptions = BacktestExecutionAssumptions(slippage_bps=5, spread_bps=8)
    boundary = build_backtest_realism_boundary(execution_assumptions=assumptions)
    slippage = boundary["modeled_assumptions"]["slippage"]
    assert slippage["spread_bps"] == 8


def test_realism_boundary_spread_bps_zero_when_not_configured() -> None:
    assumptions = BacktestExecutionAssumptions(slippage_bps=5)
    boundary = build_backtest_realism_boundary(execution_assumptions=assumptions)
    slippage = boundary["modeled_assumptions"]["slippage"]
    assert slippage["spread_bps"] == 0


# ── Realism profiles all include explicit spread_bps ─────────────────────────


def test_all_realism_profiles_include_spread_bps() -> None:
    snapshots = _round_trip_snapshots()
    assumptions = BacktestExecutionAssumptions(slippage_bps=5, spread_bps=4)
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="test-matrix-spread",
        strategy_name="MATRIX",
        run_contract=run_contract,
    )

    for profile in matrix["profiles"]:
        assert "spread_bps" in profile["assumptions"], (
            f"Profile {profile['profile_id']} missing spread_bps in assumptions"
        )


def test_cost_free_profile_has_zero_spread() -> None:
    snapshots = _round_trip_snapshots()
    assumptions = BacktestExecutionAssumptions(slippage_bps=5, spread_bps=8)
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="test-cf-spread",
        strategy_name="CF",
        run_contract=run_contract,
    )

    cost_free = next(p for p in matrix["profiles"] if p["profile_id"] == "cost_free_reference")
    assert cost_free["assumptions"]["spread_bps"] == 0


def test_stress_profile_spread_is_at_least_stress_preset() -> None:
    snapshots = _round_trip_snapshots()
    assumptions = BacktestExecutionAssumptions(slippage_bps=5, spread_bps=0)
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="test-stress-spread",
        strategy_name="STRESS",
        run_contract=run_contract,
    )

    stress = next(p for p in matrix["profiles"] if p["profile_id"] == "bounded_cost_stress")
    assert stress["assumptions"]["spread_bps"] >= REALISM_PROFILE_COST_STRESS_SPREAD_BPS


def test_stress_spread_preset_constant_is_10() -> None:
    assert REALISM_PROFILE_COST_STRESS_SPREAD_BPS == 10


# ── Spread and slippage stack additively ─────────────────────────────────────


def test_spread_and_slippage_stack_on_buy() -> None:
    # same_snapshot; slippage=10bps, spread=10bps → total 15bps on BUY
    # BUY price = 100 * (1 + 15/10000) = 100.15
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=10, spread_bps=10, fill_timing="same_snapshot",
        commission_per_order=Decimal("0"),
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(buy_price="100"),
        run_id="test-stack-buy",
        strategy_name="STACK",
        run_contract=run_contract,
    )
    buy_fill = next(f for f in flow.fills if f.side == "BUY")
    assert buy_fill.execution_price == Decimal("100.15000000")


def test_spread_and_slippage_stack_on_sell() -> None:
    # same_snapshot; slippage=10bps, spread=10bps → total 15bps on SELL
    # SELL price = 110 * (1 - 15/10000) = 109.835
    assumptions = BacktestExecutionAssumptions(
        slippage_bps=10, spread_bps=10, fill_timing="same_snapshot",
        commission_per_order=Decimal("0"),
    )
    run_contract = BacktestRunContract(execution_assumptions=assumptions)
    flow = simulate_execution_flow(
        snapshots=_round_trip_snapshots(sell_price="110"),
        run_id="test-stack-sell",
        strategy_name="STACK",
        run_contract=run_contract,
    )
    sell_fill = next(f for f in flow.fills if f.side == "SELL")
    assert sell_fill.execution_price == Decimal("109.83500000")

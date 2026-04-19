from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from cilly_trading.models import Trade
from cilly_trading.portfolio_framework import (
    CapitalAllocationRules,
    PortfolioGuardrailLimits,
    PortfolioPosition,
    PortfolioState,
    PrioritizedAllocationConfig,
    PrioritizedAllocationSignal,
    StrategyAllocationRule,
    aggregate_portfolio_exposure,
    assess_capital_allocation,
    run_portfolio_decision_pipeline,
)
from api.services.paper_inspection_service import build_portfolio_positions_from_trades


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_phase43_contract_doc_declares_bounded_partial_acceptance_surface() -> None:
    content = (
        REPO_ROOT
        / "docs"
        / "architecture"
        / "phases"
        / "phase-43-portfolio-inspection-contract.md"
    ).read_text(encoding="utf-8")

    assert "Phase 43 remains **Partially Implemented**." in content
    assert "Capital Allocation Primitive" in content
    assert "Exposure Handling Primitive" in content
    assert "Multi-Position Consistency Primitive" in content
    assert "Implemented In Scope" in content
    assert "Not Implemented In This Phase Scope" in content
    assert "does **not** imply any live-trading or broker-readiness claim" in content


def test_phase43_capital_allocation_contract_enforces_global_and_strategy_caps() -> None:
    state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=2.0,
                mark_price=100.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="ETHUSDT",
                quantity=1.0,
                mark_price=100.0,
            ),
        ),
    )
    rules = CapitalAllocationRules(
        global_capital_cap_pct=0.25,
        strategy_rules=(
            StrategyAllocationRule(
                strategy_id="alpha",
                capital_cap_pct=0.15,
                allocation_score=1.0,
            ),
            StrategyAllocationRule(
                strategy_id="beta",
                capital_cap_pct=0.25,
                allocation_score=1.0,
            ),
        ),
    )

    assessment = assess_capital_allocation(state, rules)

    assert assessment.approved is False
    assert assessment.reasons == (
        "global_cap_exceeded: total_absolute_notional=300.0 global_cap_notional=250.0",
        "strategy_cap_exceeded: strategy_id=alpha",
    )
    assert [item.rule_code for item in assessment.policy_evidence] == [
        "global_cap_notional",
        "strategy_cap_notional",
    ]


def test_phase43_exposure_handling_contract_reports_deterministic_multi_position_metrics() -> None:
    state = PortfolioState(
        account_equity=2000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="SOLUSDT",
                quantity=5.0,
                mark_price=20.0,
            ),
            PortfolioPosition(
                strategy_id="alpha",
                symbol="ADAUSDT",
                quantity=50.0,
                mark_price=1.0,
            ),
            PortfolioPosition(
                strategy_id="beta",
                symbol="ADAUSDT",
                quantity=-20.0,
                mark_price=1.0,
            ),
        ),
    )

    summary = aggregate_portfolio_exposure(state)

    assert summary.total_absolute_notional == 170.0
    assert summary.net_notional == 130.0
    assert summary.gross_exposure_pct == 0.085
    assert summary.net_exposure_pct == 0.065
    assert [item.symbol for item in summary.symbol_exposures] == ["ADAUSDT", "SOLUSDT"]
    assert summary.symbol_exposures[0].net_notional == 30.0


def test_phase43_multi_position_consistency_keeps_final_state_bounded_to_approved_signals() -> None:
    initial_state = PortfolioState(
        account_equity=1000.0,
        positions=(
            PortfolioPosition(
                strategy_id="alpha",
                symbol="BTCUSDT",
                quantity=1.0,
                mark_price=100.0,
            ),
        ),
    )

    result = run_portfolio_decision_pipeline(
        state=initial_state,
        signals=(
            PrioritizedAllocationSignal(
                signal_id="sig-1",
                strategy_id="beta",
                symbol="ETHUSDT",
                priority_score=90.0,
                requested_notional=100.0,
                signal_timestamp="2026-04-10T08:00:00Z",
                mark_price=100.0,
            ),
            PrioritizedAllocationSignal(
                signal_id="sig-2",
                strategy_id="beta",
                symbol="SOLUSDT",
                priority_score=80.0,
                requested_notional=300.0,
                signal_timestamp="2026-04-10T08:01:00Z",
                mark_price=100.0,
            ),
        ),
        allocation_config=PrioritizedAllocationConfig(
            available_capital_notional=300.0,
            max_positions=2,
            default_position_cap_notional=300.0,
            min_allocation_notional=10.0,
        ),
        allocation_rules=CapitalAllocationRules(
            global_capital_cap_pct=0.25,
            strategy_rules=(
                StrategyAllocationRule(
                    strategy_id="alpha",
                    capital_cap_pct=0.25,
                    allocation_score=1.0,
                ),
                StrategyAllocationRule(
                    strategy_id="beta",
                    capital_cap_pct=0.25,
                    allocation_score=1.0,
                ),
            ),
        ),
        guardrail_limits=PortfolioGuardrailLimits(
            max_gross_exposure_pct=1.0,
            max_abs_net_exposure_pct=1.0,
            max_offset_exposure_pct=1.0,
            max_strategy_concentration_pct=1.0,
            max_symbol_concentration_pct=1.0,
            max_position_concentration_pct=1.0,
        ),
    )

    assert result.approved_signal_ids == ("sig-1",)
    assert result.constraint_hit_signal_ids == ("sig-2",)
    assert len(result.final_state.positions) == 2
    assert {(item.strategy_id, item.symbol) for item in result.final_state.positions} == {
        ("alpha", "BTCUSDT"),
        ("beta", "ETHUSDT"),
    }


def test_phase43_portfolio_positions_aggregate_open_trades_by_strategy_symbol_only() -> None:
    trades = [
        Trade.model_validate(
            {
                "trade_id": "t-1",
                "position_id": "p-1",
                "strategy_id": "alpha",
                "symbol": "BTCUSDT",
                "direction": "long",
                "status": "open",
                "opened_at": "2026-04-10T08:00:00Z",
                "closed_at": None,
                "quantity_opened": Decimal("2"),
                "quantity_closed": Decimal("0"),
                "average_entry_price": Decimal("100"),
                "average_exit_price": None,
                "realized_pnl": None,
                "unrealized_pnl": Decimal("3"),
                "opening_order_ids": ["o-1"],
                "closing_order_ids": [],
                "execution_event_ids": ["e-1"],
            }
        ),
        Trade.model_validate(
            {
                "trade_id": "t-2",
                "position_id": "p-2",
                "strategy_id": "alpha",
                "symbol": "BTCUSDT",
                "direction": "long",
                "status": "open",
                "opened_at": "2026-04-10T08:01:00Z",
                "closed_at": None,
                "quantity_opened": Decimal("3"),
                "quantity_closed": Decimal("0"),
                "average_entry_price": Decimal("110"),
                "average_exit_price": None,
                "realized_pnl": None,
                "unrealized_pnl": Decimal("4"),
                "opening_order_ids": ["o-2"],
                "closing_order_ids": [],
                "execution_event_ids": ["e-2"],
            }
        ),
        Trade.model_validate(
            {
                "trade_id": "t-closed",
                "position_id": "p-3",
                "strategy_id": "alpha",
                "symbol": "BTCUSDT",
                "direction": "long",
                "status": "closed",
                "opened_at": "2026-04-10T08:02:00Z",
                "closed_at": "2026-04-10T08:03:00Z",
                "quantity_opened": Decimal("1"),
                "quantity_closed": Decimal("1"),
                "average_entry_price": Decimal("95"),
                "average_exit_price": Decimal("96"),
                "realized_pnl": Decimal("1"),
                "unrealized_pnl": None,
                "opening_order_ids": ["o-3"],
                "closing_order_ids": ["o-4"],
                "execution_event_ids": ["e-3", "e-4"],
            }
        ),
    ]

    positions = build_portfolio_positions_from_trades(trades=trades)

    assert len(positions) == 1
    assert positions[0].strategy_id == "alpha"
    assert positions[0].symbol == "BTCUSDT"
    assert positions[0].size == Decimal("5")
    assert positions[0].average_price == Decimal("106")
    assert positions[0].unrealized_pnl == Decimal("7")

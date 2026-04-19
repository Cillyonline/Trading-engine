from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    BacktestRunContract,
    BacktestSignalTranslationConfig,
    build_backtest_realism_boundary,
    build_cost_slippage_metrics_baseline,
    build_realism_sensitivity_matrix,
    serialize_fills,
    serialize_orders,
    serialize_positions,
    sort_snapshots,
    simulate_execution_flow,
)
from cilly_trading.engine.backtest_runner import BacktestRunner, BacktestRunnerConfig


def _sample_flow_snapshots() -> list[dict[str, object]]:
    return [
        {
            "id": "s1",
            "timestamp": "2024-01-01T00:00:00Z",
            "symbol": "AAPL",
            "open": "100",
            "signals": [
                {"signal_id": "sig-buy", "action": "BUY", "quantity": "2", "symbol": "AAPL"},
            ],
        },
        {
            "id": "s2",
            "timestamp": "2024-01-02T00:00:00Z",
            "symbol": "AAPL",
            "open": "110",
            "signals": [
                {"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"},
            ],
        },
        {
            "id": "s3",
            "timestamp": "2024-01-03T00:00:00Z",
            "symbol": "AAPL",
            "open": "111",
        },
    ]


def test_contract_validation_rejects_invalid_execution_assumptions() -> None:
    with pytest.raises(ValueError, match="slippage_bps"):
        BacktestExecutionAssumptions(slippage_bps=-1)
    with pytest.raises(ValueError, match="slippage_bps"):
        BacktestExecutionAssumptions(slippage_bps=251)
    with pytest.raises(ValueError, match="commission_per_order"):
        BacktestExecutionAssumptions(commission_per_order=Decimal("-0.01"))
    with pytest.raises(ValueError, match="commission_per_order"):
        BacktestExecutionAssumptions(commission_per_order=Decimal("25.01"))
    with pytest.raises(ValueError, match="partial_fills_allowed"):
        BacktestExecutionAssumptions(partial_fills_allowed=True)


def test_contract_validation_rejects_unsupported_execution_assumption_values() -> None:
    with pytest.raises(ValueError, match="fill_model"):
        BacktestExecutionAssumptions(fill_model="synthetic_market")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="fill_timing"):
        BacktestExecutionAssumptions(fill_timing="next_tick")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="price_source"):
        BacktestExecutionAssumptions(price_source="close_only")  # type: ignore[arg-type]


def test_contract_validation_rejects_invalid_execution_input_types() -> None:
    with pytest.raises(ValueError, match="slippage_bps must be an integer"):
        BacktestExecutionAssumptions(slippage_bps=True)  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="slippage_bps must be an integer"):
        BacktestExecutionAssumptions(slippage_bps="10")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="commission_per_order must be decimal-compatible"):
        BacktestExecutionAssumptions(commission_per_order="not-a-number")  # type: ignore[arg-type]
    with pytest.raises(ValueError, match="commission_per_order must be finite"):
        BacktestExecutionAssumptions(commission_per_order=Decimal("NaN"))
    with pytest.raises(ValueError, match="partial_fills_allowed must be a boolean"):
        BacktestExecutionAssumptions(partial_fills_allowed="false")  # type: ignore[arg-type]


def test_contract_validation_rejects_invalid_contract_version() -> None:
    with pytest.raises(ValueError, match="Unsupported backtest contract_version"):
        BacktestRunContract(contract_version="2.0.0")


def test_representative_backtest_flow_next_snapshot() -> None:
    result = simulate_execution_flow(
        snapshots=_sample_flow_snapshots(),
        run_id="run-1",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(
            execution_assumptions=BacktestExecutionAssumptions(
                slippage_bps=10,
                commission_per_order=Decimal("1.25"),
                fill_timing="next_snapshot",
            )
        ),
    )

    assert len(result.orders) == 2
    assert len(result.fills) == 2
    assert result.fills[0].order_id.endswith(":sig-buy:1")
    assert result.fills[0].occurred_at == "2024-01-02T00:00:00Z"
    assert result.fills[1].order_id.endswith(":sig-sell:2")
    assert result.fills[1].occurred_at == "2024-01-03T00:00:00Z"
    assert result.positions[0].status == "open"
    assert result.positions[0].net_quantity == Decimal("1.00000000")


def test_representative_backtest_flow_same_snapshot() -> None:
    result = simulate_execution_flow(
        snapshots=_sample_flow_snapshots(),
        run_id="run-2",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(
            execution_assumptions=BacktestExecutionAssumptions(
                slippage_bps=0,
                commission_per_order=Decimal("0"),
                fill_timing="same_snapshot",
            )
        ),
    )

    assert len(result.fills) == 2
    assert result.fills[0].occurred_at == "2024-01-01T00:00:00Z"
    assert result.fills[1].occurred_at == "2024-01-02T00:00:00Z"


def test_reproducibility_flow_serialization_is_deterministic() -> None:
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=3,
            commission_per_order=Decimal("0.55"),
        )
    )
    result_a = simulate_execution_flow(
        snapshots=_sample_flow_snapshots(),
        run_id="run-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    result_b = simulate_execution_flow(
        snapshots=_sample_flow_snapshots(),
        run_id="run-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert serialize_orders(result_a.orders) == serialize_orders(result_b.orders)
    assert serialize_fills(result_a.fills) == serialize_fills(result_b.fills)
    assert serialize_positions(result_a.positions) == serialize_positions(result_b.positions)


def test_cost_slippage_baseline_reports_expected_cost_delta() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="run-costs",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=run_contract.execution_assumptions,
    )

    assert baseline["summary"]["total_commission"] == 2.0
    assert baseline["summary"]["total_slippage_cost"] == 0.33
    assert baseline["summary"]["total_transaction_cost"] == 2.33
    assert baseline["summary"]["ending_equity_cost_aware"] == 99999.67
    assert baseline["summary"]["ending_equity_cost_free"] == 100002.0
    assert baseline["summary"]["fill_count"] == 2


def test_cost_slippage_baseline_is_reproducible() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="run-repro-baseline",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    first = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=run_contract.execution_assumptions,
    )
    second = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=run_contract.execution_assumptions,
    )

    assert first == second


def test_cost_slippage_baseline_changes_deterministically_when_cost_assumptions_change() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    low_cost_assumptions = BacktestExecutionAssumptions(
        slippage_bps=0,
        commission_per_order=Decimal("0"),
        fill_timing="next_snapshot",
    )
    high_cost_assumptions = BacktestExecutionAssumptions(
        slippage_bps=25,
        commission_per_order=Decimal("2.00"),
        fill_timing="next_snapshot",
    )

    flow_low = simulate_execution_flow(
        snapshots=snapshots,
        run_id="run-cost-low",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(execution_assumptions=low_cost_assumptions),
    )
    flow_high = simulate_execution_flow(
        snapshots=snapshots,
        run_id="run-cost-high",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(execution_assumptions=high_cost_assumptions),
    )

    baseline_low = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow_low.fills,
        execution_assumptions=low_cost_assumptions,
    )
    baseline_high = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow_high.fills,
        execution_assumptions=high_cost_assumptions,
    )

    assert baseline_low["summary"]["total_transaction_cost"] == 0.0
    assert baseline_high["summary"]["total_transaction_cost"] > baseline_low["summary"]["total_transaction_cost"]
    assert (
        baseline_high["summary"]["ending_equity_cost_aware"]
        < baseline_low["summary"]["ending_equity_cost_aware"]
    )


def test_backtest_realism_boundary_reports_modeled_and_unmodeled_assumptions() -> None:
    boundary = build_backtest_realism_boundary(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )

    assert boundary["boundary_version"] == "1.0.0"
    assert boundary["modeled_assumptions"]["fees"] == {
        "commission_model": "fixed_per_filled_order",
        "commission_per_order": "1.00",
    }
    assert boundary["modeled_assumptions"]["slippage"] == {
        "slippage_bps": 10,
        "slippage_model": "fixed_basis_points_by_side",
    }
    assert boundary["modeled_assumptions"]["fills"] == {
        "fill_model": "deterministic_market",
        "fill_timing": "next_snapshot",
        "partial_fills_allowed": False,
        "price_source": "open_then_price",
    }
    assert "Not modeled." in boundary["unmodeled_assumptions"]["market_hours"]
    assert "market-hours compliance realism" in boundary["evidence_boundary"]["unsupported_claims"]
    assert "bounded backtest evidence only" in boundary["evidence_boundary"]["decision_use_constraint"]


def test_negative_configuration_invalid_signal_mapping_fails() -> None:
    with pytest.raises(ValueError, match="Signal action mapping must not be empty"):
        BacktestSignalTranslationConfig(action_to_side={})


def test_negative_configuration_invalid_signal_payload_fails(tmp_path: Path) -> None:
    class _NoopStrategy:
        def on_run_start(self, config):  # type: ignore[no-untyped-def]
            return None

        def on_snapshot(self, snapshot, config):  # type: ignore[no-untyped-def]
            return None

        def on_run_end(self, config):  # type: ignore[no-untyped-def]
            return None

    snapshots_path = tmp_path / "snapshots.json"
    snapshots_path.write_text(
        json.dumps(
            [
                {
                    "id": "s1",
                    "timestamp": "2024-01-01T00:00:00Z",
                    "symbol": "AAPL",
                    "open": "100",
                    "signals": [{"signal_id": "sig-1", "action": "BUY", "quantity": "0"}],
                }
            ]
        ),
        encoding="utf-8",
    )
    snapshots = json.loads(snapshots_path.read_text(encoding="utf-8"))

    runner = BacktestRunner()
    with pytest.raises(ValueError, match="Signal quantity must be > 0"):
        runner.run(
            snapshots=snapshots,
            strategy_factory=lambda: _NoopStrategy(),
            config=BacktestRunnerConfig(output_dir=tmp_path / "out"),
        )


def test_realism_sensitivity_matrix_contract_schema_contains_profiles_metrics_and_deltas() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )

    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="run-matrix",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert matrix["matrix_version"] == "1.0.0"
    assert matrix["deterministic"] is True
    assert matrix["baseline_profile_id"] == "configured_baseline"
    assert matrix["profile_order"] == [
        "configured_baseline",
        "cost_free_reference",
        "bounded_cost_stress",
    ]
    assert len(matrix["profiles"]) == 3

    for profile in matrix["profiles"]:
        assert "profile_id" in profile
        assert "assumptions" in profile
        assert "summary" in profile
        assert "metrics" in profile
        assert "delta_vs_baseline" in profile
        assert "summary" in profile["delta_vs_baseline"]
        assert "metrics" in profile["delta_vs_baseline"]


def test_realism_sensitivity_matrix_is_deterministic_for_identical_inputs() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )

    first = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="run-matrix-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    second = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="run-matrix-repro",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert first == second


def test_realism_sensitivity_matrix_delta_calculation_consistency() -> None:
    snapshots = sort_snapshots(_sample_flow_snapshots())
    run_contract = BacktestRunContract(
        execution_assumptions=BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("1.00"),
            fill_timing="next_snapshot",
        )
    )
    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="run-matrix-deltas",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    profiles = {profile["profile_id"]: profile for profile in matrix["profiles"]}
    baseline = profiles["configured_baseline"]
    no_cost = profiles["cost_free_reference"]

    assert baseline["delta_vs_baseline"]["summary"]["ending_equity_cost_aware"] == 0.0
    assert baseline["delta_vs_baseline"]["metrics"]["total_return"] == 0.0
    assert no_cost["delta_vs_baseline"]["summary"]["ending_equity_cost_aware"] == pytest.approx(2.33)
    assert no_cost["delta_vs_baseline"]["summary"]["total_transaction_cost"] == pytest.approx(-2.33)

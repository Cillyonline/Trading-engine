"""Hardened deterministic execution-assumption and realism-boundary regression coverage.

These tests harden the canonical realism-boundary contract documented in
``docs/governance/backtest-realism-boundary-contract.md`` and the runtime disclosure
documented in ``docs/operations/runtime/backtest_realism_boundary_runtime.md``.

They cover:

- deterministic replay stability across the realism boundary, baseline, sensitivity
  matrix, and serialized artifacts under identical covered execution assumptions
- bounded, explainable cost sensitivity when slippage and commission assumptions
  change in isolation
- canonical bounded-realism wording in the governance and runtime docs that prevents
  overreading backtest output as live-execution proof or trader validation
"""

from __future__ import annotations

import json
from decimal import Decimal
from pathlib import Path

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    BacktestRunContract,
    build_backtest_realism_boundary,
    build_cost_slippage_metrics_baseline,
    build_realism_sensitivity_matrix,
    serialize_fills,
    serialize_orders,
    serialize_positions,
    simulate_execution_flow,
    sort_snapshots,
)


REPO_ROOT = Path(__file__).resolve().parents[1]
GOVERNANCE_DOC = (
    REPO_ROOT / "docs" / "governance" / "backtest-realism-boundary-contract.md"
)
RUNTIME_DOC = (
    REPO_ROOT
    / "docs"
    / "operations"
    / "runtime"
    / "backtest_realism_boundary_runtime.md"
)


def _canonical_snapshots() -> list[dict[str, object]]:
    return sort_snapshots(
        [
            {
                "id": "s1",
                "timestamp": "2024-01-01T00:00:00Z",
                "symbol": "AAPL",
                "open": "100",
                "signals": [
                    {"signal_id": "sig-buy", "action": "BUY", "quantity": "1", "symbol": "AAPL"},
                ],
            },
            {
                "id": "s2",
                "timestamp": "2024-01-02T00:00:00Z",
                "symbol": "AAPL",
                "open": "101",
                "signals": [
                    {"signal_id": "sig-sell", "action": "SELL", "quantity": "1", "symbol": "AAPL"},
                ],
            },
            {"id": "s3", "timestamp": "2024-01-03T00:00:00Z", "symbol": "AAPL", "open": "102"},
        ]
    )


def _baseline_assumptions() -> BacktestExecutionAssumptions:
    return BacktestExecutionAssumptions(
        slippage_bps=10,
        commission_per_order=Decimal("1.25"),
        fill_timing="next_snapshot",
    )


# ---------------------------------------------------------------------------
# Acceptance Criterion 2: deterministic replay of identical covered assumptions
# yields stable outputs.
# ---------------------------------------------------------------------------


def test_realism_boundary_disclosure_is_byte_stable_under_identical_assumptions() -> None:
    assumptions = _baseline_assumptions()

    first = build_backtest_realism_boundary(execution_assumptions=assumptions)
    second = build_backtest_realism_boundary(execution_assumptions=assumptions)

    assert first == second
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    assert set(first["modeled_assumptions"].keys()) == {"fees", "slippage", "fills"}
    assert set(first["unmodeled_assumptions"].keys()) == {
        "market_hours",
        "broker_behavior",
        "liquidity_and_microstructure",
    }


def test_deterministic_replay_artifacts_are_byte_stable_under_identical_assumptions() -> None:
    snapshots = _canonical_snapshots()
    assumptions = _baseline_assumptions()
    run_contract = BacktestRunContract(execution_assumptions=assumptions)

    first_flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="realism-replay",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    second_flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="realism-replay",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert serialize_orders(first_flow.orders) == serialize_orders(second_flow.orders)
    assert serialize_fills(first_flow.fills) == serialize_fills(second_flow.fills)
    assert serialize_positions(first_flow.positions) == serialize_positions(
        second_flow.positions
    )

    first_baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=first_flow.fills,
        execution_assumptions=assumptions,
    )
    second_baseline = build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=second_flow.fills,
        execution_assumptions=assumptions,
    )

    assert json.dumps(first_baseline, sort_keys=True, default=str) == json.dumps(
        second_baseline, sort_keys=True, default=str
    )

    first_matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="realism-replay",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )
    second_matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="realism-replay",
        strategy_name="REFERENCE",
        run_contract=run_contract,
    )

    assert json.dumps(first_matrix, sort_keys=True, default=str) == json.dumps(
        second_matrix, sort_keys=True, default=str
    )


# ---------------------------------------------------------------------------
# Acceptance Criterion 3: covered tests show bounded, explainable sensitivity
# under materially different cost assumptions.
# ---------------------------------------------------------------------------


def _baseline_cost_summary(assumptions: BacktestExecutionAssumptions) -> dict[str, object]:
    snapshots = _canonical_snapshots()
    flow = simulate_execution_flow(
        snapshots=snapshots,
        run_id="realism-sensitivity",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(execution_assumptions=assumptions),
    )
    return build_cost_slippage_metrics_baseline(
        ordered_snapshots=snapshots,
        fills=flow.fills,
        execution_assumptions=assumptions,
    )["summary"]


def test_slippage_only_increase_produces_bounded_explainable_delta() -> None:
    base = _baseline_cost_summary(_baseline_assumptions())
    higher_slippage = _baseline_cost_summary(
        BacktestExecutionAssumptions(
            slippage_bps=40,
            commission_per_order=Decimal("1.25"),
            fill_timing="next_snapshot",
        )
    )

    # Slippage cost MUST be monotonically non-decreasing in slippage_bps,
    # while commission MUST be unchanged when only slippage changes.
    assert higher_slippage["total_slippage_cost"] > base["total_slippage_cost"]
    assert higher_slippage["total_commission"] == base["total_commission"]
    assert higher_slippage["total_transaction_cost"] > base["total_transaction_cost"]
    assert (
        higher_slippage["ending_equity_cost_aware"]
        < base["ending_equity_cost_aware"]
    )


def test_commission_only_increase_produces_bounded_explainable_delta() -> None:
    base = _baseline_cost_summary(_baseline_assumptions())
    higher_commission = _baseline_cost_summary(
        BacktestExecutionAssumptions(
            slippage_bps=10,
            commission_per_order=Decimal("3.50"),
            fill_timing="next_snapshot",
        )
    )

    # Commission MUST be monotonically non-decreasing in commission_per_order,
    # while slippage MUST be unchanged when only commission changes.
    assert higher_commission["total_commission"] > base["total_commission"]
    assert higher_commission["total_slippage_cost"] == base["total_slippage_cost"]
    assert higher_commission["total_transaction_cost"] > base["total_transaction_cost"]
    assert (
        higher_commission["ending_equity_cost_aware"]
        < base["ending_equity_cost_aware"]
    )


def test_realism_sensitivity_matrix_bounded_profile_directionality() -> None:
    snapshots = _canonical_snapshots()
    matrix = build_realism_sensitivity_matrix(
        ordered_snapshots=snapshots,
        run_id="realism-sensitivity-matrix",
        strategy_name="REFERENCE",
        run_contract=BacktestRunContract(execution_assumptions=_baseline_assumptions()),
    )

    profiles = {profile["profile_id"]: profile for profile in matrix["profiles"]}

    assert profiles["cost_free_reference"]["summary"]["total_transaction_cost"] == 0.0
    assert profiles["cost_free_reference"]["summary"]["total_commission"] == 0.0
    assert profiles["cost_free_reference"]["summary"]["total_slippage_cost"] == 0.0

    assert (
        profiles["bounded_cost_stress"]["summary"]["total_transaction_cost"]
        >= profiles["configured_baseline"]["summary"]["total_transaction_cost"]
    )
    assert (
        profiles["bounded_cost_stress"]["summary"]["total_commission"]
        >= profiles["configured_baseline"]["summary"]["total_commission"]
    )
    assert (
        profiles["bounded_cost_stress"]["summary"]["total_slippage_cost"]
        >= profiles["configured_baseline"]["summary"]["total_slippage_cost"]
    )


# ---------------------------------------------------------------------------
# Acceptance Criterion 1 + 4: canonical governance + runtime docs document
# covered assumptions and prevent overreading as live-execution / trader
# validation evidence.
# ---------------------------------------------------------------------------


def test_governance_doc_defines_canonical_realism_boundary_contract() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    # canonical purpose + scope
    assert "# Backtest Realism Boundary - Canonical Contract" in content
    assert "canonical governance authority" in content

    # covered execution assumptions are explicitly canonical
    assert "## Canonical Covered Execution Assumptions" in content
    assert "`fill_model` is fixed to `deterministic_market`" in content
    assert "`fill_timing`" in content
    assert "`price_source` is fixed to `open_then_price`" in content
    assert "`partial_fills_allowed` is fixed to `false`" in content
    assert "`fixed_basis_points_by_side`" in content
    assert "`fixed_per_filled_order`" in content

    # canonical realism boundary disclosure
    assert "## Canonical Realism Boundary Disclosure" in content
    assert "`modeled_assumptions`" in content
    assert "`unmodeled_assumptions`" in content
    assert "market hours" in content
    assert "broker routing" in content
    assert "order-book depth" in content

    # deterministic replay + bounded sensitivity guarantees
    assert "## Deterministic Replay Stability (Canonical)" in content
    assert "byte-stable" in content
    assert "## Bounded Sensitivity Under Materially Different Cost Assumptions (Canonical)" in content
    assert "MUST NOT decrease `total_slippage_cost`" in content
    assert "MUST NOT decrease `total_commission`" in content
    assert "`bounded_cost_stress`" in content
    assert "`cost_free_reference`" in content


def test_governance_doc_prevents_overreading_as_live_or_trader_validation() -> None:
    content = GOVERNANCE_DOC.read_text(encoding="utf-8")

    assert "## Canonical Interpretation Boundary" in content
    assert "MUST NOT be used as evidence" in content
    assert "live-trading readiness or approval" in content
    assert "broker execution realism" in content
    assert "market-hours compliance realism" in content
    assert "liquidity or market microstructure realism" in content
    assert "trader validation or trader approval" in content
    assert "future profitability or out-of-sample robustness" in content
    assert "bounded backtest evidence only" in content
    assert "non-live by design" in content
    assert "trader_validation_not_started" in content


def test_runtime_doc_defines_realism_boundary_runtime_disclosure() -> None:
    content = RUNTIME_DOC.read_text(encoding="utf-8")

    assert "# Backtest Realism Boundary - Runtime Disclosure" in content
    assert "NON-LIVE BOUNDED EVIDENCE ONLY" in content
    assert "## Runtime Realism Disclosure Surface" in content
    assert "`boundary_version`" in content
    assert "`modeled_assumptions`" in content
    assert "`unmodeled_assumptions`" in content
    assert "`evidence_boundary`" in content
    assert "`supported_interpretation`" in content
    assert "`unsupported_claims`" in content
    assert "`qualification_constraint`" in content
    assert "`decision_use_constraint`" in content

    assert "## Deterministic Replay Runtime Behavior" in content
    assert "byte-stable" in content

    assert "## Bounded Cost-Sensitivity Runtime Behavior" in content
    assert "cost_free_reference.total_transaction_cost == 0" in content
    assert (
        "bounded_cost_stress.total_transaction_cost >= configured_baseline.total_transaction_cost"
        in content
    )


def test_runtime_doc_preserves_explicit_non_live_and_non_trader_validation_boundary() -> None:
    content = RUNTIME_DOC.read_text(encoding="utf-8")

    assert "## Non-Live Boundary" in content
    assert "No live orders are placed." in content
    assert "No broker APIs are called." in content
    assert "No real capital is at risk." in content
    assert "does not imply live-trading readiness" in content
    assert "does not constitute trader validation" in content
    assert "trader_validation_not_started" in content
    # canonical authority deferral
    assert "docs/governance/backtest-realism-boundary-contract.md" in content

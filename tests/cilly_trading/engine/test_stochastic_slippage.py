"""Tests for StochasticSlippageModel (Issue #1094)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from cilly_trading.engine.backtest_execution_contract import (
    BacktestExecutionAssumptions,
    build_backtest_realism_boundary,
)
from cilly_trading.engine.slippage import (
    STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS,
    STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS,
    STOCHASTIC_SLIPPAGE_STRESS_STD_BPS,
    StochasticSlippageModel,
    build_stochastic_stress_preset,
)


# ── Construction and validation ──────────────────────────────────────────────


def test_default_construction_succeeds() -> None:
    model = StochasticSlippageModel()
    assert model.distribution == "normal"
    assert model.mean_bps == 10.0
    assert model.std_bps == 5.0
    assert model.max_bps == 50.0
    assert model.seed is None


def test_invalid_distribution_raises() -> None:
    with pytest.raises(ValueError, match="distribution"):
        StochasticSlippageModel(distribution="triangular")  # type: ignore[arg-type]


def test_negative_mean_bps_raises() -> None:
    with pytest.raises(ValueError, match="mean_bps"):
        StochasticSlippageModel(mean_bps=-1.0)


def test_negative_std_bps_raises() -> None:
    with pytest.raises(ValueError, match="std_bps"):
        StochasticSlippageModel(std_bps=-0.5)


def test_negative_max_bps_raises() -> None:
    with pytest.raises(ValueError, match="max_bps"):
        StochasticSlippageModel(max_bps=-10.0)


def test_invalid_seed_raises() -> None:
    with pytest.raises(ValueError, match="seed"):
        StochasticSlippageModel(seed=-1)


# ── Bounds: samples always in [0, max_bps] ───────────────────────────────────


def _assert_all_within_bounds(model: StochasticSlippageModel, n: int = 500) -> None:
    for _ in range(n):
        sample = model.sample_slippage_bps()
        assert 0.0 <= sample <= model.max_bps, f"Sample {sample} outside [0, {model.max_bps}]"


def test_normal_distribution_samples_within_bounds() -> None:
    model = StochasticSlippageModel(
        distribution="normal", mean_bps=20.0, std_bps=30.0, max_bps=60.0, seed=42
    )
    _assert_all_within_bounds(model)


def test_uniform_distribution_samples_within_bounds() -> None:
    model = StochasticSlippageModel(
        distribution="uniform", mean_bps=25.0, std_bps=20.0, max_bps=80.0, seed=42
    )
    _assert_all_within_bounds(model)


def test_lognormal_distribution_samples_within_bounds() -> None:
    model = StochasticSlippageModel(
        distribution="lognormal", mean_bps=15.0, std_bps=10.0, max_bps=50.0, seed=42
    )
    _assert_all_within_bounds(model)


# ── Hard cap at max_bps ───────────────────────────────────────────────────────


def test_max_bps_hard_cap_is_enforced_at_zero() -> None:
    # max_bps=0 forces every sample to 0.
    model = StochasticSlippageModel(
        distribution="normal", mean_bps=100.0, std_bps=50.0, max_bps=0.0, seed=0
    )
    for _ in range(50):
        assert model.sample_slippage_bps() == 0.0


def test_max_bps_hard_cap_never_exceeded_with_large_distribution() -> None:
    model = StochasticSlippageModel(
        distribution="normal", mean_bps=200.0, std_bps=200.0, max_bps=10.0, seed=1
    )
    _assert_all_within_bounds(model, n=1000)


# ── Seeded reproducibility ────────────────────────────────────────────────────


def test_seeded_model_produces_reproducible_sequence() -> None:
    model_a = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=5.0, seed=7)
    model_b = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=5.0, seed=7)

    samples_a = [model_a.sample_slippage_bps() for _ in range(20)]
    samples_b = [model_b.sample_slippage_bps() for _ in range(20)]

    assert samples_a == samples_b


def test_different_seeds_produce_different_sequences() -> None:
    model_a = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=5.0, seed=1)
    model_b = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=5.0, seed=2)

    samples_a = [model_a.sample_slippage_bps() for _ in range(20)]
    samples_b = [model_b.sample_slippage_bps() for _ in range(20)]

    assert samples_a != samples_b


# ── Zero std collapses to mean ────────────────────────────────────────────────


def test_zero_std_normal_returns_mean_exactly() -> None:
    model = StochasticSlippageModel(distribution="normal", mean_bps=15.0, std_bps=0.0, seed=0)
    for _ in range(10):
        assert model.sample_slippage_bps() == 15.0


def test_zero_std_uniform_returns_mean_exactly() -> None:
    model = StochasticSlippageModel(distribution="uniform", mean_bps=12.0, std_bps=0.0, seed=0)
    for _ in range(10):
        assert model.sample_slippage_bps() == 12.0


def test_zero_mean_lognormal_returns_zero() -> None:
    model = StochasticSlippageModel(distribution="lognormal", mean_bps=0.0, std_bps=5.0, seed=0)
    for _ in range(10):
        assert model.sample_slippage_bps() == 0.0


# ── Stress preset ─────────────────────────────────────────────────────────────


def test_stress_preset_uses_canonical_constants() -> None:
    preset = build_stochastic_stress_preset()
    assert preset.mean_bps == float(STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS)
    assert preset.std_bps == float(STOCHASTIC_SLIPPAGE_STRESS_STD_BPS)
    assert preset.max_bps == float(STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS)
    assert preset.distribution == "normal"


def test_stress_preset_constant_values() -> None:
    assert STOCHASTIC_SLIPPAGE_STRESS_MEAN_BPS == 50
    assert STOCHASTIC_SLIPPAGE_STRESS_STD_BPS == 30
    assert STOCHASTIC_SLIPPAGE_STRESS_MAX_BPS == 150


def test_stress_preset_seeded_is_reproducible() -> None:
    preset_a = build_stochastic_stress_preset(seed=99)
    preset_b = build_stochastic_stress_preset(seed=99)
    assert [preset_a.sample_slippage_bps() for _ in range(10)] == [
        preset_b.sample_slippage_bps() for _ in range(10)
    ]


# ── to_payload ────────────────────────────────────────────────────────────────


def test_to_payload_contains_all_fields() -> None:
    model = StochasticSlippageModel(
        distribution="lognormal", mean_bps=20.0, std_bps=8.0, max_bps=100.0, seed=5
    )
    payload = model.to_payload()
    assert payload["distribution"] == "lognormal"
    assert payload["mean_bps"] == 20.0
    assert payload["std_bps"] == 8.0
    assert payload["max_bps"] == 100.0
    assert payload["seed"] == 5


# ── BacktestExecutionAssumptions integration ──────────────────────────────────


def test_assumptions_default_has_no_stochastic_model() -> None:
    assumptions = BacktestExecutionAssumptions()
    assert assumptions.stochastic_slippage_model is None


def test_assumptions_accepts_stochastic_model() -> None:
    model = StochasticSlippageModel(distribution="normal", mean_bps=10.0, std_bps=5.0, seed=1)
    assumptions = BacktestExecutionAssumptions(stochastic_slippage_model=model)
    assert assumptions.stochastic_slippage_model is model


def test_assumptions_to_execution_config_propagates_stochastic_model() -> None:
    model = StochasticSlippageModel(distribution="uniform", mean_bps=15.0, std_bps=5.0, seed=2)
    assumptions = BacktestExecutionAssumptions(stochastic_slippage_model=model)
    config = assumptions.to_execution_config()
    assert config.stochastic_slippage_model is model


def test_assumptions_to_execution_config_none_when_not_set() -> None:
    assumptions = BacktestExecutionAssumptions(slippage_bps=5)
    config = assumptions.to_execution_config()
    assert config.stochastic_slippage_model is None


def test_assumptions_to_payload_includes_stochastic_model_when_set() -> None:
    model = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=10.0, seed=3)
    assumptions = BacktestExecutionAssumptions(stochastic_slippage_model=model)
    payload = assumptions.to_payload()
    assert "stochastic_slippage_model" in payload
    assert payload["stochastic_slippage_model"]["distribution"] == "normal"


def test_assumptions_to_payload_excludes_stochastic_key_when_not_set() -> None:
    assumptions = BacktestExecutionAssumptions(slippage_bps=5)
    payload = assumptions.to_payload()
    assert "stochastic_slippage_model" not in payload


def test_assumptions_invalid_stochastic_model_type_raises() -> None:
    with pytest.raises((ValueError, TypeError)):
        BacktestExecutionAssumptions(stochastic_slippage_model="not_a_model")  # type: ignore[arg-type]


# ── Realism boundary reflects stochastic model ───────────────────────────────


def test_realism_boundary_slippage_model_label_is_fixed_by_default() -> None:
    assumptions = BacktestExecutionAssumptions(slippage_bps=5)
    boundary = build_backtest_realism_boundary(execution_assumptions=assumptions)
    slippage = boundary["modeled_assumptions"]["slippage"]
    assert slippage["slippage_model"] == "fixed_basis_points_by_side"
    assert "stochastic_slippage_model" not in slippage


def test_realism_boundary_slippage_model_label_is_stochastic_when_set() -> None:
    model = StochasticSlippageModel(distribution="normal", mean_bps=20.0, std_bps=10.0, seed=0)
    assumptions = BacktestExecutionAssumptions(stochastic_slippage_model=model)
    boundary = build_backtest_realism_boundary(execution_assumptions=assumptions)
    slippage = boundary["modeled_assumptions"]["slippage"]
    assert slippage["slippage_model"] == "stochastic"
    assert slippage["stochastic_slippage_model"]["distribution"] == "normal"
    assert slippage["stochastic_slippage_model"]["mean_bps"] == 20.0

from __future__ import annotations

import math
from collections.abc import Iterable

import pandas as pd
import pytest

import cilly_trading.strategies.rsi2 as rsi2_module
from cilly_trading.strategies.rsi2 import Rsi2Strategy


def _frame(*, highs: Iterable[float], closes: Iterable[float]) -> pd.DataFrame:
    return pd.DataFrame({"high": list(highs), "close": list(closes)})


def _patch_rsi(monkeypatch: pytest.MonkeyPatch, values: list[float]) -> None:
    def fake_rsi(
        df: pd.DataFrame,
        period: int = 14,
        price_column: str = "close",
    ) -> pd.Series:
        return pd.Series(values[: len(df)], index=df.index, dtype=float)

    monkeypatch.setattr(rsi2_module, "rsi", fake_rsi)


def test_eligible_prior_setup_allows_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 5.0, 30.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert [signal["stage"] for signal in signals] == ["entry_confirmed"]


def test_no_prior_setup_prevents_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 35.0, 40.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert signals == []


def test_same_bar_setup_and_confirmation_are_impossible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 5.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0], closes=[100.0, 95.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert [signal["stage"] for signal in signals] == ["setup"]


def test_non_finite_current_rsi_prevents_setup_and_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, math.nan])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0], closes=[100.0, 95.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert signals == []


def test_non_finite_warmup_bar_cannot_manufacture_prior_setup(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [math.nan, 60.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[90.0, 95.0], closes=[80.0, 91.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert signals == []


@pytest.mark.parametrize(
    ("symbol", "preset", "rsi_values", "highs", "closes"),
    [
        ("AAPL", "default", [math.nan, 95.03055574824101, 61.66177499488172], [139.67, 144.30, 144.30], [136.87, 143.16, 142.06]),
        ("NVDA", "conservative", [math.nan, 80.974403519317, 58.12969835244649], [13.245, 13.961, 13.7545], [12.6145, 13.6215, 13.484749794]),
        ("GS", "aggressive", [math.nan, 77.0, 35.0], [310.0, 320.0, 315.0], [300.0, 318.0, 311.0]),
    ],
)
def test_previously_identified_warmup_defect_patterns_do_not_confirm(
    monkeypatch: pytest.MonkeyPatch,
    symbol: str,
    preset: str,
    rsi_values: list[float],
    highs: list[float],
    closes: list[float],
) -> None:
    _patch_rsi(monkeypatch, rsi_values)
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=highs, closes=closes),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0},
    )

    assert signals == [], f"{symbol}/{preset} must not confirm without setup"


def test_setup_below_min_score_cannot_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 9.0, 30.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0]),
        {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 20.0},
    )

    assert signals == []


def test_setup_from_another_symbol_cannot_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    strategy = Rsi2Strategy()
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    _patch_rsi(monkeypatch, [50.0, 5.0])
    assert strategy.generate_signals(
        _frame(highs=[100.0, 90.0], closes=[100.0, 80.0]),
        cfg,
    )[0]["stage"] == "setup"

    _patch_rsi(monkeypatch, [50.0, 35.0])
    assert strategy.generate_signals(
        _frame(highs=[100.0, 105.0], closes=[100.0, 106.0]),
        cfg,
    ) == []


def test_setup_from_another_preset_cannot_confirm(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 15.0, 30.0])
    frame = _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0])
    aggressive_cfg = {
        "rsi_period": 2,
        "oversold_threshold": 20.0,
        "min_score": 0.0,
    }
    conservative_cfg = {
        "rsi_period": 2,
        "oversold_threshold": 10.0,
        "min_score": 0.0,
    }

    assert Rsi2Strategy().generate_signals(frame.iloc[:2], aggressive_cfg)[0]["stage"] == "setup"
    assert Rsi2Strategy().generate_signals(frame, conservative_cfg) == []


def test_repeated_confirmation_remains_allowed_while_setup_is_eligible(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    frame = _frame(
        highs=[100.0, 90.0, 92.0, 93.0],
        closes=[100.0, 80.0, 91.0, 92.0],
    )

    _patch_rsi(monkeypatch, [50.0, 5.0, 30.0, 40.0])
    first = Rsi2Strategy().generate_signals(frame.iloc[:3], cfg)
    second = Rsi2Strategy().generate_signals(frame, cfg)

    assert [signal["stage"] for signal in first] == ["entry_confirmed"]
    assert [signal["stage"] for signal in second] == ["entry_confirmed"]


def test_identical_historical_input_produces_deterministic_output(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cfg = {"rsi_period": 2, "oversold_threshold": 10.0, "min_score": 0.0}
    frame = _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0])

    _patch_rsi(monkeypatch, [50.0, 5.0, 30.0])
    first = Rsi2Strategy().generate_signals(frame, cfg)
    second = Rsi2Strategy().generate_signals(frame, cfg)

    assert first == second


def test_exit_behavior_remains_separate_from_entry_confirmation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _patch_rsi(monkeypatch, [50.0, 5.0, 80.0])
    signals = Rsi2Strategy().generate_signals(
        _frame(highs=[100.0, 90.0, 92.0], closes=[100.0, 80.0, 91.0]),
        {
            "rsi_period": 2,
            "oversold_threshold": 10.0,
            "overbought_threshold": 70.0,
            "min_score": 0.0,
        },
    )

    assert [signal["stage"] for signal in signals] == ["exit"]

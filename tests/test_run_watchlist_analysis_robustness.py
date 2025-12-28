from __future__ import annotations

from dataclasses import dataclass
import logging
from typing import Any, Dict, List

import pandas as pd
import pytest

from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis


def _df_minimal() -> pd.DataFrame:
    # minimal OHLCV schema expected by strategies
    return pd.DataFrame(
        [
            {
                "timestamp": "2025-01-01T00:00:00Z",
                "open": 1.0,
                "high": 1.0,
                "low": 1.0,
                "close": 1.0,
                "volume": 100.0,
            }
        ]
    )


@dataclass
class DummyRepo:
    should_raise: bool = False
    saved: List[dict] | None = None

    def save_signals(self, signals: List[dict]) -> None:
        if self.should_raise:
            raise RuntimeError("repo save failed")
        self.saved = list(signals)


class StrategyReturnsEmpty:
    name = "RET_EMPTY"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        return []


class StrategyRaises:
    name = "RAISER"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        raise RuntimeError("strategy boom")


def test_load_ohlcv_raises_symbol_skipped(monkeypatch: pytest.MonkeyPatch) -> None:
    # Mock path must be cilly_trading.engine.core.load_ohlcv (imported into core.py)
    def _raise(*args: Any, **kwargs: Any) -> pd.DataFrame:
        raise RuntimeError("data load failed")

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _raise)

    repo = DummyRepo()
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyReturnsEmpty()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    assert result == []
    assert repo.saved is None


def test_strategy_raises_engine_continues(monkeypatch: pytest.MonkeyPatch) -> None:
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo()
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyRaises(), StrategyReturnsEmpty()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    # no signals expected
    assert result == []
    assert repo.saved is None


def test_repo_save_signals_raises_run_completes(monkeypatch: pytest.MonkeyPatch) -> None:
    # Acceptance criterion: repo.save_signals raises -> run completes (no crash)
    # This test will currently FAIL if run_watchlist_analysis doesn't catch repo exceptions.
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    class StrategyReturnsOne:
        name = "ONE"

        def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
            return [{"score": 50.0, "stage": "setup", "confirmation_rule": "n/a"}]

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo(should_raise=True)
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyReturnsOne()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    assert len(result) == 1


def test_strategy_returns_none_no_crash(monkeypatch: pytest.MonkeyPatch) -> None:
    # Acceptance criterion: strategy returns None -> no crash
    # This test will currently FAIL if the engine assumes signals is a list.
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    class StrategyReturnsNone:
        name = "NONE"

        def generate_signals(self, df: Any, config: Dict[str, Any]) -> Any:
            return None

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo()
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyReturnsNone()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    assert result == []


def test_unknown_strategy_config_keys_logged(
    monkeypatch: pytest.MonkeyPatch,
    caplog: pytest.LogCaptureFixture,
) -> None:
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    class StrategyRecordsConfig:
        name = "RSI2"

        def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
            return []

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo()
    caplog.set_level(logging.WARNING, logger="cilly_trading.engine.core")
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[StrategyRecordsConfig()],
        engine_config=EngineConfig(),
        strategy_configs={"RSI2": {"unknown_key": 123}},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    assert "Unknown config keys:" in caplog.text
    assert "strategy=RSI2" in caplog.text
    assert "unknown_key" in caplog.text


def test_missing_strategy_config_defaults_to_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    class StrategyRecordsConfig:
        name = "RSI2"

        def __init__(self) -> None:
            self.last_config: Dict[str, Any] | None = None

        def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
            self.last_config = config
            return []

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo()
    strategy = StrategyRecordsConfig()
    result = run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[strategy],
        engine_config=EngineConfig(),
        strategy_configs={"RSI2": None},
        signal_repo=repo,
    )

    assert isinstance(result, list)
    assert strategy.last_config == {}

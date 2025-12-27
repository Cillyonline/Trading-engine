from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from api import main
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis


def _df_minimal() -> pd.DataFrame:
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


class DummyRepo:
    def __init__(self) -> None:
        self.saved: List[dict] | None = None

    def save_signals(self, signals: List[dict]) -> None:
        self.saved = list(signals)


class StrategyReturnsOne:
    name = "ONE"

    def generate_signals(self, df: Any, config: Dict[str, Any]) -> List[dict]:
        return [{"score": 50.0, "stage": "setup"}]


def test_screener_response_schema_and_ordering(monkeypatch) -> None:
    signals = [
        {
            "symbol": "BBB",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.5,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAA",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAC",
            "stage": "setup",
            "score": 50,
            "signal_strength": 0.7,
            "strategy": "TURTLE",
        },
        {
            "symbol": "CCC",
            "stage": "setup",
            "score": None,
            "signal_strength": 0.9,
            "strategy": "RSI2",
        },
        {
            "symbol": "DDD",
            "stage": "setup",
            "score": None,
            "signal_strength": None,
            "strategy": "RSI2",
        },
        {
            "symbol": "AAA",
            "stage": "setup",
            "score": 40,
            "signal_strength": 0.4,
            "strategy": "TURTLE",
        },
    ]

    def fake_run_watchlist_analysis(*args, **kwargs):
        return signals

    monkeypatch.setattr(main, "run_watchlist_analysis", fake_run_watchlist_analysis)

    request = main.ScreenerRequest(
        symbols=["AAA", "AAC", "BBB", "CCC", "DDD"],
        market_type="stock",
        lookback_days=200,
        min_score=0,
    )
    response = main.basic_screener(request)

    payload = response.model_dump()
    assert payload["market_type"] == "stock"

    items = payload["symbols"]
    assert [item["symbol"] for item in items] == ["AAA", "AAC", "BBB", "CCC", "DDD"]

    for item in items:
        assert set(["symbol", "score", "signal_strength", "setups"]).issubset(item.keys())

    top_item = items[0]
    assert top_item["symbol"] == "AAA"
    assert top_item["score"] == 50
    assert top_item["signal_strength"] == 0.7


def test_run_watchlist_analysis_deterministic_order(monkeypatch) -> None:
    def _ok(*args: Any, **kwargs: Any) -> pd.DataFrame:
        return _df_minimal()

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _ok)

    repo = DummyRepo()
    result = run_watchlist_analysis(
        symbols=["BBB", "AAA", "CCC"],
        strategies=[StrategyReturnsOne()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert [signal["symbol"] for signal in result] == ["AAA", "BBB", "CCC"]


def test_run_watchlist_analysis_symbol_failure_isolated(monkeypatch) -> None:
    def _loader(*args: Any, **kwargs: Any) -> pd.DataFrame:
        symbol = kwargs.get("symbol")
        if symbol == "BAD":
            raise RuntimeError("boom")
        return _df_minimal()

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _loader)

    repo = DummyRepo()
    result = run_watchlist_analysis(
        symbols=["BAD", "AAA", "BBB"],
        strategies=[StrategyReturnsOne()],
        engine_config=EngineConfig(),
        strategy_configs={},
        signal_repo=repo,
    )

    assert [signal["symbol"] for signal in result] == ["AAA", "BBB"]

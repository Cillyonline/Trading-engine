from __future__ import annotations

import importlib.util
import sys
from dataclasses import fields
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path


def _load_provider_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "src" / "cilly_trading" / "engine" / "data" / "market_data_provider.py"
    spec = importlib.util.spec_from_file_location("market_data_provider_contract", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market_data_provider module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


module = _load_provider_module()
Candle = module.Candle
MarketDataProvider = module.MarketDataProvider
MarketDataRequest = module.MarketDataRequest


class InMemoryDeterministicProvider:
    def __init__(self) -> None:
        self._candles = (
            Candle(
                timestamp=datetime(2025, 1, 1, tzinfo=timezone.utc),
                symbol="BTC/USDT",
                timeframe="1H",
                open=Decimal("100.0"),
                high=Decimal("101.0"),
                low=Decimal("99.5"),
                close=Decimal("100.5"),
                volume=Decimal("250.0"),
            ),
            Candle(
                timestamp=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
                symbol="BTC/USDT",
                timeframe="1H",
                open=Decimal("100.5"),
                high=Decimal("102.0"),
                low=Decimal("100.0"),
                close=Decimal("101.0"),
                volume=Decimal("300.0"),
            ),
        )

    def iter_candles(self, request: MarketDataRequest):
        candles = tuple(
            candle
            for candle in self._candles
            if candle.symbol == request.symbol and candle.timeframe == request.timeframe
        )
        if request.limit is not None:
            return iter(candles[: request.limit])
        return iter(candles)


def test_market_data_provider_runtime_contract() -> None:
    provider = InMemoryDeterministicProvider()
    assert isinstance(provider, MarketDataProvider)


def test_candle_exposes_canonical_fields() -> None:
    field_names = tuple(field.name for field in fields(Candle))
    assert field_names == (
        "timestamp",
        "symbol",
        "timeframe",
        "open",
        "high",
        "low",
        "close",
        "volume",
    )


def test_iter_candles_is_deterministic_for_identical_request() -> None:
    provider = InMemoryDeterministicProvider()
    request = MarketDataRequest(symbol="BTC/USDT", timeframe="1H")

    first = tuple(provider.iter_candles(request))
    second = tuple(provider.iter_candles(request))

    assert first == second
    assert len(first) == 2


def test_iter_candles_respects_limit_deterministically() -> None:
    provider = InMemoryDeterministicProvider()
    request = MarketDataRequest(symbol="BTC/USDT", timeframe="1H", limit=1)

    first = tuple(provider.iter_candles(request))
    second = tuple(provider.iter_candles(request))

    assert first == second
    assert len(first) == 1

from __future__ import annotations

import importlib.util
import json
import logging
import sys
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.telemetry.emitter import (
    InMemoryTelemetrySink,
    configure_telemetry_emitter,
    emit_telemetry_event,
    reset_telemetry_emission_for_tests,
)
from cilly_trading.engine.telemetry.schema import build_telemetry_event


def _load_provider_module():
    root = Path(__file__).resolve().parents[2]
    module_path = root / "src" / "cilly_trading" / "engine" / "data" / "market_data_provider.py"
    spec = importlib.util.spec_from_file_location(
        "market_data_provider_failover_telemetry",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market_data_provider module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture(autouse=True)
def _reset_telemetry() -> None:
    reset_telemetry_emission_for_tests()


module = _load_provider_module()
Candle = module.Candle
MarketDataProviderRegistry = module.MarketDataProviderRegistry
MarketDataRequest = module.MarketDataRequest
ProviderFailoverExhaustedError = module.ProviderFailoverExhaustedError


class _AlwaysFailProvider:
    def __init__(self, message: str) -> None:
        self._message = message

    def iter_candles(self, request: MarketDataRequest):
        raise RuntimeError(self._message)


class _SingleCandleProvider:
    def __init__(self, candle: Candle) -> None:
        self._candle = candle

    def iter_candles(self, request: MarketDataRequest):
        if (
            request.symbol == self._candle.symbol
            and request.timeframe == self._candle.timeframe
        ):
            return iter((self._candle,))
        return iter(())


def test_failover_telemetry_emits_schema_valid_events() -> None:
    sink = InMemoryTelemetrySink()
    configure_telemetry_emitter(sink.write)

    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=_AlwaysFailProvider("primary down"), priority=1)
    registry.register(
        name="fallback",
        provider=_SingleCandleProvider(
            Candle(
                timestamp=datetime(2025, 1, 2, tzinfo=timezone.utc),
                symbol="BTC/USDT",
                timeframe="1H",
                open=Decimal("200"),
                high=Decimal("201"),
                low=Decimal("199"),
                close=Decimal("200.5"),
                volume=Decimal("10"),
            )
        ),
        priority=2,
    )

    tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="BTC/USDT", timeframe="1H", limit=5)
        )
    )

    emitted = [json.loads(line) for line in sink.lines]

    assert [event["event"] for event in emitted] == [
        "provider_failover.attempt_failed",
        "provider_failover.recovered",
    ]
    assert emitted[0] == build_telemetry_event(
        event="provider_failover.attempt_failed",
        event_index=0,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload={
            "provider_name": "primary",
            "symbol": "BTC/USDT",
            "timeframe": "1H",
            "limit": 5,
            "reason": "RuntimeError: primary down",
        },
    ).to_dict()
    assert emitted[1] == build_telemetry_event(
        event="provider_failover.recovered",
        event_index=1,
        timestamp_utc="1970-01-01T00:00:01Z",
        payload={
            "provider_name": "fallback",
            "symbol": "BTC/USDT",
            "timeframe": "1H",
            "limit": 5,
            "failed_provider_names": ["primary"],
        },
    ).to_dict()


def test_failover_telemetry_emits_provider_exhaustion_identifiers() -> None:
    sink = InMemoryTelemetrySink()
    configure_telemetry_emitter(sink.write)

    registry = MarketDataProviderRegistry()
    registry.register(name="alpha", provider=_AlwaysFailProvider("a-down"), priority=1)
    registry.register(name="beta", provider=_AlwaysFailProvider("b-down"), priority=2)

    with pytest.raises(ProviderFailoverExhaustedError):
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="ETH/USDT", timeframe="15M")
            )
        )

    emitted = [json.loads(line) for line in sink.lines]

    assert [event["event"] for event in emitted] == [
        "provider_failover.attempt_failed",
        "provider_failover.attempt_failed",
        "provider_failover.exhausted",
    ]
    assert emitted[-1]["payload"]["failed_provider_names"] == ["alpha", "beta"]
    assert emitted[-1]["payload"]["symbol"] == "ETH/USDT"
    assert emitted[-1]["payload"]["timeframe"] == "15M"


def test_failover_telemetry_emission_is_deterministic_across_identical_runs() -> None:
    def _emit_sequence(sink: InMemoryTelemetrySink) -> tuple[str, ...]:
        configure_telemetry_emitter(sink.write)

        registry = MarketDataProviderRegistry()
        registry.register(name="primary", provider=_AlwaysFailProvider("repeatable"), priority=1)
        registry.register(
            name="fallback",
            provider=_SingleCandleProvider(
                Candle(
                    timestamp=datetime(2025, 1, 3, tzinfo=timezone.utc),
                    symbol="SOL/USDT",
                    timeframe="1H",
                    open=Decimal("10"),
                    high=Decimal("11"),
                    low=Decimal("9"),
                    close=Decimal("10.5"),
                    volume=Decimal("12"),
                )
            ),
            priority=2,
        )

        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="SOL/USDT", timeframe="1H")
            )
        )
        return sink.lines

    first_sink = InMemoryTelemetrySink()
    second_sink = InMemoryTelemetrySink()

    assert _emit_sequence(first_sink) == _emit_sequence(second_sink)


def test_emitter_without_sink_does_not_log_runtime_output(
    caplog: pytest.LogCaptureFixture,
) -> None:
    caplog.set_level(logging.INFO, logger="cilly_trading.engine.telemetry.emitter")

    serialized = emit_telemetry_event(
        "provider_failover.attempt_failed",
        event_index=0,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload={
            "provider_name": "alpha",
            "symbol": "XRP/USDT",
            "timeframe": "1H",
            "limit": None,
            "reason": "RuntimeError: a-down",
        },
    )

    assert serialized == (
        '{"component":"engine","event":"provider_failover.attempt_failed","event_index":0,'
        '"payload":{"limit":null,"provider_name":"alpha","reason":"RuntimeError: a-down",'
        '"symbol":"XRP/USDT","timeframe":"1H"},'
        '"schema_version":"cilly.engine.telemetry.v1","timestamp_utc":"1970-01-01T00:00:00Z"}'
    )
    assert [
        record.getMessage()
        for record in caplog.records
        if record.name == "cilly_trading.engine.telemetry.emitter"
    ] == []


def test_failover_telemetry_does_not_modify_failover_behavior_when_sink_fails() -> None:
    def _raising_sink(line: str) -> None:
        raise RuntimeError("telemetry sink unavailable")

    configure_telemetry_emitter(_raising_sink)

    expected = Candle(
        timestamp=datetime(2025, 1, 4, tzinfo=timezone.utc),
        symbol="ADA/USDT",
        timeframe="1H",
        open=Decimal("20"),
        high=Decimal("21"),
        low=Decimal("19"),
        close=Decimal("20.5"),
        volume=Decimal("15"),
    )
    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=_AlwaysFailProvider("primary error"), priority=1)
    registry.register(
        name="fallback",
        provider=_SingleCandleProvider(expected),
        priority=2,
    )

    candles = tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="ADA/USDT", timeframe="1H")
        )
    )

    assert candles == (expected,)

from __future__ import annotations

import importlib.util
import json
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
detect_missing_candle_intervals = module.detect_missing_candle_intervals
LocalSnapshotProvider = module.LocalSnapshotProvider
MarketDataProvider = module.MarketDataProvider
MarketDataProviderRegistry = module.MarketDataProviderRegistry
MarketDataRequest = module.MarketDataRequest
MissingCandleInterval = module.MissingCandleInterval
ProviderFailoverExhaustedError = module.ProviderFailoverExhaustedError
normalize_candle = module.normalize_candle
normalize_candles = module.normalize_candles
RegisteredMarketDataProvider = module.RegisteredMarketDataProvider
serialize_candles_deterministically = module.serialize_candles_deterministically
timeframe_to_timedelta = module.timeframe_to_timedelta


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


class AlwaysFailProvider:
    def __init__(self, message: str = "provider failure") -> None:
        self._message = message

    def iter_candles(self, request: MarketDataRequest):
        raise RuntimeError(self._message)


class SingleCandleProvider:
    def __init__(self, candle: Candle) -> None:
        self._candle = candle

    def iter_candles(self, request: MarketDataRequest):
        if (
            request.symbol == self._candle.symbol
            and request.timeframe == self._candle.timeframe
        ):
            return iter((self._candle,))
        return iter(())


class IterationFailProvider:
    def __init__(self, message: str = "iteration failure") -> None:
        self._message = message

    def iter_candles(self, request: MarketDataRequest):
        def _generator():
            raise RuntimeError(self._message)
            yield  # pragma: no cover

        return _generator()


class PartialThenFailProvider:
    def __init__(self, candles: tuple[Candle, ...], message: str = "partial failure") -> None:
        self._candles = candles
        self._message = message

    def iter_candles(self, request: MarketDataRequest):
        def _generator():
            for candle in self._candles:
                if (
                    candle.symbol == request.symbol
                    and candle.timeframe == request.timeframe
                ):
                    yield candle
            raise RuntimeError(self._message)

        return _generator()


def test_market_data_provider_runtime_contract() -> None:
    provider = InMemoryDeterministicProvider()
    assert isinstance(provider, MarketDataProvider)


def test_provider_registry_registers_provider() -> None:
    registry = MarketDataProviderRegistry()
    provider = InMemoryDeterministicProvider()
    registry.register(name="snapshot", provider=provider, priority=10)

    assert registry.get_registered() == (
        RegisteredMarketDataProvider(name="snapshot", provider=provider, priority=10),
    )


def test_provider_selection_is_deterministic() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(name="zeta", provider=InMemoryDeterministicProvider(), priority=10)
    registry.register(name="alpha", provider=InMemoryDeterministicProvider(), priority=10)
    registry.register(name="beta", provider=InMemoryDeterministicProvider(), priority=5)

    selected = registry.select_provider()
    ordered_names = tuple(entry.name for entry in registry.get_registered())

    assert selected.name == "beta"
    assert ordered_names == ("beta", "alpha", "zeta")


def test_provider_registry_failover_uses_next_priority_provider() -> None:
    registry = MarketDataProviderRegistry()
    expected = Candle(
        timestamp=datetime(2025, 1, 2, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("200.0"),
        high=Decimal("201.0"),
        low=Decimal("199.0"),
        close=Decimal("200.5"),
        volume=Decimal("100.0"),
    )
    registry.register(name="primary", provider=AlwaysFailProvider(), priority=1)
    registry.register(
        name="fallback", provider=SingleCandleProvider(expected), priority=2
    )

    candles = tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
        )
    )

    assert candles == (expected,)


def test_provider_registry_failover_raises_when_all_providers_fail() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=AlwaysFailProvider("p1"), priority=1)
    registry.register(name="secondary", provider=AlwaysFailProvider("p2"), priority=2)

    try:
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
            )
        )
    except ProviderFailoverExhaustedError as exc:
        assert tuple(failure.provider_name for failure in exc.failures) == (
            "primary",
            "secondary",
        )
    else:
        raise AssertionError("Expected ProviderFailoverExhaustedError")


def test_provider_registry_failover_handles_iteration_time_failure() -> None:
    registry = MarketDataProviderRegistry()
    expected = Candle(
        timestamp=datetime(2025, 1, 3, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("300.0"),
        high=Decimal("301.0"),
        low=Decimal("299.0"),
        close=Decimal("300.5"),
        volume=Decimal("110.0"),
    )
    registry.register(name="primary", provider=IterationFailProvider("iter-p1"), priority=1)
    registry.register(
        name="fallback", provider=SingleCandleProvider(expected), priority=2
    )

    candles = tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
        )
    )

    assert candles == (expected,)


def test_provider_registry_failover_aggregates_iteration_time_failures() -> None:
    registry = MarketDataProviderRegistry()
    registry.register(
        name="primary", provider=IterationFailProvider("iter-p1"), priority=1
    )
    registry.register(
        name="secondary", provider=IterationFailProvider("iter-p2"), priority=2
    )

    try:
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
            )
        )
    except ProviderFailoverExhaustedError as exc:
        assert tuple(failure.provider_name for failure in exc.failures) == (
            "primary",
            "secondary",
        )
        assert tuple(failure.reason for failure in exc.failures) == (
            "RuntimeError: iter-p1",
            "RuntimeError: iter-p2",
        )
    else:
        raise AssertionError("Expected ProviderFailoverExhaustedError")


def test_provider_registry_failover_discards_partial_output_before_fallback() -> None:
    registry = MarketDataProviderRegistry()
    partial_candle = Candle(
        timestamp=datetime(2025, 1, 4, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("400.0"),
        high=Decimal("401.0"),
        low=Decimal("399.0"),
        close=Decimal("400.5"),
        volume=Decimal("120.0"),
    )
    fallback_candle = Candle(
        timestamp=datetime(2025, 1, 4, 1, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("401.0"),
        high=Decimal("402.0"),
        low=Decimal("400.0"),
        close=Decimal("401.5"),
        volume=Decimal("130.0"),
    )
    registry.register(
        name="primary",
        provider=PartialThenFailProvider((partial_candle,), "partial-p1"),
        priority=1,
    )
    registry.register(
        name="fallback", provider=SingleCandleProvider(fallback_candle), priority=2
    )

    candles = tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
        )
    )

    assert candles == (fallback_candle,)


def test_provider_registry_failover_raises_when_all_partial_providers_fail() -> None:
    registry = MarketDataProviderRegistry()
    partial_a = Candle(
        timestamp=datetime(2025, 1, 5, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("500.0"),
        high=Decimal("501.0"),
        low=Decimal("499.0"),
        close=Decimal("500.5"),
        volume=Decimal("140.0"),
    )
    partial_b = Candle(
        timestamp=datetime(2025, 1, 5, 1, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("501.0"),
        high=Decimal("502.0"),
        low=Decimal("500.0"),
        close=Decimal("501.5"),
        volume=Decimal("150.0"),
    )
    registry.register(
        name="primary",
        provider=PartialThenFailProvider((partial_a,), "partial-p1"),
        priority=1,
    )
    registry.register(
        name="secondary",
        provider=PartialThenFailProvider((partial_b,), "partial-p2"),
        priority=2,
    )

    try:
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="BTC/USDT", timeframe="1H")
            )
        )
    except ProviderFailoverExhaustedError as exc:
        assert tuple(failure.provider_name for failure in exc.failures) == (
            "primary",
            "secondary",
        )
        assert tuple(failure.reason for failure in exc.failures) == (
            "RuntimeError: partial-p1",
            "RuntimeError: partial-p2",
        )
    else:
        raise AssertionError("Expected ProviderFailoverExhaustedError")


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


def test_local_snapshot_provider_loads_snapshot_dataset(tmp_path: Path) -> None:
    dataset_path = tmp_path / "snapshots.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2025-01-01T01:00:00+00:00",
                    "symbol": "BTC/USDT",
                    "timeframe": "1H",
                    "open": "100.5",
                    "high": "102.0",
                    "low": "100.0",
                    "close": "101.0",
                    "volume": "300.0",
                },
                {
                    "timestamp": "2025-01-01T00:00:00+00:00",
                    "symbol": "BTC/USDT",
                    "timeframe": "1H",
                    "open": "100.0",
                    "high": "101.0",
                    "low": "99.5",
                    "close": "100.5",
                    "volume": "250.0",
                },
                {
                    "timestamp": "2025-01-01T00:00:00+00:00",
                    "symbol": "ETH/USDT",
                    "timeframe": "1H",
                    "open": "50.0",
                    "high": "51.0",
                    "low": "49.5",
                    "close": "50.5",
                    "volume": "100.0",
                },
            ]
        ),
        encoding="utf-8",
    )
    provider = LocalSnapshotProvider(dataset_path=dataset_path)
    assert isinstance(provider, MarketDataProvider)

    candles = tuple(provider.iter_candles(MarketDataRequest(symbol="BTC/USDT", timeframe="1H")))

    assert len(candles) == 2
    assert candles[0].timestamp == datetime(2025, 1, 1, 0, tzinfo=timezone.utc)
    assert candles[1].timestamp == datetime(2025, 1, 1, 1, tzinfo=timezone.utc)


def test_local_snapshot_provider_iteration_order_is_deterministic(tmp_path: Path) -> None:
    dataset_path = tmp_path / "snapshots.json"
    dataset_path.write_text(
        json.dumps(
            [
                {
                    "timestamp": "2025-01-01T02:00:00+00:00",
                    "symbol": "BTC/USDT",
                    "timeframe": "1H",
                    "open": "102.0",
                    "high": "103.0",
                    "low": "101.0",
                    "close": "102.5",
                    "volume": "320.0",
                },
                {
                    "timestamp": "2025-01-01T00:00:00+00:00",
                    "symbol": "BTC/USDT",
                    "timeframe": "1H",
                    "open": "100.0",
                    "high": "101.0",
                    "low": "99.5",
                    "close": "100.5",
                    "volume": "250.0",
                },
                {
                    "timestamp": "2025-01-01T01:00:00+00:00",
                    "symbol": "BTC/USDT",
                    "timeframe": "1H",
                    "open": "101.0",
                    "high": "102.0",
                    "low": "100.0",
                    "close": "101.5",
                    "volume": "290.0",
                },
            ]
        ),
        encoding="utf-8",
    )
    provider = LocalSnapshotProvider(dataset_path=dataset_path)
    request = MarketDataRequest(symbol="BTC/USDT", timeframe="1H")

    first = tuple(provider.iter_candles(request))
    second = tuple(provider.iter_candles(request))

    assert first == second
    assert [candle.timestamp for candle in first] == [
        datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 2, tzinfo=timezone.utc),
    ]


def test_normalize_candle_supports_common_provider_aliases() -> None:
    normalized = normalize_candle(
        {
            "t": "2025-01-01T00:00:00Z",
            "pair": "BTC/USDT",
            "interval": "1H",
            "o": "100.0",
            "h": "101.0",
            "l": "99.0",
            "c": "100.5",
            "v": "400.0",
        }
    )

    assert normalized == Candle(
        timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        symbol="BTC/USDT",
        timeframe="1H",
        open=Decimal("100.0"),
        high=Decimal("101.0"),
        low=Decimal("99.0"),
        close=Decimal("100.5"),
        volume=Decimal("400.0"),
    )


def test_normalize_candle_raises_for_incomplete_schema() -> None:
    payload = {
        "timestamp": "2025-01-01T00:00:00+00:00",
        "symbol": "BTC/USDT",
        "timeframe": "1H",
        "open": "100.0",
        "high": "101.0",
        "low": "99.0",
        "close": "100.5",
    }

    try:
        normalize_candle(payload)
    except ValueError as exc:
        assert "Invalid snapshot dataset" in str(exc)
    else:
        raise AssertionError("Expected ValueError for incomplete candle schema")


def test_normalize_candles_orders_deterministically() -> None:
    candles = normalize_candles(
        [
            {
                "timestamp": "2025-01-01T01:00:00+00:00",
                "symbol": "BTC/USDT",
                "timeframe": "1H",
                "open": "101.0",
                "high": "102.0",
                "low": "100.0",
                "close": "101.5",
                "volume": "290.0",
            },
            {
                "timestamp": "2025-01-01T00:00:00+00:00",
                "symbol": "BTC/USDT",
                "timeframe": "1H",
                "open": "100.0",
                "high": "101.0",
                "low": "99.5",
                "close": "100.5",
                "volume": "250.0",
            },
        ]
    )

    assert [candle.timestamp for candle in candles] == [
        datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
        datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
    ]


def test_serialize_candles_deterministically_is_stable() -> None:
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, 1, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("101.0"),
            high=Decimal("102.0"),
            low=Decimal("100.0"),
            close=Decimal("101.5"),
            volume=Decimal("290.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.5"),
            close=Decimal("100.5"),
            volume=Decimal("250.0"),
        ),
    )

    first = serialize_candles_deterministically(candles)
    second = serialize_candles_deterministically(reversed(candles))

    assert first == second
    assert first == (
        '[{"timestamp":"2025-01-01T00:00:00+00:00","symbol":"BTC/USDT","timeframe":"1H",'
        '"open":"100.0","high":"101.0","low":"99.5","close":"100.5","volume":"250.0"},'
        '{"timestamp":"2025-01-01T01:00:00+00:00","symbol":"BTC/USDT","timeframe":"1H",'
        '"open":"101.0","high":"102.0","low":"100.0","close":"101.5","volume":"290.0"}]'
    )


def test_timeframe_to_timedelta_parses_canonical_units() -> None:
    assert timeframe_to_timedelta("15M").total_seconds() == 900
    assert timeframe_to_timedelta("1H").total_seconds() == 3600
    assert timeframe_to_timedelta("2D").total_seconds() == 172800
    assert timeframe_to_timedelta("1W").total_seconds() == 604800


def test_detect_missing_candle_intervals_returns_empty_for_contiguous_data() -> None:
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.0"),
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
            volume=Decimal("260.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, 2, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("101.0"),
            high=Decimal("102.5"),
            low=Decimal("100.5"),
            close=Decimal("102.0"),
            volume=Decimal("270.0"),
        ),
    )

    assert detect_missing_candle_intervals(candles) == ()


def test_detect_missing_candle_intervals_reports_gaps() -> None:
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.0"),
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
            volume=Decimal("260.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, 4, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("103.0"),
            high=Decimal("104.0"),
            low=Decimal("102.0"),
            close=Decimal("103.5"),
            volume=Decimal("280.0"),
        ),
    )

    gaps = detect_missing_candle_intervals(candles)

    assert gaps == (
        MissingCandleInterval(
            start_timestamp=datetime(2025, 1, 1, 2, tzinfo=timezone.utc),
            end_timestamp=datetime(2025, 1, 1, 3, tzinfo=timezone.utc),
            missing_count=2,
        ),
    )


def test_detect_missing_candle_intervals_is_deterministic() -> None:
    candles = (
        Candle(
            timestamp=datetime(2025, 1, 1, 0, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("100.0"),
            high=Decimal("101.0"),
            low=Decimal("99.0"),
            close=Decimal("100.5"),
            volume=Decimal("250.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, 3, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("102.0"),
            high=Decimal("103.0"),
            low=Decimal("101.0"),
            close=Decimal("102.5"),
            volume=Decimal("280.0"),
        ),
        Candle(
            timestamp=datetime(2025, 1, 1, 6, tzinfo=timezone.utc),
            symbol="BTC/USDT",
            timeframe="1H",
            open=Decimal("105.0"),
            high=Decimal("106.0"),
            low=Decimal("104.0"),
            close=Decimal("105.5"),
            volume=Decimal("300.0"),
        ),
    )

    first = detect_missing_candle_intervals(candles)
    second = detect_missing_candle_intervals(candles)

    assert first == second

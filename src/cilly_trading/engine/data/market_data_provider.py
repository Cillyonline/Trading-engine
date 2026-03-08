"""Canonical market data provider contract for engine consumers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterator, Mapping, Protocol, runtime_checkable


@dataclass(frozen=True)
class Candle:
    """Canonical candle payload returned by market data providers."""

    timestamp: datetime
    symbol: str
    timeframe: str
    open: Decimal
    high: Decimal
    low: Decimal
    close: Decimal
    volume: Decimal


@dataclass(frozen=True)
class MarketDataRequest:
    """Canonical request shape accepted by market data providers."""

    symbol: str
    timeframe: str
    limit: int | None = None


@runtime_checkable
class MarketDataProvider(Protocol):
    """Provider protocol for deterministic market data iteration.

    Contract:
    - For a logically identical request, providers must return candles in a stable order.
    - Repeated iteration over a request must yield the same sequence of candle objects.
    - Each yielded candle must contain the canonical OHLCV fields.
    """

    def iter_candles(self, request: MarketDataRequest) -> Iterator[Candle]:
        """Yield canonical candles for a request in deterministic order."""

        ...


class LocalSnapshotProvider:
    """Market data provider backed by deterministic local snapshot datasets."""

    def __init__(self, dataset_path: str | Path) -> None:
        self._dataset_path = Path(dataset_path)
        self._candles = self._load_dataset(self._dataset_path)

    def iter_candles(self, request: MarketDataRequest) -> Iterator[Candle]:
        candles = tuple(
            candle
            for candle in self._candles
            if candle.symbol == request.symbol and candle.timeframe == request.timeframe
        )
        if request.limit is not None:
            if request.limit < 0:
                raise ValueError("request.limit must be >= 0")
            candles = candles[: request.limit]
        return iter(candles)

    @staticmethod
    def _load_dataset(dataset_path: Path) -> tuple[Candle, ...]:
        try:
            payload = json.loads(dataset_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError("Invalid snapshot dataset") from exc

        if not isinstance(payload, list):
            raise ValueError("Invalid snapshot dataset")

        normalized: list[tuple[int, Candle]] = []
        for index, item in enumerate(payload):
            if not isinstance(item, Mapping):
                raise ValueError("Invalid snapshot dataset")
            normalized.append((index, LocalSnapshotProvider._parse_candle(item)))

        ordered = sorted(
            normalized,
            key=lambda pair: (
                pair[1].timestamp,
                pair[1].symbol,
                pair[1].timeframe,
                pair[0],
            ),
        )
        return tuple(candle for _, candle in ordered)

    @staticmethod
    def _parse_candle(item: Mapping[str, Any]) -> Candle:
        try:
            timestamp = LocalSnapshotProvider._parse_timestamp(item["timestamp"])
            return Candle(
                timestamp=timestamp,
                symbol=str(item["symbol"]),
                timeframe=str(item["timeframe"]),
                open=Decimal(str(item["open"])),
                high=Decimal(str(item["high"])),
                low=Decimal(str(item["low"])),
                close=Decimal(str(item["close"])),
                volume=Decimal(str(item["volume"])),
            )
        except (KeyError, ValueError, TypeError) as exc:
            raise ValueError("Invalid snapshot dataset") from exc

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Invalid snapshot dataset")
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("Invalid snapshot dataset") from exc

"""Canonical market data provider contract for engine consumers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from pathlib import Path
from typing import Any, Iterable, Iterator, Mapping, Protocol, runtime_checkable


CANONICAL_CANDLE_FIELDS: tuple[str, ...] = (
    "timestamp",
    "symbol",
    "timeframe",
    "open",
    "high",
    "low",
    "close",
    "volume",
)

_DEFAULT_FIELD_ALIASES: Mapping[str, tuple[str, ...]] = {
    "timestamp": ("timestamp", "time", "t"),
    "symbol": ("symbol", "pair", "instrument", "s"),
    "timeframe": ("timeframe", "interval", "tf"),
    "open": ("open", "o"),
    "high": ("high", "h"),
    "low": ("low", "l"),
    "close": ("close", "c"),
    "volume": ("volume", "v"),
}


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

        return normalize_candles(payload)

    @staticmethod
    def _parse_candle(item: Mapping[str, Any]) -> Candle:
        return normalize_candle(item)

    @staticmethod
    def _parse_timestamp(value: Any) -> datetime:
        if not isinstance(value, str):
            raise ValueError("Invalid snapshot dataset")
        normalized = value.replace("Z", "+00:00") if value.endswith("Z") else value
        try:
            return datetime.fromisoformat(normalized)
        except ValueError as exc:
            raise ValueError("Invalid snapshot dataset") from exc


def normalize_candle(
    payload: Mapping[str, Any],
    *,
    field_aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> Candle:
    """Normalize a provider candle payload into the canonical Candle schema."""

    aliases = field_aliases or _DEFAULT_FIELD_ALIASES
    try:
        timestamp = LocalSnapshotProvider._parse_timestamp(
            _extract_field(payload, "timestamp", aliases)
        )
        return Candle(
            timestamp=timestamp,
            symbol=str(_extract_field(payload, "symbol", aliases)),
            timeframe=str(_extract_field(payload, "timeframe", aliases)),
            open=Decimal(str(_extract_field(payload, "open", aliases))),
            high=Decimal(str(_extract_field(payload, "high", aliases))),
            low=Decimal(str(_extract_field(payload, "low", aliases))),
            close=Decimal(str(_extract_field(payload, "close", aliases))),
            volume=Decimal(str(_extract_field(payload, "volume", aliases))),
        )
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError("Invalid snapshot dataset") from exc


def normalize_candles(
    payloads: Iterable[Mapping[str, Any]],
    *,
    field_aliases: Mapping[str, tuple[str, ...]] | None = None,
) -> tuple[Candle, ...]:
    """Normalize and deterministically order candle payloads."""

    normalized: list[tuple[int, Candle]] = []
    for index, payload in enumerate(payloads):
        if not isinstance(payload, Mapping):
            raise ValueError("Invalid snapshot dataset")
        normalized.append(
            (index, normalize_candle(payload, field_aliases=field_aliases))
        )

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


def serialize_candles_deterministically(candles: Iterable[Candle]) -> str:
    """Serialize candles as canonical JSON in deterministic key and row order."""

    ordered = sorted(
        candles,
        key=lambda candle: (
            candle.timestamp,
            candle.symbol,
            candle.timeframe,
            candle.open,
            candle.high,
            candle.low,
            candle.close,
            candle.volume,
        ),
    )
    canonical = [
        {
            "timestamp": candle.timestamp.isoformat(),
            "symbol": candle.symbol,
            "timeframe": candle.timeframe,
            "open": str(candle.open),
            "high": str(candle.high),
            "low": str(candle.low),
            "close": str(candle.close),
            "volume": str(candle.volume),
        }
        for candle in ordered
    ]
    return json.dumps(canonical, separators=(",", ":"), ensure_ascii=True)


def _extract_field(
    payload: Mapping[str, Any],
    canonical_name: str,
    aliases: Mapping[str, tuple[str, ...]],
) -> Any:
    candidates = aliases.get(canonical_name, (canonical_name,))
    for key in candidates:
        if key in payload:
            return payload[key]
    raise KeyError(canonical_name)

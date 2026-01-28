"""Deterministic local replay market data adapter."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal
from pathlib import Path
from typing import Iterable, Literal, Sequence

from cilly_trading.engine.marketdata.adapter.MarketDataReader import MarketDataReader
from cilly_trading.engine.marketdata.guardrails.adapter_guardrails import assert_adapter_guardrails
from cilly_trading.engine.marketdata.models.market_data_models import (
    Bar,
    MarketDataBatch,
    MarketDataMetadata,
    MarketDataRequest,
)


@dataclass(frozen=True)
class LocalReplayConfig:
    """Configuration for local replay adapter."""

    dataset_path: Path
    format: Literal["csv", "json"]
    delay_steps: int = 0


class LocalReplayMarketDataReader(MarketDataReader):
    """Read-only market data adapter backed by deterministic local replay files."""

    def __init__(self, config: LocalReplayConfig) -> None:
        assert_adapter_guardrails(Path(__file__).resolve())
        if config.delay_steps < 0:
            raise ValueError("delay_steps must be >= 0")
        if not config.dataset_path.exists():
            raise FileNotFoundError(f"Replay dataset missing: {config.dataset_path}")
        if config.format not in ("csv", "json"):
            raise ValueError(f"Unsupported replay format: {config.format}")
        self._config = config
        self._audit_id = _compute_audit_id(config)
        self._rows = _load_rows(config)

    def get_bars(self, request: MarketDataRequest) -> MarketDataBatch:
        symbol = request.symbol.strip().upper()
        timeframe = request.timeframe.strip().upper()
        filtered = [
            row
            for row in self._rows
            if row["symbol"] == symbol and row["timeframe"] == timeframe
        ]
        filtered = _apply_delay(filtered, self._config.delay_steps)
        if request.limit is not None:
            if request.limit < 0:
                raise ValueError("limit must be >= 0")
            filtered = list(filtered)[: request.limit]

        bars = tuple(_row_to_bar(row) for row in filtered)
        metadata = MarketDataMetadata(
            audit_id=self._audit_id,
            source_path=self._config.dataset_path.name,
            delay_steps=self._config.delay_steps,
            row_count=len(bars),
        )
        return MarketDataBatch(bars=bars, metadata=metadata)


def _compute_audit_id(config: LocalReplayConfig) -> str:
    payload = {
        "dataset_name": config.dataset_path.name,
        "format": config.format,
        "delay_steps": config.delay_steps,
    }
    config_json = json.dumps(payload, sort_keys=True, separators=(",", ":"))
    file_bytes = config.dataset_path.read_bytes()
    combined = file_bytes + config_json.encode("utf-8")
    return hashlib.sha256(combined).hexdigest()


def _load_rows(config: LocalReplayConfig) -> list[dict[str, str | int]]:
    if config.format == "csv":
        return _load_csv_rows(config.dataset_path)
    return _load_json_rows(config.dataset_path)


def _load_csv_rows(path: Path) -> list[dict[str, str | int]]:
    rows: list[dict[str, str | int]] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for index, raw in enumerate(reader):
            row = _normalize_row(raw, index)
            rows.append(row)
    return _stable_sort_rows(rows)


def _load_json_rows(path: Path) -> list[dict[str, str | int]]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(raw, list):
        raise ValueError("JSON replay dataset must be a list of objects")
    rows: list[dict[str, str | int]] = []
    for index, item in enumerate(raw):
        if not isinstance(item, dict):
            raise ValueError("JSON replay dataset rows must be objects")
        row = _normalize_row(item, index)
        rows.append(row)
    return _stable_sort_rows(rows)


def _normalize_row(raw: dict[str, str], index: int) -> dict[str, str | int]:
    required = ("timestamp", "open", "high", "low", "close", "volume", "symbol", "timeframe")
    missing = [key for key in required if key not in raw]
    if missing:
        raise ValueError(f"Replay dataset missing columns: {', '.join(missing)}")
    return {
        "timestamp": str(raw["timestamp"]).strip(),
        "open": str(raw["open"]).strip(),
        "high": str(raw["high"]).strip(),
        "low": str(raw["low"]).strip(),
        "close": str(raw["close"]).strip(),
        "volume": str(raw["volume"]).strip(),
        "symbol": str(raw["symbol"]).strip().upper(),
        "timeframe": str(raw["timeframe"]).strip().upper(),
        "_index": index,
    }


def _stable_sort_rows(rows: Sequence[dict[str, str | int]]) -> list[dict[str, str | int]]:
    return sorted(rows, key=lambda row: (row["timestamp"], int(row["_index"])))


def _apply_delay(rows: Sequence[dict[str, str | int]], delay_steps: int) -> Iterable[dict[str, str | int]]:
    if delay_steps <= 0:
        return rows
    if delay_steps >= len(rows):
        return []
    return list(rows)[:-delay_steps]


def _parse_decimal(value: str) -> Decimal:
    return Decimal(value)


def _row_to_bar(row: dict[str, str | int]) -> Bar:
    return Bar(
        timestamp=row["timestamp"],
        open=_parse_decimal(row["open"]),
        high=_parse_decimal(row["high"]),
        low=_parse_decimal(row["low"]),
        close=_parse_decimal(row["close"]),
        volume=_parse_decimal(row["volume"]),
        symbol=row["symbol"],
        timeframe=row["timeframe"],
    )

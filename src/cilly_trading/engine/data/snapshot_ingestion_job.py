from __future__ import annotations

import importlib.util
import hashlib
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Iterable
from uuid import uuid4

import pandas as pd
import yfinance as yf

from cilly_trading.engine.logging import emit_structured_engine_log
from cilly_trading.repositories.snapshot_ingestion_sqlite import (
    OhlcvSnapshotRowRecord,
    SnapshotIngestionRunRecord,
    SqliteSnapshotIngestionRepository,
)
from data_layer.ingestion_validation import (
    SnapshotValidationError,
    validate_market_data_integrity,
    validate_snapshot_source,
)


def _load_sibling_module(module_name: str, filename: str):
    module_path = Path(__file__).resolve().parent / filename
    spec = importlib.util.spec_from_file_location(module_name, module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Unable to load sibling module: {filename}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


_market_data_provider = _load_sibling_module(
    "snapshot_ingestion_market_data_provider",
    "market_data_provider.py",
)
_market_dataset_contract = _load_sibling_module(
    "snapshot_ingestion_market_dataset_contract",
    "market_dataset_contract.py",
)

Candle = _market_data_provider.Candle
MarketDataProvider = _market_data_provider.MarketDataProvider
MarketDataProviderRegistry = _market_data_provider.MarketDataProviderRegistry
MarketDataRequest = _market_data_provider.MarketDataRequest
serialize_candles_deterministically = (
    _market_data_provider.serialize_candles_deterministically
)
build_market_dataset_metadata = _market_dataset_contract.build_market_dataset_metadata

SUPPORTED_SNAPSHOT_TIMEFRAME = "D1"
MAX_SNAPSHOT_CANDLES_PER_SYMBOL = 365
_TIMEFRAME_PROVIDER_INTERVALS = {
    "D1": "1d",
    "1D": "1d",
}


class SnapshotIngestionJobError(RuntimeError):
    """Raised when bounded snapshot ingestion cannot complete safely."""

    def __init__(
        self,
        code: str,
        detail: str,
        *,
        provider_name: str | None = None,
        symbol: str | None = None,
    ) -> None:
        self.code = code
        self.detail = detail
        self.provider_name = provider_name
        self.symbol = symbol
        super().__init__(f"{code}: {detail}")


@dataclass(frozen=True)
class SnapshotIngestionJobRequest:
    symbols: tuple[str, ...]
    timeframe: str
    limit: int
    provider_name: str | None = None


@dataclass(frozen=True)
class SnapshotDatasetSummary:
    symbol: str
    timeframe: str
    dataset_id: str
    start_timestamp: str
    end_timestamp: str
    row_count: int
    content_sha256: str


@dataclass(frozen=True)
class SnapshotIngestionJobResult:
    ingestion_run_id: str
    created_at: str
    provider_name: str
    timeframe: str
    symbols: tuple[str, ...]
    inserted_rows: int
    fingerprint_hash: str
    datasets: tuple[SnapshotDatasetSummary, ...]


class YFinanceDailySnapshotProvider:
    """Bounded daily snapshot provider for server-side ingestion jobs."""

    def iter_candles(self, request: MarketDataRequest) -> Iterable[Candle]:
        interval = _resolve_provider_interval(request.timeframe)
        if request.limit is None or request.limit <= 0:
            raise ValueError("snapshot_request_limit_invalid")

        end = datetime.now(timezone.utc)
        start = end - timedelta(days=request.limit * 5)
        frame = yf.download(
            request.symbol,
            start=start.date(),
            end=end.date(),
            interval=interval,
            progress=False,
            auto_adjust=False,
            actions=False,
        )
        if frame is None or frame.empty:
            return iter(())

        if isinstance(frame.columns, pd.MultiIndex):
            frame.columns = frame.columns.get_level_values(0)

        normalized = frame.reset_index()
        timestamp_column = "Datetime" if "Datetime" in normalized.columns else "Date"
        required_columns = (
            timestamp_column,
            "Open",
            "High",
            "Low",
            "Close",
            "Volume",
        )
        missing = [column for column in required_columns if column not in normalized.columns]
        if missing:
            raise ValueError(f"snapshot_provider_schema_invalid missing={','.join(missing)}")

        normalized = normalized.rename(
            columns={
                timestamp_column: "timestamp",
                "Open": "open",
                "High": "high",
                "Low": "low",
                "Close": "close",
                "Volume": "volume",
            }
        )
        normalized = normalized[
            ["timestamp", "open", "high", "low", "close", "volume"]
        ].copy()
        normalized["timestamp"] = pd.to_datetime(
            normalized["timestamp"],
            utc=True,
            errors="coerce",
        )
        normalized = normalized.dropna(subset=["timestamp"])
        normalized = normalized.sort_values("timestamp").tail(request.limit).reset_index(
            drop=True
        )

        candles: list[Candle] = []
        for row in normalized.to_dict(orient="records"):
            if any(pd.isna(row[field]) for field in ("open", "high", "low", "close", "volume")):
                raise ValueError("snapshot_provider_schema_invalid missing_numeric")
            candles.append(
                Candle(
                    timestamp=row["timestamp"].to_pydatetime(),
                    symbol=request.symbol,
                    timeframe=SUPPORTED_SNAPSHOT_TIMEFRAME,
                    open=Decimal(str(row["open"])),
                    high=Decimal(str(row["high"])),
                    low=Decimal(str(row["low"])),
                    close=Decimal(str(row["close"])),
                    volume=Decimal(str(row["volume"])),
                )
            )
        return iter(tuple(candles))


class SnapshotIngestionJob:
    """Create bounded non-live snapshot runs from a single server-side provider."""

    def __init__(
        self,
        *,
        repository: SqliteSnapshotIngestionRepository,
        provider_registry: MarketDataProviderRegistry,
    ) -> None:
        self._repository = repository
        self._provider_registry = provider_registry

    def run(self, request: SnapshotIngestionJobRequest) -> SnapshotIngestionJobResult:
        symbols = _normalize_symbols(request.symbols)
        timeframe = _normalize_timeframe(request.timeframe)
        limit = _normalize_limit(request.limit)
        provider_entry = _select_provider(
            self._provider_registry,
            provider_name=request.provider_name,
        )
        try:
            source = validate_snapshot_source(provider_entry.name)
        except SnapshotValidationError as exc:
            raise SnapshotIngestionJobError(
                "snapshot_provider_source_invalid",
                str(exc),
                provider_name=provider_entry.name,
            ) from exc

        ingestion_run_id = str(uuid4())
        created_at = _utc_now().isoformat()
        emit_structured_engine_log(
            "snapshot_ingestion.started",
            payload={
                "ingestion_run_id": ingestion_run_id,
                "limit": limit,
                "provider_name": provider_entry.name,
                "symbol_count": len(symbols),
                "symbols": list(symbols),
                "timeframe": timeframe,
            },
        )

        try:
            datasets: list[SnapshotDatasetSummary] = []
            rows: list[OhlcvSnapshotRowRecord] = []
            for symbol in symbols:
                candles = self._load_validated_candles(
                    provider=provider_entry.provider,
                    provider_name=provider_entry.name,
                    symbol=symbol,
                    timeframe=timeframe,
                    limit=limit,
                )
                datasets.append(
                    _build_dataset_summary(
                        candles=candles,
                        created_at=created_at,
                        source=source,
                    )
                )
                rows.extend(
                    _build_snapshot_rows(
                        candles=candles,
                        ingestion_run_id=ingestion_run_id,
                    )
                )

            fingerprint_hash = _compute_run_fingerprint(datasets)
            self._repository.save_snapshot_run(
                run=SnapshotIngestionRunRecord(
                    ingestion_run_id=ingestion_run_id,
                    created_at=created_at,
                    source=source,
                    symbols=symbols,
                    timeframe=timeframe,
                    fingerprint_hash=fingerprint_hash,
                ),
                rows=tuple(rows),
            )
        except SnapshotIngestionJobError as exc:
            emit_structured_engine_log(
                "snapshot_ingestion.failed",
                level="ERROR",
                payload={
                    "code": exc.code,
                    "detail": exc.detail,
                    "ingestion_run_id": ingestion_run_id,
                    "provider_name": exc.provider_name or provider_entry.name,
                    "symbol": exc.symbol,
                    "symbols": list(symbols),
                    "timeframe": timeframe,
                },
            )
            raise
        except Exception as exc:
            wrapped = SnapshotIngestionJobError(
                "snapshot_ingestion_failed",
                str(exc),
                provider_name=provider_entry.name,
            )
            emit_structured_engine_log(
                "snapshot_ingestion.failed",
                level="ERROR",
                payload={
                    "code": wrapped.code,
                    "detail": wrapped.detail,
                    "ingestion_run_id": ingestion_run_id,
                    "provider_name": provider_entry.name,
                    "symbols": list(symbols),
                    "timeframe": timeframe,
                },
            )
            raise wrapped from exc

        result = SnapshotIngestionJobResult(
            ingestion_run_id=ingestion_run_id,
            created_at=created_at,
            provider_name=provider_entry.name,
            timeframe=timeframe,
            symbols=symbols,
            inserted_rows=len(rows),
            fingerprint_hash=fingerprint_hash,
            datasets=tuple(datasets),
        )
        emit_structured_engine_log(
            "snapshot_ingestion.completed",
            payload={
                "dataset_count": len(result.datasets),
                "fingerprint_hash": result.fingerprint_hash,
                "ingestion_run_id": result.ingestion_run_id,
                "inserted_rows": result.inserted_rows,
                "provider_name": result.provider_name,
                "symbols": list(result.symbols),
                "timeframe": result.timeframe,
            },
        )
        return result

    def _load_validated_candles(
        self,
        *,
        provider: MarketDataProvider,
        provider_name: str,
        symbol: str,
        timeframe: str,
        limit: int,
    ) -> tuple[Candle, ...]:
        try:
            candles = tuple(
                provider.iter_candles(
                    MarketDataRequest(
                        symbol=symbol,
                        timeframe=timeframe,
                        limit=limit,
                    )
                )
            )
        except Exception as exc:
            raise SnapshotIngestionJobError(
                "snapshot_provider_fetch_failed",
                f"{type(exc).__name__}: {exc}",
                provider_name=provider_name,
                symbol=symbol,
            ) from exc

        if not candles:
            raise SnapshotIngestionJobError(
                "snapshot_provider_empty",
                "provider returned no candles",
                provider_name=provider_name,
                symbol=symbol,
            )
        if len(candles) > limit:
            raise SnapshotIngestionJobError(
                "snapshot_provider_limit_exceeded",
                "provider returned more candles than requested",
                provider_name=provider_name,
                symbol=symbol,
            )

        ordered = tuple(sorted(candles, key=lambda candle: candle.timestamp))
        for candle in ordered:
            if candle.symbol != symbol:
                raise SnapshotIngestionJobError(
                    "snapshot_provider_symbol_mismatch",
                    f"provider returned candle for unexpected symbol '{candle.symbol}'",
                    provider_name=provider_name,
                    symbol=symbol,
                )
            if candle.timeframe != timeframe:
                raise SnapshotIngestionJobError(
                    "snapshot_provider_timeframe_mismatch",
                    f"provider returned candle for unexpected timeframe '{candle.timeframe}'",
                    provider_name=provider_name,
                    symbol=symbol,
                )
            if candle.timestamp.tzinfo is None:
                raise SnapshotIngestionJobError(
                    "snapshot_provider_timestamp_invalid",
                    "provider returned naive timestamp",
                    provider_name=provider_name,
                    symbol=symbol,
                )

        frame = pd.DataFrame(
            [
                {
                    "timestamp": candle.timestamp.isoformat(),
                    "open": str(candle.open),
                    "high": str(candle.high),
                    "low": str(candle.low),
                    "close": str(candle.close),
                    "volume": str(candle.volume),
                }
                for candle in ordered
            ]
        )
        try:
            validate_market_data_integrity(frame)
        except SnapshotValidationError as exc:
            raise SnapshotIngestionJobError(
                "snapshot_provider_invalid_data",
                str(exc),
                provider_name=provider_name,
                symbol=symbol,
            ) from exc
        return ordered


def build_default_snapshot_provider_registry() -> MarketDataProviderRegistry:
    registry = MarketDataProviderRegistry()
    registry.register(
        name="yfinance",
        provider=YFinanceDailySnapshotProvider(),
        priority=10,
    )
    return registry


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _normalize_symbols(symbols: Iterable[str]) -> tuple[str, ...]:
    normalized = sorted({str(symbol).strip() for symbol in symbols if str(symbol).strip()})
    if not normalized:
        raise SnapshotIngestionJobError(
            "snapshot_symbols_invalid",
            "at least one symbol is required",
        )
    return tuple(normalized)


def _normalize_timeframe(timeframe: str) -> str:
    normalized = str(timeframe).strip().upper()
    if normalized not in _TIMEFRAME_PROVIDER_INTERVALS:
        raise SnapshotIngestionJobError(
            "snapshot_timeframe_unsupported",
            f"only {SUPPORTED_SNAPSHOT_TIMEFRAME} snapshot ingestion is supported",
        )
    return SUPPORTED_SNAPSHOT_TIMEFRAME


def _normalize_limit(limit: int) -> int:
    if not isinstance(limit, int):
        raise SnapshotIngestionJobError(
            "snapshot_limit_invalid",
            "limit must be an integer",
        )
    if limit <= 0 or limit > MAX_SNAPSHOT_CANDLES_PER_SYMBOL:
        raise SnapshotIngestionJobError(
            "snapshot_limit_invalid",
            f"limit must be between 1 and {MAX_SNAPSHOT_CANDLES_PER_SYMBOL}",
        )
    return limit


def _resolve_provider_interval(timeframe: str) -> str:
    normalized = str(timeframe).strip().upper()
    if normalized not in _TIMEFRAME_PROVIDER_INTERVALS:
        raise ValueError("snapshot_timeframe_unsupported")
    return _TIMEFRAME_PROVIDER_INTERVALS[normalized]


def _select_provider(
    registry: MarketDataProviderRegistry,
    *,
    provider_name: str | None,
):
    entries = registry.get_registered()
    if not entries:
        raise SnapshotIngestionJobError(
            "snapshot_provider_unavailable",
            "no snapshot providers are registered",
        )
    if provider_name is None:
        return registry.select_provider()

    normalized = provider_name.strip()
    for entry in entries:
        if entry.name == normalized:
            return entry
    raise SnapshotIngestionJobError(
        "snapshot_provider_unsupported",
        f"provider '{normalized}' is not registered for bounded snapshot ingestion",
        provider_name=normalized,
    )


def _build_dataset_summary(
    *,
    candles: tuple[Candle, ...],
    created_at: str,
    source: str,
) -> SnapshotDatasetSummary:
    content = serialize_candles_deterministically(candles)
    content_sha256 = hashlib.sha256(content.encode("utf-8")).hexdigest()
    metadata = build_market_dataset_metadata(
        symbol=candles[0].symbol,
        timeframe=candles[0].timeframe,
        source=source,
        start_timestamp=candles[0].timestamp.astimezone(timezone.utc).isoformat(),
        end_timestamp=candles[-1].timestamp.astimezone(timezone.utc).isoformat(),
        row_count=len(candles),
        content_sha256=content_sha256,
        created_at=created_at,
    )
    return SnapshotDatasetSummary(
        symbol=metadata["symbol"],
        timeframe=metadata["timeframe"],
        dataset_id=metadata["dataset_id"],
        start_timestamp=metadata["start_timestamp"],
        end_timestamp=metadata["end_timestamp"],
        row_count=metadata["row_count"],
        content_sha256=metadata["content_sha256"],
    )


def _build_snapshot_rows(
    *,
    candles: tuple[Candle, ...],
    ingestion_run_id: str,
) -> tuple[OhlcvSnapshotRowRecord, ...]:
    rows: list[OhlcvSnapshotRowRecord] = []
    for candle in candles:
        timestamp_utc = candle.timestamp.astimezone(timezone.utc)
        rows.append(
            OhlcvSnapshotRowRecord(
                ingestion_run_id=ingestion_run_id,
                symbol=candle.symbol,
                timeframe=candle.timeframe,
                ts=int(timestamp_utc.timestamp() * 1000),
                open=float(candle.open),
                high=float(candle.high),
                low=float(candle.low),
                close=float(candle.close),
                volume=float(candle.volume),
            )
        )
    return tuple(rows)


def _compute_run_fingerprint(
    datasets: Iterable[SnapshotDatasetSummary],
) -> str:
    payload = [
        {
            "content_sha256": dataset.content_sha256,
            "dataset_id": dataset.dataset_id,
            "row_count": dataset.row_count,
            "symbol": dataset.symbol,
            "timeframe": dataset.timeframe,
        }
        for dataset in datasets
    ]
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(canonical.encode("utf-8")).hexdigest()

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Optional

import pandas as pd

FORBIDDEN_SOURCES = {"demo", "seed"}


class SnapshotValidationError(ValueError):
    """Raised when snapshot ingestion validation fails."""


def _normalize_source(source: str) -> str:
    if source is None:
        raise SnapshotValidationError("snapshot_source_missing")
    normalized = source.strip()
    if not normalized:
        raise SnapshotValidationError("snapshot_source_missing")
    return normalized


def _contains_forbidden_source(source: str) -> bool:
    lowered = source.lower()
    return any(token in lowered for token in FORBIDDEN_SOURCES)


def validate_snapshot_source(
    source: str,
    *,
    existing_source: Optional[str] = None,
    forbid_demo_seed: bool = True,
) -> str:
    normalized = _normalize_source(source)
    if forbid_demo_seed and _contains_forbidden_source(normalized):
        raise SnapshotValidationError("snapshot_source_forbidden")
    if existing_source is not None:
        existing_normalized = _normalize_source(existing_source)
        if normalized != existing_normalized:
            raise SnapshotValidationError("snapshot_source_immutable")
    return normalized


def _resolve_timestamp_column(df: pd.DataFrame, timestamp_column: str) -> str:
    if timestamp_column in df.columns:
        return timestamp_column
    if timestamp_column == "timestamp" and "ts" in df.columns:
        return "ts"
    return timestamp_column


def validate_ohlcv_uniqueness(
    df: pd.DataFrame,
    *,
    symbol_column: str = "symbol",
    timeframe_column: str = "timeframe",
    timestamp_column: str = "timestamp",
) -> None:
    if df is None or df.empty:
        return

    resolved_ts = _resolve_timestamp_column(df, timestamp_column)
    required = [symbol_column, timeframe_column, resolved_ts]
    missing = [col for col in required if col not in df.columns]
    if missing:
        raise SnapshotValidationError(
            f"snapshot_missing_columns missing={','.join(missing)}"
        )

    duplicates = df.duplicated(subset=required, keep=False)
    if duplicates.any():
        raise SnapshotValidationError("snapshot_duplicate_rows")


def validate_single_source_rows(
    df: pd.DataFrame,
    *,
    source: str,
    source_column: str = "source",
) -> None:
    if df is None or df.empty:
        return
    if source_column not in df.columns:
        raise SnapshotValidationError("snapshot_source_column_missing")

    expected = _normalize_source(source)
    unique_sources = (
        df[source_column]
        .dropna()
        .astype(str)
        .map(str.strip)
        .loc[lambda s: s != ""]
        .unique()
    )
    if len(unique_sources) > 1:
        raise SnapshotValidationError("snapshot_mixed_sources")
    if len(unique_sources) == 1 and unique_sources[0] != expected:
        raise SnapshotValidationError("snapshot_mixed_sources")


@dataclass(frozen=True)
class SnapshotIngestionValidation:
    source: str
    ingestion_run_id: str
    symbols: Iterable[str]
    timeframe: str


def validate_snapshot_ingestion(
    df: pd.DataFrame,
    *,
    source: str,
    ingestion_run_id: str,
    existing_source: Optional[str] = None,
    symbols: Optional[Iterable[str]] = None,
    timeframe: Optional[str] = None,
) -> SnapshotIngestionValidation:
    normalized_source = validate_snapshot_source(
        source,
        existing_source=existing_source,
        forbid_demo_seed=True,
    )
    validate_ohlcv_uniqueness(df)
    validate_single_source_rows(df, source=normalized_source)
    return SnapshotIngestionValidation(
        source=normalized_source,
        ingestion_run_id=ingestion_run_id,
        symbols=list(symbols or []),
        timeframe=timeframe or "",
    )

from __future__ import annotations

from dataclasses import dataclass
from typing import Final

import pandas as pd

TARGET_COLUMNS: Final[tuple[str, ...]] = (
    "timestamp",
    "open",
    "high",
    "low",
    "close",
    "volume",
)


@dataclass(frozen=True)
class NormalizationResult:
    df: pd.DataFrame
    empty: bool


def _empty_result() -> NormalizationResult:
    empty_df = pd.DataFrame(columns=list(TARGET_COLUMNS))
    return NormalizationResult(df=empty_df, empty=True)


def _normalize_timestamp_column(df: pd.DataFrame) -> pd.DataFrame:
    if "timestamp" not in df.columns and "timeStamp" in df.columns:
        return df.rename(columns={"timeStamp": "timestamp"})
    return df


def normalize_ohlcv(
    df: pd.DataFrame,
    *,
    symbol: str,
    source: str,
) -> NormalizationResult:
    if df is None or df.empty:
        return _empty_result()

    working = _normalize_timestamp_column(df)
    missing = [col for col in TARGET_COLUMNS if col not in working.columns]
    if missing:
        return _empty_result()

    out = working[list(TARGET_COLUMNS)].copy()
    out["timestamp"] = pd.to_datetime(out["timestamp"], utc=True, errors="coerce")
    out = out.dropna(subset=["timestamp"])
    if out.empty:
        return _empty_result()

    for col in TARGET_COLUMNS[1:]:
        out[col] = pd.to_numeric(out[col], errors="coerce")

    out = out.dropna(subset=["open", "high", "low", "close"], how="all")
    if out.empty:
        return _empty_result()

    out = out.sort_values("timestamp").reset_index(drop=True)
    return NormalizationResult(df=out, empty=out.empty)

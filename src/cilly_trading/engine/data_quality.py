"""Data quality analysis for ingested market data.

All functions are pure and deterministic given the same input.
No database access, no side effects.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Mapping, Sequence


@dataclass(frozen=True)
class GapRecord:
    """A detected gap in the time series.

    Attributes:
        start_ts: Epoch seconds of the last bar before the gap.
        end_ts: Epoch seconds of the first bar after the gap.
        duration_bars: Approximate number of missing bars in the gap.
    """

    start_ts: float
    end_ts: float
    duration_bars: int


@dataclass(frozen=True)
class DateRange:
    """First and last bar timestamps in the series."""

    first_bar: float
    last_bar: float


@dataclass(frozen=True)
class DataQualityReport:
    """Per-symbol data quality summary.

    Attributes:
        symbol: The symbol this report covers.
        total_bars: Number of bars present in the dataset.
        expected_bars: Estimated expected bar count from date range and inferred period.
        missing_bars_count: Estimated number of missing bars (max(0, expected - actual)).
        missing_bars_pct: Missing bars as a fraction of expected_bars (0.0–1.0), or None.
        gaps: List of gaps longer than 1 expected period.
        outlier_count: Number of bars flagged as price outliers (|return| > sigma * std).
        timezone_consistent: True when all timestamps appear to be in UTC.
        date_range: First and last bar timestamps, or None if no bars.
        no_data: True when no bars exist for this symbol.
        sigma_threshold: The sigma threshold used for outlier detection.
    """

    symbol: str
    total_bars: int
    expected_bars: int
    missing_bars_count: int
    missing_bars_pct: float | None
    gaps: list[GapRecord]
    outlier_count: int
    timezone_consistent: bool
    date_range: DateRange | None
    no_data: bool
    sigma_threshold: float

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible dict."""
        return {
            "symbol": self.symbol,
            "no_data": self.no_data,
            "total_bars": self.total_bars,
            "expected_bars": self.expected_bars,
            "missing_bars_count": self.missing_bars_count,
            "missing_bars_pct": self.missing_bars_pct,
            "gaps": [
                {
                    "start_ts": g.start_ts,
                    "end_ts": g.end_ts,
                    "duration_bars": g.duration_bars,
                }
                for g in self.gaps
            ],
            "outlier_count": self.outlier_count,
            "timezone_consistent": self.timezone_consistent,
            "date_range": (
                {"first_bar": self.date_range.first_bar, "last_bar": self.date_range.last_bar}
                if self.date_range is not None
                else None
            ),
            "sigma_threshold": self.sigma_threshold,
        }


def _parse_timestamp(value: Any) -> float | None:
    """Parse a timestamp value to epoch seconds."""
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        ts = float(value)
        return ts if math.isfinite(ts) else None
    if isinstance(value, str):
        raw = value.strip().replace("Z", "+00:00")
        if not raw:
            return None
        try:
            dt = datetime.fromisoformat(raw)
        except ValueError:
            return None
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt.timestamp()
    return None


def _is_utc_timestamp(value: Any) -> bool | None:
    """Return True if timestamp is definitively UTC, False if non-UTC, None if unknown."""
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        # Raw numeric timestamps are assumed UTC in this system
        return True
    if isinstance(value, str):
        raw = value.strip()
        if raw.endswith("Z") or raw.endswith("+00:00"):
            return True
        if "+" in raw or raw.count("-") > 2:
            # Has timezone offset — check if it's zero
            raw_norm = raw.replace("Z", "+00:00")
            try:
                dt = datetime.fromisoformat(raw_norm)
            except ValueError:
                return None
            if dt.tzinfo is not None:
                offset_seconds = dt.utcoffset().total_seconds()  # type: ignore[union-attr]
                return offset_seconds == 0.0
        # No timezone info — cannot determine
        return None
    return None


def compute_data_quality_report(
    *,
    symbol: str,
    bars: Sequence[Mapping[str, Any]],
    sigma_threshold: float = 5.0,
) -> DataQualityReport:
    """Compute a data quality report for a sequence of OHLCV bars.

    Args:
        symbol: The symbol identifier (used in the report header only).
        bars: Sequence of bar dicts containing at least 'timestamp' and 'close'.
              'open', 'high', 'low' are used for outlier detection if present.
        sigma_threshold: Standard deviation multiplier for outlier detection.

    Returns:
        DataQualityReport with all quality metrics computed.
    """
    if not bars:
        return DataQualityReport(
            symbol=symbol,
            total_bars=0,
            expected_bars=0,
            missing_bars_count=0,
            missing_bars_pct=None,
            gaps=[],
            outlier_count=0,
            timezone_consistent=True,
            date_range=None,
            no_data=True,
            sigma_threshold=sigma_threshold,
        )

    # Parse and sort bars by timestamp
    parsed: list[tuple[float, dict[str, Any]]] = []
    for bar in bars:
        if not isinstance(bar, Mapping):
            continue
        ts = _parse_timestamp(bar.get("timestamp"))
        if ts is None:
            continue
        parsed.append((ts, dict(bar)))

    if not parsed:
        return DataQualityReport(
            symbol=symbol,
            total_bars=0,
            expected_bars=0,
            missing_bars_count=0,
            missing_bars_pct=None,
            gaps=[],
            outlier_count=0,
            timezone_consistent=True,
            date_range=None,
            no_data=True,
            sigma_threshold=sigma_threshold,
        )

    parsed.sort(key=lambda x: x[0])
    timestamps = [item[0] for item in parsed]
    sorted_bars = [item[1] for item in parsed]
    total_bars = len(timestamps)

    date_range = DateRange(first_bar=timestamps[0], last_bar=timestamps[-1])

    # Infer period from median gap between consecutive bars
    gaps_between: list[float] = []
    for i in range(1, total_bars):
        g = timestamps[i] - timestamps[i - 1]
        if g > 0:
            gaps_between.append(g)

    inferred_period: float | None = None
    if gaps_between:
        inferred_period = statistics.median(gaps_between)

    # Expected bars from date range and period
    if inferred_period and inferred_period > 0 and total_bars >= 2:
        total_seconds = timestamps[-1] - timestamps[0]
        expected_bars = max(total_bars, int(round(total_seconds / inferred_period)) + 1)
    else:
        expected_bars = total_bars

    missing_bars_count = max(0, expected_bars - total_bars)
    missing_bars_pct = (
        missing_bars_count / expected_bars if expected_bars > 0 else None
    )

    # Gap detection: gaps > 1.5 × inferred_period
    gap_records: list[GapRecord] = []
    if inferred_period and total_bars >= 2:
        gap_threshold = inferred_period * 1.5
        for i in range(1, total_bars):
            gap_duration = timestamps[i] - timestamps[i - 1]
            if gap_duration > gap_threshold:
                duration_bars = max(1, int(round(gap_duration / inferred_period)) - 1)
                gap_records.append(
                    GapRecord(
                        start_ts=timestamps[i - 1],
                        end_ts=timestamps[i],
                        duration_bars=duration_bars,
                    )
                )

    # Outlier detection: use close price returns; also check open/high/low if available
    outlier_count = 0
    price_columns = ["close", "open", "high", "low"]
    for col in price_columns:
        prices: list[float] = []
        for bar in sorted_bars:
            val = bar.get(col)
            if isinstance(val, (int, float)) and not isinstance(val, bool) and math.isfinite(val):
                prices.append(float(val))

        if len(prices) < 3:
            continue

        returns = [
            (prices[i] - prices[i - 1]) / prices[i - 1]
            for i in range(1, len(prices))
            if prices[i - 1] != 0.0
        ]
        if len(returns) < 2:
            continue

        mean_r = statistics.mean(returns)
        std_r = statistics.stdev(returns)
        if std_r == 0.0:
            continue

        for r in returns:
            if abs(r - mean_r) > sigma_threshold * std_r:
                outlier_count += 1
        # Count once across all columns (avoid double-counting bars, just column-outliers)

    # Timezone consistency: all timestamps should be UTC
    tz_results: list[bool] = []
    for bar in sorted_bars:
        result = _is_utc_timestamp(bar.get("timestamp"))
        if result is not None:
            tz_results.append(result)

    timezone_consistent = all(tz_results) if tz_results else True

    return DataQualityReport(
        symbol=symbol,
        total_bars=total_bars,
        expected_bars=expected_bars,
        missing_bars_count=missing_bars_count,
        missing_bars_pct=missing_bars_pct,
        gaps=gap_records,
        outlier_count=outlier_count,
        timezone_consistent=timezone_consistent,
        date_range=date_range,
        no_data=False,
        sigma_threshold=sigma_threshold,
    )

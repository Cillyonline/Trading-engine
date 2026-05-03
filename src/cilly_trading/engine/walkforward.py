"""Walk-forward validation framework for out-of-sample strategy testing.

DISCLAIMER: Out-of-sample results produced by this framework do NOT
guarantee future performance. Historical validation of any kind is subject
to structural limitations including survivorship bias, look-ahead bias
in data sourcing, and regime change. Results are provided for
methodological evaluation purposes only.

Window layout
─────────────
Rolling (anchored=False, default):
    Window k covers data[k*step : k*step + window_size].
    In-sample:  data[k*step : k*step + is_size]
    OOS:        data[k*step + is_size : k*step + window_size]

Anchored (anchored=True, expanding):
    Window k covers data[0 : (k+1)*step + is_size].
    In-sample:  data[0 : (k+1)*step]           (grows with k)
    OOS:        data[(k+1)*step : (k+1)*step + oos_size]
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Any, Mapping, Sequence

from cilly_trading.metrics.backtest_metrics import compute_backtest_metrics


PERFORMANCE_DISCLAIMER = (
    "OUT-OF-SAMPLE RESULTS DO NOT GUARANTEE FUTURE PERFORMANCE. "
    "Walk-forward validation is a methodological tool for assessing "
    "parameter robustness. It does not constitute a prediction of future "
    "returns, a readiness claim, or a trading recommendation."
)

_AGGREGATED_METRICS = (
    "sharpe_ratio",
    "max_drawdown",
    "win_rate",
    "profit_factor",
    "calmar_ratio",
    "sortino_ratio",
    "total_return",
    "cagr",
)


@dataclass(frozen=True)
class WalkForwardConfig:
    """Configuration for walk-forward validation.

    Attributes:
        in_sample_ratio: Fraction of each window used for in-sample data.
            Must be in (0, 1). Default: 0.7.
        n_windows: Number of walk-forward windows. Must be >= 1. Default: 5.
        anchored: If True, use expanding (anchored) windows where in-sample
            always starts at the first data point. If False (default), use
            rolling windows of fixed size.
    """

    in_sample_ratio: float = 0.7
    n_windows: int = 5
    anchored: bool = False

    def __post_init__(self) -> None:
        if not (0.0 < self.in_sample_ratio < 1.0):
            raise ValueError(
                f"in_sample_ratio must be in (0, 1), got {self.in_sample_ratio}"
            )
        if self.n_windows < 1:
            raise ValueError(f"n_windows must be >= 1, got {self.n_windows}")


@dataclass(frozen=True)
class WindowBoundary:
    """Explicit timestamp boundaries for a single walk-forward window.

    Attributes:
        window_index: Zero-based index of this window.
        is_start_ts: Timestamp of the first in-sample point (epoch seconds).
        is_end_ts: Timestamp of the last in-sample point (epoch seconds).
        oos_start_ts: Timestamp of the first OOS point (epoch seconds).
        oos_end_ts: Timestamp of the last OOS point (epoch seconds).
    """

    window_index: int
    is_start_ts: float
    is_end_ts: float
    oos_start_ts: float
    oos_end_ts: float


@dataclass(frozen=True)
class WindowResult:
    """OOS evaluation result for a single walk-forward window.

    Attributes:
        window_index: Zero-based index of this window.
        boundary: Explicit timestamp boundaries for the window.
        oos_equity_curve: The out-of-sample equity curve slice.
        oos_trades: The out-of-sample trade records.
        oos_metrics: Metrics computed solely from the OOS slice.
    """

    window_index: int
    boundary: WindowBoundary
    oos_equity_curve: list[dict[str, Any]]
    oos_trades: list[dict[str, Any]]
    oos_metrics: dict[str, Any]


@dataclass(frozen=True)
class OosSummary:
    """Aggregate OOS metrics across all walk-forward windows.

    For each metric key the summary includes ``mean`` and ``std`` computed
    across windows where the metric was non-null.

    Attributes:
        n_windows: Number of windows included in the aggregation.
        metrics: Dict mapping metric name → {"mean": float|None, "std": float|None,
            "n_valid": int}.
        disclaimer: Explicit statement that results are not performance guarantees.
    """

    n_windows: int
    metrics: dict[str, dict[str, Any]]
    disclaimer: str = PERFORMANCE_DISCLAIMER


@dataclass(frozen=True)
class WalkForwardResult:
    """Full result of a walk-forward validation run.

    Attributes:
        config: The configuration used for this run.
        windows: Per-window OOS evaluation results.
        oos_summary: Aggregate OOS summary across all windows.
        disclaimer: Explicit performance disclaimer.
    """

    config: WalkForwardConfig
    windows: list[WindowResult]
    oos_summary: OosSummary
    disclaimer: str = PERFORMANCE_DISCLAIMER

    def to_artifact(self) -> dict[str, Any]:
        """Serialize to a JSON-compatible artifact dict."""
        return {
            "schema_version": "1.0.0",
            "disclaimer": self.disclaimer,
            "config": {
                "in_sample_ratio": self.config.in_sample_ratio,
                "n_windows": self.config.n_windows,
                "anchored": self.config.anchored,
            },
            "windows": [
                {
                    "window_index": w.window_index,
                    "boundary": {
                        "is_start_ts": w.boundary.is_start_ts,
                        "is_end_ts": w.boundary.is_end_ts,
                        "oos_start_ts": w.boundary.oos_start_ts,
                        "oos_end_ts": w.boundary.oos_end_ts,
                    },
                    "oos_metrics": w.oos_metrics,
                }
                for w in self.windows
            ],
            "oos_summary": {
                "n_windows": self.oos_summary.n_windows,
                "disclaimer": self.oos_summary.disclaimer,
                "metrics": self.oos_summary.metrics,
            },
        }


class WalkForwardRunner:
    """Walk-forward validation runner.

    Splits an equity curve (and optionally trades) into in-sample and
    out-of-sample windows, computes OOS metrics for each window, and
    aggregates them into a summary.

    The equity curve must contain dicts with at least ``timestamp`` (numeric
    epoch seconds or ISO-8601 string) and ``equity`` (numeric) keys, already
    sorted or unsorted — the runner sorts them deterministically.

    Trade records are assigned to windows by their ``exit_ts`` field; if
    absent they are excluded from OOS trade metrics.
    """

    def run(
        self,
        *,
        equity_curve: Sequence[Mapping[str, Any]],
        trades: Sequence[Mapping[str, Any]] | None = None,
        config: WalkForwardConfig | None = None,
    ) -> WalkForwardResult:
        """Execute walk-forward validation.

        Args:
            equity_curve: Sequence of equity observations.
            trades: Optional sequence of closed-trade records.
            config: Walk-forward configuration (uses defaults if None).

        Returns:
            WalkForwardResult with per-window and aggregate OOS results.

        Raises:
            ValueError: If the equity curve is too short for the requested
                number of windows.
        """
        cfg = config if config is not None else WalkForwardConfig()
        sorted_curve = self._sort_equity_curve(list(equity_curve))
        sorted_trades = self._sort_trades(list(trades) if trades else [])

        n = len(sorted_curve)
        min_points = cfg.n_windows * 2  # at least 2 per window
        if n < min_points:
            raise ValueError(
                f"equity_curve has {n} points but at least {min_points} are required "
                f"for {cfg.n_windows} windows."
            )

        windows = self._build_windows(sorted_curve, sorted_trades, cfg)
        oos_summary = self._aggregate(windows)

        return WalkForwardResult(
            config=cfg,
            windows=windows,
            oos_summary=oos_summary,
        )

    # ── Window construction ───────────────────────────────────────────────────

    def _build_windows(
        self,
        curve: list[dict[str, Any]],
        trades: list[dict[str, Any]],
        cfg: WalkForwardConfig,
    ) -> list[WindowResult]:
        n = len(curve)
        results: list[WindowResult] = []

        if cfg.anchored:
            # Anchored (expanding): OOS chunks slide forward, IS always from 0.
            oos_step = max(1, n // (cfg.n_windows + 1))
            for k in range(cfg.n_windows):
                is_end_idx = oos_step * (k + 1)
                oos_start_idx = is_end_idx
                oos_end_idx = min(n, oos_start_idx + oos_step)
                if oos_start_idx >= n or oos_end_idx > n:
                    break
                is_slice = curve[0:is_end_idx]
                oos_slice = curve[oos_start_idx:oos_end_idx]
                if not is_slice or not oos_slice:
                    continue
                window = self._make_window(k, is_slice, oos_slice, trades)
                results.append(window)
        else:
            # Rolling: fixed-size windows slide forward.
            window_size = n // cfg.n_windows
            is_size = max(1, int(window_size * cfg.in_sample_ratio))
            oos_size = max(1, window_size - is_size)

            for k in range(cfg.n_windows):
                start_idx = k * window_size
                is_end_idx = start_idx + is_size
                oos_end_idx = start_idx + window_size
                if is_end_idx > n or oos_end_idx > n:
                    break
                is_slice = curve[start_idx:is_end_idx]
                oos_slice = curve[is_end_idx:oos_end_idx]
                if not is_slice or not oos_slice:
                    continue
                window = self._make_window(k, is_slice, oos_slice, trades)
                results.append(window)

        return results

    def _make_window(
        self,
        index: int,
        is_slice: list[dict[str, Any]],
        oos_slice: list[dict[str, Any]],
        all_trades: list[dict[str, Any]],
    ) -> WindowResult:
        is_start_ts = float(is_slice[0]["_ts"])
        is_end_ts = float(is_slice[-1]["_ts"])
        oos_start_ts = float(oos_slice[0]["_ts"])
        oos_end_ts = float(oos_slice[-1]["_ts"])

        # Verify no data leakage: OOS must start strictly after IS ends.
        assert oos_start_ts >= is_end_ts, (
            f"Window {index}: data leakage detected — OOS starts at {oos_start_ts} "
            f"but IS ends at {is_end_ts}."
        )

        boundary = WindowBoundary(
            window_index=index,
            is_start_ts=is_start_ts,
            is_end_ts=is_end_ts,
            oos_start_ts=oos_start_ts,
            oos_end_ts=oos_end_ts,
        )

        # Build clean equity curve dicts (drop internal _ts field)
        oos_equity = [{"timestamp": p["timestamp"], "equity": p["equity"]} for p in oos_slice]

        # Filter trades to OOS window by exit_ts
        oos_trades = [
            t for t in all_trades
            if self._trade_exit_ts(t) is not None
            and oos_start_ts <= self._trade_exit_ts(t) <= oos_end_ts  # type: ignore[operator]
        ]

        oos_metrics = compute_backtest_metrics(equity_curve=oos_equity, trades=oos_trades)

        return WindowResult(
            window_index=index,
            boundary=boundary,
            oos_equity_curve=oos_equity,
            oos_trades=oos_trades,
            oos_metrics=oos_metrics,
        )

    # ── Aggregation ───────────────────────────────────────────────────────────

    def _aggregate(self, windows: list[WindowResult]) -> OosSummary:
        summary_metrics: dict[str, dict[str, Any]] = {}

        for key in _AGGREGATED_METRICS:
            values = [
                w.oos_metrics[key]
                for w in windows
                if key in w.oos_metrics and w.oos_metrics[key] is not None
            ]
            n_valid = len(values)
            mean_val = statistics.mean(values) if values else None
            std_val = statistics.stdev(values) if len(values) >= 2 else None
            summary_metrics[key] = {
                "mean": mean_val,
                "std": std_val,
                "n_valid": n_valid,
            }

        return OosSummary(n_windows=len(windows), metrics=summary_metrics)

    # ── Sorting helpers ───────────────────────────────────────────────────────

    def _sort_equity_curve(self, curve: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        parsed: list[tuple[float, str, dict[str, Any]]] = []
        for point in curve:
            ts = self._parse_timestamp(point.get("timestamp"))
            if ts is None:
                continue
            equity = point.get("equity")
            if equity is None:
                continue
            raw_ts_str = str(point.get("timestamp", ""))
            record = {
                "timestamp": point["timestamp"],
                "equity": float(equity),
                "_ts": ts,
            }
            parsed.append((ts, raw_ts_str, record))

        parsed.sort(key=lambda x: (x[0], x[1]))
        return [item[2] for item in parsed]

    def _sort_trades(self, trades: list[Mapping[str, Any]]) -> list[dict[str, Any]]:
        parsed: list[tuple[float, str, dict[str, Any]]] = []
        for trade in trades:
            ts = self._parse_timestamp(trade.get("exit_ts"))
            sort_ts = ts if ts is not None else 0.0
            trade_id = str(trade.get("trade_id", ""))
            parsed.append((sort_ts, trade_id, dict(trade)))

        parsed.sort(key=lambda x: (x[0], x[1]))
        return [item[2] for item in parsed]

    def _parse_timestamp(self, value: Any) -> float | None:
        import math
        if isinstance(value, bool):
            return None
        if isinstance(value, (int, float)):
            ts = float(value)
            return ts if math.isfinite(ts) else None
        if isinstance(value, str):
            from datetime import datetime, timezone
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

    def _trade_exit_ts(self, trade: dict[str, Any]) -> float | None:
        return self._parse_timestamp(trade.get("exit_ts"))

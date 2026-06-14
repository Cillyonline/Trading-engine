"""Export deterministic historical multi-asset snapshots for TURTLE research.

Produces a backtest-compatible JSON snapshot array accepted by:
  python -m cilly_trading backtest --snapshots <PATH> ...

Usage (OHLCV only):
  python scripts/export_historical_snapshots.py \\
      --symbols AAPL,MSFT,NVDA,GS,WMT,COST \\
      --start 2023-01-01 \\
      --end   2023-12-31 \\
      --out   data/artifacts/historical_snapshots

Usage (with TURTLE signal annotations for research):
  python scripts/export_historical_snapshots.py \\
      --symbols AAPL,MSFT,NVDA,GS,WMT,COST \\
      --start 2023-01-01 \\
      --end   2023-12-31 \\
      --out   data/artifacts/historical_snapshots \\
      --annotate-signals

Outputs under <out>/ (OHLCV mode):
  historical_snapshots_<start>_<end>.json        -- backtest-compatible snapshot array
  historical_snapshots_<start>_<end>_meta.json   -- lineage / coverage metadata

Additional outputs (--annotate-signals mode):
  historical_snapshots_<start>_<end>_turtle_annotated.json   -- snapshots with embedded
      turtle_research annotation and signals array for entry_confirmed bars
  historical_snapshots_<start>_<end>_turtle_research.json    -- TURTLE signal frequency
      analysis: stage counts, score buckets, blocker rates by symbol
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
from datetime import date, datetime, timezone
from decimal import Decimal, ROUND_HALF_UP, localcontext
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# Module-level flag toggled by --no-ssl-verify before first yfinance import.
_SSL_VERIFY = True

GOVERNED_SYMBOLS = ("AAPL", "MSFT", "NVDA", "GS", "WMT", "COST")
_SNAPSHOT_DATE_FMT = "%Y-%m-%d"

# Research thresholds — read-only reference values from paper execution config.
# These are not changed by this script; they are used only to annotate whether
# raw trade-risk distance exceeds an exporter-only research threshold.
_MIN_SCORE_THRESHOLD = 60.0
_RAW_TRADE_RISK_RESEARCH_CAP_PCT = 0.01
_MAX_RISK_PER_TRADE_PCT = _RAW_TRADE_RISK_RESEARCH_CAP_PCT
_RISK_PCT_SCALE = Decimal("0.00000001")
_SCORE_BUCKETS = ("<50", "50-55", "55-60", "60-65", "65-70", "70+")
_SOURCE_YFINANCE = "yfinance"
_SOURCE_CSV_DIR = "csv-dir"

# Default TurtleStrategy parameters (match TurtleConfig defaults).
_TURTLE_DEFAULT_CONFIG: dict[str, Any] = {
    "breakout_lookback": 20,
    "proximity_threshold_pct": 0.03,
    "min_score": 30.0,
    "stop_loss_buffer_pct": 0.01,
    "confirmed_score_min": 60.0,
    "confirmed_score_range": 40.0,
    "confirmed_max_breakout_strength_pct": 0.05,
    "confirmed_entry_zone_upper_factor": 1.02,
    "setup_score_base": 80.0,
    "setup_score_range": 40.0,
    "setup_entry_zone_upper_factor": 1.01,
    "exit_lookback": 10,
}


# ---------------------------------------------------------------------------
# Snapshot ID
# ---------------------------------------------------------------------------

def _snapshot_id(symbol: str, dt: date) -> str:
    """Deterministic snapshot ID: <SYMBOL>_<YYYY-MM-DD>."""
    return f"{symbol}_{dt.strftime(_SNAPSHOT_DATE_FMT)}"


# ---------------------------------------------------------------------------
# Fetch
# ---------------------------------------------------------------------------

def _fetch_symbol(symbol: str, start: date, end: date, *, session=None) -> list[dict[str, Any]]:
    """Fetch daily OHLCV for *symbol* in [start, end] (inclusive) via yfinance."""
    import datetime as _dt

    try:
        import pandas as pd
        import yfinance as yf
    except ImportError as exc:
        raise RuntimeError(f"Missing dependency: {exc}. Install pandas and yfinance.") from exc

    # yfinance end is exclusive – add one day
    end_exclusive = end + _dt.timedelta(days=1)

    kwargs: dict[str, Any] = dict(
        start=start.strftime(_SNAPSHOT_DATE_FMT),
        end=end_exclusive.strftime(_SNAPSHOT_DATE_FMT),
        interval="1d",
        progress=False,
        auto_adjust=False,
        actions=False,
    )
    if session is not None:
        kwargs["session"] = session

    frame = yf.download(symbol, **kwargs)
    if frame is None or frame.empty:
        return []

    if isinstance(frame.columns, pd.MultiIndex):
        frame.columns = frame.columns.get_level_values(0)

    frame = frame.reset_index()
    ts_col = "Datetime" if "Datetime" in frame.columns else "Date"
    rename = {ts_col: "timestamp", "Open": "open", "High": "high",
              "Low": "low", "Close": "close", "Volume": "volume"}
    frame = frame.rename(columns=rename)
    frame = frame[["timestamp", "open", "high", "low", "close", "volume"]].copy()
    frame["timestamp"] = pd.to_datetime(frame["timestamp"], utc=True, errors="coerce")
    frame = frame.dropna(subset=["timestamp"])
    frame = frame.sort_values("timestamp").reset_index(drop=True)

    rows: list[dict[str, Any]] = []
    for _, row in frame.iterrows():
        ts: datetime = row["timestamp"].to_pydatetime()
        bar_date = ts.date()
        rows.append({
            "id": _snapshot_id(symbol, bar_date),
            "timestamp": ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "symbol": symbol,
            "open": str(round(float(row["open"]), 6)),
            "high": str(round(float(row["high"]), 6)),
            "low": str(round(float(row["low"]), 6)),
            "close": str(round(float(row["close"]), 6)),
            "volume": str(int(row["volume"])),
            "timeframe": "D1",
        })
    return rows


def _parse_local_csv_date(raw_value: str) -> datetime | None:
    value = raw_value.strip()
    if not value:
        return None
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed.astimezone(timezone.utc)
        parsed_date = date.fromisoformat(value)
        return datetime(parsed_date.year, parsed_date.month, parsed_date.day, tzinfo=timezone.utc)
    except ValueError:
        return None


def _normalize_local_csv_number(raw_value: Any, *, integer: bool = False) -> str | None:
    if raw_value is None:
        return None
    value = str(raw_value).strip()
    if not value:
        return None
    try:
        number = Decimal(value)
    except Exception:
        return None
    if not number.is_finite():
        return None
    if integer:
        return str(int(number))
    return str(round(float(number), 6))


def _fetch_symbol_from_csv_dir(
    symbol: str,
    start: date,
    end: date,
    *,
    source_dir: Path,
) -> tuple[list[dict[str, Any]], int]:
    """Read deterministic OHLCV rows from <source_dir>/<SYMBOL>.csv."""
    csv_path = source_dir / f"{symbol}.csv"
    if not csv_path.exists():
        return [], 0

    rows: list[dict[str, Any]] = []
    missing_ohlcv_rows = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        for raw in reader:
            raw_timestamp = raw.get("timestamp") or raw.get("date") or ""
            parsed_ts = _parse_local_csv_date(raw_timestamp)
            open_value = _normalize_local_csv_number(raw.get("open"))
            high_value = _normalize_local_csv_number(raw.get("high"))
            low_value = _normalize_local_csv_number(raw.get("low"))
            close_value = _normalize_local_csv_number(raw.get("close"))
            volume_value = _normalize_local_csv_number(raw.get("volume"), integer=True)
            if (
                parsed_ts is None
                or open_value is None
                or high_value is None
                or low_value is None
                or close_value is None
                or volume_value is None
            ):
                missing_ohlcv_rows += 1
                continue

            bar_date = parsed_ts.date()
            if bar_date < start or bar_date > end:
                continue

            rows.append({
                "id": _snapshot_id(symbol, bar_date),
                "timestamp": parsed_ts.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "symbol": symbol,
                "open": open_value,
                "high": high_value,
                "low": low_value,
                "close": close_value,
                "volume": volume_value,
                "timeframe": "D1",
            })

    rows.sort(key=lambda r: (r["timestamp"], r["id"]))
    return rows, missing_ohlcv_rows


# ---------------------------------------------------------------------------
# Build snapshot array + metadata
# ---------------------------------------------------------------------------

def build_export(
    symbols: tuple[str, ...],
    start: date,
    end: date,
    *,
    command: str,
    session=None,
    source: str = _SOURCE_YFINANCE,
    source_dir: Path | None = None,
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (snapshots, metadata) for the given symbol universe and date range."""
    per_symbol: dict[str, list[dict[str, Any]]] = {}
    missing_ohlcv_by_symbol: dict[str, int] = {}
    missing_symbols: list[str] = []
    actual_start: date | None = None
    actual_end: date | None = None

    for symbol in sorted(symbols):
        if source == _SOURCE_YFINANCE:
            rows = _fetch_symbol(symbol, start, end, session=session)
            missing_ohlcv_by_symbol[symbol] = sum(
                1 for r in rows
                if any(r.get(f) is None for f in ("open", "high", "low", "close", "volume"))
            )
        elif source == _SOURCE_CSV_DIR:
            if source_dir is None:
                raise ValueError("--source-dir is required when source='csv-dir'")
            rows, missing_ohlcv_rows = _fetch_symbol_from_csv_dir(
                symbol,
                start,
                end,
                source_dir=source_dir,
            )
            missing_ohlcv_by_symbol[symbol] = missing_ohlcv_rows
        else:
            raise ValueError(f"unsupported source: {source!r}")
        per_symbol[symbol] = rows
        if not rows:
            missing_symbols.append(symbol)
        else:
            dates = [
                datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%SZ").date()
                for r in rows
            ]
            sym_start = min(dates)
            sym_end = max(dates)
            actual_start = min(actual_start, sym_start) if actual_start else sym_start
            actual_end = max(actual_end, sym_end) if actual_end else sym_end

    # Merge all rows and sort deterministically by (timestamp, id)
    all_rows: list[dict[str, Any]] = [r for rows in per_symbol.values() for r in rows]
    all_rows.sort(key=lambda r: (r["timestamp"], r["id"]))

    # Deduplicate IDs (shouldn't happen, but be safe)
    seen_ids: set[str] = set()
    deduped: list[dict[str, Any]] = []
    for row in all_rows:
        if row["id"] not in seen_ids:
            seen_ids.add(row["id"])
            deduped.append(row)

    # Build content hash for lineage
    content_bytes = json.dumps(deduped, sort_keys=True, ensure_ascii=True).encode()
    content_sha256 = hashlib.sha256(content_bytes).hexdigest()

    # Coverage per symbol
    symbol_coverage: dict[str, Any] = {}
    for symbol in sorted(symbols):
        rows = per_symbol.get(symbol, [])
        symbol_coverage[symbol] = {
            "snapshot_count": len(rows),
            "missing": len(rows) == 0,
            "missing_ohlcv_rows": missing_ohlcv_by_symbol.get(symbol, 0),
        }

    metadata: dict[str, Any] = {
        "artifact_type": "historical_multi_asset_snapshot_export",
        "data_source": source,
        "source": {
            "type": source,
            "path": str(source_dir) if source_dir is not None else None,
        },
        "command": command,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "requested_date_range": {
            "start": start.strftime(_SNAPSHOT_DATE_FMT),
            "end": end.strftime(_SNAPSHOT_DATE_FMT),
        },
        "actual_date_range": {
            "start": actual_start.strftime(_SNAPSHOT_DATE_FMT) if actual_start else None,
            "end": actual_end.strftime(_SNAPSHOT_DATE_FMT) if actual_end else None,
        },
        "symbol_universe": list(sorted(symbols)),
        "symbol_coverage": symbol_coverage,
        "missing_symbols": missing_symbols,
        "total_snapshot_count": len(deduped),
        "content_sha256": content_sha256,
        "backtest_contract": {
            "compatible": True,
            "required_fields_present": ["id", "timestamp"],
            "note": (
                "Each snapshot object contains id (non-empty string) and "
                "timestamp (ISO-8601 UTC string) satisfying the --snapshots "
                "input contract of python -m cilly_trading backtest."
            ),
        },
        "traceability": {
            "issue": "#1220",
            "follows": ["#1217", "#1218", "#1219"],
            "unblocks": "historical multi-asset TURTLE score-threshold and stop-distance research",
        },
    }

    return deduped, metadata


# ---------------------------------------------------------------------------
# TURTLE signal annotation
# ---------------------------------------------------------------------------

def _build_symbol_ohlcv_df(rows: list[dict[str, Any]]):
    """Build a UTC-indexed OHLCV DataFrame from snapshot row dicts for one symbol."""
    try:
        import pandas as pd
    except ImportError as exc:
        raise RuntimeError("pandas is required") from exc

    records = []
    for r in sorted(rows, key=lambda x: x["timestamp"]):
        ts = datetime.strptime(r["timestamp"], "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        records.append({
            "timestamp": ts,
            "open": float(r["open"]),
            "high": float(r["high"]),
            "low": float(r["low"]),
            "close": float(r["close"]),
            "volume": float(r["volume"]),
        })

    df = __import__("pandas").DataFrame(records).set_index("timestamp")
    return df


def _score_bucket(score: float | None) -> str | None:
    if score is None:
        return None
    if score < 50:
        return "<50"
    if score < 55:
        return "50-55"
    if score < 60:
        return "55-60"
    if score < 65:
        return "60-65"
    if score < 70:
        return "65-70"
    return "70+"


def _derive_entry_price(signal: dict[str, Any]) -> tuple[float | None, str | None]:
    """Return the explicit entry price used for TURTLE risk annotation."""
    entry_zone = signal.get("entry_zone")
    if not isinstance(entry_zone, dict):
        return None, None
    if entry_zone.get("from_") is None or entry_zone.get("to") is None:
        return None, None

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        entry_price = (
            Decimal(str(entry_zone["from_"])) + Decimal(str(entry_zone["to"]))
        ) / Decimal("2")
    return float(entry_price), "entry_zone_midpoint"


def _derive_trade_risk_pct(
    signal: dict[str, Any],
) -> tuple[float | None, float | None, str | None]:
    entry_price, entry_price_source = _derive_entry_price(signal)
    raw_stop_loss = signal.get("stop_loss")
    if entry_price is None or entry_price <= 0 or raw_stop_loss is None:
        return None, entry_price, entry_price_source

    with localcontext() as ctx:
        ctx.prec = 28
        ctx.rounding = ROUND_HALF_UP
        stop_loss = Decimal(str(raw_stop_loss))
        entry = Decimal(str(entry_price))
        if stop_loss <= 0:
            return None, entry_price, entry_price_source
        trade_risk_pct = (abs(entry - stop_loss) / entry).quantize(_RISK_PCT_SCALE)
    return float(trade_risk_pct), entry_price, entry_price_source


def _compute_signal_id_local(
    symbol: str,
    timestamp: str,
    stage: str,
    direction: str,
) -> str:
    """Deterministic signal ID using the same identity payload as models.compute_signal_id."""
    payload: dict[str, Any] = {
        "data_source": "yfinance",
        "direction": direction,
        "market_type": "stock",
        "stage": stage,
        "strategy": "TURTLE",
        "symbol": symbol,
        "timeframe": "D1",
        "timestamp": timestamp,
    }
    canonical = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
    return hashlib.sha256(canonical.encode()).hexdigest()


def generate_turtle_signal_annotations(
    per_symbol_rows: dict[str, list[dict[str, Any]]],
    turtle_config: dict[str, Any] | None = None,
    *,
    min_score_threshold: float = _MIN_SCORE_THRESHOLD,
    max_risk_per_trade_pct: float = _MAX_RISK_PER_TRADE_PCT,
) -> dict[str, dict[str, Any]]:
    """Run TurtleStrategy rolling window on historical OHLCV data.

    For each bar of each symbol, calls generate_signals(df[:i+1], config)
    and records the resulting signal metadata (or no-signal) keyed by snapshot ID.

    Returns mapping: snapshot_id -> annotation dict.
    The returned dict can be used to embed turtle_research into snapshot objects
    and to build a research summary artifact.
    """
    from cilly_trading.strategies.turtle import TurtleStrategy

    cfg = dict(_TURTLE_DEFAULT_CONFIG)
    if turtle_config:
        cfg.update(turtle_config)

    strategy = TurtleStrategy()
    annotations: dict[str, dict[str, Any]] = {}

    for symbol, rows in per_symbol_rows.items():
        if not rows:
            continue

        df = _build_symbol_ohlcv_df(rows)

        for i in range(len(df)):
            bar_ts = df.index[i]
            bar_date = bar_ts.date()
            snap_id = _snapshot_id(symbol, bar_date)
            ts_str = bar_ts.strftime("%Y-%m-%dT%H:%M:%SZ")

            df_window = df.iloc[: i + 1]
            signals = strategy.generate_signals(df_window, cfg)

            if not signals:
                annotations[snap_id] = {
                    "symbol": symbol,
                    "timestamp": ts_str,
                    "strategy": "TURTLE",
                    "signal_produced": False,
                    "stage": None,
                    "score": None,
                    "score_bucket": None,
                    "direction": None,
                    "signal_id": None,
                    "confirmation_rule": None,
                    "entry_zone": None,
                    "entry_price": None,
                    "entry_price_source": None,
                    "stop_loss": None,
                    "trade_risk_pct": None,
                    "score_blocked": False,
                    "raw_trade_risk_research_cap_pct": max_risk_per_trade_pct,
                    "raw_trade_risk_research_exceeded": False,
                    "is_research_threshold_candidate": False,
                }
                continue

            sig = signals[0]
            stage = sig.get("stage")
            score = sig.get("score")
            direction = sig.get("direction", "long")
            derived_trade_risk_pct, entry_price, entry_price_source = _derive_trade_risk_pct(sig)
            trade_risk_pct = sig.get("trade_risk_pct")
            if stage == "entry_confirmed" or trade_risk_pct is None:
                trade_risk_pct = derived_trade_risk_pct

            sig_id = _compute_signal_id_local(symbol, ts_str, stage, direction)

            score_blocked = (
                stage in {"entry_confirmed", "setup"}
                and score is not None
                and score < min_score_threshold
            )
            raw_trade_risk_research_exceeded = (
                trade_risk_pct is not None
                and trade_risk_pct > max_risk_per_trade_pct
            )

            annotations[snap_id] = {
                "symbol": symbol,
                "timestamp": ts_str,
                "strategy": "TURTLE",
                "signal_produced": True,
                "stage": stage,
                "score": score,
                "score_bucket": _score_bucket(score),
                "direction": direction,
                "signal_id": sig_id,
                "confirmation_rule": sig.get("confirmation_rule"),
                "entry_zone": sig.get("entry_zone"),
                "entry_price": entry_price,
                "entry_price_source": entry_price_source,
                "stop_loss": sig.get("stop_loss"),
                "trade_risk_pct": trade_risk_pct,
                "score_blocked": score_blocked,
                "raw_trade_risk_research_cap_pct": max_risk_per_trade_pct,
                "raw_trade_risk_research_exceeded": raw_trade_risk_research_exceeded,
                "is_research_threshold_candidate": (
                    stage == "entry_confirmed"
                    and not score_blocked
                    and not raw_trade_risk_research_exceeded
                ),
            }

    return annotations


def _build_signals_array(
    annotation: dict[str, Any],
    *,
    min_score_threshold: float,
    max_risk_per_trade_pct: float,
) -> list[dict[str, Any]]:
    """Build the backtest-compatible signals array from a TURTLE annotation.

    Only entry_confirmed signals receive an action/quantity/risk_evidence block.
    setup and exit annotations are research-only; they do not create backtest orders.
    Risk evidence decision reflects the score threshold only. Raw trade-risk
    comparison is exporter-only sensitivity analysis, not runtime rejection.
    """
    if not annotation.get("signal_produced"):
        return []

    stage = annotation.get("stage")
    if stage != "entry_confirmed":
        return []

    score = annotation.get("score") or 0.0
    trade_risk_pct = annotation.get("trade_risk_pct")

    score_ok = score >= min_score_threshold
    raw_trade_risk_research_exceeded = (
        trade_risk_pct is not None
        and trade_risk_pct > max_risk_per_trade_pct
    )

    decision = "APPROVED" if score_ok else "REJECTED"

    blocker_parts: list[str] = []
    if not score_ok:
        blocker_parts.append(
            f"score={score:.6f} < min_score_threshold={min_score_threshold}"
        )
    reason = "; ".join(blocker_parts) if blocker_parts else "signal_approved"

    return [
        {
            "action": "BUY",
            "quantity": "1",
            "risk_evidence": {
                "decision": decision,
                "max_allowed": str(min_score_threshold),
                "raw_trade_risk_research_cap_pct": str(max_risk_per_trade_pct),
                "raw_trade_risk_research_exceeded": raw_trade_risk_research_exceeded,
                "raw_trade_risk_research_note": (
                    "Exporter-only sensitivity analysis. Runtime treats "
                    "max_risk_per_trade_pct as a sizing risk-budget input, not "
                    "as a hard raw trade_risk_pct rejection cap."
                ),
                "reason": reason,
                "rule_version": "turtle-research-v2",
                "score": str(round(score, 6)),
                "trade_risk_pct": (
                    str(round(float(trade_risk_pct), 8))
                    if trade_risk_pct is not None
                    else None
                ),
                "entry_price": annotation.get("entry_price"),
                "entry_price_source": annotation.get("entry_price_source"),
                "stop_loss": annotation.get("stop_loss"),
            },
            "score": score,
            "signal_id": annotation["signal_id"],
            "stage": stage,
            "strategy": "TURTLE",
            "symbol": annotation["symbol"],
        }
    ]


def annotate_snapshots(
    snapshots: list[dict[str, Any]],
    annotations: dict[str, dict[str, Any]],
    *,
    min_score_threshold: float = _MIN_SCORE_THRESHOLD,
    max_risk_per_trade_pct: float = _MAX_RISK_PER_TRADE_PCT,
) -> list[dict[str, Any]]:
    """Return new snapshot list with turtle_research and signals fields embedded.

    Original snapshot objects are not mutated.
    """
    result = []
    for snap in snapshots:
        enriched = dict(snap)
        snap_id = snap.get("id", "")
        ann = annotations.get(snap_id)

        if ann is not None:
            enriched["turtle_research"] = ann
            signals_arr = _build_signals_array(
                ann,
                min_score_threshold=min_score_threshold,
                max_risk_per_trade_pct=max_risk_per_trade_pct,
            )
            if signals_arr:
                enriched["signals"] = signals_arr
        else:
            enriched["turtle_research"] = {
                "symbol": snap.get("symbol"),
                "timestamp": snap.get("timestamp"),
                "strategy": "TURTLE",
                "signal_produced": False,
                "stage": None,
                "score": None,
                "score_bucket": None,
                "direction": None,
                "signal_id": None,
                "confirmation_rule": None,
                "entry_zone": None,
                "entry_price": None,
                "entry_price_source": None,
                "stop_loss": None,
                "trade_risk_pct": None,
                "score_blocked": False,
                "raw_trade_risk_research_cap_pct": max_risk_per_trade_pct,
                "raw_trade_risk_research_exceeded": False,
                "is_research_threshold_candidate": False,
            }

        result.append(enriched)
    return result


def build_turtle_research_summary(
    annotations: dict[str, dict[str, Any]],
    *,
    min_score_threshold: float = _MIN_SCORE_THRESHOLD,
    max_risk_per_trade_pct: float = _MAX_RISK_PER_TRADE_PCT,
) -> dict[str, Any]:
    """Build aggregated TURTLE signal frequency analysis by symbol."""
    by_symbol: dict[str, dict[str, Any]] = {}
    scores_by_sym: dict[str, list[float]] = {}

    for ann in annotations.values():
        symbol = ann["symbol"]
        if symbol not in by_symbol:
            by_symbol[symbol] = {
                "total_bars": 0,
                "signals_produced": 0,
                "stages": {"entry_confirmed": 0, "setup": 0, "exit": 0},
                "score_blocked_count": 0,
                "raw_trade_risk_research_exceeded_count": 0,
                "research_threshold_candidates": 0,
                "score_buckets": {bucket: 0 for bucket in _SCORE_BUCKETS},
            }
            scores_by_sym[symbol] = []

        by_symbol[symbol]["total_bars"] += 1

        if ann.get("signal_produced"):
            by_symbol[symbol]["signals_produced"] += 1
            stage = ann.get("stage")
            if stage in by_symbol[symbol]["stages"]:
                by_symbol[symbol]["stages"][stage] += 1

            score = ann.get("score")
            if score is not None:
                scores_by_sym[symbol].append(score)
                bucket = _score_bucket(score)
                if bucket in by_symbol[symbol]["score_buckets"]:
                    by_symbol[symbol]["score_buckets"][bucket] += 1

            if ann.get("score_blocked"):
                by_symbol[symbol]["score_blocked_count"] += 1
            if ann.get("raw_trade_risk_research_exceeded"):
                by_symbol[symbol]["raw_trade_risk_research_exceeded_count"] += 1
            if ann.get("is_research_threshold_candidate"):
                by_symbol[symbol]["research_threshold_candidates"] += 1

    # Attach score statistics
    for symbol, data in by_symbol.items():
        scores = scores_by_sym.get(symbol, [])
        if scores:
            data["score_min"] = round(min(scores), 6)
            data["score_max"] = round(max(scores), 6)
            data["score_mean"] = round(sum(scores) / len(scores), 6)
        else:
            data["score_min"] = None
            data["score_max"] = None
            data["score_mean"] = None

    totals: dict[str, Any] = {
        "total_bars": sum(d["total_bars"] for d in by_symbol.values()),
        "signals_produced": sum(d["signals_produced"] for d in by_symbol.values()),
        "entry_confirmed_count": sum(d["stages"]["entry_confirmed"] for d in by_symbol.values()),
        "setup_count": sum(d["stages"]["setup"] for d in by_symbol.values()),
        "exit_count": sum(d["stages"]["exit"] for d in by_symbol.values()),
        "research_threshold_candidates": sum(
            d["research_threshold_candidates"] for d in by_symbol.values()
        ),
        "score_blocked_count": sum(d["score_blocked_count"] for d in by_symbol.values()),
        "raw_trade_risk_research_exceeded_count": sum(
            d["raw_trade_risk_research_exceeded_count"] for d in by_symbol.values()
        ),
    }

    return {
        "artifact_type": "turtle_signal_frequency_research",
        "strategy": "TURTLE",
        "min_score_threshold_applied": min_score_threshold,
        "raw_trade_risk_research_cap_pct": max_risk_per_trade_pct,
        "note": (
            "Score threshold is a reference value from paper execution config. "
            "Raw trade-risk threshold comparison is exporter-only sensitivity "
            "analysis; runtime max_risk_per_trade_pct is a sizing risk-budget "
            "input, not a hard raw trade_risk_pct cap. No threshold was changed "
            "by this script."
        ),
        "by_symbol": by_symbol,
        "totals": totals,
        "traceability": {
            "issue": "#1220",
            "follows": ["#1217", "#1218", "#1219"],
        },
    }


# ---------------------------------------------------------------------------
# I/O helpers
# ---------------------------------------------------------------------------

def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True, indent=2) + "\n",
        encoding="utf-8",
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Export deterministic historical multi-asset snapshots for TURTLE backtest research. "
            "Use --annotate-signals to embed TURTLE signal annotations and produce a "
            "research summary artifact."
        ),
    )
    parser.add_argument(
        "--symbols",
        default=",".join(GOVERNED_SYMBOLS),
        help=f"Comma-separated symbol list. Default: {','.join(GOVERNED_SYMBOLS)}.",
    )
    parser.add_argument(
        "--start",
        required=True,
        metavar="YYYY-MM-DD",
        help="Inclusive start date for the historical range.",
    )
    parser.add_argument(
        "--end",
        required=True,
        metavar="YYYY-MM-DD",
        help="Inclusive end date for the historical range.",
    )
    parser.add_argument(
        "--out",
        default=str(ROOT / "data" / "artifacts" / "historical_snapshots"),
        help="Output directory for generated artifacts.",
    )
    parser.add_argument(
        "--source",
        choices=(_SOURCE_YFINANCE, _SOURCE_CSV_DIR),
        default=_SOURCE_YFINANCE,
        help="OHLCV data source. Default: yfinance.",
    )
    parser.add_argument(
        "--source-dir",
        default=None,
        help=(
            "Local OHLCV CSV directory for --source csv-dir. "
            "Expected files: <SYMBOL>.csv with date or timestamp, open, high, low, close, volume."
        ),
    )
    parser.add_argument(
        "--annotate-signals",
        action="store_true",
        default=False,
        help=(
            "Run TurtleStrategy rolling-window signal generation on the fetched OHLCV data. "
            "Embeds turtle_research annotation and signals array in each snapshot. "
            "Writes *_turtle_annotated.json (annotated snapshots) and "
            "*_turtle_research.json (signal frequency analysis)."
        ),
    )
    parser.add_argument(
        "--no-ssl-verify",
        action="store_true",
        default=False,
        help=(
            "Disable SSL certificate verification for yfinance downloads. "
            "Use only in environments where the CA chain is unavailable (e.g. Windows dev)."
        ),
    )
    return parser.parse_args()


def _build_command(args: argparse.Namespace) -> str:
    parts = [
        "python scripts/export_historical_snapshots.py",
        f"--symbols {args.symbols}",
        f"--start {args.start}",
        f"--end {args.end}",
        f"--out {args.out}",
    ]
    if getattr(args, "source", _SOURCE_YFINANCE) != _SOURCE_YFINANCE:
        parts.append(f"--source {args.source}")
    if getattr(args, "source_dir", None):
        parts.append(f"--source-dir {args.source_dir}")
    if getattr(args, "annotate_signals", False):
        parts.append("--annotate-signals")
    return " ".join(parts)


def main() -> int:
    args = _parse_args()

    global _SSL_VERIFY

    # Build optional curl_cffi session for SSL bypass before yfinance is imported.
    yf_session = None
    if getattr(args, "no_ssl_verify", False):
        _SSL_VERIFY = False
        try:
            from curl_cffi import requests as _curl_requests
            yf_session = _curl_requests.Session(verify=False)
        except ImportError:
            pass  # fallback: no session; SSL errors will surface per-symbol

    try:
        start = date.fromisoformat(args.start)
        end = date.fromisoformat(args.end)
    except ValueError as exc:
        print(f"Invalid date: {exc}", file=sys.stderr)
        return 2

    if end < start:
        print("--end must not be before --start", file=sys.stderr)
        return 2

    symbols = tuple(s.strip().upper() for s in args.symbols.split(",") if s.strip())
    if not symbols:
        print("No symbols specified.", file=sys.stderr)
        return 2
    source_dir = Path(args.source_dir) if args.source_dir else None
    if args.source == _SOURCE_CSV_DIR and source_dir is None:
        print("--source-dir is required when --source csv-dir", file=sys.stderr)
        return 2

    out_dir = Path(args.out)
    date_tag = f"{start.strftime(_SNAPSHOT_DATE_FMT)}_{end.strftime(_SNAPSHOT_DATE_FMT)}"
    snapshots_path = out_dir / f"historical_snapshots_{date_tag}.json"
    meta_path = out_dir / f"historical_snapshots_{date_tag}_meta.json"

    command = _build_command(args)
    print(f"Fetching OHLCV data for: {', '.join(symbols)}", flush=True)
    print(f"Source : {args.source}", flush=True)
    if source_dir is not None:
        print(f"Source dir : {source_dir}", flush=True)
    snapshots, metadata = build_export(
        symbols,
        start,
        end,
        command=command,
        session=yf_session,
        source=args.source,
        source_dir=source_dir,
    )

    _write_json(snapshots_path, snapshots)
    _write_json(meta_path, metadata)

    print(f"Snapshots : {snapshots_path}")
    print(f"Metadata  : {meta_path}")
    print(f"Total snapshots : {metadata['total_snapshot_count']}")
    print(f"Missing symbols : {metadata['missing_symbols'] or 'none'}")
    for sym, cov in metadata["symbol_coverage"].items():
        print(f"  {sym}: {cov['snapshot_count']} bars")

    if getattr(args, "annotate_signals", False):
        print("\nRunning TURTLE rolling-window signal annotation...", flush=True)

        # Rebuild per_symbol index from snapshots for annotation
        per_symbol: dict[str, list[dict[str, Any]]] = {}
        for snap in snapshots:
            sym = snap.get("symbol", "")
            per_symbol.setdefault(sym, []).append(snap)

        annotations = generate_turtle_signal_annotations(per_symbol)
        annotated = annotate_snapshots(snapshots, annotations)
        summary = build_turtle_research_summary(annotations)

        annotated_path = out_dir / f"historical_snapshots_{date_tag}_turtle_annotated.json"
        research_path = out_dir / f"historical_snapshots_{date_tag}_turtle_research.json"

        _write_json(annotated_path, annotated)
        _write_json(research_path, summary)

        print(f"Annotated : {annotated_path}")
        print(f"Research  : {research_path}")

        totals = summary["totals"]
        print(f"\nTURTLE signal summary ({date_tag}):")
        print(f"  Total bars       : {totals['total_bars']}")
        print(f"  Signals produced : {totals['signals_produced']}")
        print(f"    entry_confirmed: {totals['entry_confirmed_count']}")
        print(f"    setup          : {totals['setup_count']}")
        print(f"    exit           : {totals['exit_count']}")
        print(f"  Research threshold candidates : {totals['research_threshold_candidates']}")
        print(f"  Score-blocked    : {totals['score_blocked_count']}")
        print(
            "  Raw trade-risk research exceeded : "
            f"{totals['raw_trade_risk_research_exceeded_count']}"
        )

        print("\nPer-symbol breakdown:")
        for sym, data in sorted(summary["by_symbol"].items()):
            stages = data["stages"]
            print(
                f"  {sym}: signals={data['signals_produced']}/{data['total_bars']} bars  "
                f"entry_confirmed={stages['entry_confirmed']}  "
                f"setup={stages['setup']}  "
                f"exit={stages['exit']}  "
                f"score_blocked={data['score_blocked_count']}  "
                "raw_trade_risk_research_exceeded="
                f"{data['raw_trade_risk_research_exceeded_count']}  "
                f"score_min={data.get('score_min')}  "
                f"score_max={data.get('score_max')}"
            )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

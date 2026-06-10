"""Export deterministic historical multi-asset snapshots for TURTLE research.

Produces a backtest-compatible JSON snapshot array accepted by:
  python -m cilly_trading backtest --snapshots <PATH> ...

Usage:
  python scripts/export_historical_snapshots.py \\
      --symbols AAPL,MSFT,NVDA,GS,WMT,COST \\
      --start 2023-01-01 \\
      --end   2023-12-31 \\
      --out   data/artifacts/historical_snapshots

Outputs two files under <out>/:
  historical_snapshots_<start>_<end>.json   -- backtest-compatible snapshot array
  historical_snapshots_<start>_<end>_meta.json -- lineage / coverage metadata
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import date, datetime, timezone
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
) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Return (snapshots, metadata) for the given symbol universe and date range."""
    per_symbol: dict[str, list[dict[str, Any]]] = {}
    missing_symbols: list[str] = []
    actual_start: date | None = None
    actual_end: date | None = None

    for symbol in sorted(symbols):
        rows = _fetch_symbol(symbol, start, end, session=session)
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
            "missing_ohlcv_rows": sum(
                1 for r in rows
                if any(r.get(f) is None for f in ("open", "high", "low", "close", "volume"))
            ),
        }

    metadata: dict[str, Any] = {
        "artifact_type": "historical_multi_asset_snapshot_export",
        "data_source": "yfinance",
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
        description="Export deterministic historical multi-asset snapshots for TURTLE backtest research.",
    )
    parser.add_argument(
        "--symbols",
        default=",".join(GOVERNED_SYMBOLS),
        help=(
            f"Comma-separated symbol list. Default: {','.join(GOVERNED_SYMBOLS)}."
        ),
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
    return (
        f"python scripts/export_historical_snapshots.py "
        f"--symbols {args.symbols} "
        f"--start {args.start} "
        f"--end {args.end} "
        f"--out {args.out}"
    )


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

    out_dir = Path(args.out)
    date_tag = f"{start.strftime(_SNAPSHOT_DATE_FMT)}_{end.strftime(_SNAPSHOT_DATE_FMT)}"
    snapshots_path = out_dir / f"historical_snapshots_{date_tag}.json"
    meta_path = out_dir / f"historical_snapshots_{date_tag}_meta.json"

    command = _build_command(args)
    print(f"Fetching OHLCV data for: {', '.join(symbols)}", flush=True)
    snapshots, metadata = build_export(symbols, start, end, command=command, session=yf_session)

    _write_json(snapshots_path, snapshots)
    _write_json(meta_path, metadata)

    print(f"Snapshots : {snapshots_path}")
    print(f"Metadata  : {meta_path}")
    print(f"Total snapshots : {metadata['total_snapshot_count']}")
    print(f"Missing symbols : {metadata['missing_symbols'] or 'none'}")
    for sym, cov in metadata["symbol_coverage"].items():
        print(f"  {sym}: {cov['snapshot_count']} bars")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

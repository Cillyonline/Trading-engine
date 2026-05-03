#!/usr/bin/env python3
"""Offline CLI tool for data quality reports.

Usage:
    python scripts/data_quality_report.py --symbol AAPL --bars-file bars.json
    python scripts/data_quality_report.py --symbol AAPL --bars-file bars.json --sigma 3.0
    python scripts/data_quality_report.py --symbol AAPL --bars-file bars.json --output report.json

Produces the same output as GET /data/quality/{symbol} for the same underlying data.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Compute a data quality report for ingested market data. "
            "Produces the same output as GET /data/quality/{symbol}."
        )
    )
    parser.add_argument("--symbol", required=True, help="Symbol to report on (e.g. AAPL)")
    parser.add_argument(
        "--bars-file",
        required=True,
        type=Path,
        help="Path to a JSON file containing a list of bar dicts (timestamp, open, high, low, close).",
    )
    parser.add_argument(
        "--sigma",
        type=float,
        default=5.0,
        help="Standard deviation threshold for outlier detection (default: 5.0).",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Write report JSON to this file (default: stdout).",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        raw = args.bars_file.read_text(encoding="utf-8")
    except OSError as exc:
        print(f"Error reading bars file: {exc}", file=sys.stderr)
        return 1

    try:
        bars = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"Error parsing bars JSON: {exc}", file=sys.stderr)
        return 1

    if not isinstance(bars, list):
        print("bars-file must contain a JSON array of bar objects", file=sys.stderr)
        return 1

    from cilly_trading.engine.data_quality import compute_data_quality_report  # noqa: PLC0415

    report = compute_data_quality_report(
        symbol=args.symbol.strip().upper(),
        bars=bars,
        sigma_threshold=args.sigma,
    )
    output = json.dumps(report.to_dict(), sort_keys=True, separators=(",", ":"), indent=2)

    if args.output is not None:
        try:
            args.output.write_text(output + "\n", encoding="utf-8")
            print(f"WROTE {args.output}")
        except OSError as exc:
            print(f"Error writing output: {exc}", file=sys.stderr)
            return 1
    else:
        print(output)

    return 0


if __name__ == "__main__":
    sys.exit(main())

"""Tests for scripts/export_historical_snapshots.py.

Covers:
- deterministic ordering (timestamp, id)
- required backtest-contract fields (id, timestamp) on every snapshot
- symbol identity preserved in each snapshot object
- OHLCV fields preserved where data is present
- missing-symbol reporting
- metadata: requested/actual date ranges, symbol coverage, total count
- duplicate-ID deduplication
- content_sha256 is stable across identical inputs
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

# ---------------------------------------------------------------------------
# Load the module under test without executing __main__
# ---------------------------------------------------------------------------
_SCRIPT = ROOT / "scripts" / "export_historical_snapshots.py"


def _load_module():
    spec = importlib.util.spec_from_file_location("export_historical_snapshots", _SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


_mod = _load_module()
build_export = _mod.build_export
_snapshot_id = _mod._snapshot_id
GOVERNED_SYMBOLS = _mod.GOVERNED_SYMBOLS


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(symbol: str, date_str: str, *, px: float = 100.0) -> dict[str, Any]:
    """Produce a minimal OHLCV snapshot dict as returned by build_export."""
    return {
        "id": f"{symbol}_{date_str}",
        "timestamp": f"{date_str}T00:00:00Z",
        "symbol": symbol,
        "open": str(px),
        "high": str(px + 1),
        "low": str(px - 1),
        "close": str(px),
        "volume": "1000000",
        "timeframe": "D1",
    }


def _fake_fetch(symbol_rows: dict[str, list[dict[str, Any]]]):
    """Return a _fetch_symbol replacement that returns pre-canned rows."""
    def _fetch(symbol: str, start: date, end: date, *, session=None):
        return list(symbol_rows.get(symbol, []))
    return _fetch


# ---------------------------------------------------------------------------
# Snapshot ID contract
# ---------------------------------------------------------------------------

def test_snapshot_id_format():
    sid = _snapshot_id("AAPL", date(2023, 1, 3))
    assert sid == "AAPL_2023-01-03"


# ---------------------------------------------------------------------------
# Required backtest-contract fields
# ---------------------------------------------------------------------------

def test_all_snapshots_have_id_and_timestamp():
    rows = {
        "AAPL": [_make_bar("AAPL", "2023-01-03"), _make_bar("AAPL", "2023-01-04")],
        "MSFT": [_make_bar("MSFT", "2023-01-03")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, _ = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 4), command="test"
        )
    for snap in snapshots:
        assert isinstance(snap.get("id"), str) and snap["id"].strip()
        assert isinstance(snap.get("timestamp"), str) and snap["timestamp"].strip()


# ---------------------------------------------------------------------------
# Symbol identity preserved
# ---------------------------------------------------------------------------

def test_symbol_field_preserved():
    rows = {
        "NVDA": [_make_bar("NVDA", "2023-01-03")],
        "GS":   [_make_bar("GS",   "2023-01-03")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, _ = build_export(
            ("NVDA", "GS"), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    symbols_seen = {s["symbol"] for s in snapshots}
    assert "NVDA" in symbols_seen
    assert "GS" in symbols_seen


# ---------------------------------------------------------------------------
# OHLCV fields preserved
# ---------------------------------------------------------------------------

def test_ohlcv_fields_present():
    rows = {"AAPL": [_make_bar("AAPL", "2023-01-03", px=150.0)]}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, _ = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    snap = snapshots[0]
    for field in ("open", "high", "low", "close", "volume"):
        assert field in snap, f"Missing field: {field}"


# ---------------------------------------------------------------------------
# Deterministic ordering
# ---------------------------------------------------------------------------

def test_deterministic_ordering_by_timestamp_then_id():
    # Same timestamp, different symbols -> sorted by id
    rows = {
        "WMT":  [_make_bar("WMT",  "2023-01-03")],
        "AAPL": [_make_bar("AAPL", "2023-01-03")],
        "MSFT": [_make_bar("MSFT", "2023-01-03")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, _ = build_export(
            ("WMT", "AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    ids = [s["id"] for s in snapshots]
    assert ids == sorted(ids), f"Not sorted: {ids}"


def test_deterministic_ordering_by_timestamp_across_days():
    rows = {
        "AAPL": [
            _make_bar("AAPL", "2023-01-05"),
            _make_bar("AAPL", "2023-01-03"),
            _make_bar("AAPL", "2023-01-04"),
        ],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, _ = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 5), command="test"
        )
    timestamps = [s["timestamp"] for s in snapshots]
    assert timestamps == sorted(timestamps)


def test_identical_inputs_produce_identical_output():
    rows = {
        "AAPL": [_make_bar("AAPL", "2023-01-03"), _make_bar("AAPL", "2023-01-04")],
        "MSFT": [_make_bar("MSFT", "2023-01-03")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snaps1, meta1 = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 4), command="test"
        )
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snaps2, meta2 = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 4), command="test"
        )
    assert snaps1 == snaps2
    assert meta1["content_sha256"] == meta2["content_sha256"]


# ---------------------------------------------------------------------------
# Missing-symbol reporting
# ---------------------------------------------------------------------------

def test_missing_symbol_reported_in_metadata():
    rows = {
        "AAPL": [_make_bar("AAPL", "2023-01-03")],
        "MSFT": [],  # no data
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    assert "MSFT" in meta["missing_symbols"]
    assert meta["symbol_coverage"]["MSFT"]["missing"] is True
    assert meta["symbol_coverage"]["MSFT"]["snapshot_count"] == 0


# ---------------------------------------------------------------------------
# Metadata: date ranges and coverage
# ---------------------------------------------------------------------------

def test_metadata_symbol_universe_sorted():
    rows = {sym: [] for sym in GOVERNED_SYMBOLS}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            GOVERNED_SYMBOLS, date(2023, 1, 3), date(2023, 1, 31), command="test"
        )
    assert meta["symbol_universe"] == sorted(GOVERNED_SYMBOLS)


def test_metadata_requested_date_range():
    rows = {"AAPL": [_make_bar("AAPL", "2023-01-03")]}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 31), command="test"
        )
    assert meta["requested_date_range"]["start"] == "2023-01-03"
    assert meta["requested_date_range"]["end"] == "2023-01-31"


def test_metadata_actual_date_range():
    rows = {
        "AAPL": [_make_bar("AAPL", "2023-01-03"), _make_bar("AAPL", "2023-01-05")],
        "MSFT": [_make_bar("MSFT", "2023-01-04")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 5), command="test"
        )
    assert meta["actual_date_range"]["start"] == "2023-01-03"
    assert meta["actual_date_range"]["end"] == "2023-01-05"


def test_metadata_total_snapshot_count():
    rows = {
        "AAPL": [_make_bar("AAPL", "2023-01-03"), _make_bar("AAPL", "2023-01-04")],
        "MSFT": [_make_bar("MSFT", "2023-01-03")],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, meta = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 4), command="test"
        )
    assert meta["total_snapshot_count"] == len(snapshots) == 3


def test_metadata_data_source():
    rows = {"AAPL": [_make_bar("AAPL", "2023-01-03")]}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    assert meta["data_source"] == "yfinance"


# ---------------------------------------------------------------------------
# Backtest-contract compatibility flag
# ---------------------------------------------------------------------------

def test_metadata_backtest_contract_compatible():
    rows = {"AAPL": [_make_bar("AAPL", "2023-01-03")]}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    assert meta["backtest_contract"]["compatible"] is True


# ---------------------------------------------------------------------------
# Deduplication
# ---------------------------------------------------------------------------

def test_duplicate_ids_deduplicated():
    bar = _make_bar("AAPL", "2023-01-03")
    rows = {"AAPL": [bar, bar]}  # intentional duplicate
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, meta = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    ids = [s["id"] for s in snapshots]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# All six governed symbols pass required field check
# ---------------------------------------------------------------------------

def test_governed_symbol_universe_all_present():
    rows = {sym: [_make_bar(sym, "2023-01-03")] for sym in GOVERNED_SYMBOLS}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, meta = build_export(
            GOVERNED_SYMBOLS, date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    assert meta["missing_symbols"] == []
    assert meta["total_snapshot_count"] == len(GOVERNED_SYMBOLS)
    for sym in GOVERNED_SYMBOLS:
        assert meta["symbol_coverage"][sym]["snapshot_count"] == 1

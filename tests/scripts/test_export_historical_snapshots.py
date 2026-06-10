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
- TURTLE signal annotation: generate_turtle_signal_annotations
- TURTLE annotation embedding: annotate_snapshots
- build_turtle_research_summary structure and accuracy
- score_blocked / risk_blocked / is_entry_candidate flags
- signals array embedded for entry_confirmed bars
- research summary totals
"""

from __future__ import annotations

import importlib.util
import json
import sys
from datetime import date, datetime, timezone
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
generate_turtle_signal_annotations = _mod.generate_turtle_signal_annotations
annotate_snapshots = _mod.annotate_snapshots
build_turtle_research_summary = _mod.build_turtle_research_summary
_build_signals_array = _mod._build_signals_array
_MIN_SCORE_THRESHOLD = _mod._MIN_SCORE_THRESHOLD
_MAX_RISK_PER_TRADE_PCT = _mod._MAX_RISK_PER_TRADE_PCT


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_bar(symbol: str, date_str: str, *, px: float = 100.0) -> dict[str, Any]:
    """Minimal OHLCV snapshot dict as returned by build_export."""
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


def _make_trending_bars(symbol: str, n: int = 30) -> list[dict[str, Any]]:
    """Create n bars designed to trigger TURTLE entry_confirmed.

    First 21 bars: flat at 100.0 (high=100.5) to establish the rolling window.
    Bars 22+: close rises well above 100.5 to exceed the prior 20-bar highest high.
    """
    rows = []
    base = 100.0
    import datetime as _dt
    for i in range(n):
        d = date(2023, 1, 1) + _dt.timedelta(days=i)
        date_str = d.strftime("%Y-%m-%d")
        if i < 21:
            # Flat — establish a 20-bar window with high=100.5
            px = base
            hi = px + 0.5
            lo = px - 0.5
            cl = px
        else:
            # Sharp breakout: close clearly exceeds the prior 20-bar high of 100.5
            px = base * 1.05  # 105.0 — well above 100.5
            hi = px + 0.5
            lo = px - 0.5
            cl = px
        rows.append({
            "id": f"{symbol}_{date_str}",
            "timestamp": f"{date_str}T00:00:00Z",
            "symbol": symbol,
            "open": str(round(px, 6)),
            "high": str(round(hi, 6)),
            "low": str(round(lo, 6)),
            "close": str(round(cl, 6)),
            "volume": "1000000",
            "timeframe": "D1",
        })
    return rows


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
        "MSFT": [],
    }
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        _, meta = build_export(
            ("AAPL", "MSFT"), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    assert "MSFT" in meta["missing_symbols"]
    assert meta["symbol_coverage"]["MSFT"]["missing"] is True
    assert meta["symbol_coverage"]["MSFT"]["snapshot_count"] == 0


# ---------------------------------------------------------------------------
# Metadata correctness
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
    rows = {"AAPL": [bar, bar]}
    with patch.object(_mod, "_fetch_symbol", side_effect=_fake_fetch(rows)):
        snapshots, meta = build_export(
            ("AAPL",), date(2023, 1, 3), date(2023, 1, 3), command="test"
        )
    ids = [s["id"] for s in snapshots]
    assert len(ids) == len(set(ids))


# ---------------------------------------------------------------------------
# All six governed symbols
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


# ===========================================================================
# TURTLE signal annotation tests
# ===========================================================================

class TestGenerateTurtleSignalAnnotations:
    """Tests for generate_turtle_signal_annotations (rolling window signal gen)."""

    def test_empty_symbol_produces_no_annotations(self):
        anns = generate_turtle_signal_annotations({"AAPL": []})
        assert anns == {}

    def test_insufficient_history_produces_no_signal(self):
        # Fewer than breakout_lookback+1 bars → no signal
        rows = [_make_bar("AAPL", f"2023-01-0{i+1}") for i in range(5)]
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        for ann in anns.values():
            assert ann["signal_produced"] is False

    def test_annotation_has_required_fields(self):
        rows = _make_trending_bars("AAPL", n=30)
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        assert len(anns) == 30
        required = {
            "symbol", "timestamp", "strategy", "signal_produced",
            "stage", "score", "score_bucket", "direction", "signal_id",
            "confirmation_rule", "entry_zone", "stop_loss", "trade_risk_pct",
            "score_blocked", "risk_blocked", "is_entry_candidate",
        }
        for ann in anns.values():
            assert required.issubset(ann.keys()), f"Missing keys: {required - ann.keys()}"

    def test_strategy_field_is_turtle(self):
        rows = _make_trending_bars("AAPL", n=25)
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        for ann in anns.values():
            assert ann["strategy"] == "TURTLE"

    def test_signal_id_is_deterministic(self):
        rows = _make_trending_bars("AAPL", n=25)
        anns1 = generate_turtle_signal_annotations({"AAPL": rows})
        anns2 = generate_turtle_signal_annotations({"AAPL": rows})
        for snap_id in anns1:
            assert anns1[snap_id]["signal_id"] == anns2[snap_id]["signal_id"]

    def test_entry_confirmed_signal_detected(self):
        """Breakout sequence produces at least one entry_confirmed annotation."""
        rows = _make_trending_bars("AAPL", n=30)
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        stages = [a["stage"] for a in anns.values() if a["signal_produced"]]
        assert "entry_confirmed" in stages

    def test_score_blocked_flag_set_when_score_below_threshold(self):
        """entry_confirmed signals with score < 60 must have score_blocked=True."""
        rows = _make_trending_bars("AAPL", n=30)
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        for ann in anns.values():
            if ann["stage"] == "entry_confirmed" and ann["score"] is not None:
                if ann["score"] < _MIN_SCORE_THRESHOLD:
                    assert ann["score_blocked"] is True
                else:
                    assert ann["score_blocked"] is False

    def test_non_entry_confirmed_stages_not_score_blocked(self):
        """setup and exit signals never have score_blocked=True."""
        rows = _make_trending_bars("AAPL", n=30)
        anns = generate_turtle_signal_annotations({"AAPL": rows})
        for ann in anns.values():
            if ann["stage"] in ("setup", "exit"):
                assert ann["score_blocked"] is False

    def test_risk_blocked_when_trade_risk_pct_exceeds_max(self):
        """Annotation risk_blocked=True when trade_risk_pct > max_risk_per_trade_pct."""
        # Create a signal with very large trade_risk_pct by using large stop_loss_buffer
        rows = _make_trending_bars("AAPL", n=30)
        # Use large stop_loss_buffer_pct so trade_risk_pct is large
        cfg = {"stop_loss_buffer_pct": 0.50}
        anns = generate_turtle_signal_annotations({"AAPL": rows}, cfg)
        setup_with_risk = [
            a for a in anns.values()
            if a["stage"] == "setup" and a.get("trade_risk_pct") is not None
        ]
        if setup_with_risk:
            for ann in setup_with_risk:
                if ann["trade_risk_pct"] > _MAX_RISK_PER_TRADE_PCT:
                    assert ann["risk_blocked"] is True

    def test_multiple_symbols(self):
        rows_aapl = _make_trending_bars("AAPL", n=25)
        rows_msft = _make_trending_bars("MSFT", n=25)
        anns = generate_turtle_signal_annotations({"AAPL": rows_aapl, "MSFT": rows_msft})
        symbols_in_anns = {a["symbol"] for a in anns.values()}
        assert "AAPL" in symbols_in_anns
        assert "MSFT" in symbols_in_anns


class TestBuildSignalsArray:
    """Tests for _build_signals_array (backtest signals embedding)."""

    def _entry_confirmed_annotation(self, score: float = 65.0) -> dict[str, Any]:
        return {
            "signal_produced": True,
            "stage": "entry_confirmed",
            "score": score,
            "trade_risk_pct": None,
            "signal_id": "test-signal-id",
            "symbol": "AAPL",
            "strategy": "TURTLE",
        }

    def test_returns_empty_for_no_signal(self):
        ann = {"signal_produced": False, "stage": None, "score": None, "trade_risk_pct": None}
        result = _build_signals_array(
            ann,
            min_score_threshold=_MIN_SCORE_THRESHOLD,
            max_risk_per_trade_pct=_MAX_RISK_PER_TRADE_PCT,
        )
        assert result == []

    def test_returns_empty_for_setup_stage(self):
        ann = {
            "signal_produced": True, "stage": "setup", "score": 70.0,
            "trade_risk_pct": 0.005, "signal_id": "x", "symbol": "AAPL",
        }
        result = _build_signals_array(
            ann,
            min_score_threshold=_MIN_SCORE_THRESHOLD,
            max_risk_per_trade_pct=_MAX_RISK_PER_TRADE_PCT,
        )
        assert result == []

    def test_returns_empty_for_exit_stage(self):
        ann = {
            "signal_produced": True, "stage": "exit", "score": 100.0,
            "trade_risk_pct": None, "signal_id": "x", "symbol": "AAPL",
        }
        result = _build_signals_array(
            ann,
            min_score_threshold=_MIN_SCORE_THRESHOLD,
            max_risk_per_trade_pct=_MAX_RISK_PER_TRADE_PCT,
        )
        assert result == []

    def test_entry_confirmed_above_threshold_approved(self):
        ann = self._entry_confirmed_annotation(score=65.0)
        result = _build_signals_array(
            ann,
            min_score_threshold=60.0,
            max_risk_per_trade_pct=0.01,
        )
        assert len(result) == 1
        sig = result[0]
        assert sig["risk_evidence"]["decision"] == "APPROVED"
        assert sig["action"] == "BUY"
        assert sig["quantity"] == "1"
        assert sig["symbol"] == "AAPL"
        assert sig["signal_id"] == "test-signal-id"

    def test_entry_confirmed_below_threshold_rejected(self):
        ann = self._entry_confirmed_annotation(score=58.0)
        result = _build_signals_array(
            ann,
            min_score_threshold=60.0,
            max_risk_per_trade_pct=0.01,
        )
        assert len(result) == 1
        sig = result[0]
        assert sig["risk_evidence"]["decision"] == "REJECTED"
        assert "min_score_threshold" in sig["risk_evidence"]["reason"]

    def test_entry_confirmed_risk_exceeds_gate_rejected(self):
        ann = self._entry_confirmed_annotation(score=80.0)
        ann["trade_risk_pct"] = 0.05  # exceeds max_risk_per_trade_pct=0.01
        result = _build_signals_array(
            ann,
            min_score_threshold=60.0,
            max_risk_per_trade_pct=0.01,
        )
        assert len(result) == 1
        assert result[0]["risk_evidence"]["decision"] == "REJECTED"
        assert "max_risk_per_trade_pct" in result[0]["risk_evidence"]["reason"]

    def test_required_risk_evidence_fields(self):
        ann = self._entry_confirmed_annotation(score=65.0)
        result = _build_signals_array(
            ann,
            min_score_threshold=60.0,
            max_risk_per_trade_pct=0.01,
        )
        ev = result[0]["risk_evidence"]
        for field in ("decision", "max_allowed", "reason", "rule_version", "score"):
            assert field in ev, f"Missing risk_evidence field: {field}"


class TestAnnotateSnapshots:
    """Tests for annotate_snapshots (embedding turtle_research into snapshot list)."""

    def test_turtle_research_embedded_in_every_snapshot(self):
        snaps = [_make_bar("AAPL", "2023-01-03"), _make_bar("AAPL", "2023-01-04")]
        anns: dict[str, Any] = {}
        result = annotate_snapshots(snaps, anns)
        for s in result:
            assert "turtle_research" in s

    def test_original_snapshots_not_mutated(self):
        snap = _make_bar("AAPL", "2023-01-03")
        original_keys = set(snap.keys())
        annotate_snapshots([snap], {})
        assert set(snap.keys()) == original_keys

    def test_signals_array_embedded_for_approved_entry_confirmed(self):
        snap_id = "AAPL_2023-01-03"
        snap = _make_bar("AAPL", "2023-01-03")
        snap["id"] = snap_id
        anns = {
            snap_id: {
                "symbol": "AAPL",
                "timestamp": "2023-01-03T00:00:00Z",
                "strategy": "TURTLE",
                "signal_produced": True,
                "stage": "entry_confirmed",
                "score": 70.0,
                "score_bucket": "60-79",
                "direction": "long",
                "signal_id": "abc123",
                "confirmation_rule": "test",
                "entry_zone": None,
                "stop_loss": None,
                "trade_risk_pct": None,
                "score_blocked": False,
                "risk_blocked": False,
                "is_entry_candidate": True,
            }
        }
        result = annotate_snapshots([snap], anns)
        assert "signals" in result[0]
        assert result[0]["signals"][0]["action"] == "BUY"

    def test_no_signals_array_for_setup_stage(self):
        snap_id = "AAPL_2023-01-03"
        snap = _make_bar("AAPL", "2023-01-03")
        snap["id"] = snap_id
        anns = {
            snap_id: {
                "symbol": "AAPL",
                "timestamp": "2023-01-03T00:00:00Z",
                "strategy": "TURTLE",
                "signal_produced": True,
                "stage": "setup",
                "score": 70.0,
                "score_bucket": "60-79",
                "direction": "long",
                "signal_id": "abc123",
                "confirmation_rule": None,
                "entry_zone": None,
                "stop_loss": None,
                "trade_risk_pct": 0.005,
                "score_blocked": False,
                "risk_blocked": False,
                "is_entry_candidate": False,
            }
        }
        result = annotate_snapshots([snap], anns)
        assert "signals" not in result[0]

    def test_ohlcv_fields_preserved_after_annotation(self):
        snap = _make_bar("AAPL", "2023-01-03", px=150.0)
        result = annotate_snapshots([snap], {})
        for field in ("open", "high", "low", "close", "volume", "id", "timestamp"):
            assert result[0][field] == snap[field]


class TestBuildTurtleResearchSummary:
    """Tests for build_turtle_research_summary."""

    def _make_annotations(self) -> dict[str, dict[str, Any]]:
        return {
            "AAPL_2023-01-03": {
                "symbol": "AAPL", "signal_produced": True, "stage": "entry_confirmed",
                "score": 65.0, "score_bucket": "60-79",
                "score_blocked": False, "risk_blocked": False, "is_entry_candidate": True,
            },
            "AAPL_2023-01-04": {
                "symbol": "AAPL", "signal_produced": True, "stage": "setup",
                "score": 55.0, "score_bucket": "40-59",
                "score_blocked": False, "risk_blocked": False, "is_entry_candidate": False,
            },
            "AAPL_2023-01-05": {
                "symbol": "AAPL", "signal_produced": False, "stage": None,
                "score": None, "score_bucket": None,
                "score_blocked": False, "risk_blocked": False, "is_entry_candidate": False,
            },
            "GS_2023-01-03": {
                "symbol": "GS", "signal_produced": True, "stage": "entry_confirmed",
                "score": 62.0, "score_bucket": "60-79",
                "score_blocked": False, "risk_blocked": True, "is_entry_candidate": False,
            },
        }

    def test_required_top_level_fields(self):
        summary = build_turtle_research_summary(self._make_annotations())
        for key in ("artifact_type", "strategy", "min_score_threshold_applied",
                    "max_risk_per_trade_pct_applied", "by_symbol", "totals", "traceability"):
            assert key in summary

    def test_totals_counts(self):
        summary = build_turtle_research_summary(self._make_annotations())
        t = summary["totals"]
        assert t["total_bars"] == 4
        assert t["signals_produced"] == 3
        assert t["entry_confirmed_count"] == 2
        assert t["setup_count"] == 1
        assert t["exit_count"] == 0
        assert t["entry_candidates"] == 1
        assert t["risk_blocked_count"] == 1

    def test_by_symbol_aapl(self):
        summary = build_turtle_research_summary(self._make_annotations())
        aapl = summary["by_symbol"]["AAPL"]
        assert aapl["total_bars"] == 3
        assert aapl["signals_produced"] == 2
        assert aapl["stages"]["entry_confirmed"] == 1
        assert aapl["stages"]["setup"] == 1
        assert aapl["entry_candidates"] == 1
        assert aapl["score_min"] == 55.0
        assert aapl["score_max"] == 65.0

    def test_thresholds_recorded(self):
        summary = build_turtle_research_summary(
            self._make_annotations(),
            min_score_threshold=60.0,
            max_risk_per_trade_pct=0.01,
        )
        assert summary["min_score_threshold_applied"] == 60.0
        assert summary["max_risk_per_trade_pct_applied"] == 0.01

    def test_empty_annotations(self):
        summary = build_turtle_research_summary({})
        assert summary["totals"]["total_bars"] == 0
        assert summary["totals"]["signals_produced"] == 0
        assert summary["by_symbol"] == {}

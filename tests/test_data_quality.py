"""Tests for data quality report (Issue #1099)."""

from __future__ import annotations

import json
import math
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from fastapi import FastAPI

from cilly_trading.engine.data_quality import (
    DataQualityReport,
    GapRecord,
    compute_data_quality_report,
)
from api.routers.data_quality_router import build_data_quality_router


_DAY = 86_400  # seconds


# ── Helpers ───────────────────────────────────────────────────────────────────


def _bars(n: int, start_ts: float = 0.0, step: float = _DAY, base_price: float = 100.0) -> list[dict]:
    """Generate clean OHLCV bars at fixed intervals."""
    result = []
    price = base_price
    for i in range(n):
        result.append({
            "timestamp": start_ts + i * step,
            "open": price,
            "high": price + 1.0,
            "low": price - 1.0,
            "close": price,
            "volume": 1_000_000,
        })
        price += 0.5  # gentle uptrend
    return result


def _bars_with_gap(n: int, gap_after_idx: int, gap_days: int = 5) -> list[dict]:
    """Bars with a known gap of gap_days after gap_after_idx."""
    bars = _bars(n)
    gap_secs = gap_days * _DAY
    for i in range(gap_after_idx + 1, len(bars)):
        bars[i]["timestamp"] += gap_secs
    return bars


def _bars_with_outlier(n: int, outlier_idx: int, spike_factor: float = 20.0) -> list[dict]:
    """Bars with one extreme price spike at outlier_idx."""
    bars = _bars(n)
    bars[outlier_idx]["close"] = bars[outlier_idx]["close"] * spike_factor
    bars[outlier_idx]["high"] = bars[outlier_idx]["close"]
    return bars


# ── compute_data_quality_report: clean data ───────────────────────────────────


def test_clean_data_returns_no_data_false() -> None:
    report = compute_data_quality_report(symbol="AAPL", bars=_bars(30))
    assert report.no_data is False


def test_empty_bars_returns_no_data_true() -> None:
    report = compute_data_quality_report(symbol="AAPL", bars=[])
    assert report.no_data is True
    assert report.total_bars == 0


def test_total_bars_matches_input_count() -> None:
    report = compute_data_quality_report(symbol="AAPL", bars=_bars(50))
    assert report.total_bars == 50


def test_clean_data_has_no_gaps() -> None:
    report = compute_data_quality_report(symbol="AAPL", bars=_bars(30))
    assert report.gaps == []


def test_clean_data_has_zero_outliers() -> None:
    report = compute_data_quality_report(symbol="AAPL", bars=_bars(30))
    assert report.outlier_count == 0


def test_date_range_matches_first_and_last_bar() -> None:
    bars = _bars(10, start_ts=1_000_000.0)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert report.date_range is not None
    assert abs(report.date_range.first_bar - 1_000_000.0) < 1.0
    assert abs(report.date_range.last_bar - (1_000_000.0 + 9 * _DAY)) < 1.0


def test_symbol_preserved_in_report() -> None:
    report = compute_data_quality_report(symbol="MSFT", bars=_bars(5))
    assert report.symbol == "MSFT"


def test_sigma_threshold_preserved_in_report() -> None:
    report = compute_data_quality_report(symbol="X", bars=_bars(10), sigma_threshold=3.0)
    assert report.sigma_threshold == 3.0


# ── Gaps ─────────────────────────────────────────────────────────────────────


def test_known_gap_is_detected() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14, gap_days=5)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert len(report.gaps) >= 1


def test_detected_gap_has_correct_boundary_order() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14, gap_days=5)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    for gap in report.gaps:
        assert gap.end_ts > gap.start_ts


def test_detected_gap_duration_bars_is_positive() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14, gap_days=5)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    for gap in report.gaps:
        assert gap.duration_bars >= 1


def test_no_spurious_gaps_in_clean_data() -> None:
    bars = _bars(50)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert report.gaps == []


def test_missing_bars_count_reflects_gap() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14, gap_days=5)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert report.missing_bars_count > 0


def test_missing_bars_pct_is_none_when_no_data() -> None:
    report = compute_data_quality_report(symbol="X", bars=[])
    assert report.missing_bars_pct is None


def test_missing_bars_pct_is_between_zero_and_one_for_gapped_data() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14, gap_days=5)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    if report.missing_bars_pct is not None:
        assert 0.0 <= report.missing_bars_pct <= 1.0


# ── Outlier detection ─────────────────────────────────────────────────────────


def test_outlier_detected_when_spike_present() -> None:
    bars = _bars_with_outlier(30, outlier_idx=15, spike_factor=30.0)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert report.outlier_count > 0


def test_custom_sigma_threshold_affects_outlier_count() -> None:
    bars = _bars_with_outlier(50, outlier_idx=25, spike_factor=8.0)
    # Tight threshold catches more
    report_tight = compute_data_quality_report(symbol="X", bars=bars, sigma_threshold=2.0)
    # Loose threshold catches fewer
    report_loose = compute_data_quality_report(symbol="X", bars=bars, sigma_threshold=10.0)
    assert report_tight.outlier_count >= report_loose.outlier_count


# ── Timezone consistency ──────────────────────────────────────────────────────


def test_numeric_timestamps_are_timezone_consistent() -> None:
    bars = _bars(20)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    assert report.timezone_consistent is True


def test_utc_iso_string_timestamps_are_consistent() -> None:
    bars = [
        {"timestamp": "2024-01-01T00:00:00Z", "close": 100.0},
        {"timestamp": "2024-01-02T00:00:00Z", "close": 101.0},
        {"timestamp": "2024-01-03T00:00:00+00:00", "close": 102.0},
    ]
    report = compute_data_quality_report(symbol="X", bars=bars)
    assert report.timezone_consistent is True


def test_mixed_non_utc_timestamps_are_inconsistent() -> None:
    bars = [
        {"timestamp": "2024-01-01T00:00:00Z", "close": 100.0},
        {"timestamp": "2024-01-02T00:00:00+05:30", "close": 101.0},
        {"timestamp": "2024-01-03T00:00:00Z", "close": 102.0},
    ]
    report = compute_data_quality_report(symbol="X", bars=bars)
    assert report.timezone_consistent is False


# ── to_dict serialization ─────────────────────────────────────────────────────


def test_to_dict_is_json_serializable() -> None:
    bars = _bars_with_gap(30, gap_after_idx=14)
    report = compute_data_quality_report(symbol="AAPL", bars=bars)
    d = report.to_dict()
    serialized = json.dumps(d, allow_nan=False)
    restored = json.loads(serialized)
    assert restored["symbol"] == "AAPL"
    assert "gaps" in restored
    assert "outlier_count" in restored


def test_to_dict_no_data_fields_present() -> None:
    report = compute_data_quality_report(symbol="X", bars=[])
    d = report.to_dict()
    assert d["no_data"] is True
    assert d["date_range"] is None
    assert d["gaps"] == []


# ── API endpoint ──────────────────────────────────────────────────────────────


def _make_app(symbol_data: dict[str, list[dict]]) -> FastAPI:
    app = FastAPI()
    router = build_data_quality_router(
        get_bars_for_symbol=lambda sym: symbol_data.get(sym, []),
    )
    app.include_router(router)
    return app


def test_api_returns_200_for_known_symbol() -> None:
    app = _make_app({"AAPL": _bars(30)})
    client = TestClient(app)
    resp = client.get("/data/quality/AAPL")
    assert resp.status_code == 200


def test_api_returns_no_data_true_for_unknown_symbol() -> None:
    app = _make_app({})
    client = TestClient(app)
    resp = client.get("/data/quality/UNKNOWN")
    assert resp.status_code == 200
    assert resp.json()["no_data"] is True


def test_api_symbol_is_uppercased() -> None:
    app = _make_app({"AAPL": _bars(20)})
    client = TestClient(app)
    resp = client.get("/data/quality/aapl")
    assert resp.status_code == 200
    assert resp.json()["symbol"] == "AAPL"


def test_api_reports_gaps_for_gapped_data() -> None:
    app = _make_app({"GAPPED": _bars_with_gap(30, gap_after_idx=14, gap_days=5)})
    client = TestClient(app)
    resp = client.get("/data/quality/GAPPED")
    data = resp.json()
    assert data["no_data"] is False
    assert len(data["gaps"]) >= 1


def test_api_reports_outlier_for_spiked_data() -> None:
    app = _make_app({"SPIKE": _bars_with_outlier(30, outlier_idx=15, spike_factor=30.0)})
    client = TestClient(app)
    resp = client.get("/data/quality/SPIKE")
    data = resp.json()
    assert data["outlier_count"] > 0


def test_api_response_matches_direct_computation() -> None:
    bars = _bars(25)
    app = _make_app({"X": bars})
    client = TestClient(app)
    resp = client.get("/data/quality/X")
    direct = compute_data_quality_report(symbol="X", bars=bars).to_dict()
    assert resp.json() == direct


# ── CLI tool ──────────────────────────────────────────────────────────────────


def _run_cli(args: list[str], tmp_path: Path) -> "subprocess.CompletedProcess[str]":
    import subprocess, sys, os

    env = {**os.environ, "PYTHONPATH": "/home/user/Trading-engine/src"}
    return subprocess.run(
        [sys.executable, "scripts/data_quality_report.py"] + args,
        cwd="/home/user/Trading-engine",
        capture_output=True,
        text=True,
        env=env,
    )


def test_cli_outputs_valid_json(tmp_path: Path) -> None:
    bars_path = tmp_path / "bars.json"
    bars_path.write_text(json.dumps(_bars(20)), encoding="utf-8")

    result = _run_cli(["--symbol", "AAPL", "--bars-file", str(bars_path)], tmp_path)
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["symbol"] == "AAPL"


def test_cli_writes_output_file(tmp_path: Path) -> None:
    bars_path = tmp_path / "bars.json"
    bars_path.write_text(json.dumps(_bars(20)), encoding="utf-8")
    out_path = tmp_path / "report.json"

    result = _run_cli(
        ["--symbol", "AAPL", "--bars-file", str(bars_path), "--output", str(out_path)],
        tmp_path,
    )
    assert result.returncode == 0
    assert out_path.exists()
    payload = json.loads(out_path.read_text())
    assert payload["symbol"] == "AAPL"


def test_cli_returns_nonzero_for_bad_input(tmp_path: Path) -> None:
    bad_path = tmp_path / "bad.json"
    bad_path.write_text("not json", encoding="utf-8")

    result = _run_cli(["--symbol", "X", "--bars-file", str(bad_path)], tmp_path)
    assert result.returncode != 0


def test_cli_output_matches_api_output(tmp_path: Path) -> None:
    bars = _bars(25)
    bars_path = tmp_path / "bars.json"
    bars_path.write_text(json.dumps(bars), encoding="utf-8")

    result = _run_cli(["--symbol", "X", "--bars-file", str(bars_path)], tmp_path)
    assert result.returncode == 0
    cli_payload = json.loads(result.stdout)

    direct = compute_data_quality_report(symbol="X", bars=bars).to_dict()
    assert cli_payload == direct

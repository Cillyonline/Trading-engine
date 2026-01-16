from __future__ import annotations

from pathlib import Path

import pytest

from cilly_trading.models import compute_signal_id, compute_signal_reason_id
from cilly_trading.repositories.signals_sqlite import (
    SignalReconstructionError,
    SqliteSignalRepository,
    reconstruct_signal_explanation,
)


def _make_repo(tmp_path: Path) -> SqliteSignalRepository:
    db_path = tmp_path / "test_signals.db"
    return SqliteSignalRepository(db_path=db_path)


def _base_signal(**overrides):
    base = {
        "analysis_run_id": "analysis-run-1",
        "ingestion_run_id": "ingestion-run-1",
        "symbol": "AAPL",
        "strategy": "RSI2",
        "direction": "long",
        "score": 0.9,
        "timestamp": "2025-01-01T00:00:00Z",
        "stage": "setup",
        "timeframe": "D1",
        "market_type": "stock",
        "data_source": "yahoo",
    }
    base.update(overrides)
    return base


def _build_reason(
    *,
    signal_id: str,
    ordering_key: int,
    rule_id: str,
    data_id: str,
    data_value: float,
    timestamp: str,
) -> dict:
    reason = {
        "reason_type": "STATE_TRANSITION",
        "signal_id": signal_id,
        "rule_ref": {
            "rule_id": rule_id,
            "rule_version": "1.0",
        },
        "data_refs": [
            {
                "data_type": "STATE_VALUE",
                "data_id": data_id,
                "value": data_value,
                "timestamp": timestamp,
            }
        ],
        "ordering_key": ordering_key,
    }
    reason["reason_id"] = compute_signal_reason_id(
        signal_id=signal_id,
        reason_type=reason["reason_type"],
        rule_ref=reason["rule_ref"],
        data_refs=reason["data_refs"],
    )
    return reason


def _signal_with_reasons():
    signal = _base_signal()
    signal_id = compute_signal_id(signal)
    reasons = [
        _build_reason(
            signal_id=signal_id,
            ordering_key=10,
            rule_id="rule-alpha",
            data_id="state-1",
            data_value=1.0,
            timestamp="2025-01-01T00:00:00Z",
        ),
        _build_reason(
            signal_id=signal_id,
            ordering_key=20,
            rule_id="rule-beta",
            data_id="state-2",
            data_value=2.0,
            timestamp="2025-01-01T00:00:00Z",
        ),
    ]
    signal["reasons"] = reasons
    return signal


def test_persist_reasons_roundtrip(tmp_path: Path) -> None:
    repo = _make_repo(tmp_path)
    signal = _signal_with_reasons()

    repo.save_signals([signal])

    rows = repo.list_signals(limit=1)
    assert rows[0]["analysis_run_id"] == signal["analysis_run_id"]
    assert rows[0]["ingestion_run_id"] == signal["ingestion_run_id"]
    assert rows[0]["reasons"] == signal["reasons"]


def test_reconstruct_signal_explanation_success() -> None:
    signal = _signal_with_reasons()

    explanation = reconstruct_signal_explanation(signal)

    assert explanation["signal_id"] == compute_signal_id(signal)
    assert explanation["symbol"] == signal["symbol"]
    assert explanation["reasons"] == signal["reasons"]


def test_reconstruct_signal_explanation_missing_reasons() -> None:
    signal = _base_signal()

    with pytest.raises(SignalReconstructionError, match="Signal reasons are missing"):
        reconstruct_signal_explanation(signal)


def test_reconstruct_signal_explanation_invalid_reason_id() -> None:
    signal = _signal_with_reasons()
    signal["reasons"][0]["reason_id"] = "sr_invalid"

    with pytest.raises(SignalReconstructionError, match="Signal reason ID does not match"):
        reconstruct_signal_explanation(signal)


def test_reconstruct_signal_explanation_non_canonical_order() -> None:
    signal = _signal_with_reasons()
    signal["reasons"] = list(reversed(signal["reasons"]))

    with pytest.raises(SignalReconstructionError, match="not in canonical order"):
        reconstruct_signal_explanation(signal)


def test_reconstruct_signal_explanation_missing_linkage() -> None:
    signal = _signal_with_reasons()
    signal.pop("analysis_run_id")

    with pytest.raises(
        SignalReconstructionError,
        match="missing required fields for reconstruction",
    ):
        reconstruct_signal_explanation(signal)

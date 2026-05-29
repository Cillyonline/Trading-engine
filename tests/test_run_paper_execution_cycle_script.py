from __future__ import annotations

import importlib.util
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from cilly_trading.engine.paper_execution_worker import BoundedPaperExecutionWorker
from cilly_trading.engine.paper_execution_risk_profile import (
    PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID,
)
from cilly_trading.repositories.execution_core_sqlite import (
    SqliteCanonicalExecutionRepository,
)
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    module_path = REPO_ROOT / "scripts" / "run_paper_execution_cycle.py"
    spec = importlib.util.spec_from_file_location(
        "test_run_paper_execution_cycle_script_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_paper_execution_cycle.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_run_paper_execution_cycle_includes_canonical_risk_profile(
    tmp_path: Path,
) -> None:
    module = _load_script_module()

    db_path = tmp_path / "paper_execution.db"
    evidence_dir = tmp_path / "evidence"

    exit_code = module.run_paper_execution_cycle(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        signal_limit=10,
        ran_at=datetime(2026, 1, 1, 0, 0, 0, tzinfo=timezone.utc),
    )
    assert exit_code == module.EXIT_CYCLE_NO_ELIGIBLE

    evidence_files = sorted(evidence_dir.glob("paper-execution-no-eligible-*.json"))
    assert len(evidence_files) == 1

    payload = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert payload["risk_profile"]["contract_id"] == PAPER_EXECUTION_RISK_PROFILE_CONTRACT_ID


def test_run_paper_execution_cycle_routes_exit_signals_to_worker(
    tmp_path: Path,
) -> None:
    module = _load_script_module()

    db_path = tmp_path / "paper_execution_exit.db"
    evidence_dir = tmp_path / "evidence"
    execution_repo = SqliteCanonicalExecutionRepository(db_path=db_path)
    signal_repo = SqliteSignalRepository(db_path=db_path)
    worker = BoundedPaperExecutionWorker(repository=execution_repo)

    entry_result = worker.process_signal({
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "entry_zone": {"from_": 100.0, "to": 100.0},
        "signal_id": "script-exit-entry",
    })
    assert entry_result.outcome == "eligible"

    signal_repo.save_signals([
        {
            "symbol": "AAPL",
            "strategy": "s",
            "direction": "long",  # type: ignore[typeddict-item]
            "score": 80.0,
            "timestamp": "2026-01-02T12:00:00Z",
            "stage": "exit",  # type: ignore[typeddict-item]
            "entry_zone": {"from_": 110.0, "to": 110.0},
            "timeframe": "1d",
            "market_type": "stock",  # type: ignore[typeddict-item]
            "data_source": "yahoo",  # type: ignore[typeddict-item]
            "ingestion_run_id": "ing-script-exit",
            "signal_id": "script-exit-signal",
        }
    ])

    exit_code = module.run_paper_execution_cycle(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        signal_limit=10,
        ran_at=datetime(2026, 1, 3, 0, 0, 0, tzinfo=timezone.utc),
    )

    assert exit_code == module.EXIT_CYCLE_PASS
    evidence_files = sorted(evidence_dir.glob("paper-execution-pass-*.json"))
    assert len(evidence_files) == 1
    payload = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert payload["eligible"] == 1
    assert payload["results"][0]["outcome"] == "eligible:full_exit"
    assert payload["results"][0]["trade_id"] == entry_result.trade_id

    closed_trade = execution_repo.get_trade(entry_result.trade_id)
    assert closed_trade is not None
    assert closed_trade.status == "closed"


def test_run_paper_execution_cycle_uses_current_run_scope_over_stale_turtle_rows(
    tmp_path: Path,
) -> None:
    module = _load_script_module()

    db_path = tmp_path / "paper_execution_scope.db"
    evidence_dir = tmp_path / "evidence"
    signal_repo = SqliteSignalRepository(db_path=db_path)

    signal_repo.save_signals(
        [
            {
                "signal_id": "turtle-scope-signal",
                "analysis_run_id": "analysis-stale",
                "ingestion_run_id": "ingestion-stale",
                "symbol": "WMT",
                "strategy": "TURTLE",
                "direction": "long",  # type: ignore[typeddict-item]
                "score": 80.0,
                "timestamp": "2026-05-27T12:00:00Z",
                "stage": "setup",  # type: ignore[typeddict-item]
                "entry_zone": {"from_": 100.0, "to": 100.0},
                "timeframe": "D1",
                "market_type": "stock",  # type: ignore[typeddict-item]
                "data_source": "snapshot",  # type: ignore[typeddict-item]
            },
            {
                "signal_id": "turtle-scope-signal",
                "analysis_run_id": "analysis-current",
                "ingestion_run_id": "ingestion-current",
                "symbol": "WMT",
                "strategy": "TURTLE",
                "direction": "long",  # type: ignore[typeddict-item]
                "score": 80.0,
                "timestamp": "2026-05-28T12:00:00Z",
                "stage": "setup",  # type: ignore[typeddict-item]
                "entry_zone": {"from_": 100.0, "to": 100.0},
                "stop_loss": 95.0,
                "timeframe": "D1",
                "market_type": "stock",  # type: ignore[typeddict-item]
                "data_source": "snapshot",  # type: ignore[typeddict-item]
            },
        ]
    )

    exit_code = module.run_paper_execution_cycle(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        signal_limit=10,
        analysis_run_id="analysis-current",
        ingestion_run_id="ingestion-current",
        ran_at=datetime(2026, 5, 28, 13, 0, 0, tzinfo=timezone.utc),
    )

    assert exit_code == module.EXIT_CYCLE_PASS
    evidence_file = evidence_dir / "paper-execution-pass-20260528T130000Z.json"
    payload = json.loads(evidence_file.read_text(encoding="utf-8"))

    assert payload["signals_read"] == 1
    assert payload["signal_scope"] == {
        "analysis_run_id": "analysis-current",
        "fallback_reason": None,
        "ingestion_run_id": "ingestion-current",
        "scope_filters": ["analysis_run_id", "ingestion_run_id"],
        "selection_mode": "current_run_scope",
        "signals_read": 1,
    }
    assert payload["eligible"] == 1
    assert payload["rejected"] == 0
    assert payload["diagnostics_summary"]["missing_trade_risk_input_count"] == 0
    assert payload["results"][0]["outcome"] == "eligible"
    assert payload["results"][0]["decision_inputs"]["trade_risk_pct"] == "0.05"


def test_run_paper_execution_cycle_fallback_uses_latest_signal_identity_with_risk(
    tmp_path: Path,
) -> None:
    module = _load_script_module()

    db_path = tmp_path / "paper_execution_fallback.db"
    evidence_dir = tmp_path / "evidence"
    signal_repo = SqliteSignalRepository(db_path=db_path)

    signal_repo.save_signals(
        [
            {
                "signal_id": "turtle-fallback-signal",
                "analysis_run_id": "analysis-old",
                "ingestion_run_id": "ingestion-old",
                "symbol": "COST",
                "strategy": "TURTLE",
                "direction": "long",  # type: ignore[typeddict-item]
                "score": 80.0,
                "timestamp": "2026-05-27T12:00:00Z",
                "stage": "setup",  # type: ignore[typeddict-item]
                "entry_zone": {"from_": 200.0, "to": 200.0},
                "timeframe": "D1",
                "market_type": "stock",  # type: ignore[typeddict-item]
                "data_source": "snapshot",  # type: ignore[typeddict-item]
            },
            {
                "signal_id": "turtle-fallback-signal",
                "analysis_run_id": "analysis-new",
                "ingestion_run_id": "ingestion-new",
                "symbol": "COST",
                "strategy": "TURTLE",
                "direction": "long",  # type: ignore[typeddict-item]
                "score": 80.0,
                "timestamp": "2026-05-28T12:00:00Z",
                "stage": "setup",  # type: ignore[typeddict-item]
                "entry_zone": {"from_": 200.0, "to": 200.0},
                "trade_risk_pct": 0.03,
                "timeframe": "D1",
                "market_type": "stock",  # type: ignore[typeddict-item]
                "data_source": "snapshot",  # type: ignore[typeddict-item]
            },
        ]
    )

    exit_code = module.run_paper_execution_cycle(
        db_path=str(db_path),
        evidence_dir=str(evidence_dir),
        signal_limit=10,
        ran_at=datetime(2026, 5, 28, 14, 0, 0, tzinfo=timezone.utc),
    )

    assert exit_code == module.EXIT_CYCLE_PASS
    evidence_file = evidence_dir / "paper-execution-pass-20260528T140000Z.json"
    payload = json.loads(evidence_file.read_text(encoding="utf-8"))

    assert payload["signals_read"] == 1
    assert payload["signal_scope"]["selection_mode"] == "latest_per_identity_fallback"
    assert payload["signal_scope"]["fallback_reason"] == "current_run_scope_unavailable"
    assert payload["eligible"] == 1
    assert payload["rejected"] == 0
    assert payload["diagnostics_summary"]["missing_trade_risk_input_count"] == 0
    assert payload["results"][0]["outcome"] == "eligible"
    assert payload["results"][0]["decision_inputs"]["trade_risk_pct"] == "0.03"

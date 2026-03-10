from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import Any, Literal

import pandas as pd
import pytest
from fastapi.testclient import TestClient
from risk.contracts import RiskDecision, RiskEvaluationRequest, RiskGate

import api.main as api_main
from cilly_trading.engine.core import EngineConfig, run_watchlist_analysis
from cilly_trading.engine.logging import (
    InMemoryEngineLogSink,
    configure_engine_log_emitter,
    reset_engine_logging_for_tests,
)
from cilly_trading.engine.metrics import (
    get_engine_metrics_snapshot,
    reset_engine_metrics_registry,
)
from cilly_trading.engine.pipeline.orchestrator import run_pipeline
from cilly_trading.engine.strategy_lifecycle.model import StrategyLifecycleState
from cilly_trading.engine.telemetry.emitter import (
    InMemoryTelemetrySink,
    configure_telemetry_emitter,
    reset_telemetry_emission_for_tests,
)


def _load_provider_module():
    root = Path(__file__).resolve().parents[3]
    module_path = root / "src" / "cilly_trading" / "engine" / "data" / "market_data_provider.py"
    spec = importlib.util.spec_from_file_location(
        "market_data_provider_observability_integration",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load market_data_provider module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


_provider_module = _load_provider_module()
Candle = _provider_module.Candle
MarketDataProviderRegistry = _provider_module.MarketDataProviderRegistry
MarketDataRequest = _provider_module.MarketDataRequest
ProviderFailoverExhaustedError = _provider_module.ProviderFailoverExhaustedError


@pytest.fixture(autouse=True)
def _reset_observability_state() -> None:
    reset_engine_logging_for_tests()
    reset_engine_metrics_registry()
    reset_telemetry_emission_for_tests()


@dataclass
class _SignalRepo:
    saved: list[dict[str, Any]] | None = None

    def save_signals(self, signals: list[dict[str, Any]]) -> None:
        self.saved = list(signals)


class _LineageRepo:
    def save_lineage(self, ctx: Any) -> None:
        return None


class _SingleSignalStrategy:
    name = "GENERIC"

    def generate_signals(
        self,
        df: pd.DataFrame,
        config: dict[str, Any],
    ) -> list[dict[str, Any]]:
        return [{"stage": "setup", "score": 7}]


class _RejectedRiskGate(RiskGate):
    def __init__(self, reason: str) -> None:
        self._reason = reason

    def evaluate(self, request: RiskEvaluationRequest) -> RiskDecision:
        return RiskDecision(
            decision="REJECTED",
            score=500.0,
            max_allowed=100.0,
            reason=self._reason,
            timestamp=datetime(2026, 1, 1, tzinfo=timezone.utc),
            rule_version="integration-v1",
        )


class _ProductionLifecycleStore:
    def get_state(self, strategy_id: str) -> StrategyLifecycleState:
        return StrategyLifecycleState.PRODUCTION

    def set_state(self, strategy_id: str, new_state: StrategyLifecycleState) -> None:
        return None


@dataclass(frozen=True)
class _Position:
    quantity: Decimal
    avg_price: Decimal


@dataclass(frozen=True)
class _ExecutionConfig:
    slippage_bps: int
    commission_per_order: Decimal
    price_scale: Decimal = Decimal("0.00000001")
    money_scale: Decimal = Decimal("0.01")
    quantity_scale: Decimal = Decimal("0.00000001")
    fill_timing: Literal["next_snapshot", "same_snapshot"] = "next_snapshot"


class _AlwaysFailProvider:
    def __init__(self, message: str) -> None:
        self._message = message

    def iter_candles(self, request: MarketDataRequest):
        raise RuntimeError(self._message)


class _SingleCandleProvider:
    def __init__(self, candle: Candle) -> None:
        self._candle = candle

    def iter_candles(self, request: MarketDataRequest):
        return iter((self._candle,))


def _analysis_dataframe(*args: Any, **kwargs: Any) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "timestamp": "2026-01-01T00:00:00Z",
                "open": 100,
                "high": 101,
                "low": 99,
                "close": 100,
                "volume": 10,
            }
        ]
    )


def _parse_json_lines(lines: tuple[str, ...]) -> list[dict[str, Any]]:
    return [json.loads(line) for line in lines]


def _runtime_payload(
    *,
    mode: str,
    updated_at: datetime,
) -> dict[str, object]:
    return {
        "schema_version": "v1",
        "runtime_id": "engine-runtime-observability",
        "mode": mode,
        "timestamps": {
            "started_at": "2026-01-01T12:00:00+00:00",
            "updated_at": updated_at.isoformat(),
        },
        "ownership": {"owner_tag": "engine"},
        "extensions": [
            {
                "name": "core.health",
                "point": "health",
                "enabled": True,
                "source": "core",
            },
            {
                "name": "core.introspection",
                "point": "introspection",
                "enabled": True,
                "source": "core",
            },
            {
                "name": "core.status",
                "point": "status",
                "enabled": True,
                "source": "core",
            },
        ],
    }


def _configure_health_environment(
    *,
    monkeypatch: pytest.MonkeyPatch,
    checked_at: datetime,
    updated_at: datetime,
    db_path: Path,
    kill_switch_active: bool,
) -> None:
    monkeypatch.setattr(api_main, "start_engine_runtime", lambda: "running")
    monkeypatch.setattr(api_main, "shutdown_engine_runtime", lambda: "stopped")
    monkeypatch.setattr(
        api_main,
        "get_runtime_introspection_payload",
        lambda: _runtime_payload(mode="running", updated_at=updated_at),
    )
    monkeypatch.setattr(api_main, "_health_now", lambda: checked_at)
    monkeypatch.setattr(api_main, "ANALYSIS_DB_PATH", str(db_path))
    monkeypatch.setenv(
        "CILLY_EXECUTION_KILL_SWITCH_ACTIVE",
        "true" if kill_switch_active else "false",
    )
    for name in (
        "CILLY_EXECUTION_DRAWDOWN_MAX_PCT",
        "CILLY_EXECUTION_DAILY_LOSS_MAX_ABS",
        "CILLY_PORTFOLIO_PEAK_EQUITY",
        "CILLY_PORTFOLIO_CURRENT_EQUITY",
        "CILLY_PORTFOLIO_START_OF_DAY_EQUITY",
    ):
        monkeypatch.delenv(name, raising=False)


def _read_health_payloads() -> dict[str, dict[str, Any]]:
    with TestClient(api_main.app) as client:
        return {
            "/health": client.get("/health").json(),
            "/health/engine": client.get("/health/engine").json(),
            "/health/data": client.get("/health/data").json(),
            "/health/guards": client.get("/health/guards").json(),
        }


def _run_healthy_observability_scenario(
    *,
    monkeypatch: pytest.MonkeyPatch,
    base_dir: Path,
) -> dict[str, Any]:
    reset_engine_logging_for_tests()
    reset_engine_metrics_registry()
    reset_telemetry_emission_for_tests()

    log_sink = InMemoryEngineLogSink()
    telemetry_sink = InMemoryTelemetrySink()
    configure_engine_log_emitter(log_sink.write)
    configure_telemetry_emitter(telemetry_sink.write)

    monkeypatch.setattr("cilly_trading.engine.core.load_ohlcv", _analysis_dataframe)

    run_watchlist_analysis(
        symbols=["AAPL"],
        strategies=[_SingleSignalStrategy()],
        engine_config=EngineConfig(external_data_enabled=True),
        strategy_configs={},
        signal_repo=_SignalRepo(),
        ingestion_run_id="ingest-observability",
        snapshot_id="snapshot-observability",
        lineage_repo=_LineageRepo(),
    )

    run_pipeline(
        signal={
            "orders": [],
            "snapshot": {"timestamp": "2026-01-02T00:00:00Z", "open": "100"},
        },
        risk_gate=_RejectedRiskGate("drawdown limit breached"),
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=RiskEvaluationRequest(
            request_id="req-observability",
            strategy_id="strategy-a",
            symbol="AAPL",
            notional_usd=500.0,
            metadata={"guard_type": "drawdown"},
        ),
        position=_Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        execution_config=_ExecutionConfig(
            slippage_bps=10,
            commission_per_order=Decimal("1.25"),
        ),
    )

    registry = MarketDataProviderRegistry()
    registry.register(
        name="primary",
        provider=_AlwaysFailProvider("primary unavailable"),
        priority=1,
    )
    registry.register(
        name="fallback",
        provider=_SingleCandleProvider(
            Candle(
                timestamp=datetime(2026, 1, 3, tzinfo=timezone.utc),
                symbol="AAPL",
                timeframe="1D",
                open=Decimal("100"),
                high=Decimal("101"),
                low=Decimal("99"),
                close=Decimal("100.5"),
                volume=Decimal("10"),
            )
        ),
        priority=2,
    )
    tuple(
        registry.iter_candles_with_failover(
            MarketDataRequest(symbol="AAPL", timeframe="1D", limit=5)
        )
    )

    checked_at = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
    db_path = base_dir / "analysis.db"
    base_dir.mkdir(parents=True, exist_ok=True)
    db_path.write_text("", encoding="utf-8")
    _configure_health_environment(
        monkeypatch=monkeypatch,
        checked_at=checked_at,
        updated_at=checked_at - timedelta(seconds=15),
        db_path=db_path,
        kill_switch_active=False,
    )

    structured_logs = _parse_json_lines(log_sink.lines)
    return {
        "structured_logs": structured_logs,
        "telemetry_events": _parse_json_lines(telemetry_sink.lines),
        "metrics": get_engine_metrics_snapshot(),
        "health": _read_health_payloads(),
    }


def _run_failure_observability_scenario(
    *,
    monkeypatch: pytest.MonkeyPatch,
    base_dir: Path,
) -> dict[str, Any]:
    reset_engine_logging_for_tests()
    reset_engine_metrics_registry()
    reset_telemetry_emission_for_tests()

    log_sink = InMemoryEngineLogSink()
    telemetry_sink = InMemoryTelemetrySink()
    configure_engine_log_emitter(log_sink.write)
    configure_telemetry_emitter(telemetry_sink.write)

    run_pipeline(
        signal={
            "orders": [],
            "snapshot": {"timestamp": "2026-01-02T00:00:00Z", "open": "100"},
        },
        risk_gate=_RejectedRiskGate("unsupported guard source"),
        lifecycle_store=_ProductionLifecycleStore(),
        risk_request=RiskEvaluationRequest(
            request_id="req-emergency",
            strategy_id="strategy-a",
            symbol="AAPL",
            notional_usd=500.0,
            metadata={"guard_type": "unsupported_guard"},
        ),
        position=_Position(quantity=Decimal("0"), avg_price=Decimal("0")),
        execution_config=_ExecutionConfig(
            slippage_bps=10,
            commission_per_order=Decimal("1.25"),
        ),
    )

    registry = MarketDataProviderRegistry()
    registry.register(name="primary", provider=_AlwaysFailProvider("alpha down"), priority=1)
    registry.register(name="backup", provider=_AlwaysFailProvider("beta down"), priority=2)
    with pytest.raises(ProviderFailoverExhaustedError):
        tuple(
            registry.iter_candles_with_failover(
                MarketDataRequest(symbol="ETH/USDT", timeframe="15M")
            )
        )

    checked_at = datetime(2026, 1, 1, 12, 0, 30, tzinfo=timezone.utc)
    missing_db_path = base_dir / "missing.db"
    _configure_health_environment(
        monkeypatch=monkeypatch,
        checked_at=checked_at,
        updated_at=checked_at - timedelta(minutes=3),
        db_path=missing_db_path,
        kill_switch_active=True,
    )

    structured_logs = _parse_json_lines(log_sink.lines)
    return {
        "structured_logs": structured_logs,
        "telemetry_events": _parse_json_lines(telemetry_sink.lines),
        "metrics": get_engine_metrics_snapshot(),
        "health": _read_health_payloads(),
    }


def test_observability_integration_is_deterministic_for_healthy_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = _run_healthy_observability_scenario(
        monkeypatch=monkeypatch,
        base_dir=tmp_path / "healthy-first",
    )
    second = _run_healthy_observability_scenario(
        monkeypatch=monkeypatch,
        base_dir=tmp_path / "healthy-second",
    )

    assert first == second
    assert [event["event"] for event in first["structured_logs"]] == [
        "analysis_run.started",
        "signal.generated",
        "analysis_run.completed",
        "order_submission.attempt",
        "guard.triggered",
        "provider_failover.attempt_failed",
        "provider_failover.recovered",
    ]
    assert [event["event_index"] for event in first["structured_logs"]] == list(range(7))
    assert [event["event"] for event in first["telemetry_events"]] == [
        "provider_failover.attempt_failed",
        "provider_failover.recovered",
    ]
    assert first["metrics"] == {
        "analysis_runs": 1,
        "signals_generated": 1,
        "orders_submitted": 1,
        "guard_triggers": 1,
        "provider_failovers": 1,
    }
    assert first["health"] == {
        "/health": {
            "status": "healthy",
            "mode": "running",
            "reason": "runtime_running_fresh",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/engine": {
            "subsystem": "engine",
            "status": "healthy",
            "ready": True,
            "mode": "running",
            "reason": "runtime_running_fresh",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/data": {
            "subsystem": "data",
            "status": "healthy",
            "ready": True,
            "reason": "data_source_available",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/guards": {
            "subsystem": "guards",
            "status": "healthy",
            "ready": True,
            "decision": "allowing",
            "blocking": False,
            "guards": {
                "drawdown_guard": {"enabled": False, "blocking": False},
                "daily_loss_guard": {"enabled": False, "blocking": False},
                "kill_switch": {"active": False, "blocking": False},
            },
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
    }


def test_observability_integration_is_deterministic_for_failure_runtime(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    first = _run_failure_observability_scenario(
        monkeypatch=monkeypatch,
        base_dir=tmp_path / "failure-first",
    )
    second = _run_failure_observability_scenario(
        monkeypatch=monkeypatch,
        base_dir=tmp_path / "failure-second",
    )

    assert first == second
    assert [event["event"] for event in first["structured_logs"]] == [
        "order_submission.attempt",
        "guard.triggered",
        "provider_failover.attempt_failed",
        "provider_failover.attempt_failed",
        "provider_failover.exhausted",
    ]
    assert [event["event_index"] for event in first["structured_logs"]] == list(range(5))
    assert [event["event"] for event in first["telemetry_events"]] == [
        "provider_failover.attempt_failed",
        "provider_failover.attempt_failed",
        "provider_failover.exhausted",
    ]
    assert first["metrics"] == {
        "analysis_runs": 0,
        "signals_generated": 0,
        "orders_submitted": 1,
        "guard_triggers": 1,
        "provider_failovers": 1,
    }
    assert first["health"] == {
        "/health": {
            "status": "unavailable",
            "mode": "running",
            "reason": "runtime_running_timeout",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/engine": {
            "subsystem": "engine",
            "status": "unavailable",
            "ready": True,
            "mode": "running",
            "reason": "runtime_running_timeout",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/data": {
            "subsystem": "data",
            "status": "unavailable",
            "ready": False,
            "reason": "data_source_unavailable",
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
        "/health/guards": {
            "subsystem": "guards",
            "status": "degraded",
            "ready": False,
            "decision": "blocking",
            "blocking": True,
            "guards": {
                "drawdown_guard": {"enabled": False, "blocking": False},
                "daily_loss_guard": {"enabled": False, "blocking": False},
                "kill_switch": {"active": True, "blocking": True},
            },
            "checked_at": "2026-01-01T12:00:30+00:00",
        },
    }

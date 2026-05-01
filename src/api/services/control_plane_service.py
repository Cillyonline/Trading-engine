from __future__ import annotations

import os
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Literal

from cilly_trading.compliance.daily_loss_guard import (
    configured_daily_loss_limit,
    should_block_execution_for_daily_loss,
)
from cilly_trading.compliance.drawdown_guard import (
    configured_drawdown_threshold,
    should_block_execution_for_drawdown,
)
from cilly_trading.compliance.kill_switch import is_kill_switch_active
from cilly_trading.config.external_data import EXTERNAL_DATA_ENABLED
from cilly_trading.portfolio import PortfolioState as CompliancePortfolioState

from ..models import (
    ComplianceGuardStatusResponse,
    ComplianceStatusResponse,
    DailyLossGuardStatusResponse,
    DrawdownGuardStatusResponse,
    GuardStatusCollectionResponse,
    KillSwitchStatusResponse,
    RuntimeIntrospectionResponse,
    SystemStateResponse,
)


@dataclass
class ControlPlaneHealthDependencies:
    resolve_analysis_db_path: Callable[[], str]
    now: Callable[[], datetime]
    get_runtime_introspection_payload: Callable[[], dict[str, Any]]
    evaluate_runtime_health: Callable[..., Any]


def runtime_health_payload(*, deps: ControlPlaneHealthDependencies) -> dict[str, Any]:
    payload = deps.get_runtime_introspection_payload()
    snapshot = {
        "mode": payload["mode"],
        "updated_at": datetime.fromisoformat(payload["timestamps"]["updated_at"]),
    }
    checked_at = deps.now()
    evaluation = deps.evaluate_runtime_health(snapshot, now=checked_at)
    ready = payload["mode"] in {"ready", "running", "paused"}
    reason = "bounded_runtime_ready" if ready else evaluation.reason
    status = "healthy" if ready else evaluation.status

    return {
        "status": status,
        "ready": ready,
        "mode": payload["mode"],
        "reason": reason,
        "runtime_status": evaluation.status,
        "runtime_reason": evaluation.reason,
        "checked_at": checked_at.isoformat(),
    }


def health_payload(*, deps: ControlPlaneHealthDependencies) -> dict[str, Any]:
    return runtime_health_payload(deps=deps)


def health_engine_payload(*, deps: ControlPlaneHealthDependencies) -> dict[str, Any]:
    payload = runtime_health_payload(deps=deps)

    return {
        "subsystem": "engine",
        "status": payload["status"],
        "ready": payload["ready"],
        "mode": payload["mode"],
        "reason": payload["reason"],
        "runtime_status": payload["runtime_status"],
        "runtime_reason": payload["runtime_reason"],
        "checked_at": payload["checked_at"],
    }


def health_data_payload(*, deps: ControlPlaneHealthDependencies) -> dict[str, Any]:
    checked_at = deps.now()
    db_path = Path(deps.resolve_analysis_db_path())
    ready = db_path.exists()
    status: Literal["healthy", "unavailable"] = "healthy" if ready else "unavailable"
    reason = "data_source_available" if ready else "data_source_unavailable"

    return {
        "subsystem": "data",
        "status": status,
        "ready": ready,
        "reason": reason,
        "checked_at": checked_at.isoformat(),
        "external_data_gate": "enabled" if EXTERNAL_DATA_ENABLED else "disabled",
    }


def guard_decision(*, blocking: bool) -> Literal["allowing", "blocking"]:
    return "blocking" if blocking else "allowing"


def read_bool_env(*names: str) -> bool | None:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        normalized = raw_value.strip().lower()
        if normalized in {"1", "true", "yes", "on"}:
            return True
        if normalized in {"0", "false", "no", "off"}:
            return False
    return None


def read_float_env(*names: str) -> float | None:
    for name in names:
        raw_value = os.getenv(name)
        if raw_value is None:
            continue
        try:
            return float(raw_value)
        except (TypeError, ValueError):
            continue
    return None


def load_compliance_guard_status_sources() -> tuple[dict[str, object], CompliancePortfolioState]:
    kill_switch_active = read_bool_env(
        "CILLY_EXECUTION_KILL_SWITCH_ACTIVE",
        "execution.kill_switch.active",
    )
    drawdown_max_pct = read_float_env(
        "CILLY_EXECUTION_DRAWDOWN_MAX_PCT",
        "execution.drawdown.max_pct",
    )
    daily_loss_max_abs = read_float_env(
        "CILLY_EXECUTION_DAILY_LOSS_MAX_ABS",
        "execution.daily_loss.max_abs",
    )

    peak_equity = read_float_env(
        "CILLY_PORTFOLIO_PEAK_EQUITY",
        "portfolio.peak_equity",
    )
    current_equity = read_float_env(
        "CILLY_PORTFOLIO_CURRENT_EQUITY",
        "portfolio.current_equity",
    )
    start_of_day_equity = read_float_env(
        "CILLY_PORTFOLIO_START_OF_DAY_EQUITY",
        "portfolio.start_of_day_equity",
    )

    guard_config: dict[str, object] = {
        "execution.kill_switch.active": kill_switch_active is True,
    }
    if drawdown_max_pct is not None:
        guard_config["execution.drawdown.max_pct"] = drawdown_max_pct
    if daily_loss_max_abs is not None:
        guard_config["execution.daily_loss.max_abs"] = daily_loss_max_abs

    portfolio_state = CompliancePortfolioState(
        peak_equity=peak_equity if peak_equity is not None else 0.0,
        current_equity=current_equity if current_equity is not None else 0.0,
        start_of_day_equity=start_of_day_equity,
    )
    return guard_config, portfolio_state


def build_compliance_guard_status_response() -> ComplianceGuardStatusResponse:
    guard_config, portfolio_state = load_compliance_guard_status_sources()

    drawdown_threshold = configured_drawdown_threshold(config=guard_config)
    drawdown_blocking = should_block_execution_for_drawdown(
        portfolio_state=portfolio_state,
        config=guard_config,
    )
    daily_loss_limit = configured_daily_loss_limit(config=guard_config)
    daily_loss_blocking = should_block_execution_for_daily_loss(
        portfolio_state=portfolio_state,
        config=guard_config,
    )
    kill_switch_is_active = is_kill_switch_active(config=guard_config)
    overall_blocking = drawdown_blocking or daily_loss_blocking or kill_switch_is_active

    return ComplianceGuardStatusResponse(
        compliance=ComplianceStatusResponse(
            blocking=overall_blocking,
            decision=guard_decision(blocking=overall_blocking),
        ),
        guards=GuardStatusCollectionResponse(
            drawdown_guard=DrawdownGuardStatusResponse(
                enabled=drawdown_threshold is not None,
                blocking=drawdown_blocking,
                decision=guard_decision(blocking=drawdown_blocking),
                threshold_pct=drawdown_threshold,
                current_drawdown_pct=portfolio_state.drawdown(),
            ),
            daily_loss_guard=DailyLossGuardStatusResponse(
                enabled=daily_loss_limit is not None,
                blocking=daily_loss_blocking,
                decision=guard_decision(blocking=daily_loss_blocking),
                max_daily_loss_abs=daily_loss_limit,
                current_daily_loss_abs=portfolio_state.daily_loss(),
            ),
            kill_switch=KillSwitchStatusResponse(
                active=kill_switch_is_active,
                blocking=kill_switch_is_active,
                decision=guard_decision(blocking=kill_switch_is_active),
            ),
        ),
    )


def health_guards_payload(*, deps: ControlPlaneHealthDependencies) -> dict[str, Any]:
    checked_at = deps.now()
    guard_status = build_compliance_guard_status_response()
    blocking = guard_status.compliance.blocking

    return {
        "subsystem": "guards",
        "status": "degraded" if blocking else "healthy",
        "ready": not blocking,
        "decision": guard_status.compliance.decision,
        "blocking": blocking,
        "guards": {
            "drawdown_guard": {
                "enabled": guard_status.guards.drawdown_guard.enabled,
                "blocking": guard_status.guards.drawdown_guard.blocking,
            },
            "daily_loss_guard": {
                "enabled": guard_status.guards.daily_loss_guard.enabled,
                "blocking": guard_status.guards.daily_loss_guard.blocking,
            },
            "kill_switch": {
                "active": guard_status.guards.kill_switch.active,
                "blocking": guard_status.guards.kill_switch.blocking,
            },
        },
        "checked_at": checked_at.isoformat(),
    }


def build_runtime_introspection_response(
    *,
    get_runtime_introspection_payload: Callable[[], dict[str, Any]],
) -> RuntimeIntrospectionResponse:
    payload = get_runtime_introspection_payload()
    payload.setdefault("extensions", [])
    return RuntimeIntrospectionResponse(**payload)


def build_system_state_response(
    *,
    get_system_state_payload: Callable[[], dict[str, Any]],
) -> SystemStateResponse:
    payload = get_system_state_payload()
    payload["runtime"].setdefault("extensions", [])
    return SystemStateResponse(**payload)

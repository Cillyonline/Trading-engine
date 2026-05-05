from __future__ import annotations

import json
import logging
import os
import sys
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import Header, HTTPException

from ..models import ComplianceGuardStatusResponse, RuntimeIntrospectionResponse, ScreenerRequest, ScreenerResponse, SystemStateResponse
from ..services.jwt_auth import JwtSettings, TokenValidationError, decode_access_token
from . import analysis_service, control_plane_service


class _JsonLogFormatter(logging.Formatter):
    """JSON formatter for structured log output.

    Emits the standard envelope (``timestamp``, ``level``, ``logger``,
    ``message``) plus any structured ``extra={...}`` fields supplied by
    callers and the per-request id installed by
    :class:`api.middleware.RequestIdLogFilter`. Output keys are sorted to
    keep diffs stable in log-tail tooling and golden-file tests.
    """

    # Standard ``LogRecord`` attributes we never propagate as user fields.
    _RESERVED_ATTRS: frozenset[str] = frozenset(
        {
            "args",
            "asctime",
            "created",
            "exc_info",
            "exc_text",
            "filename",
            "funcName",
            "levelname",
            "levelno",
            "lineno",
            "message",
            "module",
            "msecs",
            "msg",
            "name",
            "pathname",
            "process",
            "processName",
            "relativeCreated",
            "stack_info",
            "thread",
            "threadName",
            "taskName",
        }
    )

    def format(self, record: logging.LogRecord) -> str:
        payload: dict[str, Any] = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
        }
        # Promote request_id (installed by RequestIdLogFilter) to a
        # top-level field so log-aggregation indices can pivot on it.
        request_id = getattr(record, "request_id", None)
        if request_id and request_id != "-":
            payload["request_id"] = request_id
        # Surface any structured ``extra={...}`` fields. ``logging`` merges
        # them onto the LogRecord as plain attributes, so we filter out
        # the reserved built-ins to avoid leaking internals.
        for key, value in record.__dict__.items():
            if key in self._RESERVED_ATTRS or key.startswith("_") or key == "request_id":
                continue
            if key in payload:
                continue
            try:
                json.dumps(value)
            except TypeError:
                value = repr(value)
            payload[key] = value
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, sort_keys=True, ensure_ascii=True, default=str)


def configure_logging() -> None:
    """
    Central logging configuration for the Cilly Trading Engine.
    Runs once during app startup.

    Note: Uvicorn with --reload can import modules multiple times.
    This guard prevents duplicate handlers.
    """
    log_level = os.getenv("CILLY_LOG_LEVEL", "INFO").upper()
    log_format = os.getenv("CILLY_LOG_FORMAT", "text").strip().lower()
    formatter: logging.Formatter
    if log_format == "json":
        formatter = _JsonLogFormatter()
    else:
        formatter = logging.Formatter("%(asctime)s %(levelname)s %(name)s - %(message)s")

    root_logger = logging.getLogger()
    root_logger.setLevel(log_level)

    if not root_logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setLevel(log_level)
        handler.setFormatter(formatter)
        root_logger.addHandler(handler)
        return

    for handler in root_logger.handlers:
        handler.setLevel(log_level)
        handler.setFormatter(formatter)


@dataclass
class CompositionRuntimeService:
    logger: logging.Logger
    default_db_path: str
    role_header_name: str
    role_precedence: dict[str, int]
    jwt_settings: JwtSettings
    phase_13_read_only_endpoints: frozenset[str]
    engine_runtime_not_running_status: int
    engine_runtime_not_running_code: str
    get_analysis_db_path_override: Callable[[], Optional[str]]
    get_analysis_run_repo: Callable[[], Any]
    get_signal_repo: Callable[[], Any]
    get_watchlist_repo: Callable[[], Any]
    get_default_strategy_configs: Callable[[], Dict[str, Dict[str, Any]]]
    get_create_strategy: Callable[[], Callable[[str], Any]]
    get_create_registered_strategies: Callable[[], Callable[[], List[Any]]]
    get_trigger_operator_analysis_run: Callable[[], Callable[..., List[Dict[str, Any]]]]
    get_runtime_controller: Callable[[], Any]
    get_engine_runtime_guard_active: Callable[[], bool]
    get_run_watchlist_analysis: Callable[[], Callable[..., List[Dict[str, Any]]]]
    get_require_ingestion_run_compat: Callable[[], Callable[..., None]]
    get_require_snapshot_ready_compat: Callable[[], Callable[..., None]]
    get_run_snapshot_analysis_compat: Callable[[], Callable[..., List[Dict[str, Any]]]]
    get_require_engine_runtime_running_compat: Callable[[], Callable[[], None]]
    snapshot_data_error_class: type[Exception]
    get_runtime_introspection_payload: Callable[[], Callable[[], dict[str, Any]]]
    get_system_state_payload: Callable[[], Callable[[], dict[str, Any]]]

    def assert_phase_13_read_only_endpoint(self, endpoint_path: str) -> None:
        assert endpoint_path in self.phase_13_read_only_endpoints

    def require_role(self, minimum_role: str):
        required_rank = self.role_precedence[minimum_role]
        role_header_name = self.role_header_name
        role_precedence = self.role_precedence
        # Capture a reference to self so that jwt_settings is evaluated at
        # request time.  This allows runtime monkeypatching in tests and
        # supports in-process reconfiguration without rebuilding the router.
        service = self

        def _enforce_role(
            authorization: str | None = Header(default=None),
            x_cilly_role: str | None = Header(default=None, alias=role_header_name),
        ) -> str:
            if service.jwt_settings.enabled:
                # JWT mode: require a valid Bearer token; reject legacy header.
                if authorization is None or not authorization.startswith("Bearer "):
                    raise HTTPException(status_code=401, detail="unauthorized")
                token = authorization.split(" ", 1)[1]
                try:
                    payload = decode_access_token(
                        token,
                        public_key=service.jwt_settings.public_key,
                        algorithm=service.jwt_settings.algorithm,
                    )
                except TokenValidationError:
                    raise HTTPException(status_code=401, detail="unauthorized")
                role = payload.get("role", "").strip().lower()
                caller_rank = role_precedence.get(role)
                if caller_rank is None:
                    raise HTTPException(status_code=401, detail="unauthorized")
                if caller_rank < required_rank:
                    raise HTTPException(status_code=403, detail="forbidden")
                return role

            # Header fallback: staging / trusted-proxy mode.
            # Active only when CILLY_JWT_PUBLIC_KEY is not configured.
            if x_cilly_role is None:
                raise HTTPException(status_code=401, detail="unauthorized")
            normalized_role = x_cilly_role.strip().lower()
            caller_rank = role_precedence.get(normalized_role)
            if caller_rank is None:
                raise HTTPException(status_code=401, detail="unauthorized")
            if caller_rank < required_rank:
                raise HTTPException(status_code=403, detail="forbidden")
            return normalized_role

        return _enforce_role

    def health_now(self) -> datetime:
        return datetime.now(timezone.utc)

    def resolve_analysis_db_path(self) -> str:
        analysis_db_path = self.get_analysis_db_path_override()
        if analysis_db_path:
            resolved = str(analysis_db_path)
            self.logger.debug("Analysis DB path resolved via ANALYSIS_DB_PATH override: %s", resolved)
            return resolved

        analysis_run_repo = self.get_analysis_run_repo()
        repo_path = getattr(analysis_run_repo, "_db_path", None)
        if repo_path:
            resolved = str(repo_path)
            self.logger.debug("Analysis DB path resolved via analysis_run_repo._db_path: %s", resolved)
            return resolved

        resolved = str(self.default_db_path)
        self.logger.debug("Analysis DB path resolved via DEFAULT_DB_PATH fallback: %s", resolved)
        return resolved

    def require_ingestion_run(self, ingestion_run_id: str) -> None:
        analysis_service.require_ingestion_run(
            ingestion_run_id=ingestion_run_id,
            analysis_run_repo=self.get_analysis_run_repo(),
        )

    def require_snapshot_ready(
        self,
        ingestion_run_id: str,
        *,
        symbols: list[str],
        timeframe: str = "D1",
    ) -> None:
        analysis_service.require_snapshot_ready(
            ingestion_run_id=ingestion_run_id,
            analysis_run_repo=self.get_analysis_run_repo(),
            symbols=symbols,
            timeframe=timeframe,
        )

    def require_engine_runtime_running(self) -> None:
        if not self.get_engine_runtime_guard_active():
            return

        runtime_state = self.get_runtime_controller().state
        if runtime_state != "running":
            raise HTTPException(
                status_code=self.engine_runtime_not_running_status,
                detail={
                    "code": self.engine_runtime_not_running_code,
                    "state": runtime_state,
                },
            )

    def run_snapshot_analysis(self, *args: Any, **kwargs: Any) -> List[Dict[str, Any]]:
        self.get_require_engine_runtime_running_compat()()
        try:
            return self.get_run_watchlist_analysis()(*args, **kwargs, snapshot_only=True)
        except self.snapshot_data_error_class as exc:
            self.logger.error("Snapshot data invalid: component=api error=%s", exc)
            raise HTTPException(status_code=422, detail="snapshot_data_invalid") from exc

    def analysis_service_dependencies(self) -> analysis_service.AnalysisServiceDependencies:
        return analysis_service.AnalysisServiceDependencies(
            analysis_run_repo=self.get_analysis_run_repo(),
            signal_repo=self.get_signal_repo(),
            watchlist_repo=self.get_watchlist_repo(),
            default_strategy_configs=self.get_default_strategy_configs(),
            require_ingestion_run=self.get_require_ingestion_run_compat(),
            require_snapshot_ready=self.get_require_snapshot_ready_compat(),
            run_snapshot_analysis=self.get_run_snapshot_analysis_compat(),
            resolve_analysis_db_path=self.resolve_analysis_db_path,
            create_strategy=self.get_create_strategy(),
            create_registered_strategies=self.get_create_registered_strategies(),
            trigger_operator_analysis_run=self.get_trigger_operator_analysis_run(),
        )

    def basic_screener(self, req: ScreenerRequest) -> ScreenerResponse:
        return analysis_service.basic_screener(req=req, deps=self.analysis_service_dependencies())

    def read_compliance_guard_status(self) -> ComplianceGuardStatusResponse:
        return control_plane_service.build_compliance_guard_status_response()

    def runtime_introspection(self) -> RuntimeIntrospectionResponse:
        self.assert_phase_13_read_only_endpoint("/runtime/introspection")
        return control_plane_service.build_runtime_introspection_response(
            get_runtime_introspection_payload=self.get_runtime_introspection_payload(),
        )

    def system_state(self) -> SystemStateResponse:
        return control_plane_service.build_system_state_response(
            get_system_state_payload=self.get_system_state_payload(),
        )

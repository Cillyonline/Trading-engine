from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Callable, Dict, List, Optional

from fastapi import Header, HTTPException

from ..models import ComplianceGuardStatusResponse, RuntimeIntrospectionResponse, ScreenerRequest, ScreenerResponse, SystemStateResponse
from . import analysis_service, control_plane_service


def configure_logging() -> None:
    """
    Central logging configuration for the Cilly Trading Engine.
    Runs once during app startup.

    Note: Uvicorn with --reload can import modules multiple times.
    This guard prevents duplicate handlers.
    """
    import os

    log_level = os.getenv("CILLY_LOG_LEVEL", "INFO").upper()

    root_logger = logging.getLogger()
    if root_logger.handlers:
        return

    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s %(name)s - %(message)s",
    )


@dataclass
class CompositionRuntimeService:
    logger: logging.Logger
    default_db_path: str
    role_header_name: str
    role_precedence: dict[str, int]
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

        def _enforce_role(
            x_cilly_role: str | None = Header(default=None, alias=self.role_header_name)
        ) -> str:
            if x_cilly_role is None:
                raise HTTPException(status_code=401, detail="unauthorized")

            normalized_role = x_cilly_role.strip().lower()
            caller_rank = self.role_precedence.get(normalized_role)
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

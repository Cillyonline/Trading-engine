from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from fastapi import APIRouter, Depends, HTTPException

from ..models import (
    ComplianceGuardStatusResponse,
    ExecutionControlResponse,
    RuntimeIntrospectionResponse,
    SystemStateResponse,
)
from ..services.control_plane_service import (
    ControlPlaneHealthDependencies,
    build_compliance_guard_status_response,
    build_runtime_introspection_response,
    build_system_state_response,
    health_data_payload,
    health_engine_payload,
    health_guards_payload,
    health_payload,
)


@dataclass
class ControlPlaneRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    assert_phase_13_read_only_endpoint: Callable[[str], None]
    get_health_now: Callable[[], Callable[[], Any]]
    get_resolve_analysis_db_path: Callable[[], Callable[[], str]]
    get_runtime_introspection_payload: Callable[[], Callable[[], dict[str, Any]]]
    get_runtime_health_evaluator: Callable[[], Callable[..., Any]]
    get_system_state_payload: Callable[[], Callable[[], dict[str, Any]]]
    get_start_engine_runtime: Callable[[], Callable[[], str]]
    get_shutdown_engine_runtime: Callable[[], Callable[[], str]]
    get_pause_engine_runtime: Callable[[], Callable[[], str]]
    get_resume_engine_runtime: Callable[[], Callable[[], str]]
    get_lifecycle_transition_error: Callable[[], type[Exception]]


def _health_dependencies(deps: ControlPlaneRouterDependencies) -> ControlPlaneHealthDependencies:
    return ControlPlaneHealthDependencies(
        resolve_analysis_db_path=deps.get_resolve_analysis_db_path(),
        now=deps.get_health_now(),
        get_runtime_introspection_payload=deps.get_runtime_introspection_payload(),
        evaluate_runtime_health=deps.get_runtime_health_evaluator(),
    )


def build_control_plane_router(
    *,
    deps: ControlPlaneRouterDependencies,
) -> APIRouter:
    router = APIRouter()

    @router.get("/health")
    def health_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> dict[str, Any]:
        deps.assert_phase_13_read_only_endpoint("/health")
        return health_payload(deps=_health_dependencies(deps))

    @router.get("/health/engine")
    def health_engine_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> dict[str, Any]:
        return health_engine_payload(deps=_health_dependencies(deps))

    @router.get("/health/data")
    def health_data_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> dict[str, Any]:
        return health_data_payload(deps=_health_dependencies(deps))

    @router.get("/health/guards")
    def health_guards_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> dict[str, Any]:
        return health_guards_payload(deps=_health_dependencies(deps))

    @router.get(
        "/compliance/guards/status",
        response_model=ComplianceGuardStatusResponse,
    )
    def read_compliance_guard_status_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> ComplianceGuardStatusResponse:
        return build_compliance_guard_status_response()

    @router.get(
        "/runtime/introspection",
        response_model=RuntimeIntrospectionResponse,
    )
    def runtime_introspection_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> RuntimeIntrospectionResponse:
        deps.assert_phase_13_read_only_endpoint("/runtime/introspection")
        return build_runtime_introspection_response(
            get_runtime_introspection_payload=deps.get_runtime_introspection_payload(),
        )

    @router.get(
        "/system/state",
        response_model=SystemStateResponse,
        summary="System State",
        description="Read-only system runtime state for operator inspection.",
    )
    def system_state_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> SystemStateResponse:
        return build_system_state_response(get_system_state_payload=deps.get_system_state_payload())

    @router.post(
        "/execution/start",
        response_model=ExecutionControlResponse,
        summary="Start Execution",
        description="Ensure the engine runtime is in running state using the existing lifecycle start semantics.",
    )
    def start_execution_handler(
        _: str = Depends(deps.require_role("owner")),
    ) -> ExecutionControlResponse:
        lifecycle_transition_error = deps.get_lifecycle_transition_error()
        try:
            state = deps.get_start_engine_runtime()()
        except lifecycle_transition_error as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ExecutionControlResponse(state=state)

    @router.post(
        "/execution/stop",
        response_model=ExecutionControlResponse,
        summary="Stop Execution",
        description="Stop the engine runtime using the existing lifecycle shutdown semantics.",
    )
    def stop_execution_handler(
        _: str = Depends(deps.require_role("owner")),
    ) -> ExecutionControlResponse:
        state = deps.get_shutdown_engine_runtime()()
        return ExecutionControlResponse(state=state)

    @router.post(
        "/execution/pause",
        response_model=ExecutionControlResponse,
        summary="Pause Execution",
        description="Pause engine execution while preserving runtime ownership and introspection state.",
    )
    def pause_execution_handler(
        _: str = Depends(deps.require_role("owner")),
    ) -> ExecutionControlResponse:
        lifecycle_transition_error = deps.get_lifecycle_transition_error()
        try:
            state = deps.get_pause_engine_runtime()()
        except lifecycle_transition_error as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ExecutionControlResponse(state=state)

    @router.post(
        "/execution/resume",
        response_model=ExecutionControlResponse,
        summary="Resume Execution",
        description="Resume engine execution after an operator pause.",
    )
    def resume_execution_handler(
        _: str = Depends(deps.require_role("owner")),
    ) -> ExecutionControlResponse:
        lifecycle_transition_error = deps.get_lifecycle_transition_error()
        try:
            state = deps.get_resume_engine_runtime()()
        except lifecycle_transition_error as exc:
            raise HTTPException(status_code=409, detail=str(exc)) from exc
        return ExecutionControlResponse(state=state)

    return router

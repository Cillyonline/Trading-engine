"""Bounded composition helpers for api.main."""

from .main_compat import (
    MainModuleCompatibilitySurface,
    bind_main_runtime_exports,
    bind_main_runtime_service_exports,
)
from .repositories import ApiRepositories, create_api_repositories
from .router_wiring import ApiRouterWiring, include_api_routers
from .runtime_assembly import (
    build_api_router_wiring,
    build_runtime_lifecycle_dependencies,
    create_scheduled_analysis_runner,
    create_runtime_service,
)
from .runtime_lifecycle import RuntimeLifecycleDependencies, register_runtime_lifecycle
from .runtime_settings import ApiRuntimeSettings, build_api_runtime_settings, build_default_strategy_configs

__all__ = [
    "ApiRepositories",
    "ApiRouterWiring",
    "ApiRuntimeSettings",
    "MainModuleCompatibilitySurface",
    "RuntimeLifecycleDependencies",
    "bind_main_runtime_exports",
    "bind_main_runtime_service_exports",
    "build_api_router_wiring",
    "build_api_runtime_settings",
    "build_default_strategy_configs",
    "build_runtime_lifecycle_dependencies",
    "create_scheduled_analysis_runner",
    "create_api_repositories",
    "create_runtime_service",
    "include_api_routers",
    "register_runtime_lifecycle",
]

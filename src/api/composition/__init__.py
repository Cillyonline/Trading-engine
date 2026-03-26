"""Bounded composition helpers for api.main."""

from .router_wiring import ApiRouterWiring, include_api_routers
from .runtime_lifecycle import RuntimeLifecycleDependencies, register_runtime_lifecycle

__all__ = [
    "ApiRouterWiring",
    "RuntimeLifecycleDependencies",
    "include_api_routers",
    "register_runtime_lifecycle",
]

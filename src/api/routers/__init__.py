"""Internal API router builders."""

from .analysis_router import AnalysisRouterDependencies, build_analysis_router
from .control_plane_router import ControlPlaneRouterDependencies, build_control_plane_router
from .inspection_router import InspectionRouterDependencies, build_inspection_router
from .paper_runtime_evidence_series_router import (
    PaperRuntimeEvidenceSeriesRouterDependencies,
    build_paper_runtime_evidence_series_router,
)
from .watchlists_router import WatchlistsRouterDependencies, build_watchlists_router

__all__ = [
    "AnalysisRouterDependencies",
    "ControlPlaneRouterDependencies",
    "InspectionRouterDependencies",
    "PaperRuntimeEvidenceSeriesRouterDependencies",
    "WatchlistsRouterDependencies",
    "build_analysis_router",
    "build_control_plane_router",
    "build_inspection_router",
    "build_paper_runtime_evidence_series_router",
    "build_watchlists_router",
]

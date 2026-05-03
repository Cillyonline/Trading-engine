"""Internal API router builders."""

from .analysis_router import AnalysisRouterDependencies, build_analysis_router
from .compliance_router import build_compliance_router
from .control_plane_router import ControlPlaneRouterDependencies, build_control_plane_router
from .inspection_router import InspectionRouterDependencies, build_inspection_router
from .journal_router import JournalRouterDependencies, build_journal_router
from .paper_runtime_evidence_series_router import (
    PaperRuntimeEvidenceSeriesRouterDependencies,
    build_paper_runtime_evidence_series_router,
)
from .metrics_router import MetricsRouterDependencies, build_metrics_router
from .watchlists_router import WatchlistsRouterDependencies, build_watchlists_router

__all__ = [
    "AnalysisRouterDependencies",
    "ControlPlaneRouterDependencies",
    "InspectionRouterDependencies",
    "JournalRouterDependencies",
    "MetricsRouterDependencies",
    "PaperRuntimeEvidenceSeriesRouterDependencies",
    "WatchlistsRouterDependencies",
    "build_analysis_router",
    "build_compliance_router",
    "build_control_plane_router",
    "build_inspection_router",
    "build_journal_router",
    "build_metrics_router",
    "build_paper_runtime_evidence_series_router",
    "build_watchlists_router",
]

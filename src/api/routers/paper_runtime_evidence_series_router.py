from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

from fastapi import APIRouter, Depends

from ..models.paper_runtime_evidence_series_models import PaperRuntimeEvidenceSeriesResponse
from ..services.paper_runtime_evidence_series_service import read_paper_runtime_evidence_series


@dataclass
class PaperRuntimeEvidenceSeriesRouterDependencies:
    require_role: Callable[[str], Callable[..., str]]
    get_evidence_series_dir: Callable[[], Optional[Path]]


def build_paper_runtime_evidence_series_router(
    *,
    deps: PaperRuntimeEvidenceSeriesRouterDependencies,
) -> APIRouter:
    router = APIRouter()

    @router.get(
        "/paper/runtime/evidence-series",
        response_model=PaperRuntimeEvidenceSeriesResponse,
        summary="Paper Runtime Evidence Series",
        description=(
            "Read-only inspection endpoint for offline bounded paper-runtime evidence series "
            "summaries. The endpoint only reads configured local JSON evidence artifacts and "
            "cannot trigger runtime execution, signal generation, risk logic, data ingestion, "
            "deployment, live trading, broker integration, or readiness/profitability claims."
        ),
    )
    def read_paper_runtime_evidence_series_handler(
        _: str = Depends(deps.require_role("read_only")),
    ) -> PaperRuntimeEvidenceSeriesResponse:
        return read_paper_runtime_evidence_series(
            evidence_series_dir=deps.get_evidence_series_dir(),
        )

    return router

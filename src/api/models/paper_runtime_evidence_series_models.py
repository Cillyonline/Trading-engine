from __future__ import annotations

from typing import Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict


class PaperRuntimeEvidenceSeriesBoundaryResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mode: Literal["paper_runtime_evidence_series_inspection_only"]
    analysis_boundary: Literal["offline_analysis_only"]
    inspection_statement: str
    non_live_statement: str
    out_of_scope: List[str]


class PaperRuntimeEvidenceSeriesTotalsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    eligible: int
    skipped: int
    rejected: int


class PaperRuntimeEvidenceSeriesReconciliationResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    mismatch_total: int
    status_counts: Dict[str, int]


class PaperRuntimeEvidenceSeriesSourceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    directory: Optional[str]
    pattern: str
    recursive: bool


class PaperRuntimeEvidenceSeriesResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal["not_configured", "missing", "empty", "available"]
    boundary: PaperRuntimeEvidenceSeriesBoundaryResponse
    source: PaperRuntimeEvidenceSeriesSourceResponse
    run_count: int
    run_quality_distribution: Dict[str, int]
    eligible_skipped_rejected_totals: PaperRuntimeEvidenceSeriesTotalsResponse
    skip_reason_counts: Dict[str, int]
    reconciliation: PaperRuntimeEvidenceSeriesReconciliationResponse
    mismatch_counts: Dict[str, int]
    summary_files: List[str]
    run_files: List[str]
    message: str

"""Lineage context definitions for analysis runs."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone


class LineageMissingError(ValueError):
    """Raised when required lineage data is missing or invalid."""


@dataclass(frozen=True)
class LineageContext:
    """Immutable lineage context for a single analysis run.

    Args:
        snapshot_id: Stable snapshot identifier used for the analysis.
        ingestion_run_id: Ingestion run identifier for the snapshot data.
        analysis_run_id: Deterministic analysis run identifier.
        created_at: UTC timestamp for lineage creation.
    """

    snapshot_id: str
    ingestion_run_id: str
    analysis_run_id: str
    created_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))

    def __post_init__(self) -> None:
        for field_name in ("snapshot_id", "ingestion_run_id", "analysis_run_id"):
            value = getattr(self, field_name, None)
            if value is None or not str(value).strip():
                raise LineageMissingError(f"{field_name} is required for lineage context")

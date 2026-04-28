"""Read-only paper-runtime evidence series inspection.

This module reads saved offline bounded paper-runtime JSON outputs from disk.
It does not import or execute runtime runners, paper execution, signal
generation, risk logic, data ingestion, or deployment code.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any, Literal, Optional

from ..models.paper_runtime_evidence_series_models import (
    PaperRuntimeEvidenceSeriesBoundaryResponse,
    PaperRuntimeEvidenceSeriesReconciliationResponse,
    PaperRuntimeEvidenceSeriesResponse,
    PaperRuntimeEvidenceSeriesSourceResponse,
    PaperRuntimeEvidenceSeriesTotalsResponse,
)

DEFAULT_PATTERN = "run-*.json"
RUN_QUALITY_VALUES = ("healthy", "no_eligible", "degraded")


def _boundary() -> PaperRuntimeEvidenceSeriesBoundaryResponse:
    return PaperRuntimeEvidenceSeriesBoundaryResponse(
        mode="paper_runtime_evidence_series_inspection_only",
        analysis_boundary="offline_analysis_only",
        inspection_statement=(
            "This endpoint only reads saved bounded paper-runtime evidence files and returns "
            "deterministic aggregate inspection data."
        ),
        non_live_statement=(
            "This endpoint does not trigger paper-runtime execution and does not imply live "
            "trading, broker readiness, trader validation, production readiness, or profitability."
        ),
        out_of_scope=[
            "triggering paper-runtime runs",
            "modifying paper execution behavior",
            "modifying signal generation",
            "modifying risk logic",
            "modifying data ingestion behavior",
            "deploying runtime changes",
            "live trading",
            "broker integration",
            "readiness or profitability claims",
        ],
    )


def _empty_response(
    *,
    state: Literal["not_configured", "missing", "empty", "available"],
    source_dir: Optional[Path],
    pattern: str,
    recursive: bool,
    message: str,
) -> PaperRuntimeEvidenceSeriesResponse:
    quality = {key: 0 for key in sorted(RUN_QUALITY_VALUES)}
    return PaperRuntimeEvidenceSeriesResponse(
        state=state,
        boundary=_boundary(),
        source=PaperRuntimeEvidenceSeriesSourceResponse(
            directory=str(source_dir.resolve()) if source_dir is not None else None,
            pattern=pattern,
            recursive=recursive,
        ),
        run_count=0,
        run_quality_distribution=quality,
        eligible_skipped_rejected_totals=PaperRuntimeEvidenceSeriesTotalsResponse(
            eligible=0,
            skipped=0,
            rejected=0,
        ),
        skip_reason_counts={},
        reconciliation=PaperRuntimeEvidenceSeriesReconciliationResponse(
            mismatch_total=0,
            status_counts={},
        ),
        mismatch_counts={},
        summary_files=[],
        run_files=[],
        message=message,
    )


def _to_int(value: Any) -> int:
    if isinstance(value, bool):
        return 0
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0


def _relative_path(path: Path, base: Path) -> str:
    try:
        return path.relative_to(base).as_posix()
    except ValueError:
        return path.as_posix()


def _load_run_files(
    *,
    input_dir: Path,
    pattern: str,
    recursive: bool,
) -> list[tuple[Path, dict[str, Any]]]:
    paths = input_dir.rglob(pattern) if recursive else input_dir.glob(pattern)
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted(
        (candidate for candidate in paths if candidate.is_file()),
        key=lambda item: item.as_posix(),
    ):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(payload, dict):
            loaded.append((path, payload))
    return loaded


def _execution_payload(run: dict[str, Any]) -> dict[str, Any]:
    steps = run.get("steps")
    if not isinstance(steps, dict):
        return {}
    execution_step = steps.get("bounded_paper_execution_cycle")
    if not isinstance(execution_step, dict):
        return {}
    payload = execution_step.get("payload")
    return payload if isinstance(payload, dict) else {}


def _reconciliation_payload(run: dict[str, Any]) -> dict[str, Any]:
    steps = run.get("steps")
    if isinstance(steps, dict):
        reconciliation_step = steps.get("reconciliation")
        if isinstance(reconciliation_step, dict):
            payload = reconciliation_step.get("payload")
            if isinstance(payload, dict):
                return payload

    verification_surfaces = run.get("verification_surfaces")
    if isinstance(verification_surfaces, dict):
        payload = verification_surfaces.get("paper-reconciliation")
        if isinstance(payload, dict):
            return payload

    return {}


def _run_quality(run: dict[str, Any]) -> str:
    value = run.get("run_quality_status")
    if isinstance(value, str) and value:
        return value
    if run.get("status") == "failed":
        return "degraded"
    return "unknown"


def _skip_reason_from_result(result: dict[str, Any]) -> str | None:
    outcome = result.get("outcome")
    if isinstance(outcome, str) and outcome.startswith("skip:"):
        return outcome.removeprefix("skip:")
    reason = result.get("reason")
    if isinstance(reason, str) and reason:
        return reason.removeprefix("skip:")
    return None


def _sorted_counter(counter: Counter[str]) -> dict[str, int]:
    return {key: counter[key] for key in sorted(counter)}


def read_paper_runtime_evidence_series(
    *,
    evidence_series_dir: Optional[Path],
    pattern: str = DEFAULT_PATTERN,
    recursive: bool = True,
) -> PaperRuntimeEvidenceSeriesResponse:
    if evidence_series_dir is None:
        return _empty_response(
            state="not_configured",
            source_dir=None,
            pattern=pattern,
            recursive=recursive,
            message="CILLY_PAPER_RUNTIME_EVIDENCE_SERIES_DIR is not configured.",
        )

    base = evidence_series_dir.resolve()
    if not base.exists():
        return _empty_response(
            state="missing",
            source_dir=base,
            pattern=pattern,
            recursive=recursive,
            message="Configured paper-runtime evidence series directory does not exist.",
        )
    if not base.is_dir():
        return _empty_response(
            state="missing",
            source_dir=base,
            pattern=pattern,
            recursive=recursive,
            message="Configured paper-runtime evidence series path is not a directory.",
        )

    loaded = _load_run_files(input_dir=base, pattern=pattern, recursive=recursive)
    if not loaded:
        return _empty_response(
            state="empty",
            source_dir=base,
            pattern=pattern,
            recursive=recursive,
            message="Configured paper-runtime evidence series directory contains no matching run files.",
        )

    run_quality_counts: Counter[str] = Counter()
    skip_reason_counts: Counter[str] = Counter()
    reconciliation_status_counts: Counter[str] = Counter()
    mismatch_counts: Counter[str] = Counter()
    eligible_total = 0
    skipped_total = 0
    rejected_total = 0
    mismatch_total = 0
    summary_files: list[str] = []
    run_files: list[str] = []

    for path, run in loaded:
        run_files.append(_relative_path(path, base))
        run_quality_counts[_run_quality(run)] += 1

        execution = _execution_payload(run)
        eligible_total += _to_int(execution.get("eligible"))
        skipped_total += _to_int(execution.get("skipped"))
        rejected_total += _to_int(execution.get("rejected"))

        results = execution.get("results")
        if isinstance(results, list):
            for result in results:
                if not isinstance(result, dict):
                    continue
                reason = _skip_reason_from_result(result)
                if reason:
                    skip_reason_counts[reason] += 1

        reconciliation = _reconciliation_payload(run)
        status = reconciliation.get("status")
        if isinstance(status, str) and status:
            reconciliation_status_counts[status] += 1
        elif reconciliation.get("ok") is True:
            reconciliation_status_counts["ok"] += 1
        elif reconciliation.get("ok") is False:
            reconciliation_status_counts["fail"] += 1
        else:
            reconciliation_status_counts["unknown"] += 1

        mismatches = _to_int(reconciliation.get("mismatches"))
        mismatch_total += mismatches
        if mismatches > 0:
            mismatch_counts[_relative_path(path, base)] = mismatches

        summary_file = run.get("summary_file")
        if isinstance(summary_file, str) and summary_file:
            summary_files.append(summary_file)

    quality = _sorted_counter(run_quality_counts)
    for value in RUN_QUALITY_VALUES:
        quality.setdefault(value, 0)

    return PaperRuntimeEvidenceSeriesResponse(
        state="available",
        boundary=_boundary(),
        source=PaperRuntimeEvidenceSeriesSourceResponse(
            directory=str(base),
            pattern=pattern,
            recursive=recursive,
        ),
        run_count=len(loaded),
        run_quality_distribution=dict(sorted(quality.items())),
        eligible_skipped_rejected_totals=PaperRuntimeEvidenceSeriesTotalsResponse(
            eligible=eligible_total,
            skipped=skipped_total,
            rejected=rejected_total,
        ),
        skip_reason_counts=_sorted_counter(skip_reason_counts),
        reconciliation=PaperRuntimeEvidenceSeriesReconciliationResponse(
            mismatch_total=mismatch_total,
            status_counts=_sorted_counter(reconciliation_status_counts),
        ),
        mismatch_counts=_sorted_counter(mismatch_counts),
        summary_files=sorted(summary_files),
        run_files=sorted(run_files),
        message="Paper-runtime evidence series summary is available for read-only inspection.",
    )

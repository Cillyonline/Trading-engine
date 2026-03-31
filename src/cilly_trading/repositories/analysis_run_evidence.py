from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping

from cilly_trading.engine.result_artifact import canonical_json_bytes

DEFAULT_ANALYSIS_EVIDENCE_DIR_ENV_VAR = "CILLY_ANALYSIS_EVIDENCE_DIR"
DEFAULT_ANALYSIS_EVIDENCE_ROOT = (
    Path(__file__).resolve().parents[3] / "runs" / "analysis_run_evidence"
)

EVIDENCE_ARTIFACT_NAME = "analysis-run-evidence.json"
EVIDENCE_HASH_NAME = "analysis-run-evidence.sha256"
OPERATOR_REVIEW_ARTIFACT_NAME = "operator-review.json"
OPERATOR_REVIEW_HASH_NAME = "operator-review.sha256"


def resolve_analysis_evidence_root() -> Path:
    configured_path = os.getenv(DEFAULT_ANALYSIS_EVIDENCE_DIR_ENV_VAR)
    if configured_path:
        return Path(configured_path).expanduser()
    return DEFAULT_ANALYSIS_EVIDENCE_ROOT


def _parse_iso8601_utc(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=UTC)
    return parsed.astimezone(UTC)


def _review_week_label(snapshot_created_at: str | None, persisted_created_at: str) -> str:
    reference = _parse_iso8601_utc(snapshot_created_at) or _parse_iso8601_utc(persisted_created_at)
    if reference is None:
        return "unknown-week"
    iso_year, iso_week, _ = reference.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _write_artifact(
    artifact_dir: Path,
    *,
    artifact_name: str,
    hash_name: str,
    payload: Mapping[str, Any],
) -> tuple[Path, Path, str]:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    artifact_bytes = canonical_json_bytes(payload)
    artifact_path = artifact_dir / artifact_name
    artifact_path.write_bytes(artifact_bytes)

    artifact_sha256 = _sha256_bytes(artifact_bytes)
    hash_path = artifact_dir / hash_name
    hash_path.write_text(f"{artifact_sha256}\n", encoding="utf-8")
    return artifact_path, hash_path, artifact_sha256


def _normalize_symbols(value: Any) -> list[str]:
    if not isinstance(value, list):
        return []
    normalized: list[str] = []
    for item in value:
        if isinstance(item, str) and item.strip():
            normalized.append(item.strip())
    return normalized


def _classify_outcome(result_payload: Mapping[str, Any]) -> str:
    if "ranked_results" in result_payload:
        failures = result_payload.get("failures")
        ranked_results = result_payload.get("ranked_results")
        failure_count = len(failures) if isinstance(failures, list) else 0
        ranked_count = len(ranked_results) if isinstance(ranked_results, list) else 0
        if failure_count > 0:
            return "isolated_symbol_failure"
        if ranked_count == 0:
            return "empty_success"
        return "populated_success"

    signals = result_payload.get("signals")
    signal_count = len(signals) if isinstance(signals, list) else 0
    if signal_count == 0:
        return "empty_success"
    return "populated_success"


def _workflow_details(
    request_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any],
) -> dict[str, Any]:
    if request_payload.get("workflow") == "watchlist_execution":
        watchlist_id = request_payload.get("watchlist_id") or result_payload.get("watchlist_id")
        watchlist_name = result_payload.get("watchlist_name")
        comparison_payload = {
            key: value
            for key, value in request_payload.items()
            if key != "ingestion_run_id"
        }
        return {
            "kind": "watchlist_execution",
            "endpoint": "POST /watchlists/{watchlist_id}/execute",
            "scope": {
                "watchlist_id": watchlist_id,
                "watchlist_name": watchlist_name,
            },
            "comparison_payload": comparison_payload,
            "comparison_scope": f"watchlist:{watchlist_id}",
        }

    symbol = request_payload.get("symbol") or result_payload.get("symbol")
    strategy = request_payload.get("strategy") or result_payload.get("strategy")
    comparison_payload = {
        key: value
        for key, value in request_payload.items()
        if key != "ingestion_run_id"
    }
    return {
        "kind": "single_symbol_analysis",
        "endpoint": "POST /analysis/run",
        "scope": {
            "symbol": symbol,
            "strategy": strategy,
        },
        "comparison_payload": comparison_payload,
        "comparison_scope": f"analysis:{symbol}:{strategy}",
    }


def _result_counts(result_payload: Mapping[str, Any]) -> dict[str, int]:
    if "ranked_results" in result_payload:
        ranked_results = result_payload.get("ranked_results")
        failures = result_payload.get("failures")
        return {
            "ranked_results": len(ranked_results) if isinstance(ranked_results, list) else 0,
            "failures": len(failures) if isinstance(failures, list) else 0,
        }

    signals = result_payload.get("signals")
    return {
        "signals": len(signals) if isinstance(signals, list) else 0,
    }


def _build_analysis_run_evidence_bundle(
    *,
    analysis_run_id: str,
    ingestion_run_id: str,
    request_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any],
    persisted_created_at: str,
    ingestion_metadata: Mapping[str, Any] | None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    root = evidence_root or resolve_analysis_evidence_root()
    snapshot_created_at = None
    snapshot_symbols: list[str] = []
    if ingestion_metadata is not None:
        raw_snapshot_created_at = ingestion_metadata.get("created_at")
        snapshot_created_at = (
            str(raw_snapshot_created_at) if isinstance(raw_snapshot_created_at, str) else None
        )
        snapshot_symbols = _normalize_symbols(ingestion_metadata.get("symbols"))

    review_week = _review_week_label(snapshot_created_at, persisted_created_at)
    artifact_dir = root / review_week / analysis_run_id

    workflow = _workflow_details(request_payload, result_payload)
    comparison_payload = workflow["comparison_payload"]
    comparison_json = json.dumps(
        comparison_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    request_json = json.dumps(
        request_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    result_json = json.dumps(
        result_payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )

    evidence_payload = {
        "analysis_run_id": analysis_run_id,
        "artifact": "analysis_run_evidence",
        "artifact_version": "1",
        "comparison": {
            "comparison_key": hashlib.sha256(comparison_json.encode("utf-8")).hexdigest(),
            "comparison_payload": comparison_payload,
            "comparison_scope": workflow["comparison_scope"],
            "request_sha256": hashlib.sha256(request_json.encode("utf-8")).hexdigest(),
            "result_sha256": hashlib.sha256(result_json.encode("utf-8")).hexdigest(),
            "review_week": review_week,
        },
        "ingestion_run_id": ingestion_run_id,
        "persisted_created_at": persisted_created_at,
        "request": dict(request_payload),
        "result": dict(result_payload),
        "snapshot": {
            "created_at": snapshot_created_at,
            "fingerprint_hash": (
                ingestion_metadata.get("fingerprint_hash") if ingestion_metadata else None
            ),
            "ingestion_run_id": ingestion_run_id,
            "source": ingestion_metadata.get("source") if ingestion_metadata else None,
            "symbols": snapshot_symbols,
            "symbols_count": len(snapshot_symbols),
            "timeframe": ingestion_metadata.get("timeframe") if ingestion_metadata else None,
        },
        "workflow": {
            "endpoint": workflow["endpoint"],
            "kind": workflow["kind"],
            "outcome_classification": _classify_outcome(result_payload),
            "scope": workflow["scope"],
        },
    }
    evidence_sha256 = _sha256_bytes(canonical_json_bytes(evidence_payload))

    operator_review_payload = {
        "analysis_run_id": analysis_run_id,
        "artifact": "operator_review",
        "artifact_version": "1",
        "artifacts": {
            "evidence_file": EVIDENCE_ARTIFACT_NAME,
            "evidence_sha256_file": EVIDENCE_HASH_NAME,
        },
        "comparison": {
            "comparison_key": evidence_payload["comparison"]["comparison_key"],
            "comparison_scope": workflow["comparison_scope"],
            "request_sha256": evidence_payload["comparison"]["request_sha256"],
            "result_sha256": evidence_payload["comparison"]["result_sha256"],
            "review_week": review_week,
        },
        "counts": _result_counts(result_payload),
        "ingestion_run_id": ingestion_run_id,
        "outcome_classification": evidence_payload["workflow"]["outcome_classification"],
        "persisted_created_at": persisted_created_at,
        "scope": workflow["scope"],
        "snapshot": {
            "created_at": snapshot_created_at,
            "fingerprint_hash": (
                ingestion_metadata.get("fingerprint_hash") if ingestion_metadata else None
            ),
            "timeframe": ingestion_metadata.get("timeframe") if ingestion_metadata else None,
        },
        "workflow_kind": workflow["kind"],
    }

    public_metadata = {
        "artifact_dir": str(artifact_dir),
        "evidence_file": str(artifact_dir / EVIDENCE_ARTIFACT_NAME),
        "evidence_sha256": evidence_sha256,
        "evidence_sha256_file": str(artifact_dir / EVIDENCE_HASH_NAME),
        "operator_review_file": str(artifact_dir / OPERATOR_REVIEW_ARTIFACT_NAME),
        "operator_review_sha256": _sha256_bytes(canonical_json_bytes(operator_review_payload)),
        "operator_review_sha256_file": str(artifact_dir / OPERATOR_REVIEW_HASH_NAME),
        "review_week": review_week,
    }
    return {
        "metadata": public_metadata,
        "evidence_payload": evidence_payload,
        "operator_review_payload": operator_review_payload,
    }


def build_analysis_run_evidence_metadata(
    *,
    analysis_run_id: str,
    ingestion_run_id: str,
    request_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any],
    persisted_created_at: str,
    ingestion_metadata: Mapping[str, Any] | None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    bundle = _build_analysis_run_evidence_bundle(
        analysis_run_id=analysis_run_id,
        ingestion_run_id=ingestion_run_id,
        request_payload=request_payload,
        result_payload=result_payload,
        persisted_created_at=persisted_created_at,
        ingestion_metadata=ingestion_metadata,
        evidence_root=evidence_root,
    )
    return dict(bundle["metadata"])


def write_analysis_run_evidence_artifacts(
    *,
    analysis_run_id: str,
    ingestion_run_id: str,
    request_payload: Mapping[str, Any],
    result_payload: Mapping[str, Any],
    persisted_created_at: str,
    ingestion_metadata: Mapping[str, Any] | None,
    evidence_root: Path | None = None,
) -> dict[str, Any]:
    bundle = _build_analysis_run_evidence_bundle(
        analysis_run_id=analysis_run_id,
        ingestion_run_id=ingestion_run_id,
        request_payload=request_payload,
        result_payload=result_payload,
        persisted_created_at=persisted_created_at,
        ingestion_metadata=ingestion_metadata,
        evidence_root=evidence_root,
    )
    artifact_dir = Path(bundle["metadata"]["artifact_dir"])
    _write_artifact(
        artifact_dir,
        artifact_name=EVIDENCE_ARTIFACT_NAME,
        hash_name=EVIDENCE_HASH_NAME,
        payload=bundle["evidence_payload"],
    )
    _write_artifact(
        artifact_dir,
        artifact_name=OPERATOR_REVIEW_ARTIFACT_NAME,
        hash_name=OPERATOR_REVIEW_HASH_NAME,
        payload=bundle["operator_review_payload"],
    )
    return dict(bundle["metadata"])

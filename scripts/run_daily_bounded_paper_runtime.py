"""One-command bounded daily paper runtime runner (OPS-P64).

Runs the OPS-P63 daily bounded workflow in this exact order:
1) Snapshot ingestion
2) Analysis and signal generation
3) Bounded paper execution cycle
4) Reconciliation
5) Evidence capture

Non-live boundary:
    This runner orchestrates bounded paper-runtime scripts and read-only
    inspection captures only. It does not place live orders, does not call
    broker APIs, and does not claim production readiness.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB_PATH = ROOT / "cilly_trading.db"
DEFAULT_SNAPSHOT_EVIDENCE_DIR = ROOT / "runs" / "snapshot_ingestion"
DEFAULT_EXECUTION_EVIDENCE_DIR = ROOT / "runs" / "paper-execution"
DEFAULT_RECONCILIATION_EVIDENCE_DIR = ROOT / "runs" / "reconciliation"
DEFAULT_REVIEW_EVIDENCE_DIR = ROOT / "runs" / "daily-runtime"
DEFAULT_RUN_RECORD_DIR = ROOT / "runs" / "daily-runtime"

ROLE_HEADER_NAME = "X-Cilly-Role"
ROLE_OPERATOR = "operator"
ROLE_READ_ONLY = "read_only"

STEP_ORDER = (
    "snapshot_ingestion",
    "analysis_signal_generation",
    "bounded_paper_execution_cycle",
    "reconciliation",
    "evidence_capture",
)

EXIT_CODE_SUCCESS = 0
EXIT_CODE_SNAPSHOT_FAILED = 10
EXIT_CODE_ANALYSIS_FAILED = 11
EXIT_CODE_EXECUTION_FAILED = 12
EXIT_CODE_RECONCILIATION_FAILED = 13
EXIT_CODE_EVIDENCE_FAILED = 14

RUN_QUALITY_CLASSIFICATION_VERSION = 1
OPERATOR_ACTION_CONTRACT_VERSION = 1
PAPER_STATE_FRESHNESS_CLASSIFICATION_VERSION = 1
PAPER_STATE_FRESHNESS_STALE_AFTER_SECONDS = 24 * 60 * 60
OPERATOR_REVIEW_OUTCOME_ARTIFACT_VERSION = 1
OPERATOR_REVIEW_OUTCOME_WORKFLOW_ID = "bounded_daily_paper_runtime"
OPERATOR_REVIEW_OUTCOME_WORKFLOW_VERSION = "OPS-P64"
OPERATOR_REVIEW_OUTCOME_ARTIFACT_ID = "operator-review"
OPERATOR_REVIEW_OUTCOME_NON_INFERENCE_STATEMENT = (
    "This artifact records bounded paper-runtime observations only. It is not trader validation, "
    "not profitability evidence, and not broker/live readiness evidence."
)
STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_VERSION = 1
STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_ID = (
    "ops_bounded_stale_open_paper_trade_review"
)
STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_MODE = "bounded_stale_paper_trade_review"
STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ARTIFACT_VERSION = 1
STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ARTIFACT_ID = (
    "ops_bounded_stale_open_paper_trade_review_outcome"
)
STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ALLOWED_DECISIONS: frozenset[str] = frozenset(
    {
        "acknowledged_no_action",
        "needs_followup",
        "external_action_recorded",
        "deferred",
    }
)
STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_PROHIBITED_DECISIONS: frozenset[str] = frozenset(
    {
        "auto_close_trade",
        "reset_paper_state",
        "mark_to_market",
        "force_eligible_trade_creation",
        "lower_thresholds_to_bypass_stale_blockers",
        "infer_trader_validation_or_profitability",
    }
)
STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_REVIEWER_NOT_PROVIDED = "not_provided"
STALE_OPEN_PAPER_TRADE_REVIEW_ALLOWED_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "action_code": "inspect_trade_lifecycle_evidence",
        "action_summary": (
            "Inspect the captured per-trade lifecycle evidence (trade_id, position_id, "
            "symbol, strategy, direction, status, opened_at, account_as_of, ages, freshness, "
            "duplicate_entry_blocker)."
        ),
    },
    {
        "action_code": "compare_with_paper_inspection_surfaces",
        "action_summary": (
            "Compare the lifecycle evidence with the latest paper-account, paper-trades, "
            "paper-positions, and paper-reconciliation read-only surfaces captured by this run."
        ),
    },
    {
        "action_code": "record_review_outcome_externally",
        "action_summary": (
            "Record the manual review outcome externally or in an explicitly non-mutating "
            "evidence artifact; do not modify paper state to communicate the result."
        ),
    },
)
STALE_OPEN_PAPER_TRADE_REVIEW_PROHIBITED_ACTIONS: tuple[dict[str, str], ...] = (
    {
        "action_code": "auto_close_trade",
        "action_summary": "Do not auto-close the stale open paper trade.",
    },
    {
        "action_code": "reset_paper_state",
        "action_summary": "Do not reset paper account, paper trades, or paper positions state.",
    },
    {
        "action_code": "mark_to_market",
        "action_summary": "Do not mark the stale paper position to market.",
    },
    {
        "action_code": "force_eligible_trade_creation",
        "action_summary": "Do not force eligible trade creation to bypass the stale duplicate-entry blocker.",
    },
    {
        "action_code": "lower_thresholds_to_bypass_stale_blockers",
        "action_summary": "Do not lower score, risk, or duplicate thresholds to bypass stale blockers.",
    },
    {
        "action_code": "infer_trader_validation_or_profitability",
        "action_summary": (
            "Do not infer trader validation, profitability, broker readiness, live readiness, "
            "or production readiness from this stale-state review evidence."
        ),
    },
)
STALE_OPEN_PAPER_TRADE_REVIEW_NON_INFERENCE_STATEMENT = (
    "This bounded stale open paper-trade review evidence is operationally useful for "
    "evidence hygiene only. It is not trader validation and not profitability evidence; "
    "it does not assert broker readiness, live readiness, or production readiness."
)
STALE_OPEN_PAPER_TRADE_REVIEW_GUIDANCE_BY_STATUS: dict[str, str] = {
    "no_review_required": (
        "No stale or unknown-freshness open paper trades observed in this bounded run; "
        "no operator review action is required from this workflow surface."
    ),
    "review_required": (
        "Operator must inspect the listed stale or unknown-freshness open paper trades, "
        "compare lifecycle evidence with the bounded paper-account/trades/positions/reconciliation "
        "surfaces, and record the review outcome without mutating paper state."
    ),
}
PAPER_STATE_DUPLICATE_ENTRY_REASON_PATTERN = re.compile(
    r"^open trade exists for \((?P<symbol>[^,]+),\s*(?P<strategy>[^,]+),\s*(?P<direction>[^)]+)\)$"
)
PAPER_STATE_OPERATOR_REVIEW_GUIDANCE = {
    "fresh": (
        "Open paper state is current within the bounded daily freshness window; "
        "record duplicate-entry blocking as technically valid paper-state evidence."
    ),
    "stale": (
        "Open paper state is older than the bounded daily freshness window; "
        "operator must review lifecycle evidence before interpreting duplicate-entry blockers."
    ),
    "unknown": (
        "Open paper state freshness cannot be established from available metadata; "
        "operator must review account and trade lifecycle evidence before interpretation."
    ),
}

RUN_QUALITY_OPERATOR_ACTION_CONTRACTS: dict[str, dict[str, str]] = {
    "healthy": {
        "action_category": "informational",
        "action_code": "record_and_continue",
        "action_summary": (
            "Record the bounded daily runtime evidence and continue the next scheduled bounded run."
        ),
        "escalation_boundary": (
            "No escalation from this state alone. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "no_eligible": {
        "action_category": "review_required",
        "action_code": "review_no_eligible_and_record",
        "action_summary": (
            "Review the bounded no-eligible outcome, confirm skip reasons and inputs, and record the run without retrying solely to force activity."
        ),
        "escalation_boundary": (
            "Escalate only when adjacent bounded evidence is contradictory or the no-eligible pattern is unexpected for the stated inputs. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "degraded": {
        "action_category": "blocking",
        "action_code": "stop_and_open_follow_up",
        "action_summary": (
            "Treat the bounded run as blocked for continuation claims, investigate the degraded evidence, and open or update follow-up before the next bounded decision."
        ),
        "escalation_boundary": (
            "Do not continue staged evaluation claims from this run until the degraded cause is resolved. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
}

FAILED_STEP_OPERATOR_ACTION_CONTRACTS: dict[str, dict[str, str]] = {
    "snapshot_ingestion": {
        "action_category": "retry_required",
        "action_code": "fix_pre_execution_failure_and_rerun",
        "action_summary": (
            "Correct the pre-execution failure cause and rerun the bounded daily workflow."
        ),
        "escalation_boundary": (
            "Retry is bounded to failures before paper execution starts. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "analysis_signal_generation": {
        "action_category": "retry_required",
        "action_code": "fix_pre_execution_failure_and_rerun",
        "action_summary": (
            "Correct the pre-execution failure cause and rerun the bounded daily workflow."
        ),
        "escalation_boundary": (
            "Retry is bounded to failures before paper execution starts. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "bounded_paper_execution_cycle": {
        "action_category": "blocking",
        "action_code": "stop_and_investigate_before_rerun",
        "action_summary": (
            "Stop and investigate the bounded execution failure before any rerun decision."
        ),
        "escalation_boundary": (
            "Do not rerun the full workflow blindly after execution has started. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "reconciliation": {
        "action_category": "blocking",
        "action_code": "stop_and_investigate_before_rerun",
        "action_summary": (
            "Stop and investigate the bounded reconciliation failure before any rerun decision."
        ),
        "escalation_boundary": (
            "Do not continue staged evaluation claims until reconciliation is resolved. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
    "evidence_capture": {
        "action_category": "blocking",
        "action_code": "stop_and_investigate_before_rerun",
        "action_summary": (
            "Stop and investigate the missing or failed bounded evidence capture before any rerun decision."
        ),
        "escalation_boundary": (
            "Do not rerun the full workflow blindly after execution-stage evidence has already been produced. Do not treat bounded paper evidence as live, broker, or production readiness."
        ),
    },
}

DEFAULT_FAILED_STEP_OPERATOR_ACTION_CONTRACT: dict[str, str] = {
    "action_category": "blocking",
    "action_code": "stop_and_investigate_before_rerun",
    "action_summary": (
        "Stop and investigate the bounded runtime failure before any rerun decision."
    ),
    "escalation_boundary": (
        "Do not treat bounded paper evidence as live, broker, or production readiness."
    ),
}


class DailyRuntimeStepError(RuntimeError):
    def __init__(
        self,
        *,
        step: str,
        exit_code: int,
        detail: str,
        context: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(detail)
        self.step = step
        self.exit_code = exit_code
        self.detail = detail
        self.context = context or {}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(microsecond=0)


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python scripts/run_daily_bounded_paper_runtime.py",
        description=(
            "Run the OPS-P63 bounded daily paper runtime workflow in one command. "
            "Stops on first failure with bounded error output."
        ),
    )
    parser.add_argument(
        "--db-path",
        default=str(DEFAULT_DB_PATH),
        help="SQLite database path. Default: cilly_trading.db in repo root.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:18000",
        help="API base URL used for analysis trigger and read-only captures.",
    )
    parser.add_argument(
        "--symbols",
        default="AAPL,MSFT,NVDA,GS,WMT,COST",
        help="Comma-separated symbol list for snapshot ingestion.",
    )
    parser.add_argument(
        "--timeframe",
        default="D1",
        help="Snapshot timeframe for ingestion. Default: D1.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=90,
        help="Snapshot candle limit per symbol. Default: 90.",
    )
    parser.add_argument(
        "--provider",
        default="yfinance",
        help="Snapshot provider for ingestion. Default: yfinance.",
    )
    parser.add_argument(
        "--analysis-symbol",
        default="AAPL",
        help="Symbol used for the analysis/signal-generation step.",
    )
    parser.add_argument(
        "--analysis-strategy",
        default="RSI2",
        help="Strategy used for the analysis/signal-generation step.",
    )
    parser.add_argument(
        "--analysis-market-type",
        default="stock",
        choices=("stock", "crypto"),
        help="Market type for the analysis step. Default: stock.",
    )
    parser.add_argument(
        "--analysis-lookback-days",
        type=int,
        default=200,
        help="Lookback days for the analysis step. Default: 200.",
    )
    parser.add_argument(
        "--snapshot-evidence-dir",
        default=str(DEFAULT_SNAPSHOT_EVIDENCE_DIR),
        help="Evidence output dir for snapshot ingestion.",
    )
    parser.add_argument(
        "--execution-evidence-dir",
        default=str(DEFAULT_EXECUTION_EVIDENCE_DIR),
        help="Evidence output dir for bounded paper execution.",
    )
    parser.add_argument(
        "--reconciliation-evidence-dir",
        default=str(DEFAULT_RECONCILIATION_EVIDENCE_DIR),
        help="Evidence output dir for reconciliation.",
    )
    parser.add_argument(
        "--review-evidence-dir",
        default=str(DEFAULT_REVIEW_EVIDENCE_DIR),
        help="Evidence output dir for review artifact generation.",
    )
    parser.add_argument(
        "--run-record-dir",
        default=str(DEFAULT_RUN_RECORD_DIR),
        help="Base directory for endpoint snapshot run-record captures.",
    )
    parser.add_argument(
        "--signals-limit",
        type=int,
        default=100,
        help="Limit used when capturing /signals run-record evidence. Default: 100.",
    )
    return parser.parse_args(argv)


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def _request_json(
    url: str,
    *,
    headers: dict[str, str],
    method: str = "GET",
    payload: dict[str, Any] | None = None,
) -> dict[str, Any]:
    encoded_payload = None
    request_headers = dict(headers)
    if payload is not None:
        encoded_payload = json.dumps(payload, sort_keys=True).encode("utf-8")
        request_headers["Content-Type"] = "application/json"

    request = urllib.request.Request(
        url=url,
        data=encoded_payload,
        headers=request_headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=10) as response:  # nosec B310
        raw = response.read().decode("utf-8")

    parsed = json.loads(raw)
    if not isinstance(parsed, dict):
        raise ValueError(f"expected JSON object from {url}")
    return parsed


def _extract_last_json_record(*streams: str) -> dict[str, Any] | None:
    last_payload: dict[str, Any] | None = None
    for stream in streams:
        if not stream:
            continue
        for line in stream.splitlines():
            candidate = line.strip()
            if not candidate:
                continue
            if not (candidate.startswith("{") and candidate.endswith("}")):
                continue
            try:
                parsed = json.loads(candidate)
            except json.JSONDecodeError:
                continue
            if isinstance(parsed, dict):
                last_payload = parsed
    return last_payload


def _write_json_file(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n",
        encoding="utf-8",
    )


def _json_file_bytes(payload: dict[str, Any]) -> bytes:
    return (json.dumps(payload, sort_keys=True, ensure_ascii=True) + "\n").encode("utf-8")


def _write_json_file_with_sha256(path: Path, payload: dict[str, Any]) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    json_bytes = _json_file_bytes(payload)
    path.write_bytes(json_bytes)
    digest = hashlib.sha256(json_bytes).hexdigest()
    path.with_suffix(f"{path.suffix}.sha256").write_text(f"{digest}  {path.name}\n", encoding="ascii")
    return digest


def _invoke_python_script(
    *,
    script_path: Path,
    script_args: list[str],
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> subprocess.CompletedProcess[str]:
    command = [sys.executable, str(script_path), *script_args]
    return run_command(command)


def _build_error_payload(
    *,
    step: str,
    detail: str,
    started_at: datetime,
    failed_at: datetime,
    steps_completed: list[str],
    ingestion_run_id: str | None,
    context: dict[str, Any] | None,
) -> dict[str, Any]:
    payload: dict[str, Any] = {
        "code": "daily_bounded_runtime_failed",
        "detail": detail,
        "failed_at": failed_at.isoformat(),
        "failed_step": step,
        "run_quality_status": "degraded",
        "started_at": started_at.isoformat(),
        "status": "failed",
        "step_order": list(STEP_ORDER),
        "steps_completed": steps_completed,
        "operator_action_contract_version": OPERATOR_ACTION_CONTRACT_VERSION,
        "operator_action_contract": _build_failed_step_action_contract(step),
    }
    if ingestion_run_id is not None:
        payload["ingestion_run_id"] = ingestion_run_id
    if context:
        payload["context"] = context
    return payload


def _to_int_or_none(value: Any) -> int | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return None
    return None


def _parse_iso_datetime(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    normalized = value.strip()
    if normalized.endswith("Z"):
        normalized = f"{normalized[:-1]}+00:00"
    try:
        parsed = datetime.fromisoformat(normalized)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _items_from_payload(payload: dict[str, Any] | None, key: str = "items") -> list[dict[str, Any]]:
    if not isinstance(payload, dict):
        return []
    raw_items = payload.get(key)
    if not isinstance(raw_items, list):
        return []
    return [item for item in raw_items if isinstance(item, dict)]


def _normalized_trade_tuple(item: dict[str, Any]) -> tuple[str, str, str] | None:
    symbol = item.get("symbol")
    strategy = item.get("strategy_id", item.get("strategy"))
    direction = item.get("direction")
    if not all(isinstance(value, str) and value for value in (symbol, strategy, direction)):
        return None
    return (str(symbol), str(strategy), str(direction))


def _duplicate_entry_reason_tuple(reason: Any) -> tuple[str, str, str] | None:
    if not isinstance(reason, str):
        return None
    match = PAPER_STATE_DUPLICATE_ENTRY_REASON_PATTERN.match(reason.strip())
    if match is None:
        return None
    return (
        match.group("symbol").strip(),
        match.group("strategy").strip(),
        match.group("direction").strip(),
    )


def _duplicate_entry_blocker_index(
    *,
    execution_payload: dict[str, Any] | None,
    signals_payload: dict[str, Any] | None,
) -> dict[tuple[str, str, str], list[str]]:
    """Return a deterministic index of duplicate-entry blocker keys to reasons.

    Each key is a normalized ``(symbol, strategy, direction)`` tuple. The
    associated value is the ordered list of execution-result ``reason`` strings
    that produced the duplicate-entry skip for that key. Reasons may be empty
    when the execution result did not carry a reason string.
    """

    signals_by_id: dict[str, dict[str, Any]] = {}
    for signal in _items_from_payload(signals_payload):
        signal_id = signal.get("signal_id")
        if isinstance(signal_id, str) and signal_id:
            signals_by_id[signal_id] = signal

    blocker_index: dict[tuple[str, str, str], list[str]] = {}
    results = _items_from_payload(execution_payload, key="results")
    for result in results:
        outcome = result.get("outcome")
        reason = result.get("reason")
        if outcome != "skip:duplicate_entry" and reason != "skip:duplicate_entry":
            continue
        key: tuple[str, str, str] | None = _normalized_trade_tuple(result)
        if key is None:
            key = _duplicate_entry_reason_tuple(reason)
        if key is None:
            signal_id = result.get("signal_id")
            if isinstance(signal_id, str):
                key = _normalized_trade_tuple(signals_by_id.get(signal_id, {}))
        if key is None:
            continue
        bucket = blocker_index.setdefault(key, [])
        if isinstance(reason, str) and reason and reason != "skip:duplicate_entry":
            bucket.append(reason)
    return blocker_index


def _duplicate_entry_blocker_keys(
    *,
    execution_payload: dict[str, Any] | None,
    signals_payload: dict[str, Any] | None,
) -> set[tuple[str, str, str]]:
    return set(
        _duplicate_entry_blocker_index(
            execution_payload=execution_payload,
            signals_payload=signals_payload,
        ).keys()
    )


def _classify_paper_state_freshness(
    *,
    account_as_of: Any,
    observed_at: datetime,
) -> tuple[str, int | None]:
    as_of = _parse_iso_datetime(account_as_of)
    if as_of is None:
        return "unknown", None
    age_seconds = int((observed_at.astimezone(timezone.utc) - as_of).total_seconds())
    if age_seconds < 0:
        return "unknown", age_seconds
    if age_seconds > PAPER_STATE_FRESHNESS_STALE_AFTER_SECONDS:
        return "stale", age_seconds
    return "fresh", age_seconds


def _classify_timestamp_freshness(
    *,
    timestamp: Any,
    observed_at: datetime,
) -> tuple[str, int | None]:
    parsed = _parse_iso_datetime(timestamp)
    if parsed is None:
        return "unknown", None
    age_seconds = int((observed_at.astimezone(timezone.utc) - parsed).total_seconds())
    if age_seconds < 0:
        return "unknown", age_seconds
    if age_seconds > PAPER_STATE_FRESHNESS_STALE_AFTER_SECONDS:
        return "stale", age_seconds
    return "fresh", age_seconds


def _combined_open_trade_freshness(*, account_freshness: str, trade_freshness: str) -> str:
    if "unknown" in {account_freshness, trade_freshness}:
        return "unknown"
    if "stale" in {account_freshness, trade_freshness}:
        return "stale"
    return "fresh"


def _paper_state_blocker_classification(
    *,
    freshness: str,
    duplicate_entry_blocker: bool,
) -> str:
    if duplicate_entry_blocker and freshness == "fresh":
        return "fresh_open_trade_blocker"
    if duplicate_entry_blocker and freshness == "stale":
        return "stale_open_trade_review_required"
    if duplicate_entry_blocker:
        return "unknown_freshness_review_required"
    if freshness == "fresh":
        return "fresh_open_trade"
    if freshness == "stale":
        return "stale_open_trade_review_required"
    return "unknown_freshness_review_required"


def _risk_profile_has_key(risk_profile: dict[str, Any], key: str) -> bool:
    return key in risk_profile and risk_profile.get(key) is not None


def _risk_profile_numeric(risk_profile: dict[str, Any], key: str) -> bool:
    if not _risk_profile_has_key(risk_profile, key):
        return False
    value = risk_profile.get(key)
    if isinstance(value, bool):
        return False
    if isinstance(value, (int, float)):
        return True
    if isinstance(value, str):
        try:
            float(value)
        except ValueError:
            return False
        return True
    return False


def _risk_control_item(
    *,
    control_id: str,
    control_name: str,
    implemented: bool,
    configured: bool,
    active: bool,
    applied_count: int,
    blocked_count: int,
    skipped_count: int,
    inactive_reason: str | None,
    validation_note: str,
) -> dict[str, Any]:
    return {
        "control_id": control_id,
        "control_name": control_name,
        "implemented": implemented,
        "configured": configured,
        "active": active,
        "applied_count": applied_count,
        "blocked_count": blocked_count,
        "skipped_count": skipped_count,
        "inactive_reason": inactive_reason,
        "evidence_scope": "bounded_paper_execution_cycle",
        "validation_note": validation_note,
    }


def _execution_results(execution_payload: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(execution_payload, dict):
        return []
    raw_results = execution_payload.get("results")
    if not isinstance(raw_results, list):
        return []
    return [item for item in raw_results if isinstance(item, dict)]


def _outcome_counts(results: list[dict[str, Any]]) -> dict[str, int]:
    counts: dict[str, int] = {}
    for result in results:
        outcome = result.get("outcome")
        if isinstance(outcome, str) and outcome:
            counts[outcome] = counts.get(outcome, 0) + 1
    return counts


def _count_outcomes(counts: dict[str, int], outcomes: set[str]) -> int:
    return sum(counts.get(outcome, 0) for outcome in outcomes)


def build_risk_control_activation_evidence(
    *,
    execution_payload: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    payload = execution_payload if isinstance(execution_payload, dict) else {}
    risk_profile = payload.get("risk_profile")
    risk_profile = risk_profile if isinstance(risk_profile, dict) else {}

    results = _execution_results(payload)
    total_results = len(results)
    counts = _outcome_counts(results)
    eligible_count = counts.get("eligible", 0)
    fill_count = eligible_count + counts.get("eligible:partial_exit", 0) + counts.get("eligible:full_exit", 0)
    invalid_signal_count = counts.get("reject:invalid_signal_fields", 0)
    exit_signal_count = counts.get("skip:exit_signal_not_entry_candidate", 0)
    score_blocked_count = counts.get("skip:score_below_threshold", 0)
    duplicate_blocked_count = counts.get("skip:duplicate_entry", 0)
    pre_duplicate_not_reached = invalid_signal_count + exit_signal_count + score_blocked_count
    pre_sizing_not_reached = _count_outcomes(
        counts,
        {
            "reject:invalid_signal_fields",
            "skip:exit_signal_not_entry_candidate",
            "skip:score_below_threshold",
            "skip:duplicate_entry",
            "skip:cooldown_active",
            "skip:entry_zone_not_reached",
            "skip:regime_filtered",
            "skip:drawdown_guard_active",
        },
    )
    sizing_blocked_count = _count_outcomes(
        counts,
        {
            "reject:missing_trade_risk_input",
            "reject:invalid_trade_risk_input",
            "reject:max_risk_per_trade_exceeded",
        },
    )
    max_concurrent_blocked_count = counts.get("reject:concurrent_position_limit_exceeded", 0)
    exposure_blocked_count = _count_outcomes(
        counts,
        {
            "reject:account_exposure_limit_exceeded",
            "reject:strategy_exposure_limit_exceeded",
            "reject:symbol_exposure_limit_exceeded",
        },
    )
    correlation_blocked_count = counts.get("skip:correlation_risk_blocked", 0)
    drawdown_blocked_count = counts.get("skip:drawdown_guard_active", 0)
    regime_blocked_count = counts.get("skip:regime_filtered", 0)
    post_sizing_reached_count = (
        fill_count
        + max_concurrent_blocked_count
        + exposure_blocked_count
        + correlation_blocked_count
    )

    score_configured = _risk_profile_has_key(risk_profile, "min_score_threshold")
    duplicate_configured = True
    sizing_configured = risk_profile.get("sizing_method") == "stop_distance"
    commission_configured = _risk_profile_has_key(risk_profile, "commission_rate")
    slippage_configured = _risk_profile_has_key(risk_profile, "slippage_rate")
    exposure_configured = all(
        _risk_profile_has_key(risk_profile, key)
        for key in (
            "max_total_exposure_pct",
            "max_strategy_exposure_pct",
            "max_symbol_exposure_pct",
        )
    )
    max_concurrent_configured = _risk_profile_has_key(risk_profile, "max_concurrent_positions")
    correlation_configured = _risk_profile_has_key(risk_profile, "correlation_check_enabled")
    drawdown_configured = _risk_profile_has_key(risk_profile, "drawdown_guard_enabled")
    regime_configured = _risk_profile_has_key(risk_profile, "allowed_regimes")

    score_active = score_configured
    sizing_active = sizing_configured
    commission_active = _risk_profile_numeric(risk_profile, "commission_rate")
    slippage_active = _risk_profile_numeric(risk_profile, "slippage_rate")
    exposure_active = exposure_configured
    max_concurrent_active = max_concurrent_configured
    correlation_active = risk_profile.get("correlation_check_enabled") is True
    drawdown_active = risk_profile.get("drawdown_guard_enabled") is True
    allowed_regimes = risk_profile.get("allowed_regimes")
    regime_active = isinstance(allowed_regimes, list) and len(allowed_regimes) > 0

    score_applied_count = max(total_results - invalid_signal_count - exit_signal_count, 0)
    duplicate_applied_count = max(total_results - pre_duplicate_not_reached, 0)
    sizing_applied_count = max(total_results - pre_sizing_not_reached, 0)
    exposure_skipped_count = max(total_results - post_sizing_reached_count, 0)

    return [
        _risk_control_item(
            control_id="score_threshold_gate",
            control_name="Score threshold gate",
            implemented=True,
            configured=score_configured,
            active=score_active,
            applied_count=score_applied_count if score_active else 0,
            blocked_count=score_blocked_count if score_active else 0,
            skipped_count=invalid_signal_count + exit_signal_count if score_active else total_results,
            inactive_reason=None if score_active else "min_score_threshold not configured",
            validation_note=(
                "Applied to entry candidates; skip:score_below_threshold outcomes are counted as blocking."
                if score_active
                else "Not validated by this run because min_score_threshold is not configured."
            ),
        ),
        _risk_control_item(
            control_id="duplicate_entry_gate",
            control_name="Duplicate-entry gate",
            implemented=True,
            configured=duplicate_configured,
            active=True,
            applied_count=duplicate_applied_count,
            blocked_count=duplicate_blocked_count,
            skipped_count=pre_duplicate_not_reached,
            inactive_reason=None,
            validation_note="Applied after score gating; skip:duplicate_entry outcomes are counted as blocking.",
        ),
        _risk_control_item(
            control_id="stop_distance_sizing",
            control_name="Stop-distance sizing",
            implemented=True,
            configured=sizing_configured,
            active=sizing_active,
            applied_count=sizing_applied_count if sizing_active else 0,
            blocked_count=sizing_blocked_count if sizing_active else 0,
            skipped_count=pre_sizing_not_reached if sizing_active else total_results,
            inactive_reason=None if sizing_active else "sizing_method is not stop_distance",
            validation_note=(
                "Applied to candidates reaching sizing; missing or invalid trade-risk inputs are counted as blocking."
                if sizing_active
                else "Not validated by this run because stop-distance sizing is disabled by config."
            ),
        ),
        _risk_control_item(
            control_id="commission_model",
            control_name="Commission model",
            implemented=True,
            configured=commission_configured,
            active=commission_active,
            applied_count=fill_count if commission_active else 0,
            blocked_count=0,
            skipped_count=max(total_results - fill_count, 0) if commission_active else total_results,
            inactive_reason=None if commission_active else "commission_rate is not configured as a numeric value",
            validation_note=(
                "Configured and applied to paper fills; applied_count is zero when no fills occurred."
                if commission_active
                else "Not validated by this run because commission_rate is not active."
            ),
        ),
        _risk_control_item(
            control_id="slippage_model",
            control_name="Slippage model",
            implemented=True,
            configured=slippage_configured,
            active=slippage_active,
            applied_count=fill_count if slippage_active else 0,
            blocked_count=0,
            skipped_count=max(total_results - fill_count, 0) if slippage_active else total_results,
            inactive_reason=None if slippage_active else "slippage_rate is not configured as a numeric value",
            validation_note=(
                "Configured and applied to paper fills; applied_count is zero when no fills occurred."
                if slippage_active
                else "Not validated by this run because slippage_rate is not active."
            ),
        ),
        _risk_control_item(
            control_id="exposure_limits",
            control_name="Exposure limits",
            implemented=True,
            configured=exposure_configured,
            active=exposure_active,
            applied_count=(post_sizing_reached_count - max_concurrent_blocked_count) if exposure_active else 0,
            blocked_count=exposure_blocked_count if exposure_active else 0,
            skipped_count=exposure_skipped_count + max_concurrent_blocked_count if exposure_active else total_results,
            inactive_reason=None if exposure_active else "one or more exposure limit fields are not configured",
            validation_note=(
                "Applied to candidates reaching exposure checks; earlier gates and max-concurrent blocks are counted as not reached."
                if exposure_active
                else "Not validated by this run because exposure limits are not fully configured."
            ),
        ),
        _risk_control_item(
            control_id="max_concurrent_positions",
            control_name="Max concurrent positions",
            implemented=True,
            configured=max_concurrent_configured,
            active=max_concurrent_active,
            applied_count=post_sizing_reached_count if max_concurrent_active else 0,
            blocked_count=max_concurrent_blocked_count if max_concurrent_active else 0,
            skipped_count=exposure_skipped_count if max_concurrent_active else total_results,
            inactive_reason=None if max_concurrent_active else "max_concurrent_positions is not configured",
            validation_note=(
                "Applied to candidates reaching post-sizing risk checks; rejects are counted as blocking."
                if max_concurrent_active
                else "Not validated by this run because max_concurrent_positions is not configured."
            ),
        ),
        _risk_control_item(
            control_id="correlation_gate",
            control_name="Correlation gate",
            implemented=True,
            configured=correlation_configured,
            active=correlation_active,
            applied_count=correlation_blocked_count if correlation_active else 0,
            blocked_count=correlation_blocked_count if correlation_active else 0,
            skipped_count=max(total_results - correlation_blocked_count, 0) if correlation_active else total_results,
            inactive_reason=None if correlation_active else "disabled by config: correlation_check_enabled=false",
            validation_note=(
                "Applied when price history is supplied and the gate is enabled; correlation blocks are counted as blocking."
                if correlation_active
                else "Not validated by this run because correlation_check_enabled is disabled by config."
            ),
        ),
        _risk_control_item(
            control_id="drawdown_guard",
            control_name="Drawdown guard",
            implemented=True,
            configured=drawdown_configured,
            active=drawdown_active,
            applied_count=drawdown_blocked_count if drawdown_active else 0,
            blocked_count=drawdown_blocked_count if drawdown_active else 0,
            skipped_count=max(total_results - drawdown_blocked_count, 0) if drawdown_active else total_results,
            inactive_reason=None if drawdown_active else "disabled by config: drawdown_guard_enabled=false",
            validation_note=(
                "Applied when enabled before sizing; drawdown guard skips are counted as blocking."
                if drawdown_active
                else "Not validated by this run because drawdown_guard_enabled is disabled by config."
            ),
        ),
        _risk_control_item(
            control_id="regime_filter",
            control_name="Regime filter",
            implemented=True,
            configured=regime_configured,
            active=regime_active,
            applied_count=regime_blocked_count if regime_active else 0,
            blocked_count=regime_blocked_count if regime_active else 0,
            skipped_count=max(total_results - regime_blocked_count, 0) if regime_active else total_results,
            inactive_reason=None if regime_active else "no allowed regimes configured: allowed_regimes is empty",
            validation_note=(
                "Applied when regime state is supplied and allowed_regimes is non-empty; filtered regimes are counted as blocking."
                if regime_active
                else "Not validated by this run because allowed_regimes is empty."
            ),
        ),
    ]


def build_paper_state_freshness_evidence(
    *,
    trades_payload: dict[str, Any] | None,
    positions_payload: dict[str, Any] | None,
    account_payload: dict[str, Any] | None,
    execution_payload: dict[str, Any] | None,
    signals_payload: dict[str, Any] | None,
    observed_at: datetime,
) -> dict[str, Any]:
    account = account_payload.get("account") if isinstance(account_payload, dict) else None
    account = account if isinstance(account, dict) else {}
    account_as_of = account.get("as_of")
    account_freshness, account_age_seconds = _classify_paper_state_freshness(
        account_as_of=account_as_of,
        observed_at=observed_at,
    )
    duplicate_blocker_index = _duplicate_entry_blocker_index(
        execution_payload=execution_payload,
        signals_payload=signals_payload,
    )
    duplicate_blocker_keys = set(duplicate_blocker_index.keys())

    positions_by_id: dict[str, dict[str, Any]] = {}
    for position in _items_from_payload(positions_payload):
        position_id = position.get("position_id")
        if isinstance(position_id, str) and position_id:
            positions_by_id[position_id] = position

    open_trade_evidence: list[dict[str, Any]] = []
    duplicate_blocker_count = 0
    review_required_count = 0
    for trade in _items_from_payload(trades_payload):
        if trade.get("status") != "open":
            continue
        trade_freshness, trade_age_seconds = _classify_timestamp_freshness(
            timestamp=trade.get("opened_at"),
            observed_at=observed_at,
        )
        freshness = _combined_open_trade_freshness(
            account_freshness=account_freshness,
            trade_freshness=trade_freshness,
        )
        trade_key = _normalized_trade_tuple(trade)
        duplicate_entry_blocker = trade_key in duplicate_blocker_keys if trade_key is not None else False
        duplicate_entry_blocker_reason: str | None = None
        if duplicate_entry_blocker and trade_key is not None:
            reasons = duplicate_blocker_index.get(trade_key) or []
            if reasons:
                duplicate_entry_blocker_reason = reasons[0]
        if duplicate_entry_blocker:
            duplicate_blocker_count += 1
        classification = _paper_state_blocker_classification(
            freshness=freshness,
            duplicate_entry_blocker=duplicate_entry_blocker,
        )
        if classification.endswith("_review_required"):
            review_required_count += 1

        position_id = trade.get("position_id")
        position = positions_by_id.get(position_id) if isinstance(position_id, str) else None
        open_trade_evidence.append(
            {
                "account_as_of": account_as_of,
                "account_age_seconds": account_age_seconds,
                "account_freshness": account_freshness,
                "age_seconds": account_age_seconds,
                "average_entry_price": trade.get("average_entry_price"),
                "classification": classification,
                "current_state": "open" if trade.get("status") == "open" else "closed",
                "direction": trade.get("direction"),
                "duplicate_entry_blocker": duplicate_entry_blocker,
                "duplicate_entry_blocker_reason": duplicate_entry_blocker_reason,
                "freshness": freshness,
                "opened_at": trade.get("opened_at"),
                "operator_review_guidance": PAPER_STATE_OPERATOR_REVIEW_GUIDANCE[freshness],
                "position_id": position_id,
                "position_status": position.get("status") if isinstance(position, dict) else None,
                "quantity_closed": trade.get("quantity_closed"),
                "quantity_opened": trade.get("quantity_opened"),
                "status": trade.get("status"),
                "strategy": trade.get("strategy_id", trade.get("strategy")),
                "symbol": trade.get("symbol"),
                "trade_age_seconds": trade_age_seconds,
                "trade_freshness": trade_freshness,
                "trade_id": trade.get("trade_id"),
            }
        )

    open_trade_evidence.sort(
        key=lambda item: (
            str(item.get("symbol") or ""),
            str(item.get("strategy") or ""),
            str(item.get("direction") or ""),
            str(item.get("trade_id") or ""),
        )
    )

    return {
        "classification_version": PAPER_STATE_FRESHNESS_CLASSIFICATION_VERSION,
        "account_as_of": account_as_of,
        "observed_at": observed_at.isoformat(),
        "account_freshness": account_freshness,
        "account_age_seconds": account_age_seconds,
        "freshness": account_freshness,
        "age_seconds": account_age_seconds,
        "stale_after_seconds": PAPER_STATE_FRESHNESS_STALE_AFTER_SECONDS,
        "open_trade_count": len(open_trade_evidence),
        "duplicate_entry_blocker_count": duplicate_blocker_count,
        "review_required_count": review_required_count,
        "operator_review_guidance": PAPER_STATE_OPERATOR_REVIEW_GUIDANCE[account_freshness],
        "open_trades": open_trade_evidence,
    }


def build_operator_review_outcome_artifact(
    *,
    paper_state_freshness: dict[str, Any],
    source_daily_runtime_summary: str,
    observed_at: datetime,
) -> dict[str, Any]:
    review_outcomes: list[dict[str, Any]] = []
    for trade in _items_from_payload(paper_state_freshness, key="open_trades"):
        if (
            trade.get("classification") != "stale_open_trade_review_required"
            or trade.get("duplicate_entry_blocker") is not True
        ):
            continue
        review_outcomes.append(
            {
                "account_as_of": trade.get("account_as_of"),
                "account_freshness": trade.get("account_freshness"),
                "classification": trade.get("classification"),
                "decision_validity": "valid_review_required_evidence",
                "direction": trade.get("direction"),
                "duplicate_entry_blocker": True,
                "duplicate_entry_blocker_reason": "stale_open_trade_duplicate_entry_blocker",
                "mutates_paper_state": False,
                "opened_at": trade.get("opened_at"),
                "operator_decision": "pending_operator_review",
                "operator_review_guidance": trade.get("operator_review_guidance"),
                "operator_rationale": (
                    "Stale open paper trade blocked duplicate entry; operator must review lifecycle evidence "
                    "before interpreting the blocker."
                ),
                "position_id": trade.get("position_id"),
                "position_status": trade.get("position_status"),
                "review_required": True,
                "status": trade.get("status"),
                "strategy": trade.get("strategy"),
                "symbol": trade.get("symbol"),
                "trade_age_seconds": trade.get("trade_age_seconds"),
                "trade_freshness": trade.get("trade_freshness"),
                "trade_id": trade.get("trade_id"),
            }
        )

    review_outcomes.sort(
        key=lambda item: (
            str(item.get("symbol") or ""),
            str(item.get("strategy") or ""),
            str(item.get("direction") or ""),
            str(item.get("trade_id") or ""),
        )
    )

    return {
        "artifact_id": OPERATOR_REVIEW_OUTCOME_ARTIFACT_ID,
        "artifact_version": OPERATOR_REVIEW_OUTCOME_ARTIFACT_VERSION,
        "invalid_count": 0,
        "mutates_paper_state": False,
        "non_inference_statement": OPERATOR_REVIEW_OUTCOME_NON_INFERENCE_STATEMENT,
        "observed_at": observed_at.isoformat(),
        "read_only": True,
        "recorded_count": len(review_outcomes),
        "review_outcomes": review_outcomes,
        "review_required_count": int(paper_state_freshness.get("review_required_count") or 0),
        "source_daily_runtime_summary": source_daily_runtime_summary,
        "workflow_id": OPERATOR_REVIEW_OUTCOME_WORKFLOW_ID,
        "workflow_version": OPERATOR_REVIEW_OUTCOME_WORKFLOW_VERSION,
    }


_STALE_OPEN_PAPER_TRADE_REVIEW_CLASSIFICATIONS: frozenset[str] = frozenset(
    {
        "stale_open_trade_review_required",
        "unknown_freshness_review_required",
    }
)


def build_stale_open_paper_trade_review_workflow(
    *,
    paper_state_freshness: dict[str, Any] | None,
) -> dict[str, Any]:
    """Build the bounded read-only operator-review workflow for stale open paper trades.

    The workflow is built deterministically from the existing paper-state freshness
    evidence. It does not read or mutate paper state itself: it only re-projects the
    already-captured evidence into a structured operator-facing surface that lists
    stale open paper trades, links them to duplicate-entry blockers when evidence
    exists, and enumerates the allowed read-only review actions and the prohibited
    mutation actions.
    """

    freshness = paper_state_freshness if isinstance(paper_state_freshness, dict) else {}
    open_trades_raw = freshness.get("open_trades")
    open_trades = [item for item in open_trades_raw if isinstance(item, dict)] if isinstance(open_trades_raw, list) else []

    review_trades: list[dict[str, Any]] = []
    duplicate_blocker_review_count = 0
    non_duplicate_blocker_review_count = 0
    unknown_freshness_review_count = 0

    for trade in open_trades:
        classification = trade.get("classification")
        per_trade_classification = (
            classification
            if classification in _STALE_OPEN_PAPER_TRADE_REVIEW_CLASSIFICATIONS
            else "fresh_no_review_required"
        )
        review_entry = {
            "trade_id": trade.get("trade_id"),
            "position_id": trade.get("position_id"),
            "symbol": trade.get("symbol"),
            "strategy": trade.get("strategy"),
            "direction": trade.get("direction"),
            "status": trade.get("status"),
            "opened_at": trade.get("opened_at"),
            "account_as_of": trade.get("account_as_of"),
            "trade_age_seconds": trade.get("trade_age_seconds"),
            "account_age_seconds": trade.get("account_age_seconds"),
            "trade_freshness": trade.get("trade_freshness"),
            "account_freshness": trade.get("account_freshness"),
            "freshness": trade.get("freshness"),
            "duplicate_entry_blocker": bool(trade.get("duplicate_entry_blocker")),
            "duplicate_entry_blocker_reason": trade.get("duplicate_entry_blocker_reason"),
            "classification": classification,
            "review_classification": per_trade_classification,
            "operator_review_guidance": trade.get("operator_review_guidance"),
        }
        if per_trade_classification == "fresh_no_review_required":
            continue
        if per_trade_classification == "unknown_freshness_review_required":
            unknown_freshness_review_count += 1
        if review_entry["duplicate_entry_blocker"]:
            duplicate_blocker_review_count += 1
        else:
            non_duplicate_blocker_review_count += 1
        review_trades.append(review_entry)

    review_required_count = len(review_trades)
    workflow_status = "review_required" if review_required_count > 0 else "no_review_required"

    return {
        "workflow_id": STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_ID,
        "workflow_version": STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_VERSION,
        "mode": STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_MODE,
        "read_only": True,
        "mutates_paper_state": False,
        "workflow_status": workflow_status,
        "review_required_count": review_required_count,
        "duplicate_entry_blocker_review_count": duplicate_blocker_review_count,
        "non_duplicate_entry_blocker_review_count": non_duplicate_blocker_review_count,
        "unknown_freshness_review_count": unknown_freshness_review_count,
        "stale_open_trades": review_trades,
        "allowed_actions": [dict(action) for action in STALE_OPEN_PAPER_TRADE_REVIEW_ALLOWED_ACTIONS],
        "prohibited_actions": [dict(action) for action in STALE_OPEN_PAPER_TRADE_REVIEW_PROHIBITED_ACTIONS],
        "review_guidance": STALE_OPEN_PAPER_TRADE_REVIEW_GUIDANCE_BY_STATUS[workflow_status],
        "non_inference_statement": STALE_OPEN_PAPER_TRADE_REVIEW_NON_INFERENCE_STATEMENT,
    }


def _normalize_reviewer_id(value: Any) -> str:
    """Return a reviewer/operator identifier or the explicit not-provided sentinel."""

    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_REVIEWER_NOT_PROVIDED


def _normalize_source_summary_reference(value: Any) -> str | None:
    """Return a source daily-runtime-summary reference string or None."""

    if isinstance(value, str):
        stripped = value.strip()
        if stripped:
            return stripped
    return None


def build_stale_open_paper_trade_review_outcome_artifact(
    *,
    stale_open_paper_trade_review_workflow: dict[str, Any] | None,
    review_payload: dict[str, Any] | None,
    observed_at: datetime,
    source_summary_reference: Any = None,
) -> dict[str, Any]:
    """Build a bounded, non-mutating operator review outcome artifact.

    The artifact records the operator review decision per stale open paper trade
    surfaced by the bounded ``stale_open_paper_trade_review_workflow`` evidence.
    It is strictly evidence-only:

    * It does not close, reset, mark-to-market, or otherwise modify any paper
      account, paper trade, paper position, order, execution-event, or
      reconciliation state.
    * It does not infer trader validation, profitability, broker readiness,
      live readiness, or production readiness.
    * Inputs are read deterministically and are never mutated.

    Invalid or incomplete review payloads are classified into the artifact
    without raising; callers can detect them via ``review_outcome_status`` and
    per-trade ``decision_validity`` fields. The artifact still carries the
    explicit ``mutates_paper_state: false`` evidence and prohibited-action
    statements so that no downstream consumer can mistake a rejection path for
    a mutation path.
    """

    workflow = (
        stale_open_paper_trade_review_workflow
        if isinstance(stale_open_paper_trade_review_workflow, dict)
        else {}
    )
    raw_stale_trades = workflow.get("stale_open_trades")
    stale_trades = (
        [item for item in raw_stale_trades if isinstance(item, dict)]
        if isinstance(raw_stale_trades, list)
        else []
    )

    payload = review_payload if isinstance(review_payload, dict) else {}
    raw_decisions = payload.get("decisions")
    decisions = (
        [item for item in raw_decisions if isinstance(item, dict)]
        if isinstance(raw_decisions, list)
        else []
    )
    decisions_by_trade_id: dict[str, dict[str, Any]] = {}
    duplicate_payload_decision_count = 0
    for decision in decisions:
        trade_id = decision.get("trade_id")
        if not isinstance(trade_id, str) or not trade_id:
            continue
        if trade_id in decisions_by_trade_id:
            duplicate_payload_decision_count += 1
            continue
        decisions_by_trade_id[trade_id] = decision

    reviewer_id = _normalize_reviewer_id(payload.get("reviewer_id"))
    source_reference = _normalize_source_summary_reference(source_summary_reference)
    if source_reference is None:
        source_reference = _normalize_source_summary_reference(
            payload.get("source_summary_reference")
        )

    review_entries: list[dict[str, Any]] = []
    valid_decision_count = 0
    invalid_decision_count = 0
    missing_decision_count = 0
    prohibited_decision_count = 0
    matched_trade_ids: set[str] = set()

    for trade in stale_trades:
        trade_id = trade.get("trade_id")
        decision_entry = decisions_by_trade_id.get(trade_id) if isinstance(trade_id, str) else None
        if isinstance(trade_id, str) and trade_id:
            matched_trade_ids.add(trade_id)

        operator_decision: str | None = None
        operator_rationale: str | None = None
        decision_validity = "missing_decision"

        if isinstance(decision_entry, dict):
            raw_decision = decision_entry.get("decision")
            raw_rationale = decision_entry.get("rationale")
            decision_str = raw_decision.strip() if isinstance(raw_decision, str) else ""
            rationale_str = raw_rationale.strip() if isinstance(raw_rationale, str) else ""
            operator_decision = decision_str or None
            operator_rationale = rationale_str or None
            if not decision_str:
                decision_validity = "missing_decision"
            elif decision_str in STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_PROHIBITED_DECISIONS:
                decision_validity = "prohibited_decision"
            elif decision_str not in STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ALLOWED_DECISIONS:
                decision_validity = "unrecognized_decision"
            elif not rationale_str:
                decision_validity = "missing_rationale"
            else:
                decision_validity = "valid"

        if decision_validity == "valid":
            valid_decision_count += 1
        elif decision_validity == "missing_decision":
            missing_decision_count += 1
            invalid_decision_count += 1
        elif decision_validity == "prohibited_decision":
            prohibited_decision_count += 1
            invalid_decision_count += 1
        else:
            invalid_decision_count += 1

        review_entries.append(
            {
                "trade_id": trade.get("trade_id"),
                "position_id": trade.get("position_id"),
                "symbol": trade.get("symbol"),
                "strategy": trade.get("strategy"),
                "direction": trade.get("direction"),
                "opened_at": trade.get("opened_at"),
                "account_as_of": trade.get("account_as_of"),
                "trade_freshness": trade.get("trade_freshness"),
                "account_freshness": trade.get("account_freshness"),
                "duplicate_entry_blocker": bool(trade.get("duplicate_entry_blocker")),
                "duplicate_entry_blocker_reason": trade.get("duplicate_entry_blocker_reason"),
                "review_classification": trade.get("review_classification"),
                "operator_decision": operator_decision,
                "operator_rationale": operator_rationale,
                "decision_validity": decision_validity,
            }
        )

    review_entries.sort(
        key=lambda item: (
            str(item.get("symbol") or ""),
            str(item.get("strategy") or ""),
            str(item.get("direction") or ""),
            str(item.get("trade_id") or ""),
        )
    )

    unmatched_payload_decisions = sorted(
        trade_id
        for trade_id in decisions_by_trade_id.keys()
        if trade_id not in matched_trade_ids
    )

    reviewed_trade_count = len(review_entries)
    if reviewed_trade_count == 0:
        review_outcome_status = "no_review_required"
    elif invalid_decision_count == 0 and reviewed_trade_count > 0:
        review_outcome_status = "recorded"
    elif valid_decision_count == 0:
        review_outcome_status = "invalid_payload"
    else:
        review_outcome_status = "partially_recorded"

    artifact: dict[str, Any] = {
        "artifact_id": STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ARTIFACT_ID,
        "artifact_version": STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ARTIFACT_VERSION,
        "workflow_id": workflow.get("workflow_id", STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_ID),
        "workflow_version": workflow.get(
            "workflow_version", STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_VERSION
        ),
        "mode": workflow.get("mode", STALE_OPEN_PAPER_TRADE_REVIEW_WORKFLOW_MODE),
        "observed_at": observed_at.isoformat(),
        "source_summary_reference": source_reference,
        "reviewer_id": reviewer_id,
        "review_outcome_status": review_outcome_status,
        "reviewed_trade_count": reviewed_trade_count,
        "valid_decision_count": valid_decision_count,
        "invalid_decision_count": invalid_decision_count,
        "missing_decision_count": missing_decision_count,
        "prohibited_decision_count": prohibited_decision_count,
        "duplicate_payload_decision_count": duplicate_payload_decision_count,
        "unmatched_payload_decision_trade_ids": unmatched_payload_decisions,
        "reviewed_stale_open_trades": review_entries,
        "allowed_decisions": sorted(STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_ALLOWED_DECISIONS),
        "prohibited_decisions": sorted(
            STALE_OPEN_PAPER_TRADE_REVIEW_OUTCOME_PROHIBITED_DECISIONS
        ),
        "prohibited_actions": [
            dict(action) for action in STALE_OPEN_PAPER_TRADE_REVIEW_PROHIBITED_ACTIONS
        ],
        "read_only": True,
        "mutates_paper_state": False,
        "non_inference_statement": STALE_OPEN_PAPER_TRADE_REVIEW_NON_INFERENCE_STATEMENT,
    }
    return artifact


def _classify_run_quality(
    *,
    execution_step: dict[str, Any] | None,
    reconciliation_step: dict[str, Any] | None,
) -> dict[str, Any]:
    execution_returncode: int | None = None
    execution_status: str | None = None
    execution_eligible: int | None = None
    reconciliation_ok: bool | None = None
    reconciliation_mismatches: int | None = None

    execution_payload: dict[str, Any] | None = None
    if isinstance(execution_step, dict):
        raw_returncode = execution_step.get("returncode")
        if isinstance(raw_returncode, int):
            execution_returncode = raw_returncode
        raw_payload = execution_step.get("payload")
        if isinstance(raw_payload, dict):
            execution_payload = raw_payload

    if execution_payload is not None:
        raw_status = execution_payload.get("status")
        if isinstance(raw_status, str):
            execution_status = raw_status
        execution_eligible = _to_int_or_none(execution_payload.get("eligible"))

    reconciliation_payload: dict[str, Any] | None = None
    if isinstance(reconciliation_step, dict):
        raw_payload = reconciliation_step.get("payload")
        if isinstance(raw_payload, dict):
            reconciliation_payload = raw_payload

    if reconciliation_payload is not None:
        raw_ok = reconciliation_payload.get("ok")
        if isinstance(raw_ok, bool):
            reconciliation_ok = raw_ok
        reconciliation_mismatches = _to_int_or_none(reconciliation_payload.get("mismatches"))

    reconciliation_degraded = (reconciliation_ok is False) or (
        reconciliation_mismatches is not None and reconciliation_mismatches > 0
    )
    execution_no_eligible = (execution_returncode == 1) or (execution_status == "no_eligible")
    execution_healthy = (
        execution_returncode == 0
        and execution_status in {"pass", "ok"}
        and execution_eligible is not None
        and execution_eligible > 0
    )
    reconciliation_clean = (
        reconciliation_ok is True and (reconciliation_mismatches is None or reconciliation_mismatches == 0)
    )

    if reconciliation_degraded:
        run_quality_status = "degraded"
    elif execution_no_eligible and reconciliation_clean:
        run_quality_status = "no_eligible"
    elif execution_healthy and reconciliation_clean:
        run_quality_status = "healthy"
    else:
        run_quality_status = "degraded"

    return {
        "operator_action_contract": _build_run_quality_action_contract(run_quality_status),
        "operator_action_contract_version": OPERATOR_ACTION_CONTRACT_VERSION,
        "run_quality_classification_version": RUN_QUALITY_CLASSIFICATION_VERSION,
        "run_quality_status": run_quality_status,
        "run_quality_inputs": {
            "execution_eligible": execution_eligible,
            "execution_returncode": execution_returncode,
            "execution_status": execution_status,
            "reconciliation_mismatches": reconciliation_mismatches,
            "reconciliation_ok": reconciliation_ok,
        },
    }


def _build_run_quality_action_contract(run_quality_status: str) -> dict[str, str]:
    contract = RUN_QUALITY_OPERATOR_ACTION_CONTRACTS.get(run_quality_status)
    if contract is None:
        raise ValueError(f"unsupported run_quality_status for operator action contract: {run_quality_status}")
    return dict(contract)


def _build_failed_step_action_contract(step: str) -> dict[str, str]:
    contract = FAILED_STEP_OPERATOR_ACTION_CONTRACTS.get(
        step,
        DEFAULT_FAILED_STEP_OPERATOR_ACTION_CONTRACT,
    )
    return dict(contract)


def run_daily_bounded_paper_runtime(
    *,
    db_path: str,
    base_url: str,
    symbols: str,
    timeframe: str,
    limit: int,
    provider: str,
    analysis_symbol: str,
    analysis_strategy: str,
    analysis_market_type: str,
    analysis_lookback_days: int,
    snapshot_evidence_dir: str,
    execution_evidence_dir: str,
    reconciliation_evidence_dir: str,
    review_evidence_dir: str,
    run_record_dir: str,
    signals_limit: int,
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]] = _run_command,
    request_json: Callable[..., dict[str, Any]] = _request_json,
    now_fn: Callable[[], datetime] = _utc_now,
) -> dict[str, Any]:
    started_at = now_fn()
    base_url = base_url.rstrip("/")
    steps_completed: list[str] = []
    ingestion_run_id: str | None = None

    script_outputs: dict[str, dict[str, Any]] = {}

    try:
        # Step 1: snapshot ingestion
        snapshot_result = _invoke_python_script(
            script_path=ROOT / "scripts" / "run_snapshot_ingestion.py",
            script_args=[
                "--symbols",
                symbols,
                "--timeframe",
                timeframe,
                "--limit",
                str(limit),
                "--provider",
                provider,
                "--db-path",
                db_path,
                "--evidence-dir",
                snapshot_evidence_dir,
            ],
            run_command=run_command,
        )
        snapshot_payload = _extract_last_json_record(
            snapshot_result.stdout,
            snapshot_result.stderr,
        )
        script_outputs["snapshot_ingestion"] = {
            "returncode": snapshot_result.returncode,
            "payload": snapshot_payload,
        }
        if snapshot_result.returncode != 0:
            raise DailyRuntimeStepError(
                step="snapshot_ingestion",
                exit_code=EXIT_CODE_SNAPSHOT_FAILED,
                detail="snapshot ingestion step failed",
                context={
                    **script_outputs["snapshot_ingestion"],
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            )
        try:
            ingestion_run_id = str(snapshot_payload["result"]["ingestion_run_id"])  # type: ignore[index]
        except (TypeError, KeyError) as exc:
            raise DailyRuntimeStepError(
                step="snapshot_ingestion",
                exit_code=EXIT_CODE_SNAPSHOT_FAILED,
                detail="snapshot ingestion output missing result.ingestion_run_id",
                context={
                    **script_outputs["snapshot_ingestion"],
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            ) from exc
        steps_completed.append("snapshot_ingestion")

        # Step 2: analysis / signal generation
        analysis_request = {
            "ingestion_run_id": ingestion_run_id,
            "symbol": analysis_symbol,
            "strategy": analysis_strategy,
            "market_type": analysis_market_type,
            "lookback_days": analysis_lookback_days,
        }
        try:
            analysis_payload = request_json(
                f"{base_url}/analysis/run",
                method="POST",
                headers={ROLE_HEADER_NAME: ROLE_OPERATOR},
                payload=analysis_request,
            )
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            TimeoutError,
            ValueError,
            json.JSONDecodeError,
        ) as exc:
            raise DailyRuntimeStepError(
                step="analysis_signal_generation",
                exit_code=EXIT_CODE_ANALYSIS_FAILED,
                detail=f"analysis step failed: {type(exc).__name__}: {exc}",
                context={
                    "request": analysis_request,
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            ) from exc
        if "analysis_run_id" not in analysis_payload:
            raise DailyRuntimeStepError(
                step="analysis_signal_generation",
                exit_code=EXIT_CODE_ANALYSIS_FAILED,
                detail="analysis response missing analysis_run_id",
                context={
                    "request": analysis_request,
                    "response": analysis_payload,
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            )
        steps_completed.append("analysis_signal_generation")

        # Step 3: bounded paper execution cycle
        execution_result = _invoke_python_script(
            script_path=ROOT / "scripts" / "run_paper_execution_cycle.py",
            script_args=[
                "--db-path",
                db_path,
                "--evidence-dir",
                execution_evidence_dir,
            ],
            run_command=run_command,
        )
        execution_payload = _extract_last_json_record(
            execution_result.stdout,
            execution_result.stderr,
        )
        script_outputs["bounded_paper_execution_cycle"] = {
            "returncode": execution_result.returncode,
            "payload": execution_payload,
        }
        if execution_result.returncode not in (0, 1):
            raise DailyRuntimeStepError(
                step="bounded_paper_execution_cycle",
                exit_code=EXIT_CODE_EXECUTION_FAILED,
                detail="bounded paper execution cycle failed",
                context={
                    **script_outputs["bounded_paper_execution_cycle"],
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            )
        steps_completed.append("bounded_paper_execution_cycle")

        # Step 4: reconciliation
        reconciliation_result = _invoke_python_script(
            script_path=ROOT / "scripts" / "run_post_run_reconciliation.py",
            script_args=[
                "--db-path",
                db_path,
                "--evidence-dir",
                reconciliation_evidence_dir,
            ],
            run_command=run_command,
        )
        reconciliation_payload = _extract_last_json_record(
            reconciliation_result.stdout,
            reconciliation_result.stderr,
        )
        script_outputs["reconciliation"] = {
            "returncode": reconciliation_result.returncode,
            "payload": reconciliation_payload,
        }
        if reconciliation_result.returncode != 0:
            raise DailyRuntimeStepError(
                step="reconciliation",
                exit_code=EXIT_CODE_RECONCILIATION_FAILED,
                detail="reconciliation step failed",
                context={
                    **script_outputs["reconciliation"],
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            )
        steps_completed.append("reconciliation")

        # Step 5a: evidence generation
        review_result = _invoke_python_script(
            script_path=ROOT / "scripts" / "generate_weekly_review.py",
            script_args=[
                "--db-path",
                db_path,
                "--evidence-dir",
                review_evidence_dir,
            ],
            run_command=run_command,
        )
        review_payload = _extract_last_json_record(
            review_result.stdout,
            review_result.stderr,
        )
        script_outputs["evidence_capture"] = {
            "returncode": review_result.returncode,
            "payload": review_payload,
        }
        if review_result.returncode != 0:
            raise DailyRuntimeStepError(
                step="evidence_capture",
                exit_code=EXIT_CODE_EVIDENCE_FAILED,
                detail="evidence generation step failed",
                context={
                    **script_outputs["evidence_capture"],
                    "steps_completed": list(steps_completed),
                    "ingestion_run_id": ingestion_run_id,
                },
            )

        # Step 5b: endpoint snapshot run record
        run_date = started_at.strftime("%Y-%m-%d")
        run_record_path = Path(run_record_dir) / run_date
        quoted_ingestion_run_id = urllib.parse.quote(ingestion_run_id, safe="")
        endpoint_payloads = {
            "signals": request_json(
                f"{base_url}/signals?ingestion_run_id={quoted_ingestion_run_id}&limit={signals_limit}",
                headers={ROLE_HEADER_NAME: ROLE_READ_ONLY},
            ),
            "paper-trades": request_json(
                f"{base_url}/paper/trades",
                headers={ROLE_HEADER_NAME: ROLE_READ_ONLY},
            ),
            "paper-positions": request_json(
                f"{base_url}/paper/positions",
                headers={ROLE_HEADER_NAME: ROLE_READ_ONLY},
            ),
            "paper-account": request_json(
                f"{base_url}/paper/account",
                headers={ROLE_HEADER_NAME: ROLE_READ_ONLY},
            ),
            "paper-reconciliation": request_json(
                f"{base_url}/paper/reconciliation",
                headers={ROLE_HEADER_NAME: ROLE_READ_ONLY},
            ),
        }
        endpoint_files: dict[str, str] = {}
        for name, payload in endpoint_payloads.items():
            target = run_record_path / f"{name}.json"
            _write_json_file(target, payload)
            endpoint_files[name] = str(target)

        steps_completed.append("evidence_capture")

        completed_at = now_fn()
        run_quality = _classify_run_quality(
            execution_step=script_outputs["bounded_paper_execution_cycle"],
            reconciliation_step=script_outputs["reconciliation"],
        )
        paper_state_freshness = build_paper_state_freshness_evidence(
            trades_payload=endpoint_payloads["paper-trades"],
            positions_payload=endpoint_payloads["paper-positions"],
            account_payload=endpoint_payloads["paper-account"],
            execution_payload=script_outputs["bounded_paper_execution_cycle"]["payload"],
            signals_payload=endpoint_payloads["signals"],
            observed_at=completed_at,
        )
        risk_control_activation = build_risk_control_activation_evidence(
            execution_payload=script_outputs["bounded_paper_execution_cycle"]["payload"],
        )
        stale_open_paper_trade_review_workflow = build_stale_open_paper_trade_review_workflow(
            paper_state_freshness=paper_state_freshness,
        )
        summary_payload: dict[str, Any] = {
            "analysis_run_id": str(analysis_payload.get("analysis_run_id", "")),
            "completed_at": completed_at.isoformat(),
            "ingestion_run_id": ingestion_run_id,
            "paper_state_freshness": paper_state_freshness,
            "risk_control_activation": risk_control_activation,
            "stale_open_paper_trade_review_workflow": stale_open_paper_trade_review_workflow,
            **run_quality,
            "run_record_dir": str(run_record_path),
            "status": "ok",
            "step_order": list(STEP_ORDER),
            "steps_completed": steps_completed,
            "steps": {
                "snapshot_ingestion": script_outputs["snapshot_ingestion"],
                "analysis_signal_generation": {"response": analysis_payload},
                "bounded_paper_execution_cycle": script_outputs["bounded_paper_execution_cycle"],
                "reconciliation": script_outputs["reconciliation"],
                "evidence_capture": script_outputs["evidence_capture"],
            },
            "verification_surfaces": endpoint_files,
        }
        summary_file = run_record_path / f"daily-runtime-summary-{started_at.strftime('%Y%m%dT%H%M%SZ')}.json"
        _write_json_file(summary_file, summary_payload)
        operator_review_path = run_record_path / "operator-review.json"
        operator_review_payload = build_operator_review_outcome_artifact(
            paper_state_freshness=paper_state_freshness,
            source_daily_runtime_summary=str(summary_file),
            observed_at=completed_at,
        )
        _write_json_file_with_sha256(
            operator_review_path,
            operator_review_payload,
        )
        summary_payload["summary_file"] = str(summary_file)
        return summary_payload
    except DailyRuntimeStepError:
        raise
    except (
        urllib.error.URLError,
        urllib.error.HTTPError,
        TimeoutError,
        ValueError,
        json.JSONDecodeError,
    ) as exc:
        raise DailyRuntimeStepError(
            step="evidence_capture",
            exit_code=EXIT_CODE_EVIDENCE_FAILED,
            detail=f"evidence capture step failed: {type(exc).__name__}: {exc}",
            context={
                "steps_completed": list(steps_completed),
                "ingestion_run_id": ingestion_run_id,
            },
        ) from exc


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    started_at = _utc_now()
    ingestion_run_id: str | None = None
    steps_completed: list[str] = []

    try:
        summary = run_daily_bounded_paper_runtime(
            db_path=str(Path(args.db_path)),
            base_url=args.base_url,
            symbols=args.symbols,
            timeframe=args.timeframe,
            limit=args.limit,
            provider=args.provider,
            analysis_symbol=args.analysis_symbol,
            analysis_strategy=args.analysis_strategy,
            analysis_market_type=args.analysis_market_type,
            analysis_lookback_days=args.analysis_lookback_days,
            snapshot_evidence_dir=str(Path(args.snapshot_evidence_dir)),
            execution_evidence_dir=str(Path(args.execution_evidence_dir)),
            reconciliation_evidence_dir=str(Path(args.reconciliation_evidence_dir)),
            review_evidence_dir=str(Path(args.review_evidence_dir)),
            run_record_dir=str(Path(args.run_record_dir)),
            signals_limit=args.signals_limit,
            run_command=_run_command,
            request_json=_request_json,
            now_fn=_utc_now,
        )
        print(json.dumps(summary, sort_keys=True, ensure_ascii=True))
        return EXIT_CODE_SUCCESS
    except DailyRuntimeStepError as exc:
        failed_at = _utc_now()
        context = exc.context or {}
        context_ingestion_run_id = context.get("ingestion_run_id")
        if isinstance(context_ingestion_run_id, str) and context_ingestion_run_id:
            ingestion_run_id = context_ingestion_run_id
        context_steps_completed = context.get("steps_completed")
        if isinstance(context_steps_completed, list):
            steps_completed = [str(item) for item in context_steps_completed]
        payload = _build_error_payload(
            step=exc.step,
            detail=exc.detail,
            started_at=started_at,
            failed_at=failed_at,
            steps_completed=steps_completed,
            ingestion_run_id=ingestion_run_id,
            context=context,
        )
        print(json.dumps(payload, sort_keys=True, ensure_ascii=True), file=sys.stderr)
        return exc.exit_code


if __name__ == "__main__":
    raise SystemExit(main())

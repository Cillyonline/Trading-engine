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
import json
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
        summary_payload: dict[str, Any] = {
            "analysis_run_id": str(analysis_payload.get("analysis_run_id", "")),
            "completed_at": completed_at.isoformat(),
            "ingestion_run_id": ingestion_run_id,
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

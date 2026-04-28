"""Offline bounded paper-runtime evidence series summarizer.

Analysis-only boundary:
    This script reads saved JSON run-output files from disk and produces an
    aggregate summary. It does not import or execute the daily runtime runner,
    paper execution worker, signal generation, risk logic, or deployment flow.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from pathlib import Path
from typing import Any


DEFAULT_PATTERN = "run-*.json"
RUN_QUALITY_VALUES = ("healthy", "no_eligible", "degraded")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Summarize saved bounded paper-runtime JSON outputs. "
            "This is offline analysis tooling only."
        ),
    )
    parser.add_argument(
        "--input-dir",
        required=True,
        help="Directory containing saved run-output JSON files.",
    )
    parser.add_argument(
        "--pattern",
        default=DEFAULT_PATTERN,
        help=f"Glob pattern for run files. Default: {DEFAULT_PATTERN}.",
    )
    parser.add_argument(
        "--no-recursive",
        action="store_true",
        help="Only scan the input directory itself instead of scanning recursively.",
    )
    parser.add_argument(
        "--format",
        choices=("json", "markdown"),
        default="json",
        help="Summary output format. Default: json.",
    )
    parser.add_argument(
        "--output",
        help="Optional output file path. When omitted, writes to stdout.",
    )
    return parser.parse_args(argv)


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


def _load_run_files(input_dir: Path, pattern: str, *, recursive: bool) -> list[tuple[Path, dict[str, Any]]]:
    if not input_dir.exists():
        raise FileNotFoundError(f"input directory does not exist: {input_dir}")
    if not input_dir.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_dir}")

    paths = input_dir.rglob(pattern) if recursive else input_dir.glob(pattern)
    loaded: list[tuple[Path, dict[str, Any]]] = []
    for path in sorted((p for p in paths if p.is_file()), key=lambda p: p.as_posix()):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(payload, dict):
            raise ValueError(f"run file must contain a JSON object: {path}")
        loaded.append((path, payload))
    return loaded


def _relative_path(path: Path, base: Path) -> str:
    try:
        relative = path.relative_to(base)
    except ValueError:
        relative = path
    return relative.as_posix()


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


def summarize_evidence(input_dir: Path, pattern: str = DEFAULT_PATTERN, *, recursive: bool = True) -> dict[str, Any]:
    base = input_dir.resolve()
    loaded = _load_run_files(base, pattern, recursive=recursive)

    run_quality_counts: Counter[str] = Counter()
    skip_reason_counts: Counter[str] = Counter()
    reconciliation_status_counts: Counter[str] = Counter()
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
        reconciliation_status = reconciliation.get("status")
        if isinstance(reconciliation_status, str) and reconciliation_status:
            reconciliation_status_counts[reconciliation_status] += 1
        elif reconciliation.get("ok") is True:
            reconciliation_status_counts["ok"] += 1
        elif reconciliation.get("ok") is False:
            reconciliation_status_counts["fail"] += 1
        else:
            reconciliation_status_counts["unknown"] += 1
        mismatch_total += _to_int(reconciliation.get("mismatches"))

        summary_file = run.get("summary_file")
        if isinstance(summary_file, str) and summary_file:
            summary_files.append(summary_file)

    run_quality_distribution = _sorted_counter(run_quality_counts)
    for value in RUN_QUALITY_VALUES:
        run_quality_distribution.setdefault(value, 0)

    return {
        "analysis_boundary": "offline_analysis_only",
        "eligible_skipped_rejected_totals": {
            "eligible": eligible_total,
            "rejected": rejected_total,
            "skipped": skipped_total,
        },
        "input": {
            "directory": str(base),
            "pattern": pattern,
            "recursive": recursive,
        },
        "reconciliation": {
            "mismatch_total": mismatch_total,
            "status_counts": _sorted_counter(reconciliation_status_counts),
        },
        "run_count": len(loaded),
        "run_files": sorted(run_files),
        "run_quality_distribution": dict(sorted(run_quality_distribution.items())),
        "skip_reason_counts": _sorted_counter(skip_reason_counts),
        "summary_files": sorted(summary_files),
    }


def render_markdown(summary: dict[str, Any]) -> str:
    quality = summary["run_quality_distribution"]
    totals = summary["eligible_skipped_rejected_totals"]
    reconciliation = summary["reconciliation"]
    lines = [
        "# Bounded Paper Runtime Evidence Series Summary",
        "",
        "Analysis boundary: offline analysis only. This output does not alter runtime execution.",
        "",
        f"- Run count: {summary['run_count']}",
        f"- Eligible total: {totals['eligible']}",
        f"- Skipped total: {totals['skipped']}",
        f"- Rejected total: {totals['rejected']}",
        f"- Reconciliation mismatches: {reconciliation['mismatch_total']}",
        "",
        "## Run Quality Distribution",
        "",
    ]
    for key in sorted(quality):
        lines.append(f"- {key}: {quality[key]}")

    lines.extend(["", "## Skip Reasons", ""])
    skip_reasons = summary["skip_reason_counts"]
    if skip_reasons:
        for key in sorted(skip_reasons):
            lines.append(f"- {key}: {skip_reasons[key]}")
    else:
        lines.append("- none: 0")

    lines.extend(["", "## Reconciliation Status", ""])
    for key, value in reconciliation["status_counts"].items():
        lines.append(f"- {key}: {value}")

    lines.extend(["", "## Summary Files", ""])
    summary_files = summary["summary_files"]
    if summary_files:
        for path in summary_files:
            lines.append(f"- {path}")
    else:
        lines.append("- none")

    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    summary = summarize_evidence(
        Path(args.input_dir),
        pattern=args.pattern,
        recursive=not args.no_recursive,
    )
    if args.format == "markdown":
        rendered = render_markdown(summary)
    else:
        rendered = json.dumps(summary, sort_keys=True, ensure_ascii=True, indent=2) + "\n"

    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

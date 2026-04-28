from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    module_path = REPO_ROOT / "scripts" / "validation" / "summarize_bounded_paper_runtime_evidence.py"
    spec = importlib.util.spec_from_file_location(
        "test_bounded_paper_runtime_evidence_summarizer_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load summarize_bounded_paper_runtime_evidence.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def _write_json(path: Path, payload: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, sort_keys=True) + "\n", encoding="utf-8")


def test_summarizer_aggregates_saved_run_outputs_deterministically(tmp_path: Path) -> None:
    module = _load_script_module()

    _write_json(
        tmp_path / "2026-04-07" / "run-002.json",
        {
            "run_quality_status": "no_eligible",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 0,
                        "rejected": 1,
                        "results": [
                            {"outcome": "skip:score_below_threshold", "signal_id": "sig-3"},
                            {"outcome": "reject:invalid_quantity", "signal_id": "sig-4"},
                        ],
                        "skipped": 1,
                        "status": "no_eligible",
                    },
                    "returncode": 1,
                },
                "reconciliation": {
                    "payload": {"mismatches": 0, "ok": True, "status": "pass"},
                    "returncode": 0,
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-07/daily-runtime-summary.json",
        },
    )
    _write_json(
        tmp_path / "2026-04-06" / "run-001.json",
        {
            "run_quality_status": "healthy",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 2,
                        "rejected": 0,
                        "results": [
                            {"outcome": "eligible", "signal_id": "sig-1"},
                            {"outcome": "skip:duplicate_entry", "signal_id": "sig-2"},
                        ],
                        "skipped": 1,
                        "status": "pass",
                    },
                    "returncode": 0,
                },
                "reconciliation": {
                    "payload": {"mismatches": 0, "ok": True, "status": "pass"},
                    "returncode": 0,
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary.json",
        },
    )
    _write_json(
        tmp_path / "2026-04-08" / "run-003.json",
        {
            "run_quality_status": "degraded",
            "status": "ok",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {
                        "eligible": 1,
                        "rejected": 0,
                        "results": [{"outcome": "skip:duplicate_entry", "signal_id": "sig-5"}],
                        "skipped": 1,
                        "status": "pass",
                    },
                    "returncode": 0,
                },
                "reconciliation": {
                    "payload": {"mismatches": 2, "ok": False, "status": "fail"},
                    "returncode": 1,
                },
            },
            "summary_file": "/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json",
        },
    )

    first = module.summarize_evidence(tmp_path, pattern="run-*.json")
    second = module.summarize_evidence(tmp_path, pattern="run-*.json")

    assert first == second
    assert first["analysis_boundary"] == "offline_analysis_only"
    assert first["run_count"] == 3
    assert first["run_files"] == [
        "2026-04-06/run-001.json",
        "2026-04-07/run-002.json",
        "2026-04-08/run-003.json",
    ]
    assert first["run_quality_distribution"] == {
        "degraded": 1,
        "healthy": 1,
        "no_eligible": 1,
    }
    assert first["eligible_skipped_rejected_totals"] == {
        "eligible": 3,
        "rejected": 1,
        "skipped": 3,
    }
    assert first["skip_reason_counts"] == {
        "duplicate_entry": 2,
        "score_below_threshold": 1,
    }
    assert first["reconciliation"] == {
        "mismatch_total": 2,
        "status_counts": {"fail": 1, "pass": 2},
    }
    assert first["summary_files"] == [
        "/data/artifacts/daily-runtime/2026-04-06/daily-runtime-summary.json",
        "/data/artifacts/daily-runtime/2026-04-07/daily-runtime-summary.json",
        "/data/artifacts/daily-runtime/2026-04-08/daily-runtime-summary.json",
    ]


def test_summarizer_cli_writes_json_and_markdown_outputs(tmp_path: Path) -> None:
    module = _load_script_module()
    _write_json(
        tmp_path / "run-001.json",
        {
            "run_quality_status": "healthy",
            "steps": {
                "bounded_paper_execution_cycle": {
                    "payload": {"eligible": 1, "rejected": 0, "results": [], "skipped": 0}
                },
                "reconciliation": {"payload": {"mismatches": 0, "ok": True}},
            },
            "summary_file": "summary-001.json",
        },
    )
    json_output = tmp_path / "summary.json"
    markdown_output = tmp_path / "summary.md"

    assert module.main(
        [
            "--input-dir",
            str(tmp_path),
            "--pattern",
            "run-*.json",
            "--output",
            str(json_output),
        ]
    ) == 0
    assert module.main(
        [
            "--input-dir",
            str(tmp_path),
            "--pattern",
            "run-*.json",
            "--format",
            "markdown",
            "--output",
            str(markdown_output),
        ]
    ) == 0

    parsed = json.loads(json_output.read_text(encoding="utf-8"))
    assert parsed["run_count"] == 1
    markdown = markdown_output.read_text(encoding="utf-8")
    assert "# Bounded Paper Runtime Evidence Series Summary" in markdown
    assert "Analysis boundary: offline analysis only." in markdown
    assert "- healthy: 1" in markdown

"""Regression tests for the parallel JSON loader in the evidence series service.

These tests cover the behaviour that was changed when `_load_run_files` was
moved from a sequential read loop to a `ThreadPoolExecutor`-backed parallel
read (issue #1129):

* Many evidence files still produce a deterministic, sorted output.
* The path-traversal guard still rejects symlinks pointing outside the
  configured evidence directory.
"""

from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from api.services.paper_runtime_evidence_series_service import (
    read_paper_runtime_evidence_series,
)


def _write_run(path: Path, index: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "run_quality_status": "healthy",
        "status": "ok",
        "steps": {
            "bounded_paper_execution_cycle": {
                "payload": {
                    "eligible": index,
                    "rejected": 0,
                    "results": [],
                    "skipped": 0,
                }
            },
            "reconciliation": {
                "payload": {"mismatches": 0, "ok": True, "status": "pass"}
            },
        },
    }
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


def test_parallel_loader_preserves_sorted_order_for_many_files(tmp_path: Path) -> None:
    # Use enough files to exercise the parallel path (well above the small
    # short-circuit) and to surface any ordering bug introduced by threading.
    file_count = 40
    for index in range(file_count):
        _write_run(tmp_path / f"run-{index:03d}.json", index)

    response = read_paper_runtime_evidence_series(evidence_series_dir=tmp_path)

    assert response.state == "available"
    assert response.run_count == file_count
    expected_files = [f"run-{index:03d}.json" for index in range(file_count)]
    assert response.run_files == expected_files
    assert response.eligible_skipped_rejected_totals.eligible == sum(range(file_count))


def test_parallel_loader_rejects_symlink_escaping_base(tmp_path: Path) -> None:
    outside_dir = tmp_path / "outside"
    outside_dir.mkdir()
    target = outside_dir / "leak.json"
    target.write_text("{}", encoding="utf-8")

    base = tmp_path / "evidence"
    base.mkdir()
    _write_run(base / "run-001.json", 1)

    symlink_path = base / "run-002.json"
    try:
        os.symlink(target, symlink_path)
    except (OSError, NotImplementedError):
        pytest.skip("symlinks not supported on this platform")

    with pytest.raises(ValueError, match="Path traversal attempt"):
        read_paper_runtime_evidence_series(evidence_series_dir=base)

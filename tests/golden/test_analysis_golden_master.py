from __future__ import annotations

import os
from pathlib import Path

from tests.utils.golden_master import (
    build_canonical_output_bytes,
    prepare_snapshot_db,
    write_canonical_output_snapshot,
)


def _format_byte(value: int | None) -> str:
    if value is None:
        return "None"
    return f"{value} (0x{value:02x})"


def _context_slice(data: bytes, index: int, radius: int = 20) -> str:
    start = max(0, index - radius)
    end = min(len(data), index + radius)
    return data[start:end].decode("utf-8", errors="replace")


def _describe_first_diff(expected: bytes, actual: bytes) -> str:
    min_len = min(len(expected), len(actual))
    mismatch_index = next(
        (
            idx
            for idx, (left, right) in enumerate(zip(expected[:min_len], actual[:min_len], strict=True))
            if left != right
        ),
        None,
    )
    if mismatch_index is None:
        mismatch_index = min_len

    expected_byte = expected[mismatch_index] if mismatch_index < len(expected) else None
    actual_byte = actual[mismatch_index] if mismatch_index < len(actual) else None

    expected_context = _context_slice(expected, mismatch_index)
    actual_context = _context_slice(actual, mismatch_index)

    return (
        "first_difference_index: {index}\n"
        "expected_byte: {expected_byte}\n"
        "actual_byte: {actual_byte}\n"
        "expected_context: {expected_context}\n"
        "actual_context: {actual_context}"
    ).format(
        index=mismatch_index,
        expected_byte=_format_byte(expected_byte),
        actual_byte=_format_byte(actual_byte),
        expected_context=expected_context,
        actual_context=actual_context,
    )


def test_analysis_golden_master_snapshot(tmp_path: Path) -> None:
    snapshot_path = Path("tests/golden/analysis_output_golden_v1.json")
    expected_bytes = snapshot_path.read_bytes()

    db_path = tmp_path / "analysis.db"
    prepare_snapshot_db(db_path)
    actual_bytes = build_canonical_output_bytes(db_path)

    if os.environ.get("UPDATE_GOLDEN_SNAPSHOTS") == "1":
        expected_bytes = write_canonical_output_snapshot(snapshot_path, db_path)

    if actual_bytes != expected_bytes:
        details = _describe_first_diff(expected_bytes, actual_bytes)
        raise AssertionError(
            "Golden master mismatch\n"
            f"snapshot_path: {snapshot_path}\n"
            f"expected_length: {len(expected_bytes)}\n"
            f"actual_length: {len(actual_bytes)}\n"
            f"{details}"
        )

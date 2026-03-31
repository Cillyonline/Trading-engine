from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _read(relative_path: str) -> str:
    return (REPO_ROOT / relative_path).read_text(encoding="utf-8")


def test_ops_p50_authoritative_snapshot_ingestion_contract_is_bounded_and_explicit() -> None:
    content = _read("docs/operations/runtime/snapshot_ingestion_contract.md")

    assert content.startswith("# Canonical Real-Market Snapshot Ingestion Contract")
    assert "single authoritative server-side contract" in content
    assert "It governs server-side snapshot creation only." in content
    assert "It does not define a public API." in content
    assert "It does not expand into live trading, broker execution, charting, or UI scope." in content


def test_ops_p50_contract_defines_required_ingestion_run_fields_and_snapshot_row_shape() -> None:
    content = _read("docs/operations/runtime/snapshot_ingestion_contract.md")

    assert "| `ingestion_run_id` | required |" in content
    assert "| `created_at` | required |" in content
    assert "| `source` | required |" in content
    assert "| `symbols_json` | required |" in content
    assert "| `timeframe` | required |" in content
    assert "| `fingerprint_hash` | optional |" in content

    assert "| `ingestion_run_id` | required | Foreign key to the parent `ingestion_runs` row. |" in content
    assert "| `symbol` | required | Instrument identifier covered by the snapshot. |" in content
    assert "| `timeframe` | required | Timeframe for the row. |" in content
    assert "| `ts` | required | Candle timestamp stored as Unix epoch milliseconds. |" in content
    assert "| `open` | required | Open price. |" in content
    assert "| `high` | required | High price. |" in content
    assert "| `low` | required | Low price. |" in content
    assert "| `close` | required | Close price. |" in content
    assert "| `volume` | required | Volume value stored with the candle. |" in content


def test_ops_p50_contract_distinguishes_valid_missing_invalid_and_immutability_boundary() -> None:
    content = _read("docs/operations/runtime/snapshot_ingestion_contract.md")

    assert "### Valid snapshot" in content
    assert "### Missing snapshot" in content
    assert "### Invalid snapshot" in content
    assert "`ingestion_run_not_found` and `ingestion_run_not_ready`" in content
    assert "`snapshot_data_invalid`" in content
    assert "The ingestion boundary is append-only at create time and immutable after" in content
    assert "corrections, reloads, or provider changes require a new `ingestion_run_id`" in content
    assert "`ohlcv_snapshots` rows must not be updated or deleted in place" in content


def test_ops_p50_usage_and_analyst_docs_reference_same_contract_boundary() -> None:
    usage = _read("docs/operations/api/usage_contract.md")
    analyst = _read("docs/operations/analyst-workflow.md")
    analyst_flat = " ".join(analyst.split())

    assert "docs/operations/runtime/snapshot_ingestion_contract.md" in usage
    assert "docs/operations/runtime/snapshot_ingestion_contract.md" in analyst
    assert "analysis endpoints do not define or expose a public ingestion API" in usage
    assert (
        "snapshot creation is bounded to server-side creation of `ingestion_runs` "
        "and `ohlcv_snapshots` for later analysis use"
    ) in analyst_flat
    assert "The snapshot-only API contract remains the authoritative deterministic runtime boundary." in usage

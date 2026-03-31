from __future__ import annotations

import importlib.util
import json
import sys
from dataclasses import dataclass
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_script_module():
    module_path = REPO_ROOT / "scripts" / "run_snapshot_ingestion.py"
    spec = importlib.util.spec_from_file_location(
        "test_run_snapshot_ingestion_script_module",
        module_path,
    )
    if spec is None or spec.loader is None:
        raise RuntimeError("Unable to load run_snapshot_ingestion.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@dataclass(frozen=True)
class _FakeJobResult:
    ingestion_run_id: str
    created_at: str
    provider_name: str
    timeframe: str
    symbols: tuple[str, ...]
    inserted_rows: int
    fingerprint_hash: str
    datasets: tuple[dict[str, object], ...]


class _FakeRepository:
    def __init__(self, *, db_path: Path) -> None:
        self.db_path = db_path


def test_run_snapshot_ingestion_writes_success_evidence_and_releases_lock(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()
    evidence_dir = tmp_path / "evidence"
    lock_path = tmp_path / "snapshot-ingestion.lock"
    db_path = tmp_path / "analysis.db"

    class _FakeJob:
        def __init__(self, *, repository, provider_registry) -> None:
            self.repository = repository
            self.provider_registry = provider_registry

        def run(self, request):
            assert request.symbols == ("AAPL", "MSFT")
            assert request.timeframe == "D1"
            assert request.provider_name == "yfinance"
            return _FakeJobResult(
                ingestion_run_id="run-123",
                created_at="2026-03-31T06:05:00+00:00",
                provider_name="yfinance",
                timeframe="D1",
                symbols=("AAPL", "MSFT"),
                inserted_rows=180,
                fingerprint_hash="fingerprint-123",
                datasets=(),
            )

    monkeypatch.setattr(module, "SnapshotIngestionJob", _FakeJob)
    monkeypatch.setattr(module, "SqliteSnapshotIngestionRepository", _FakeRepository)
    monkeypatch.setattr(
        module,
        "build_default_snapshot_provider_registry",
        lambda: "provider-registry",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_snapshot_ingestion.py",
            "--symbols",
            "AAPL,MSFT",
            "--provider",
            "yfinance",
            "--db-path",
            str(db_path),
            "--evidence-dir",
            str(evidence_dir),
            "--lock-file",
            str(lock_path),
        ],
    )

    exit_code = module.main()

    assert exit_code == 0
    output = json.loads(capsys.readouterr().out)
    evidence_file = evidence_dir / "ingestion-run-run-123.json"
    assert output["status"] == "ok"
    assert output["evidence_file"] == str(evidence_file)
    assert evidence_file.exists()
    assert json.loads(evidence_file.read_text(encoding="utf-8"))["result"]["ingestion_run_id"] == "run-123"
    assert not lock_path.exists()


def test_run_snapshot_ingestion_fails_closed_when_lock_exists(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()
    evidence_dir = tmp_path / "evidence"
    lock_path = tmp_path / "snapshot-ingestion.lock"
    lock_path.write_text("{\"status\":\"running\"}\n", encoding="utf-8")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_snapshot_ingestion.py",
            "--symbols",
            "AAPL",
            "--evidence-dir",
            str(evidence_dir),
            "--lock-file",
            str(lock_path),
        ],
    )

    exit_code = module.main()

    assert exit_code == 1
    output = json.loads(capsys.readouterr().err)
    assert output["code"] == "snapshot_ingestion_already_running"
    evidence_files = sorted(evidence_dir.glob("snapshot-ingestion-failed-*.json"))
    assert len(evidence_files) == 1
    assert output["evidence_file"] == str(evidence_files[0])
    assert lock_path.exists()


def test_run_snapshot_ingestion_writes_failure_evidence_for_job_error(
    monkeypatch,
    tmp_path: Path,
    capsys,
) -> None:
    module = _load_script_module()
    evidence_dir = tmp_path / "evidence"
    lock_path = tmp_path / "snapshot-ingestion.lock"

    class _FailingJob:
        def __init__(self, *, repository, provider_registry) -> None:
            self.repository = repository
            self.provider_registry = provider_registry

        def run(self, request):
            raise module.SnapshotIngestionJobError(
                "snapshot_provider_empty",
                "provider returned no candles",
                provider_name="yfinance",
                symbol="AAPL",
            )

    monkeypatch.setattr(module, "SnapshotIngestionJob", _FailingJob)
    monkeypatch.setattr(module, "SqliteSnapshotIngestionRepository", _FakeRepository)
    monkeypatch.setattr(
        module,
        "build_default_snapshot_provider_registry",
        lambda: "provider-registry",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "run_snapshot_ingestion.py",
            "--symbols",
            "AAPL",
            "--provider",
            "yfinance",
            "--evidence-dir",
            str(evidence_dir),
            "--lock-file",
            str(lock_path),
        ],
    )

    exit_code = module.main()

    assert exit_code == 1
    output = json.loads(capsys.readouterr().err)
    evidence_files = sorted(evidence_dir.glob("snapshot-ingestion-failed-*.json"))
    assert output["code"] == "snapshot_provider_empty"
    assert len(evidence_files) == 1
    assert output["evidence_file"] == str(evidence_files[0])
    assert not lock_path.exists()

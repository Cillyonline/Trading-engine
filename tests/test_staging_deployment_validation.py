from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from scripts.validate_staging_deployment import (
    EXIT_CODE_LOGGING_CHECK_FAILED,
    HealthSnapshot,
    PersistenceProbe,
    StagingValidationError,
    run_staging_validation,
)


REPO_ROOT = Path(__file__).resolve().parents[1]


def _healthy_snapshot() -> HealthSnapshot:
    return HealthSnapshot(
        health={"status": "healthy"},
        engine={"mode": "running", "reason": "runtime_running_fresh", "ready": True},
        data={"reason": "data_source_available", "ready": True},
        guards={"decision": "allowing", "ready": True},
    )


def test_staging_artifacts_define_canonical_runtime_contract() -> None:
    dockerfile_content = (
        REPO_ROOT / "docker" / "staging" / "Dockerfile"
    ).read_text(encoding="utf-8")
    compose_content = (
        REPO_ROOT / "docker" / "staging" / "docker-compose.staging.yml"
    ).read_text(encoding="utf-8")

    assert "FROM python:3.12.8-slim" in dockerfile_content
    assert "python -m pip install -U pip uv" in dockerfile_content
    assert "uv sync --frozen --no-dev" in dockerfile_content
    assert 'CILLY_DB_PATH="/data/cilly_trading.db"' in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content
    assert 'CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile_content

    assert "dockerfile: docker/staging/Dockerfile" in compose_content
    assert '"18000:8000"' in compose_content
    assert "working_dir: /data" in compose_content
    assert "CILLY_DB_PATH: /data/cilly_trading.db" in compose_content
    assert "CILLY_LOG_FORMAT: json" in compose_content
    assert "restart: unless-stopped" in compose_content
    assert "healthcheck:" in compose_content
    assert "cilly_staging_data:/data" in compose_content


def test_run_staging_validation_includes_logging_and_persistence_checks() -> None:
    commands: list[list[str]] = []
    log_checks: list[int] = []
    deleted_probes: list[str] = []
    compose_file = Path("docker/staging/docker-compose.staging.yml")

    def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        commands.append(command)
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def _wait_for_readiness(**_kwargs) -> HealthSnapshot:
        return _healthy_snapshot()

    def _validate_logs(*, minimum_startup_entries: int, **_kwargs) -> dict[str, int]:
        log_checks.append(minimum_startup_entries)
        return {"startup_entries": minimum_startup_entries, "json_lines": minimum_startup_entries}

    def _create_probe(_base_url: str) -> PersistenceProbe:
        return PersistenceProbe(
            watchlist_id="ops-p46-probe",
            name="OPS-P46 probe",
            symbols=("AAPL",),
        )

    def _verify_probe(*, probe: PersistenceProbe, **_kwargs) -> dict[str, object]:
        return {
            "watchlist_id": probe.watchlist_id,
            "persisted": True,
        }

    def _delete_probe(*, probe: PersistenceProbe, **_kwargs) -> None:
        deleted_probes.append(probe.watchlist_id)

    summary = run_staging_validation(
        compose_file=compose_file,
        base_url="http://127.0.0.1:18000",
        timeout_seconds=5,
        keep_running=False,
        run_command=_run_command,
        wait_for_readiness=_wait_for_readiness,
        validate_compose_logs=_validate_logs,
        create_persistence_probe=_create_probe,
        verify_persistence_probe=_verify_probe,
        delete_persistence_probe=_delete_probe,
    )

    assert commands == [
        ["docker", "compose", "-f", str(compose_file), "config"],
        ["docker", "compose", "-f", str(compose_file), "up", "-d", "--build"],
        ["docker", "compose", "-f", str(compose_file), "restart", "api"],
        ["docker", "compose", "-f", str(compose_file), "down", "--remove-orphans"],
    ]
    assert log_checks == [1, 2]
    assert deleted_probes == ["ops-p46-probe"]
    assert summary["logging"] == {
        "pre_restart": {"startup_entries": 1, "json_lines": 1},
        "post_restart": {"startup_entries": 2, "json_lines": 2},
    }
    assert summary["persistence"] == {
        "watchlist_id": "ops-p46-probe",
        "persisted": True,
    }


def test_run_staging_validation_raises_logging_exit_code_when_log_validation_fails() -> None:
    def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    def _wait_for_readiness(**_kwargs) -> HealthSnapshot:
        return _healthy_snapshot()

    with pytest.raises(StagingValidationError) as exc_info:
        run_staging_validation(
            compose_file=Path("docker/staging/docker-compose.staging.yml"),
            base_url="http://127.0.0.1:18000",
            timeout_seconds=5,
            keep_running=True,
            run_command=_run_command,
            wait_for_readiness=_wait_for_readiness,
            validate_compose_logs=lambda **_kwargs: (_ for _ in ()).throw(
                ValueError("json_operational_logs_missing")
            ),
        )

    assert exc_info.value.exit_code == EXIT_CODE_LOGGING_CHECK_FAILED

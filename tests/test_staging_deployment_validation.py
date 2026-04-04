from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

import scripts.validate_staging_deployment as staging_validation
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
    assert "COPY scripts ./scripts" in dockerfile_content
    assert 'CILLY_DB_PATH="/data/db/cilly_trading.db"' in dockerfile_content
    assert "RUN mkdir -p /data/db /data/artifacts /data/logs /data/runtime-state /app/runs/phase6" in dockerfile_content
    assert "HEALTHCHECK" in dockerfile_content
    assert 'CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]' in dockerfile_content

    assert "dockerfile: docker/staging/Dockerfile" in compose_content
    assert '"18000:8000"' in compose_content
    assert 'user: "${CILLY_CONTAINER_UID:?set CILLY_CONTAINER_UID}:${CILLY_CONTAINER_GID:?set CILLY_CONTAINER_GID}"' in compose_content
    assert "working_dir: /data" in compose_content
    assert 'PYTHONPATH: "${PYTHONPATH:?set PYTHONPATH}"' in compose_content
    assert 'CILLY_DB_PATH: "${CILLY_DB_PATH:?set CILLY_DB_PATH}"' in compose_content
    assert 'CILLY_LOG_LEVEL: "${CILLY_LOG_LEVEL:?set CILLY_LOG_LEVEL}"' in compose_content
    assert 'CILLY_LOG_FORMAT: "${CILLY_LOG_FORMAT:?set CILLY_LOG_FORMAT}"' in compose_content
    assert "restart: unless-stopped" in compose_content
    assert "healthcheck:" in compose_content
    assert 'source: "${CILLY_STAGING_DB_DIR:?set CILLY_STAGING_DB_DIR}"' in compose_content
    assert "target: /data/db" in compose_content
    assert 'source: "${CILLY_STAGING_ARTIFACT_DIR:?set CILLY_STAGING_ARTIFACT_DIR}"' in compose_content
    assert "target: /data/artifacts" in compose_content
    assert 'source: "${CILLY_STAGING_JOURNAL_DIR:?set CILLY_STAGING_JOURNAL_DIR}"' in compose_content
    assert "target: /app/runs/phase6" in compose_content
    assert 'source: "${CILLY_STAGING_LOG_DIR:?set CILLY_STAGING_LOG_DIR}"' in compose_content
    assert "target: /data/logs" in compose_content
    assert 'source: "${CILLY_STAGING_RUNTIME_STATE_DIR:?set CILLY_STAGING_RUNTIME_STATE_DIR}"' in compose_content
    assert "target: /data/runtime-state" in compose_content


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
        env_file=Path(".env"),
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
        ["docker", "compose", "--env-file", ".env", "-f", str(compose_file), "config"],
        ["docker", "compose", "--env-file", ".env", "-f", str(compose_file), "up", "-d", "--build"],
        ["docker", "compose", "--env-file", ".env", "-f", str(compose_file), "restart", "api"],
        ["docker", "compose", "--env-file", ".env", "-f", str(compose_file), "down", "--remove-orphans"],
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
            env_file=Path(".env"),
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


def test_wait_for_readiness_retries_after_transient_connection_reset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = {"count": 0}

    def _check_readiness(_base_url: str) -> HealthSnapshot:
        attempts["count"] += 1
        if attempts["count"] == 1:
            raise ConnectionResetError(104, "Connection reset by peer")
        return _healthy_snapshot()

    monkeypatch.setattr(staging_validation, "_check_readiness", _check_readiness)
    monkeypatch.setattr(staging_validation.time, "sleep", lambda _seconds: None)

    snapshot = staging_validation._wait_for_readiness(
        base_url="http://127.0.0.1:18000",
        timeout_seconds=1,
        poll_interval_seconds=0.0,
    )

    assert attempts["count"] == 2
    assert snapshot == _healthy_snapshot()

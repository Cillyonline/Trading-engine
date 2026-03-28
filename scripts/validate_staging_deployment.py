from __future__ import annotations

import argparse
import json
import subprocess
import time
import urllib.error
import urllib.request
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

READ_ONLY_ROLE_HEADER = "X-Cilly-Role"
READ_ONLY_ROLE_VALUE = "read_only"
OPERATOR_ROLE_VALUE = "operator"

EXIT_CODE_COMPOSE_CONFIG_FAILED = 20
EXIT_CODE_COMPOSE_UP_FAILED = 21
EXIT_CODE_HEALTH_CHECK_FAILED = 22
EXIT_CODE_RESTART_FAILED = 23
EXIT_CODE_POST_RESTART_HEALTH_FAILED = 24
EXIT_CODE_COMPOSE_DOWN_FAILED = 25
EXIT_CODE_LOGGING_CHECK_FAILED = 26
EXIT_CODE_PERSISTENCE_CHECK_FAILED = 27


@dataclass(frozen=True)
class HealthSnapshot:
    health: dict[str, Any]
    engine: dict[str, Any]
    data: dict[str, Any]
    guards: dict[str, Any]


@dataclass(frozen=True)
class PersistenceProbe:
    watchlist_id: str
    name: str
    symbols: tuple[str, ...]


class StagingValidationError(RuntimeError):
    def __init__(self, message: str, *, exit_code: int) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def _run_command(command: list[str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(command, capture_output=True, text=True)


def _run_compose(
    *,
    compose_file: Path,
    args: list[str],
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]],
) -> subprocess.CompletedProcess[str]:
    command = ["docker", "compose", "-f", str(compose_file), *args]
    return run_command(command)


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
        url,
        data=encoded_payload,
        headers=request_headers,
        method=method,
    )
    with urllib.request.urlopen(request, timeout=3) as response:  # nosec B310
        body = response.read().decode("utf-8")

    parsed = json.loads(body)
    if not isinstance(parsed, dict):
        raise ValueError(f"Expected object payload from {url}, got {type(parsed).__name__}")
    return parsed


def _fetch_json(url: str) -> dict[str, Any]:
    return _request_json(
        url,
        headers={READ_ONLY_ROLE_HEADER: READ_ONLY_ROLE_VALUE},
    )


def _check_readiness(base_url: str) -> HealthSnapshot:
    health = _fetch_json(f"{base_url}/health")
    engine = _fetch_json(f"{base_url}/health/engine")
    data = _fetch_json(f"{base_url}/health/data")
    guards = _fetch_json(f"{base_url}/health/guards")

    if not engine.get("ready"):
        raise ValueError("engine readiness check failed")
    if not data.get("ready"):
        raise ValueError("data readiness check failed")
    if not guards.get("ready"):
        raise ValueError("guards readiness check failed")

    return HealthSnapshot(
        health=health,
        engine=engine,
        data=data,
        guards=guards,
    )


def _wait_for_readiness(
    *,
    base_url: str,
    timeout_seconds: int,
    poll_interval_seconds: float = 2.0,
) -> HealthSnapshot:
    deadline = time.monotonic() + timeout_seconds
    last_error = "readiness_not_reached"

    while time.monotonic() < deadline:
        try:
            return _check_readiness(base_url)
        except (urllib.error.URLError, TimeoutError, ValueError, json.JSONDecodeError) as exc:
            last_error = str(exc)
            time.sleep(poll_interval_seconds)

    raise TimeoutError(last_error)


def _extract_json_record(line: str) -> dict[str, Any] | None:
    start = line.find("{")
    end = line.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None

    try:
        payload = json.loads(line[start : end + 1])
    except json.JSONDecodeError:
        return None

    if isinstance(payload, dict):
        return payload
    return None


def _validate_compose_logs(
    *,
    compose_file: Path,
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]],
    minimum_startup_entries: int,
) -> dict[str, Any]:
    logs_result = _run_compose(
        compose_file=compose_file,
        args=["logs", "--no-color", "api"],
        run_command=run_command,
    )
    if logs_result.returncode != 0:
        raise ValueError("docker compose logs api failed")

    json_records: list[dict[str, Any]] = []
    startup_entries = 0
    for line in logs_result.stdout.splitlines():
        record = _extract_json_record(line.strip())
        if record is None:
            continue
        if {"timestamp", "level", "logger", "message"} - set(record):
            continue
        json_records.append(record)
        if record["message"] == "Cilly Trading Engine API starting up":
            startup_entries += 1

    if not json_records:
        raise ValueError("json_operational_logs_missing")
    if startup_entries < minimum_startup_entries:
        raise ValueError("startup_log_entries_missing")

    return {
        "json_lines": len(json_records),
        "startup_entries": startup_entries,
    }


def _create_persistence_probe(base_url: str) -> PersistenceProbe:
    watchlist_id = f"ops-p46-{uuid.uuid4().hex[:12]}"
    name = f"OPS-P46 {watchlist_id[-6:]}"
    symbols = ("AAPL",)
    created = _request_json(
        f"{base_url}/watchlists",
        headers={READ_ONLY_ROLE_HEADER: OPERATOR_ROLE_VALUE},
        method="POST",
        payload={
            "watchlist_id": watchlist_id,
            "name": name,
            "symbols": list(symbols),
        },
    )
    if created.get("watchlist_id") != watchlist_id:
        raise ValueError("persistence_probe_create_failed")

    return PersistenceProbe(
        watchlist_id=watchlist_id,
        name=name,
        symbols=symbols,
    )


def _verify_persistence_probe(
    *,
    base_url: str,
    probe: PersistenceProbe,
) -> dict[str, Any]:
    persisted = _request_json(
        f"{base_url}/watchlists/{probe.watchlist_id}",
        headers={READ_ONLY_ROLE_HEADER: READ_ONLY_ROLE_VALUE},
    )
    if persisted.get("watchlist_id") != probe.watchlist_id:
        raise ValueError("persistence_probe_missing_after_restart")
    if persisted.get("name") != probe.name:
        raise ValueError("persistence_probe_name_changed_after_restart")
    if tuple(persisted.get("symbols", ())) != probe.symbols:
        raise ValueError("persistence_probe_symbols_changed_after_restart")

    return {
        "watchlist_id": probe.watchlist_id,
        "persisted": True,
    }


def _delete_persistence_probe(
    *,
    base_url: str,
    probe: PersistenceProbe,
) -> None:
    _request_json(
        f"{base_url}/watchlists/{probe.watchlist_id}",
        headers={READ_ONLY_ROLE_HEADER: OPERATOR_ROLE_VALUE},
        method="DELETE",
    )


def run_staging_validation(
    *,
    compose_file: Path,
    base_url: str,
    timeout_seconds: int,
    keep_running: bool,
    run_command: Callable[[list[str]], subprocess.CompletedProcess[str]] = _run_command,
    wait_for_readiness: Callable[..., HealthSnapshot] = _wait_for_readiness,
    validate_compose_logs: Callable[..., dict[str, Any]] = _validate_compose_logs,
    create_persistence_probe: Callable[[str], PersistenceProbe] = _create_persistence_probe,
    verify_persistence_probe: Callable[..., dict[str, Any]] = _verify_persistence_probe,
    delete_persistence_probe: Callable[..., None] = _delete_persistence_probe,
) -> dict[str, Any]:
    up_succeeded = False
    summary: dict[str, Any] = {}
    phase = "pre_start"
    persistence_probe: PersistenceProbe | None = None

    config_result = _run_compose(
        compose_file=compose_file,
        args=["config"],
        run_command=run_command,
    )
    if config_result.returncode != 0:
        raise StagingValidationError(
            "docker compose config failed",
            exit_code=EXIT_CODE_COMPOSE_CONFIG_FAILED,
        )
    print("STAGING_VALIDATE:CONFIG_OK")

    try:
        up_result = _run_compose(
            compose_file=compose_file,
            args=["up", "-d", "--build"],
            run_command=run_command,
        )
        if up_result.returncode != 0:
            raise StagingValidationError(
                "docker compose up failed",
                exit_code=EXIT_CODE_COMPOSE_UP_FAILED,
            )
        up_succeeded = True
        print("STAGING_VALIDATE:UP_OK")

        phase = "pre_restart_health"
        first_snapshot = wait_for_readiness(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        summary["pre_restart"] = {
            "mode": first_snapshot.engine.get("mode"),
            "health_status": first_snapshot.health.get("status"),
            "engine_reason": first_snapshot.engine.get("reason"),
            "data_reason": first_snapshot.data.get("reason"),
            "guards_decision": first_snapshot.guards.get("decision"),
        }
        print("STAGING_VALIDATE:HEALTH_OK")

        phase = "pre_restart_logs"
        summary["logging"] = {
            "pre_restart": validate_compose_logs(
                compose_file=compose_file,
                run_command=run_command,
                minimum_startup_entries=1,
            )
        }
        print("STAGING_VALIDATE:LOGS_OK")

        phase = "persistence_probe_create"
        persistence_probe = create_persistence_probe(base_url)
        print("STAGING_VALIDATE:PERSISTENCE_PROBE_OK")

        restart_result = _run_compose(
            compose_file=compose_file,
            args=["restart", "api"],
            run_command=run_command,
        )
        if restart_result.returncode != 0:
            raise StagingValidationError(
                "docker compose restart api failed",
                exit_code=EXIT_CODE_RESTART_FAILED,
            )
        print("STAGING_VALIDATE:RESTART_OK")

        phase = "post_restart_health"
        second_snapshot = wait_for_readiness(
            base_url=base_url,
            timeout_seconds=timeout_seconds,
        )
        summary["post_restart"] = {
            "mode": second_snapshot.engine.get("mode"),
            "health_status": second_snapshot.health.get("status"),
            "engine_reason": second_snapshot.engine.get("reason"),
            "data_reason": second_snapshot.data.get("reason"),
            "guards_decision": second_snapshot.guards.get("decision"),
        }
        print("STAGING_VALIDATE:POST_RESTART_HEALTH_OK")

        phase = "post_restart_logs"
        summary["logging"]["post_restart"] = validate_compose_logs(
            compose_file=compose_file,
            run_command=run_command,
            minimum_startup_entries=2,
        )
        print("STAGING_VALIDATE:POST_RESTART_LOGS_OK")

        phase = "post_restart_persistence"
        if persistence_probe is None:
            raise ValueError("persistence_probe_missing")
        summary["persistence"] = verify_persistence_probe(
            base_url=base_url,
            probe=persistence_probe,
        )
        print("STAGING_VALIDATE:PERSISTENCE_OK")

        return summary
    except TimeoutError as exc:
        if phase == "post_restart_health":
            raise StagingValidationError(
                f"health checks failed after restart: {exc}",
                exit_code=EXIT_CODE_POST_RESTART_HEALTH_FAILED,
            ) from exc
        raise StagingValidationError(
            f"health checks failed: {exc}",
            exit_code=EXIT_CODE_HEALTH_CHECK_FAILED,
        ) from exc
    except (urllib.error.URLError, ValueError, json.JSONDecodeError) as exc:
        if phase.startswith("pre_restart_logs") or phase.startswith("post_restart_logs"):
            raise StagingValidationError(
                f"logging validation failed: {exc}",
                exit_code=EXIT_CODE_LOGGING_CHECK_FAILED,
            ) from exc
        if phase.startswith("persistence_probe") or phase == "post_restart_persistence":
            raise StagingValidationError(
                f"restart persistence validation failed: {exc}",
                exit_code=EXIT_CODE_PERSISTENCE_CHECK_FAILED,
            ) from exc
        raise StagingValidationError(
            f"health checks failed: {exc}",
            exit_code=EXIT_CODE_HEALTH_CHECK_FAILED,
        ) from exc
    finally:
        if up_succeeded and persistence_probe is not None:
            try:
                delete_persistence_probe(
                    base_url=base_url,
                    probe=persistence_probe,
                )
            except (urllib.error.URLError, ValueError, json.JSONDecodeError):
                pass

        if up_succeeded and not keep_running:
            down_result = _run_compose(
                compose_file=compose_file,
                args=["down", "--remove-orphans"],
                run_command=run_command,
            )
            if down_result.returncode != 0:
                raise StagingValidationError(
                    "docker compose down failed",
                    exit_code=EXIT_CODE_COMPOSE_DOWN_FAILED,
                )
            print("STAGING_VALIDATE:DOWN_OK")


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python scripts/validate_staging_deployment.py",
        description=(
            "Bounded staging deployment validation: compose config, health checks, "
            "operational logging, and restart persistence checks."
        ),
    )
    parser.add_argument(
        "--compose-file",
        default="docker/staging/docker-compose.staging.yml",
        help="Path to the staging docker compose file.",
    )
    parser.add_argument(
        "--base-url",
        default="http://127.0.0.1:18000",
        help="Base URL for health/readiness checks.",
    )
    parser.add_argument(
        "--timeout-seconds",
        type=int,
        default=90,
        help="Readiness timeout in seconds for each health verification phase.",
    )
    parser.add_argument(
        "--keep-running",
        action="store_true",
        help="Leave the compose stack running after validation.",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)

    try:
        summary = run_staging_validation(
            compose_file=Path(args.compose_file),
            base_url=args.base_url.rstrip("/"),
            timeout_seconds=args.timeout_seconds,
            keep_running=args.keep_running,
        )
    except StagingValidationError as exc:
        print(f"STAGING_VALIDATE:FAILED:{exc}")
        return exc.exit_code

    print("STAGING_VALIDATE:SUCCESS")
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

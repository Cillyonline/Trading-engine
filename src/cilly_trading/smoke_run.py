"""Deterministic smoke-run execution per docs/smoke-run.md."""

from __future__ import annotations

import csv
import json
import math
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class SmokeRunConfig:
    engine_name: str
    engine_version: str
    precision: int


@dataclass(frozen=True)
class SmokeRunInput:
    run_id: str
    base_currency: str
    quote_currency: str
    start_price: float
    end_price: float
    ticks: int


class SmokeRunError(Exception):
    """Base exception for smoke-run errors."""

    def __init__(self, exit_code: int, message: str) -> None:
        super().__init__(message)
        self.exit_code = exit_code


def run_smoke_run(
    fixtures_dir: str | Path = "fixtures/smoke-run",
    artifacts_dir: str | Path = "artifacts/smoke-run",
) -> int:
    """Execute the deterministic smoke-run contract.

    Args:
        fixtures_dir: Directory containing the smoke-run fixtures.
        artifacts_dir: Directory where smoke-run artifacts are written.

    Returns:
        Exit code as defined in docs/smoke-run.md.
    """

    try:
        fixtures_path = Path(fixtures_dir)
        input_path = fixtures_path / "input.json"
        expected_path = fixtures_path / "expected.csv"
        config_path = fixtures_path / "config.yaml"
        _ensure_fixtures_exist([input_path, expected_path, config_path])

        input_payload = _load_input(input_path)
        config_payload = _load_config(config_path)
        expected_rows = _load_expected(expected_path)

        _validate_constraints(input_payload, config_payload, expected_rows)

        result_payload = {
            "engine_name": config_payload.engine_name,
            "engine_version": config_payload.engine_version,
            "precision": config_payload.precision,
            "run_id": input_payload.run_id,
            "status": "ok",
            "ticks": input_payload.ticks,
        }
        result_bytes = json.dumps(
            result_payload,
            separators=(",", ":"),
            sort_keys=True,
        ).encode("utf-8")
        _write_result(Path(artifacts_dir), result_bytes)

        _emit_stdout()
        return 0
    except SmokeRunError as exc:
        return exc.exit_code


def _ensure_fixtures_exist(paths: list[Path]) -> None:
    missing = [path for path in paths if not path.is_file()]
    if missing:
        raise SmokeRunError(10, "fixtures_missing")


def _load_input(path: Path) -> SmokeRunInput:
    payload = _read_json(path)
    required_keys = {
        "run_id": str,
        "base_currency": str,
        "quote_currency": str,
        "start_price": (int, float),
        "end_price": (int, float),
        "ticks": int,
    }
    _ensure_mapping(payload)
    for key, expected_type in required_keys.items():
        if key not in payload or payload[key] is None:
            raise SmokeRunError(11, "fixtures_invalid")
        value = payload[key]
        if isinstance(value, bool):
            raise SmokeRunError(11, "fixtures_invalid")
        if not isinstance(value, expected_type):
            raise SmokeRunError(11, "fixtures_invalid")

    start_price = float(payload["start_price"])
    end_price = float(payload["end_price"])
    if not math.isfinite(start_price) or not math.isfinite(end_price):
        raise SmokeRunError(12, "constraints_failed")

    ticks = int(payload["ticks"])
    if payload["ticks"] != ticks:
        raise SmokeRunError(11, "fixtures_invalid")

    return SmokeRunInput(
        run_id=str(payload["run_id"]),
        base_currency=str(payload["base_currency"]),
        quote_currency=str(payload["quote_currency"]),
        start_price=start_price,
        end_price=end_price,
        ticks=ticks,
    )


def _load_config(path: Path) -> SmokeRunConfig:
    payload = _read_simple_yaml_mapping(path)
    required_keys = {"engine_name", "engine_version", "precision"}
    if not required_keys.issubset(payload.keys()):
        raise SmokeRunError(11, "fixtures_invalid")
    if payload["engine_name"] is None or payload["engine_version"] is None:
        raise SmokeRunError(11, "fixtures_invalid")

    try:
        precision = int(payload["precision"])
    except (TypeError, ValueError):
        raise SmokeRunError(11, "fixtures_invalid") from None
    if payload["precision"] != precision:
        raise SmokeRunError(11, "fixtures_invalid")

    return SmokeRunConfig(
        engine_name=str(payload["engine_name"]),
        engine_version=str(payload["engine_version"]),
        precision=precision,
    )


def _load_expected(path: Path) -> list[dict[str, str]]:
    try:
        with path.open("r", encoding="utf-8", newline="") as handle:
            reader = csv.reader(handle)
            try:
                header = next(reader)
            except StopIteration:
                raise SmokeRunError(11, "fixtures_invalid") from None
            if header != ["run_id", "tick_index", "price"]:
                raise SmokeRunError(11, "fixtures_invalid")
            rows = []
            for row in reader:
                if len(row) != 3:
                    raise SmokeRunError(11, "fixtures_invalid")
                rows.append({"run_id": row[0], "tick_index": row[1], "price": row[2]})
            return rows
    except OSError:
        raise SmokeRunError(11, "fixtures_invalid") from None


def _validate_constraints(
    input_payload: SmokeRunInput,
    config_payload: SmokeRunConfig,
    expected_rows: list[dict[str, str]],
) -> None:
    if input_payload.ticks < 1:
        raise SmokeRunError(12, "constraints_failed")
    if len(expected_rows) != input_payload.ticks:
        raise SmokeRunError(12, "constraints_failed")

    for index, row in enumerate(expected_rows):
        if row["run_id"] != input_payload.run_id:
            raise SmokeRunError(12, "constraints_failed")
        try:
            tick_index = int(row["tick_index"])
        except ValueError:
            raise SmokeRunError(12, "constraints_failed") from None
        if tick_index != index:
            raise SmokeRunError(12, "constraints_failed")

        price = _parse_decimal(row["price"])
        if price is None:
            raise SmokeRunError(12, "constraints_failed")
        if _decimal_places(price) > config_payload.precision:
            raise SmokeRunError(12, "constraints_failed")


def _parse_decimal(raw: str) -> Decimal | None:
    try:
        value = Decimal(raw)
    except (InvalidOperation, ValueError):
        return None
    if value.is_nan() or value.is_infinite():
        return None
    return value


def _decimal_places(value: Decimal) -> int:
    exponent = value.as_tuple().exponent
    if exponent >= 0:
        return 0
    return -exponent


def _read_json(path: Path) -> Any:
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, json.JSONDecodeError):
        raise SmokeRunError(11, "fixtures_invalid") from None


def _read_simple_yaml_mapping(path: Path) -> dict[str, Any]:
    try:
        content = path.read_text(encoding="utf-8")
    except OSError:
        raise SmokeRunError(11, "fixtures_invalid") from None

    mapping: dict[str, Any] = {}
    for line in content.splitlines():
        if not line.strip():
            continue
        if ":" not in line:
            raise SmokeRunError(11, "fixtures_invalid")
        key, value = line.split(":", 1)
        key = key.strip()
        if not key:
            raise SmokeRunError(11, "fixtures_invalid")
        value = value.strip()
        if value == "":
            mapping[key] = None
        else:
            if value.isdigit():
                mapping[key] = int(value)
            else:
                mapping[key] = value
    return mapping


def _ensure_mapping(payload: Any) -> None:
    if not isinstance(payload, dict):
        raise SmokeRunError(11, "fixtures_invalid")


def _write_result(artifacts_dir: Path, result_bytes: bytes) -> None:
    try:
        artifacts_dir.mkdir(parents=True, exist_ok=True)
    except OSError:
        raise SmokeRunError(13, "output_mismatch") from None

    result_path = artifacts_dir / "result.json"
    if result_path.exists():
        try:
            existing = result_path.read_bytes()
        except OSError:
            raise SmokeRunError(13, "output_mismatch") from None
        if existing != result_bytes:
            raise SmokeRunError(13, "output_mismatch")

    try:
        result_path.write_bytes(result_bytes)
    except OSError:
        raise SmokeRunError(13, "output_mismatch") from None


def _emit_stdout() -> None:
    lines = [
        "SMOKE_RUN:START",
        "SMOKE_RUN:FIXTURES_OK",
        "SMOKE_RUN:CHECKS_OK",
        "SMOKE_RUN:END",
    ]
    for line in lines:
        print(line)

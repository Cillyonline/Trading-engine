"""Evaluate CLI execution helpers."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, Mapping

from cilly_trading.engine.determinism_guard import (
    DeterminismViolationError,
    install_guard,
    uninstall_guard,
)
from cilly_trading.metrics import compute_metrics, write_metrics_artifact


class EvaluateInputError(ValueError):
    """Raised when evaluate input cannot be loaded or validated."""


def _parse_constant(_value: str) -> Any:
    raise ValueError("invalid constant")


def _load_artifact(path: Path) -> Mapping[str, Any]:
    try:
        payload = json.loads(
            path.read_text(encoding="utf-8"),
            parse_constant=_parse_constant,
        )
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise EvaluateInputError("Invalid artifact input") from exc

    if not isinstance(payload, Mapping):
        raise EvaluateInputError("Invalid artifact input")

    summary = payload.get("summary")
    equity_curve = payload.get("equity_curve")
    trades = payload.get("trades")

    if summary is not None and not isinstance(summary, Mapping):
        raise EvaluateInputError("Invalid artifact input")
    if equity_curve is not None and not isinstance(equity_curve, list):
        raise EvaluateInputError("Invalid artifact input")
    if trades is not None and not isinstance(trades, list):
        raise EvaluateInputError("Invalid artifact input")

    return payload


def run_evaluate(*, artifact_path: Path, out_dir: Path) -> int:
    """Run deterministic metrics evaluation command and return deterministic exit code."""

    install_guard()
    try:
        payload = _load_artifact(artifact_path)
        metrics = compute_metrics(payload)
        output_path = write_metrics_artifact(metrics, out_dir)
        print(f"WROTE {output_path}")
        return 0
    except DeterminismViolationError as exc:
        print(str(exc), file=sys.stderr)
        return 10
    except EvaluateInputError as exc:
        print(str(exc), file=sys.stderr)
        return 20
    except Exception as exc:  # pragma: no cover - fallback protection
        print(f"Unexpected error: {exc}", file=sys.stderr)
        return 1
    finally:
        uninstall_guard()

"""Deterministic offline analysis entry-run for fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any, Dict, List

from cilly_trading.engine.core import EngineConfig, compute_analysis_run_id, run_watchlist_analysis
from cilly_trading.engine.data import ingest_local_snapshot_deterministic
from cilly_trading.engine.deterministic_guard import determinism_guard
from cilly_trading.repositories.signals_sqlite import SqliteSignalRepository
from cilly_trading.strategies.rsi2 import Rsi2Strategy

DEFAULT_FIXTURES_DIR = Path("fixtures/deterministic-analysis")
DEFAULT_OUTPUT_PATH = Path("tests/output/deterministic-analysis.json")


class DeterministicRunConfigError(ValueError):
    """Raised when the deterministic run configuration is invalid."""


def _load_run_config(fixtures_dir: Path) -> Dict[str, Any]:
    config_path = fixtures_dir / "analysis_config.json"
    if not config_path.exists():
        raise DeterministicRunConfigError("deterministic_config_missing")
    payload = json.loads(config_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise DeterministicRunConfigError("deterministic_config_invalid")
    return payload


def _resolve_strategy(name: str):
    if name.upper() == "RSI2":
        return Rsi2Strategy()
    raise DeterministicRunConfigError(f"deterministic_strategy_unknown:{name}")


def _build_output_payload(
    *,
    config: Dict[str, Any],
    ingestion_run_id: str,
    snapshot_id: str,
    analysis_run_id: str,
    signals: List[Dict[str, Any]],
) -> Dict[str, Any]:
    sorted_signals = sorted(signals, key=lambda s: s.get("signal_id", ""))
    return {
        "analysis_run_id": analysis_run_id,
        "ingestion_run_id": ingestion_run_id,
        "snapshot_id": snapshot_id,
        "symbols": sorted(config["symbols"]),
        "strategies": sorted(config["strategies"]),
        "engine_config": config["engine_config"],
        "signals": sorted_signals,
    }


def run_deterministic_analysis(
    *,
    fixtures_dir: Path = DEFAULT_FIXTURES_DIR,
    output_path: Path = DEFAULT_OUTPUT_PATH,
    db_path: Path | None = None,
) -> Path:
    """Run the deterministic offline analysis against fixture data.

    Args:
        fixtures_dir: Directory containing the deterministic fixtures.
        output_path: Path to write the deterministic output artifact.
        db_path: Optional SQLite DB path for the run.

    Returns:
        Path to the output artifact.
    """
    with determinism_guard():
        fixtures_dir = Path(fixtures_dir)
        config = _load_run_config(fixtures_dir)

        symbols = config.get("symbols")
        strategies = config.get("strategies")
        if not isinstance(symbols, list) or not symbols:
            raise DeterministicRunConfigError("deterministic_symbols_invalid")
        if not isinstance(strategies, list) or not strategies:
            raise DeterministicRunConfigError("deterministic_strategies_invalid")

        engine_config_payload = config.get("engine_config", {})
        engine_config = EngineConfig(
            timeframe=engine_config_payload.get("timeframe", "D1"),
            lookback_days=int(engine_config_payload.get("lookback_days", 200)),
            market_type=engine_config_payload.get("market_type", "stock"),
            data_source=engine_config_payload.get("data_source", "yahoo"),
            external_data_enabled=False,
        )

        snapshot_config = config.get("snapshot", {})
        snapshot_file = snapshot_config.get("file")
        ingestion_run_id = snapshot_config.get("ingestion_run_id")
        created_at = snapshot_config.get("created_at")
        source = snapshot_config.get("source", "fixture")
        if not snapshot_file or not ingestion_run_id or not created_at:
            raise DeterministicRunConfigError("deterministic_snapshot_config_invalid")

        if db_path is None:
            db_path = output_path.with_suffix(".db")

        ingestion_result = ingest_local_snapshot_deterministic(
            input_path=fixtures_dir / snapshot_file,
            symbol=symbols[0],
            timeframe=engine_config.timeframe,
            source=source,
            ingestion_run_id=ingestion_run_id,
            created_at=created_at,
            db_path=db_path,
        )

        strategy_instances = [_resolve_strategy(name) for name in strategies]
        strategy_configs = config.get("strategy_configs", {})
        signal_repo = SqliteSignalRepository(db_path=db_path)

        signals = run_watchlist_analysis(
            symbols=symbols,
            strategies=strategy_instances,
            engine_config=engine_config,
            strategy_configs=strategy_configs,
            signal_repo=signal_repo,
            ingestion_run_id=ingestion_result.ingestion_run_id,
            snapshot_id=ingestion_result.snapshot_id,
            db_path=db_path,
        )

        run_request_payload = {
            "symbols": sorted(symbols),
            "strategies": sorted(strategies),
            "engine_config": {
                "timeframe": engine_config.timeframe,
                "lookback_days": engine_config.lookback_days,
                "market_type": engine_config.market_type,
                "data_source": engine_config.data_source,
            },
            "ingestion_run_id": ingestion_result.ingestion_run_id,
            "snapshot_id": ingestion_result.snapshot_id,
            "snapshot_only": False,
        }
        analysis_run_id = compute_analysis_run_id(run_request_payload)
        output_payload = _build_output_payload(
            config=config,
            ingestion_run_id=ingestion_result.ingestion_run_id,
            snapshot_id=ingestion_result.snapshot_id,
            analysis_run_id=analysis_run_id,
            signals=signals,
        )

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(
                output_payload,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ),
            encoding="utf-8",
        )

    return output_path


def main() -> int:
    parser = argparse.ArgumentParser(description="Deterministic offline analysis run.")
    parser.add_argument(
        "--fixtures-dir",
        default=str(DEFAULT_FIXTURES_DIR),
        help="Path to deterministic fixtures directory.",
    )
    parser.add_argument(
        "--output",
        default=str(DEFAULT_OUTPUT_PATH),
        help="Output JSON path for deterministic results.",
    )
    parser.add_argument(
        "--db-path",
        default=None,
        help="Optional SQLite DB path for the deterministic run.",
    )
    args = parser.parse_args()

    output_path = run_deterministic_analysis(
        fixtures_dir=Path(args.fixtures_dir),
        output_path=Path(args.output),
        db_path=Path(args.db_path) if args.db_path else None,
    )
    print(output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

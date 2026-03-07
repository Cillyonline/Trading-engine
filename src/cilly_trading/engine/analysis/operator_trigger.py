from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


def trigger_operator_analysis_run(
    *,
    execute: Callable[..., list[dict[str, Any]]],
    symbol: str,
    strategy: str,
    ingestion_run_id: str,
    execute_kwargs: dict[str, Any],
) -> list[dict[str, Any]]:
    logger.info(
        "Operator analysis run requested: component=control_plane symbol=%s strategy=%s ingestion_run_id=%s",
        symbol,
        strategy,
        ingestion_run_id,
    )
    try:
        signals = execute(**execute_kwargs)
    except Exception:
        logger.exception(
            "Operator analysis run failed: component=control_plane symbol=%s strategy=%s ingestion_run_id=%s",
            symbol,
            strategy,
            ingestion_run_id,
        )
        raise

    logger.info(
        "Operator analysis run completed: component=control_plane symbol=%s strategy=%s ingestion_run_id=%s signals=%d",
        symbol,
        strategy,
        ingestion_run_id,
        len(signals),
    )
    return signals

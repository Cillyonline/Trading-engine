"""Minimal deterministic reference strategy."""

from __future__ import annotations

from typing import Any, Dict, List

import pandas as pd

from cilly_trading.engine.core import BaseStrategy
from cilly_trading.models import Signal


class ReferenceStrategy(BaseStrategy):
    """Reference strategy that intentionally emits no signals."""

    name: str = "REFERENCE"

    def generate_signals(
        self,
        df: pd.DataFrame,
        config: Dict[str, Any],
    ) -> List[Signal]:
        _ = df
        _ = config
        return []

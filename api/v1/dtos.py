"""Pydantic DTOs for the stable v1 Signals API."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, ConfigDict


class SignalV1ItemDTO(BaseModel):
    signal_id: str
    run_id: Optional[str]
    asset: str
    strategy: str
    signal_time: datetime
    direction: str
    confidence: Optional[float] = None
    metadata: Optional[Dict[str, Any]] = None

    model_config = ConfigDict(extra="forbid")


class SignalV1ResponseDTO(BaseModel):
    items: List[SignalV1ItemDTO]
    next_cursor: Optional[str] = None
    count: int

    model_config = ConfigDict(extra="forbid")

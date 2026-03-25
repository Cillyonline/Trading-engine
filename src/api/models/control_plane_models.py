from __future__ import annotations

from typing import List, Literal

from pydantic import BaseModel, ConfigDict, Field


class RuntimeIntrospectionTimestampsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    started_at: str
    updated_at: str


class RuntimeIntrospectionOwnershipResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    owner_tag: str


class RuntimeIntrospectionExtensionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: str
    point: Literal["status", "health", "introspection"]
    enabled: bool
    source: Literal["core", "extension"]


class RuntimeIntrospectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    runtime_id: str
    mode: str
    timestamps: RuntimeIntrospectionTimestampsResponse
    ownership: RuntimeIntrospectionOwnershipResponse
    extensions: List[RuntimeIntrospectionExtensionResponse] = Field(default_factory=list)


class GuardStatusDecisionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    enabled: bool
    blocking: bool
    decision: Literal["allowing", "blocking"]


class DrawdownGuardStatusResponse(GuardStatusDecisionResponse):
    model_config = ConfigDict(extra="forbid")

    threshold_pct: float | None
    current_drawdown_pct: float


class DailyLossGuardStatusResponse(GuardStatusDecisionResponse):
    model_config = ConfigDict(extra="forbid")

    max_daily_loss_abs: float | None
    current_daily_loss_abs: float


class KillSwitchStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    active: bool
    blocking: bool
    decision: Literal["allowing", "blocking"]


class GuardStatusCollectionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    drawdown_guard: DrawdownGuardStatusResponse
    daily_loss_guard: DailyLossGuardStatusResponse
    kill_switch: KillSwitchStatusResponse


class ComplianceStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    blocking: bool
    decision: Literal["allowing", "blocking"]


class ComplianceGuardStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    compliance: ComplianceStatusResponse
    guards: GuardStatusCollectionResponse


class SystemStateMetadataResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    read_only: Literal[True]
    source: str


class SystemStateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    schema_version: str
    status: str
    runtime: RuntimeIntrospectionResponse
    metadata: SystemStateMetadataResponse


class ExecutionControlResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: str

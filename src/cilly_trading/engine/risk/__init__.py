"""Risk gate utilities for execution boundary enforcement."""

from .authority import (
    APPROVED_RISK_FRAMEWORK_REASON_CODE,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC,
    BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID,
)
from .gate import (
    RISK_FRAMEWORK_REASON_CODES,
    RiskApprovalMissingError,
    RiskEvidenceDisciplineError,
    RiskRejectedError,
    ThresholdRiskGate,
    adapt_risk_framework_response_to_risk_decision,
    build_guard_trigger_telemetry_event,
    build_guard_trigger_telemetry_events,
    enforce_approved_risk_decision,
    evaluate_risk_framework_execution_decision,
    resolve_runtime_guard_type,
)

__all__ = [
    "APPROVED_RISK_FRAMEWORK_REASON_CODE",
    "BOUNDED_RISK_FRAMEWORK_AUTHORITY_CONTRACT_DOC",
    "BOUNDED_RISK_FRAMEWORK_AUTHORITY_ID",
    "RISK_FRAMEWORK_REASON_CODES",
    "RiskApprovalMissingError",
    "RiskEvidenceDisciplineError",
    "RiskRejectedError",
    "ThresholdRiskGate",
    "adapt_risk_framework_response_to_risk_decision",
    "build_guard_trigger_telemetry_event",
    "build_guard_trigger_telemetry_events",
    "enforce_approved_risk_decision",
    "evaluate_risk_framework_execution_decision",
    "resolve_runtime_guard_type",
]

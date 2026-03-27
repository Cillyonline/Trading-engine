"""Canonical Phase 42b handoff contract for downstream Phase 43/44 usage."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable, Mapping


HANDOFF_CONTRACT_VERSION = "1.0.0"

PHASE_43_REQUIRED_FIELDS: tuple[str, ...] = (
    "artifact_version",
    "run.run_id",
    "run.deterministic",
    "snapshot_linkage.mode",
    "snapshot_linkage.start",
    "snapshot_linkage.end",
    "snapshot_linkage.count",
    "strategy.name",
    "strategy.params",
    "run_config.contract_version",
    "run_config.execution_assumptions",
    "run_config.reproducibility_metadata",
    "summary.start_equity",
    "summary.end_equity",
    "equity_curve",
    "metrics_baseline.assumptions",
    "metrics_baseline.summary",
    "metrics_baseline.metrics.cost_aware",
)

PHASE_44_REQUIRED_FIELDS: tuple[str, ...] = (
    "orders",
    "fills",
    "positions",
    "metrics_baseline.trades",
)

TRADER_AUTHORITATIVE_FIELDS: tuple[str, ...] = (
    "run.run_id",
    "snapshot_linkage",
    "strategy",
    "run_config.execution_assumptions",
    "metrics_baseline.summary",
    "metrics_baseline.metrics.cost_aware",
    "metrics_baseline.metrics.deltas",
)


@dataclass(frozen=True)
class GateStatus:
    """Deterministic gate status for one downstream phase boundary."""

    passed: bool
    missing_fields: tuple[str, ...]
    reasons: tuple[str, ...]

    def to_payload(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "missing_fields": list(self.missing_fields),
            "reasons": list(self.reasons),
        }


def build_phase_handoff_contract(payload: Mapping[str, Any]) -> dict[str, Any]:
    """Build canonical handoff evidence contract for Phase 42b outputs."""

    assumptions_aligned = _assumptions_aligned(payload)
    technical_gate = _technical_gate(payload)
    phase_43_gate = _phase_43_gate(payload, assumptions_aligned=assumptions_aligned)
    phase_44_gate = _phase_44_gate(payload, phase_43_gate=phase_43_gate)

    return {
        "contract_version": HANDOFF_CONTRACT_VERSION,
        "source_phase": "42b",
        "target_phases": ["43", "44"],
        "required_evidence": {
            "phase_43_portfolio_simulation": list(PHASE_43_REQUIRED_FIELDS),
            "phase_44_paper_trading_readiness": list(PHASE_44_REQUIRED_FIELDS),
        },
        "authoritative_outputs": {
            "trader_interpretation": list(TRADER_AUTHORITATIVE_FIELDS),
        },
        "assumption_alignment": {
            "run_config_execution_assumptions_match_metrics_baseline_assumptions": assumptions_aligned,
        },
        "acceptance_gates": {
            "technically_valid_backtest_artifact": technical_gate.to_payload(),
            "phase_43_portfolio_simulation_ready": phase_43_gate.to_payload(),
            "phase_44_paper_trading_readiness_evidence_ready": phase_44_gate.to_payload(),
        },
    }


def _phase_43_gate(payload: Mapping[str, Any], *, assumptions_aligned: bool) -> GateStatus:
    missing_fields = _missing_fields(payload, PHASE_43_REQUIRED_FIELDS)
    reasons: list[str] = []
    if missing_fields:
        reasons.append("missing_phase_43_required_fields")
    if not assumptions_aligned:
        reasons.append("run_config_and_metrics_baseline_assumptions_mismatch")
    return GateStatus(
        passed=(not missing_fields and assumptions_aligned),
        missing_fields=missing_fields,
        reasons=tuple(reasons),
    )


def _phase_44_gate(payload: Mapping[str, Any], *, phase_43_gate: GateStatus) -> GateStatus:
    missing_fields = _missing_fields(payload, PHASE_44_REQUIRED_FIELDS)
    reasons: list[str] = []
    if not phase_43_gate.passed:
        reasons.append("phase_43_gate_not_passed")
    if missing_fields:
        reasons.append("missing_phase_44_required_fields")
    return GateStatus(
        passed=(phase_43_gate.passed and not missing_fields),
        missing_fields=missing_fields,
        reasons=tuple(reasons),
    )


def _technical_gate(payload: Mapping[str, Any]) -> GateStatus:
    required_fields = (
        "artifact_version",
        "run.run_id",
        "run.deterministic",
        "snapshot_linkage",
        "strategy",
        "summary",
        "equity_curve",
    )
    missing_fields = _missing_fields(payload, required_fields)
    deterministic_flag = _get_path(payload, "run.deterministic")
    reasons: list[str] = []
    if missing_fields:
        reasons.append("missing_backtest_artifact_fields")
    if deterministic_flag is not True:
        reasons.append("run_not_marked_deterministic")
    return GateStatus(
        passed=(not missing_fields and deterministic_flag is True),
        missing_fields=missing_fields,
        reasons=tuple(reasons),
    )


def _assumptions_aligned(payload: Mapping[str, Any]) -> bool:
    run_assumptions = _get_path(payload, "run_config.execution_assumptions")
    baseline_assumptions = _get_path(payload, "metrics_baseline.assumptions")
    if not isinstance(run_assumptions, Mapping) or not isinstance(baseline_assumptions, Mapping):
        return False
    return dict(run_assumptions) == dict(baseline_assumptions)


def _missing_fields(payload: Mapping[str, Any], paths: Iterable[str]) -> tuple[str, ...]:
    missing: list[str] = []
    for path in paths:
        value = _get_path(payload, path)
        if value is _MISSING:
            missing.append(path)
    return tuple(missing)


_MISSING = object()


def _get_path(payload: Mapping[str, Any], path: str) -> Any:
    current: Any = payload
    for token in path.split("."):
        if not isinstance(current, Mapping) or token not in current:
            return _MISSING
        current = current[token]
    return current

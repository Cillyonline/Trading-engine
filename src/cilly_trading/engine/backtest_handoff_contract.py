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

PORTFOLIO_TO_PAPER_REQUIRED_INPUTS: tuple[str, ...] = (
    *PHASE_43_REQUIRED_FIELDS,
    *PHASE_44_REQUIRED_FIELDS,
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

ARTIFACT_LINEAGE_REQUIRED_FIELDS: tuple[str, ...] = (
    "run.run_id",
    "snapshot_linkage.mode",
    "snapshot_linkage.start",
    "snapshot_linkage.end",
    "snapshot_linkage.count",
    "strategy.name",
    "strategy.params",
    "run_config.contract_version",
    "run_config.execution_assumptions",
    "run_config.reproducibility_metadata",
)

BACKTEST_TO_PORTFOLIO_UNSUPPORTED_CLAIMS: tuple[str, ...] = (
    "portfolio-readiness inferred from technical artifact validity alone",
    "paper-readiness inferred without a passed portfolio boundary",
    "live-trading readiness or approval",
    "broker execution readiness or approval",
    "guaranteed or certain outcome claims",
)

PORTFOLIO_TO_PAPER_UNSUPPORTED_CLAIMS: tuple[str, ...] = (
    "paper-readiness inferred from vague or implicit portfolio evidence",
    "live-trading readiness or approval",
    "production readiness or approval",
    "broker execution readiness or approval",
    "trader-validation or guaranteed outcome claims",
)

BACKTEST_TO_PORTFOLIO_READINESS_BOUNDARY = (
    "Portfolio simulation may consume only explicit backtest evidence inputs and artifact lineage "
    "carried by this contract."
)

PORTFOLIO_TO_PAPER_READINESS_BOUNDARY = (
    "Paper readiness may consume only explicit portfolio-ready evidence and canonical execution "
    "artifacts carried by this contract."
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
    artifact_lineage = _artifact_lineage_status(payload)

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
        "artifact_lineage": artifact_lineage,
        "canonical_handoffs": {
            "backtest_to_portfolio": _handoff_contract_payload(
                handoff_id="phase_42b_backtest_to_phase_43_portfolio",
                producer_phase="42b",
                consumer_phase="43",
                readiness_gate="phase_43_portfolio_simulation_ready",
                prerequisite_gates=("technically_valid_backtest_artifact",),
                required_inputs=PHASE_43_REQUIRED_FIELDS,
                artifact_lineage=artifact_lineage,
                readiness_boundary=BACKTEST_TO_PORTFOLIO_READINESS_BOUNDARY,
                unsupported_claims=BACKTEST_TO_PORTFOLIO_UNSUPPORTED_CLAIMS,
                gate_status=phase_43_gate,
            ),
            "portfolio_to_paper": _handoff_contract_payload(
                handoff_id="phase_43_portfolio_to_phase_44_paper",
                producer_phase="43",
                consumer_phase="44",
                readiness_gate="phase_44_paper_trading_readiness_evidence_ready",
                prerequisite_gates=("phase_43_portfolio_simulation_ready",),
                required_inputs=PORTFOLIO_TO_PAPER_REQUIRED_INPUTS,
                artifact_lineage=artifact_lineage,
                readiness_boundary=PORTFOLIO_TO_PAPER_READINESS_BOUNDARY,
                unsupported_claims=PORTFOLIO_TO_PAPER_UNSUPPORTED_CLAIMS,
                gate_status=phase_44_gate,
            ),
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
        reasons.append("portfolio_simulation_requires_explicit_backtest_evidence")
    if not assumptions_aligned:
        reasons.append("run_config_and_metrics_baseline_assumptions_mismatch")
        reasons.append("portfolio_simulation_requires_aligned_execution_assumptions")
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
        reasons.append("paper_readiness_requires_portfolio_ready_evidence")
    if missing_fields:
        reasons.append("missing_phase_44_required_fields")
        reasons.append("paper_readiness_requires_canonical_execution_evidence")
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


def _artifact_lineage_status(payload: Mapping[str, Any]) -> dict[str, Any]:
    missing_fields = _missing_fields(payload, ARTIFACT_LINEAGE_REQUIRED_FIELDS)
    return {
        "complete": not missing_fields,
        "required_fields": list(ARTIFACT_LINEAGE_REQUIRED_FIELDS),
        "missing_fields": list(missing_fields),
    }


def _handoff_contract_payload(
    *,
    handoff_id: str,
    producer_phase: str,
    consumer_phase: str,
    readiness_gate: str,
    prerequisite_gates: tuple[str, ...],
    required_inputs: tuple[str, ...],
    artifact_lineage: Mapping[str, Any],
    readiness_boundary: str,
    unsupported_claims: tuple[str, ...],
    gate_status: GateStatus,
) -> dict[str, Any]:
    return {
        "handoff_id": handoff_id,
        "producer_phase": producer_phase,
        "consumer_phase": consumer_phase,
        "readiness_gate": readiness_gate,
        "prerequisite_gates": list(prerequisite_gates),
        "required_inputs": list(required_inputs),
        "artifact_lineage_complete": artifact_lineage["complete"],
        "artifact_lineage_required_fields": list(artifact_lineage["required_fields"]),
        "artifact_lineage_missing_fields": list(artifact_lineage["missing_fields"]),
        "readiness_boundary": readiness_boundary,
        "unsupported_claims": list(unsupported_claims),
        "gate_status": gate_status.to_payload(),
    }


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

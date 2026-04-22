# Decision Review API

This document defines the canonical bounded read-only decision-review surface for operator and research review workflows.

## Read-Only Endpoint

All access requires `X-Cilly-Role: read_only` (or a higher role).

- Canonical surface: `GET /decision-review`
- Backward-compatible covered surface: `GET /decision-cards`

No mutation endpoints are introduced by this surface.

## Purpose

The canonical endpoint exposes deterministic decision-card outcomes and explanations so reviewers can inspect why a candidate was blocked, approved, or kept in ranked review flow without cross-surface reconstruction.

Claim boundary discipline for this surface:

- confidence language is evidence-aligned only; confidence text must reference bounded aggregate/component/threshold evidence semantics
- confidence is explicitly bounded by upstream evidence quality (signal, backtest, portfolio-fit, risk); limited upstream evidence limits the achievable confidence tier
- qualification and rationale language is bounded to paper-trading qualification scope
- qualification state is contract-bounded (`reject` | `watch` | `paper_candidate` | `paper_approved`) and deterministic from hard-gate + score semantics
- inspection outputs must not imply live-trading approval, broker readiness, production readiness, trader validation, or guaranteed outcomes
- non-inference and claim-boundary evaluation is enforced from canonical structured boundary fields first, with wording fallback only for compatibility when structured fields are unavailable

Structured non-inference boundary fields contract for decision/inspection payloads:

- `contract_id`: `bounded_non_inference_boundary_fields.read_only.v1`
- `contract_version`: `1.0.0`
- `evaluation_mode`: `structured_primary_with_wording_fallback`
- canonical fields: `qualification_state`, `paper_scope_summary`, `state_explanation_evidence`, `action`, `bounded_decision_metrics`, `action_rule_trace`, `trader_validation_boundary`, `paper_profitability_boundary`, `live_readiness_boundary`
- `overall_status`: deterministic (`aligned` | `weak` | `missing`)
- `failure_reasons`: explicit deterministic boundary-failure reasons

## Deterministic Ordering

Default ordering is deterministic:

- `generated_at_utc DESC`
- tie-breaker: `decision_card_id ASC`
- tie-breaker: `run_id ASC`
- tie-breaker: `artifact_name ASC`

Optional `sort=generated_at_asc` reverses only the primary timestamp direction while preserving deterministic tie-breakers.

## Filtering

Supported query filters:

- `run_id`
- `symbol`
- `strategy_id`
- `decision_card_id`
- `qualification_state` (`reject`, `watch`, `paper_candidate`, `paper_approved`)
- `review_state`:
  - `blocked` -> `qualification_state=reject`
  - `approved` -> `qualification_state=paper_approved`
  - `ranked` -> non-reject outcomes (`watch`, `paper_candidate`, `paper_approved`)

Pagination:

- `limit` (`1..500`, default `50`)
- `offset` (`>=0`, default `0`)

## Response Contract

```json
{
  "workflow_id": "ui_decision_review_surface_v1",
  "boundary": {
    "mode": "non_live_decision_review_surface",
    "technical_decision_review_statement": "This canonical decision-review surface consolidates bounded decision-card evidence for deterministic operator and analyst inspection.",
    "trader_validation_statement": "Decision-review evidence is technical read-only evidence and is not trader validation.",
    "operational_readiness_statement": "Decision-review evidence does not establish operational readiness, live trading readiness, or broker execution readiness.",
    "non_inference_boundary_contract": {
      "contract_id": "bounded_non_inference_boundary_fields.read_only.v1",
      "contract_version": "1.0.0",
      "evaluation_mode": "structured_primary_with_wording_fallback"
    },
    "strategy_readiness_evidence": {
      "inferred_readiness_claim": "prohibited"
    },
    "legacy_surface_mappings": [
      {
        "surface": "/decision-cards",
        "mapping": "Deterministic 1:1 item evidence mapping for qualification_state, action, win_rate, expected_value, and non_inference_boundary."
      },
      {
        "surface": "/signals/decision-surface",
        "mapping": "Canonical decision-card evidence fields (qualification_state, action, win_rate, expected_value) remain explicitly aligned for backward-compatible consumer mapping."
      }
    ],
    "in_scope": [],
    "out_of_scope": []
  },
  "items": [
    {
      "run_id": "run-a",
      "artifact_name": "decision_card.json",
      "decision_card_id": "dc-001",
      "generated_at_utc": "2026-03-24T08:00:00Z",
      "symbol": "AAPL",
      "strategy_id": "RSI2",
      "qualification_state": "paper_approved",
      "action": "entry",
      "win_rate": 0.864,
      "expected_value": 1.0,
      "qualification_color": "green",
      "qualification_summary": "Opportunity is approved for bounded paper-trading only.",
      "aggregate_score": 84.15,
      "confidence_tier": "high",
      "hard_gate_policy_version": "hard-gates.v1",
      "hard_gate_blocking_failure": false,
      "hard_gates": [],
      "component_scores": [],
      "rationale_summary": "Qualification is resolved from explicit hard gates, bounded scores, and confidence rules.",
      "gate_explanations": [],
      "score_explanations": [],
      "final_explanation": "Action state is deterministic and does not imply live-trading approval.",
      "metadata": {},
      "non_inference_boundary": {
        "contract_id": "bounded_non_inference_boundary_fields.read_only.v1",
        "contract_version": "1.0.0",
        "evaluation_mode": "structured_primary_with_wording_fallback",
        "overall_status": "aligned",
        "qualification_state": {"present": true, "source": "structured_fields", "failure_reason": null},
        "paper_scope_summary": {"present": true, "source": "structured_fields", "failure_reason": null},
        "state_explanation_evidence": {"present": true, "source": "structured_fields", "failure_reason": null},
        "action": {"present": true, "source": "structured_fields", "failure_reason": null},
        "bounded_decision_metrics": {"present": true, "source": "structured_fields", "failure_reason": null},
        "action_rule_trace": {"present": true, "source": "structured_fields", "failure_reason": null},
        "trader_validation_boundary": {"present": true, "source": "structured_fields", "failure_reason": null},
        "paper_profitability_boundary": {"present": true, "source": "structured_fields", "failure_reason": null},
        "live_readiness_boundary": {"present": true, "source": "structured_fields", "failure_reason": null},
        "failure_reasons": []
      }
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

## Legacy Surface Mapping

- `/decision-cards` remains available and backward-compatible.
- `/signals/decision-surface` remains available and keeps explicit parity for canonical decision-card evidence fields:
  - `qualification_state`
  - `action`
  - `win_rate`
  - `expected_value`

## Explanation Fields for Operator Review

The inspection payload explicitly includes:

- canonical bounded action evidence (`qualification_state`, `action`, `win_rate`, `expected_value`)
- hard-gate evaluations (`hard_gates`)
- component-level score rationales (`component_scores`)
- gate and score explanation lists (`gate_explanations`, `score_explanations`)
- final qualification explanation (`final_explanation`)
- structured non-inference boundary evaluation with explicit per-field status and deterministic failure reasons (`non_inference_boundary`)

This keeps decision outputs explainable without introducing mutation or live-trading controls.

The runtime contract validation for decision cards enforces structured boundary semantics first and keeps wording checks as bounded compatibility fallback while continuing to reject unsupported confidence inflation language.

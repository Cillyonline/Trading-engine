# Decision Card Inspection API

This document defines the bounded read-only inspection surface for decision-card outputs used by operator and research review workflows.

## Read-Only Endpoint

All access requires `X-Cilly-Role: read_only` (or a higher role).

- `GET /decision-cards`

No mutation endpoints are introduced by this surface.

## Purpose

The endpoint exposes decision-card outcomes and their explanations so reviewers can inspect why a candidate was blocked, approved, or kept in ranked review flow.

Claim boundary discipline for this surface:

- confidence language is evidence-aligned only; confidence text must reference bounded aggregate/component/threshold evidence semantics
- confidence is explicitly bounded by upstream evidence quality (signal, backtest, portfolio-fit, risk); limited upstream evidence limits the achievable confidence tier
- qualification and rationale language is bounded to paper-trading qualification scope
- qualification state is contract-bounded (`reject` | `watch` | `paper_candidate` | `paper_approved`) and deterministic from hard-gate + score semantics
- inspection outputs must not imply live-trading approval, broker readiness, production readiness, trader validation, or guaranteed outcomes

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
  "items": [
    {
      "run_id": "run-a",
      "artifact_name": "decision_card.json",
      "decision_card_id": "dc-001",
      "generated_at_utc": "2026-03-24T08:00:00Z",
      "symbol": "AAPL",
      "strategy_id": "RSI2",
      "qualification_state": "paper_approved",
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
      "metadata": {}
    }
  ],
  "limit": 50,
  "offset": 0,
  "total": 1
}
```

## Explanation Fields for Operator Review

The inspection payload explicitly includes:

- hard-gate evaluations (`hard_gates`)
- component-level score rationales (`component_scores`)
- gate and score explanation lists (`gate_explanations`, `score_explanations`)
- final qualification explanation (`final_explanation`)

This keeps decision outputs explainable without introducing mutation or live-trading controls.

The runtime contract validation for decision cards enforces this wording boundary and rejects unsupported confidence inflation language.

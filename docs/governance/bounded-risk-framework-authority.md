# Bounded Risk-Framework Authority (Governance Overlay)

## 1. Purpose

This governance overlay closes the bounded risk-framework authority gap by
pointing all risk-governance reading paths to one canonical bounded
risk-framework authority contract.

The canonical bounded risk-framework authority contract lives at:

- `docs/architecture/risk/bounded_risk_framework_authority_contract.md`

This overlay does not redefine bounded risk semantics. It records the
governance-level acknowledgement that:

- the canonical bounded authority id is `risk_framework_bounded_non_live_v1`
- it covers the currently implemented bounded risk primitives only
- it covers bounded stop-loss, position-sizing, trade-risk, strategy-risk,
  symbol-risk, and portfolio-risk evidence for non-live evaluation only
- it preserves explicit non-live, non-broker, no-readiness-overclaim
  boundaries

## 2. Scope

In scope for this overlay:

- governance-level pointer to the canonical bounded risk-framework authority
  contract
- governance-level restatement of bounded non-live wording boundaries
- governance-level alignment with bounded technical risk evidence
- governance-level acknowledgement of deterministic bounded risk-budget
  evidence without live-trading or broker-readiness claims

Out of scope for this overlay:

- new risk models
- threshold retuning
- strategy changes
- execution-policy redesign
- live trading scope
- broker integration
- readiness or profitability claims
- broad UI expansion

## 3. Bounded Wording Boundaries

The bounded risk-framework authority is bounded non-live technical evidence.
It is governed by the following wording boundaries:

- it is not live-trading authorization
- it is not broker-execution authorization
- it is not trader validation
- it is not operational readiness
- it is not production readiness
- it is not a profitability or edge claim

Any risk-governance documentation that consumes this overlay must preserve
these boundaries.

## 4. Cross-References

- `docs/architecture/risk/bounded_risk_framework_authority_contract.md`
  (canonical bounded risk-framework authority contract)
- `docs/architecture/risk/risk_framework.md`
- `docs/architecture/risk/non_live_evaluation_contract.md`
- `docs/architecture/risk/contract.md`
- `docs/governance/qualification-claim-evidence-discipline.md`
- `ROADMAP_MASTER.md` Phase 27 (Risk Framework Governance)

# Qualification Claim Evidence Discipline

## 1. Purpose

This governance contract defines bounded evidence discipline for qualification claims and trader-facing confidence language.
It keeps technical implementation status, trader validation, and operational readiness as separate claim layers.

## 2. Evidence Hierarchy for Qualification Claims

Qualification claims must remain inside this ordered evidence hierarchy:

1. Hard-gate evidence (explicit pass/fail gates with recorded evidence)
2. Bounded component evidence (`signal_quality`, `backtest_quality`, `portfolio_fit`, `risk_alignment`, `execution_readiness`)
3. Bounded aggregate/confidence resolution (`low` | `medium` | `high`)
4. Bounded paper-trading qualification state (`reject` | `watch` | `paper_candidate` | `paper_approved`)

Claiming a higher layer without evidence for lower layers is out of contract.

## 3. Bounded Trader-Facing Confidence Language

Confidence language is evidence-aligned only when it:

- references bounded evidence semantics (aggregate score, component scores, thresholds, explicit evidence)
- remains in paper-trading qualification scope
- avoids certainty or readiness claims outside available evidence

The following claim classes are unsupported in qualification outputs and must be rejected:

- live-trading readiness/approval claims
- production readiness claims
- broker execution readiness claims
- trader-validation claims
- guaranteed/certain outcome claims

## 4. Runtime and Documentation Alignment Rule

Documentation and runtime wording must enforce the same boundary:

- decision-card contract wording and runtime output wording use the same evidence hierarchy
- inspection API wording mirrors the same boundary
- qualification outputs explicitly state they do not imply live-trading approval

## 5. Validation Rule

Where claim-boundary enforcement exists in runtime contracts, validation must fail closed for unsupported claim language.
Validation is required for:

- confidence reason text
- qualification summary text
- rationale summary/final explanation text

## 6. Non-Goals

This governance contract does not grant:

- live trading approval
- broker execution approval
- operational production approval

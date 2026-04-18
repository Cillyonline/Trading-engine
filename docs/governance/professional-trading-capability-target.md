# Professional Trading Capability Target (Canonical)

## Purpose

Define the canonical repository-wide professional-trading capability target for
the current direction ("mehr Trading Profi").

This document is a steering anchor for follow-up issues. It is not a generic
vision statement.

## Authority and Boundaries

- This document defines capability direction and prioritization semantics for
  current repository work.
- It does not redefine phase taxonomy authority from
  `docs/architecture/roadmap/execution_roadmap.md`.
- It does not redefine canonical phase maturity/status authority from
  `ROADMAP_MASTER.md`.
- It does not authorize live trading, broker integration, or production
  readiness claims.

## Canonical Direction Statement

For this repository revision, "mehr Trading Profi" means:

Build and harden bounded, evidence-backed, professional operator capabilities
for deterministic analysis, decision quality, risk-aware paper execution, and
reviewability, while preserving strict non-live governance boundaries.

## Repository-Specific Core Capabilities

1. Professional signal and decision quality
   - Keep signal quality, scoring semantics, and decision-card evidence explicit
     and auditable.
   - Keep qualification claims bounded by evidence discipline, not by marketing
     language.
2. Professional analysis-to-paper workflow reliability
   - Prioritize deterministic, repeatable signal-to-paper runtime workflows over
     scope expansion.
   - Tighten daily operator run discipline for bounded paper operations.
3. Professional risk and guard behavior
   - Strengthen explicit risk/guard decisions in runtime and evidence outputs.
   - Keep risk alignment reviewable across artifacts, APIs, and operator usage.
4. Professional readiness separation
   - Preserve strict separation between technical implementation, trader
     validation, and operational readiness.
   - Prevent inference between readiness classes in docs, APIs, and UI surfaces.
5. Professional product-surface governance
   - Keep `/ui` as the canonical bounded product-surface authority for current
     repository direction.
   - Treat `frontend/` as non-authoritative unless explicitly promoted by
     governance.
6. Professional evidence-first change discipline
   - Prioritize follow-up issues that improve deterministic tests, contracts,
     evidence artifacts, and documentation alignment for bounded capabilities.

## Current Classification

### Weiterhin passend

- Deterministic-first implementation and testing discipline.
- Explicit non-live, non-broker, bounded paper-trading governance.
- `/ui` canonical product-surface authority with non-inference boundaries.
- Separation of technical status, trader validation, and operational readiness.
- Evidence-gated qualification and decision semantics.

### Anpassungsbeduerftig

- Prioritization language that is phase-number-first but capability-second.
- Roadmap/progress wording that can over-index on status labels without direct
  capability steering impact.
- Generic dashboard phrasing not tied to professional operator outcomes and
  bounded evidence semantics.

### Veraltet

- Implicit progression logic that treats old phase advancement as sufficient
  proxy for professional trading capability direction.
- Any wording that equates technical implementation progress with trader-ready
  or operationally ready outcomes.

### Aktuell nicht priorisiert

- Live-trading enablement or approval.
- Broker integration expansion.
- New architecture tracks or subsystem introduction.
- Broad dashboard/product-surface expansion outside bounded operator workflow
  consolidation.
- New roadmap phase creation as a substitute for capability hardening.

## Handling of Older or Competing Steering Logics

- Phase and boundary governance remain valid control surfaces, but they are not
  by themselves the primary target-definition mechanism for current direction.
- When old wording conflicts with this capability target, follow-up issues must
  align wording and scope to this document while preserving canonical roadmap
  and taxonomy authorities.
- Do not continue legacy steering patterns that optimize for phase-label
  movement without clear professional-capability impact.

## Alignment References

- `README.md` (entry-point link surface)
- `docs/index.md` (documentation navigation link surface)
- `ROADMAP_MASTER.md` (canonical phase maturity/status authority)
- `docs/architecture/roadmap/execution_roadmap.md` (authoritative audited
  phase taxonomy)
- `docs/operations/ui/product-surface-authority-contract.md`
- `docs/governance/strategy-readiness-gates.md`
- `docs/governance/qualification-claim-evidence-discipline.md`

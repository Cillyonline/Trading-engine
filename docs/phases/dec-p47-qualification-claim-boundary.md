# DEC-P47 - Qualification Claim Boundary

## Goal

Define bounded evidence discipline for qualification claims and trader-facing confidence language.

## Claim Boundary

Qualification outputs are bounded to paper-trading scope and must not be interpreted as trader validation or operational readiness.

Required evidence order:

1. hard-gate evidence
2. bounded component evidence
3. bounded confidence tier resolution
4. bounded paper-trading qualification state

## Enforcement Surface

- `docs/governance/qualification-claim-evidence-discipline.md` defines governance rules
- `docs/architecture/decision_card_contract.md` defines contract wording requirements
- `docs/api/decision_card_inspection.md` mirrors read-surface wording boundaries
- `src/cilly_trading/engine/decision_card_contract.py` enforces claim-boundary validation

## Out-of-Scope Reminder

This issue does not imply:

- live trading approval
- broker execution approval
- broad runtime/UI redesign

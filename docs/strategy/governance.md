# Strategy Governance Policy

## Scope

This policy defines approval and quality requirements for introducing or modifying strategy packs and strategies in this repository. It applies to all pull requests that add, update, deprecate, or remove strategy-related artifacts under the documentation and strategy-pack governance surface.

## Governance Principles

All strategy changes must adhere to the following principles:

- **Determinism:** Strategy behavior and validation outcomes must be reproducible from the same inputs.
- **Compatibility stability:** Public compatibility expectations must remain stable unless an explicitly governed version change is made.
- **Version governance:** Strategy and pack versioning must follow semantic expectations, including explicit major/minor/patch intent.
- **Explicit registration:** Every new strategy must be explicitly registered in the applicable registry mechanism; implicit discovery is not acceptable.
- **Auditability:** Strategy intent, version history, and approval trail must be reviewable through documented metadata and pull request records.

## Mandatory Review Checklist

A reviewer must verify all of the following before approval:

- Registry registration is present and correct for each new strategy.
- Metadata completeness is satisfied (required identifiers, version, compatibility, and ownership fields).
- Pack model compliance is validated against the documented strategy-pack model.
- Documentation standard compliance is met for strategy and pack documentation.
- Determinism validation confirms the strategy has deterministic behavior constraints.
- Smoke run verification confirms a deterministic smoke run has passed.
- Version bump correctness matches the semantic impact of the proposed change.

## Compatibility Requirements

All strategy submissions must satisfy these compatibility rules:

- An engine compatibility field is required in strategy or pack metadata.
- Breaking changes require a **MAJOR** version bump.
- Backward compatibility must be explicitly evaluated and documented in the pull request.
- No implicit behavior changes are allowed; behavior-impacting changes must be explicit and version-governed.

## Documentation Requirements

Each strategy pack change must include and maintain documentation with at least:

- A README per strategy pack.
- Parameter definitions for all user-configurable or pack-configurable inputs.
- A deterministic behavior statement describing why repeated executions are reproducible.
- A risk disclosure section covering known limitations and operational risks.

## Deterministic Validation Requirements

A strategy is eligible for approval only if deterministic validation confirms:

- No randomness is used in decision logic or output generation.
- No system time dependency affects strategy behavior.
- No network calls are performed by strategy logic during evaluation.
- No environment branching changes behavior across environments.
- A deterministic smoke run must pass.

## Approval Requirements

A pull request introducing or modifying strategies must meet all approval conditions:

- At least one designated maintainer approval is required.
- Explicit PR review is required (approval cannot be inferred from comments or merges alone).
- No self-approval is allowed without a second reviewer.
- The PR must reference the governing Issue ID.
- Required tests must pass before merge.

## Rejection Criteria

A strategy pull request must be rejected if any of the following conditions are present:

- Missing metadata.
- Non-deterministic behavior.
- Incomplete documentation.
- Versioning violations.
- Breaking public contract without a **MAJOR** version bump.

## Non-Goals

This policy intentionally does not define:

- CI enforcement mechanisms.
- Runtime enforcement mechanisms.
- Performance benchmarking requirements.

FILES CHANGED: docs/strategy/governance.md

Acceptance Criteria Mapping:
- File exists → satisfied by this document.
- Review checklist explicitly listed → see ## Mandatory Review Checklist.
- Approval requirement documented → see ## Approval Requirements.
- No runtime changes → documentation-only change.

# Release Governance Contract - Server-Ready Stage

## 1. Purpose and Stage Boundary
This contract defines bounded release governance for the server-ready stage of Cilly Trading Engine operations.

The covered deployment stage is limited to deterministic local operation and staging-first server deployment validation. This contract does not grant production approval and does not declare live-trading readiness.

## 2. Versioning Rules for This Stage
1. Semantic versioning (`MAJOR.MINOR.PATCH`) is the only valid release version format for this stage.
2. Exactly one authoritative engine version exists per release and it applies to API, CLI, and published runtime artifacts used in this stage.
3. Version increments must be classified before tagging using the current repository versioning rules.
4. The authoritative release version is the tagged version, not an untagged branch head.

## 3. Release-Tag Expectations
1. Every stage release must map to exactly one immutable git tag in the format `vX.Y.Z`.
2. The tag must point to one audited release commit that passed the bounded release checklist for this stage.
3. Moving or deleting an existing release tag is forbidden.
4. A rollback or corrective release must use an existing last-known-good tag or a newly created corrective tag; force-retagging is forbidden.

## 4. Feature-Flag Boundaries (Covered Deployment Modes)
Covered deployment modes in this stage:
- deterministic local mode
- staging-first server mode

Feature-flag boundary rules:
1. Flags may only gate behavior that remains inside covered deployment modes.
2. Flags must not be used to enable live order routing, broker connectivity, or any runtime path outside the covered stage boundary.
3. Staging validation flags must fail closed (disabled by default) unless explicitly enabled for bounded validation.
4. A feature flag is not a scope override: enabling a flag cannot promote this stage to production approval.

## 5. Rollback Discipline for Bounded Operational Recovery
1. Rollback starts when a release fails contract checks, health/readiness checks, or bounded staging validation.
2. First response is bounded mitigation: disable only the failing stage-scoped flag when the regression is flag-scoped.
3. If mitigation is insufficient, rollback to a last-known-good release tag.
4. After rollback, run version verification, smoke run, and staging validation checks before resuming staged operation.
5. Record every rollback decision with incident reference, from-tag, to-tag, owner, timestamp, and verification evidence.

## 6. Governance Consistency Rules
1. This contract is normative for server-ready stage release governance wording.
2. Related release and rollback documents must not contradict these boundaries.
3. If any governance wording implies production approval or live-trading readiness, treat it as out-of-scope and non-authoritative for this stage.

## 7. Explicit Non-Goals
This stage contract does not define:
- live trading rollout
- broker integrations
- CI platform redesign
- strategy logic expansion
- UI redesign
- production high-availability approval

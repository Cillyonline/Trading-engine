# CODE-B6 Consolidation Plan

Issue: `#698`  
Date: `2026-03-19`  
Scope: planning only. This document defines the controlled consolidation
sequence for duplicated helper and configuration code paths. It does not
authorize refactors, helper deletion, import rewrites, or runtime behavior
changes in this issue.

## Purpose

The duplication audit in
`docs/architecture/code_b6_duplication_audit.md` and the ownership contracts in
`docs/architecture/shared_utility_ownership.md` and
`docs/architecture/configuration_boundary.md` identify where duplicated helper
and configuration logic exists and who should own it. This document adds the
missing execution plan: the order, issue boundaries, risk controls, and
rollback expectations required to consolidate those paths safely.

The plan is intentionally implementation-ready. Reviewers should be able to use
it to open later issues without re-deciding sequence, blast radius, or safety
rules.

## Planning constraints

- No runtime behavior changes are introduced by issue `#698`.
- No source or test files are modified by issue `#698`.
- Later implementation issues must preserve all current public and internal
  contracts unless a separate issue explicitly changes a contract.
- Later implementation issues must consolidate one duplication family at a
  time.
- Later implementation issues must move consumers to canonical owners before
  deleting duplicate implementations.
- Exact duplicates should be consolidated before near or divergent duplicates
  when that order reduces runtime risk.

## Inputs this plan depends on

This plan assumes the following current-state documents remain authoritative:

- `docs/architecture/code_b6_duplication_audit.md`
- `docs/architecture/shared_utility_ownership.md`
- `docs/architecture/configuration_boundary.md`

If a later source review contradicts one of those documents, the affected issue
must stop and update the documentation first instead of improvising a new
consolidation path in code.

## Consolidation goals

The future implementation sequence must achieve all of the following:

- remove duplicated helper stacks in a controlled order
- consolidate around the canonical owners already documented in `#696` and
  `#697`
- keep each implementation issue small enough for behavior-equivalence review
- minimize runtime risk by starting with exact duplicates and narrow consumer
  sets
- defer broad config-alignment work until lower-risk shared helper foundations
  are stable

## Safety rules for all later implementation issues

Every follow-up implementation issue created from this plan must obey these
rules:

1. One duplication family per issue. Do not combine identity helpers, artifact
   writers, trade helpers, and config consolidation in one code change.
2. Introduce or extract the canonical helper first. Rewire consumers second.
   Delete duplicate implementations only after all targeted consumers are
   proven equivalent.
3. Preserve signatures and payload semantics at the call boundary unless the
   issue explicitly targets boundary cleanup only and proves no caller-visible
   behavior change.
4. Keep domain-specific contracts domain-specific. Shared primitives may move
   first; alert-specific, dataset-specific, or strategy-specific payload rules
   must not be generalized accidentally.
5. If the issue needs unrelated cleanup to proceed, stop and split the issue.
6. If the issue exposes a hidden contract mismatch rather than a true duplicate,
   stop and document the mismatch before continuing.

## Consolidation sequence

The recommended migration order is based on two filters:

- behavior risk: exact duplicates before near or divergent duplicates
- blast radius: narrow utility families before broader config paths

### Stage 0: lock the reference baseline

Definition:

- use the duplication audit and ownership docs as the baseline for later work
- confirm file scope and acceptance criteria for each later issue before code
  changes begin

Why first:

- later issues need a fixed baseline so they do not reinterpret ownership or
  duplicate families during implementation

Runtime risk:

- none; documentation only

### Stage 1: consolidate canonical identity primitives used by `models.py` and `engine/core.py`

Target family:

- exact duplicate canonical normalization helpers
- exact duplicate canonical JSON helpers
- exact duplicate `sha256` helpers
- exact duplicate signal identity payload and signal ID helpers

Source family from audit:

- duplication audit finding 1

Canonical owner:

- shared model / contract boundary as defined in
  `docs/architecture/shared_utility_ownership.md`

Why this is first:

- it is the strongest exact-duplicate family in the audit
- ownership is already explicit
- consolidating primitives early reduces later repeated work in alert and
  artifact issues

Implementation-ready step:

- extract or formalize one canonical helper stack in the shared model boundary
- rewire `src/cilly_trading/engine/core.py` to use the owner implementation
- keep current signal ID field set and canonicalization semantics unchanged
- remove the duplicated engine-local copies only after consumer migration is
  complete

Risk level:

- low to medium

Rollback rule:

- restore the previous engine-local helper definitions and imports if any ID,
  canonical JSON, or hash behavior changes during review

### Stage 2: consolidate exact duplicate trade post-processing helpers

Target family:

- exact duplicate decimal conversion
- exact duplicate rounding helpers
- exact duplicate float conversion
- exact duplicate trade ordering helpers

Source family from audit:

- duplication audit finding 3

Canonical owner:

- shared helper location chosen within the existing trading/reporting boundary,
  consistent with `#696` ownership rules

Why this is second:

- the duplicate set is exact and isolated to two artifact builders
- these helpers are narrower than the broader artifact-writer family
- it reduces later risk for the near-duplicate metrics family in the next stage

Implementation-ready step:

- introduce one shared helper module or helper owner for deterministic trade
  post-processing primitives used by artifact builders
- rewire `src/cilly_trading/equity_curve.py` and
  `src/cilly_trading/performance_report.py`
- delete the duplicate local helpers only after both consumers are migrated

Risk level:

- low

Rollback rule:

- restore local helpers in the affected artifact builders if trade ordering,
  rounding, or numeric conversion output changes

### Stage 3: extend the trade helper consolidation to the near-duplicate metrics path

Target family:

- near-duplicate numeric normalization and trade ordering helpers in
  `risk_adjusted_metrics.py`

Source family from audit:

- duplication audit finding 4

Canonical owner:

- the shared trade-helper owner introduced in Stage 2

Why this follows Stage 2:

- Stage 2 establishes the exact shared baseline first
- `risk_adjusted_metrics.py` diverges slightly and should only be aligned after
  the exact artifact-builder helpers are stable

Implementation-ready step:

- migrate only the identical numeric and ordering primitives to the shared
  helper owner
- keep metrics-specific extraction logic local if it remains contract-specific
- do not combine this stage with metrics math changes

Risk level:

- low to medium

Rollback rule:

- restore metrics-local helper implementations if metric payload extraction or
  ordering semantics drift

### Stage 4: consolidate canonical artifact serialization primitives

Target family:

- near-duplicate canonical JSON bytes helpers
- repeated SHA sidecar writing pattern where behavior is equivalent

Source family from audit:

- duplication audit finding 5

Canonical owner:

- shared canonical serialization and hashing primitives remain model-owned
- file output orchestration remains artifact-module-owned

Why this follows the identity and trade-helper stages:

- it has more consumers and more variation than the earlier exact-duplicate
  families
- it becomes safer once shared serialization and hashing primitives are already
  established

Implementation-ready step:

- separate shared serialization/hash primitives from module-local file writing
- migrate modules that already have matching canonical JSON and sidecar
  semantics first
- keep `metrics/artifact.py` local for any behavior that still differs
- only align the metrics path in a separate follow-up issue if its contract is
  proven equivalent

Risk level:

- medium

Rollback rule:

- restore local serialization/write helpers in any module where artifact bytes,
  trailing newline behavior, or sidecar output changes

### Stage 5: consolidate compliance guard configuration parsing

Target family:

- near-duplicate config readers for drawdown, daily loss, and kill-switch state
- repeated low-level config assembly in `src/api/main.py`

Source family from audit:

- duplication audit finding 9

Canonical owner:

- process/runtime configuration boundary under `src/cilly_trading/config/*` as
  defined in `docs/architecture/shared_utility_ownership.md` and
  `docs/architecture/configuration_boundary.md`

Why this is later:

- this work touches control-path configuration behavior
- ownership is clear, but the risk is higher than the exact helper families
- it is safer after shared consolidation patterns have already been proven on
  lower-risk helper stacks

Implementation-ready step:

- extract shared runtime config parsing helpers into the runtime config boundary
- rewire compliance modules and API assembly to consume those helpers
- keep guard decision logic local to the compliance modules
- do not change config key names, ranges, or precedence in this stage

Risk level:

- medium

Rollback rule:

- restore current API-local and guard-local config parsing if environment or
  guard-state resolution changes

### Stage 6: align strategy configuration parsing with canonical schema ownership

Target family:

- divergent duplication between `config_schema.py` normalization and
  strategy-local dataclass parsing

Source family from audit:

- duplication audit finding 7

Canonical owner:

- `src/cilly_trading/strategies/config_schema.py`

Why this is last in the in-scope sequence:

- this is the broadest and highest-risk family in scope
- it includes known key-name drift and local strategy assumptions
- forcing it earlier would mix consolidation with semantic alignment risk

Implementation-ready step:

- move one strategy at a time to schema-owned normalization outputs
- preserve the currently effective config contract per strategy during each
  issue
- treat alias mapping and default equivalence as explicit acceptance criteria
- only delete strategy-local parsing once schema-owned inputs are fully proven
  equivalent for that strategy

Risk level:

- medium to high

Rollback rule:

- restore the strategy-local parsing path for the affected strategy if resolved
  config keys, defaults, or coercion semantics change

## Deferred duplication families

The audit identifies additional duplication families that should not be merged
into the first consolidation sequence for `#698`:

- alert-event identity as a near-duplicate of the signal identity stack
- market-data and audit hashing families with distinct payload contracts
- lightweight string/list normalization across validation entrypoints
- portfolio state models that are similar by name but not by contract

These families are deferred because they either have broader contract variance
or are not required to satisfy the helper/config planning scope of this issue.

## Implementation issue groups

The sequence above should be opened as separate later issues with the following
recommended boundaries.

### Issue group A: canonical identity primitives

- scope:
  - shared model-owned normalization, canonical JSON, hashing, and signal ID
    helpers
  - direct engine core consumers only
- acceptance focus:
  - identical signal ID output
  - identical analysis-run ID behavior where shared primitives are reused
  - no engine behavior change beyond helper ownership

### Issue group B: exact trade helper extraction

- scope:
  - deterministic trade numeric and ordering helpers used by
    `equity_curve.py` and `performance_report.py`
- acceptance focus:
  - identical ordered trade output
  - identical numeric rounding and conversion results

### Issue group C: metrics trade-helper alignment

- scope:
  - reuse only the exact shared primitives from issue group B in
    `risk_adjusted_metrics.py`
- acceptance focus:
  - identical metric inputs after helper reuse
  - no metrics formula changes

### Issue group D: canonical artifact serialization primitives

- scope:
  - shared canonical serialization and hashing primitives
  - direct artifact writer consumers with matching contracts
- acceptance focus:
  - identical artifact bytes
  - identical sidecar hash output where sidecars already exist

### Issue group E: compliance config reader consolidation

- scope:
  - runtime config readers for guard state assembly
  - direct API/compliance consumers only
- acceptance focus:
  - identical config precedence and defaulting
  - identical guard state outcomes

### Issue group F: per-strategy config alignment

- scope:
  - one strategy implementation at a time plus `config_schema.py`
- acceptance focus:
  - identical resolved strategy config for the targeted strategy
  - no cross-strategy behavior changes

## Migration order rationale

The recommended order minimizes runtime risk for three reasons:

1. It starts with exact duplicates where equivalence is easiest to prove.
2. It establishes shared primitives before moving broader or more divergent
   consumers onto them.
3. It pushes configuration-alignment work to the end, where semantic drift risk
   is highest.

That means the safe migration order is:

1. canonical identity primitives
2. exact trade helpers
3. metrics trade-helper alignment
4. canonical artifact serialization primitives
5. compliance config readers
6. per-strategy config alignment

## Risk register

### Risk 1: hidden semantic drift inside a supposed duplicate family

Where it applies:

- stages 3 through 6 especially

Failure mode:

- a helper looks duplicated but embeds a consumer-specific rule that changes
  output after consolidation

Mitigation:

- treat exact and near-duplicate families differently
- migrate only proven-identical primitives first
- keep contract-specific extraction or payload assembly local until reviewed

Rollback:

- restore the consumer-local helper and defer the family to a narrower issue

### Risk 2: canonical owner becomes too generic

Where it applies:

- stages 1, 4, 5, and 6

Failure mode:

- a consolidation issue creates a catch-all helper layer that violates the
  ownership boundaries defined in `#696` and `#697`

Mitigation:

- require every issue to name the canonical owner boundary before code changes
- reject generic `utils.py` placements outside the documented owners

Rollback:

- move the extracted helper back to the nearest documented owner and revert
  consumer rewrites that depended on the wrong placement

### Risk 3: consumer migration and helper deletion happen in one unsafe step

Where it applies:

- every stage

Failure mode:

- duplicate helpers are removed before behavior equivalence is proven in all
  targeted consumers

Mitigation:

- require a two-step implementation shape inside each issue:
  - establish shared owner
  - migrate consumers
  - remove duplicates last

Rollback:

- restore the deleted local helper and postpone deletion to a follow-up issue
  if needed

### Risk 4: configuration consolidation changes precedence or key semantics

Where it applies:

- stages 5 and 6

Failure mode:

- the consolidation accidentally changes defaults, aliases, coercion, or
  precedence

Mitigation:

- treat precedence and key-name equivalence as explicit acceptance criteria
- migrate one config family or one strategy at a time
- do not combine config consolidation with feature changes

Rollback:

- restore the previous parsing path for the affected config family or strategy

## Rollback strategy summary

If any later implementation issue shows behavior drift, the rollback path is:

1. restore the original consumer-local helper or parsing path
2. keep the new shared helper only if it is unused and harmless, otherwise
   revert it too
3. document the contract mismatch that blocked consolidation
4. reopen the duplication family in a narrower issue with corrected scope

Rollback should be done per duplication family, not by abandoning the full
consolidation roadmap.

## Review checklist for later implementation issues

Reviewers should reject a follow-up implementation issue if any of the
following is missing:

- the issue names the duplication family it is consolidating
- the issue names the canonical owner defined in `#696` or `#697`
- the issue limits file scope to the owner and direct consumers
- the issue states whether the family is exact, near, or divergent
- the issue preserves behavior before deleting local duplicates
- the issue defines a rollback point

## Exit condition for issue `#698`

Issue `#698` is complete when this document gives reviewers a concrete,
low-risk sequence for later consolidation of duplicated helper and config code
paths, including:

- documented consolidation sequence
- implementation-ready issue groups
- a migration order that prioritizes low-risk exact duplicates first
- explicit risk and rollback guidance for each stage

## Manual validation performed

Manual validation for this plan consisted of review of:

- `docs/architecture/code_b6_duplication_audit.md`
- `docs/architecture/shared_utility_ownership.md`
- `docs/architecture/configuration_boundary.md`
- `docs/architecture/api_boundary_cleanup_refactor_plan.md`

That review confirmed that:

- the helper and config duplication families in scope are already documented
- canonical ownership is already defined for the in-scope families
- the remaining missing artifact for `#698` was the implementation sequence,
  migration order, and safety guidance

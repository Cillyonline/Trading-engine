# GitHub Workflow, Issue Structure, and Milestone Audit

## Scope

This audit documents the repository's current GitHub workflow, issue structure, and milestone usage for issue `#687`.

It is descriptive only. It does not change issues, milestones, workflow behavior, or governance rules.

## Audit Method

- Reviewed the current repository-level GitHub configuration in `.github/ISSUE_TEMPLATE/issue.md`, `.github/pull_request_template.md`, and `.github/workflows/ci.yml`.
- Reviewed all existing GitHub issues across open and closed states.
- Reviewed all existing GitHub milestones across open and closed states.
- Used manual sampling across early, mid, and recent issue eras to confirm the observed patterns.

## Current GitHub Workflow Overview

### Repository workflow artifacts

- One issue template exists: `.github/ISSUE_TEMPLATE/issue.md`
- One pull request template exists: `.github/pull_request_template.md`
- One GitHub Actions workflow exists: `.github/workflows/ci.yml`

### Current issue workflow in practice

The currently documented GitHub workflow is:

1. Create an issue.
2. Implement work through a pull request that references the issue with `Closes #<IssueID>`.
3. Run the repository CI workflow.
4. Merge once checks pass and review is complete.

### What is standardized today

- New issues have a single canonical template with:
  - `Goal`
  - `Context (optional)`
  - `IN SCOPE`
  - `OUT OF SCOPE`
  - `Acceptance Criteria`
  - `Test Requirements`
  - `Files allowed to change`
  - `Files NOT allowed to change`
  - `Notes / Risks`
- Pull requests have a standard body template that expects:
  - `Closes #<IssueID>`
  - Acceptance-criteria checklist
  - Constraints checklist
  - Test evidence
- CI currently runs one smoke-run contract workflow on `push` to `main` and on `pull_request`.

### What is not standardized or enforced today

- Existing issues are not backfilled to the current issue template.
- The current CI workflow does not validate issue structure, issue scope fields, milestone usage, or milestone naming.
- The PR template requests `Closes #<IssueID>`, but the current repository workflow does not include an active GitHub Action that enforces that string.
- Milestone assignment is mostly used, but not universally applied.

## Issue Inventory Summary

### Overall counts

- Total issues reviewed: `357`
- Issues without a milestone: `4`
- Issues using the full current-style structure (`Goal`, `IN SCOPE`, `Acceptance Criteria`, and explicit file constraints): `235`
- Issues using a partial structured format: `99`
- Free-form issues with little or no modern scope structure: `23`

### Structure adoption by period

| Period | Total issues | Full template | Partial structured | Free-form |
| --- | ---: | ---: | ---: | ---: |
| Through January 2026 | 111 | 21 | 72 | 18 |
| February 2026 | 125 | 98 | 25 | 2 |
| March 2026 | 121 | 116 | 2 | 3 |

### Representative issue patterns

#### 1. Early free-form or loosely structured issues

Examples:

- `#1` uses German headings (`Ziel`, `Kontext`, `Beschreibung`, `Akzeptanzkriterien`) and does not define explicit scope boundaries or allowed files.
- `#31` to `#38` era issues often rely on title conventions and milestone context rather than a consistent body contract.

Observed characteristics:

- mixed language
- inconsistent heading names
- missing `OUT OF SCOPE`
- missing file-level boundaries
- acceptance criteria present in some issues but not normalized

#### 2. Mid-era partially structured issues

Examples:

- `#121` contains `Goal`, `IN SCOPE`, `OUT OF SCOPE`, and `Acceptance Criteria`, but does not include explicit allowed/not-allowed file sections.
- `#143` includes `Issue Type`, `Goal`, `In Scope`, `Out of Scope`, and `Allowed Files`, but uses different heading casing and wording than the current template.
- `#533` includes `Context`, `Goals`, `Acceptance Criteria`, and `Out of Scope`, but no explicit file constraints and no milestone.

Observed characteristics:

- scope usually exists, but section names vary
- file constraints are optional or omitted
- issue body quality depends on authoring period rather than a stable repository rule
- some governance/process issues remain outside milestone structure

#### 3. Recent fully templated issues

Examples:

- `#679` to `#698`
- the full GOV-B4, ARCH-B5, DOCS-B3, REPO-B2, and CODE-B6 issue sets

Observed characteristics:

- consistent heading names
- explicit scope boundaries
- explicit test requirements
- explicit file permissions
- clearer implementation boundaries than earlier issues

## Issue Structure Findings

### Finding 1: Issue quality improved significantly, but the repository contains three distinct issue eras

The issue history is not structurally uniform. The repository currently contains:

- an early free-form era
- a partially normalized middle era
- a recent fully templated era

This means contributors must infer issue expectations differently depending on when an issue was created.

### Finding 2: Scope definition is inconsistent across older and mid-era issues

Recent issues consistently separate `IN SCOPE` and `OUT OF SCOPE`.

Older issues frequently omit one or more of:

- explicit non-goals
- file boundaries
- test requirements
- a clear single deliverable

This creates ambiguity about whether an issue is implementation work, planning work, tracking work, or documentation work.

### Finding 3: File-level implementation boundaries are a recent governance addition

Only `235` of `357` issues include the current-style explicit file constraints. Earlier issues often rely on narrative wording instead of hard modification boundaries.

This is a material governance improvement, but it is not historically consistent across the backlog.

### Finding 4: Tracking and execution issues are mixed into the same issue pool with inconsistent signaling

Examples:

- `#307` and `#321` are explicit milestone tracking issues with `Files allowed to change: None`.
- `#143` is setup/governance work for exploration.
- many other issues are direct implementation tasks.

The repository uses a single issue list for:

- implementation tasks
- audits
- documentation work
- governance work
- tracking/exit issues
- exploratory question issues

That is workable, but the labeling and structure for distinguishing those roles has not been fully consistent over time.

### Finding 5: A small number of issues are outside the milestone model entirely

The following issues have no milestone:

- `#1`
- `#56`
- `#510`
- `#533`

This is a small share of the backlog, but it shows milestone assignment has not been fully universal.

## Milestone Inventory Summary

### Overall counts

- Total milestones reviewed: `71`
- Open milestones: `5`
- Closed milestones: `66`

### Naming families currently in use

The milestone set uses multiple naming families:

- `MVP ...`
- `EXP-...`
- `DISC-...`
- `Phase ...`
- `Governance Alignment ...`
- `Documentation Alignment ...`
- `Cleanup ...`
- uncategorized names such as `Roadmap Governance & Alignment` and `Repo Hardening Foundation`

### Current active milestone pattern

The active open milestones are the recent cleanup block milestones:

- `Cleanup - Repository Hygiene (Block 2)`
- `Cleanup - Documentation Consolidation (Block 3)`
- `Cleanup - GitHub Process & Governance (Block 4)`
- `Cleanup - Architecture Boundary Cleanup (Block 5)`
- `Cleanup - Code Deduplication & Consistency (Block 6)`

This block-based cleanup structure is internally consistent.

## Milestone Findings

### Finding 6: Milestone naming is not globally consistent across the repository history

Examples of different naming models:

- product-version milestones: `MVP 1.0 - Hardening`
- exploration/discovery milestones: `EXP-1 ...`, `DISC-2 ...`
- phase milestones: `Phase 10 - ...`
- alignment milestones: `Governance Alignment - ...`, `Documentation Alignment - ...`
- cleanup block milestones: `Cleanup - ... (Block N)`
- custom standalone milestones: `Roadmap Governance & Alignment`, `Repo Hardening Foundation`

The current cleanup block format is clean, but it sits on top of a historically mixed milestone taxonomy.

### Finding 7: Some milestone titles overlap by phase number instead of maintaining one phase = one milestone

Duplicate or overlapping phase identifiers exist, for example:

- `Phase 6 - Controlled External Exposure`
- `Phase 6 - Controlled External Exposure` with alternate punctuation in the actual milestone title
- `Phase 9 - Real-World Data Validation (Offline)`
- `Phase 9 - Quality & Test Hardening`
- `Phase 9 - Formal Exit`
- `Phase 18 - External Integration & Client Contracts`
- `Phase 18 - Operational Snapshot Runtime`
- `Phase 23 - Backtest Evaluation & Metrics`
- `Phase 23 - Research Dashboard Governance`
- `Phase 27 - Risk Management Framework`
- `Phase 27 - Risk Framework Isolation & Enforcement`
- `Phase 33 - Execution Control & Trade Lifecycle`
- `Phase 33 - Data Pipeline & Market Data Governance`

This creates overlap between milestone identity and milestone theme. In practice, some phase numbers represent a single milestone, while others represent multiple different milestones.

### Finding 8: There is at least one exact naming duplication caused by punctuation variance

Two separate milestones exist for Phase 6 with the same wording and only punctuation variation.

This is a clear naming inconsistency.

### Finding 9: Some milestones appear to encode phase progression, while others encode work type or governance theme

Examples:

- `Phase 35 - Observability & Telemetry` encodes roadmap progression.
- `Cleanup - GitHub Process & Governance (Block 4)` encodes a cleanup workstream block.
- `Governance Alignment - Roadmap Authority & Phase Status` encodes a governance adjustment theme.

These are all valid organizational concepts, but they do not follow one shared milestone model.

### Finding 10: Milestone scope overlap is most visible around reused phase numbers

The largest overlap risk is not duplicate issue membership within a milestone. It is semantic overlap between milestone names that imply the same roadmap phase while describing different work packages.

Examples:

- Phase 17 and Phase 17b both relate to interface/dashboard concerns.
- Phase 23 is used both for backtest evaluation and later research dashboard governance.
- Phase 18 is used for both external integration and operational snapshot runtime.

This makes milestone titles harder to interpret without reading their descriptions.

## Current Usage Patterns

### Issues are usually milestone-driven

Only `4` of `357` issues have no milestone. Milestone usage is therefore strong overall.

### Recent work is organized as tightly grouped milestone blocks

The newest cleanup milestones each contain a small, ordered issue set, for example:

- audit issue
- definition issue
- standardization issue
- enforcement or planning issue

This is the clearest and most internally consistent pattern in the current repository.

### Older milestone usage is more roadmap-like than governance-like

The older repository history uses milestones as broad program increments:

- MVP releases
- discovery phases
- roadmap phases

The newer repository history uses milestones as tightly scoped governance and cleanup blocks.

That shift is visible and useful, but it means milestone semantics changed over time.

## Efficiency and Governance Impact

### What currently works well

- Recent issues are substantially clearer than older issues.
- The current issue template defines scope, verification, and file boundaries well.
- PRs have a consistent expected structure.
- Milestones are used for nearly all issues.
- The current cleanup block milestones are easy to follow.

### Current inefficiencies and risks

- Reviewers must interpret multiple historical issue formats.
- Older issues do not always communicate scope boundaries or modification limits clearly.
- Milestone titles do not always reveal whether they represent a phase, a release, a discovery effort, or a governance cleanup block.
- Reused phase numbers create naming ambiguity.
- Governance expectations exist in templates and issue writing style, but are only partially enforced by workflow automation.

## Conclusion

The repository has clearly moved toward a disciplined GitHub workflow, but it has not yet reached historical consistency.

The current state can be summarized as follows:

- Issue structure is now strong for recent work, but the full issue history is mixed across three structural eras.
- Milestone usage is widespread, but milestone naming and semantics are historically inconsistent.
- The most important issue inconsistency is missing or uneven scope definition in older issues.
- The most important milestone inconsistency is overlapping phase naming and mixed taxonomy models.
- The current cleanup-block governance work is more structured than the older roadmap-era workflow and provides the clearest baseline for future standardization.

## Manual Validation Notes

This audit was manually validated against:

- all open and closed issue records available through the repository issue list
- all open and closed milestone records available through the repository milestone list
- representative issue samples from early, middle, and recent repository history
- the current repository `.github` workflow and template files

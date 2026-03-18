# Canonical GitHub Workflow

## Purpose

This document defines the canonical minimal GitHub workflow for planning, executing, and tracking work in this repository.

It standardizes the path from roadmap planning to merged pull request without changing existing issues, creating milestones, or enforcing these rules technically.

## Canonical Flow

The required workflow is:

`roadmap -> milestone -> issue -> PR -> merge`

Each step has one purpose:

1. **Roadmap**
   Defines the larger workstream, phase, or program direction.
2. **Milestone**
   Groups issues that belong to one roadmap phase or one bounded execution block.
3. **Issue**
   Defines one clear goal that can be implemented and reviewed as a single unit.
4. **Pull Request**
   Delivers the implementation for exactly one issue and records validation evidence.
5. **Merge**
   Completes the issue after review and required checks pass.

## Workflow Steps

### 1. Plan work in the roadmap

Roadmap entries define the planning layer.

They should answer:

- what phase or workstream exists
- why that work matters
- what outcome is expected at a high level

Roadmap entries do not replace implementation issues. They provide the planning source that later maps into milestones and issues.

### 2. Group work in a milestone

Each implementation issue must belong to a milestone when milestone usage is applicable for that workstream.

A milestone is the execution container between roadmap planning and issue execution.

A milestone should represent one of the following:

- one roadmap phase
- one bounded cleanup block
- one bounded governance or documentation block tied to a roadmap-level objective

A milestone must not mix unrelated roadmap goals.

### 3. Define one issue with one clear goal

An issue is the smallest tracked unit of planned work.

Each issue must define one clear goal. An issue must not combine multiple unrelated deliverables in one scope.

Required issue rules:

- one issue = one clear goal
- no mixed scopes
- issue scope must stay within its parent milestone
- the issue body must make the implementation boundary understandable and actionable

For issue creation, the author should define:

- `Goal`
- `IN SCOPE`
- `OUT OF SCOPE`
- `Acceptance Criteria`
- `Test Requirements`
- allowed and restricted file boundaries when relevant

An issue should be rejected or rewritten if it:

- combines planning work and implementation work in one ticket
- combines multiple unrelated deliverables
- has acceptance criteria that cannot be reviewed clearly
- has no understandable boundary for what is included vs excluded

### 4. Open one PR for one issue

A pull request is the execution artifact for one issue.

PR rules:

- a PR must reference its issue
- a PR must not mix work from multiple unrelated issues
- the PR description must make it obvious how the change satisfies the issue acceptance criteria

The required reference format is:

- `Closes #<IssueID>`

If a PR cannot truthfully close the issue it references, the PR is not ready for merge.

### 5. Merge after review and validation

Merge is the final tracking step.

A PR may be merged only when:

- the PR references the governing issue
- the implementation matches the issue scope
- acceptance criteria are satisfied
- required review is complete
- required tests or validation have passed

After merge, the merged PR becomes the implementation record for the issue, and the issue becomes the traceable unit of completed work inside the milestone.

## Roadmap to Milestone Mapping

The roadmap is the planning source. Milestones are the execution grouping derived from roadmap planning.

The mapping rule is:

- roadmap defines the phase or workstream
- milestone groups the executable issue set for that phase or workstream

This means:

- one roadmap phase may map to one milestone when the phase is already bounded
- one roadmap workstream may map to one bounded milestone block when the work is being executed as a cleanup or governance block
- milestone naming should make the roadmap relationship understandable

Milestones should not be created as unrelated buckets with no roadmap meaning.

## Phase Mapping Rule

Phases map to milestones as the default planning model.

The default interpretation is:

- a phase is the roadmap-level definition of a work area
- a milestone is the GitHub execution container for that phase

If a phase is too broad for a single execution window, it may be represented by a bounded milestone block, but that block must still trace back to a defined roadmap phase or roadmap-governed workstream.

The repository should therefore maintain this chain of traceability:

`roadmap phase/workstream -> milestone -> issue -> PR -> merge`

## Minimal Governance Rules

The canonical workflow is governed by these minimal rules:

1. A roadmap item defines the planning context.
2. A milestone groups related issues under that planning context.
3. An issue must have one clear goal.
4. Mixed scopes are not allowed in one issue.
5. A PR must reference its governing issue.
6. A PR should implement one issue only.
7. Merge happens only after scope, review, and validation are satisfied.

## Non-Goals

This document does not define:

- changes to existing issue history
- creation of new milestones
- GitHub Actions or bot enforcement
- label taxonomy
- branching strategy

## Manual Validation

This workflow is valid if a contributor can read this document and answer all of the following without extra interpretation:

- how work moves from planning to merge
- what a milestone represents
- what an issue is allowed to contain
- why a PR must reference an issue
- how roadmap phases relate to milestones

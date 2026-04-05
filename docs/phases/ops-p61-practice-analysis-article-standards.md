# OPS-P61 - Practice and Analysis Article Standards

## Goal

Define one canonical editorial standard and Definition of Done for Practice Articles and Analysis Articles, aligned to the completed Knowledge Article standard reference from issue `#7`.

## Context and Authority

Issue `#890` consolidates former issues `#8` (Practice Article) and `#9` (Analysis Article) to prevent parallel inconsistency.

This artifact treats the issue body as authoritative scope and keeps the issue title/body mismatch out of implementation scope.

## Scope Boundary

In scope:
- define what a Practice Article is
- define what an Analysis Article is
- define purpose, expected structure, quality expectations, and Definition of Done for both
- keep both structurally consistent with the Knowledge Article standard reference pattern
- keep Analysis Articles clearly separated from signal-style and recommendation-style outputs
- provide a reusable review reference for drafting and QA

Out of scope:
- implementation work
- agent prompt design
- WordPress publishing logic
- Elementor work
- redefining the Knowledge Article itself

## Dependencies

- `#3` - Phase 2 editorial epic exists
- `#1` - Phase 2 MVP content types and governance boundaries decision is completed
- `#7` - Knowledge Article standard is the structural reference source

## Shared Structural Template (Knowledge-Reference Alignment)

The shared template below is the required structure across Knowledge, Practice, and Analysis article standards.

1. Purpose and intended use
2. Required structure blocks
3. Quality expectations
4. Definition of Done (DoD)
5. Review checklist for drafting and QA

This template is the alignment baseline used by this issue for Practice and Analysis standards.

## Practice Article Standard

### Purpose and Intended Use

Practice Articles are execution-focused educational pieces that guide the reader through a bounded method, workflow, or repeatable procedure in a practical way.

### Required Structure Blocks

1. Title and scope statement
2. Purpose and expected learning outcome
3. Preconditions and required inputs
4. Step-by-step practice workflow
5. Verification checkpoints and expected outcomes
6. Typical mistakes and bounded correction guidance
7. Closing recap and follow-up practice suggestions

### Quality Expectations

- language is clear, procedural, and testable by a reviewer
- each step has observable output or checkpoint criteria
- prerequisites and constraints are explicit before execution steps
- the article avoids vague guidance that cannot be verified
- examples stay bounded to the article objective and do not drift to unrelated topics

### Definition of Done (Practice Article)

- [ ] purpose and intended use are explicit
- [ ] all required structure blocks are present
- [ ] step sequence is complete and internally consistent
- [ ] checkpoints define what "correct" output looks like
- [ ] quality expectations are met and reviewable
- [ ] article is usable by drafting and QA without additional interpretation

## Analysis Article Standard

### Purpose and Intended Use

Analysis Articles are interpretation-focused evidence documents that explain observations, reasoning, and bounded conclusions without crossing into signal or recommendation behavior.

### Required Structure Blocks

1. Title and analysis scope statement
2. Context and evidence basis
3. Observations and interpretation
4. Assumptions, constraints, and uncertainty notes
5. Bounded conclusion summary
6. Review checklist and DoD confirmation block

### Quality Expectations

- reasoning is traceable to explicit evidence statements
- assumptions and uncertainty are explicit, not implicit
- claims are bounded, falsifiable, and non-promotional
- wording avoids prescriptive trading or execution language
- conclusions stay inside editorial analysis boundaries

### Non-Signal Boundary Rules (Mandatory)

Analysis Articles must not include:
- buy, sell, entry, exit, position-sizing, or execution directives
- recommendation language ("should trade", "must enter now", "best signal")
- signal scoring output presented as actionable instruction
- target/stop style instruction framing

Analysis Articles must include:
- explicit non-recommendation framing
- bounded interpretation language tied to available evidence
- clear separation between analysis commentary and any future execution process

### Definition of Done (Analysis Article)

- [ ] purpose and intended use are explicit
- [ ] all required structure blocks are present
- [ ] evidence-to-interpretation traceability is clear
- [ ] non-signal boundary rules are explicitly satisfied
- [ ] no recommendation or execution directive language is present
- [ ] article is usable by drafting and QA without additional interpretation

## Cross-Content Structural Consistency Matrix

| Structural Category | Knowledge (Reference) | Practice | Analysis |
| --- | --- | --- | --- |
| Purpose and intended use | Required | Required | Required |
| Required structure blocks | Required | Required | Required |
| Quality expectations | Required | Required | Required |
| Definition of Done | Required | Required | Required |
| Drafting and QA review checklist | Required | Required | Required |
| Non-signal editorial boundary | Required where applicable | Required by scope discipline | Mandatory and explicit |

This table is the structural consistency checkpoint across the three content types.

## Verification Steps and Pass Criteria

1. Check structural consistency across all three content types.
   - Pass criteria: the shared template and consistency matrix show matching section categories.
2. Check that the task remains within Phase 2.
   - Pass criteria: this artifact documents editorial contract scope only and does not claim other phase work.
3. Check that no later implementation details are pulled forward.
   - Pass criteria: no runtime, publishing, agent prompt, or technical implementation instructions are introduced.
4. Check that recommendation/signal drift is explicitly prevented for Analysis Articles.
   - Pass criteria: explicit mandatory non-signal boundary rules and DoD checks are present.

## Roadmap Check (Phase 2)

This issue belongs to Phase 2 because it documents MVP content-type standards and Definition of Done boundaries for editorial governance.

This artifact does not redefine architecture, does not introduce implementation details, and does not claim readiness beyond documented editorial contract scope.

## Issue-Level Definition of Done Coverage

- scope respected
- acceptance criteria met
- verification steps documented
- roadmap check completed

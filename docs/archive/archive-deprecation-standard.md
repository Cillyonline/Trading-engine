# Archive And Deprecation Path Standard

## Document Status
- Class: Canonical
- Canonical Source(s): N/A (Class=Canonical)
- Rationale: This file is the authoritative process standard for safe legacy
  documentation deprecation and archiving.

## Goal

Define a safe, reversible path to remove uncertain legacy documents from active
navigation without losing historical knowledge.

## Status Vocabulary

- `Deprecated`: Legacy document remains available for traceability, but active
  usage must migrate to a named successor.
- `Archived`: Inactive historical record. Not part of active navigation.
- `Superseded by`: Mandatory successor reference to the active canonical or
  derived replacement.

## Mandatory Header For Deprecated/Archived Documents

Every deprecated or archived document must include this block:

```md
## Document Status
- Class: <Deprecated|Archived>
- Canonical Source(s): <authoritative active document(s)>
- Superseded by: <active replacement path or "N/A">
- Rationale: <short reason>
```

If no safe successor exists yet, keep the document out of archive and classify
it as deprecated until a successor is defined.

## Deprecation Flow

1. Confirm document is uncertain/legacy and not canonical authority.
2. Add `Document Status` block with `Class: Deprecated`.
3. Add explicit `Superseded by` path to active replacement.
4. Remove deprecated path from active navigation (`docs/index.md`) when the
   successor link is stable.
5. Keep the deprecated file reachable by direct link during migration.

## Archive Flow

1. Archive only after successor migration is complete.
2. Ensure archived file keeps `Superseded by` reference.
3. Keep archive files outside active navigation sections.
4. Never make canonical main documents primarily depend on archive links.

## Successor Chain Rule

- Every deprecated/archived document must resolve to an active successor path.
- Successor chains must be finite and end on a non-archived document.
- Broken or circular successor chains block archival approval.

## Navigation And Canonical Guardrails

- `docs/index.md` is an active navigation surface and must prefer active paths.
- Canonical main documents must not primarily reference `docs/archive/**`.
- Archive links are allowed only as historical context, not as primary
  operational guidance.

## Review Checklist

1. Deprecated/archived document has required status metadata.
2. `Superseded by` path exists and points to active documentation.
3. No canonical main document primarily routes users into archive content.
4. `docs/index.md` keeps active navigation paths and avoids archive-first flows.

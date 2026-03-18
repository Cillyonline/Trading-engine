# Canonical output snapshots (golden masters)

This repository uses **canonical output snapshots** (golden masters) to protect the deterministic analysis contract. A snapshot is a committed JSON file that represents the canonical engine output for a fixed snapshot database input.

## Rules of use

### When snapshots are required
- Any change that affects the **contracted analysis output payload** (fields, ordering, canonicalization, schema versioning, or deterministic computation logic) must be reflected in the golden master snapshot so that drift is visible and reviewed.  
- Any contract change that is intended to be **breaking or observable** must be captured by an updated snapshot and the related schema versioning rules.

### When snapshots are allowed
- Updating a snapshot is allowed **only** when a contract change is intentional, reviewed, and accompanied by the explicit update action described below.
- Snapshot updates are allowed only inside `tests/golden/**` and must be committed as part of the change.

### When snapshots are forbidden
- Snapshots must **not** be updated to "make tests pass" when output drift is unexpected or unintended.
- Snapshots must **not** be updated for runtime-only changes that do not impact the canonical analysis output.
- Snapshots must **not** be removed. Removal is out of scope and forbidden.

## Contract changes that require snapshot updates
Update the golden master snapshot when any of the following are changed intentionally:
- Output fields or field names in the canonical analysis payload.
- Canonical ordering, stable JSON formatting, or serialization rules.
- Deterministic output computation that affects signal payload contents.
- Schema version updates or schema enum changes that are tied to the output payload.

## Snapshot lifecycle and retention
- Golden master snapshots are **versioned** and stored in `tests/golden/**`.
- Snapshot files are retained indefinitely to make output drift visible in history.
- Each snapshot file must have an explicit version suffix (example: `analysis_output_golden_v1.json`) and is treated as immutable history.

## Enforcement (tests + CI)
- Tests compare computed output bytes against the committed snapshot. Any drift fails the test and therefore CI.
- Tests do **not** auto-update snapshots. Updates require an explicit developer action.

## Explicit snapshot update action
To intentionally update the golden master snapshot, run the golden master test with the environment flag below. This is the **only** documented update mechanism:

```bash
UPDATE_GOLDEN_SNAPSHOTS=1 pytest tests/golden/test_analysis_golden_master.py
```

This action rewrites the snapshot file and produces an explicit diff that must be reviewed and committed.

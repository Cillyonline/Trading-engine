# Review Package Template

Use this template after implementing a GitHub issue.

Purpose:
- give Codex A enough evidence to review implementation
- verify active issue scope
- verify acceptance criteria
- verify test evidence
- verify risk and governance boundaries

Do not omit sections.
If a section does not apply, write `None`.

---

## SUMMARY

Briefly describe what was implemented.

---

## ACTIVE ISSUE

#<issue-number> — <issue-title>

---

## MODIFIED FILES

- `<path>` — <short description>

---

## NEW FILES

- `<path>` — <short description>

---

## DELETED FILES

- `<path>` — <reason>

---

## TEST COMMAND

<exact command here>

---

## FULL TEST OUTPUT

<full output here>

---

## ACCEPTANCE CRITERIA EVIDENCE

- AC1: <satisfied | partial | failed> — <one sentence evidence>
- AC2: <satisfied | partial | failed> — <one sentence evidence>
- AC3: <satisfied | partial | failed> — <one sentence evidence>

---

## RISK NOTES

State whether the change affects:

- trading logic
- backtesting assumptions
- risk framework
- execution/order lifecycle
- data persistence
- API contracts
- deployment/runtime behavior
- security/secrets
- paid APIs

If none apply, write `None`.

---

## OUT OF SCOPE

List what was intentionally not changed.

---

## FOLLOW-UP ISSUES

List follow-up work, or write `None`.

---

## GOVERNANCE CHECK

- [ ] Implementation stayed inside active issue scope
- [ ] No unrelated refactor
- [ ] No architecture drift
- [ ] No unsupported live-trading claim
- [ ] No broker-readiness claim
- [ ] No production-readiness claim
- [ ] No trader-validation claim
- [ ] No profitability claim
- [ ] No secrets or credentials added

---

## CRITICAL LANE CHECK

Complete only if relevant.

- [ ] Human review required
- [ ] Auto-merge forbidden
- [ ] Risk notes included
- [ ] Rollback/recovery notes included where runtime behavior changed

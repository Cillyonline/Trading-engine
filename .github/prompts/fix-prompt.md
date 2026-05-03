# Fix Prompt Template

Use this template when Codex A returns `CHANGES REQUIRED`.

Purpose:
- give Codex B a strict correction request
- keep the fix inside the active issue scope
- prevent unrelated refactors
- require test evidence and a complete review package

Do not use this template for new feature work.
Do not expand the active issue scope.
Do not introduce unrelated refactors.

---

## MODE

EXECUTION

---

## ACTIVE ISSUE

#<issue-number> — <issue-title>

---

## BLOCKING DEFECT

<one sentence describing the blocking defect>

---

## REQUIRED CHANGES

1. <imperative change>
2. <imperative change>
3. <imperative change>

Rules:
- Use exact file paths when known.
- Do not use vague wording.
- Do not use "consider", "for example", "at least", or "if needed".
- Do not add new features.
- Do not refactor unrelated code.

---

## ACCEPTANCE TARGET

- <exact verifiable target>
- <exact verifiable target>
- <exact verifiable target>

---

## FILES ALLOWED

- `<path>`
- `<path>`

---

## FILES NOT ALLOWED

- `<path>`
- `<path>`

---

## MUST REMAIN UNCHANGED

- <behavior, file, API, schema, or document that must remain unchanged>
- <behavior, file, API, schema, or document that must remain unchanged>

---

## TEST REQUIREMENTS

Run and return exact output for:

<test command>

---

## RETURN PACKAGE

Return a complete review package:

- SUMMARY
- MODIFIED FILES
- NEW FILES
- DELETED FILES
- TEST COMMAND
- FULL TEST OUTPUT
- RISK NOTES
- OUT OF SCOPE
- FOLLOW-UP ISSUES

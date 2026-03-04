\# AGENTS.md — Codex Test Guard \& Branch Discipline



\## Definition of Done (HARD)

\- Do NOT claim completion unless this command is run and passes:

&nbsp; python -m uv run -- python -m pytest --import-mode=importlib



\## Environment

\- Ensure dependencies are installed via:

&nbsp; python -m uv sync --frozen --extra test



\## Branch rules

\- Never commit directly to main.

\- Work only on a feature branch or Codex worktree branch.

\- Keep changes strictly inside the GitHub Issue scope and allowed files.



\## Safety

\- No scope expansion, no refactors outside the issue.

\- Preserve determinism, governance, and compliance guarantees.


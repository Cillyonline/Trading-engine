\# AGENTS.md — Codex Test Guard \& Branch Discipline



This file defines the working rules for AI agents (Codex) operating in this repository.



---



\# Definition of Done (HARD)



Do NOT claim completion unless the full test suite is executed and passes.



Required command:



python -m uv run -- python -m pytest --import-mode=importlib



All tests must pass before finishing any task.



---



\# Environment



Ensure dependencies are installed via:



python -m uv sync --frozen --extra test



Agents must verify the environment before running tests.



---



\# Standard Issue Workflow



When implementing a GitHub Issue follow this process:



1\. Analyze the GitHub issue and the repository structure.

2\. Produce a short implementation plan.

3\. Wait for approval before writing code.

4\. Implement only the files allowed by the issue.

5\. Avoid changes outside the issue scope.

6\. Run the full test suite.

7\. Only report completion when tests pass.



---



\# Branch Rules



\- Never commit directly to `main`.

\- Work only on a feature branch or Codex worktree branch.

\- Keep changes strictly inside the GitHub Issue scope and allowed files.



Typical workflow:



git checkout main  

git pull  

git checkout -b feature/<issue-name>



---



\# Safety Rules



\- No scope expansion.

\- No refactors outside the issue.

\- No architectural changes unless explicitly requested.

\- Preserve determinism, governance, and compliance guarantees.



---



\# Architecture Respect



Agents must respect existing module boundaries and repository structure.



Do NOT:



\- move modules

\- rename core components

\- change interfaces



unless the GitHub issue explicitly requires it.



---



\# Testing Requirements



Before finishing any implementation the agent must run:



python -m uv run -- python -m pytest --import-mode=importlib



Completion is invalid if tests are not executed.



---



\# Determinism Requirement



All implementations must preserve deterministic behavior.



No hidden state, randomness, or environment-dependent logic may be introduced.



---



\# Commit Discipline



Commits must:



\- be minimal

\- stay inside the issue scope

\- not modify unrelated files


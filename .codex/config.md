\# Codex Project Configuration



\## Environment Setup

python -m uv sync --frozen --extra test



\## Run Tests

python -m uv run -- python -m pytest --import-mode=importlib



\## Development Workflow

1\. Create a new branch before changes

2\. Implement changes according to GitHub issue

3\. Run full pytest suite

4\. Commit changes with descriptive message

5\. Push branch to GitHub



\## Rules

\- Never modify files outside the issue scope

\- Always run tests before committing

\- Keep deterministic behavior intact

\- Do not bypass risk or compliance modules


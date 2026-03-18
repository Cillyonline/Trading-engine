# Getting Started (Owner)

## A. Purpose
This guide provides the single authoritative setup path for local development.
Use it to prepare the environment, install the repository, and then hand off to
the canonical local-run or testing documents.

## B. Prerequisites
- Python 3.12+
- `pip`
- Git installed

## C. Clone the Repository

```bash
git clone <repo-url>
cd Trading-engine
```

## D. Single Authoritative Setup Method (canonical)
From the repository root, run exactly:

### Bash (macOS/Linux)

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -e ".[test]"
```

### PowerShell (Windows)

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e ".[test]"
```

The install step is canonical because it comes from the repository-controlled
`pyproject.toml`. It replaces older requirements-file-based instructions.

## E. Next Steps

- To start and verify the local API, continue to `docs/local_run.md`.
- To run the repository test suite, continue to `docs/testing.md`.
- To run the deterministic smoke run, continue to `docs/smoke-run.md`.

## F. Troubleshooting
- If `uvicorn: command not found` appears, activate the virtual environment again:

  Bash (macOS/Linux):
  ```bash
  source .venv/bin/activate
  ```

  PowerShell (Windows):
  ```powershell
  .\.venv\Scripts\Activate.ps1
  ```

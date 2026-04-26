# Working SOP – Cilly Trading Engine

## Default
- MODE: EXECUTION
- Exactly one active Issue

## Workflow
1) DEFINE
   - Create/confirm Issue exists (use Issue template)
   - Acceptance Criteria are testable
   - Set Board status: Ready

2) EXECUTE
   - Codex B implements strictly per the active Issue
   - Open a PR

3) VERIFY
   - Run local tests
   - Record commands + outputs in PR ("How to Test")

4) REVIEW GATE
   - Codex B provides list of all modified/new files
   - Provide full file contents to Codex A
   - Codex A returns: APPROVED or CHANGES REQUIRED

5) CLOSE
   - PR must include: Closes #<IssueID>
   - Merge only after APPROVED + green test
   - Issue closes automatically on merge
   - Set Board status: Done

## Blocked Rule
- If blocked: fix the blocker only
- No new topics while blocked

## Error Reporting
Always provide:
- command executed
- full output
- expected vs actual

## Definition of Done (DoD)
A change is considered DONE only if:
- Acceptance Criteria are fully met
- Tests were run and results are recorded in the PR
- Required status check test is green
- PR includes Closes #<IssueID>
- Codex A review gate result is recorded (APPROVED or CHANGES REQUIRED)
- No scope creep beyond the linked Issue
- Phase 6 gilt nur als abgeschlossen, wenn die Exit-Kriterien und die Exit-Checklist vollständig erfüllt sind: [phase-6-exit-criteria.md](../architecture/phase-6-exit-criteria.md), [checklists/phase-6-exit-checklist.md](../testing/checklists/phase-6-exit-checklist.md)

## Canonical Staging Deployment Contract
- For server deployment topology, runtime boundaries, environment/config separation, and non-productive scope, use:
  [runtime/staging-first-deployment-topology.md](runtime/staging-first-deployment-topology.md)
- The contract is staging-first and must not be interpreted as production or live-trading readiness.

## Deterministic Smoke Run – Local Execution

### Prerequisites
- Python 3 available in your environment.
- Run from the repository root so the default fixtures path (`fixtures/smoke-run/`) is available.
- Ensure the package is importable by setting `PYTHONPATH=src`. There is no installed top-level CLI command, so use the documented Python module command.

### Command (exact)
```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

### Expected stdout on success (exact, line-by-line)
```
SMOKE_RUN:START
SMOKE_RUN:FIXTURES_OK
SMOKE_RUN:CHECKS_OK
SMOKE_RUN:END
```

### Artifacts
- `artifacts/smoke-run/result.json`

### Exit code semantics
- `0` — success.
- `10` — fixtures missing (`input.json`, `expected.csv`, `config.yaml`).
- `11` — fixtures invalid (format, missing required keys/columns, or parse errors).
- `12` — constraints failed (validation errors or determinism guard triggered).
- `13` — output mismatch (artifact write/read mismatch).

### Determinism note
The smoke-run is deterministic: no time access, no randomness, and no network access are permitted during execution. Any attempt to access these will fail the run via the determinism guard.

### Reference
- [smoke-run.md](../testing/smoke-run.md)

## Quality Gate: Deterministic Smoke Run (Mandatory)

### Gate name
Deterministic Smoke Run

### Execution command (exact)
```bash
PYTHONPATH=src python -c 'from cilly_trading.smoke_run import run_smoke_run; raise SystemExit(run_smoke_run())'
```

### PASS conditions (explicit)
- Exit code == 0.
- Stdout contains EXACTLY (line-by-line, in order, no extra output):
  ```
  SMOKE_RUN:START
  SMOKE_RUN:FIXTURES_OK
  SMOKE_RUN:CHECKS_OK
  SMOKE_RUN:END
  ```

### FAIL conditions (explicit)
- Exit code != 0.
- Exit codes:
  - 10 (fixtures missing)
  - 11 (fixtures invalid)
  - 12 (constraints failed)
  - 13 (output mismatch)
- OR stdout deviates from the required success lines.
- Failure cases do NOT require specific stdout markers; failure is determined by exit code and/or deviation from the success stdout contract.

## Remote (Codespaces)

### Start Codespace
1) Open the repository on GitHub.
2) Select **Code → Codespaces → Create codespace on main**.
3) Wait for the devcontainer to finish provisioning and dependency install.

### Run Tests
```bash
python -m pytest
```

## Pull Request Testing
- Pull Requests are automatically tested in GitHub Actions.
- A green check allows merge.
- A red check blocks merge until tests pass.

### Run Paper Trading (Simulation)
Bounded paper-runtime operation is documented in dedicated runtime contracts,
not inline in this SOP. The current owner-facing bounded command path is the
OPS-P64 daily runner, which orchestrates the OPS-P63 workflow through existing
snapshot ingestion, analysis, bounded paper execution, reconciliation, and
evidence-capture steps.

Local OPS-P64 invocation:

```bash
python scripts/run_daily_bounded_paper_runtime.py \
  --db-path cilly_trading.db \
  --base-url http://127.0.0.1:18000
```

This command remains bounded and non-live. It does not provide live trading,
broker integration, real-capital execution, production-readiness evidence,
trader-validation evidence, or profitability claims.

Reference:
- [paper_trading.md](paper-trading.md)
- [runtime/p63-daily-bounded-paper-runtime-workflow.md](runtime/p63-daily-bounded-paper-runtime-workflow.md)
- [runtime/p64-one-command-bounded-daily-paper-runtime-runner.md](runtime/p64-one-command-bounded-daily-paper-runtime-runner.md)

**Datum:** 2026-03-29
**Thema:** Bounded Staging Prep – Host vorbereitet

**Ziel:**
Linux-Server für den ersten bounded Staging-Deploy der Cilly Trading Engine vorbereiten, ohne Public Exposure.

**Was wurde geprüft oder geändert:**
- OS-Version verifiziert: Debian GNU/Linux 13.4 (trixie)
- Kernel: 6.12.74+deb13+1-amd64
- Zeitzone: Europe/Berlin
- SSH extern erfolgreich getestet
- Ressourcen geprüft:
  - 4 vCPU
  - 7.8 GiB RAM
  - 240 GiB frei auf /
- curl vorhanden
- git installiert: 2.47.3
- Docker Engine installiert: 29.3.1
- Docker Compose Plugin installiert: v5.1.1
- Docker-Funktion mit hello-world erfolgreich geprüft
- Listening Ports geprüft: nur 22/tcp
- Verzeichnisstruktur angelegt:
  - /srv/apps/trading-engine
  - /srv/data/trading-engine
  - /srv/logs/trading-engine
  - /srv/backups/manual
- Compose-Grunddatei angelegt:
  - /srv/apps/trading-engine/compose.yml
- .env angelegt:
  - /srv/apps/trading-engine/.env
  - Rechte 600

**Ergebnis:**
- Host für bounded Staging vorbereitet: ja
- Docker betriebsbereit: ja
- Compose betriebsbereit: ja
- App bereits deployt: nein
- Public Exposure durchgeführt: nein**Datum:** 2026-03-29
**Thema:** Bounded Staging Prep – Bestandsaufnahme

**Ziel:**
Server-Basis für ersten bounded Staging-Deploy prüfen.

**Was wurde geprüft oder geändert:**
- OS-Version: Debian GNU/Linux 13.4 (trixie)
- Kernel: 6.12.74+deb13+1-amd64
- Docker-Version: noch nicht installiert
- Compose-Version: noch nicht installiert
- git: noch nicht installiert
- curl: 8.14.1 vorhanden
- vCPU: 4
- RAM: 7.8 GiB
- freier Speicher auf /: 240 GiB
- Zeitzone: Europe/Berlin
- SSH-Dienst: active, enabled
- Listening Ports: nur 22/tcp auf IPv4 und IPv6
- Gast-Firewall: keine Regeln sichtbar

**Ergebnis:**
- Mindestressourcen erfüllt: ja
- Externer SSH-Zugang funktioniert: ja
- Public Exposure für App-Dienste: noch nicht durchgeführt

**Risiken / Auffälligkeiten:**
- Root-Login per Passwort aktuell aktiv
- Keine Gast-Firewall-Regeln sichtbar
- Kein Swap konfiguriert
- Provider-Firewall im SCP weiterhin separat zu prüfen

**Folgeschritt:**
- git installieren
- Docker Engine + Compose Plugin über offizielles Docker-Repo installieren
- keine App-Ports veröffentlichen

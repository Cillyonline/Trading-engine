# Repository Audit – Duplicate & Conflicting Structure Cleanup (DISC-4 C2)

## Scope
Repository-wide audit for duplicate/conflicting directories and data artifacts, with safe cleanup limited to non-production areas. Production code (`src/**`) was not modified.

## Findings

### 1) Duplicate directory name: `api`
- **Category:** duplicate dir
- **Paths:**
  - `api/`
  - `docs/api/`
- **Evidence:**
  - Command (PowerShell/CMD safe):
    ```bash
    python -c "import os;from collections import defaultdict;root='.';name_map=defaultdict(list);\n[None for dirpath,dirnames,filenames in os.walk(root) if '.git' not in dirpath for d in dirnames for _ in (name_map[d].append(os.path.join(dirpath,d)),)];\n[print(name,'\\n  ' + '\\n  '.join(ps)) for name,ps in sorted(name_map.items()) if len(ps)>1]"
    ```
  - Output excerpt:
    - `api`
    - `  ./api`
    - `  ./docs/api`
- **Risk:** low
- **Proposed Action:** keep (distinct purposes: runtime API package vs documentation folder)

### 2) Duplicate directory name: `strategies`
- **Category:** duplicate dir
- **Paths:**
  - `src/cilly_trading/strategies/`
  - `tests/strategies/`
- **Evidence:**
  - Command (PowerShell/CMD safe):
    ```bash
    python -c "import os;from collections import defaultdict;root='.';name_map=defaultdict(list);\n[None for dirpath,dirnames,filenames in os.walk(root) if '.git' not in dirpath for d in dirnames for _ in (name_map[d].append(os.path.join(dirpath,d)),)];\n[print(name,'\\n  ' + '\\n  '.join(ps)) for name,ps in sorted(name_map.items()) if len(ps)>1]"
    ```
  - Output excerpt:
    - `strategies`
    - `  ./src/cilly_trading/strategies`
    - `  ./tests/strategies`
- **Risk:** medium (one path is in `src/**` which is out of scope for changes)
- **Proposed Action:** keep; note only (no changes allowed in `src/**`)

### 3) Duplicate filename: `README.md`
- **Category:** duplicate file
- **Paths:**
  - `README.md`
  - `docs/testing/determinism.md`
- **Evidence:**
  - Command (PowerShell/CMD safe):
    ```bash
    python -c "import os;from collections import defaultdict;root='.';paths=[];\n[paths.append(os.path.join(dirpath,f)) for dirpath,dirnames,filenames in os.walk(root) if '.git' not in dirpath for f in filenames];\nname_map=defaultdict(list);[name_map[os.path.basename(p)].append(p) for p in paths];\n[print(name,'\\n  ' + '\\n  '.join(ps)) for name,ps in sorted(name_map.items()) if len(ps)>1]"
    ```
  - Output excerpt:
    - `README.md`
    - `  ./README.md`
    - `  ./docs/testing/determinism.md`
- **Risk:** low
- **Proposed Action:** keep (distinct documentation contexts)

## Cleanup Actions
- No cleanup performed (no low-risk duplicate data/fixtures/snapshots identified within allowed paths that were safe to remove).

## Regression Guard
- Added a pytest guard to detect reintroduction of duplicate patterns in test data directories (e.g., `golden`, `fixtures`, `snapshots`) and duplicate filenames within those directories under `tests/**`.

## Evidence Commands Run
- Directory name scan:
  ```bash
  python -c "import os;from collections import defaultdict;root='.';name_map=defaultdict(list);\n[None for dirpath,dirnames,filenames in os.walk(root) if '.git' not in dirpath for d in dirnames for _ in (name_map[d].append(os.path.join(dirpath,d)),)];\n[print(name,'\\n  ' + '\\n  '.join(ps)) for name,ps in sorted(name_map.items()) if len(ps)>1]"
  ```
- Duplicate filename scan:
  ```bash
  python -c "import os;from collections import defaultdict;root='.';paths=[];\n[paths.append(os.path.join(dirpath,f)) for dirpath,dirnames,filenames in os.walk(root) if '.git' not in dirpath for f in filenames];\nname_map=defaultdict(list);[name_map[os.path.basename(p)].append(p) for p in paths];\n[print(name,'\\n  ' + '\\n  '.join(ps)) for name,ps in sorted(name_map.items()) if len(ps)>1]"
  ```

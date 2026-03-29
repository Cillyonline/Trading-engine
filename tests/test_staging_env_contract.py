from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
ENV_EXAMPLE_PATH = REPO_ROOT / ".env.example"
COMPOSE_PATH = REPO_ROOT / "docker" / "staging" / "docker-compose.staging.yml"
STAGING_DOC_PATH = (
    REPO_ROOT / "docs" / "operations" / "runtime" / "staging-server-deployment.md"
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_env_example_declares_required_bounded_first_paper_keys() -> None:
    content = _read(ENV_EXAMPLE_PATH)

    required_keys = [
        "PYTHONPATH",
        "CILLY_DB_PATH",
        "CILLY_LOG_LEVEL",
        "CILLY_LOG_FORMAT",
        "CILLY_STAGING_DB_DIR",
        "CILLY_STAGING_ARTIFACT_DIR",
        "CILLY_STAGING_JOURNAL_DIR",
        "CILLY_STAGING_LOG_DIR",
        "CILLY_STAGING_RUNTIME_STATE_DIR",
        "CILLY_CONTAINER_UID",
        "CILLY_CONTAINER_GID",
    ]

    for key in required_keys:
        assert f"{key}=" in content


def test_env_example_declares_db_path_and_snapshot_first_secret_wording() -> None:
    content = _read(ENV_EXAMPLE_PATH)

    assert "CILLY_DB_PATH=/data/db/cilly_trading.db" in content
    assert "Canonical first paper deployment is snapshot-first" in content
    assert "does not require" in content
    assert "provider secrets" in content


def test_env_example_contract_aligns_with_compose_and_staging_doc() -> None:
    env_content = _read(ENV_EXAMPLE_PATH)
    compose_content = _read(COMPOSE_PATH)
    doc_content = _read(STAGING_DOC_PATH)

    # DB path contract
    assert "CILLY_DB_PATH=/data/db/cilly_trading.db" in env_content
    assert 'CILLY_DB_PATH: "${CILLY_DB_PATH:?set CILLY_DB_PATH}"' in compose_content
    assert "- `CILLY_DB_PATH=/data/db/cilly_trading.db`" in doc_content
    assert "Database path (persistent): `/data/db/cilly_trading.db`" in doc_content

    # Bind-mount variable contract
    bind_vars = [
        ("CILLY_STAGING_DB_DIR", "/data/db"),
        ("CILLY_STAGING_ARTIFACT_DIR", "/data/artifacts"),
        ("CILLY_STAGING_JOURNAL_DIR", "/app/runs/phase6"),
        ("CILLY_STAGING_LOG_DIR", "/data/logs"),
        ("CILLY_STAGING_RUNTIME_STATE_DIR", "/data/runtime-state"),
    ]
    for var_name, target in bind_vars:
        assert f"{var_name}=" in env_content
        assert f'source: "${{{var_name}:?set {var_name}}}"' in compose_content
        assert f"target: {target}" in compose_content
        assert f"`{var_name}`" in doc_content
        assert f"`{target}`" in doc_content

    # UID/GID runtime contract
    assert "CILLY_CONTAINER_UID=" in env_content
    assert "CILLY_CONTAINER_GID=" in env_content
    assert (
        'user: "${CILLY_CONTAINER_UID:?set CILLY_CONTAINER_UID}:${CILLY_CONTAINER_GID:?set CILLY_CONTAINER_GID}"'
        in compose_content
    )
    assert "- `CILLY_CONTAINER_UID`" in doc_content
    assert "- `CILLY_CONTAINER_GID`" in doc_content
    assert "${CILLY_CONTAINER_UID}:${CILLY_CONTAINER_GID}" in doc_content

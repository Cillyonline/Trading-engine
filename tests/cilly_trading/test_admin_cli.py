"""Tests for the bounded admin CLI (issue #1140)."""

from __future__ import annotations

import sqlite3
import subprocess
import sys
from pathlib import Path

import pytest

from cilly_trading.cli.admin import build_parser, main


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _seed_db(path: Path) -> None:
    conn = sqlite3.connect(path)
    try:
        conn.execute("CREATE TABLE t (id INTEGER PRIMARY KEY, value TEXT NOT NULL);")
        conn.executemany(
            "INSERT INTO t (value) VALUES (?);",
            [("alpha",), ("beta",), ("gamma",)],
        )
        conn.commit()
    finally:
        conn.close()


def _row_count(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        cur = conn.execute("SELECT COUNT(*) FROM t;")
        return int(cur.fetchone()[0])
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# top-level CLI / help
# ---------------------------------------------------------------------------
def test_parser_includes_all_subcommands() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    for name in ("backup", "migrate", "cleanup"):
        assert name in help_text


def test_module_entrypoint_help() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    env = {"PYTHONPATH": str(repo_root / "src")}
    proc = subprocess.run(
        [sys.executable, "-m", "cilly_trading.cli", "--help"],
        cwd=str(repo_root),
        env={**env},
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert "backup" in proc.stdout
    assert "migrate" in proc.stdout
    assert "cleanup" in proc.stdout


def test_cli_unknown_command_returns_nonzero() -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(["nope"])
    # argparse exits 2 for unknown subcommand.
    assert excinfo.value.code != 0


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------
def test_backup_creates_consistent_copy(tmp_path: Path, capsys) -> None:
    src = tmp_path / "src.db"
    _seed_db(src)
    dest = tmp_path / "backup.db"

    rc = main(["backup", "--db-path", str(src), "--output", str(dest)])
    assert rc == 0
    assert dest.exists()
    # Source must remain untouched.
    assert _row_count(src) == 3
    # Destination must contain the same rows.
    assert _row_count(dest) == 3

    out = capsys.readouterr().out
    assert "backup written" in out


def test_backup_missing_source_returns_error(tmp_path: Path, capsys) -> None:
    dest = tmp_path / "backup.db"
    rc = main(
        ["backup", "--db-path", str(tmp_path / "missing.db"), "--output", str(dest)]
    )
    assert rc == 2
    err = capsys.readouterr().err
    assert "source database does not exist" in err


def test_backup_refuses_overwrite_without_force(tmp_path: Path, capsys) -> None:
    src = tmp_path / "src.db"
    _seed_db(src)
    dest = tmp_path / "backup.db"
    dest.write_bytes(b"existing")
    rc = main(["backup", "--db-path", str(src), "--output", str(dest)])
    assert rc == 2
    assert "destination already exists" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------
def test_migrate_invokes_existing_runner(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "migrate.db"
    captured = {}

    def fake_run_migrations(target_path):  # noqa: ANN001 - test stub
        captured["target"] = Path(target_path)
        return 7

    monkeypatch.setattr(
        "cilly_trading.db.migrations.run_migrations", fake_run_migrations
    )
    rc = main(["migrate", "--db-path", str(db_path)])
    assert rc == 0
    assert captured["target"] == db_path
    assert "migrations applied: 7" in capsys.readouterr().out


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
def test_cleanup_dry_run_does_not_delete(tmp_path: Path, capsys) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    a = artifact_dir / "a.tmp"
    b = artifact_dir / "b.tmp"
    a.write_text("x")
    b.write_text("y")

    rc = main(
        ["cleanup", "--path", str(artifact_dir), "--pattern", "*.tmp"]
    )
    assert rc == 0
    assert a.exists() and b.exists()
    out = capsys.readouterr().out
    assert "dry-run" in out
    assert "would delete" in out


def test_cleanup_delete_requires_confirm(tmp_path: Path, capsys) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    target = artifact_dir / "x.tmp"
    target.write_text("z")

    rc = main(
        ["cleanup", "--path", str(artifact_dir), "--pattern", "*.tmp", "--delete"]
    )
    assert rc == 2
    assert target.exists(), "must not delete without --confirm"
    assert "--confirm" in capsys.readouterr().err


def test_cleanup_delete_with_confirm_removes_files(tmp_path: Path, capsys) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    target = artifact_dir / "x.tmp"
    target.write_text("z")

    rc = main(
        [
            "cleanup",
            "--path",
            str(artifact_dir),
            "--pattern",
            "*.tmp",
            "--delete",
            "--confirm",
        ]
    )
    assert rc == 0
    assert not target.exists()
    assert "deleted 1 file" in capsys.readouterr().out


def test_cleanup_no_matches_is_zero_exit(tmp_path: Path, capsys) -> None:
    artifact_dir = tmp_path / "artifacts"
    artifact_dir.mkdir()
    rc = main(["cleanup", "--path", str(artifact_dir), "--pattern", "*.tmp"])
    assert rc == 0
    assert "no files matched" in capsys.readouterr().out

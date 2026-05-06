"""Bounded admin / maintenance CLI for the Cilly Trading engine (issue #1140).

This CLI is intentionally narrow:

  * ``backup``  – Make a SQLite backup copy of the engine database.
  * ``migrate`` – Invoke the existing migration runner from
    ``cilly_trading.db.migrations.run_migrations`` without duplicating its
    logic.
  * ``cleanup`` – Inspect (and optionally delete) artifact files. The default
    behavior is **dry-run**; deletion only happens when ``--delete`` is passed
    explicitly.

The CLI does not perform any broker actions, live-trading actions, real-money
execution, scheduling, or remote automation.
"""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path
from typing import Iterable, Optional, Sequence

from cilly_trading.db import DEFAULT_DB_PATH


def _resolve_db_path(value: Optional[str]) -> Path:
    return Path(value) if value else Path(DEFAULT_DB_PATH)


# ---------------------------------------------------------------------------
# backup
# ---------------------------------------------------------------------------
def cmd_backup(args: argparse.Namespace) -> int:
    """Create a consistent SQLite backup at ``--output``."""

    source = _resolve_db_path(args.db_path)
    if not source.exists():
        print(f"error: source database does not exist: {source}", file=sys.stderr)
        return 2

    destination = Path(args.output)
    if destination.exists() and not args.force:
        print(
            f"error: destination already exists (use --force to overwrite): {destination}",
            file=sys.stderr,
        )
        return 2

    destination.parent.mkdir(parents=True, exist_ok=True)

    # ``sqlite3.Connection.backup`` produces a consistent online copy even
    # while another process holds a write lock (WAL-safe).
    src_conn = sqlite3.connect(source)
    try:
        dest_conn = sqlite3.connect(destination)
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
    finally:
        src_conn.close()

    print(f"backup written: {destination}")
    return 0


# ---------------------------------------------------------------------------
# migrate
# ---------------------------------------------------------------------------
def cmd_migrate(args: argparse.Namespace) -> int:
    """Apply pending migrations using the existing migration runner."""

    # Imported lazily so that ``--help`` works even when the migration module
    # has expensive imports.
    from cilly_trading.db.migrations import run_migrations

    target = _resolve_db_path(args.db_path)
    applied = run_migrations(target)
    print(f"migrations applied: {applied} (db={target})")
    return 0


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------
def _iter_candidate_files(path: Path, pattern: str) -> Iterable[Path]:
    if not path.exists():
        return ()
    return sorted(p for p in path.rglob(pattern) if p.is_file())


def cmd_cleanup(args: argparse.Namespace) -> int:
    """Inspect (and optionally delete) artifact files.

    Defaults to a dry run. ``--delete`` is required for any file removal.
    """

    target = Path(args.path)
    pattern = args.pattern

    candidates = list(_iter_candidate_files(target, pattern))
    if not candidates:
        print(f"cleanup: no files matched (path={target}, pattern={pattern!r})")
        return 0

    if not args.delete:
        print(
            f"cleanup (dry-run): {len(candidates)} file(s) would be deleted "
            f"(path={target}, pattern={pattern!r})"
        )
        for path in candidates:
            print(f"  would delete: {path}")
        print("re-run with --delete to actually remove files.")
        return 0

    if not args.confirm:
        print(
            "error: --delete requires --confirm to actually remove files.",
            file=sys.stderr,
        )
        return 2

    deleted = 0
    for path in candidates:
        try:
            path.unlink()
            deleted += 1
        except OSError as exc:  # pragma: no cover - defensive
            print(f"warning: failed to delete {path}: {exc}", file=sys.stderr)
    print(f"cleanup: deleted {deleted} file(s) (path={target}, pattern={pattern!r})")
    return 0


# ---------------------------------------------------------------------------
# argparse wiring
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cilly_trading.cli",
        description=(
            "Bounded maintenance CLI for the Cilly Trading engine. "
            "All commands are local operator tools; no broker, live-trading, "
            "or real-money execution actions are exposed."
        ),
    )
    sub = parser.add_subparsers(dest="command", required=True, metavar="<command>")

    backup = sub.add_parser(
        "backup", help="Create a SQLite backup copy of the engine database."
    )
    backup.add_argument(
        "--db-path",
        dest="db_path",
        default=None,
        help="Source database path (default: cilly_trading.db DEFAULT_DB_PATH).",
    )
    backup.add_argument(
        "--output", "-o", required=True, help="Destination backup file path."
    )
    backup.add_argument(
        "--force",
        action="store_true",
        help="Overwrite destination if it already exists.",
    )
    backup.set_defaults(func=cmd_backup)

    migrate = sub.add_parser(
        "migrate", help="Apply pending SQLite schema migrations (idempotent)."
    )
    migrate.add_argument(
        "--db-path",
        dest="db_path",
        default=None,
        help="Database path (default: cilly_trading.db DEFAULT_DB_PATH).",
    )
    migrate.set_defaults(func=cmd_migrate)

    cleanup = sub.add_parser(
        "cleanup",
        help=(
            "Inspect (and optionally delete) artifact files. "
            "Dry-run by default; requires --delete --confirm to actually remove files."
        ),
    )
    cleanup.add_argument(
        "--path",
        required=True,
        help="Root directory to scan for artifact files.",
    )
    cleanup.add_argument(
        "--pattern",
        default="*",
        help="Glob pattern relative to --path (default: '*').",
    )
    cleanup.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete matched files (still requires --confirm).",
    )
    cleanup.add_argument(
        "--confirm",
        action="store_true",
        help="Required confirmation flag for destructive deletion.",
    )
    cleanup.set_defaults(func=cmd_cleanup)

    return parser


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return int(args.func(args))


if __name__ == "__main__":
    sys.exit(main())

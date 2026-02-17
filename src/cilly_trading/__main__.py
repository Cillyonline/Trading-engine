"""Module entrypoint for cilly_trading CLI."""

from __future__ import annotations

import argparse
from pathlib import Path

from .version import get_version


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m cilly_trading")
    parser.add_argument("--version", action="version", version=get_version())

    subparsers = parser.add_subparsers(dest="command", required=True)

    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("--snapshots", required=True)
    backtest_parser.add_argument("--strategy", required=True)
    backtest_parser.add_argument("--out", required=True)
    backtest_parser.add_argument("--run-id", default="deterministic")
    backtest_parser.add_argument("--strategy-module", action="append", default=None)

    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the package CLI and return process exit code."""

    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "backtest":
        from .cli.backtest_cli import run_backtest

        return run_backtest(
            snapshots_path=Path(args.snapshots),
            strategy_name=args.strategy,
            out_dir=Path(args.out),
            run_id=args.run_id,
            strategy_modules=args.strategy_module,
        )

    parser.print_usage()
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

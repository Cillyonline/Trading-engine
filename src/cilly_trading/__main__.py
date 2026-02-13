"""Module entrypoint for cilly_trading CLI."""

from __future__ import annotations

import argparse

from .version import get_version


def main() -> int:
    """Run the package CLI.

    Returns:
        int: Process exit code.
    """
    parser = argparse.ArgumentParser(prog="cilly_trading")
    parser.add_argument(
        "--version",
        action="store_true",
        help="Print the cilly_trading package version and exit.",
    )
    args = parser.parse_args()

    if args.version:
        print(get_version())
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

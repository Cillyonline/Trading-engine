"""Module entrypoint for cilly_trading CLI."""

from __future__ import annotations

import sys

from .version import get_version


USAGE = "usage: python -m cilly_trading --version"


def main(argv: list[str] | None = None) -> int:
    """Run the package CLI and return process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)

    if args == ["--version"]:
        print(get_version())
        return 0

    if args:
        print("unknown arguments", file=sys.stderr)
    print(USAGE, file=sys.stderr)
    return 2


if __name__ == "__main__":
    raise SystemExit(main())

"""Export the FastAPI OpenAPI schema to a JSON file (issue #1138).

Usage::

    PYTHONPATH=src python scripts/export_openapi.py [--output openapi.json]

This script imports ``api.main:app`` and writes the generated OpenAPI
schema to disk. It does **not** start the API server and does **not**
make any external network calls.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Export the Cilly Trading Engine FastAPI OpenAPI schema to a JSON file."
        )
    )
    parser.add_argument(
        "--output",
        "-o",
        type=Path,
        default=Path("openapi.json"),
        help="Output path for the OpenAPI JSON file (default: ./openapi.json).",
    )
    return parser


def export_openapi(output_path: Path) -> Path:
    """Write the OpenAPI schema for ``api.main:app`` to ``output_path``."""

    # Imported lazily so that ``--help`` works even if the API import path
    # is not configured.
    from api.main import app

    schema = app.openapi()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(schema, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    args = _build_arg_parser().parse_args(argv)
    written = export_openapi(args.output)
    print(f"OpenAPI schema written to {written}")
    return 0


if __name__ == "__main__":
    sys.exit(main())

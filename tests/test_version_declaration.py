"""Tests for package version declaration and exposure."""

from __future__ import annotations

import subprocess
import sys

import cilly_trading
from cilly_trading.version import get_version


def test_package_version_is_non_empty_string() -> None:
    """Assert package-level __version__ is present and non-empty."""
    assert isinstance(cilly_trading.__version__, str)
    assert cilly_trading.__version__.strip() != ""


def test_get_version_matches_package_version() -> None:
    """Assert helper API returns same authoritative package version."""
    assert get_version() == cilly_trading.__version__


def test_module_cli_version_prints_and_exits_zero() -> None:
    """Assert module CLI exposes version and exits successfully."""
    result = subprocess.run(
        [sys.executable, "-m", "cilly_trading", "--version"],
        check=False,
        capture_output=True,
        text=True,
    )

    assert result.returncode == 0
    assert result.stdout.strip() == cilly_trading.__version__

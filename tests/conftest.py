"""Pytest configuration exposing canonical bounded contract-test fixtures.

This module exposes the shared bounded contract-test helpers defined in
``tests.utils.consumer_contract_helpers`` as pytest fixtures so that
suites can opt into the canonical pattern via fixture injection without
direct imports.

The fixtures and helpers are read-only, deterministic, and do not infer
runtime behavior. They do not imply live-trading readiness, broker
execution readiness, or trader-validation evidence.
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import pytest

from tests.utils.consumer_contract_helpers import (
    REPO_ROOT,
    assert_contains_all,
    assert_starts_with,
    read_repo_text,
)


@pytest.fixture(scope="session")
def repo_root() -> Path:
    """Session-scoped fixture exposing the repository root path."""

    return REPO_ROOT


@pytest.fixture(scope="session")
def read_repo_doc() -> Callable[[str], str]:
    """Session-scoped fixture returning the bounded read-only doc reader."""

    return read_repo_text


@pytest.fixture(scope="session")
def doc_assert_contains_all() -> Callable[..., None]:
    """Session-scoped fixture returning the deterministic substring asserter."""

    return assert_contains_all


@pytest.fixture(scope="session")
def doc_assert_starts_with() -> Callable[[str, str], None]:
    """Session-scoped fixture returning the deterministic prefix asserter."""

    return assert_starts_with

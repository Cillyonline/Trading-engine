from __future__ import annotations

import importlib


def test_prometheus_client_runtime_dependency_imports() -> None:
    assert importlib.import_module("prometheus_client") is not None


def test_api_main_runtime_imports() -> None:
    assert importlib.import_module("api.main") is not None

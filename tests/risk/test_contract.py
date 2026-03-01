"""Unit tests for Issue #482 risk contract definitions."""

from __future__ import annotations

import ast
from dataclasses import FrozenInstanceError, is_dataclass
from pathlib import Path
from typing import get_type_hints

import pytest

from engine.risk_framework.contract import (
    RiskEvaluationRequest,
    RiskEvaluationResponse,
    RiskEvaluator,
)


def test_request_and_response_construction() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=10.0,
        account_equity=100000.0,
        current_exposure=25000.0,
    )
    response = RiskEvaluationResponse(
        approved=True,
        reason="within limits",
        adjusted_position_size=None,
        risk_score=0.12,
    )

    assert request.strategy_id == "strategy-a"
    assert request.symbol == "AAPL"
    assert request.proposed_position_size == 10.0
    assert request.account_equity == 100000.0
    assert request.current_exposure == 25000.0

    assert response.approved is True
    assert response.reason == "within limits"
    assert response.adjusted_position_size is None
    assert response.risk_score == 0.12


def test_request_and_response_are_frozen_dataclasses() -> None:
    assert is_dataclass(RiskEvaluationRequest)
    assert RiskEvaluationRequest.__dataclass_params__.frozen is True

    assert is_dataclass(RiskEvaluationResponse)
    assert RiskEvaluationResponse.__dataclass_params__.frozen is True


def test_request_rejects_mutation() -> None:
    request = RiskEvaluationRequest(
        strategy_id="strategy-a",
        symbol="AAPL",
        proposed_position_size=10.0,
        account_equity=100000.0,
        current_exposure=25000.0,
    )

    with pytest.raises(FrozenInstanceError):
        request.symbol = "MSFT"  # type: ignore[misc]


def test_response_rejects_mutation() -> None:
    response = RiskEvaluationResponse(
        approved=False,
        reason="limit exceeded",
        adjusted_position_size=3.0,
        risk_score=0.91,
    )

    with pytest.raises(FrozenInstanceError):
        response.approved = True  # type: ignore[misc]


def test_request_deterministic_equality() -> None:
    payload = dict(
        strategy_id="strategy-a",
        symbol="BTC-USD",
        proposed_position_size=1.5,
        account_equity=50000.0,
        current_exposure=10000.0,
    )

    left = RiskEvaluationRequest(**payload)
    right = RiskEvaluationRequest(**payload)

    assert left == right
    assert hash(left) == hash(right)
    assert repr(left) == repr(right)


def test_contract_uses_no_forbidden_execution_or_orchestrator_imports() -> None:
    source = Path("engine/risk_framework/contract.py").read_text(encoding="utf-8")
    tree = ast.parse(source)

    imported_modules: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_modules.update(alias.name for alias in node.names)
        if isinstance(node, ast.ImportFrom) and node.module:
            imported_modules.add(node.module)

    forbidden_prefixes = ("engine.execution", "engine.orchestrator")

    assert not any(
        module.startswith(prefix)
        for module in imported_modules
        for prefix in forbidden_prefixes
    )


def test_protocol_evaluate_signature() -> None:
    annotations = get_type_hints(RiskEvaluator.evaluate)

    assert annotations["request"] is RiskEvaluationRequest
    assert annotations["return"] is RiskEvaluationResponse

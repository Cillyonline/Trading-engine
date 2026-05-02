"""Tests for CircuitBreaker."""

from __future__ import annotations

import time

import pytest

from cilly_trading.engine.circuit_breaker import CircuitBreaker, CircuitOpenError


def _ok() -> str:
    return "ok"


def _fail() -> None:
    raise RuntimeError("boom")


def test_closed_state_passes_through() -> None:
    cb = CircuitBreaker(name="test")
    assert cb.call(_ok) == "ok"
    assert cb.state == "closed"


def test_opens_after_max_failures() -> None:
    cb = CircuitBreaker(name="test", max_failures=2, cooldown_s=60.0)
    for _ in range(2):
        with pytest.raises(RuntimeError):
            cb.call(_fail)
    assert cb.state == "open"


def test_open_circuit_raises_circuit_open_error() -> None:
    cb = CircuitBreaker(name="test", max_failures=1, cooldown_s=60.0)
    with pytest.raises(RuntimeError):
        cb.call(_fail)
    with pytest.raises(CircuitOpenError):
        cb.call(_ok)


def test_half_open_after_cooldown_allows_probe() -> None:
    cb = CircuitBreaker(name="test", max_failures=1, cooldown_s=0.01)
    with pytest.raises(RuntimeError):
        cb.call(_fail)
    time.sleep(0.02)
    assert cb.state == "half-open"
    assert cb.call(_ok) == "ok"
    assert cb.state == "closed"


def test_reset_restores_closed_state() -> None:
    cb = CircuitBreaker(name="test", max_failures=1, cooldown_s=60.0)
    with pytest.raises(RuntimeError):
        cb.call(_fail)
    cb.reset()
    assert cb.state == "closed"
    assert cb.call(_ok) == "ok"


def test_timeout_opens_circuit() -> None:
    cb = CircuitBreaker(name="test", max_failures=2, cooldown_s=60.0, call_timeout_s=0.05)

    def _slow() -> None:
        time.sleep(5)

    for _ in range(2):
        with pytest.raises(TimeoutError):
            cb.call(_slow)

    assert cb.state == "open"


def test_success_resets_failure_count() -> None:
    cb = CircuitBreaker(name="test", max_failures=3, cooldown_s=60.0)
    with pytest.raises(RuntimeError):
        cb.call(_fail)
    cb.call(_ok)
    assert cb.state == "closed"
    # One more failure should not open the circuit (counter was reset)
    with pytest.raises(RuntimeError):
        cb.call(_fail)
    assert cb.state == "closed"

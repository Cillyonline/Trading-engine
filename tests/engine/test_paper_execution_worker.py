"""Targeted tests for the bounded paper execution worker (OPS-P52).

Acceptance criteria verified:
    AC1: Eligible signals are converted into bounded paper execution state deterministically.
    AC2: Ineligible signals are skipped or rejected with explicit outcome codes.
    AC3: Restart behavior preserves authoritative state (idempotent persistence).
    AC4: Execution state is aligned with the canonical paper-state authority.
    AC5: Bounded execution (score, duplicate-entry, cooldown, exposure limits).
"""

from __future__ import annotations

from decimal import Decimal
from pathlib import Path

import pytest

from cilly_trading.engine.paper_execution_risk_profile import PaperExecutionRiskProfile
from cilly_trading.engine.paper_execution_worker import (
    BoundedPaperExecutionWorker,
    COOLDOWN_HOURS,
    DEFAULT_PAPER_ENTRY_PRICE,
    DEFAULT_PAPER_QUANTITY,
    MAX_RISK_PER_TRADE_PCT,
    MAX_TRADE_RISK_PCT,
    MAX_CONCURRENT_POSITIONS,
    MIN_TRADE_RISK_PCT,
    NOTIONAL_ROUNDING_QUANTUM,
    MAX_POSITION_PCT,
    MAX_TOTAL_EXPOSURE_PCT,
    MIN_SCORE_THRESHOLD,
    SignalEvaluationResult,
    _compute_paper_order_id,
    _compute_paper_trade_id,
    _direction_to_order_side,
    _resolve_signal_id,
)
from cilly_trading.models import Signal
from cilly_trading.repositories.execution_core_sqlite import SqliteCanonicalExecutionRepository


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def repo(tmp_path: Path) -> SqliteCanonicalExecutionRepository:
    return SqliteCanonicalExecutionRepository(db_path=tmp_path / "paper_worker_test.db")


@pytest.fixture
def worker(repo: SqliteCanonicalExecutionRepository) -> BoundedPaperExecutionWorker:
    return BoundedPaperExecutionWorker(repository=repo)


def _make_signal(
    *,
    symbol: str = "AAPL",
    strategy: str = "rsi2",
    direction: str = "long",
    score: float = 75.0,
    timestamp: str = "2024-01-15T10:00:00Z",
    stage: str = "setup",
    trade_risk_pct: float = 0.20,
    signal_id: str | None = None,
) -> Signal:
    sig: Signal = {
        "symbol": symbol,
        "strategy": strategy,
        "direction": direction,  # type: ignore[typeddict-item]
        "score": score,
        "timestamp": timestamp,
        "stage": stage,  # type: ignore[typeddict-item]
        "trade_risk_pct": trade_risk_pct,
    }
    if signal_id is not None:
        sig["signal_id"] = signal_id
    return sig


# ---------------------------------------------------------------------------
# Policy constant sanity checks
# ---------------------------------------------------------------------------


def test_policy_constants_match_documented_defaults() -> None:
    """AC5: policy constants match the values declared in the policy doc."""
    assert MIN_SCORE_THRESHOLD == 60.0
    assert MAX_POSITION_PCT == Decimal("0.10")
    assert MAX_RISK_PER_TRADE_PCT == Decimal("0.01")
    assert MIN_TRADE_RISK_PCT == Decimal("0.005")
    assert MAX_TRADE_RISK_PCT == Decimal("0.20")
    assert NOTIONAL_ROUNDING_QUANTUM == Decimal("0.01")
    assert MAX_TOTAL_EXPOSURE_PCT == Decimal("0.80")
    assert MAX_CONCURRENT_POSITIONS == 10
    assert COOLDOWN_HOURS == 24
    assert DEFAULT_PAPER_QUANTITY == Decimal("1")
    assert DEFAULT_PAPER_ENTRY_PRICE == Decimal("100")


def test_direction_to_order_side_long() -> None:
    """long direction maps to BUY side."""
    assert _direction_to_order_side("long") == "BUY"


def test_direction_to_order_side_unknown_raises() -> None:
    """Unknown direction raises ValueError."""
    import pytest
    with pytest.raises(ValueError, match="unknown direction"):
        _direction_to_order_side("sideways")


# ---------------------------------------------------------------------------
# AC2: Ineligible signals — reject:invalid_signal_fields
# ---------------------------------------------------------------------------


def test_missing_symbol_returns_reject(worker: BoundedPaperExecutionWorker) -> None:
    signal: Signal = {
        "strategy": "rsi2",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2024-01-15T10:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
    }
    result = worker.process_signal(signal)
    assert result.outcome == "reject:invalid_signal_fields"
    assert result.order_id is None
    assert result.trade_id is None


def test_missing_strategy_returns_reject(worker: BoundedPaperExecutionWorker) -> None:
    signal: Signal = {
        "symbol": "AAPL",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2024-01-15T10:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
    }
    result = worker.process_signal(signal)
    assert result.outcome == "reject:invalid_signal_fields"


def test_score_out_of_range_returns_reject(worker: BoundedPaperExecutionWorker) -> None:
    result = worker.process_signal(_make_signal(score=150.0))
    assert result.outcome == "reject:invalid_signal_fields"
    assert "out of range" in (result.reason or "")


def test_unparseable_timestamp_returns_reject(worker: BoundedPaperExecutionWorker) -> None:
    sig = _make_signal()
    sig["timestamp"] = "not-a-timestamp"
    result = worker.process_signal(sig)
    assert result.outcome == "reject:invalid_signal_fields"


# ---------------------------------------------------------------------------
# AC2: Ineligible signals — skip:score_below_threshold
# ---------------------------------------------------------------------------


def test_score_below_threshold_is_skipped(worker: BoundedPaperExecutionWorker) -> None:
    result = worker.process_signal(_make_signal(score=59.0))
    assert result.outcome == "skip:score_below_threshold"
    assert result.order_id is None


def test_score_exactly_at_threshold_is_eligible(
    worker: BoundedPaperExecutionWorker,
) -> None:
    result = worker.process_signal(_make_signal(score=60.0))
    assert result.outcome == "eligible"


def test_score_above_threshold_is_eligible(worker: BoundedPaperExecutionWorker) -> None:
    result = worker.process_signal(_make_signal(score=80.0))
    assert result.outcome == "eligible"


def test_midrange_score_is_not_rejected_as_invalid_field(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Score values in 0..100 must not be rejected by field validation."""
    result = worker.process_signal(_make_signal(score=46.676762456528515))
    assert result.outcome == "skip:score_below_threshold"
    assert result.reason is not None
    assert "min_score_threshold" in result.reason


# ---------------------------------------------------------------------------
# AC1: Eligible signal → canonical paper entities persisted
# ---------------------------------------------------------------------------


def test_eligible_signal_creates_order_in_repository(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC1: eligible signal persists an Order to the canonical repository."""
    signal = _make_signal(signal_id="sig-001")
    result = worker.process_signal(signal)

    assert result.outcome == "eligible"
    assert result.order_id is not None

    order = repo.get_order(result.order_id)
    assert order is not None
    assert order.symbol == "AAPL"
    assert order.strategy_id == "rsi2"
    assert order.side == "BUY"  # "long" direction → BUY side
    assert order.status == "filled"
    assert order.quantity > Decimal("0")
    assert order.filled_quantity == order.quantity


def test_eligible_signal_creates_execution_events_in_repository(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC1: eligible signal persists ExecutionEvents (created, submitted, filled)."""
    signal = _make_signal(signal_id="sig-002")
    result = worker.process_signal(signal)

    assert result.order_id is not None
    events = repo.list_execution_events(order_id=result.order_id)

    event_types = {e.event_type for e in events}
    assert "created" in event_types
    assert "submitted" in event_types
    assert "filled" in event_types


def test_eligible_signal_creates_open_trade_in_repository(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC1: eligible signal persists an open Trade to the canonical repository."""
    signal = _make_signal(signal_id="sig-003")
    result = worker.process_signal(signal)

    assert result.trade_id is not None
    trade = repo.get_trade(result.trade_id)
    assert trade is not None
    assert trade.status == "open"
    assert trade.direction == "long"
    assert trade.symbol == "AAPL"
    assert trade.strategy_id == "rsi2"
    assert trade.quantity_opened > Decimal("0")
    assert trade.average_entry_price == DEFAULT_PAPER_ENTRY_PRICE


def test_eligible_signal_result_contains_signal_and_entity_ids(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """AC1: result for an eligible signal includes signal_id, order_id, trade_id."""
    signal = _make_signal(signal_id="sig-004")
    result = worker.process_signal(signal)

    assert result.outcome == "eligible"
    assert result.signal_id == "sig-004"
    assert result.order_id is not None
    assert result.trade_id is not None
    assert result.decision_inputs is not None
    assert result.decision_inputs["max_risk_per_trade_pct"] == "0.01"


# ---------------------------------------------------------------------------
# AC1: Determinism — same signal always produces the same entity IDs
# ---------------------------------------------------------------------------


def test_entity_ids_are_deterministic_across_runs(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC1: entity IDs are computed deterministically from signal identity."""
    signal = _make_signal(signal_id="sig-det-001")
    signal_id = _resolve_signal_id(signal)

    expected_order_id = _compute_paper_order_id(signal_id)
    expected_trade_id = _compute_paper_trade_id(signal_id)

    worker = BoundedPaperExecutionWorker(repository=repo)
    result = worker.process_signal(signal)

    assert result.order_id == expected_order_id
    assert result.trade_id == expected_trade_id


def test_same_signal_id_produces_same_order_and_trade_ids() -> None:
    """AC1: ID computation is a pure deterministic function of the signal ID."""
    sid = "test-signal-determinism"
    assert _compute_paper_order_id(sid) == _compute_paper_order_id(sid)
    assert _compute_paper_trade_id(sid) == _compute_paper_trade_id(sid)


def test_different_signal_ids_produce_different_entity_ids() -> None:
    """AC1: distinct signals produce distinct entity IDs (no collision)."""
    order_a = _compute_paper_order_id("signal-a")
    order_b = _compute_paper_order_id("signal-b")
    assert order_a != order_b


# ---------------------------------------------------------------------------
# AC3: Restart safety — second run with same signal skips (duplicate-entry)
# ---------------------------------------------------------------------------


def test_restart_second_run_same_signal_is_skipped(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC3: re-processing the same signal after restart produces skip:duplicate_entry."""
    signal = _make_signal(signal_id="sig-restart-001")

    worker_first = BoundedPaperExecutionWorker(repository=repo)
    result_first = worker_first.process_signal(signal)
    assert result_first.outcome == "eligible"

    # Simulate restart: new worker instance, same repo (persisted state)
    worker_second = BoundedPaperExecutionWorker(repository=repo)
    result_second = worker_second.process_signal(signal)
    assert result_second.outcome == "skip:duplicate_entry"


def test_restart_state_in_repository_is_unchanged(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC3: after restart and re-run, the repository state is identical."""
    signal = _make_signal(signal_id="sig-restart-002")

    worker = BoundedPaperExecutionWorker(repository=repo)
    result = worker.process_signal(signal)

    orders_before = repo.list_orders()
    trades_before = repo.list_trades()
    events_before = repo.list_execution_events()

    # Re-run with same repo (simulated restart) — state must not change
    worker2 = BoundedPaperExecutionWorker(repository=repo)
    worker2.process_signal(signal)  # skip:duplicate_entry

    assert repo.list_orders() == orders_before
    assert repo.list_trades() == trades_before
    assert repo.list_execution_events() == events_before


# ---------------------------------------------------------------------------
# AC2 / AC5: Duplicate-entry skip
# ---------------------------------------------------------------------------


def test_duplicate_entry_skip_for_same_symbol_strategy_direction(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC2: second signal for same (symbol, strategy, direction) → skip:duplicate_entry."""
    sig1 = _make_signal(signal_id="sig-dup-001", timestamp="2024-01-15T10:00:00Z")
    sig2 = _make_signal(signal_id="sig-dup-002", timestamp="2024-01-16T12:00:00Z")

    worker = BoundedPaperExecutionWorker(repository=repo)
    r1 = worker.process_signal(sig1)
    assert r1.outcome == "eligible"

    r2 = worker.process_signal(sig2)
    assert r2.outcome == "skip:duplicate_entry"


def test_no_duplicate_entry_for_different_symbols(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC2: different symbols are independent — no duplicate-entry skip."""
    sig_aapl = _make_signal(
        symbol="AAPL",
        signal_id="sig-sym-001",
        timestamp="2024-01-15T10:00:00Z",
    )
    sig_msft = _make_signal(
        symbol="MSFT",
        signal_id="sig-sym-002",
        timestamp="2024-01-15T10:00:00Z",
    )

    worker = BoundedPaperExecutionWorker(repository=repo)
    r1 = worker.process_signal(sig_aapl)
    r2 = worker.process_signal(sig_msft)
    assert r1.outcome == "eligible"
    assert r2.outcome == "eligible"


# ---------------------------------------------------------------------------
# AC2 / AC5: Cooldown skip
# ---------------------------------------------------------------------------


def test_cooldown_skip_within_24h(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC2: signal within 24h cooldown window → skip:cooldown_active."""
    # First entry succeeds
    sig1 = _make_signal(
        symbol="TSLA",
        strategy="turtle",
        signal_id="sig-cool-001",
        timestamp="2024-02-01T10:00:00Z",
    )
    worker = BoundedPaperExecutionWorker(repository=repo)
    r1 = worker.process_signal(sig1)
    assert r1.outcome == "eligible"

    # Close the open trade to clear duplicate-entry block
    trade = repo.get_trade(r1.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    from cilly_trading.models import Trade
    closed_trade = Trade.model_validate(
        {
            **trade.model_dump(mode="python"),
            "status": "closed",
            "quantity_closed": trade.quantity_opened,
            "closed_at": "2024-02-01T11:00:00Z",
            "average_exit_price": Decimal("100"),
            "realized_pnl": Decimal("0"),
            "exposure_notional": Decimal("0"),
        }
    )
    repo.save_trade(closed_trade)

    # Second signal for same pair within 24h → cooldown active
    sig2 = _make_signal(
        symbol="TSLA",
        strategy="turtle",
        signal_id="sig-cool-002",
        timestamp="2024-02-01T20:00:00Z",  # 10h later — within 24h
    )
    r2 = worker.process_signal(sig2)
    assert r2.outcome == "skip:cooldown_active"


def test_cooldown_cleared_after_24h(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC5: signal after 24h cooldown window is eligible."""
    sig1 = _make_signal(
        symbol="TSLA",
        strategy="turtle",
        signal_id="sig-cool-003",
        timestamp="2024-02-01T10:00:00Z",
    )
    worker = BoundedPaperExecutionWorker(repository=repo)
    r1 = worker.process_signal(sig1)
    assert r1.outcome == "eligible"

    # Close the open trade
    trade = repo.get_trade(r1.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    from cilly_trading.models import Trade
    closed_trade = Trade.model_validate(
        {
            **trade.model_dump(mode="python"),
            "status": "closed",
            "quantity_closed": trade.quantity_opened,
            "closed_at": "2024-02-02T09:00:00Z",
            "average_exit_price": Decimal("100"),
            "realized_pnl": Decimal("0"),
            "exposure_notional": Decimal("0"),
        }
    )
    repo.save_trade(closed_trade)

    # 25h later — cooldown elapsed
    sig2 = _make_signal(
        symbol="TSLA",
        strategy="turtle",
        signal_id="sig-cool-004",
        timestamp="2024-02-02T11:00:00Z",  # 25h after sig1
    )
    r2 = worker.process_signal(sig2)
    assert r2.outcome == "eligible"


# ---------------------------------------------------------------------------
# AC5: Exposure and position-limit checks
# ---------------------------------------------------------------------------


def test_concurrent_position_limit_enforced(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC5: exceeding concurrent position limit → reject:concurrent_position_limit_exceeded."""
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(max_concurrent_positions=2),
    )

    symbols = ["SYM1", "SYM2", "SYM3"]
    results = []
    for i, sym in enumerate(symbols):
        sig = _make_signal(
            symbol=sym,
            signal_id=f"sig-conc-{i:03d}",
            timestamp="2024-03-01T10:00:00Z",
        )
        results.append(worker.process_signal(sig))

    assert results[0].outcome == "eligible"
    assert results[1].outcome == "eligible"
    assert results[2].outcome == "reject:concurrent_position_limit_exceeded"


def test_total_exposure_limit_enforced(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC5: exceeding total exposure limit → reject:total_exposure_exceeds_limit."""
    # equity=1000, max_total_exposure_pct=0.80 → max_exposure=800
    # DEFAULT_PAPER_ENTRY_PRICE=100 → each position notional=100
    # after 8 positions exposure=800 → 9th should reject
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("1000"),
            max_risk_per_trade_pct=Decimal("0.10"),
            min_trade_risk_pct=Decimal("0.10"),
            max_trade_risk_pct=Decimal("1.00"),
            max_total_exposure_pct=Decimal("0.80"),
            max_concurrent_positions=20,
        ),
    )

    eligible_count = 0
    reject_count = 0
    for i in range(10):
        sig = _make_signal(
            symbol=f"SYM{i:02d}",
            signal_id=f"sig-exp-{i:03d}",
            timestamp="2024-03-01T10:00:00Z",
            trade_risk_pct=1.0,
        )
        result = worker.process_signal(sig)
        if result.outcome == "eligible":
            eligible_count += 1
        elif result.outcome == "reject:total_exposure_exceeds_limit":
            reject_count += 1

    assert eligible_count == 8
    assert reject_count == 2


def test_max_risk_per_trade_limit_enforced(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC5: proposed position exceeding per-position cap → reject:position_size_exceeds_limit."""
    # equity=500, max_position_pct=0.10 → max_position_notional=50
    # DEFAULT_PAPER_ENTRY_PRICE=100 → proposed_notional=100 > 50 → reject
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            account_equity=Decimal("90"),
            max_risk_per_trade_pct=Decimal("0.0001"),
            min_trade_risk_pct=Decimal("0.005"),
            max_trade_risk_pct=Decimal("0.20"),
        ),
    )
    result = worker.process_signal(_make_signal(signal_id="sig-pos-001", trade_risk_pct=0.20))
    assert result.outcome == "reject:max_risk_per_trade_exceeded"


def test_missing_trade_risk_input_is_rejected_fail_closed(
    worker: BoundedPaperExecutionWorker,
) -> None:
    signal = _make_signal(signal_id="sig-missing-trade-risk")
    del signal["trade_risk_pct"]
    result = worker.process_signal(signal)
    assert result.outcome == "reject:missing_trade_risk_input"


def test_invalid_trade_risk_input_is_rejected_fail_closed(
    worker: BoundedPaperExecutionWorker,
) -> None:
    signal = _make_signal(signal_id="sig-invalid-trade-risk")
    signal["trade_risk_pct"] = -0.1
    result = worker.process_signal(signal)
    assert result.outcome == "reject:invalid_trade_risk_input"


def test_identical_inputs_produce_identical_reason_codes_and_sizing_payloads(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    worker_a = BoundedPaperExecutionWorker(repository=repo)
    worker_b = BoundedPaperExecutionWorker(repository=repo)
    signal = _make_signal(signal_id="sig-deterministic-reject")
    del signal["trade_risk_pct"]

    result_a = worker_a.process_signal(signal)
    result_b = worker_b.process_signal(signal)

    assert result_a.outcome == "reject:missing_trade_risk_input"
    assert result_b.outcome == "reject:missing_trade_risk_input"
    assert result_a.reason == result_b.reason
    assert result_a.decision_inputs == result_b.decision_inputs


# ---------------------------------------------------------------------------
# AC4: Canonical authority alignment
# ---------------------------------------------------------------------------


def test_order_and_trade_reference_same_position_id(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: order.position_id and trade.position_id are consistent."""
    result = worker.process_signal(_make_signal(signal_id="sig-auth-001"))
    order = repo.get_order(result.order_id)  # type: ignore[arg-type]
    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert order is not None and trade is not None
    assert order.position_id == trade.position_id


def test_order_and_trade_reference_same_trade_id(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: order.trade_id matches trade.trade_id."""
    result = worker.process_signal(_make_signal(signal_id="sig-auth-002"))
    order = repo.get_order(result.order_id)  # type: ignore[arg-type]
    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert order is not None and trade is not None
    assert order.trade_id == trade.trade_id


def test_execution_events_reference_correct_order(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: all execution events reference the canonical order ID."""
    result = worker.process_signal(_make_signal(signal_id="sig-auth-003"))
    events = repo.list_execution_events(order_id=result.order_id)
    assert all(e.order_id == result.order_id for e in events)


def test_trade_opening_order_ids_includes_order(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: trade.opening_order_ids contains the canonical order ID."""
    result = worker.process_signal(_make_signal(signal_id="sig-auth-004"))
    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    assert result.order_id in trade.opening_order_ids


def test_trade_execution_event_ids_includes_fill_event(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: trade.execution_event_ids contains the fill event."""
    result = worker.process_signal(_make_signal(signal_id="sig-auth-005"))
    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    events = repo.list_execution_events(order_id=result.order_id)
    filled_events = [e for e in events if e.event_type == "filled"]
    assert len(filled_events) == 1
    assert filled_events[0].event_id in trade.execution_event_ids


def test_state_authority_is_canonical_repository(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC4: all state is derived from the canonical execution repository."""
    from cilly_trading.portfolio.paper_state_authority import (
        PAPER_STATE_AUTHORITY_ID,
        assert_state_authority,
    )

    result = worker.process_signal(_make_signal(signal_id="sig-auth-006"))

    orders = repo.list_orders()
    events = repo.list_execution_events()
    trades = repo.list_trades()

    assertion = assert_state_authority(
        orders=orders,
        execution_events=events,
        trades=trades,
    )

    assert assertion.authority_id == PAPER_STATE_AUTHORITY_ID
    assert assertion.restart_safe is True
    assert assertion.canonical_orders >= 1
    assert assertion.canonical_trades >= 1


# ---------------------------------------------------------------------------
# AC1 / AC5: Batch processing
# ---------------------------------------------------------------------------


def test_batch_processes_all_signals_with_individual_outcomes(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """AC1: batch returns one result per signal."""
    signals = [
        _make_signal(signal_id=f"sig-batch-{i:03d}", symbol=f"B{i:02d}")
        for i in range(3)
    ]
    results = worker.process_batch(signals)
    assert len(results) == 3
    assert all(isinstance(r, SignalEvaluationResult) for r in results)


def test_batch_eligible_signals_each_create_distinct_entities(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """AC1: batch of distinct eligible signals each create distinct entities."""
    signals = [
        _make_signal(signal_id=f"sig-dist-{i:03d}", symbol=f"D{i:02d}")
        for i in range(3)
    ]
    results = worker.process_batch(signals)

    eligible = [r for r in results if r.outcome == "eligible"]
    assert len(eligible) == 3

    order_ids = {r.order_id for r in eligible}
    trade_ids = {r.trade_id for r in eligible}
    assert len(order_ids) == 3
    assert len(trade_ids) == 3


def test_batch_skips_ineligible_and_processes_eligible(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """AC1+AC2: mixed batch — eligible and ineligible signals handled independently."""
    signals = [
        _make_signal(signal_id="sig-mix-001", symbol="OK1", score=80.0),
        _make_signal(signal_id="sig-mix-002", symbol="LOW", score=30.0),  # below threshold
        _make_signal(signal_id="sig-mix-003", symbol="OK2", score=90.0),
    ]
    results = worker.process_batch(signals)

    assert results[0].outcome == "eligible"
    assert results[1].outcome == "skip:score_below_threshold"
    assert results[2].outcome == "eligible"


# ---------------------------------------------------------------------------
# Non-live boundary: no broker calls, no live state
# ---------------------------------------------------------------------------


def test_worker_does_not_touch_live_attributes(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """Verify the worker only uses the canonical paper repository (no live attributes)."""
    # The worker should not have broker, live_order, or external_api attributes
    assert not hasattr(worker, "broker")
    assert not hasattr(worker, "live_order_router")
    assert not hasattr(worker, "external_api")

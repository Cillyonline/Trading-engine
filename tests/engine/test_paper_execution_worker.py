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
    # Long entries pay slippage: fill_price = entry_price * (1 + slippage_rate)
    expected_fill = DEFAULT_PAPER_ENTRY_PRICE * (
        Decimal("1") + worker.risk_profile.slippage_rate
    )
    assert trade.average_entry_price == expected_fill.quantize(Decimal("0.0001"))


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
            commission_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
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


# ---------------------------------------------------------------------------
# #1143: Risk-based position sizing — derive trade_risk_pct from stop_loss
# ---------------------------------------------------------------------------


def _make_signal_with_stop_loss(
    *,
    entry_low: float = 95.0,
    entry_high: float = 105.0,
    stop_loss: float = 95.0,
    signal_id: str = "sig-stop-loss-001",
) -> Signal:
    """Build a signal with stop_loss but no explicit trade_risk_pct."""
    sig: Signal = {
        "symbol": "AAPL",
        "strategy": "rsi2",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 75.0,
        "timestamp": "2024-01-15T10:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "stop_loss": stop_loss,
        "entry_zone": {
            "from_": entry_low,
            "to": entry_high,
        },
        "signal_id": signal_id,
    }
    return sig


def test_signal_with_stop_loss_only_is_eligible(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """A signal carrying stop_loss but no trade_risk_pct must size deterministically."""
    signal = _make_signal_with_stop_loss(
        entry_low=95.0,
        entry_high=105.0,
        stop_loss=95.0,
    )
    result = worker.process_signal(signal)
    assert result.outcome == "eligible", result.reason


def test_signal_with_stop_loss_derives_trade_risk_pct(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """trade_risk_pct = |entry - stop| / entry; with entry=100, stop=95 -> 0.05."""
    signal = _make_signal_with_stop_loss(
        entry_low=95.0,
        entry_high=105.0,
        stop_loss=95.0,
    )
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"
    assert result.decision_inputs is not None
    assert Decimal(result.decision_inputs["trade_risk_pct"]) == Decimal("0.05")


def test_signal_with_explicit_trade_risk_pct_overrides_stop_loss(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Explicit trade_risk_pct on the signal wins over stop-loss derivation."""
    signal = _make_signal_with_stop_loss(
        entry_low=95.0,
        entry_high=105.0,
        stop_loss=95.0,
        signal_id="sig-explicit-wins",
    )
    signal["trade_risk_pct"] = 0.10
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"
    assert result.decision_inputs is not None
    assert Decimal(result.decision_inputs["trade_risk_pct"]) == Decimal("0.10")


def test_signal_with_invalid_stop_loss_is_rejected(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Stop-loss <= 0 fails closed without falling back to default sizing."""
    signal = _make_signal_with_stop_loss(stop_loss=-1.0)
    result = worker.process_signal(signal)
    assert result.outcome == "reject:invalid_trade_risk_input"


def test_signal_with_stop_loss_equal_to_entry_is_rejected(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Stop at entry would imply 0 risk distance and infinite size; reject explicitly."""
    signal = _make_signal_with_stop_loss(
        entry_low=100.0,
        entry_high=100.0,
        stop_loss=100.0,
    )
    result = worker.process_signal(signal)
    assert result.outcome == "reject:invalid_trade_risk_input"


def test_signal_position_size_scales_inversely_with_stop_distance(
    tmp_path: Path,
) -> None:
    """Tighter stops produce larger positions for the same risk budget."""
    repo_a = SqliteCanonicalExecutionRepository(db_path=tmp_path / "tight.db")
    worker_a = BoundedPaperExecutionWorker(repository=repo_a)
    sig_tight = _make_signal_with_stop_loss(
        entry_low=98.0,
        entry_high=102.0,
        stop_loss=98.0,
        signal_id="sig-tight",
    )
    result_tight = worker_a.process_signal(sig_tight)

    repo_b = SqliteCanonicalExecutionRepository(db_path=tmp_path / "wide.db")
    worker_b = BoundedPaperExecutionWorker(repository=repo_b)
    sig_wide = _make_signal_with_stop_loss(
        entry_low=90.0,
        entry_high=110.0,
        stop_loss=90.0,
        signal_id="sig-wide",
    )
    result_wide = worker_b.process_signal(sig_wide)

    assert result_tight.outcome == "eligible"
    assert result_wide.outcome == "eligible"

    tight_notional = Decimal(result_tight.decision_inputs["proposed_position_notional"])  # type: ignore[index]
    wide_notional = Decimal(result_wide.decision_inputs["proposed_position_notional"])  # type: ignore[index]
    assert tight_notional > wide_notional


# ---------------------------------------------------------------------------
# #1141: Commission and slippage applied at fill time
# ---------------------------------------------------------------------------


def test_long_entry_pays_slippage_above_reference_price(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """A long entry fills above the entry-zone midpoint by exactly slippage_rate."""
    signal = _make_signal(signal_id="sig-slip-long", direction="long")
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"

    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    expected_fill = DEFAULT_PAPER_ENTRY_PRICE * (
        Decimal("1") + worker.risk_profile.slippage_rate
    )
    assert trade.average_entry_price == expected_fill.quantize(Decimal("0.0001"))


def test_apply_slippage_helper_handles_long_and_short(
) -> None:
    """The _apply_slippage helper adjusts price in the trade direction."""
    from cilly_trading.engine.paper_execution_worker import _apply_slippage

    long_fill = _apply_slippage(
        reference_price=Decimal("100"),
        direction="long",
        slippage_rate=Decimal("0.001"),
    )
    short_fill = _apply_slippage(
        reference_price=Decimal("100"),
        direction="short",
        slippage_rate=Decimal("0.001"),
    )
    assert long_fill == Decimal("100.1000")
    assert short_fill == Decimal("99.9000")


def test_filled_event_records_non_zero_commission(
    worker: BoundedPaperExecutionWorker,
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """The filled execution event carries the commission charge for the trade."""
    signal = _make_signal(signal_id="sig-commission")
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"

    events = repo.list_execution_events(order_id=result.order_id)
    fill_events = [event for event in events if event.event_type == "filled"]
    assert len(fill_events) == 1
    fill_event = fill_events[0]
    assert fill_event.commission is not None
    assert fill_event.commission > Decimal("0")
    expected_commission = (
        fill_event.execution_quantity
        * fill_event.execution_price
        * worker.risk_profile.commission_rate
    ).quantize(Decimal("0.0001"))
    assert fill_event.commission == expected_commission


def test_zero_cost_profile_preserves_legacy_fill_behaviour(
    repo: SqliteCanonicalExecutionRepository,
) -> None:
    """Setting commission_rate=0 and slippage_rate=0 reproduces pre-#1141 behaviour."""
    worker = BoundedPaperExecutionWorker(
        repository=repo,
        risk_profile=PaperExecutionRiskProfile(
            commission_rate=Decimal("0"),
            slippage_rate=Decimal("0"),
        ),
    )
    signal = _make_signal(signal_id="sig-zero-cost")
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"

    trade = repo.get_trade(result.trade_id)  # type: ignore[arg-type]
    assert trade is not None
    assert trade.average_entry_price == DEFAULT_PAPER_ENTRY_PRICE


# ---------------------------------------------------------------------------
# #1144: Entry-bar fill validation — only fill when bar reaches entry zone
# ---------------------------------------------------------------------------


def _make_signal_with_entry_zone(
    *,
    entry_low: float = 95.0,
    entry_high: float = 105.0,
    signal_id: str = "sig-entry-zone-001",
    timestamp: str = "2024-01-15T10:00:00Z",
) -> Signal:
    return {
        "symbol": "AAPL",
        "strategy": "rsi2",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 75.0,
        "timestamp": timestamp,
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "entry_zone": {"from_": entry_low, "to": entry_high},
        "signal_id": signal_id,
    }


def test_entry_bar_intersecting_zone_is_eligible(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Bar that crosses the zone produces a normal eligible fill."""
    from cilly_trading.engine.paper_execution_worker import EntryBar

    signal = _make_signal_with_entry_zone()
    bar = EntryBar(high=Decimal("106"), low=Decimal("94"))
    result = worker.process_signal(signal, entry_bar=bar)
    assert result.outcome == "eligible", result.reason


def test_entry_bar_above_zone_skips_with_no_fill(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Gap-up bar entirely above the zone never reaches the entry — no fill."""
    from cilly_trading.engine.paper_execution_worker import EntryBar

    signal = _make_signal_with_entry_zone()
    bar = EntryBar(high=Decimal("110"), low=Decimal("106"))
    result = worker.process_signal(signal, entry_bar=bar)
    assert result.outcome == "skip:entry_zone_not_reached"


def test_entry_bar_below_zone_skips_with_no_fill(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Gap-down bar entirely below the zone never reaches the entry — no fill."""
    from cilly_trading.engine.paper_execution_worker import EntryBar

    signal = _make_signal_with_entry_zone()
    bar = EntryBar(high=Decimal("90"), low=Decimal("85"))
    result = worker.process_signal(signal, entry_bar=bar)
    assert result.outcome == "skip:entry_zone_not_reached"


def test_entry_bar_touching_zone_boundary_is_eligible(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Bar low exactly at zone_high is treated as a fill (boundary inclusive)."""
    from cilly_trading.engine.paper_execution_worker import EntryBar

    signal = _make_signal_with_entry_zone()
    bar = EntryBar(high=Decimal("110"), low=Decimal("105"))
    result = worker.process_signal(signal, entry_bar=bar)
    assert result.outcome == "eligible"


def test_no_entry_bar_supplied_keeps_legacy_behaviour(
    worker: BoundedPaperExecutionWorker,
) -> None:
    """Callers without bar context skip the new check — backwards compatible."""
    signal = _make_signal_with_entry_zone()
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"


def test_bar_intersects_entry_zone_helper_is_pure() -> None:
    """The exposed helper returns booleans for any input pair."""
    from cilly_trading.engine.paper_execution_worker import bar_intersects_entry_zone

    assert bar_intersects_entry_zone(
        bar_low=Decimal("95"),
        bar_high=Decimal("105"),
        zone_low=Decimal("96"),
        zone_high=Decimal("104"),
    )
    assert not bar_intersects_entry_zone(
        bar_low=Decimal("110"),
        bar_high=Decimal("115"),
        zone_low=Decimal("95"),
        zone_high=Decimal("105"),
    )


# ---------------------------------------------------------------------------
# #1142: Stop-loss breach evaluation helper
# ---------------------------------------------------------------------------


def test_long_stop_loss_breached_when_bar_low_touches_stop() -> None:
    from cilly_trading.engine.paper_execution_worker import stop_loss_breached

    assert stop_loss_breached(
        direction="long",
        stop_loss=Decimal("95"),
        bar_low=Decimal("94"),
        bar_high=Decimal("100"),
    )
    assert stop_loss_breached(
        direction="long",
        stop_loss=Decimal("95"),
        bar_low=Decimal("95"),
        bar_high=Decimal("100"),
    )


def test_long_stop_loss_not_breached_when_bar_stays_above_stop() -> None:
    from cilly_trading.engine.paper_execution_worker import stop_loss_breached

    assert not stop_loss_breached(
        direction="long",
        stop_loss=Decimal("95"),
        bar_low=Decimal("96"),
        bar_high=Decimal("100"),
    )


def test_short_stop_loss_breached_when_bar_high_touches_stop() -> None:
    from cilly_trading.engine.paper_execution_worker import stop_loss_breached

    assert stop_loss_breached(
        direction="short",
        stop_loss=Decimal("105"),
        bar_low=Decimal("100"),
        bar_high=Decimal("106"),
    )


def test_short_stop_loss_not_breached_when_bar_stays_below_stop() -> None:
    from cilly_trading.engine.paper_execution_worker import stop_loss_breached

    assert not stop_loss_breached(
        direction="short",
        stop_loss=Decimal("105"),
        bar_low=Decimal("100"),
        bar_high=Decimal("104"),
    )


def test_stop_loss_helper_rejects_unknown_direction() -> None:
    from cilly_trading.engine.paper_execution_worker import stop_loss_breached

    with pytest.raises(ValueError, match="unknown direction"):
        stop_loss_breached(
            direction="sideways",
            stop_loss=Decimal("100"),
            bar_low=Decimal("99"),
            bar_high=Decimal("101"),
        )


# ---------------------------------------------------------------------------
# #1147: ATR-based position sizing
# ---------------------------------------------------------------------------


def _atr_profile(**kwargs) -> PaperExecutionRiskProfile:
    return PaperExecutionRiskProfile(
        account_equity=Decimal("100000"),
        max_risk_per_trade_pct=Decimal("0.01"),
        min_trade_risk_pct=Decimal("0.005"),
        max_trade_risk_pct=Decimal("0.50"),
        max_total_exposure_pct=Decimal("1.00"),
        max_strategy_exposure_pct=Decimal("1.00"),
        max_symbol_exposure_pct=Decimal("1.00"),
        max_concurrent_positions=20,
        commission_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        cooldown_hours=0,
        **kwargs,
    )


def test_atr_sizing_produces_notional_proportional_to_risk_budget(
    tmp_path: Path,
) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "atr1.db")
    profile = _atr_profile(sizing_method="atr", atr_multiple=Decimal("2.0"))
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "atr": 2.0,
        "entry_zone": {"from_": 100.0, "to": 100.0},
    }
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"
    # ATR-derived risk_pct = (2.0 * 2.0) / 100.0 = 0.04
    # proposed_notional = equity * max_risk_pct / trade_risk_pct = 100000 * 0.01 / 0.04 = 25000
    assert result.decision_inputs is not None
    assert Decimal(result.decision_inputs["trade_risk_pct"]) == Decimal("0.04")


def test_atr_sizing_rejected_when_atr_not_provided(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "atr2.db")
    profile = _atr_profile(sizing_method="atr")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        # no atr field
    }
    result = worker.process_signal(signal)
    assert result.outcome == "reject:atr_not_provided"


def test_fixed_sizing_uses_explicit_trade_risk_pct(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "fixed1.db")
    profile = _atr_profile(sizing_method="fixed")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
    }
    result = worker.process_signal(signal)
    assert result.outcome == "eligible"
    assert result.decision_inputs is not None
    assert Decimal(result.decision_inputs["trade_risk_pct"]) == Decimal("0.05")


def test_fixed_sizing_rejected_when_trade_risk_pct_missing(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "fixed2.db")
    profile = _atr_profile(sizing_method="fixed")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    signal: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        # no trade_risk_pct
    }
    result = worker.process_signal(signal)
    assert result.outcome == "reject:missing_trade_risk_input"


def test_atr_multiple_scales_position_size(tmp_path: Path) -> None:
    """Higher atr_multiple → larger stop distance → smaller position size."""
    def _notional(atr_multiple: str) -> Decimal:
        repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / f"atrm_{atr_multiple}.db")
        profile = _atr_profile(sizing_method="atr", atr_multiple=Decimal(atr_multiple))
        worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)
        sig: Signal = {
            "symbol": "AAPL",
            "strategy": "s",
            "direction": "long",  # type: ignore[typeddict-item]
            "score": 80.0,
            "timestamp": "2026-01-01T00:00:00Z",
            "stage": "setup",  # type: ignore[typeddict-item]
            "atr": 1.0,
            "entry_zone": {"from_": 100.0, "to": 100.0},
        }
        result = worker.process_signal(sig)
        assert result.decision_inputs is not None
        return Decimal(result.decision_inputs["proposed_position_notional"])

    notional_2x = _notional("2.0")
    notional_4x = _notional("4.0")
    assert notional_4x < notional_2x


# ---------------------------------------------------------------------------
# #1145: Correlation risk gate
# ---------------------------------------------------------------------------


def _corr_profile(**kwargs) -> PaperExecutionRiskProfile:
    return PaperExecutionRiskProfile(
        account_equity=Decimal("100000"),
        max_risk_per_trade_pct=Decimal("0.01"),
        min_trade_risk_pct=Decimal("0.005"),
        max_trade_risk_pct=Decimal("0.50"),
        max_total_exposure_pct=Decimal("1.00"),
        max_strategy_exposure_pct=Decimal("1.00"),
        max_symbol_exposure_pct=Decimal("1.00"),
        max_concurrent_positions=20,
        commission_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        cooldown_hours=0,
        **kwargs,
    )


def _price_history_perfectly_correlated() -> dict[str, list[float]]:
    base = [float(i) for i in range(1, 61)]
    return {"AAPL": base, "MSFT": base}


def test_correlation_gate_blocks_entry_when_highly_correlated(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "corr1.db")
    profile = _corr_profile(
        correlation_check_enabled=True,
        correlation_threshold=0.7,
        max_correlated_pairs=0,  # block any correlated pair
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    # Open an AAPL position first
    aapl: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-corr-aapl",
    }
    first = worker.process_signal(aapl)
    assert first.outcome == "eligible"

    # Now try MSFT — perfectly correlated with AAPL
    msft: Signal = {
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-corr-msft",
    }
    blocked = worker.process_signal(msft, price_history=_price_history_perfectly_correlated())
    assert blocked.outcome == "skip:correlation_risk_blocked"
    assert blocked.reason is not None


def test_correlation_gate_skipped_when_disabled(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "corr2.db")
    profile = _corr_profile(
        correlation_check_enabled=False,
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    aapl: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-nc-aapl",
    }
    worker.process_signal(aapl)

    msft: Signal = {
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-nc-msft",
    }
    result = worker.process_signal(msft, price_history=_price_history_perfectly_correlated())
    assert result.outcome == "eligible"


def test_correlation_gate_passes_without_price_history(tmp_path: Path) -> None:
    """When price_history is None, correlation check is silently skipped."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "corr3.db")
    profile = _corr_profile(
        correlation_check_enabled=True,
        max_correlated_pairs=0,
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    aapl: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-noph-aapl",
    }
    worker.process_signal(aapl)

    msft: Signal = {
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-noph-msft",
    }
    result = worker.process_signal(msft, price_history=None)
    assert result.outcome == "eligible"


# ---------------------------------------------------------------------------
# #1146: Drawdown guard
# ---------------------------------------------------------------------------


def _drawdown_profile(**kwargs) -> PaperExecutionRiskProfile:
    return PaperExecutionRiskProfile(
        account_equity=Decimal("100000"),
        max_risk_per_trade_pct=Decimal("0.01"),
        min_trade_risk_pct=Decimal("0.005"),
        max_trade_risk_pct=Decimal("0.50"),
        max_total_exposure_pct=Decimal("1.00"),
        max_strategy_exposure_pct=Decimal("1.00"),
        max_symbol_exposure_pct=Decimal("1.00"),
        max_concurrent_positions=20,
        commission_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        cooldown_hours=0,
        **kwargs,
    )


def test_compute_drawdown_state_no_trades() -> None:
    from cilly_trading.engine.paper_execution_worker import _compute_drawdown_state

    losses, dd = _compute_drawdown_state([], initial_equity=Decimal("100000"))
    assert losses == 0
    assert dd == Decimal("0")


def test_compute_drawdown_state_consecutive_losses_counted_from_most_recent() -> None:
    from cilly_trading.engine.paper_execution_worker import _compute_drawdown_state
    from cilly_trading.models import Trade

    # qty=100 units @ entry 100; exit prices chosen so realized_pnl matches
    def _closed_trade(trade_id: str, exit_price: str, pnl: Decimal, closed_at: str) -> Trade:
        return Trade.model_validate(
            {
                "trade_id": trade_id,
                "position_id": f"pos-{trade_id}",
                "strategy_id": "s",
                "symbol": "AAPL",
                "direction": "long",
                "status": "closed",
                "opened_at": "2026-01-01T00:00:00Z",
                "closed_at": closed_at,
                "quantity_opened": Decimal("100"),
                "quantity_closed": Decimal("100"),
                "average_entry_price": Decimal("100"),
                "average_exit_price": Decimal(exit_price),
                "exposure_notional": Decimal("0"),  # fully closed — no remaining exposure
                "realized_pnl": pnl,
                "opening_order_ids": [],
                "execution_event_ids": [],
            }
        )

    trades = [
        _closed_trade("t1", "105", Decimal("500"), "2026-01-01T00:00:00Z"),   # win  (100 * 5 = 500)
        _closed_trade("t2", "98", Decimal("-200"), "2026-01-02T00:00:00Z"),   # loss (100 * -2 = -200)
        _closed_trade("t3", "97", Decimal("-300"), "2026-01-03T00:00:00Z"),   # loss (100 * -3 = -300)
    ]
    losses, dd = _compute_drawdown_state(trades, initial_equity=Decimal("100000"))
    assert losses == 2
    # peak was after t1: 100500; current is 100000; drawdown = 500/100500
    assert dd > Decimal("0")


def test_drawdown_guard_blocks_entry_after_consecutive_losses(tmp_path: Path) -> None:
    from cilly_trading.models import Trade

    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "dg1.db")
    profile = _drawdown_profile(
        drawdown_guard_enabled=True,
        max_consecutive_losses=2,
        max_drawdown_pct=Decimal("0.50"),
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    # Inject 2 closed losing trades directly into the repo
    for i in range(2):
        repo.save_trade(Trade.model_validate(
            {
                "trade_id": f"loss-{i}",
                "position_id": f"pos-loss-{i}",
                "strategy_id": "s",
                "symbol": "AAPL",
                "direction": "long",
                "status": "closed",
                "opened_at": f"2026-01-0{i+1}T00:00:00Z",
                "closed_at": f"2026-01-0{i+1}T12:00:00Z",
                "quantity_opened": Decimal("1"),
                "quantity_closed": Decimal("1"),
                "average_entry_price": Decimal("100"),
                "average_exit_price": Decimal("90"),
                "exposure_notional": Decimal("0"),
                "realized_pnl": Decimal("-10"),
                "opening_order_ids": [],
                "execution_event_ids": [],
            }
        ))

    result = worker.process_signal({
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-10T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-dg-block",
    })
    assert result.outcome == "skip:drawdown_guard_active"
    assert "consecutive_losses" in (result.reason or "")


def test_drawdown_guard_disabled_does_not_block(tmp_path: Path) -> None:
    from cilly_trading.models import Trade

    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "dg2.db")
    profile = _drawdown_profile(
        drawdown_guard_enabled=False,
        max_consecutive_losses=1,
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    repo.save_trade(Trade.model_validate(
        {
            "trade_id": "loss-x",
            "position_id": "pos-loss-x",
            "strategy_id": "s",
            "symbol": "AAPL",
            "direction": "long",
            "status": "closed",
            "opened_at": "2026-01-01T00:00:00Z",
            "closed_at": "2026-01-01T12:00:00Z",
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("90"),
            "exposure_notional": Decimal("0"),
            "realized_pnl": Decimal("-10"),
            "opening_order_ids": [],
            "execution_event_ids": [],
        }
    ))

    result = worker.process_signal({
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-10T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-dg-nodisable",
    })
    assert result.outcome == "eligible"


def test_drawdown_guard_blocks_on_equity_drawdown(tmp_path: Path) -> None:
    from cilly_trading.models import Trade

    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "dg3.db")
    profile = _drawdown_profile(
        drawdown_guard_enabled=True,
        max_consecutive_losses=100,     # not triggered by streak
        max_drawdown_pct=Decimal("0.05"),  # 5% drawdown limit
        sizing_method="fixed",
    )
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=profile)

    # A single large win then a large loss to create >5% drawdown from peak
    repo.save_trade(Trade.model_validate(
        {
            "trade_id": "win-dd",
            "position_id": "pos-win-dd",
            "strategy_id": "s",
            "symbol": "AAPL",
            "direction": "long",
            "status": "closed",
            "opened_at": "2026-01-01T00:00:00Z",
            "closed_at": "2026-01-02T00:00:00Z",
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("200"),
            "exposure_notional": Decimal("0"),
            "realized_pnl": Decimal("10000"),  # equity peak = 110000
            "opening_order_ids": [],
            "execution_event_ids": [],
        }
    ))
    repo.save_trade(Trade.model_validate(
        {
            "trade_id": "loss-dd",
            "position_id": "pos-loss-dd",
            "strategy_id": "s",
            "symbol": "AAPL",
            "direction": "long",
            "status": "closed",
            "opened_at": "2026-01-03T00:00:00Z",
            "closed_at": "2026-01-04T00:00:00Z",
            "quantity_opened": Decimal("1"),
            "quantity_closed": Decimal("1"),
            "average_entry_price": Decimal("100"),
            "average_exit_price": Decimal("50"),
            "exposure_notional": Decimal("0"),
            "realized_pnl": Decimal("-7000"),  # current equity = 103000; dd = 7000/110000 ≈ 6.4%
            "opening_order_ids": [],
            "execution_event_ids": [],
        }
    ))

    result = worker.process_signal({
        "symbol": "MSFT",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-10T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "signal_id": "sig-dg-equity",
    })
    assert result.outcome == "skip:drawdown_guard_active"
    assert "drawdown_pct" in (result.reason or "")


# ---------------------------------------------------------------------------
# #1148: Partial take-profit (process_exit_signal)
# ---------------------------------------------------------------------------


def _exit_profile(**kwargs) -> PaperExecutionRiskProfile:
    return PaperExecutionRiskProfile(
        account_equity=Decimal("100000"),
        max_risk_per_trade_pct=Decimal("0.01"),
        min_trade_risk_pct=Decimal("0.005"),
        max_trade_risk_pct=Decimal("0.50"),
        max_total_exposure_pct=Decimal("1.00"),
        max_strategy_exposure_pct=Decimal("1.00"),
        max_symbol_exposure_pct=Decimal("1.00"),
        max_concurrent_positions=20,
        commission_rate=Decimal("0"),
        slippage_rate=Decimal("0"),
        cooldown_hours=0,
        sizing_method="fixed",
        **kwargs,
    )


def _entry_signal(signal_id: str, symbol: str = "AAPL") -> Signal:
    return {
        "symbol": symbol,
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-01T00:00:00Z",
        "stage": "setup",  # type: ignore[typeddict-item]
        "trade_risk_pct": 0.05,
        "entry_zone": {"from_": 100.0, "to": 100.0},
        "signal_id": signal_id,
    }


def test_process_exit_signal_full_exit_closes_trade(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "exit1.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_exit_profile())

    entry_result = worker.process_signal(_entry_signal("sig-exit-full"))
    assert entry_result.outcome == "eligible"
    assert entry_result.trade_id is not None

    exit_sig: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T12:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "entry_zone": {"from_": 110.0, "to": 110.0},
        "signal_id": "sig-exit-full-out",
    }
    result = worker.process_exit_signal(exit_sig)
    assert result.outcome == "eligible:full_exit"
    assert result.trade_id == entry_result.trade_id

    trades = repo.list_trades(strategy_id="s", symbol="AAPL", limit=10)
    closed = [t for t in trades if t.status == "closed"]
    assert len(closed) == 1
    assert closed[0].closed_at == "2026-01-02T12:00:00Z"
    assert closed[0].realized_pnl is not None


def test_process_exit_signal_partial_exit_leaves_trade_open(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "exit2.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_exit_profile())

    worker.process_signal(_entry_signal("sig-exit-partial"))

    exit_sig: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T12:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "entry_zone": {"from_": 110.0, "to": 110.0},
        "exit_pct": 0.5,
        "signal_id": "sig-exit-partial-out",
    }
    result = worker.process_exit_signal(exit_sig)
    assert result.outcome == "eligible:partial_exit"

    trades = repo.list_trades(strategy_id="s", symbol="AAPL", limit=10)
    open_trades = [t for t in trades if t.status == "open"]
    assert len(open_trades) == 1
    assert open_trades[0].quantity_closed > Decimal("0")
    assert open_trades[0].quantity_closed < open_trades[0].quantity_opened


def test_process_exit_signal_skipped_when_no_open_position(tmp_path: Path) -> None:
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "exit3.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_exit_profile())

    result = worker.process_exit_signal({
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "signal_id": "sig-exit-nopos",
    })
    assert result.outcome == "skip:no_open_position_to_exit"


def test_process_exit_signal_partial_then_full_exit(tmp_path: Path) -> None:
    """Two sequential exits: 50% then the remaining 100% close the trade."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "exit4.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_exit_profile())

    worker.process_signal(_entry_signal("sig-2step-entry"))

    partial: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "entry_zone": {"from_": 110.0, "to": 110.0},
        "exit_pct": 0.5,
        "signal_id": "sig-2step-partial",
    }
    r1 = worker.process_exit_signal(partial)
    assert r1.outcome == "eligible:partial_exit"

    full: Signal = {
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-03T00:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "entry_zone": {"from_": 115.0, "to": 115.0},
        "signal_id": "sig-2step-full",
    }
    r2 = worker.process_exit_signal(full)
    assert r2.outcome == "eligible:full_exit"

    trades = repo.list_trades(strategy_id="s", symbol="AAPL", limit=10)
    closed = [t for t in trades if t.status == "closed"]
    assert len(closed) == 1


def test_process_exit_signal_realized_pnl_positive_on_profitable_exit(tmp_path: Path) -> None:
    """Exit at a higher price than entry must produce positive realized_pnl."""
    repo = SqliteCanonicalExecutionRepository(db_path=tmp_path / "exit5.db")
    worker = BoundedPaperExecutionWorker(repository=repo, risk_profile=_exit_profile())

    worker.process_signal(_entry_signal("sig-pnl-entry"))

    result = worker.process_exit_signal({
        "symbol": "AAPL",
        "strategy": "s",
        "direction": "long",  # type: ignore[typeddict-item]
        "score": 80.0,
        "timestamp": "2026-01-02T00:00:00Z",
        "stage": "exit",  # type: ignore[typeddict-item]
        "entry_zone": {"from_": 120.0, "to": 120.0},  # exit at 120, entry was 100
        "signal_id": "sig-pnl-exit",
    })
    assert result.outcome == "eligible:full_exit"

    trades = repo.list_trades(strategy_id="s", symbol="AAPL", limit=10)
    closed = [t for t in trades if t.status == "closed"]
    assert len(closed) == 1
    assert (closed[0].realized_pnl or Decimal("0")) > Decimal("0")

"""Focused tests for the BaseSqliteRepository read-query helpers (issue #1137)."""

from __future__ import annotations

from cilly_trading.repositories._base_sqlite import BaseSqliteRepository


def test_append_equality_filter_skips_none() -> None:
    where: list[str] = []
    params: list[object] = []
    BaseSqliteRepository._append_equality_filter(where, params, "symbol", None)
    assert where == []
    assert params == []


def test_append_equality_filter_appends_value() -> None:
    where: list[str] = []
    params: list[object] = []
    BaseSqliteRepository._append_equality_filter(where, params, "symbol", "AAPL")
    assert where == ["symbol = ?"]
    assert params == ["AAPL"]


def test_append_equality_filters_handles_mix() -> None:
    where: list[str] = []
    params: list[object] = []
    BaseSqliteRepository._append_equality_filters(
        where,
        params,
        (
            ("symbol", "AAPL"),
            ("strategy", None),
            ("run_id", "rid-1"),
        ),
    )
    assert where == ["symbol = ?", "run_id = ?"]
    assert params == ["AAPL", "rid-1"]


def test_compose_where_clause_empty_returns_empty_string() -> None:
    assert BaseSqliteRepository._compose_where_clause([]) == ""


def test_compose_where_clause_joins_with_and() -> None:
    assert (
        BaseSqliteRepository._compose_where_clause(["a = ?", "b = ?"])
        == "WHERE a = ? AND b = ?"
    )


def test_pagination_params_returns_int_pair() -> None:
    pair = BaseSqliteRepository._pagination_params(10, 5)
    assert pair == [10, 5]
    assert all(isinstance(value, int) for value in pair)

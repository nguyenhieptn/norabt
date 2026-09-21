from __future__ import annotations

from dataclasses import dataclass

import pytest

from Agent.backend.research.outcomes import compute_outcome_metrics


@dataclass(frozen=True)
class _Trade:
    close_time: int
    realized_pnl: float


def _trades(pnls):
    return [_Trade(close_time=i, realized_pnl=p) for i, p in enumerate(pnls)]


def test_basic_metrics_hand_computed_with_reference_capital():
    # cumulative: 10, 5, 25, -5, 0 ; peak_cumulative: 10,10,25,25,25
    # drawdown_abs: 0,5,0,30,25 -> max 30
    # peak_equity (capital=100): 110,110,125,125,125
    # drawdown_pct: 0, 4.545..., 0, 24.0, 20.0 -> max 24.0
    trades = _trades([10, -5, 20, -30, 5])
    metrics = compute_outcome_metrics(trades, reference_capital=100.0)

    assert metrics.trade_count == 5
    assert metrics.total_pnl == pytest.approx(0.0)
    assert metrics.total_pnl_pct == pytest.approx(0.0)
    assert metrics.win_rate_pct == pytest.approx(60.0)
    assert metrics.max_drawdown_abs == pytest.approx(30.0)
    assert metrics.max_drawdown_pct == pytest.approx(24.0)
    assert metrics.max_losing_streak == 1
    assert metrics.has_losing_streak_5 is False
    assert metrics.has_losing_streak_10 is False
    assert metrics.collapsed is False
    assert metrics.reference_capital == 100.0


def test_metrics_without_reference_capital_report_currency_only():
    trades = _trades([10, -5, 20, -30, 5])
    metrics = compute_outcome_metrics(trades, reference_capital=None)

    # Drawdown in currency is translation-invariant: identical with or
    # without a capital baseline.
    assert metrics.max_drawdown_abs == pytest.approx(30.0)
    assert metrics.max_drawdown_pct is None
    assert metrics.total_pnl_pct is None
    assert metrics.collapsed is None
    assert metrics.reference_capital is None


def test_metrics_ignore_input_order_and_sort_by_close_time():
    ordered = _trades([10, -5, 20, -30, 5])
    shuffled = list(reversed(ordered))
    assert compute_outcome_metrics(shuffled, reference_capital=100.0) == (
        compute_outcome_metrics(ordered, reference_capital=100.0)
    )


def test_losing_streaks_five_and_ten():
    pnls = [-1] * 6 + [1] + [-1] * 10
    metrics = compute_outcome_metrics(_trades(pnls), reference_capital=1000.0)
    assert metrics.max_losing_streak == 10
    assert metrics.has_losing_streak_5 is True
    assert metrics.has_losing_streak_10 is True


def test_losing_streak_below_five_is_not_flagged():
    pnls = [-1, -1, -1, -1, 1, -1, -1]
    metrics = compute_outcome_metrics(_trades(pnls), reference_capital=1000.0)
    assert metrics.max_losing_streak == 4
    assert metrics.has_losing_streak_5 is False


def test_collapse_flag_uses_the_configured_threshold():
    # One trade, -40 against a 100 reference capital -> 40% drawdown.
    trades = _trades([-40.0])
    below_threshold = compute_outcome_metrics(
        trades, reference_capital=100.0, collapse_drawdown_pct=50.0
    )
    above_threshold = compute_outcome_metrics(
        trades, reference_capital=100.0, collapse_drawdown_pct=30.0
    )
    assert below_threshold.max_drawdown_pct == pytest.approx(40.0)
    assert below_threshold.collapsed is False
    assert above_threshold.collapsed is True


def test_win_rate_all_wins_and_all_losses():
    all_wins = compute_outcome_metrics(_trades([1, 2, 3]), reference_capital=10.0)
    assert all_wins.win_rate_pct == pytest.approx(100.0)
    all_losses = compute_outcome_metrics(_trades([-1, -2, -3]), reference_capital=10.0)
    assert all_losses.win_rate_pct == pytest.approx(0.0)


def test_rejects_empty_trade_list():
    with pytest.raises(ValueError):
        compute_outcome_metrics([], reference_capital=100.0)

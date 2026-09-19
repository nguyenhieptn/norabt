"""Translate a trade-count horizon into calendar time.

Context: "500 trades" alone is unreadable -- it is a handful of days for a
scalper and years for a swing trader -- and a reader cannot tell when a
conclusion is an extrapolation past the data actually observed without both
numbers. `MonteCarloSimulationEngine.run_simulation` now reports
`trades_per_day`, `horizon_calendar_days`, `observed_span_days` and
`horizon_exceeds_observed` on top of the existing horizon-in-trades fields.
"""

from __future__ import annotations

import pytest

from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

DAY_MS = 86_400_000


def trade(index: int, pnl: float, open_time: int, close_time: int) -> TradeLedgerItem:
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol="BTC-USDT-SWAP",
        side=PositionSide.LONG,
        open_time=open_time,
        close_time=close_time,
        realized_pnl=pnl,
        holding_time_minutes=(close_time - open_time) / 60_000.0,
    )


def _scalper_ledger(n: int = 40, minutes_per_trade: int = 10) -> list[TradeLedgerItem]:
    """A fast bot: trades tightly packed in real time."""
    step_ms = minutes_per_trade * 60_000
    return [
        trade(i, 5.0 if i % 3 else -4.0, i * step_ms, i * step_ms + step_ms)
        for i in range(n)
    ]


def _swing_ledger(n: int = 40, days_per_trade: int = 20) -> list[TradeLedgerItem]:
    """A slow bot: trades spread thinly across real time."""
    step_ms = days_per_trade * DAY_MS
    return [
        trade(i, 5.0 if i % 3 else -4.0, i * step_ms, i * step_ms + step_ms)
        for i in range(n)
    ]


def test_a_scalper_shows_many_trades_per_day_and_a_short_calendar_horizon():
    result = MonteCarloSimulationEngine.run_simulation(
        _scalper_ledger(), 1_000.0, iterations=500, seed=1, block_bootstrap=True
    )
    assert result.is_valid
    assert result.trades_per_day is not None
    assert result.trades_per_day > 50  # 10-minute trades: >100/day of real time
    assert result.horizon_calendar_days is not None
    assert result.horizon_calendar_days < 1.0  # its own trade count fits in under a day


def test_a_swing_trader_shows_few_trades_per_day_and_a_long_calendar_horizon():
    result = MonteCarloSimulationEngine.run_simulation(
        _swing_ledger(), 1_000.0, iterations=500, seed=1, block_bootstrap=True
    )
    assert result.is_valid
    assert result.trades_per_day is not None
    assert result.trades_per_day < 0.1
    assert result.horizon_calendar_days is not None
    assert result.horizon_calendar_days > 300  # its own trade count spans about 2 years


def test_the_same_trade_count_means_wildly_different_calendar_spans():
    """The headline point of this feature: two bots that both get judged over
    (say) their own ~40-trade horizon are not being judged over the same
    real-world exposure at all.
    """
    scalper = MonteCarloSimulationEngine.run_simulation(
        _scalper_ledger(), 1_000.0, iterations=500, seed=1, block_bootstrap=True
    )
    swing = MonteCarloSimulationEngine.run_simulation(
        _swing_ledger(), 1_000.0, iterations=500, seed=1, block_bootstrap=True
    )
    assert scalper.horizon_trades == swing.horizon_trades
    assert scalper.horizon_calendar_days < swing.horizon_calendar_days


def test_insufficient_timestamps_yield_none_not_a_guess():
    """Fewer than two trades: there is no elapsed time to estimate a rate
    from, so the fields must be None rather than some fabricated number.
    """
    single = [trade(0, 5.0, 0, 60_000)]
    trades_per_day, observed_span_days = MonteCarloSimulationEngine._trade_cadence(
        single
    )
    assert trades_per_day is None
    assert observed_span_days is None

    empty_cadence = MonteCarloSimulationEngine._trade_cadence([])
    assert empty_cadence == (None, None)


def test_all_trades_closing_at_the_same_instant_gives_a_zero_span_not_a_guess():
    """Multiple trades but zero elapsed time: the span is genuinely zero, but
    a rate (trades / 0 days) is undefined, not merely large -- must be None.
    """
    same_time = [trade(i, 1.0, 0, 0) for i in range(5)]
    trades_per_day, observed_span_days = MonteCarloSimulationEngine._trade_cadence(
        same_time
    )
    assert trades_per_day is None
    assert observed_span_days == 0.0


def test_horizon_exceeds_observed_flags_extrapolation_past_the_ledger():
    """A caller-pinned horizon far beyond the bot's own trade count, on a slow
    bot, must be recognizable as running past the calendar span actually
    observed.
    """
    trades = _swing_ledger(n=25, days_per_trade=20)  # spans ~500 days, ~25 trades
    result = MonteCarloSimulationEngine.run_simulation(
        trades,
        1_000.0,
        iterations=500,
        horizon_trades=500,  # far more trades than this bot has ever made
        seed=1,
        block_bootstrap=True,
    )
    assert result.is_valid
    assert result.horizon_exceeds_observed is True
    assert result.horizon_calendar_days > result.observed_span_days


def test_horizon_within_the_observed_span_is_not_flagged_as_extrapolation():
    trades = _swing_ledger(n=40, days_per_trade=20)  # spans ~800 days
    result = MonteCarloSimulationEngine.run_simulation(
        trades,
        1_000.0,
        iterations=500,
        horizon_trades=10,  # far short of the bot's own observed history
        seed=1,
        block_bootstrap=True,
    )
    assert result.is_valid
    assert result.horizon_exceeds_observed is False


def test_horizon_exceeds_observed_is_none_when_cadence_cannot_be_estimated():
    same_time = [trade(i, 5.0 if i % 3 else -4.0, 0, 0) for i in range(25)]
    result = MonteCarloSimulationEngine.run_simulation(
        same_time, 1_000.0, iterations=200, seed=1, block_bootstrap=True
    )
    assert result.is_valid
    assert result.trades_per_day is None
    assert result.horizon_calendar_days is None
    assert result.horizon_exceeds_observed is None


def test_default_horizon_equals_observed_span_up_to_float_noise_and_is_not_flagged():
    """Regression for the real bug: with `--horizon` left blank, the horizon
    is set to the bot's own trade count, so `horizon_calendar_days` (=
    `horizon / trades_per_day`) and `observed_span_days` (the same
    `len(trades) / observed_span_days` cadence computed the other way
    round) are the SAME quantity by construction. They can only differ by
    float rounding noise -- observed in production on bot BB3398A957270A39
    as `horizon_calendar_days=56.58428614583334` vs
    `observed_span_days=56.58428614583333`, a ~1e-14 day (sub-millisecond)
    gap that a bare `>` comparison used to flag as "extrapolation" on every
    bot using the default horizon. Exercised here via the exact production
    numbers directly, and via a real `run_simulation` call with the default
    horizon to prove the whole pipeline agrees.
    """
    assert (
        MonteCarloSimulationEngine._horizon_exceeds_observed(
            56.58428614583334, 56.58428614583333
        )
        is False
    )

    trades = _swing_ledger(n=30, days_per_trade=2)
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=200, seed=1, block_bootstrap=True
    )
    assert result.is_valid
    assert result.horizon_basis == "OWN_TRADE_COUNT"
    assert result.horizon_calendar_days == pytest.approx(result.observed_span_days)
    assert result.horizon_exceeds_observed is False


def test_gap_of_one_day_but_under_two_percent_is_not_flagged():
    """A ~100-day observed span with a ~1-day gap clears the absolute
    (1-day) floor but not the relative (2%) floor -- must stay False, since
    a long-lived bot's small relative overrun is not a meaningful
    extrapolation.
    """
    assert MonteCarloSimulationEngine._horizon_exceeds_observed(101.0, 100.0) is False


def test_gap_over_two_percent_and_over_one_day_is_flagged_as_real_extrapolation():
    """A horizon several times the observed span (e.g. simulating 500 trades
    for a bot with only ~72 trades on record) clears both floors comfortably
    and must be flagged -- this is the genuine extrapolation case the flag
    exists to catch.
    """
    assert MonteCarloSimulationEngine._horizon_exceeds_observed(400.0, 56.58) is True


def test_horizon_exceeds_observed_is_none_when_either_input_is_missing():
    assert MonteCarloSimulationEngine._horizon_exceeds_observed(None, 56.0) is None
    assert MonteCarloSimulationEngine._horizon_exceeds_observed(56.0, None) is None
    assert MonteCarloSimulationEngine._horizon_exceeds_observed(None, None) is None

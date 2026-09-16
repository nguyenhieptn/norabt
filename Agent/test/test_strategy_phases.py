"""A record only means something against the market it was earned in."""

from __future__ import annotations

from typing import List

import pytest

from Agent.backend.mcp.analytics.strategy.phases import (
    MarketPhase,
    PhaseTimeline,
    build_timeline,
)
from Agent.backend.mcp.analytics.strategy.profile import StrategyPhaseAnalyzer
from Agent.backend.mcp.schemas.bot_result import PositionSide, TradeLedgerItem

HOUR_MS = 3_600_000
START_MS = 1_780_000_000_000


def _candles(moves: List[float], start: float = 100.0):
    """One candle per hour, each closing `move` percent from the last."""
    out, price = [], start
    for i, move in enumerate(moves):
        nxt = price * (1 + move / 100.0)
        out.append(
            {
                "timestamp": START_MS + i * HOUR_MS,
                "open": price,
                "high": max(price, nxt) * 1.001,
                "low": min(price, nxt) * 0.999,
                "close": nxt,
            }
        )
        price = nxt
    return out


def _trade(index: int, pnl: float, side=PositionSide.LONG, symbol="TEST-USDT-SWAP"):
    open_ms = START_MS + index * HOUR_MS
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol=symbol,
        side=side,
        open_time=open_ms,
        close_time=open_ms + HOUR_MS,
        realized_pnl=pnl,
        quantity=1.0,
        leverage=10.0,
        holding_time_minutes=60.0,
    )


def _flat_timeline(phase: MarketPhase, hours: int = 2000) -> PhaseTimeline:
    return PhaseTimeline(
        symbol="TEST",
        timestamps=[START_MS + i * HOUR_MS for i in range(hours)],
        phases=[phase] * hours,
        closes=[100.0] * hours,
    )


def test_a_steady_climb_is_labelled_an_uptrend():
    timeline = build_timeline("TEST", _candles([0.05] * 1200))

    assert timeline.phase_at(START_MS + 1100 * HOUR_MS) in (
        MarketPhase.UPTREND_CALM,
        MarketPhase.UPTREND_VOLATILE,
    )


def test_a_steady_slide_is_labelled_a_downtrend():
    timeline = build_timeline("TEST", _candles([-0.05] * 1200))

    assert timeline.phase_at(START_MS + 1100 * HOUR_MS) in (
        MarketPhase.DOWNTREND_CALM,
        MarketPhase.DOWNTREND_VOLATILE,
    )


def test_hours_before_the_warmup_stay_unknown():
    """EMA200 on ten candles is a number, not evidence."""
    timeline = build_timeline("TEST", _candles([0.05] * 300))

    assert timeline.phase_at(START_MS + 10 * HOUR_MS) is MarketPhase.UNKNOWN


def test_a_timestamp_outside_the_series_is_unknown_not_the_nearest_phase():
    timeline = build_timeline("TEST", _candles([0.05] * 1200))

    assert timeline.phase_at(START_MS - HOUR_MS) is MarketPhase.UNKNOWN


def test_profit_earned_in_one_phase_is_reported_as_regime_dependence():
    """95 % of one bot's profit came from a single phase; that must be visible."""
    timelines = {"TEST": _flat_timeline(MarketPhase.UPTREND_VOLATILE)}
    trades = [_trade(i, 100.0) for i in range(10)]

    result = StrategyPhaseAnalyzer.analyze(trades, timelines)

    assert result.regime_dependence_pct == pytest.approx(100.0)
    assert result.best_phase == MarketPhase.UPTREND_VOLATILE.value
    assert result.phase_coverage_pct == pytest.approx(100.0)


def test_a_phase_the_bot_lost_in_is_named():
    timelines = {"TEST": _flat_timeline(MarketPhase.DOWNTREND_CALM)}
    trades = [_trade(i, -50.0) for i in range(8)]

    result = StrategyPhaseAnalyzer.analyze(trades, timelines)

    assert result.losing_phases == [MarketPhase.DOWNTREND_CALM.value]
    assert result.tested_in_downtrend is True


def test_a_phase_the_market_offered_but_the_bot_skipped_is_untested_not_safe():
    hours = 2000
    half = hours // 2
    timeline = PhaseTimeline(
        symbol="TEST",
        timestamps=[START_MS + i * HOUR_MS for i in range(hours)],
        # The market spent the back half in a downtrend the bot never traded.
        phases=[MarketPhase.UPTREND_CALM] * half
        + [MarketPhase.DOWNTREND_CALM] * (hours - half),
        closes=[100.0] * hours,
    )
    trades = [_trade(i, 20.0) for i in range(10)]

    result = StrategyPhaseAnalyzer.analyze(trades, {"TEST": timeline})

    assert MarketPhase.DOWNTREND_CALM.value in result.untested_phases
    assert result.tested_in_downtrend is False


def test_trades_on_an_instrument_without_candles_count_as_uncovered():
    """No candles means no phase; it must not be folded into a known bucket."""
    timelines = {"TEST": _flat_timeline(MarketPhase.RANGE_CALM)}
    trades = [_trade(i, 10.0) for i in range(5)] + [
        _trade(i, 10.0, symbol="NOCANDLE-USDT-SWAP") for i in range(5, 10)
    ]

    result = StrategyPhaseAnalyzer.analyze(trades, timelines)

    assert result.trades_without_phase == 5
    assert result.phase_coverage_pct == pytest.approx(50.0)


def test_buying_after_a_rally_reads_as_trend_following():
    timeline = build_timeline("TEST", _candles([0.2] * 1200))
    trades = [_trade(1000 + i, 10.0, side=PositionSide.LONG) for i in range(10)]

    result = StrategyPhaseAnalyzer.analyze(trades, {"TEST": timeline})

    assert result.entry_style == "TREND_FOLLOWING"
    assert result.entry_style_evidence


def test_shorting_into_a_rally_reads_as_mean_reversion():
    timeline = build_timeline("TEST", _candles([0.2] * 1200))
    trades = [_trade(1000 + i, 10.0, side=PositionSide.SHORT) for i in range(10)]

    result = StrategyPhaseAnalyzer.analyze(trades, {"TEST": timeline})

    assert result.entry_style == "MEAN_REVERSION"
    assert result.directional_bias == "SHORT_ONLY"


def test_a_one_way_book_is_reported_as_such():
    timelines = {"TEST": _flat_timeline(MarketPhase.RANGE_CALM)}
    trades = [_trade(i, 10.0, side=PositionSide.LONG) for i in range(10)]

    result = StrategyPhaseAnalyzer.analyze(trades, timelines)

    assert result.directional_bias == "LONG_ONLY"
    assert result.long_share_pct == pytest.approx(100.0)

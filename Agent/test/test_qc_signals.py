"""A risk signal that fires on most of the population carries no information."""

from __future__ import annotations

from typing import List

import pytest

from Agent.backend.mcp.analytics.behavior.detector import BehavioralPatternDetector
from Agent.backend.mcp.schemas.bot_result import (
    BotResult,
    PositionSide,
    StrategyObservations,
    TradeLedgerItem,
)
from Agent.backend.qc.evaluator.lenses.strategy_drift import StrategyDriftLens
from Agent.backend.qc.schemas.risk_assessment import EvidenceStatus

HOUR_MS = 3_600_000
START_MS = 1_780_000_000_000


def _trade(index: int, pnl: float, margin: float, symbol="BTC-USDT-SWAP", lever=10.0):
    open_ms = START_MS + index * HOUR_MS
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol=symbol,
        side=PositionSide.LONG,
        open_time=open_ms,
        close_time=open_ms + 600_000,
        realized_pnl=pnl,
        margin=margin,
        leverage=lever,
        quantity=1.0,
        holding_time_minutes=10.0,
    )


def _analyze(trades: List[TradeLedgerItem], open_positions: int = 0):
    return BehavioralPatternDetector.analyze(trades, open_positions)


def test_doubling_down_after_losses_on_one_market_is_flagged():
    trades, size = [], 100.0
    for i in range(20):
        losing = i % 2 == 0
        trades.append(_trade(i, -50.0 if losing else 40.0, size))
        size = size * 2.0 if losing else 100.0

    assert _analyze(trades).martingale_escalation_detected is True


def test_a_bot_that_simply_varies_its_size_is_not_called_martingale():
    """Without a control group, random sizing clears a bare post-loss threshold."""
    # Size cycles on a period of 4, outcome on a period of 3, so the two never
    # line up: escalation after a loss is as likely as escalation after a win.
    sizes = [100.0, 300.0, 120.0, 400.0]
    trades = [_trade(i, -50.0 if i % 3 == 0 else 40.0, sizes[i % 4]) for i in range(48)]

    result = _analyze(trades)

    assert result.martingale_escalation_detected is False


def test_escalation_is_judged_within_one_market_not_across_them():
    """Losing on BTC then opening a routine DOGE position is not doubling down."""
    trades = []
    for i in range(20):
        if i % 2 == 0:
            trades.append(_trade(i, -50.0, 100.0, symbol="BTC-USDT-SWAP"))
        else:
            trades.append(_trade(i, 40.0, 5_000.0, symbol="DOGE-USDT-SWAP"))

    assert _analyze(trades).martingale_escalation_detected is False


def test_one_leverage_bump_in_a_long_ledger_is_not_an_escalation_pattern():
    trades = [_trade(i, -10.0 if i == 0 else 20.0, 100.0) for i in range(40)]
    trades[1] = _trade(1, 20.0, 100.0, lever=25.0)

    assert _analyze(trades).leverage_escalation_detected is False


def _bot_with(strategy: StrategyObservations, trade_count: int = 100) -> BotResult:
    from Agent.test.conftest import FIXED_AS_OF_MS

    bot = BotResult.model_construct(
        strategy_observations=strategy,
        performance=type("P", (), {"trade_count": trade_count})(),
        trade_ledger_summary=[],
        as_of_ms=FIXED_AS_OF_MS,
    )
    return bot


def test_the_strategy_dimension_abstains_when_the_ledger_cannot_be_placed():
    """It used to return NOT_APPLICABLE for every bot, making the dimension dead."""
    result = StrategyDriftLens.evaluate(
        _bot_with(StrategyObservations(observed_profile="X", phase_coverage_pct=10.0))
    )

    assert result.status == EvidenceStatus.UNKNOWN


def test_profit_concentrated_in_one_regime_raises_the_strategy_score():
    spread = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                regime_dependence_pct=30.0,
                tested_in_downtrend=True,
            )
        )
    )
    concentrated = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                regime_dependence_pct=95.0,
                best_phase="UPTREND_VOLATILE",
                tested_in_downtrend=True,
            )
        )
    )

    assert concentrated.score > spread.score
    assert concentrated.status == EvidenceStatus.AVAILABLE
    assert any("95%" in finding for finding in concentrated.key_findings)


def test_never_having_traded_a_downtrend_counts_against_the_bot():
    untested = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                tested_in_downtrend=False,
            )
        )
    )
    tested = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=90.0,
                tested_in_downtrend=True,
            )
        )
    )

    assert untested.score > tested.score


def test_confidence_follows_how_much_of_the_ledger_was_placed():
    result = StrategyDriftLens.evaluate(
        _bot_with(
            StrategyObservations(
                observed_profile="X",
                phase_coverage_pct=60.0,
                tested_in_downtrend=True,
            )
        )
    )

    assert result.confidence == pytest.approx(0.6)

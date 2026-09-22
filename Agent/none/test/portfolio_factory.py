"""Minimal in-memory `BotResult` builder for the portfolio tests.

Deliberately NOT a fixture on disk: the portfolio maths has to be tested
against series whose correlation is known exactly (identical, exactly
inverted, disjoint in time), and no real ledger provides those. The on-disk
fixtures are used in test_portfolio_pipeline.py, where the question is
whether the wiring survives real data rather than whether the arithmetic is
right.
"""

from __future__ import annotations

from typing import Dict, List, Optional, Sequence

from Agent.backend.bot.mcp.analytics.drawdown.underwater import (
    DrawdownUnderwaterAnalyzer,
)
from Agent.backend.bot.mcp.analytics.strategy.exit_rule import ExitRuleAnalyzer
from Agent.backend.bot.mcp.capital.equity_curve import CapitalModel
from Agent.backend.bot.mcp.schemas.bot_result import (
    BehavioralObservations,
    BotCurrentState,
    BotIdentity,
    BotPerformanceMetrics,
    BotResult,
    DataQualityAssessment,
    DeferredLossProfile,
    DrawdownAnalysis,
    LedgerReconciliation,
    PositionSide,
    RiskMeasurementMode,
    SimulationResults,
    StrategyObservations,
    TradeLedgerItem,
    TradeStatistics,
)

DAY_MS = 24 * 60 * 60 * 1000
BASE_MS = 1_700_000_000_000


def make_trades(
    pnls: Sequence[float],
    start_ms: int = BASE_MS,
    step_ms: int = DAY_MS,
    symbol: str = "BTC",
    prefix: str = "t",
    hold_minutes: float = 60.0,
    entry_price: float = 100.0,
    pnl_to_move: float = 1.0,
) -> List[TradeLedgerItem]:
    """One closed trade per step, so a bucket index maps to a list index.

    Entry and exit prices are filled in because `ExitRuleAnalyzer` reads the
    PRICE move, not the PnL, and skips any trade missing either side --
    without them a factory-built bot is unfingerprintable and every
    style-comparison test would pass vacuously. `pnl_to_move` scales PnL into
    a percentage move so a caller can keep the two independent when a test
    needs bots with matching behaviour and differing PnL.
    """
    trades: List[TradeLedgerItem] = []
    for index, pnl in enumerate(pnls):
        close_time = start_ms + index * step_ms
        move = float(pnl) * pnl_to_move
        trades.append(
            TradeLedgerItem(
                trade_id=f"{prefix}{index}",
                symbol=symbol,
                side=PositionSide.LONG,
                open_time=close_time - int(hold_minutes * 60_000),
                close_time=close_time,
                entry_price=entry_price,
                exit_price=entry_price * (1.0 + move / 100.0),
                notional=1_000.0,
                leverage=5.0,
                realized_pnl=float(pnl),
                holding_time_minutes=hold_minutes,
            )
        )
    return trades


def make_bot(
    code: str,
    trades: Sequence[TradeLedgerItem],
    *,
    nick_name: Optional[str] = None,
    symbol: str = "BTC",
    capital_at_risk: Optional[float] = 10_000.0,
    current_notional: Optional[float] = 5_000.0,
    side: PositionSide = PositionSide.LONG,
    exposure_share: Optional[Dict[str, float]] = None,
    exposure_by_symbol: Optional[Dict[str, float]] = None,
    as_of_ms: int = BASE_MS,
) -> BotResult:
    total = sum(trade.realized_pnl for trade in trades)
    capital = CapitalModel(basis="TEST", capital_at_risk=capital_at_risk)
    wins = sum(1 for trade in trades if trade.realized_pnl > 0)
    count = len(trades)
    return BotResult(
        identity=BotIdentity(
            bot_id=f"bot_{code}",
            unique_code=code,
            nick_name=nick_name or f"Bot {code}",
            symbol=symbol,
            asset_context=symbol,
            primary_traded_symbol=symbol,
            observed_symbols=[symbol],
            symbol_exposure_share=exposure_share or {symbol: 1.0},
        ),
        timestamp=as_of_ms,
        as_of_ms=as_of_ms,
        current_state=BotCurrentState(
            current_position_side=side,
            current_notional=current_notional,
            exposure_by_symbol=exposure_by_symbol or (
                {symbol: current_notional} if current_notional else {}
            ),
        ),
        performance=BotPerformanceMetrics(
            trade_count=count,
            win_rate=(wins / count * 100.0) if count else 0.0,
            loss_rate=((count - wins) / count * 100.0) if count else 0.0,
            total_pnl=total,
        ),
        deferred_loss=DeferredLossProfile(realized_pnl=total),
        trade_statistics=TradeStatistics(
            sample_size=count,
            measurement_mode=RiskMeasurementMode.FULL,
            return_basis="ABSOLUTE_PNL",
        ),
        trade_ledger_summary=list(trades),
        behavioral_observations=BehavioralObservations(),
        strategy_observations=StrategyObservations(observed_profile="TEST"),
        # Chạy đúng bộ phân tích thật: một `DrawdownAnalysis()` rỗng khiến
        # mọi so sánh sụt giảm giữa thành viên và sổ gộp thành None vs None.
        drawdown_analysis=DrawdownUnderwaterAnalyzer.analyze(
            list(trades), capital
        ),
        simulation_results=SimulationResults(
            simulation_method="TEST",
            iterations=0,
            sample_size=count,
            horizon_trades=0,
            return_basis="ABSOLUTE_PNL",
            is_valid=False,
        ),
        # Dựng như `BotObservationService` dựng: thiếu trường này thì mọi
        # phép so sánh cách chơi lặng lẽ bỏ qua bot và test pass rỗng.
        exit_rule=ExitRuleAnalyzer.analyze(list(trades)),
        reconciliation=LedgerReconciliation(status="OK", ledger_pnl=total),
        capital=capital,
        data_quality=DataQualityAssessment(
            completeness_score=1.0,
            freshness_score=1.0,
            overall_score=1.0,
            freshness_ms=0,
            measurement_mode=RiskMeasurementMode.FULL,
            valid_trade_count=count,
        ),
    )

from __future__ import annotations

from typing import List, Optional

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.report.qc.evaluator.lenses.behavioral_risk import BehavioralRiskLens
from Agent.backend.report.qc.evaluator.lenses.drawdown_risk import DrawdownRiskLens
from Agent.backend.report.qc.evaluator.lenses.leverage_exposure import LeverageExposureLens
from Agent.backend.report.qc.evaluator.lenses.liquidity_execution import LiquidityExecutionLens
from Agent.backend.report.qc.evaluator.lenses.market_alignment import MarketAlignmentLens
from Agent.backend.report.qc.evaluator.lenses.performance_quality import PerformanceQualityLens
from Agent.backend.report.qc.evaluator.lenses.portfolio_risk import PortfolioRiskLens
from Agent.backend.report.qc.evaluator.lenses.return_r_quality import ReturnRQualityLens
from Agent.backend.report.qc.evaluator.lenses.strategy_drift import StrategyDriftLens
from Agent.backend.report.qc.evaluator.lenses.tail_risk import TailRiskLens
from Agent.backend.report.qc.schemas.risk_assessment import BotRiskAssessment, RiskDimensions
from Agent.backend.report.qc.scoring.fusion import RiskFusionEngine


class QCCoreService:
    """LOGIC 3: evaluate only MarketResult + BotResult, with optional prior/portfolio context."""

    @staticmethod
    def assess_bot(
        market: Optional[MarketResult],
        bot: BotResult,
        previous_assessment: Optional[BotRiskAssessment] = None,
        portfolio_bots: Optional[List[BotResult]] = None,
    ) -> BotRiskAssessment:
        if market is not None and market.symbol != bot.identity.symbol:
            raise ValueError(
                f"MarketResult symbol {market.symbol} does not match the market this bot "
                f"trades ({bot.identity.symbol})"
            )
        dimensions = RiskDimensions(
            market_alignment=MarketAlignmentLens.evaluate(market, bot),
            performance_quality=PerformanceQualityLens.evaluate(bot),
            return_r_quality=ReturnRQualityLens.evaluate(bot),
            drawdown_risk=DrawdownRiskLens.evaluate(bot),
            tail_risk=TailRiskLens.evaluate(bot),
            leverage_exposure=LeverageExposureLens.evaluate(market, bot),
            behavioral_risk=BehavioralRiskLens.evaluate(bot),
            strategy_drift=StrategyDriftLens.evaluate(bot),
            liquidity_execution=LiquidityExecutionLens.evaluate(market, bot),
            portfolio_risk=PortfolioRiskLens.evaluate(market, bot, portfolio_bots),
        )
        return RiskFusionEngine.fuse(market, bot, dimensions, previous_assessment)

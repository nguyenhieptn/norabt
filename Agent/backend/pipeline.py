from __future__ import annotations

from pathlib import Path
from typing import List, Optional

from pydantic import BaseModel

from Agent.backend.control.execution.okx_executor import OKXControlExecutor
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import (
    ControlDecision,
    ExecutionMode,
)
from Agent.backend.infra.config import config
from Agent.backend.infra.quality import EvaluationMode
from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.mcp.service import BotObservationService
from Agent.backend.qc.schemas.risk_assessment import BotRiskAssessment
from Agent.backend.qc.history.store import AssessmentHistoryStore
from Agent.backend.qc.service import QCCoreService
from Agent.backend.universe.registry import UniverseRegistry


class RiskSupervisionResult(BaseModel):
    traded_symbol: str
    market_available: bool
    market_resolution: str
    universe_eligible: bool
    eligibility_reason: str
    market_result: Optional[MarketResult] = None
    bot_result: BotResult
    risk_assessment: BotRiskAssessment
    control_decision: ControlDecision


class RiskSupervisionPipeline:
    """One vertical slice: bot snapshot -> its real market -> QC -> control record."""

    def __init__(
        self,
        data_dir: Optional[Path] = None,
        market_service: Optional[MarketService] = None,
        bot_service: Optional[BotObservationService] = None,
        controller: Optional[ControlDecisionEngine] = None,
        evaluation_mode: EvaluationMode = EvaluationMode.SNAPSHOT,
        history: Optional[AssessmentHistoryStore] = None,
        persist_history: bool = True,
    ) -> None:
        self.history = history or AssessmentHistoryStore()
        self.persist_history = persist_history
        self.data_dir = data_dir or Path(config.DATA_DIR)
        self.market_service = market_service or MarketService(
            self.data_dir, evaluation_mode
        )
        self.bot_service = bot_service or BotObservationService(
            self.data_dir, evaluation_mode
        )
        self.controller = controller or ControlDecisionEngine(
            mode=ExecutionMode.READ_ONLY
        )

    def resolve_market(
        self, traded_symbol: str, as_of_ms: Optional[int] = None
    ) -> tuple[Optional[MarketResult], str]:
        """Find the market the bot actually trades, never a substitute."""
        for venue_type in ("CEX", "DEX"):
            try:
                return (
                    self.market_service.get_market_result(
                        traded_symbol, venue_type=venue_type, as_of_ms=as_of_ms
                    ),
                    f"RESOLVED_{venue_type}",
                )
            except (MarketDataUnavailableError, ValueError):
                continue
        return None, "NO_MARKET_DATA_FOR_TRADED_SYMBOL"

    def run(
        self,
        asset: str,
        bot_folder_name: str,
        venue_type: str = "CEX",
        seed: int = 42,
        as_of_ms: Optional[int] = None,
        previous_assessment: Optional[BotRiskAssessment] = None,
        portfolio_bots: Optional[List[BotResult]] = None,
        simulation_iterations: int = 10_000,
        simulation_horizon: int = 500,
    ) -> RiskSupervisionResult:
        bot = self.bot_service.get_bot_result(
            asset,
            bot_folder_name,
            seed=seed,
            venue_type=venue_type,
            as_of_ms=as_of_ms,
            simulation_iterations=simulation_iterations,
            simulation_horizon=simulation_horizon,
        )
        traded_symbol = bot.identity.symbol
        market, resolution = self.resolve_market(traded_symbol, as_of_ms=as_of_ms)

        eligible = False
        reason = "NO_MARKET_DATA_FOR_TRADED_SYMBOL"
        if market is not None:
            registry = UniverseRegistry(self.data_dir)
            eligible = any(
                candidate.asset_id == market.asset_id
                for candidate in registry.list_all()
            )
            reason = registry.list_rejections().get(
                market.asset_id, "ELIGIBLE" if eligible else "NOT_IN_UNIVERSE"
            )

        prior = previous_assessment or self.history.latest(bot.identity.bot_id)
        assessment = QCCoreService.assess_bot(
            market,
            bot,
            previous_assessment=prior,
            portfolio_bots=portfolio_bots,
        )
        if self.persist_history:
            self.history.append(assessment)
        decision = OKXControlExecutor.execute(
            self.controller.decide(assessment, now_ms=as_of_ms)
        )
        return RiskSupervisionResult(
            traded_symbol=traded_symbol,
            market_available=market is not None,
            market_resolution=resolution,
            universe_eligible=eligible,
            eligibility_reason=reason,
            market_result=market,
            bot_result=bot,
            risk_assessment=assessment,
            control_decision=decision,
        )

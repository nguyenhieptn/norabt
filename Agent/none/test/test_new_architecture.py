from __future__ import annotations

import pytest

from Agent.backend.control.execution.okx_executor import OKXControlExecutor
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import (
    ControlAction,
    ExecutionMode,
    ExecutionStatus,
)
from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.report.qc.schemas.risk_assessment import (
    BotRiskAssessment,
    EvidenceStatus,
    RiskTier,
    RiskTrend,
)
from Agent.backend.report.qc.service import QCCoreService
from Agent.backend.market.universe.registry import UniverseRegistry
from Agent.none.test.conftest import FIXED_AS_OF_MS


def test_universe_registry():
    registry = UniverseRegistry.get_instance()
    assert registry.list_candidates()
    assert len(registry.list_cex()) <= 30
    assert len(registry.list_dex()) <= 20
    assert all(asset.volume_24h_usd is not None for asset in registry.list_all())
    assert all(asset.depth_02_usd is not None for asset in registry.list_all())


def test_logic1_market_service(market_btc):
    assert isinstance(market_btc, MarketResult)
    assert market_btc.symbol == "BTC"
    assert market_btc.price_state.last_price > 0
    # Flow direction and OI move with every refresh, so assert the invariants the
    # dataset must satisfy rather than whichever way the market leaned today.
    assert market_btc.orderflow_state.flow_bias in (
        "BUY_PRESSURE",
        "SELL_PRESSURE",
        "NEUTRAL",
    )
    assert market_btc.derivatives_state.open_interest > 0
    assert market_btc.macro_state.btc_correlation == pytest.approx(1.0)
    assert market_btc.macro_state.btc_beta == pytest.approx(1.0)
    assert "macro" not in market_btc.data_quality.missing_sources


def test_logic2_mcp_simulation(bot_top):
    assert isinstance(bot_top, BotResult)
    assert bot_top.performance.trade_count == 72
    assert bot_top.performance.roi_pct == pytest.approx(50.65)
    assert bot_top.identity.asset_context == "MU"
    assert bot_top.identity.primary_traded_symbol == "MU"
    assert bot_top.trade_statistics.sample_size == 72
    assert bot_top.simulation_results.iterations == 1_000
    assert bot_top.simulation_results.horizon_trades == 500
    assert bot_top.simulation_results.is_valid
    assert bot_top.simulation_results.p_loss_after_500_trades is not None


def test_logic3_qc_core_differential(market_mu, market_hype, bot_top, bot_poor):
    good = QCCoreService.assess_bot(market_mu, bot_top)
    poor = QCCoreService.assess_bot(market_hype, bot_poor)
    assert isinstance(good, BotRiskAssessment)
    assert isinstance(poor, BotRiskAssessment)
    assert good.risk_score < poor.risk_score
    assert good.risk_tier in (RiskTier.HEALTHY, RiskTier.WATCH)
    assert poor.risk_score > good.risk_score
    assert poor.dimensions.behavioral_risk.score > good.dimensions.behavioral_risk.score
    # Instrument attribution is missing, so alignment is judged at reduced confidence.
    assert poor.dimensions.market_alignment.status == EvidenceStatus.AVAILABLE
    assert poor.dimensions.market_alignment.confidence < 1.0
    assert good.risk_trend == RiskTrend.UNKNOWN


def test_control_layer_is_read_only(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor)
    decision = ControlDecisionEngine(mode=ExecutionMode.READ_ONLY).decide(
        assessment, now_ms=FIXED_AS_OF_MS
    )
    assert decision.action in (
        ControlAction.MONITOR,
        ControlAction.WARN,
        ControlAction.BLOCK_NEW_TRADES,
        ControlAction.REDUCE,
        ControlAction.PAUSE,
    )
    executed = OKXControlExecutor.execute(decision)
    assert executed.execution_status == ExecutionStatus.RECORDED_READ_ONLY
    assert "external_request_sent" not in (executed.execution_details or {})


def test_reproducibility_and_determinism(market_mu, bot_top):
    first = QCCoreService.assess_bot(market_mu, bot_top)
    second = QCCoreService.assess_bot(market_mu, bot_top)
    assert first.assessment_id == second.assessment_id
    assert first.risk_score == second.risk_score
    assert first.risk_tier == second.risk_tier
    assert first.recommended_action == second.recommended_action


def test_full_vertical_pipeline_is_safe_and_typed():
    result = RiskSupervisionPipeline().run(
        "MU",
        "bot_BB3398A957270A39",
        venue_type="CEX",
        seed=42,
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=200,
        simulation_horizon=100,
    )
    assert isinstance(result.market_result, MarketResult)
    assert isinstance(result.bot_result, BotResult)
    assert isinstance(result.risk_assessment, BotRiskAssessment)
    assert result.traded_symbol == "MU"
    assert result.market_available is True
    assert result.market_resolution == "RESOLVED_CEX"
    assert result.control_decision.execution_mode == ExecutionMode.READ_ONLY
    assert (
        result.control_decision.execution_status == ExecutionStatus.RECORDED_READ_ONLY
    )

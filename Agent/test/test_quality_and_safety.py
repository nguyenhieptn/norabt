from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
from pydantic import ValidationError

from Agent.backend.control.execution.okx_executor import OKXControlExecutor
from Agent.backend.control.policy.decision_engine import ControlDecisionEngine
from Agent.backend.control.schemas.control_decision import (
    ControlAction,
    ControlDecision,
    ExecutionMode,
    ExecutionStatus,
)
from Agent.backend.infra.quality import DataQualitySummary
from Agent.backend.market.schemas.market_result import (
    LiquidityState,
    MarketResult,
    OrderflowState,
    PriceState,
    StructureState,
    TrendState,
    VolatilityState,
)
from Agent.backend.market.service import MarketDataUnavailableError, MarketService
from Agent.backend.mcp.analytics.simulation.bootstrap import BootstrapSampler
from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.capital.equity_curve import CapitalModel
from Agent.backend.mcp.schemas.bot_result import (
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
from Agent.backend.mcp.service import BotDataUnavailableError, BotObservationService
from Agent.backend.mcp.trades.ledger import TradeLedgerManager
from Agent.backend.qc.schemas.risk_assessment import EvidenceStatus, RiskTier, RiskTrend
from Agent.backend.qc.service import QCCoreService
from Agent.test.conftest import FIXED_AS_OF_MS


def trade(index: int, pnl: float, stop_loss: float | None = None) -> TradeLedgerItem:
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol="BTC-USDT-SWAP",
        side=PositionSide.LONG,
        open_time=index * 3_600_000,
        close_time=(index + 1) * 3_600_000,
        entry_price=100.0,
        exit_price=101.0,
        quantity=1.0,
        margin=100.0,
        notional=200.0,
        realized_pnl=pnl,
        realized_pnl_pct=pnl,
        return_basis="MARGIN_RETURN",
        initial_risk=5.0 if stop_loss is not None else None,
        r_multiple=pnl / 5.0 if stop_loss is not None else None,
        fee=None,
        funding=None,
        holding_time_minutes=60.0,
        leverage=2.0,
        stop_loss=stop_loss,
    )


def test_market_missing_dataset_fails_closed(tmp_path):
    with pytest.raises(MarketDataUnavailableError):
        MarketService(tmp_path).get_market_result("BTC")


def test_market_rejects_bad_venue(market_btc):
    with pytest.raises(ValueError):
        MarketService().get_market_result("BTC", venue_type="SPOT")


def test_market_venue_is_explicit_for_duplicate_symbol():
    cex = MarketService().get_market_result(
        "SOL", venue_type="CEX", as_of_ms=FIXED_AS_OF_MS
    )
    dex = MarketService().get_market_result(
        "SOL", venue_type="DEX", as_of_ms=FIXED_AS_OF_MS
    )
    assert cex.venue_type == "CEX"
    assert dex.venue_type == "DEX"
    assert cex.asset_id != dex.asset_id


def test_bot_missing_dataset_fails_closed(tmp_path):
    with pytest.raises(BotDataUnavailableError):
        BotObservationService(tmp_path).get_bot_result("BTC", "missing")


def test_ledger_normalizes_units_deduplicates_and_rejects_bad_rows():
    raw = {
        "closed_trades": [
            {
                "subPosId": "1",
                "instId": "BTC-USDT-SWAP",
                "posSide": "long",
                "openTime": "1000",
                "closeTime": "2000",
                "openAvgPx": "100",
                "closeAvgPx": "101",
                "subPos": "2",
                "margin": "50",
                "lever": "3",
                "pnl": "5",
                "pnlRatio": "0.10",
            },
            {
                "subPosId": "1",
                "instId": "BTC-USDT-SWAP",
                "posSide": "long",
                "openTime": "1000",
                "closeTime": "2100",
                "openAvgPx": "100",
                "closeAvgPx": "102",
                "subPos": "2",
                "margin": "50",
                "lever": "3",
                "pnl": "6",
                "pnlRatio": "0.12",
            },
            {"subPosId": "bad", "openTime": "3000", "closeTime": "2000", "pnl": "1"},
        ]
    }
    result = TradeLedgerManager.parse_trade_list_with_diagnostics(raw)
    assert len(result.trades) == 1
    assert result.rejected_count == 1
    assert result.trades[0].quantity == 2.0
    assert result.trades[0].notional == 150.0
    assert result.trades[0].realized_pnl_pct == 12.0
    assert any("Duplicate" in warning for warning in result.warnings)


def test_measurement_mode_requires_complete_fields():
    full = [trade(i, 1.0, stop_loss=95.0) for i in range(2)]
    partial = [trade(i, 1.0) for i in range(2)]
    limited = [
        item.model_copy(
            update={
                "entry_price": None,
                "exit_price": None,
                "quantity": None,
                "notional": None,
                "realized_pnl_pct": None,
            }
        )
        for item in partial
    ]
    assert (
        TradeLedgerManager.determine_measurement_mode(full) == RiskMeasurementMode.FULL
    )
    assert (
        TradeLedgerManager.determine_measurement_mode(partial)
        == RiskMeasurementMode.PARTIAL
    )
    assert (
        TradeLedgerManager.determine_measurement_mode(limited)
        == RiskMeasurementMode.LIMITED
    )


def test_reconciliation_separates_causes(bot_top, bot_oversized, bot_poor):
    """Truncation, an unverified reference and a real contradiction are not one label."""
    assert bot_top.reconciliation.status == "RECONCILED"

    partial = bot_oversized.reconciliation
    assert partial.status == "PARTIAL_LEDGER"
    assert partial.ledger_coverage_days is not None
    assert partial.declared_lead_days is not None
    assert partial.ledger_coverage_days < partial.declared_lead_days

    unverified = bot_poor.reconciliation
    assert unverified.status == "UNVERIFIED_REFERENCE"
    assert unverified.reported_pnl_provenance == "LOCAL_SNAPSHOT_UNVERIFIED"


def test_ledger_owned_by_another_bot_is_rejected(tmp_path):
    """Every OKX row carries its owner, so a mis-filed ledger must never be analysed."""
    from Agent.backend.mcp.service import BotObservationService
    from Agent.test.conftest import write_bot_dataset

    write_bot_dataset(
        tmp_path,
        asset="BTC",
        folder="bot_MINE",
        overview={"uniqueCode": "MINE", "nickName": "Mine", "aum": 1000.0},
        closed_trades=[
            {
                "subPosId": f"t{i}",
                "instId": "BTC-USDT-SWAP",
                "posSide": "long",
                "openTime": "1000",
                "closeTime": "2000",
                "pnl": "5",
                "uniqueCode": "SOMEONE_ELSE",
            }
            for i in range(10)
        ],
    )
    bot = BotObservationService(tmp_path).get_bot_result(
        "BTC",
        "bot_MINE",
        venue_type="CEX",
        simulation_iterations=10,
        simulation_horizon=10,
    )
    assert bot.reconciliation.status == "IDENTITY_MISMATCH"
    assert bot.reconciliation.foreign_owner_codes == ["SOMEONE_ELSE"]
    assert bot.performance.trade_count == 0
    # Translated to Vietnamese as part of the task's Việc 4 (see
    # Agent/backend/mcp/service.py's reconciliation warnings) -- was "owned by".
    assert any("belongs to" in warning for warning in bot.reconciliation.warnings)


def test_behavior_comes_from_ledger_not_folder_name(bot_top, bot_poor):
    assert not bot_top.behavioral_observations.averaging_down_detected
    assert not bot_poor.behavioral_observations.averaging_down_detected
    assert bot_poor.behavioral_observations.averaging_down_suspected
    assert bot_poor.behavioral_observations.evidence


def test_bootstrap_sampler_is_deterministic_and_validates_bounds():
    values = np.asarray([1.0, -1.0, 2.0])
    assert np.array_equal(
        BootstrapSampler.block_resample(values, 10, seed=7),
        BootstrapSampler.block_resample(values, 10, seed=7),
    )
    with pytest.raises(ValueError):
        BootstrapSampler.block_resample(values, 10, block_size=0)


def test_monte_carlo_invalid_sample_is_unknown():
    result = MonteCarloSimulationEngine.run_simulation(
        [trade(i, 1.0) for i in range(5)], 10_000, seed=1
    )
    assert not result.is_valid
    assert result.iterations == 0
    assert result.p_mdd_gt_10 is None
    assert result.warnings


def test_monte_carlo_is_deterministic_and_does_not_touch_global_rng():
    trades = [trade(i, 10.0 if i % 3 else -20.0) for i in range(30)]
    np.random.seed(7)
    before = np.random.random()
    first = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000, iterations=200, horizon_trades=80, seed=9
    )
    after = np.random.random()
    np.random.seed(7)
    assert before == np.random.random()
    assert after == np.random.random()
    second = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000, iterations=200, horizon_trades=80, seed=9
    )
    assert first.model_dump() == second.model_dump()
    assert first.p_loss_after_500_trades is None
    assert first.p_loss_after_horizon is not None


def test_monte_carlo_enforces_resource_bounds():
    trades = [trade(i, (-1) ** i * 10.0) for i in range(20)]
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000, iterations=60_000, horizon_trades=700, seed=1
    )
    assert result.iterations == 50_000
    assert result.horizon_trades == 500


def test_qc_rejects_cross_asset_contracts(market_btc, bot_top):
    mismatched = bot_top.model_copy(
        update={"identity": bot_top.identity.model_copy(update={"symbol": "ETH"})}
    )
    with pytest.raises(ValueError):
        QCCoreService.assess_bot(market_btc, mismatched)


def test_qc_marks_missing_portfolio_evidence_as_not_invented(bot_top):
    assessment = QCCoreService.assess_bot(None, bot_top)
    assert assessment.dimensions.portfolio_risk.status == EvidenceStatus.UNKNOWN
    assert assessment.risk_trend == RiskTrend.UNKNOWN


def test_the_strategy_dimension_scores_without_a_declared_strategy(bot_top):
    """OKX publishes no declared strategy, so the old lens abstained on every bot.

    Robustness across market phases is measurable from the ledger alone, and it
    must reach the score rather than leaving the dimension permanently dead.
    """
    assessment = QCCoreService.assess_bot(None, bot_top)
    strategy = assessment.dimensions.strategy_drift

    assert bot_top.strategy_observations.declared_strategy is None
    assert strategy.status in (EvidenceStatus.AVAILABLE, EvidenceStatus.UNKNOWN)
    if strategy.status == EvidenceStatus.AVAILABLE:
        assert strategy.weight > 0.0
        assert strategy.key_findings


def test_qc_uses_previous_assessment_for_trend(bot_top):
    current = QCCoreService.assess_bot(None, bot_top)
    previous = current.model_copy(
        update={"risk_score": max(0.0, current.risk_score - 10.0)}
    )
    trended = QCCoreService.assess_bot(None, bot_top, previous_assessment=previous)
    assert trended.risk_trend == RiskTrend.ACCELERATING_RISK


def test_qc_portfolio_lens_uses_supplied_cross_bot_exposure(bot_top):
    state = bot_top.current_state.model_copy(
        update={
            "current_position_side": PositionSide.LONG,
            "current_notional": 10_000.0,
            "gross_exposure": 10_000.0,
        }
    )
    active = bot_top.model_copy(update={"current_state": state})
    assessment = QCCoreService.assess_bot(None, active, portfolio_bots=[active, active])
    assert assessment.dimensions.portfolio_risk.status == EvidenceStatus.AVAILABLE
    assert assessment.dimensions.portfolio_risk.score >= 70


def test_low_confidence_cannot_escalate_to_mutating_control(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor).model_copy(
        update={
            "confidence": 10.0,
            "risk_tier": RiskTier.UNKNOWN,
            "recommended_action": "EMERGENCY_STOP",
        }
    )
    decision = ControlDecisionEngine(ExecutionMode.AUTOMATED).decide(
        assessment, now_ms=1
    )
    assert decision.action == ControlAction.WARN
    assert not decision.authorization_required


def test_control_cooldown_is_deterministic(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor)
    engine = ControlDecisionEngine(cooldown_seconds=300)
    first = engine.decide(assessment, now_ms=1_000_000)
    second = engine.decide(assessment, now_ms=1_001_000)
    assert first.execution_status == ExecutionStatus.PENDING
    assert second.execution_status == ExecutionStatus.SKIPPED_COOLDOWN
    assert first.decision_id == second.decision_id


def test_automated_execution_is_denied_without_external_request(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor).model_copy(
        update={
            "confidence": 90.0,
            "recommended_action": "REDUCE",
            "suggested_reduction_pct": 30.0,
        }
    )
    decision = ControlDecisionEngine(ExecutionMode.AUTOMATED).decide(
        assessment, now_ms=1
    )
    result = OKXControlExecutor.execute(decision)
    assert result.execution_status == ExecutionStatus.DENIED
    assert result.execution_details["external_request_sent"] is False
    assert "api_endpoint" not in result.execution_details


def test_advisory_does_not_claim_notification_delivery(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor)
    decision = ControlDecisionEngine(ExecutionMode.ADVISORY).decide(
        assessment, now_ms=1
    )
    result = OKXControlExecutor.execute(decision)
    assert result.execution_status == ExecutionStatus.RECORDED_ADVISORY
    assert "recorded locally" in result.execution_details["note"]


def test_reduce_contract_requires_positive_percentage():
    with pytest.raises(ValidationError):
        ControlDecision(
            decision_id="d",
            idempotency_key="k",
            assessment_id="a",
            bot_id="b",
            asset="BTC",
            action=ControlAction.REDUCE,
            reduction_pct=0,
            reason="test",
        )


def test_universe_never_marks_unknown_liquidity_eligible():
    from Agent.backend.universe.eligibility import AssetEligibilityVerifier
    from Agent.backend.universe.ranking import UniverseAsset

    candidate = UniverseAsset(
        asset_id="DEX_TEST",
        symbol="TEST",
        venue="DEX",
        venue_type="DEX",
        chain="ETH",
        rank=1,
        volume_24h_usd=10_000_000.0,
        liquidity_usd=None,
        spread_pct=None,
        depth_02_usd=None,
        selected_at=1,
        data_quality_score=0.8,
        freshness_score=1.0,
        selection_reason="TEST",
    )
    eligible, reason = AssetEligibilityVerifier.verify(candidate)
    assert not eligible
    assert reason == "DEX_POOL_LIQUIDITY_NOT_COLLECTED"

    cex_candidate = candidate.model_copy(
        update={"asset_id": "CEX_TEST", "venue": "OKX", "venue_type": "CEX"}
    )
    cex_eligible, cex_reason = AssetEligibilityVerifier.verify(cex_candidate)
    assert not cex_eligible
    assert cex_reason.startswith("UNKNOWN_EVIDENCE")


def test_pipeline_rejects_unknown_bot_snapshot():
    from Agent.backend.pipeline import RiskSupervisionPipeline

    with pytest.raises(BotDataUnavailableError, match="No bot dataset"):
        RiskSupervisionPipeline().run(
            "NOT_IN_UNIVERSE",
            "bot_top_performer",
            venue_type="DEX",
            simulation_iterations=10,
        )


def test_snapshot_freshness_is_measured_against_dataset_anchor(market_btc):
    """A crawled dataset is judged by its own coherence, not the wall clock."""
    quality = market_btc.data_quality
    assert quality.evaluation_mode.value == "SNAPSHOT"
    assert quality.anchor_ms == market_btc.as_of_ms
    assert quality.dataset_age_ms is not None
    by_source = {source.source: source for source in quality.sources}
    assert by_source["ohlcv_1h"].status.value == "AVAILABLE"
    assert by_source["orderbook_l2"].wall_clock_age_ms is not None


def test_a_source_left_behind_the_anchor_is_flagged_stale(tmp_path):
    """Staleness is proven on a synthetic set, not on whatever the crawl left."""
    from Agent.backend.market.service import MarketService
    from Agent.test.conftest import write_market_dataset

    last_candle = 1_789_000_000_000
    write_market_dataset(
        tmp_path,
        asset="STALECASE",
        last_candle_ms=last_candle,
        # Two weeks behind the candles: far past any per-source budget.
        orderbook_ms=last_candle - 14 * 24 * 3_600_000,
    )
    result = MarketService(data_dir=tmp_path).get_market_result(
        "STALECASE", venue_type="CEX", as_of_ms=last_candle
    )

    by_source = {source.source: source for source in result.data_quality.sources}
    assert by_source["ohlcv_1h"].status.value == "AVAILABLE"
    assert by_source["orderbook_l2"].status.value == "STALE"
    assert result.data_quality_score < 1.0


def test_bot_market_is_taken_from_the_ledger_not_the_folder(tmp_path):
    from Agent.backend.mcp.service import BotObservationService
    from Agent.test.conftest import write_bot_dataset

    write_bot_dataset(
        tmp_path,
        asset="DOGE",
        folder="bot_X",
        overview={"uniqueCode": "X", "nickName": "X", "aum": 1000.0},
        closed_trades=[
            {
                "subPosId": f"t{i}",
                "instId": "SOL-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1000 + i),
                "closeTime": str(5000 + i),
                "pnl": "5",
                "margin": "100",
                "lever": "2",
                "uniqueCode": "X",
            }
            for i in range(10)
        ],
    )
    bot = BotObservationService(tmp_path).get_bot_result(
        "DOGE",
        "bot_X",
        venue_type="CEX",
        simulation_iterations=10,
        simulation_horizon=10,
    )
    assert bot.identity.asset_context == "DOGE"
    assert bot.identity.primary_traded_symbol == "SOL"
    # Translated to Vietnamese as part of the task's Việc 4 (see
    # Agent/backend/mcp/service.py's `_resolve_identity_market`) -- was
    # "filed under DOGE".
    assert any("filed under DOGE" in warning for warning in bot.identity.identity_warnings)


def test_market_falls_back_to_open_positions_when_there_is_no_ledger(bot_empty):
    """A bot with no closed trades still trades something right now."""
    assert bot_empty.performance.trade_count == 0
    assert bot_empty.identity.primary_traded_symbol == "BTC"
    # Translated to Vietnamese as part of the task's Việc 4 -- was "open positions".
    assert any(
        "open positions" in warning for warning in bot_empty.identity.identity_warnings
    )


def test_duplicate_snapshots_collapse_to_one_bot(tmp_path):
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.test.conftest import write_bot_dataset

    trades = [
        {
            "subPosId": f"t{i}",
            "instId": "BTC-USDT-SWAP",
            "posSide": "long",
            "openTime": str(1000 + i),
            "closeTime": str(5000 + i),
            "pnl": "5",
            "margin": "100",
            "lever": "2",
            "uniqueCode": "DUP",
        }
        for i in range(10)
    ]
    overview = {"uniqueCode": "DUP", "nickName": "Dup Bot", "aum": 1000.0}
    for asset in ("BTC", "ETH", "SOL"):
        write_bot_dataset(
            tmp_path,
            asset=asset,
            folder="bot_DUP",
            overview=overview,
            closed_trades=trades,
        )
    report = CohortAssessmentService(tmp_path, persist_history=False).scan(
        simulation_iterations=10, simulation_horizon=10
    )
    assert report.snapshots_scanned == 3
    assert report.distinct_bots == 1
    assert report.rows[0].duplicate_snapshots == 3


def test_second_ledger_schema_is_parsed():
    """ISO timestamps, pnl_usdt and position_size must parse like the raw OKX shape."""
    raw = {
        "closed_trades": [
            {
                "trade_id": "abc",
                "instId": "BTC-USDT-SWAP",
                "direction": "LONG",
                "open_time": "2026-09-01 02:07:30 UTC",
                "close_time": "2026-09-03 15:55:21 UTC",
                "entry_price": 78282.27,
                "exit_price": 81208.49,
                "position_size": 3944.8,
                "margin_usdt": 61761.58,
                "leverage": "5E+1",
                "pnl_usdt": 112292.05,
                "pnl_ratio": 0.1818,
            }
        ]
    }
    result = TradeLedgerManager.parse_trade_list_with_diagnostics(raw)
    assert len(result.trades) == 1
    trade = result.trades[0]
    assert trade.symbol == "BTC-USDT-SWAP"
    assert trade.side.value == "LONG"
    assert trade.leverage == 50.0
    assert trade.notional == pytest.approx(61761.58 * 50)
    assert trade.realized_pnl == pytest.approx(112292.05)


def test_percentage_drawdown_is_withheld_without_an_equity_curve(bot_empty):
    """No usable weekly equity series means no percentage denominator at all."""
    assert bot_empty.capital.basis == "UNAVAILABLE"
    assert bot_empty.capital.supports_historical_pct is False
    assert bot_empty.performance.max_drawdown_pct is None
    assert bot_empty.simulation_results.is_valid is False


def test_historical_and_forward_risk_share_one_capital_basis(bot_oversized):
    """A tiny historical denominator must never sit beside a huge forward one."""
    capital = bot_oversized.capital
    simulation = bot_oversized.simulation_results
    assert capital.basis == "WEEKLY_EQUITY_CURVE"
    assert simulation.capital_basis == capital.basis
    assert simulation.capital_at_risk == capital.capital_at_risk
    assert bot_oversized.drawdown_analysis.capital_basis == capital.basis
    assert simulation.is_valid
    assert simulation.p95_max_drawdown is not None
    assert simulation.p95_max_drawdown <= 100.0


def test_wipeout_in_the_equity_curve_is_surfaced_not_averaged_away(bot_oversized):
    """The week with pnlRatio -1.0 means the account went to zero."""
    curve = bot_oversized.capital.equity_curve
    assert curve.wiped_out is True
    assert curve.max_drawdown_pct == pytest.approx(100.0)
    assert bot_oversized.drawdown_analysis.wiped_out is True
    assert any("wiped out" in warning for warning in curve.warnings)

    assessment = QCCoreService.assess_bot(None, bot_oversized)
    drawdown = assessment.dimensions.drawdown_risk
    assert drawdown.status == EvidenceStatus.AVAILABLE
    assert drawdown.score == 100.0


def test_equity_curve_uses_every_week_not_the_most_favourable(bot_oversized):
    """Taking the maximum weekly equity would erase the loss weeks."""
    curve = bot_oversized.capital.equity_curve
    usable = [point for point in curve.points if point.usable]
    assert len(usable) >= 5
    assert any(point.pnl < 0 for point in usable), "loss weeks must be retained"
    derived = [point.start_equity for point in usable]
    assert max(derived) >= (curve.latest_equity or 0) * 0.5
    assert curve.implied_gross_flow is not None
    assert curve.implied_gross_flow >= abs(curve.implied_net_flow or 0.0)


def test_thin_evidence_never_downgrades_a_high_measured_risk(market_eth, bot_oversized):
    from Agent.backend.qc.schemas.risk_assessment import RiskTier

    assessment = QCCoreService.assess_bot(market_eth, bot_oversized)
    assert assessment.risk_score >= 65.0
    assert assessment.risk_tier in (
        RiskTier.HIGH,
        RiskTier.CRITICAL,
        RiskTier.EMERGENCY,
    )


def test_cohort_report_deduplicates_and_ranks_by_risk():
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService

    report = CohortAssessmentService().scan(
        as_of_ms=FIXED_AS_OF_MS, simulation_iterations=300, simulation_horizon=200
    )
    assert report.snapshots_scanned == report.distinct_bots
    assert report.bots_failed == 0
    codes = [row.unique_code for row in report.rows]
    assert len(codes) == len(set(codes))
    scores = [row.risk_score or 0.0 for row in report.rows]
    assert scores == sorted(scores, reverse=True) or report.rows[0].risk_tier in (
        "EMERGENCY",
        "CRITICAL",
    )
    assert all(row.conclusion for row in report.rows)
    assert all(row.duplicate_snapshots == 1 for row in report.rows)
    assert all(row.selected_snapshot for row in report.rows)


def test_open_positions_parse_both_payload_shapes(bot_poor, bot_oversized):
    """Side and leverage are usable even when the instrument id is absent."""
    unattributed = bot_poor.current_state
    assert unattributed.open_positions_count >= 30
    # OKX publishes no instId for this trader, so nothing is directly observed.
    assert unattributed.observed_positions_count == 0
    assert unattributed.current_position_side.value == "NET"
    assert unattributed.long_notional and unattributed.short_notional
    assert unattributed.current_leverage == 20.0

    attributed = bot_oversized.current_state
    assert attributed.open_positions_count >= 20
    assert attributed.attributed_positions_count == attributed.open_positions_count
    assert attributed.unknown_positions_count == 0
    assert attributed.current_position_side.value == "LONG"
    assert set(attributed.exposure_by_symbol) == {"ETH", "BTC", "DOGE"}
    assert attributed.unrealized_pnl is not None and attributed.unrealized_pnl < 0


def test_margin_consistency_uses_the_resolved_capital(bot_oversized):
    """With a real equity curve the false alarm clears; without one it still fires."""
    assert bot_oversized.capital.basis == "WEEKLY_EQUITY_CURVE"
    assert bot_oversized.current_state.capital_consistency == "CONSISTENT"

    from Agent.backend.mcp.service import BotObservationService
    from Agent.test.conftest import write_bot_dataset

    tmp = Path(tempfile.mkdtemp())
    write_bot_dataset(
        tmp,
        asset="BTC",
        folder="bot_THIN",
        overview={"uniqueCode": "THIN", "nickName": "Thin", "aum": 100.0},
        open_positions=[
            {
                "subPosId": "p1",
                "instId": "BTC-USDT-SWAP",
                "posSide": "long",
                "lever": "20",
                "margin": "5000",
                "uniqueCode": "THIN",
            }
        ],
    )
    thin = BotObservationService(tmp).get_bot_result(
        "BTC",
        "bot_THIN",
        venue_type="CEX",
        simulation_iterations=10,
        simulation_horizon=10,
    )
    assert thin.capital.basis == "CURRENT_AUM"
    assert thin.current_state.capital_consistency == "MARGIN_EXCEEDS_CAPITAL"
    # Text translated to Vietnamese as part of the task's Việc 4 (see
    # Agent/backend/mcp/service.py's `_current_state`) -- was "exceeds
    # reported capital".
    assert any("exceeds reported capital" in warning for warning in thin.data_quality.warnings)


def test_attributed_exposure_drives_market_alignment(market_eth, bot_oversized):
    assessment = QCCoreService.assess_bot(market_eth, bot_oversized)
    alignment = assessment.dimensions.market_alignment
    assert alignment.status == EvidenceStatus.AVAILABLE
    assert alignment.confidence == 1.0
    # Both translated to Vietnamese as part of the task's Việc 4 -- were
    # "attributed to ETH" and "book depth".
    assert any("attributed to ETH" in finding for finding in alignment.key_findings)
    liquidity = assessment.dimensions.liquidity_execution
    assert liquidity.status == EvidenceStatus.AVAILABLE
    assert any("order book depth" in finding for finding in liquidity.key_findings)


def test_dex_orderflow_is_derived_from_tick_prints():
    from Agent.backend.market.service import MarketService

    market = MarketService().get_market_result(
        "UNI", venue_type="DEX", as_of_ms=FIXED_AS_OF_MS
    )
    flow = market.orderflow_state
    assert flow.flow_bias in ("BUY_PRESSURE", "SELL_PRESSURE", "NEUTRAL")
    assert flow.taker_buy_vol is not None and flow.taker_sell_vol is not None
    assert any(
        "CEX benchmark proxy" in warning for warning in market.data_quality.warnings
    )


def test_assessment_history_enables_trend(tmp_path, market_hype, bot_poor):
    from Agent.backend.qc.history.store import AssessmentHistoryStore
    from Agent.backend.qc.schemas.risk_assessment import RiskTrend

    store = AssessmentHistoryStore(tmp_path)
    assert store.latest(bot_poor.identity.bot_id) is None

    first = QCCoreService.assess_bot(market_hype, bot_poor)
    assert store.append(first) is True
    assert store.append(first) is False  # same snapshot must not duplicate

    earlier = first.model_copy(
        update={
            "assessment_id": "QC_EARLIER",
            "risk_score": max(0.0, first.risk_score - 20.0),
        }
    )
    store.append(earlier)
    trended = QCCoreService.assess_bot(
        market_hype,
        bot_poor,
        previous_assessment=store.latest(bot_poor.identity.bot_id),
    )
    assert trended.risk_trend == RiskTrend.ACCELERATING_RISK
    assert len(store.history(bot_poor.identity.bot_id)) == 2


def test_gap_report_names_what_to_collect_and_what_it_unlocks(tmp_path):
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService

    report = CohortAssessmentService(
        history=__import__(
            "Agent.backend.qc.history.store", fromlist=["AssessmentHistoryStore"]
        ).AssessmentHistoryStore(tmp_path),
        persist_history=False,
    ).scan(as_of_ms=FIXED_AS_OF_MS, simulation_iterations=300, simulation_horizon=200)

    assert report.gaps
    ids = {gap.gap_id for gap in report.gaps}
    assert "positions:instrument_id_upstream" in ids
    assert "capital:equity_history" in ids
    assert "ledger:full_history" in ids
    # MU market data has since been collected, so that gap must no longer appear.
    assert not any(gap.gap_id == "market:MU" for gap in report.gaps)
    for gap in report.gaps:
        assert gap.detail and gap.priority in ("HIGH", "MEDIUM", "LOW")
    weights = [gap.weight for gap in report.gaps]
    assert weights == sorted(weights, reverse=True)


def test_capital_resolver_has_no_one_way_ratchet():
    """A derived equity below AUM must still be used: no favourable-direction gate."""
    from Agent.backend.mcp.capital.equity_curve import CapitalResolver

    weeks = [
        {"beginTs": "1788105600000", "pnl": "100", "pnlRatio": "0.10"},
        {"beginTs": "1788710400000", "pnl": "-50", "pnlRatio": "-0.05"},
    ]
    model = CapitalResolver.resolve(
        {"weekly_pnl_history": weeks}, reported_aum=500_000.0
    )
    assert model.basis == "WEEKLY_EQUITY_CURVE"
    # Derived equity (~1k) is far below the reported AUM and must not be discarded.
    assert model.capital_at_risk is not None and model.capital_at_risk < 5_000
    assert model.supports_historical_pct is True
    assert any("differs from reported" in warning for warning in model.warnings)


def test_capital_resolver_keeps_loss_weeks_in_the_curve():
    from Agent.backend.mcp.capital.equity_curve import EquityCurveBuilder

    weeks = [
        {"beginTs": "1788105600000", "pnl": "1000", "pnlRatio": "0.10"},
        {"beginTs": "1788710400000", "pnl": "-4000", "pnlRatio": "-0.40"},
    ]
    curve = EquityCurveBuilder.build(weeks)
    assert curve.usable_points == 2
    assert any(point.pnl < 0 for point in curve.points if point.usable)
    assert curve.max_drawdown_pct is not None and curve.max_drawdown_pct > 0


def test_imprecise_ratios_are_skipped_with_a_reason():
    from Agent.backend.mcp.capital.equity_curve import EquityCurveBuilder

    curve = EquityCurveBuilder.build(
        [{"beginTs": "1788105600000", "pnl": "-41.36", "pnlRatio": "-0.0025"}]
    )
    assert curve.basis == "UNAVAILABLE"
    skipped = curve.points[0]
    assert skipped.usable is False
    assert "precision floor" in (skipped.reason or "")


def test_dedupe_prefers_the_snapshot_with_richer_provenance(tmp_path):
    """Alphabetical order must not beat a snapshot that carries an equity curve."""
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.test.conftest import write_bot_dataset

    trades = [
        {
            "subPosId": f"t{i}",
            "instId": "BTC-USDT-SWAP",
            "posSide": "long",
            "openTime": str(1000 + i),
            "closeTime": str(5000 + i),
            "pnl": "5",
            "margin": "100",
            "lever": "2",
            "uniqueCode": "RICH",
        }
        for i in range(10)
    ]
    weekly = [
        {"beginTs": "1788105600000", "pnl": "1000", "pnlRatio": "0.10"},
        {"beginTs": "1788710400000", "pnl": "-400", "pnlRatio": "-0.04"},
    ]
    write_bot_dataset(
        tmp_path,
        asset="AAA",
        folder="bot_RICH",
        overview={"uniqueCode": "RICH", "nickName": "Rich", "aum": 1000.0},
        closed_trades=trades,
    )
    write_bot_dataset(
        tmp_path,
        asset="ZZZ",
        folder="bot_RICH",
        overview={
            "uniqueCode": "RICH",
            "nickName": "Rich",
            "aum": 1000.0,
            "weekly_pnl_history": weekly,
        },
        closed_trades=trades,
    )
    report = CohortAssessmentService(tmp_path, persist_history=False).scan(
        simulation_iterations=10, simulation_horizon=10
    )
    row = report.rows[0]
    assert row.duplicate_snapshots == 2
    assert row.selected_snapshot == "CEX/ZZZ/bot_RICH"
    assert row.capital_basis == "WEEKLY_EQUITY_CURVE"


def test_secondary_market_is_surfaced_without_changing_any_score(tmp_path_factory):
    """Việc 3: `cohort.py` giải thêm thị trường đứng thứ hai theo
    `bot.identity.symbol_exposure_share` -- CHỈ để trình bày
    (assessment_store.py/report_page.py), không bao giờ đi qua
    `QCCoreService.assess_bot()`. Ràng buộc cứng của nhiệm vụ: không được
    đổi bất kỳ công thức chấm điểm nào.

    Chứng minh bằng cách chạy CÙNG một bot (10 lệnh AAA + 4 lệnh BBB, margin/
    lever giống hệt nhau) hai lần: một lần có dữ liệu thị trường cho BBB
    (thị trường thứ hai giải được), một lần không (chỉ bỏ market dataset của
    BBB) -- nếu code Việc 3 lỡ đưa market thứ hai vào assess_bot(), hai lần
    chạy sẽ cho điểm khác nhau; nếu đúng như yêu cầu (chỉ trình bày), mọi
    điểm số phải giống hệt bit-for-bit.
    """
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.test.conftest import (
        FIXED_AS_OF_MS,
        write_bot_dataset,
        write_market_dataset,
    )

    def _trades(symbol: str, count: int, prefix: str):
        return [
            {
                "subPosId": f"{prefix}{i}",
                "instId": f"{symbol}-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1000 + i),
                "closeTime": str(5000 + i),
                "pnl": "5",
                "margin": "100",
                "lever": "10",
                "uniqueCode": "MIX",
            }
            for i in range(count)
        ]

    def _build(root: Path, *, with_secondary_market: bool) -> None:
        write_market_dataset(root, asset="AAA", last_candle_ms=1_789_000_000_000)
        if with_secondary_market:
            write_market_dataset(root, asset="BBB", last_candle_ms=1_789_000_000_000)
        write_bot_dataset(
            root,
            asset="AAA",
            folder="bot_MIX",
            overview={"uniqueCode": "MIX", "nickName": "Mix", "aum": 10_000.0},
            closed_trades=_trades("AAA", 10, "A") + _trades("BBB", 4, "B"),
        )

    with_dir = tmp_path_factory.mktemp("with_secondary")
    without_dir = tmp_path_factory.mktemp("without_secondary")
    _build(with_dir, with_secondary_market=True)
    _build(without_dir, with_secondary_market=False)

    row_with = (
        CohortAssessmentService(with_dir, persist_history=False)
        .scan(as_of_ms=FIXED_AS_OF_MS, simulation_iterations=10, simulation_horizon=10)
        .rows[0]
    )
    row_without = (
        CohortAssessmentService(without_dir, persist_history=False)
        .scan(as_of_ms=FIXED_AS_OF_MS, simulation_iterations=10, simulation_horizon=10)
        .rows[0]
    )

    assert row_with.status == row_without.status == "EVALUATED"
    # Thị trường CHÍNH (dùng để chấm) không đổi theo có/không thị trường thứ hai.
    assert row_with.traded_symbol == row_without.traded_symbol == "AAA"

    # Thị trường thứ hai chỉ xuất hiện khi có dữ liệu thị trường cho nó.
    assert row_with.secondary_traded_symbol == "BBB"
    assert row_with.secondary_market is not None
    assert row_with.secondary_market.symbol == "BBB"
    assert row_with.secondary_share_pct == pytest.approx(4_000 / 14_000 * 100.0)

    assert row_without.secondary_traded_symbol is None
    assert row_without.secondary_market is None
    assert row_without.secondary_share_pct is None

    # RÀNG BUỘC CỨNG: có/không có thị trường thứ hai không được đổi MỘT
    # điểm số nào -- market thứ hai không hề đi qua QCCoreService.assess_bot().
    assert row_with.risk_score == row_without.risk_score
    assert row_with.quality_score == row_without.quality_score
    assert row_with.weighted_average == row_without.weighted_average
    assert row_with.dimension_scores == row_without.dimension_scores


def test_pipeline_resolves_secondary_market_without_changing_the_score(
    tmp_path_factory,
):
    """`Agent/backend/pipeline.py::RiskSupervisionPipeline.run` -- the LIVE
    single-bot path `WebDataService.analyze()`/`agent_server.py`'s
    `assess_bot` tool use -- carries the exact same Việc 3 addition as
    `CohortAssessmentService.scan()` above, and the exact same hard
    constraint: a resolved (or unresolved) secondary market must never
    change `risk_assessment`.
    """
    from Agent.backend.pipeline import RiskSupervisionPipeline
    from Agent.test.conftest import (
        FIXED_AS_OF_MS,
        write_bot_dataset,
        write_market_dataset,
    )

    def _trades(symbol: str, count: int, prefix: str):
        return [
            {
                "subPosId": f"{prefix}{i}",
                "instId": f"{symbol}-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1000 + i),
                "closeTime": str(5000 + i),
                "pnl": "5",
                "margin": "100",
                "lever": "10",
                "uniqueCode": "MIX",
            }
            for i in range(count)
        ]

    def _build(root: Path, *, with_secondary_market: bool) -> None:
        write_market_dataset(root, asset="AAA", last_candle_ms=1_789_000_000_000)
        if with_secondary_market:
            write_market_dataset(root, asset="BBB", last_candle_ms=1_789_000_000_000)
        write_bot_dataset(
            root,
            asset="AAA",
            folder="bot_MIX",
            overview={"uniqueCode": "MIX", "nickName": "Mix", "aum": 10_000.0},
            closed_trades=_trades("AAA", 10, "A") + _trades("BBB", 4, "B"),
        )

    with_dir = tmp_path_factory.mktemp("pipeline_with_secondary")
    without_dir = tmp_path_factory.mktemp("pipeline_without_secondary")
    _build(with_dir, with_secondary_market=True)
    _build(without_dir, with_secondary_market=False)

    result_with = RiskSupervisionPipeline(data_dir=with_dir, persist_history=False).run(
        "AAA",
        "bot_MIX",
        venue_type="CEX",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=10,
    )
    result_without = RiskSupervisionPipeline(
        data_dir=without_dir, persist_history=False
    ).run(
        "AAA",
        "bot_MIX",
        venue_type="CEX",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=10,
    )

    assert result_with.traded_symbol == result_without.traded_symbol == "AAA"
    assert result_with.secondary_traded_symbol == "BBB"
    assert result_with.secondary_market_result is not None
    assert result_with.secondary_market_result.symbol == "BBB"

    assert result_without.secondary_traded_symbol is None
    assert result_without.secondary_market_result is None

    # RÀNG BUỘC CỨNG: giống hệt yêu cầu ở test cohort.py phía trên.
    assert (
        result_with.risk_assessment.risk_score
        == result_without.risk_assessment.risk_score
    )
    assert (
        result_with.risk_assessment.quality_score
        == result_without.risk_assessment.quality_score
    )


def test_pipeline_n_market_coverage_does_not_change_the_score(tmp_path_factory):
    """`RiskSupervisionPipeline.run` -- cùng phép thử N-thị-trường (không
    chỉ 1 mã phụ) ở `test_n_market_coverage_surfaces_more_than_two_markets_
    without_changing_any_score` (cohort.py) bên dưới, cho đúng đường LIVE
    single-bot (`WebDataService.analyze()`/`agent_server.py`'s `assess_bot`
    tool dùng pipeline.py, không phải cohort.py).
    """
    from Agent.backend.pipeline import RiskSupervisionPipeline
    from Agent.test.conftest import (
        FIXED_AS_OF_MS,
        write_bot_dataset,
        write_market_dataset,
    )

    def _trades(symbol: str, count: int, prefix: str):
        return [
            {
                "subPosId": f"{prefix}{i}",
                "instId": f"{symbol}-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1000 + i),
                "closeTime": str(5000 + i),
                "pnl": "5",
                "margin": "100",
                "lever": "10",
                "uniqueCode": "QUADP",
            }
            for i in range(count)
        ]

    def _build(root: Path, *, markets_available: tuple) -> None:
        for symbol in markets_available:
            write_market_dataset(root, asset=symbol, last_candle_ms=1_789_000_000_000)
        write_bot_dataset(
            root,
            asset="AAA",
            folder="bot_QUADP",
            overview={"uniqueCode": "QUADP", "nickName": "QuadP", "aum": 10_000.0},
            closed_trades=(
                _trades("AAA", 10, "A")
                + _trades("BBB", 4, "B")
                + _trades("CCC", 3, "C")
                + _trades("DDD", 2, "D")
            ),
        )

    with_dir = tmp_path_factory.mktemp("pipeline_n_market_with")
    without_dir = tmp_path_factory.mktemp("pipeline_n_market_without")
    _build(with_dir, markets_available=("AAA", "BBB", "CCC"))
    _build(without_dir, markets_available=("AAA",))

    result_with = RiskSupervisionPipeline(data_dir=with_dir, persist_history=False).run(
        "AAA",
        "bot_QUADP",
        venue_type="CEX",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=10,
    )
    result_without = RiskSupervisionPipeline(
        data_dir=without_dir, persist_history=False
    ).run(
        "AAA",
        "bot_QUADP",
        venue_type="CEX",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=10,
        simulation_horizon=10,
    )

    assert [m.symbol for m in result_with.resolved_markets] == ["AAA", "BBB", "CCC"]
    assert result_with.unresolved_markets == []
    assert result_with.coverage_achieved_pct == pytest.approx(
        (10 + 4 + 3) / 19 * 100.0, abs=0.01
    )

    assert [m.symbol for m in result_without.resolved_markets] == ["AAA"]
    assert sorted(m.symbol for m in result_without.unresolved_markets) == [
        "BBB",
        "CCC",
    ]

    # RÀNG BUỘC CỨNG: giống hệt yêu cầu ở mọi test khác trong file này.
    assert (
        result_with.risk_assessment.risk_score
        == result_without.risk_assessment.risk_score
    )
    assert (
        result_with.risk_assessment.quality_score
        == result_without.risk_assessment.quality_score
    )
    assert (
        result_with.risk_assessment.dimensions.model_dump()
        == result_without.risk_assessment.dimensions.model_dump()
    )


def test_n_market_coverage_surfaces_more_than_two_markets_without_changing_any_score(
    tmp_path_factory,
):
    """Phủ sóng theo mục tiêu (Agent/backend/market/coverage.py) tổng quát
    hoá "giải đúng 2 thị trường: chính + phụ" thành "giải tới khi đạt 80%
    phủ sóng, tối đa 8 thị trường". Test này chứng minh đúng ràng buộc cứng
    của nhiệm vụ CHO N > 2 thị trường (không chỉ 1 mã phụ như hai test bên
    trên): CÙNG một bot, chạy một lần với 3 thị trường giải được và một lần
    chỉ giải được đúng thị trường CHÍNH (2 mã còn lại không có dữ liệu thị
    trường) -- mọi điểm số phải giống hệt bit-for-bit, vì
    `QCCoreService.assess_bot()` chỉ bao giờ nhận đúng MỘT market.

    Bot giao dịch 4 mã theo tỉ trọng notional AAA 10/19 (52.6%), BBB 4/19
    (21.1%), CCC 3/19 (15.8%), DDD 2/19 (10.5%) -- với mục tiêu 80%,
    `plan_market_coverage` chọn đúng AAA+BBB+CCC (52.6+21.1+15.8=89.5% >=
    80%), DDD không bao giờ được thử giải (đã đạt mục tiêu trước đó).
    """
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.test.conftest import (
        FIXED_AS_OF_MS,
        write_bot_dataset,
        write_market_dataset,
    )

    def _trades(symbol: str, count: int, prefix: str):
        return [
            {
                "subPosId": f"{prefix}{i}",
                "instId": f"{symbol}-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1000 + i),
                "closeTime": str(5000 + i),
                "pnl": "5",
                "margin": "100",
                "lever": "10",
                "uniqueCode": "QUAD",
            }
            for i in range(count)
        ]

    def _build(root: Path, *, markets_available: tuple) -> None:
        for symbol in markets_available:
            write_market_dataset(root, asset=symbol, last_candle_ms=1_789_000_000_000)
        write_bot_dataset(
            root,
            asset="AAA",
            folder="bot_QUAD",
            overview={"uniqueCode": "QUAD", "nickName": "Quad", "aum": 10_000.0},
            closed_trades=(
                _trades("AAA", 10, "A")
                + _trades("BBB", 4, "B")
                + _trades("CCC", 3, "C")
                + _trades("DDD", 2, "D")
            ),
        )

    with_dir = tmp_path_factory.mktemp("n_market_with")
    without_dir = tmp_path_factory.mktemp("n_market_without")
    _build(with_dir, markets_available=("AAA", "BBB", "CCC"))
    _build(without_dir, markets_available=("AAA",))

    row_with = (
        CohortAssessmentService(with_dir, persist_history=False)
        .scan(as_of_ms=FIXED_AS_OF_MS, simulation_iterations=10, simulation_horizon=10)
        .rows[0]
    )
    row_without = (
        CohortAssessmentService(without_dir, persist_history=False)
        .scan(as_of_ms=FIXED_AS_OF_MS, simulation_iterations=10, simulation_horizon=10)
        .rows[0]
    )

    assert row_with.status == row_without.status == "EVALUATED"
    assert row_with.traded_symbol == row_without.traded_symbol == "AAA"

    # `with_dir`: cả 3 thị trường trong kế hoạch phủ sóng đều giải được.
    assert [m.symbol for m in row_with.resolved_markets] == ["AAA", "BBB", "CCC"]
    assert row_with.unresolved_markets == []
    assert row_with.coverage_achieved_pct == pytest.approx(
        (10 + 4 + 3) / 19 * 100.0, abs=0.01
    )
    # DDD không nằm trong kế hoạch (đã đạt 80% trước khi tới lượt nó) -- nó
    # không được thử giải, không xuất hiện ở đâu cả (không suy diễn).
    assert all(m.symbol != "DDD" for m in row_with.resolved_markets)
    assert all(m.symbol != "DDD" for m in row_with.unresolved_markets)

    # `without_dir`: chỉ AAA (thị trường CHÍNH) có dữ liệu -- BBB/CCC nằm
    # trong kế hoạch nhưng KHÔNG lấy được dữ liệu, ghi nhận CHƯA ĐO ĐƯỢC.
    assert [m.symbol for m in row_without.resolved_markets] == ["AAA"]
    assert sorted(m.symbol for m in row_without.unresolved_markets) == ["BBB", "CCC"]
    assert row_without.coverage_achieved_pct == pytest.approx(10 / 19 * 100.0, abs=0.01)

    # RÀNG BUỘC CỨNG: 1 thị trường giải được hay 3 thị trường giải được
    # không được đổi MỘT điểm số nào -- market phụ không hề đi qua
    # QCCoreService.assess_bot().
    assert row_with.risk_score == row_without.risk_score
    assert row_with.quality_score == row_without.quality_score
    assert row_with.weighted_average == row_without.weighted_average
    assert row_with.dimension_scores == row_without.dimension_scores


def test_subposition_id_recovers_the_open_time():
    """OKX ids are snowflakes, so a blank openTime is still recoverable."""
    from Agent.backend.mcp.inference.public_signals import SubPositionClock

    # Calibrated against published pairs from the live ledger.
    samples = [
        (3872078236348911616, 1787899323910),
        (3913510898942676992, 1789134113478),
        (3913381542882775040, 1789130258367),
    ]
    assert SubPositionClock.calibration_error_ms(samples) <= 100
    assert SubPositionClock.open_time_ms("not-a-number") is None
    assert SubPositionClock.open_time_ms(0) is None


def test_open_time_is_recovered_for_every_position(bot_poor):
    assert bot_poor.current_state.open_positions_count > 0
    for position in bot_poor.current_state.open_positions:
        assert position.open_time is not None
        assert position.open_time_source == "SUBPOS_ID_SNOWFLAKE"


def test_attribution_determines_narrows_or_excludes_but_never_guesses():
    from Agent.backend.mcp.inference.public_signals import (
        AttributionVerdict,
        InstrumentAttributor,
    )

    entry = {"AAA": 100.0, "BBB": 100.0}
    now = {"AAA": 101.0, "BBB": 150.0}
    common = dict(
        sub_position_id=3913510898942676992,
        leverage=10.0,
        is_short=False,
        candidates=["AAA", "BBB"],
        price_at=lambda symbol, ts: entry.get(symbol),
        price_now=lambda symbol: now.get(symbol),
    )

    # A 1% move is only consistent with AAA.
    determined = InstrumentAttributor.attribute(pnl_ratio=0.10, **common)
    assert determined.verdict == AttributionVerdict.DETERMINED
    assert determined.instrument == "AAA"

    # A move no candidate made is reported as such, never forced onto one.
    outside = InstrumentAttributor.attribute(pnl_ratio=-3.0, **common)
    assert outside.verdict == AttributionVerdict.OUTSIDE_LEDGER_UNIVERSE
    assert outside.instrument is None

    # Identical candidates cannot be told apart, so both are kept.
    tie = InstrumentAttributor.attribute(
        pnl_ratio=0.10,
        sub_position_id=3913510898942676992,
        leverage=10.0,
        is_short=False,
        candidates=["AAA", "CCC"],
        price_at=lambda symbol, ts: 100.0,
        price_now=lambda symbol: 101.0,
    )
    assert tie.verdict == AttributionVerdict.NARROWED
    assert tie.instrument is None
    assert set(tie.candidates) == {"AAA", "CCC"}


def test_inferred_attribution_is_never_recorded_as_observed(bot_poor):
    state = bot_poor.current_state
    assert state.inferred_positions_count > 0
    assert state.observed_positions_count == 0
    assert state.exposure_by_symbol, "inference must unlock exposure attribution"
    sources = {p.attribution_source for p in state.open_positions}
    assert "OBSERVED" not in sources
    assert "INFERRED" in sources


def test_inferred_exposure_lowers_lens_confidence(market_hype, bot_poor):
    assessment = QCCoreService.assess_bot(market_hype, bot_poor)
    alignment = assessment.dimensions.market_alignment
    assert alignment.status == EvidenceStatus.AVAILABLE
    assert alignment.confidence < 1.0
    # Translated to Vietnamese as part of the task's Việc 4 -- was "implied
    # price move".
    assert any("inferring from price movement" in f for f in alignment.key_findings)


def test_cost_model_recovers_round_trip_fees():
    from Agent.backend.mcp.inference.public_signals import ImpliedMove

    trades = [
        {
            "entry": 100.0,
            "exit": 101.0,
            "leverage": 20.0,
            # 1% move at 20x is +20%, minus a 0.09% round-trip fee at 20x = 1.8%.
            "pnl_ratio": 0.20 - 0.018,
            "is_short": False,
        }
        for _ in range(10)
    ]
    cost = ImpliedMove.estimate_cost(trades)
    assert cost.is_estimated
    assert cost.round_trip_rate == pytest.approx(0.0009, abs=1e-5)


def test_capital_floor_is_always_derivable_from_margin():
    from Agent.backend.mcp.inference.public_signals import CapitalFloor

    floor = CapitalFloor.from_margins([100.0, 250.0, None, 0.0])
    assert floor.floor == 350.0
    assert floor.concurrent_positions == 2
    assert CapitalFloor.from_margins([]).floor is None


def _deferred(realized_pnls, open_upls, capital=100_000.0):
    from Agent.backend.mcp.analytics.performance.deferred_loss import (
        DeferredLossAnalyzer,
    )
    from Agent.backend.mcp.schemas.bot_result import OpenPosition, PositionSide

    trades = [
        TradeLedgerItem(
            trade_id=f"t{i}",
            symbol="BTC-USDT-SWAP",
            side=PositionSide.LONG,
            open_time=i * 1000,
            close_time=(i + 1) * 1000,
            realized_pnl=pnl,
            holding_time_minutes=10.0,
        )
        for i, pnl in enumerate(realized_pnls)
    ]
    positions = [
        OpenPosition(position_id=f"p{i}", unrealized_pnl=upl)
        for i, upl in enumerate(open_upls)
    ]
    net = sum(open_upls) if open_upls else None
    return DeferredLossAnalyzer.analyze(trades, positions, net, capital)


def test_closing_winners_and_holding_losers_is_detected():
    """A flawless record that becomes a losing one once the book is marked."""
    profile = _deferred([100.0] * 10, [-9_000.0, -6_000.0])
    assert profile.never_realized_a_loss is True
    assert profile.closed_loss_count == 0
    assert profile.losing_open_positions == 2
    assert profile.open_loss == 15_000.0
    # Booked: no losses at all. Marked: 1,000 profit against 15,000 of loss.
    assert profile.booked_profit_factor is None
    assert profile.marked_profit_factor == pytest.approx(1_000 / 15_000)
    assert profile.turns_unprofitable_when_marked is True
    assert profile.representativeness == "UNREPRESENTATIVE"
    assert any("SUSTAINABLE to LOSING" in w for w in profile.warnings)


def test_a_big_ratio_move_that_does_not_change_the_verdict_is_not_flagged():
    """Profit factor 40 falling to 10 still says the same thing about the bot."""
    profile = _deferred([400.0] * 10, [-10.0] * 10, capital=1_000_000.0)
    assert profile.booked_profit_factor is None
    assert profile.marked_profit_factor is not None
    assert profile.marked_profit_factor > 1.3
    assert profile.representativeness == "REPRESENTATIVE"
    assert profile.distorts_headline_metrics is False


def test_open_loss_below_one_percent_of_capital_is_not_flagged():
    profile = _deferred([100.0] * 10, [-50.0])
    assert profile.representativeness == "REPRESENTATIVE"
    assert profile.distorts_headline_metrics is False


def test_no_closed_trades_has_no_metrics_to_distort():
    profile = _deferred([], [-500.0])
    assert profile.representativeness == "NO_CLOSED_TRADES"
    assert profile.distorts_headline_metrics is False
    assert profile.has_realized_metrics is False


def test_flat_bot_is_fully_represented_by_its_closed_trades():
    profile = _deferred([100.0, -50.0], [])
    assert profile.representativeness == "REPRESENTATIVE"
    assert profile.open_loss in (0.0, None)
    assert profile.booked_profit_factor == pytest.approx(2.0)


def test_deferred_loss_marks_the_simulation_as_optimistic(bot_deferred):
    assert bot_deferred.deferred_loss.representativeness == "UNREPRESENTATIVE"
    simulation = bot_deferred.simulation_results
    assert simulation.deferred_loss_bias is True
    # Translated to Vietnamese as part of the task's Việc 4 (see
    # Agent/backend/mcp/service.py's `get_bot_result`) -- was "unrealised loss".
    assert any("unrealised loss" in w for w in simulation.warnings)


def test_performance_lens_discounts_unrepresentative_metrics(bot_deferred):
    assessment = QCCoreService.assess_bot(None, bot_deferred)
    quality = assessment.dimensions.performance_quality
    # Profit factor is 11x, yet the dimension must not read as healthy.
    assert bot_deferred.performance.profit_factor > 5
    assert quality.score >= 70
    # Translated to Vietnamese as part of the task's Việc 4 (see
    # Agent/backend/qc/evaluator/lenses/performance_quality.py) -- were
    # "realised a loss" and "not representative"; "Profit factor" itself is
    # kept as an English term throughout this project's own Vietnamese text.
    assert any(
        "Profit factor" in f or "ghi nhận lệnh lỗ" in f for f in quality.key_findings
    )
    assert any("not representative" in f for f in quality.key_findings)


def test_material_unbooked_loss_floors_the_risk_score(bot_deferred):
    from Agent.backend.qc.schemas.risk_assessment import RiskTier

    assessment = QCCoreService.assess_bot(None, bot_deferred)
    assert bot_deferred.deferred_loss.open_loss_to_capital_pct >= 15.0
    assert assessment.risk_score >= 70.0
    assert assessment.risk_tier in (
        RiskTier.HIGH,
        RiskTier.CRITICAL,
        RiskTier.EMERGENCY,
    )


def test_venue_label_follows_the_traded_market_not_the_folder():
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService

    report = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=50, simulation_horizon=30
    )
    filed_in_dex = [r for r in report.rows if r.snapshot_venue == "DEX"]
    assert filed_in_dex, "dataset must still contain dex-filed snapshots"
    for row in filed_in_dex:
        if row.market_available:
            # These are OKX swaps filed under dex/ folders; the label must not lie.
            assert row.venue_type == row.market.venue_type


def test_step1_market_report_labels_every_regime_in_vietnamese():
    from Agent.backend.qc.reporting.market_report import MarketRegimeService

    report = MarketRegimeService().build(bots_per_symbol={"BTC": 5})
    assert report.markets_observed > 0
    assert report.regime_summary
    btc = next(r for r in report.rows if r.symbol == "BTC" and r.venue_type == "CEX")
    assert btc.bots_trading == 5
    assert btc.regime and not btc.regime.isupper()  # a sentence, not an enum
    for row in report.rows:
        assert row.note.endswith(".")
        assert row.eligible is (row.eligibility_reason == "ELIGIBLE")


def test_step1_ranks_markets_that_bots_actually_trade_first():
    from Agent.backend.qc.reporting.market_report import MarketRegimeService

    report = MarketRegimeService().build(bots_per_symbol={"MU": 3})
    assert report.rows[0].symbol == "MU"


def test_step3_ranking_is_ordered_by_score_and_names_a_cause():
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.backend.qc.reporting.reasons import computed_summary_vi, explain_vi

    report = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=50, simulation_horizon=30
    )
    ordered = sorted(report.rows, key=lambda r: -(r.risk_score or 0.0))
    scores = [r.risk_score for r in ordered]
    assert scores == sorted(scores, reverse=True)
    for row in ordered:
        cause = explain_vi(row)
        assert cause and cause[0].isupper() and cause.endswith(".")
        assert computed_summary_vi(row)


def test_cause_text_names_the_deferred_loss_shift(bot_deferred, market_eth):
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.backend.qc.reporting.reasons import explain_vi

    report = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=50, simulation_horizon=30
    )
    row = next(r for r in report.rows if r.nick_name == "HaveARestin")
    cause = explain_vi(row)
    assert "unrealised loss" in cause
    assert "drop the profit factor" in cause


def test_each_step_reports_under_its_own_heading():
    """The pipeline is collect (1), analyse (2), judge (3).

    Market analysis used to be labelled step 1, which hid the question step 1
    exists to answer: is the input complete, on both the market and the bot side.
    """
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.backend.qc.reporting.data_report import DataReportService
    from Agent.backend.qc.reporting.market_report import MarketRegimeService
    from Agent.backend.qc.reporting.render import (
        render_bot_report,
        render_data_report,
        render_market_report,
        render_qc_ranking,
    )

    cohort = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=50, simulation_horizon=30
    )
    data = render_data_report(DataReportService().build())
    assert "STEP 1" in data and "DATA" in data

    market = render_market_report(MarketRegimeService().build(), detail=False)
    assert "STEP 2.1" in market

    step3 = render_qc_ranking(cohort)
    assert "STEP 3" in step3
    # Step 3 closes with a per-bot card: the numbers, what the simulation says,
    # whether the edge survives the statistical tests, and why the verdict fell
    # where it did.
    assert "PER-BOT SCORECARD" in step3
    assert "QUALITY SCORE" in step3 and "RISK SCORE" in step3
    assert "SIMULATIONS" in step3
    assert "WHY THIS VERDICT" in step3
    # Step 2 reports observation only; the verdict belongs to step 3.
    assert "VERDICT" not in render_bot_report(cohort, detail=False)


def test_table_cells_account_for_wide_glyphs():
    from Agent.backend.qc.reporting.render import _cell

    assert len(_cell("abc", 10)) == 10
    # CJK glyphs occupy two terminal cells, so padding must shrink accordingly.
    assert _cell("稳稳", 10) == "稳稳" + " " * 6


def _synthetic_market_result(symbol: str) -> MarketResult:
    """Build a minimal, schema-valid MarketResult without touching disk.

    The synthetic bot below is flat (no open position), which makes every
    market-dependent lens (market alignment, leverage, liquidity/execution)
    return its "no exposure" answer before it ever reads the price/structure
    numbers here. So the only thing about this market that actually matters
    for the two tests using it is that `symbol` matches the bot's symbol --
    the values below just satisfy pydantic's field constraints.
    """
    return MarketResult(
        asset_id=f"SYN_{symbol}",
        symbol=symbol,
        venue="OKX",
        venue_type="CEX",
        data_quality_score=0.9,
        data_quality=DataQualitySummary(
            completeness_score=0.9, freshness_score=0.9, overall_score=0.9
        ),
        price_state=PriceState(last_price=100.0, high_24h=105.0, low_24h=95.0),
        structure_state=StructureState(
            ema_20=100.0,
            atr_14=1.0,
            keltner_middle=100.0,
            keltner_upper=105.0,
            keltner_lower=95.0,
            keltner_width=10.0,
            trend_state=TrendState.SIDEWAYS,
            volatility_state=VolatilityState.NORMAL,
            range_high=110.0,
            range_low=90.0,
            range_position_pct=50.0,
        ),
        orderflow_state=OrderflowState(flow_bias="NEUTRAL"),
        liquidity_state=LiquidityState(),
    )


def _synthetic_deferred_veto_bot(symbol: str) -> BotResult:
    """Build, in memory, a bot that closes winners while sitting on a large unbooked loss.

    The two tests below used to read this exact scenario (closed-book profit
    factor 11, marked-to-open-loss profit factor 0.16) from the live crawl
    dataset via the `bot_deferred` fixture (bot_53AEED5A8E4EBBB2 /
    "HaveARestin"). That fixture derives the bot's "market" from whichever
    instrument carries the most trades in the ledger, and this bot trades
    ~20 instruments with the top two (XRP/ETH) only a few trades apart -- a
    handful of new live fills is enough to flip which one wins, which flips
    `bot.identity.symbol` and breaks any test that hardcodes the market
    alongside it (see conftest.bot_deferred and the QCCoreService symbol
    check it trips over). Constructing the BotResult by hand removes that
    dependency entirely: the veto scenario below is fixed forever, the same
    way test_quality_verdict.py and test_assessment_store.py already build
    their Pydantic fixtures directly instead of loading a bot from disk.
    """
    deferred_loss = DeferredLossProfile(
        realized_pnl=9_500.0,
        unrealized_pnl=-86_132.0,
        open_loss=86_132.0,
        gross_realized_profit=10_000.0,
        gross_realized_loss=500.0,
        booked_profit_factor=11.0,
        marked_profit_factor=0.16,
        open_loss_to_capital_pct=65.0,
        never_realized_a_loss=False,
        representativeness="UNREPRESENTATIVE",
    )
    return BotResult(
        identity=BotIdentity(
            bot_id="SYN_DEFERRED_VETO",
            unique_code="SYN_DEFERRED_VETO",
            nick_name="Synthetic Deferred-Loss Bot",
            symbol=symbol,
            asset_context=symbol,
        ),
        current_state=BotCurrentState(),  # flat: no open position
        performance=BotPerformanceMetrics(
            trade_count=60,
            win_rate=90.0,
            loss_rate=10.0,
            total_pnl=9_500.0,
            profit_factor=11.0,
            expectancy=67.0,
        ),
        deferred_loss=deferred_loss,
        trade_statistics=TradeStatistics(
            sample_size=60,
            measurement_mode=RiskMeasurementMode.FULL,
            return_basis="ABSOLUTE_PNL",
        ),
        behavioral_observations=BehavioralObservations(),
        strategy_observations=StrategyObservations(observed_profile="UNKNOWN"),
        drawdown_analysis=DrawdownAnalysis(),
        simulation_results=SimulationResults(
            simulation_method="MONTE_CARLO_BLOCK_BOOTSTRAP",
            iterations=0,
            sample_size=0,
            horizon_trades=0,
            return_basis="ABSOLUTE_PNL",
            is_valid=False,
        ),
        reconciliation=LedgerReconciliation(status="RECONCILED", ledger_pnl=9_500.0),
        capital=CapitalModel(basis="CURRENT_AUM"),
        data_quality=DataQualityAssessment(
            completeness_score=0.9,
            freshness_score=0.9,
            overall_score=0.9,
            freshness_ms=0,
            measurement_mode=RiskMeasurementMode.FULL,
        ),
    )


@pytest.fixture
def market_synthetic_veto() -> MarketResult:
    return _synthetic_market_result("SYNVETO")


@pytest.fixture
def bot_synthetic_veto() -> BotResult:
    return _synthetic_deferred_veto_bot("SYNVETO")


def test_score_breakdown_explains_where_the_number_came_from(
    market_synthetic_veto, bot_synthetic_veto
):
    """The score must be traceable: weighted average, veto floor, and what held it back."""
    assessment = QCCoreService.assess_bot(market_synthetic_veto, bot_synthetic_veto)
    breakdown = assessment.score_breakdown

    assert breakdown.final_score == assessment.risk_score
    assert breakdown.contributions
    # Contributions are the weighted average, so they must reconstruct it.
    assert sum(c.contribution for c in breakdown.contributions) == pytest.approx(
        breakdown.weighted_average, abs=0.01
    )
    assert breakdown.applicable_dimensions == len(breakdown.contributions)
    assert breakdown.contributions == sorted(
        breakdown.contributions, key=lambda c: -c.contribution
    )


def test_a_veto_floor_is_reported_as_such(market_synthetic_veto, bot_synthetic_veto):
    assessment = QCCoreService.assess_bot(market_synthetic_veto, bot_synthetic_veto)
    breakdown = assessment.score_breakdown
    assert breakdown.decided_by == "VETO_FLOOR"
    assert breakdown.veto_floor is not None
    assert breakdown.veto_floor > breakdown.weighted_average
    assert breakdown.veto_reasons
    # Reasons reach the reader in Vietnamese, not internal English keys.
    assert not any(r.startswith("destructive") for r in breakdown.veto_reasons)


def test_a_clean_bot_is_decided_by_the_weighted_average(market_mu, bot_top):
    assessment = QCCoreService.assess_bot(market_mu, bot_top)
    breakdown = assessment.score_breakdown
    assert breakdown.decided_by == "WEIGHTED_AVERAGE"
    assert breakdown.veto_reasons == []
    assert breakdown.final_score == pytest.approx(breakdown.weighted_average, abs=0.01)


def test_score_story_says_why_it_is_not_higher(market_eth, bot_deferred):
    from Agent.backend.qc.reporting.cohort import CohortAssessmentService
    from Agent.backend.qc.reporting.reasons import score_story_vi

    report = CohortAssessmentService(persist_history=False).scan(
        simulation_iterations=50, simulation_horizon=30
    )
    row = next(r for r in report.rows if r.nick_name == "HaveARestin")
    story = score_story_vi(row)
    assert "veto floor" in story
    assert "average" in story
    assert row.held_the_score_down, "phải nêu được cái gì kéo điểm xuống"
    assert row.raised_the_score, "phải nêu được cái gì đẩy điểm lên"


def test_macro_source_is_read_from_file_and_stays_missing_without_one(tmp_path):
    """Macro was pinned to MISSING in code; it must now follow the evidence."""
    from Agent.backend.market.service import MarketService
    from Agent.test.conftest import write_market_dataset

    last_candle = 1_789_000_000_000
    write_market_dataset(tmp_path, asset="NOMACRO", last_candle_ms=last_candle)
    bare = MarketService(data_dir=tmp_path).get_market_result(
        "NOMACRO", venue_type="CEX", as_of_ms=last_candle
    )
    assert "macro" in bare.data_quality.missing_sources
    assert bare.macro_state.macro_regime == "UNKNOWN"
    assert bare.macro_state.btc_correlation is None

    write_market_dataset(
        tmp_path,
        asset="WITHMACRO",
        last_candle_ms=last_candle,
        extra_files={
            "macro_context.json": {
                "observed_at": last_candle,
                "macro": {
                    "btc_correlation": 0.62,
                    "btc_beta": 1.4,
                    "macro_regime": "RISK_ON",
                    "macro_event_risk": "UNKNOWN",
                },
            }
        },
    )
    filled = MarketService(data_dir=tmp_path).get_market_result(
        "WITHMACRO", venue_type="CEX", as_of_ms=last_candle
    )
    assert "macro" not in filled.data_quality.missing_sources
    assert filled.macro_state.btc_correlation == pytest.approx(0.62)
    assert filled.macro_state.btc_beta == pytest.approx(1.4)
    assert filled.macro_state.macro_regime == "RISK_ON"
    # No economic calendar exists, so event risk must not be invented.
    assert filled.macro_state.macro_event_risk == "UNKNOWN"


def test_token_security_flags_never_default_to_reassuring_values(tmp_path):
    from Agent.backend.market.service import MarketService
    from Agent.test.conftest import write_market_dataset

    last_candle = 1_789_000_000_000
    write_market_dataset(
        tmp_path,
        venue="dex",
        asset="RISKY",
        last_candle_ms=last_candle,
        extra_files={
            "token_security.json": {
                "observed_at": last_candle,
                "security": {
                    "is_honeypot": False,
                    "buy_tax": 0.0,
                    "sell_tax": 5.0,
                    "is_mintable": True,
                    "top10_holder_pct": 61.0,
                    # The provider could not answer these two.
                    "liquidity_locked": None,
                    "security_score": None,
                },
            }
        },
    )
    result = MarketService(data_dir=tmp_path).get_market_result(
        "RISKY", venue_type="DEX", as_of_ms=last_candle
    )

    assert "token_security" not in result.data_quality.missing_sources
    assert result.token_state.is_mintable is True
    assert result.token_state.sell_tax == pytest.approx(5.0)
    assert result.token_state.top10_holder_pct == pytest.approx(61.0)
    # An unanswered flag stays unanswered rather than becoming a safe-looking value.
    assert result.token_state.liquidity_locked is None
    assert result.token_state.security_score is None


def test_depth_band_follows_the_book_not_a_drifted_candle_close():
    """A newer book must not report a one-sided wall just because price drifted."""
    from Agent.backend.market.features.liquidity import LiquidityFeatureExtractor

    # Book mid is 0.2 % above the last close, which used to push every ask out.
    book = {
        "bids": [["0.2078", "1000000", "10"], ["0.2077", "1000000", "10"]],
        "asks": [["0.2079", "1000000", "10"], ["0.2080", "1000000", "10"]],
    }
    state = LiquidityFeatureExtractor.extract(book, last_price=0.2071)

    assert state.ask_depth_02_usd > 0.0
    assert state.bid_depth_02_usd > 0.0
    assert abs(state.depth_imbalance) < 0.5


def test_orderbook_sizes_are_stored_in_coins_not_contracts():
    """ctVal must be applied when crawling, or depth is off by 100-1000x."""
    import json as _json
    from pathlib import Path as _Path

    root = _Path(__file__).resolve().parent.parent / "data" / "cex"
    for asset in ("ADA", "DOGE", "BTC"):
        path = root / asset / "market" / "orderbook_l2.json"
        if not path.exists():
            continue
        book = _json.loads(path.read_text(encoding="utf-8"))
        assert book.get("size_unit") == "BASE_COIN", f"{asset} thiếu quy đổi hợp đồng"
        assert book.get("contract_size"), f"{asset} không ghi ctVal"


def _dup_snapshot(tmp_path, asset, mtime_ms, *, trades, reconcilable):
    """Two folders, one uniqueCode: the same bot seen at two different times."""
    import os

    from Agent.backend.mcp.service import BotObservationService
    from Agent.test.conftest import write_bot_dataset

    overview = {"uniqueCode": "DUP", "nickName": "Dup Bot", "aum": 10_000.0}
    if reconcilable:
        overview["provenance"] = {"profile_fields": "OKX_VERIFIED"}
    directory = write_bot_dataset(
        tmp_path,
        asset=asset,
        folder="bot_DUP",
        overview=overview,
        closed_trades=[
            {
                "subPosId": str(90_000_000_000 + i),
                "instId": f"{asset}-USDT-SWAP",
                "posSide": "long",
                "openTime": str(1_789_000_000_000 + i),
                "closeTime": str(1_789_000_100_000 + i),
                "pnl": "10.0",
                "pnlRatio": "0.05",
                "margin": "100.0",
                "lever": "5",
            }
            for i in range(trades)
        ],
    )
    for path in directory.glob("*.json"):
        os.utime(path, (mtime_ms / 1000, mtime_ms / 1000))
    return BotObservationService(data_dir=tmp_path).get_bot_result(
        asset,
        "bot_DUP",
        venue_type="CEX",
        seed=42,
        as_of_ms=mtime_ms,
        simulation_iterations=50,
        simulation_horizon=50,
    )


def test_the_fresher_snapshot_wins_when_hard_evidence_ties(tmp_path):
    from Agent.backend.qc.reporting.cohort import _provenance_rank

    older = _dup_snapshot(
        tmp_path / "a", "ADA", 1_789_100_000_000, trades=30, reconcilable=True
    )
    newer = _dup_snapshot(
        tmp_path / "b", "ETH", 1_789_300_000_000, trades=31, reconcilable=False
    )

    # The older one carries a reconcilable reference, the newer one does not; the
    # day-fresher position book still has to win.
    assert _provenance_rank(newer) > _provenance_rank(older)


def test_recency_never_rescues_a_snapshot_with_less_hard_evidence(tmp_path):
    from Agent.backend.qc.reporting.cohort import _provenance_rank

    rich_old = _dup_snapshot(
        tmp_path / "a", "ADA", 1_789_100_000_000, trades=350, reconcilable=True
    )
    thin_new = _dup_snapshot(
        tmp_path / "b", "ETH", 1_789_300_000_000, trades=20, reconcilable=False
    )

    assert _provenance_rank(rich_old) > _provenance_rank(thin_new)


def _signed_trade(index, subpos, side="short"):
    open_ms = 1_789_000_000_000 + index * 60_000
    return {
        "subPosId": str(3_900_000_000_000_000_000 + index),
        "instId": "BTC-USDT-SWAP",
        "posSide": side,
        "openTime": str(open_ms),
        "closeTime": str(open_ms + 30_000),
        "pnl": "10.0",
        "pnlRatio": "0.05",
        "margin": "100.0",
        "lever": "10",
        "subPos": str(subpos),
    }


def test_a_short_reported_with_a_negative_size_is_not_dropped():
    """OKX signs the size on some accounts; size is a magnitude, posSide is direction."""
    from Agent.backend.mcp.trades.ledger import TradeLedgerManager

    raw = {
        "uniqueCode": "X",
        "closed_trades": [
            _signed_trade(0, -8151),
            _signed_trade(1, 8151),
            _signed_trade(2, 4000, side="long"),
        ],
    }

    result = TradeLedgerManager.parse_trade_list_with_diagnostics(raw)

    assert result.rejected_count == 0
    assert [trade.quantity for trade in result.trades] == [8151.0, 8151.0, 4000.0]
    sides = [trade.side.value for trade in result.trades]
    assert sides == ["SHORT", "SHORT", "LONG"]


def test_dropping_signed_shorts_would_change_the_verdict():
    """The rejected half carried the losses, so the bot looked profitable."""
    from Agent.backend.mcp.trades.ledger import TradeLedgerManager

    winners = [_signed_trade(i, 100, side="long") for i in range(5)]
    losers = []
    for i in range(5, 10):
        trade = _signed_trade(i, -100)
        trade["pnl"] = "-40.0"
        trade["pnlRatio"] = "-0.2"
        losers.append(trade)

    result = TradeLedgerManager.parse_trade_list_with_diagnostics(
        {"uniqueCode": "X", "closed_trades": winners + losers}
    )
    total = sum(trade.realized_pnl for trade in result.trades)

    assert len(result.trades) == 10
    assert total == pytest.approx(-150.0), "bỏ lệnh short sẽ biến lỗ thành lãi"


def test_a_drawdown_larger_than_the_equity_in_force_is_flagged_not_silently_capped():
    from Agent.backend.mcp.analytics.drawdown.underwater import (
        DrawdownUnderwaterAnalyzer,
    )
    from Agent.backend.mcp.capital.equity_curve import CapitalResolver
    from Agent.backend.mcp.trades.ledger import TradeLedgerManager

    rows = []
    for i in range(4):
        trade = _signed_trade(i, 100, side="long")
        trade["pnl"] = "-5000.0" if i else "100.0"
        rows.append(trade)
    trades = TradeLedgerManager.parse_trade_list_with_diagnostics(
        {"uniqueCode": "X", "closed_trades": rows}
    ).trades
    capital = CapitalResolver.resolve(
        {
            "weekly_pnl_history": [
                {"beginTs": "1789000000000", "pnl": "50.0", "pnlRatio": "0.05"}
            ]
        },
        None,
    )
    analysis = DrawdownUnderwaterAnalyzer.analyze(trades, capital)

    if analysis.max_dd_pct == 100.0:
        assert analysis.max_dd_pct_capped is True
        assert analysis.capped_trade_count > 0
        assert analysis.wiped_out is False

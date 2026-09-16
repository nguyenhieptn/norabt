"""`decide()` names the horizon when the read depends on it -- without ever
softening the verdict itself.

Context: `SimulationResults.horizon_stability_label` and
`horizon_exceeds_observed` existed before this change but nothing in the QC
verdict layer read them, so a bot judged "safe" at one arbitrary horizon (or
at a horizon longer than any data ever observed) read no differently from one
that is actually stable everywhere. `decide()` now appends plain-language
context about this to `reason`, strictly additive: it must never move a bot
between buckets, and a veto-driven NGUY HIỂM stays NGUY HIỂM.
"""

from __future__ import annotations

from types import SimpleNamespace

from Agent.backend.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.mcp.schemas.bot_result import (
    BehavioralObservations,
    BotCurrentState,
    BotIdentity,
    BotPerformanceMetrics,
    BotResult,
    CapitalModel,
    DataQualityAssessment,
    DeferredLossProfile,
    DrawdownAnalysis,
    HorizonOutcome,
    LedgerReconciliation,
    RiskMeasurementMode,
    SimulationResults,
    StrategyObservations,
    TradeStatistics,
)
from Agent.backend.qc.scoring.verdict import (
    VERDICT_DANGEROUS,
    VERDICT_PROMISING,
    decide,
)


def _bot(simulation_results: SimulationResults) -> BotResult:
    return BotResult(
        identity=BotIdentity(
            bot_id="SYN_HORIZON",
            unique_code="SYN_HORIZON",
            nick_name="Synthetic Horizon Bot",
            symbol="BTC-USDT-SWAP",
            asset_context="BTC-USDT-SWAP",
        ),
        current_state=BotCurrentState(),
        performance=BotPerformanceMetrics(
            trade_count=200,
            win_rate=60.0,
            loss_rate=40.0,
            total_pnl=5_000.0,
        ),
        deferred_loss=DeferredLossProfile(realized_pnl=5_000.0),
        trade_statistics=TradeStatistics(
            sample_size=200,
            measurement_mode=RiskMeasurementMode.FULL,
            return_basis="ABSOLUTE_PNL",
        ),
        behavioral_observations=BehavioralObservations(),
        strategy_observations=StrategyObservations(
            observed_profile="UNKNOWN", tested_in_downtrend=True
        ),
        drawdown_analysis=DrawdownAnalysis(),
        simulation_results=simulation_results,
        reconciliation=LedgerReconciliation(status="RECONCILED", ledger_pnl=5_000.0),
        capital=CapitalModel(basis="CURRENT_AUM"),
        data_quality=DataQualityAssessment(
            completeness_score=0.9,
            freshness_score=0.9,
            overall_score=0.9,
            freshness_ms=0,
            measurement_mode=RiskMeasurementMode.FULL,
        ),
    )


def _sim(**overrides) -> SimulationResults:
    fields = dict(
        simulation_method="STATIONARY_BOOTSTRAP",
        iterations=8_000,
        sample_size=200,
        horizon_trades=200,
        return_basis="ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
        is_valid=True,
        p_mdd_gt_15=1.0,
    )
    fields.update(overrides)
    return SimulationResults(**fields)


def _scenario(label: str, horizon_trades: int, probability_of_profit: float):
    return HorizonOutcome(
        label=label,
        horizon_trades=horizon_trades,
        iterations=3_000,
        is_valid=True,
        probability_of_profit=probability_of_profit,
        p_loss_after_horizon=100.0 - probability_of_profit,
    )


def test_a_stable_horizon_label_adds_no_horizon_commentary():
    sim = _sim(horizon_stability_label=MonteCarloSimulationEngine.STABLE_LABEL)
    verdict = decide(_bot(sim), risk_score=20.0, quality_score=80.0)

    assert "horizon" not in verdict.reason.lower()


def test_no_stability_label_at_all_adds_no_horizon_commentary():
    sim = _sim(horizon_stability_label=None)
    verdict = decide(_bot(sim), risk_score=20.0, quality_score=80.0)

    assert "horizon" not in verdict.reason.lower()


def test_an_unstable_horizon_label_is_named_with_each_horizons_numbers():
    sim = _sim(
        horizon_stability_label=MonteCarloSimulationEngine.SHORT_ONLY_LABEL,
        horizon_scenarios=[
            _scenario("SHORT", 30, 80.0),
            _scenario("MEDIUM", 200, 50.0),
            _scenario("LONG", 600, 10.0),
        ],
    )
    verdict = decide(_bot(sim), risk_score=20.0, quality_score=80.0)

    assert MonteCarloSimulationEngine.SHORT_ONLY_LABEL in verdict.reason
    assert "SHORT 30" in verdict.reason
    assert "MEDIUM 200" in verdict.reason
    assert "LONG 600" in verdict.reason


def test_horizon_exceeding_observed_data_is_named_as_extrapolation():
    sim = _sim(
        horizon_exceeds_observed=True,
        horizon_calendar_days=90.0,
        observed_span_days=30.0,
    )
    verdict = decide(_bot(sim), risk_score=20.0, quality_score=80.0)

    assert "ngoại suy" in verdict.reason


def test_horizon_within_observed_data_adds_no_extrapolation_warning():
    sim = _sim(
        horizon_exceeds_observed=False,
        horizon_calendar_days=10.0,
        observed_span_days=30.0,
    )
    verdict = decide(_bot(sim), risk_score=20.0, quality_score=80.0)

    assert "ngoại suy" not in verdict.reason
    assert verdict.verdict == VERDICT_PROMISING


def test_a_veto_driven_dangerous_verdict_stays_dangerous_with_horizon_notes():
    """The absolute safety constraint: horizon commentary is context, never a
    downgrade. A bot vetoed at NGUY HIỂM must still be NGUY HIỂM after this
    text is appended, whatever the horizon situation looks like.
    """
    sim = _sim(
        horizon_stability_label=MonteCarloSimulationEngine.SHORT_ONLY_LABEL,
        horizon_scenarios=[
            _scenario("SHORT", 30, 80.0),
            _scenario("MEDIUM", 200, 50.0),
            _scenario("LONG", 600, 10.0),
        ],
        horizon_exceeds_observed=True,
        horizon_calendar_days=400.0,
        observed_span_days=60.0,
    )
    verdict = decide(
        _bot(sim),
        risk_score=90.0,
        quality_score=40.0,
        risk_drivers=["rủi ro đuôi mô phỏng cực đoan"],
    )

    assert verdict.verdict == VERDICT_DANGEROUS
    assert "rủi ro đuôi mô phỏng cực đoan" in verdict.reason
    assert MonteCarloSimulationEngine.SHORT_ONLY_LABEL in verdict.reason
    assert "ngoại suy" in verdict.reason


def test_bots_without_simulation_results_are_unaffected():
    """Backward compatibility: callers/tests that pass a lightweight stand-in
    without `simulation_results` (as test_quality_verdict.py's SimpleNamespace
    fixtures do) must keep working exactly as before -- no AttributeError, no
    horizon text.
    """
    bare = SimpleNamespace(
        performance=SimpleNamespace(trade_count=100),
        deferred_loss=SimpleNamespace(
            booked_profit_factor=2.0,
            marked_profit_factor=2.0,
            never_realized_a_loss=False,
            open_loss_to_capital_pct=1.0,
        ),
        drawdown_analysis=SimpleNamespace(max_dd_pct=8.0, max_dd_pct_capped=False),
        strategy_observations=SimpleNamespace(
            phase_coverage_pct=90.0,
            regime_dependence_pct=30.0,
            losing_phases=[],
            tested_in_downtrend=True,
        ),
    )
    verdict = decide(bare, risk_score=25.0, quality_score=80.0)

    assert "horizon" not in verdict.reason.lower()

"""Out-of-sample holdout validation and the scenario laboratory."""

from __future__ import annotations

import numpy as np
import pytest

from Agent.backend.pipeline import RiskSupervisionPipeline
from Agent.backend.report.qc.reporting.scenarios import (
    MIN_SCENARIO_TRADES,
    build_scenario_laboratory,
)
from Agent.backend.report.qc.reporting.validation import (
    MIN_LEDGER_FOR_SPLIT,
    build_folds,
    build_out_of_sample_validation,
)
from Agent.none.test.conftest import FIXED_AS_OF_MS


@pytest.fixture(scope="module")
def bot_and_market():
    result = RiskSupervisionPipeline(persist_history=False).run(
        "MU",
        "bot_BB3398A957270A39",
        as_of_ms=FIXED_AS_OF_MS,
        simulation_iterations=20,
        simulation_horizon=10,
    )
    return result.bot_result, result.market_result


# --------------------------------------------------------------------------- #
# Holdout validation
# --------------------------------------------------------------------------- #


def test_folds_never_look_into_the_future(bot_and_market):
    bot, _ = bot_and_market
    folds = build_folds(bot.trade_ledger_summary)
    assert folds, "expected folds for a ledger of this size"
    for fold in folds:
        assert fold.in_sample.end_ms is not None
        assert fold.out_of_sample.start_ms is not None
        # Every out-of-sample trade must close at or after the last in-sample one.
        assert fold.out_of_sample.start_ms >= fold.in_sample.end_ms


def test_folds_are_chronological_and_non_overlapping(bot_and_market):
    bot, _ = bot_and_market
    folds = build_folds(bot.trade_ledger_summary)
    for earlier, later in zip(folds, folds[1:]):
        # The expanding in-sample window grows; the test windows march forward.
        assert later.in_sample.trades > earlier.in_sample.trades
        assert later.out_of_sample.start_ms >= earlier.out_of_sample.end_ms


def test_validation_abstains_on_a_short_ledger(bot_and_market):
    bot, _ = bot_and_market
    short = bot.model_copy(
        update={"trade_ledger_summary": bot.trade_ledger_summary[: MIN_LEDGER_FOR_SPLIT - 1]}
    )
    validation = build_out_of_sample_validation(short)
    assert validation.status == "INSUFFICIENT_SAMPLE"
    assert validation.stability_grade == "UNKNOWN"
    assert validation.limitations
    # Abstaining must not invent a gate verdict.
    assert validation.gate_passed is None


def test_validation_reports_degradation_rather_than_a_headline(bot_and_market):
    bot, _ = bot_and_market
    validation = build_out_of_sample_validation(bot)
    assert validation.status == "EVALUATED"
    assert validation.folds
    for fold in validation.folds:
        assert fold.reliability in (
            "STABLE",
            "DEGRADED",
            "SEVERELY_DEGRADED",
            "UNRELIABLE",
        )
    assert validation.assumptions, "the method's assumptions must travel with it"


def test_profit_factor_is_undefined_without_a_realized_loss(bot_and_market):
    """A window with no losing trade must not report an enormous edge."""
    bot, _ = bot_and_market
    winners = [t for t in bot.trade_ledger_summary if t.realized_pnl > 0][:10]
    assert winners
    from Agent.backend.report.qc.reporting.validation import _window_metrics

    metrics = _window_metrics(winners)
    assert metrics.profit_factor is None
    assert metrics.win_rate == 100.0


# --------------------------------------------------------------------------- #
# Scenario laboratory
# --------------------------------------------------------------------------- #


def test_every_scenario_states_assumptions_and_is_never_observed(bot_and_market):
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    assert lab.scenarios
    for scenario in lab.scenarios:
        assert scenario.status in ("SIMULATED", "UNTESTED", "INSUFFICIENT")
        assert scenario.assumptions, f"{scenario.scenario_id} states no assumptions"
        assert scenario.evidence_ids


def test_a_simulated_scenario_always_carries_an_interval(bot_and_market):
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    simulated = [s for s in lab.scenarios if s.status == "SIMULATED"]
    assert simulated
    for scenario in simulated:
        assert scenario.total_pnl is not None
        assert scenario.total_pnl.p05 is not None
        assert scenario.total_pnl.p95 is not None
        assert scenario.total_pnl.p05 <= scenario.total_pnl.p50 <= scenario.total_pnl.p95
        assert scenario.probability_of_loss_pct is not None


def test_a_thin_regime_is_reported_not_silently_borrowed(bot_and_market):
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    thin = [s for s in lab.scenarios if s.status == "INSUFFICIENT"]
    for scenario in thin:
        assert scenario.sample_size < MIN_SCENARIO_TRADES
        # No numbers may leak from a regime that was never adequately observed.
        assert scenario.total_pnl is None
        assert scenario.central_estimate is None
        assert scenario.limitations


def test_untested_regimes_carry_no_scenario(bot_and_market):
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    scenario_regimes = {
        s.conditioning.get("regime") for s in lab.scenarios if s.family == "REGIME"
    }
    for regime in lab.untested_conditions:
        assert regime not in scenario_regimes


def test_scenarios_are_reproducible_from_the_seed(bot_and_market):
    bot, market = bot_and_market
    first = build_scenario_laboratory(bot, market, iterations=200, seed=7)
    second = build_scenario_laboratory(bot, market, iterations=200, seed=7)
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    other = build_scenario_laboratory(bot, market, iterations=200, seed=8)
    assert other.model_dump(mode="json") != first.model_dump(mode="json")


def test_execution_stress_never_improves_the_book(bot_and_market):
    """Charging a cost must reduce PnL; a stress that helps is a sign error."""
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=400, seed=11)
    baseline = next(s for s in lab.scenarios if s.scenario_id == "scenario.baseline")
    for scenario in lab.scenarios:
        if scenario.family != "EXECUTION" or scenario.status != "SIMULATED":
            continue
        assert scenario.total_pnl.p50 < baseline.total_pnl.p50


def test_laboratory_handles_an_empty_ledger(bot_and_market):
    bot, market = bot_and_market
    empty = bot.model_copy(update={"trade_ledger_summary": []})
    lab = build_scenario_laboratory(empty, market, iterations=50)
    assert lab.scenarios == []
    assert lab.limitations


# --------------------------------------------------------------------------- #
# Regime scenarios resample real trades, never a reconstructed series
# --------------------------------------------------------------------------- #


def test_every_trade_carries_the_phase_it_was_opened_in(bot_and_market):
    bot, _ = bot_and_market
    ledger = bot.trade_ledger_summary
    assert ledger
    labelled = [t for t in ledger if t.market_phase]
    assert labelled, "expected the ledger to carry per-trade market phases"
    # "not measurable" (None) and "measured, outside candle range" (UNKNOWN)
    # are different states and must not be collapsed.
    for trade in ledger:
        assert trade.market_phase is None or isinstance(trade.market_phase, str)


def test_per_trade_labels_agree_with_the_aggregated_breakdown(bot_and_market):
    """The stamped labels and the phase table come from the same pass, so any
    disagreement means one of them is being derived a second, different way."""
    bot, _ = bot_and_market
    from collections import Counter

    stamped = Counter(
        t.market_phase
        for t in bot.trade_ledger_summary
        if t.market_phase and t.market_phase != "UNKNOWN"
    )
    aggregated = {p.phase: p.trades for p in bot.strategy_observations.phase_breakdown}
    assert dict(stamped) == aggregated


def test_regime_scenarios_resample_only_that_regimes_trades(bot_and_market):
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    regime_scenarios = [s for s in lab.scenarios if s.family == "REGIME"]
    assert regime_scenarios
    for scenario in regime_scenarios:
        regime = scenario.conditioning["regime"]
        matched = scenario.conditioning["matched_trades"]
        # Every trade behind the scenario really carries this regime's label.
        actual = [
            t for t in bot.trade_ledger_summary if t.market_phase == regime
        ]
        assert matched == len(actual)
        assert scenario.sample_size == matched


def test_no_scenario_claims_a_reconstructed_series(bot_and_market):
    """The previous implementation synthesised a regime's PnL from its measured
    expectancy. Nothing may do that again without saying so."""
    bot, market = bot_and_market
    lab = build_scenario_laboratory(bot, market, iterations=200)
    for scenario in lab.scenarios:
        for assumption in scenario.assumptions:
            assert "reconstruct" not in assumption.lower()

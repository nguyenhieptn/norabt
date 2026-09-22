"""Multi-horizon Monte Carlo support.

Context: a hard verdict threshold that ignores horizon flagged 15 of 30 bots
as dangerous. The complaint behind that number was concrete: some strategies
are built to be held for a handful of trades and burn out over hundreds, so
judging every bot on one horizon (usually its own full trade count) measures
the wrong thing for a scalper. These tests cover the fix at the data layer:
`MonteCarloSimulationEngine.run_simulation` now also runs SHORT and LONG
horizons alongside the existing one (renamed MEDIUM in the comparison) and
reports how sensitive the outcome is to that choice. It does not change any
verdict logic -- that is explicitly out of scope here.
"""

from __future__ import annotations

import numpy as np

from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.schemas.bot_result import PositionSide, TradeLedgerItem


def trade(index: int, pnl: float) -> TradeLedgerItem:
    return TradeLedgerItem(
        trade_id=f"t{index}",
        symbol="BTC-USDT-SWAP",
        side=PositionSide.LONG,
        open_time=index * 3_600_000,
        close_time=(index + 1) * 3_600_000,
        realized_pnl=pnl,
        holding_time_minutes=60.0,
    )


def scalper_style_trades(n: int = 150) -> list[TradeLedgerItem]:
    """Many small wins, a catastrophic loss roughly every 40 fills.

    This is the "picking up nickels in front of a steamroller" shape the
    complaint describes: a short peek rarely lands on the rare blow-up, so it
    reads as safe; a long enough sample almost certainly draws one, so the
    same bot reads as ruinous. Neither read is wrong -- they are true at
    different horizons, which is exactly the case a single fixed horizon
    cannot represent.
    """
    return [trade(i, -500.0 if i % 40 == 39 else 8.0) for i in range(n)]


def consistently_losing_trades(n: int = 100) -> list[TradeLedgerItem]:
    """A steady negative-expectancy strategy: no rare tail, just a losing edge.

    Unlike the scalper shape above, there is nothing here that a longer or
    shorter sample would reveal differently -- the edge is negative on every
    trade, so every horizon should agree.
    """
    return [trade(i, -15.0 if i % 2 == 0 else 8.0) for i in range(n)]


def test_three_horizons_produce_different_results_on_a_trending_ledger():
    trades = scalper_style_trades()
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=4_000, seed=42, block_bootstrap=True
    )
    assert result.is_valid
    labels = [h.label for h in result.horizon_scenarios]
    assert labels == ["SHORT", "MEDIUM", "LONG"]

    by_label = {h.label: h for h in result.horizon_scenarios}
    # SHORT is a fraction of the bot's own trade count, LONG a multiple of it,
    # both distinct from MEDIUM (the bot's own trade count, capped).
    assert by_label["SHORT"].horizon_trades < by_label["MEDIUM"].horizon_trades
    assert by_label["MEDIUM"].horizon_trades < by_label["LONG"].horizon_trades
    assert by_label["LONG"].horizon_trades <= MonteCarloSimulationEngine.MAX_HORIZON

    # The rare-catastrophic-loss shape means SHORT rarely draws the blow-up
    # and LONG almost always does -- the three horizons must actually differ,
    # not just carry different labels.
    profits = [h.probability_of_profit for h in by_label.values()]
    assert len(set(profits)) == 3
    assert (
        by_label["SHORT"].probability_of_profit > by_label["LONG"].probability_of_profit
    )


def test_short_term_winner_long_term_blowup_is_labeled_short_only():
    trades = scalper_style_trades()
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=4_000, seed=42, block_bootstrap=True
    )
    by_label = {h.label: h for h in result.horizon_scenarios}
    # This dataset must actually demonstrate the claim: profitable-odds short,
    # losing-odds long. If a future change to the synthetic data breaks that,
    # the assertion on the label below would otherwise pass for the wrong
    # reason.
    assert by_label["SHORT"].probability_of_profit >= 50.0
    assert by_label["LONG"].probability_of_profit < 50.0

    assert result.horizon_stability_label == MonteCarloSimulationEngine.SHORT_ONLY_LABEL
    assert result.horizon_sensitivity is not None
    assert result.horizon_sensitivity > 0.0


def test_bad_at_every_horizon_is_labeled_stable():
    trades = consistently_losing_trades()
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=4_000, seed=7, block_bootstrap=True
    )
    by_label = {h.label: h for h in result.horizon_scenarios}
    # Every horizon must actually show a losing bot for this to test the
    # "stable but bad" case rather than something else.
    assert all(h.probability_of_profit < 50.0 for h in by_label.values())

    # STABLE here means the losing verdict is not an artifact of the horizon
    # picked -- it is the same important distinction as a stable win, just
    # with the opposite sign. See MonteCarloSimulationEngine._classify_horizon_stability.
    assert result.horizon_stability_label == MonteCarloSimulationEngine.STABLE_LABEL


def test_needs_time_label_when_short_horizon_is_noisy_but_long_horizon_wins():
    # A "long-shot" shape: frequent small losses, a rare large win (a trend
    # follower that eats small stop-outs waiting for the one move that pays
    # for all of them). A short peek rarely catches the rare win, so it reads
    # as a coin flip or worse; give the law of large numbers enough trades
    # and the rare win's size pulls the odds of profit above even.
    n = 140
    trades = [trade(i, 400.0 if i % 40 == 39 else -8.0) for i in range(n)]
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=4_000, seed=42, block_bootstrap=True
    )
    by_label = {h.label: h for h in result.horizon_scenarios}
    assert by_label["SHORT"].probability_of_profit < 50.0
    assert by_label["LONG"].probability_of_profit >= 50.0
    assert result.horizon_stability_label == MonteCarloSimulationEngine.NEEDS_TIME_LABEL


def test_too_few_trades_is_still_invalid_and_reports_no_scenarios():
    trades = [trade(i, 1.0) for i in range(5)]
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=200, seed=1
    )
    assert not result.is_valid
    assert result.horizon_scenarios == []
    assert result.horizon_sensitivity is None
    assert result.horizon_stability_label is None


def test_min_sample_size_boundary_produces_a_usable_short_horizon():
    # Exactly MIN_SAMPLE_SIZE trades: SHORT must not divide down to zero and
    # the run must not raise (guards against a 0-length horizon or a 0/0 in
    # the derived percentages).
    n = MonteCarloSimulationEngine.MIN_SAMPLE_SIZE
    trades = [trade(i, 10.0 if i % 2 else -5.0) for i in range(n)]
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=300, seed=3, block_bootstrap=True
    )
    assert result.is_valid
    assert len(result.horizon_scenarios) == 3
    for scenario in result.horizon_scenarios:
        assert scenario.horizon_trades >= 1
        assert scenario.is_valid


def test_long_horizon_still_respects_max_horizon_cap():
    n = 400
    trades = [trade(i, 5.0 if i % 3 else -4.0) for i in range(n)]
    result = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=500, seed=11, block_bootstrap=True
    )
    by_label = {h.label: h for h in result.horizon_scenarios}
    assert by_label["LONG"].horizon_trades <= MonteCarloSimulationEngine.MAX_HORIZON
    assert by_label["MEDIUM"].horizon_trades <= MonteCarloSimulationEngine.MAX_HORIZON


# --- Regression: nothing about the pre-existing single-horizon fields changed ---

_LEGACY_FIELDS_UNCHANGED_DEFAULT_HORIZON = {
    "capital_at_risk": 1000.0,
    "capital_basis": "CURRENT_AUM",
    "cvar_95_pct": 7.045454545454546,
    "cvar_99_pct": 9.45,
    "deferred_loss_bias": False,
    "deflated_sharpe": None,
    "expected_terminal_equity": 997.36,
    "horizon_basis": "OWN_TRADE_COUNT",
    "horizon_trades": 30,
    "inference_notes": [],
    "inference_reliable": True,
    "is_valid": True,
    "iterations": 500,
    "mar_ratio_median": 0.0,
    "mar_ratio_p05": -0.8575714285714284,
    "median_max_drawdown": 4.854368932038835,
    "median_terminal_equity": 1000.0,
    "min_track_record_trades": None,
    "p10_outcome": 940.0,
    "p50_outcome": 1000.0,
    "p90_max_drawdown": 8.0,
    "p90_outcome": 1060.0,
    "p95_max_drawdown": 9.803921568627452,
    "p99_max_drawdown": 11.882376237623761,
    "p_10_loss_streak": 0.0,
    "p_5_loss_streak": 0.0,
    "p_capital_loss_gt_current_dd": 38.0,
    "p_loss_after_500_trades": None,
    "p_loss_after_horizon": 39.800000000000004,
    "p_mdd_gt_10": 2.8000000000000003,
    "p_mdd_gt_15": 0.0,
    "p_mdd_gt_25": 0.0,
    "p_recovery_gt_30d": 0.0,
    "p_ruin": 0.0,
    "probabilistic_sharpe": None,
    "probability_of_profit": 60.199999999999996,
    "profit_factor_median": 1.0,
    "profit_factor_p05": 0.75,
    "profit_pct_best": 12.0,
    "profit_pct_p05": -6.0,
    "profit_pct_p10": -6.0,
    "profit_pct_p25": -3.0,
    "profit_pct_p50": 0.0,
    "profit_pct_p75": 3.0,
    "profit_pct_p90": 6.0,
    "profit_pct_p95": 6.0,
    "profit_pct_worst": -12.0,
    "return_basis": "ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
    "sample_size": 30,
    "selection_trials": None,
    "sharpe_per_trade": None,
    "simulation_method": "STATIONARY_BOOTSTRAP",
    "var_95_pct": 6.0,
    "var_99_pct": 9.0,
    "warnings": [],
    "worst_percentile_drawdown": 13.0,
    "worst_terminal_equity": 880.0,
}

_LEGACY_FIELDS_UNCHANGED_CALLER_SET_HORIZON = {
    "capital_at_risk": 1000.0,
    "capital_basis": "CURRENT_AUM",
    "cvar_95_pct": 11.565217391304348,
    "cvar_99_pct": 14.0,
    "deferred_loss_bias": False,
    "deflated_sharpe": None,
    "expected_terminal_equity": 1002.6,
    "horizon_basis": "CALLER_SET",
    "horizon_trades": 80,
    "inference_notes": [],
    "inference_reliable": True,
    "is_valid": True,
    "iterations": 200,
    "mar_ratio_median": -0.1015,
    "mar_ratio_p05": -0.8150288461538461,
    "median_max_drawdown": 7.2727272727272725,
    "median_terminal_equity": 990.0,
    "min_track_record_trades": None,
    "p10_outcome": 900.0,
    "p50_outcome": 990.0,
    "p90_max_drawdown": 12.745098039215685,
    "p90_outcome": 1110.0,
    "p95_max_drawdown": 14.299583911234391,
    "p99_max_drawdown": 16.026915887850443,
    "p_10_loss_streak": 0.0,
    "p_5_loss_streak": 0.0,
    "p_capital_loss_gt_current_dd": None,
    "p_loss_after_500_trades": None,
    "p_loss_after_horizon": 54.0,
    "p_mdd_gt_10": 24.5,
    "p_mdd_gt_15": 2.0,
    "p_mdd_gt_25": 0.5,
    "p_recovery_gt_30d": None,
    "p_ruin": 0.0,
    "probabilistic_sharpe": None,
    "probability_of_profit": 46.0,
    "profit_factor_median": 0.9814814814814815,
    "profit_factor_p05": 0.8333333333333334,
    "profit_pct_best": 20.0,
    "profit_pct_p05": -10.0,
    "profit_pct_p10": -10.0,
    "profit_pct_p25": -4.0,
    "profit_pct_p50": -1.0,
    "profit_pct_p75": 5.0,
    "profit_pct_p90": 11.0,
    "profit_pct_p95": 11.0,
    "profit_pct_worst": -22.0,
    "return_basis": "ABSOLUTE_PNL_RELATIVE_TO_EQUITY",
    "sample_size": 30,
    "selection_trials": None,
    "sharpe_per_trade": None,
    "simulation_method": "STATIONARY_BOOTSTRAP",
    "var_95_pct": 10.0,
    "var_99_pct": 13.0,
    "warnings": [],
    "worst_percentile_drawdown": 25.49019607843137,
    "worst_terminal_equity": 780.0,
}


def _thirty_trade_ledger() -> list[TradeLedgerItem]:
    return [trade(i, 10.0 if i % 3 else -20.0) for i in range(30)]


def test_legacy_fields_are_byte_identical_to_pre_multi_horizon_snapshot_default():
    """Golden-value regression test, captured from this engine before
    multi-horizon support was added (same trades, same seed, same call).

    This is the most important test in this file: multi-horizon support must
    be purely additive. If any of these numbers move, the MEDIUM-horizon
    computation stopped being bit-identical to the original single-horizon
    computation, which every other passing test in this repo implicitly
    depends on.
    """
    result = MonteCarloSimulationEngine.run_simulation(
        _thirty_trade_ledger(),
        1000.0,
        iterations=500,
        seed=123,
        block_bootstrap=True,
        current_drawdown_pct=5.0,
        trade_frequency_per_day=2.0,
    )
    dumped = result.model_dump()
    for field, expected in _LEGACY_FIELDS_UNCHANGED_DEFAULT_HORIZON.items():
        assert dumped[field] == expected, f"{field} drifted from pre-change snapshot"


def test_legacy_fields_are_byte_identical_to_pre_multi_horizon_snapshot_caller_set():
    """Same regression, but for an explicit caller-supplied horizon
    (horizon_basis=CALLER_SET) rather than the default OWN_TRADE_COUNT path.
    """
    result = MonteCarloSimulationEngine.run_simulation(
        _thirty_trade_ledger(),
        1000.0,
        iterations=200,
        horizon_trades=80,
        seed=9,
        block_bootstrap=True,
    )
    dumped = result.model_dump()
    for field, expected in _LEGACY_FIELDS_UNCHANGED_CALLER_SET_HORIZON.items():
        assert dumped[field] == expected, f"{field} drifted from pre-change snapshot"


def test_multi_horizon_run_is_deterministic_and_does_not_touch_global_rng():
    trades = scalper_style_trades()
    np.random.seed(7)
    before = np.random.random()
    first = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=500, seed=9, block_bootstrap=True
    )
    after = np.random.random()
    np.random.seed(7)
    assert before == np.random.random()
    assert after == np.random.random()

    second = MonteCarloSimulationEngine.run_simulation(
        trades, 1_000.0, iterations=500, seed=9, block_bootstrap=True
    )
    assert first.model_dump() == second.model_dump()

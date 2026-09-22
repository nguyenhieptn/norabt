"""The portfolio maths, tested against series whose answer is known exactly.

Every case here exists because getting it wrong produces a plausible-looking
number rather than an error: a correlation of 0.0 where the truth is "not
measurable", a rank correlation manufactured out of tie-breaking, a
diversification ratio that reports a benefit a correlated pair never had.
"""

from __future__ import annotations

import math

import numpy as np
import pytest

from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer, _rank
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger
from Agent.none.test.portfolio_factory import BASE_MS, DAY_MS, make_bot, make_trades

_SERIES = [1.0, -2.0, 3.0, -1.0, 0.5, -0.5, 2.0, -3.0, 1.5, -1.5] * 6  # 60 days


def _analyze(bots, exposure=None):
    series = TimeSeriesMerger.merge(bots)
    return series, CorrelationAnalyzer.analyze(series, exposure or {})


# --------------------------------------------------------------------------- #
# Alignment
# --------------------------------------------------------------------------- #


def test_one_trade_per_day_lands_in_daily_buckets() -> None:
    """The bucket ladder must pick 1d here: 60 days is well past MIN_BUCKETS."""
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
    ]
    series = TimeSeriesMerger.merge(bots)
    assert series.diagnostics.bucket_label == "1d"
    assert series.diagnostics.evaluated_buckets == len(_SERIES)
    assert series.matrix.shape == (2, len(_SERIES))


def test_only_the_shared_window_is_measured() -> None:
    """A bot that started later contributes nothing before it existed.

    Its absence is not a run of zero-PnL days; counting it as such would drag
    every coefficient toward whatever the other bot did in that period.
    """
    late_start = BASE_MS + 20 * DAY_MS
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES[:40], start_ms=late_start)),
    ]
    series = TimeSeriesMerger.merge(bots)
    assert series.diagnostics.overlap_start_ms == late_start
    assert series.diagnostics.overlap_end_ms == BASE_MS + 59 * DAY_MS
    # 40 shared days, not 60 and not 100.
    assert series.diagnostics.evaluated_buckets == 40


def test_member_with_too_few_trades_is_excluded_by_name() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
        make_bot("CCC", make_trades([1.0, 2.0, 3.0])),
    ]
    series = TimeSeriesMerger.merge(bots)
    assert "Bot CCC" in series.diagnostics.excluded
    assert "closed trades" in series.diagnostics.excluded["Bot CCC"]
    assert series.labels == ["Bot AAA", "Bot BBB"]


def test_non_overlapping_periods_produce_no_measurement() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES, start_ms=BASE_MS + 400 * DAY_MS)),
    ]
    series, matrix = _analyze(bots)
    assert series.is_valid is False
    assert matrix.is_valid is False
    assert any("overlap" in warning for warning in matrix.warnings)


def test_idle_buckets_are_dropped_so_n_is_not_inflated() -> None:
    """Both bots trade every third day. The 40 days nobody traded carry no
    information about co-movement and must not pad the sample size."""
    sparse = [0.0] * 0
    trades_a = make_trades(_SERIES[:20], step_ms=3 * DAY_MS)
    trades_b = make_trades(_SERIES[:20], step_ms=3 * DAY_MS)
    series = TimeSeriesMerger.merge(
        [make_bot("AAA", trades_a), make_bot("BBB", trades_b)]
    )
    assert series.diagnostics.span_buckets == 58
    assert series.diagnostics.evaluated_buckets == 20
    assert series.diagnostics.dropped_idle_buckets == 38
    assert sparse == []


# --------------------------------------------------------------------------- #
# Correlation
# --------------------------------------------------------------------------- #


def test_identical_series_correlate_at_one() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
    ]
    _, matrix = _analyze(bots)
    pair = matrix.pairs[0]
    assert pair.pearson == pytest.approx(1.0)
    assert pair.spearman == pytest.approx(1.0)
    assert matrix.average_pearson == pytest.approx(1.0)
    assert pair.relationship.value == "HIGH"


def test_exactly_inverted_series_correlate_at_minus_one() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-value for value in _SERIES])),
    ]
    _, matrix = _analyze(bots)
    pair = matrix.pairs[0]
    assert pair.pearson == pytest.approx(-1.0)
    assert pair.spearman == pytest.approx(-1.0)
    assert pair.relationship.value == "INVERSE"


def test_a_flat_bot_is_unmeasurable_not_uncorrelated() -> None:
    """Zero variance means there is no coefficient, and `None` says so.

    Returning 0.0 would claim the pair was measured and found independent --
    a far stronger statement than the data supports, and the one that would
    let a flat bot look like free diversification.
    """
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([2.0] * 60)),
    ]
    _, matrix = _analyze(bots)
    assert matrix.pairs[0].pearson is None
    assert "never varied" in matrix.pairs[0].note


def test_ranks_average_their_ties() -> None:
    """The tie rule is what stops idle buckets manufacturing rank correlation.

    With positional tie-breaking, the four zeros below would take ranks 1-4 in
    array order -- the same order for every bot -- and any two mostly-idle
    bots would then look strongly rank-correlated purely from where their
    zeros sit in the array.
    """
    ranks = _rank(np.array([0.0, 5.0, 0.0, 0.0, 0.0, 9.0]))
    assert list(ranks[[0, 2, 3, 4]]) == [2.5, 2.5, 2.5, 2.5]
    assert ranks[1] == 5.0
    assert ranks[5] == 6.0


def test_bots_that_never_trade_together_are_flagged() -> None:
    """Alternating activity is not co-movement, however the number comes out."""
    even = make_trades(_SERIES[:30], step_ms=2 * DAY_MS)
    odd = make_trades(_SERIES[:30], start_ms=BASE_MS + DAY_MS, step_ms=2 * DAY_MS)
    _, matrix = _analyze([make_bot("AAA", even), make_bot("BBB", odd)])
    assert matrix.pairs[0].co_active_buckets == 0
    assert any("same bucket" in warning for warning in matrix.warnings)


def test_p_value_marks_a_short_window_as_not_significant() -> None:
    """21 buckets of pure noise must not come back as a measured relationship."""
    rng = np.random.default_rng(7)
    bots = [
        make_bot("AAA", make_trades(list(rng.normal(0, 1, 21)))),
        make_bot("BBB", make_trades(list(rng.normal(0, 1, 21)))),
    ]
    _, matrix = _analyze(bots)
    pair = matrix.pairs[0]
    assert pair.observations == 21
    assert pair.p_value is not None and pair.p_value > 0.05
    assert pair.is_significant is False
    assert "not distinguishable from zero" in pair.note


def test_exposure_overlap_is_independent_of_pnl_correlation() -> None:
    """Same instruments, opposite behaviour: the two answers must disagree."""
    bots = [
        make_bot("AAA", make_trades(_SERIES), exposure_share={"BTC": 1.0}),
        make_bot(
            "BBB",
            make_trades([-value for value in _SERIES]),
            exposure_share={"BTC": 1.0},
        ),
    ]
    _, matrix = _analyze(
        bots, {"AAA": {"BTC": 1.0}, "BBB": {"BTC": 1.0}}
    )
    pair = matrix.pairs[0]
    assert pair.exposure_overlap == pytest.approx(1.0)
    assert pair.pearson == pytest.approx(-1.0)
    assert pair.shared_symbols == ["BTC"]


def test_three_bots_produce_a_full_symmetric_matrix() -> None:
    rng = np.random.default_rng(3)
    bots = [
        make_bot(code, make_trades(list(rng.normal(0, 1, 60))))
        for code in ("AAA", "BBB", "CCC")
    ]
    _, matrix = _analyze(bots)
    assert len(matrix.pairs) == 3
    assert len(matrix.pearson) == 3
    for i in range(3):
        assert matrix.pearson[i][i] == pytest.approx(1.0)
        for j in range(3):
            assert matrix.pearson[i][j] == pytest.approx(matrix.pearson[j][i])


# --------------------------------------------------------------------------- #
# Joint simulation
# --------------------------------------------------------------------------- #


def _joint(bots, iterations=2_000):
    series = TimeSeriesMerger.merge(bots)
    capitals = [bot.capital.capital_at_risk for bot in bots]
    return JointMonteCarloEngine.run(
        series, capitals, iterations=iterations, seed=11
    )


def test_perfectly_correlated_bots_buy_no_diversification() -> None:
    """Two copies of one bot are one bet: the joint loss tail must match the
    undiversified benchmark, not beat it."""
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES)),
    ]
    result = _joint(bots)
    assert result.is_valid
    assert result.diversification_ratio == pytest.approx(0.0, abs=0.06)
    # And the counterfactual has to show what was forfeited.
    assert result.independent_var_95_pct < result.var_95_pct
    assert result.correlation_cost_pct > 0.0


def test_inverted_bots_cut_the_loss_tail() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades([-value for value in _SERIES])),
    ]
    result = _joint(bots)
    assert result.is_valid
    assert result.diversification_ratio > 0.5
    assert result.var_95_pct < result.sum_individual_var_95_pct


def test_var_is_positive_for_a_loss_matching_the_per_bot_engine() -> None:
    """Sign convention: a VaR quoted alongside `SimulationResults.var_95_pct`
    must mean the same thing, or the two get read with opposite signs."""
    losing = [-abs(value) - 1.0 for value in _SERIES]
    bots = [
        make_bot("AAA", make_trades(losing)),
        make_bot("BBB", make_trades(losing)),
    ]
    result = _joint(bots)
    assert result.var_95_pct > 0.0
    assert result.cvar_95_pct >= result.var_95_pct


def test_missing_capital_withholds_the_simulation_rather_than_guessing() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(_SERIES), capital_at_risk=None),
    ]
    result = _joint(bots)
    assert result.is_valid is False
    assert result.var_95_pct is None
    assert any("capital at risk" in warning for warning in result.warnings)


def test_same_seed_reproduces_the_same_numbers() -> None:
    bots = [
        make_bot("AAA", make_trades(_SERIES)),
        make_bot("BBB", make_trades(list(reversed(_SERIES)))),
    ]
    first = _joint(bots)
    second = _joint(bots)
    assert first.var_95_pct == second.var_95_pct
    assert first.diversification_ratio == second.diversification_ratio
    assert math.isfinite(first.var_95_pct)

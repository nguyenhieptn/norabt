"""A Sharpe ratio is a claim; these tests check the claim is tested properly."""

from __future__ import annotations

import math

import numpy as np
import pytest

from Agent.backend.mcp.analytics.simulation.inference import (
    MIN_OBSERVATIONS,
    _normal_cdf,
    _normal_ppf,
    analyse,
)


def test_the_normal_quantile_and_cdf_match_published_values():
    assert _normal_ppf(0.975) == pytest.approx(1.959964, abs=1e-5)
    assert _normal_ppf(0.95) == pytest.approx(1.644854, abs=1e-5)
    assert _normal_cdf(1.959964) == pytest.approx(0.975, abs=1e-5)
    assert _normal_cdf(0.0) == pytest.approx(0.5, abs=1e-12)


def test_the_variance_term_collapses_to_the_textbook_value_on_normal_returns():
    """With skew 0 and kurtosis 3 the formula must reduce to 1 + SR^2/2."""
    rng = np.random.default_rng(11)
    returns = rng.normal(0.01, 0.04, 20_000)

    result = analyse(returns)
    sharpe = result.sharpe_per_trade
    observed = 1 - result.skewness * sharpe + (result.kurtosis - 1) / 4 * sharpe**2

    assert result.kurtosis == pytest.approx(3.0, abs=0.1)
    assert observed == pytest.approx(1 + sharpe**2 / 2, rel=0.02)


def test_a_losing_record_gets_a_low_probabilistic_sharpe():
    rng = np.random.default_rng(3)
    losing = rng.normal(-0.004, 0.03, 400)

    result = analyse(losing)

    assert result.psr < 0.1
    assert result.min_track_record_trades is None


def test_a_longer_record_needs_less_faith_than_a_short_one():
    """Same edge, more trades: the probability the Sharpe is real must rise."""
    rng = np.random.default_rng(5)
    short = analyse(rng.normal(0.003, 0.03, 40))
    long = analyse(rng.normal(0.003, 0.03, 4_000))

    assert long.psr > short.psr


def test_picking_the_best_of_many_candidates_deflates_the_sharpe():
    """The bot was chosen as the best of its pool; DSR must price that in."""
    rng = np.random.default_rng(9)
    returns = rng.normal(0.004, 0.03, 300)

    alone = analyse(returns)
    picked = analyse(returns, selection_trials=60)

    assert picked.deflated_sharpe is not None
    assert picked.deflated_sharpe < alone.psr
    assert picked.expected_max_sharpe > 0


def test_more_candidates_means_a_harder_threshold():
    rng = np.random.default_rng(13)
    returns = rng.normal(0.004, 0.03, 300)

    few = analyse(returns, selection_trials=5)
    many = analyse(returns, selection_trials=200)

    assert many.expected_max_sharpe > few.expected_max_sharpe
    assert many.deflated_sharpe < few.deflated_sharpe


def test_minimum_track_record_length_is_consistent_with_the_psr():
    """MinTRL is the n at which PSR would reach the confidence level."""
    rng = np.random.default_rng(17)
    returns = rng.normal(0.002, 0.03, 500)

    result = analyse(returns, confidence=0.95)
    variance_term = (
        1
        - result.skewness * result.sharpe_per_trade
        + (result.kurtosis - 1) / 4 * result.sharpe_per_trade**2
    )
    expected = 1 + variance_term * (1.644854 / result.sharpe_per_trade) ** 2

    assert result.min_track_record_trades == pytest.approx(expected, rel=1e-3)


def test_a_moment_driven_by_one_outlier_is_marked_unreliable():
    """One 50 % fill in a 120-trade ledger must not produce confident stats."""
    rng = np.random.default_rng(23)
    returns = np.concatenate([rng.normal(0.002, 0.01, 120), [0.5]])

    result = analyse(returns)

    assert result.reliable is False
    assert any("Kurtosis" in note for note in result.notes)


def test_a_clean_sample_is_not_marked_unreliable():
    rng = np.random.default_rng(29)

    assert analyse(rng.normal(0.004, 0.03, 1_000)).reliable is True


def test_too_few_trades_yields_no_inference_rather_than_a_guess():
    result = analyse([0.01] * (MIN_OBSERVATIONS - 1))

    assert result.psr is None
    assert result.sharpe_per_trade is None
    assert result.notes


def test_a_flat_return_series_is_refused_instead_of_dividing_by_zero():
    result = analyse([0.0] * 50)

    assert result.psr is None
    assert not math.isnan(result.sample_size)

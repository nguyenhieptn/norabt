from __future__ import annotations

import math

import pytest

from Agent.backend.research.statistics import (
    bootstrap_correlation_ci,
    permutation_null_correlation,
    spearman_correlation,
)


def test_spearman_perfect_negative_correlation():
    assert spearman_correlation([1, 2, 3, 4, 5], [5, 4, 3, 2, 1]) == pytest.approx(-1.0)


def test_spearman_perfect_positive_correlation():
    assert spearman_correlation([1, 2, 3], [1, 2, 3]) == pytest.approx(1.0)


def test_spearman_no_ties_matches_hand_computed_value():
    """rho = 1 - 6*sum(d^2) / (n*(n^2-1)) with no ties: ranks are [1,2,3,4,5]
    and [2,1,4,3,5], d = [-1,1,-1,1,0], sum(d^2)=4, n=5 -> rho = 1 - 24/120 = 0.8.
    """
    assert spearman_correlation([1, 2, 3, 4, 5], [2, 1, 4, 3, 5]) == pytest.approx(0.8)


def test_spearman_with_ties_matches_hand_computed_value():
    """x=[1,1,2,3] ranks to [1.5,1.5,3,4]; y=[1,2,2,3] ranks to [1,2.5,2.5,4].
    Pearson correlation of those rank vectors is 3.75/4.5 = 0.8333...
    (worked out by hand in the module design; see Agent/backend/research/
    statistics.py's _rank for the averaging convention this depends on).
    """
    assert spearman_correlation([1, 1, 2, 3], [1, 2, 2, 3]) == pytest.approx(
        0.8333333333333334
    )


def test_spearman_constant_input_is_nan():
    assert math.isnan(spearman_correlation([1, 1, 1], [1, 2, 3]))


def test_spearman_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        spearman_correlation([1, 2, 3], [1, 2])


def test_spearman_rejects_too_few_points():
    with pytest.raises(ValueError):
        spearman_correlation([1], [1])


def test_bootstrap_ci_for_perfect_correlation_is_tight_at_one():
    """Every bootstrap resample of (x, y=x) keeps x'[i] == y'[i] elementwise
    (the same index is drawn for both), so every valid resample's rank
    correlation is still exactly 1.0 -- the CI must collapse to a point.
    """
    x = list(range(20))
    y = list(range(20))
    result = bootstrap_correlation_ci(x, y, seed=0, n_resamples=500)
    assert result.point_estimate == pytest.approx(1.0)
    assert result.ci_low == pytest.approx(1.0)
    assert result.ci_high == pytest.approx(1.0)
    assert result.n_valid_resamples > 0


def test_bootstrap_ci_is_reproducible_with_the_same_seed():
    x = [1, 5, 2, 4, 3, 7, 6, 9, 8, 10]
    y = [2, 1, 4, 3, 6, 5, 8, 7, 10, 9]
    first = bootstrap_correlation_ci(x, y, seed=1, n_resamples=200)
    second = bootstrap_correlation_ci(x, y, seed=1, n_resamples=200)
    assert first == second


def test_bootstrap_ci_differs_for_different_seeds_but_stays_reproducible():
    x = [1, 5, 2, 4, 3, 7, 6, 9, 8, 10]
    y = [2, 1, 4, 3, 6, 5, 8, 7, 10, 9]
    seed_one = bootstrap_correlation_ci(x, y, seed=1, n_resamples=200)
    seed_two = bootstrap_correlation_ci(x, y, seed=2, n_resamples=200)
    # Not a hard requirement that they differ, but with 200 resamples over a
    # non-degenerate sample this pair of seeds is known to land on different
    # percentile estimates -- guards against the seed silently being ignored.
    assert (seed_one.ci_low, seed_one.ci_high) != (seed_two.ci_low, seed_two.ci_high)


def test_bootstrap_ci_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        bootstrap_correlation_ci([1, 2, 3], [1, 2], seed=0)


def test_permutation_null_reproducible_with_same_seed():
    x = list(range(30))
    y = list(range(30))
    y[3], y[4] = y[4], y[3]
    y[10], y[20] = y[20], y[10]
    first = permutation_null_correlation(x, y, seed=3, n_permutations=300)
    second = permutation_null_correlation(x, y, seed=3, n_permutations=300)
    assert first.observed == second.observed
    assert first.null_samples == second.null_samples
    assert first.p_value_two_sided == second.p_value_two_sided


def test_permutation_null_p_value_is_small_for_a_strong_real_signal():
    """A near-perfect monotonic relationship (rho ~ 0.955) should sit far out
    in the tail of a null built from shuffling y -- shuffled labels essentially
    never reproduce that strong a rank correlation by chance over 30 points.
    """
    x = list(range(30))
    y = list(range(30))
    y[3], y[4] = y[4], y[3]
    y[10], y[20] = y[20], y[10]
    result = permutation_null_correlation(x, y, seed=3, n_permutations=1000)
    assert result.observed == pytest.approx(0.9550611790878755)
    assert result.p_value_two_sided < 0.01


def test_permutation_null_rejects_mismatched_lengths():
    with pytest.raises(ValueError):
        permutation_null_correlation([1, 2, 3], [1, 2], seed=0)

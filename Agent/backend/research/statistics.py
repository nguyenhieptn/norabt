"""Spearman rank correlation, a bootstrap CI for it, and a shuffle null.

Hand-rolled on top of numpy only -- no scipy, per this project's no-new-
dependency rule (numpy is already a dependency). Spearman's rho is just the
Pearson correlation of the two samples' ranks (average rank on ties), which
is all `spearman_correlation` below computes.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple

import numpy as np


def _rank(values: np.ndarray) -> np.ndarray:
    """Average ("fractional") ranks, 1-based, with ties sharing the mean rank
    of the positions they span -- the standard convention Spearman's rho
    uses.
    """
    order = np.argsort(values, kind="mergesort")
    sorted_values = values[order]
    n = len(values)
    ranks = np.empty(n, dtype=float)
    i = 0
    while i < n:
        j = i
        while j + 1 < n and sorted_values[j + 1] == sorted_values[i]:
            j += 1
        average_rank = (i + j) / 2.0 + 1.0
        ranks[order[i : j + 1]] = average_rank
        i = j + 1
    return ranks


def spearman_correlation(x: Sequence[float], y: Sequence[float]) -> float:
    """Spearman's rank correlation coefficient between x and y.

    Returns nan if either sample has zero variance in rank (e.g. every value
    identical), since correlation is undefined there -- callers must check
    for nan rather than treat it as zero.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.shape != y_arr.shape:
        raise ValueError("x and y must have the same length")
    if x_arr.size < 2:
        raise ValueError("need at least 2 paired observations")

    rank_x = _rank(x_arr)
    rank_y = _rank(y_arr)
    rank_x_centered = rank_x - rank_x.mean()
    rank_y_centered = rank_y - rank_y.mean()
    denom = np.sqrt((rank_x_centered**2).sum() * (rank_y_centered**2).sum())
    if denom == 0:
        return float("nan")
    return float((rank_x_centered * rank_y_centered).sum() / denom)


@dataclass(frozen=True)
class BootstrapResult:
    point_estimate: float
    ci_low: float
    ci_high: float
    ci_low_pct: float
    ci_high_pct: float
    n_resamples: int
    n_valid_resamples: int
    seed: int


def bootstrap_correlation_ci(
    x: Sequence[float],
    y: Sequence[float],
    seed: int,
    n_resamples: int = 2000,
    ci_low_pct: float = 2.5,
    ci_high_pct: float = 97.5,
) -> BootstrapResult:
    """Percentile bootstrap CI for spearman_correlation(x, y).

    Resamples PAIRS (x[i], y[i]) with replacement -- i.e. resamples bots, not
    individual trades -- n_resamples times, recomputes the correlation each
    time, and reports the requested percentiles. Deterministic for a given
    seed (uses numpy's Generator API, not the legacy global RNG), so a second
    run with the same seed reproduces byte-identical bounds.

    Resamples whose shuffled correlation is undefined (nan, e.g. a resample
    that happens to draw the same bot n times) are dropped before taking
    percentiles; n_valid_resamples reports how many were left.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.shape != y_arr.shape:
        raise ValueError("x and y must have the same length")
    n = x_arr.size
    if n < 2:
        raise ValueError("need at least 2 paired observations to bootstrap")

    point_estimate = spearman_correlation(x_arr, y_arr)
    rng = np.random.default_rng(seed)
    stats = np.empty(n_resamples, dtype=float)
    for i in range(n_resamples):
        idx = rng.integers(0, n, size=n)
        stats[i] = spearman_correlation(x_arr[idx], y_arr[idx])
    valid = stats[~np.isnan(stats)]
    n_valid = int(valid.size)
    if n_valid == 0:
        return BootstrapResult(
            point_estimate=point_estimate,
            ci_low=float("nan"),
            ci_high=float("nan"),
            ci_low_pct=ci_low_pct,
            ci_high_pct=ci_high_pct,
            n_resamples=n_resamples,
            n_valid_resamples=0,
            seed=seed,
        )
    lo, hi = np.percentile(valid, [ci_low_pct, ci_high_pct])
    return BootstrapResult(
        point_estimate=point_estimate,
        ci_low=float(lo),
        ci_high=float(hi),
        ci_low_pct=ci_low_pct,
        ci_high_pct=ci_high_pct,
        n_resamples=n_resamples,
        n_valid_resamples=n_valid,
        seed=seed,
    )


@dataclass(frozen=True)
class PermutationNullResult:
    observed: float
    null_samples: Tuple[float, ...]
    p_value_two_sided: float
    n_permutations: int
    seed: int


def permutation_null_correlation(
    x: Sequence[float],
    y: Sequence[float],
    seed: int,
    n_permutations: int = 2000,
) -> PermutationNullResult:
    """Shuffle y relative to x n_permutations times and recompute the
    correlation each time, to show what a coefficient of the observed size
    would look like if the score carried no real information (the null
    hypothesis: risk_score and this outcome are independent).

    The two-sided p-value is the fraction of null-shuffle correlations at
    least as extreme (by absolute value) as the observed one -- the standard
    permutation-test estimator. NaN null samples (degenerate shuffles) are
    excluded from both the returned samples and the p-value denominator.
    """
    x_arr = np.asarray(x, dtype=float)
    y_arr = np.asarray(y, dtype=float)
    if x_arr.shape != y_arr.shape:
        raise ValueError("x and y must have the same length")
    n = x_arr.size
    if n < 2:
        raise ValueError("need at least 2 paired observations to permute")

    observed = spearman_correlation(x_arr, y_arr)
    rng = np.random.default_rng(seed)
    samples = np.empty(n_permutations, dtype=float)
    for i in range(n_permutations):
        shuffled_y = rng.permutation(y_arr)
        samples[i] = spearman_correlation(x_arr, shuffled_y)
    valid = samples[~np.isnan(samples)]
    if valid.size == 0 or np.isnan(observed):
        p_value = float("nan")
    else:
        p_value = float(np.mean(np.abs(valid) >= abs(observed)))
    return PermutationNullResult(
        observed=observed,
        null_samples=tuple(float(v) for v in samples),
        p_value_two_sided=p_value,
        n_permutations=n_permutations,
        seed=seed,
    )

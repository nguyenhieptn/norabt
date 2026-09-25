"""Pairwise co-movement between bots, measured two ways that can disagree.

PEARSON answers "when one bot's PnL is above its average, is the other's?" --
linear, driven by the big buckets, and the coefficient a joint VaR is
consistent with. SPEARMAN answers the same question about RANKS, so it
survives the fat tails a trading ledger always has and is not carried by one
shared blow-up week. Reporting both is deliberate: a pair that is high on
Pearson but low on Spearman shares its disasters without sharing its ordinary
days, which is precisely the pair a portfolio owner most needs to know about,
and either number alone hides it.

EXPOSURE OVERLAP is a third, independent question -- do these bots hold the
same instruments -- and it routinely disagrees with both. Two bots on the same
symbol running opposite strategies overlap fully and correlate negatively;
two bots on unrelated alts overlap not at all and correlate at 0.9 because
both are levered beta to Bitcoin. Neither one implies the other, so neither is
allowed to stand in for the other.

scipy is NOT a dependency of this project (see Agent/requirements.txt: numpy
only), so the rank transform and the p-value are implemented here rather than
imported. Both are standard textbook forms, noted at each site.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence

import numpy as np

from Agent.backend.report.qc.portfolio.schemas import (
    CorrelationMatrix,
    PairCorrelation,
    PairRelationship,
)
from Agent.backend.report.qc.portfolio.timeseries import AlignedSeries


def _rank(values: np.ndarray) -> np.ndarray:
    """Average-tie ranks, the transform Spearman's rho is defined on.

    Ties must share the mean of the ranks they span. A trading series bucketed
    by time is full of exact ties (every bucket the bot sat out is 0.0), and
    breaking them by position instead -- which `argsort().argsort()` alone
    does -- would invent an ordering among those idle buckets out of nothing
    but their place in the array, and that invented ordering is the same for
    every bot, manufacturing rank correlation where there is none.
    """
    order = np.argsort(values, kind="mergesort")
    ranks = np.empty(len(values), dtype=np.float64)
    ranks[order] = np.arange(1, len(values) + 1, dtype=np.float64)
    sorted_values = values[order]
    start = 0
    for index in range(1, len(sorted_values) + 1):
        if index == len(sorted_values) or sorted_values[index] != sorted_values[start]:
            if index - start > 1:
                ranks[order[start:index]] = ranks[order[start:index]].mean()
            start = index
    return ranks


def _pearson(a: np.ndarray, b: np.ndarray) -> Optional[float]:
    """Pearson r, or None where it is undefined rather than zero.

    A constant series has no variance, so there is no coefficient to report.
    Returning 0.0 there would read as "measured, and they are unrelated",
    which is a different and much stronger claim than "not measurable".
    """
    if len(a) < 3:
        return None
    std_a = float(np.std(a))
    std_b = float(np.std(b))
    if std_a <= 0.0 or std_b <= 0.0:
        return None
    r = float(np.corrcoef(a, b)[0, 1])
    if not math.isfinite(r):
        return None
    return max(-1.0, min(1.0, r))


def _p_value(r: Optional[float], n: int) -> Optional[float]:
    """Two-sided p for H0: rho = 0, via Fisher's z transform.

    z = artanh(r) * sqrt(n - 3) is approximately standard normal under the
    null, and the normal tail is available from `math.erfc` without pulling in
    scipy. The transform needs n > 3 and |r| < 1; both are guarded.
    """
    if r is None or n <= 3:
        return None
    if abs(r) >= 1.0:
        return 0.0
    z = math.atanh(r) * math.sqrt(n - 3)
    return max(0.0, min(1.0, math.erfc(abs(z) / math.sqrt(2.0))))


def _exposure_overlap(
    a: Dict[str, float], b: Dict[str, float]
) -> Optional[float]:
    """Cosine similarity of two exposure-share vectors, 0-1.

    Cosine rather than a plain shared-symbol count because share matters: a bot
    with 98% of its book in BTC and 2% in SOL is not half-overlapped with a
    pure SOL bot. Both vectors are non-negative, so the result stays in [0, 1]
    and needs no rescaling.
    """
    if not a or not b:
        return None
    symbols = sorted(set(a) | set(b))
    vec_a = np.array([float(a.get(symbol, 0.0)) for symbol in symbols])
    vec_b = np.array([float(b.get(symbol, 0.0)) for symbol in symbols])
    norm = float(np.linalg.norm(vec_a) * np.linalg.norm(vec_b))
    if norm <= 0.0:
        return None
    return max(0.0, min(1.0, float(np.dot(vec_a, vec_b)) / norm))


class CorrelationAnalyzer:
    # Bands for the human-readable label only. The coefficient itself is always
    # reported, so a reader who wants their own threshold has the number.
    INVERSE_THRESHOLD = -0.2
    LOW_THRESHOLD = 0.3
    MODERATE_THRESHOLD = 0.6
    SIGNIFICANCE_ALPHA = 0.05

    @classmethod
    def _relationship(cls, r: Optional[float]) -> PairRelationship:
        if r is None:
            return PairRelationship.UNKNOWN
        if r <= cls.INVERSE_THRESHOLD:
            return PairRelationship.INVERSE
        if r < cls.LOW_THRESHOLD:
            return PairRelationship.LOW
        if r < cls.MODERATE_THRESHOLD:
            return PairRelationship.MODERATE
        return PairRelationship.HIGH

    @staticmethod
    def _note(
        pair: PairRelationship,
        r: Optional[float],
        shared_symbols: Sequence[str],
        overlap: Optional[float],
        significant: bool,
    ) -> str:
        if r is None:
            return "Not measurable: at least one bot's PnL never varied over the shared window"
        if not significant:
            return (
                f"r = {r:+.2f}, but not distinguishable from zero at this sample "
                "size -- treat as unmeasured rather than as independence"
            )
        if pair is PairRelationship.INVERSE:
            return f"r = {r:+.2f}: these two tend to offset each other"
        if pair is PairRelationship.HIGH:
            if shared_symbols:
                return (
                    f"r = {r:+.2f} and they trade {', '.join(shared_symbols[:3])} in "
                    "common -- effectively one position split across two bots"
                )
            return (
                f"r = {r:+.2f} despite trading different instruments -- a shared "
                "driver, not diversification"
            )
        if pair is PairRelationship.MODERATE:
            return f"r = {r:+.2f}: partly overlapping, some diversification remains"
        if overlap is not None and overlap > 0.5:
            return (
                f"r = {r:+.2f} even though they hold {overlap:.0%} of the same "
                "exposure -- genuinely different behaviour on the same instruments"
            )
        return f"r = {r:+.2f}: largely independent"

    @classmethod
    def analyze(
        cls,
        series: AlignedSeries,
        exposure_by_code: Optional[Dict[str, Dict[str, float]]] = None,
    ) -> CorrelationMatrix:
        exposure_by_code = exposure_by_code or {}
        labels = list(series.labels)
        codes = list(series.codes)
        count = len(labels)
        warnings = list(series.diagnostics.warnings)

        if count < 2 or not series.diagnostics.is_valid:
            return CorrelationMatrix(
                labels=labels,
                codes=codes,
                alignment=series.diagnostics,
                is_valid=False,
                warnings=warnings
                or ["The shared window was too short to measure co-movement"],
            )

        matrix = series.matrix
        observations = int(matrix.shape[1])
        ranks = np.vstack([_rank(matrix[row]) for row in range(count)])

        pearson: List[List[Optional[float]]] = [
            [None] * count for _ in range(count)
        ]
        spearman: List[List[Optional[float]]] = [
            [None] * count for _ in range(count)
        ]
        pairs: List[PairCorrelation] = []
        overlaps: List[float] = []

        for i in range(count):
            # A series correlates perfectly with itself only if it varies at
            # all; keeping the diagonal honest means a flat member shows as
            # unmeasurable everywhere, including against itself.
            self_r = _pearson(matrix[i], matrix[i])
            pearson[i][i] = self_r
            spearman[i][i] = _pearson(ranks[i], ranks[i])
            for j in range(i + 1, count):
                r = _pearson(matrix[i], matrix[j])
                rho = _pearson(ranks[i], ranks[j])
                pearson[i][j] = pearson[j][i] = r
                spearman[i][j] = spearman[j][i] = rho

                co_active = int(
                    np.count_nonzero((matrix[i] != 0.0) & (matrix[j] != 0.0))
                )
                p_value = _p_value(r, observations)
                significant = p_value is not None and p_value < cls.SIGNIFICANCE_ALPHA
                exposure_a = exposure_by_code.get(codes[i], {})
                exposure_b = exposure_by_code.get(codes[j], {})
                shared = sorted(set(exposure_a) & set(exposure_b))
                overlap = _exposure_overlap(exposure_a, exposure_b)
                if overlap is not None:
                    overlaps.append(overlap)
                relationship = cls._relationship(r)
                pairs.append(
                    PairCorrelation(
                        label_a=labels[i],
                        label_b=labels[j],
                        code_a=codes[i],
                        code_b=codes[j],
                        pearson=r,
                        spearman=rho,
                        observations=observations,
                        co_active_buckets=co_active,
                        p_value=p_value,
                        is_significant=significant,
                        shared_symbols=shared,
                        exposure_overlap=overlap,
                        relationship=relationship,
                        note=cls._note(
                            relationship, r, shared, overlap, significant
                        ),
                    )
                )

        measured = [pair.pearson for pair in pairs if pair.pearson is not None]
        if not measured:
            warnings.append(
                "No pair produced a usable coefficient; every member's PnL was "
                "flat across the shared window"
            )
        strongest = max(
            (pair for pair in pairs if pair.pearson is not None),
            key=lambda pair: pair.pearson,
            default=None,
        )
        for pair in pairs:
            if pair.co_active_buckets == 0 and pair.pearson is not None:
                warnings.append(
                    f"[{pair.label_a}] and [{pair.label_b}] never had PnL in the "
                    "same period, so their coefficient describes alternating "
                    "activity rather than co-movement"
                )

        return CorrelationMatrix(
            labels=labels,
            codes=codes,
            pearson=pearson,
            spearman=spearman,
            pairs=pairs,
            average_pearson=float(np.mean(measured)) if measured else None,
            max_pearson=float(np.max(measured)) if measured else None,
            max_pearson_pair=(
                [strongest.label_a, strongest.label_b] if strongest else None
            ),
            min_pearson=float(np.min(measured)) if measured else None,
            average_exposure_overlap=(
                float(np.mean(overlaps)) if overlaps else None
            ),
            alignment=series.diagnostics,
            is_valid=bool(measured),
            warnings=warnings,
        )

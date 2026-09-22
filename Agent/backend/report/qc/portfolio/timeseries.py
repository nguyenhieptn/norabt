"""Put several bots' closed-trade ledgers on one shared clock.

Every cross-bot number in this package -- correlation, joint VaR, the
diversification ratio -- is a statement about what the bots did AT THE SAME
TIME, so none of them can be computed until the ledgers share a time axis.
That alignment involves three choices that change the answer, and all three
are recorded in `AlignmentDiagnostics` rather than left implicit:

1. WHICH TIMESTAMP. A trade's realized PnL is booked when it CLOSES, so
   `close_time` is the event time. Using `open_time` would attribute a loss to
   the moment the bot committed rather than the moment the account felt it,
   and two bots holding for very different durations would then appear to move
   together purely because they entered together.

2. WHICH WINDOW. Only the span where every included bot was actually trading.
   Outside it a bot contributes an unbroken run of zeros that it never had the
   chance to fill, which drags every correlation toward whatever the other
   bots were doing at the time.

3. HOW WIDE A BUCKET. See `_choose_bucket`.

Absolute quote-currency PnL is what goes into the matrix, not per-trade
percentages. Correlation does not care (it is scale invariant), but the joint
simulation does: a portfolio owner loses dollars, and summing percentages
across bots of different sizes would silently equal-weight them.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

import numpy as np

from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.report.qc.portfolio.schemas import AlignmentDiagnostics

_MINUTE_MS = 60_000
_HOUR_MS = 60 * _MINUTE_MS
_DAY_MS = 24 * _HOUR_MS

# Coarsest first. `_choose_bucket` walks this until a bucket produces enough
# observations, which means it always lands on the WIDEST bucket that still
# has statistical power -- see that function for why that direction.
_BUCKET_LADDER: Tuple[Tuple[str, int], ...] = (
    ("1d", _DAY_MS),
    ("4h", 4 * _HOUR_MS),
    ("1h", _HOUR_MS),
    ("15m", 15 * _MINUTE_MS),
)


@dataclass(frozen=True)
class AlignedSeries:
    """The shared-clock matrix, plus everything needed to interpret it."""

    labels: List[str]
    codes: List[str]
    # (N, T) realized PnL in quote currency: row per bot, column per bucket.
    matrix: np.ndarray
    # (T,) bucket start timestamps in ms, ascending.
    bucket_starts: np.ndarray
    bucket_ms: int
    diagnostics: AlignmentDiagnostics

    @property
    def is_valid(self) -> bool:
        return self.diagnostics.is_valid


class TimeSeriesMerger:
    """Align N bots' realized PnL onto one bucketed time axis."""

    # Below this a bot has no usable series of its own and is excluded rather
    # than carried as noise. Matches `MonteCarloSimulationEngine`'s own
    # MIN_SAMPLE_SIZE: the same ledger that is too thin to bootstrap on its
    # own is too thin to correlate.
    MIN_TRADES_PER_MEMBER = 10
    # A correlation needs a sample. Ten paired observations puts the standard
    # error of r near 0.33, at which point the coefficient is not measuring
    # anything a reader should act on.
    MIN_BUCKETS = 20
    # 10 <= n < 40: computable, but every coefficient carries a wide interval
    # (see `PairCorrelation.p_value`, which is reported for exactly this
    # reason).
    THIN_BUCKETS = 40
    # A guard on memory and on absurd resolutions, not a statistical claim.
    MAX_BUCKETS = 20_000

    @classmethod
    def _choose_bucket(cls, span_ms: int) -> Tuple[str, int, str]:
        """Pick the WIDEST bucket that still yields `MIN_BUCKETS` observations.

        The direction matters and is not the obvious one. A finer bucket gives
        more columns, which looks like more statistical power, but bots do not
        trade continuously: at 15-minute resolution a bot closing four trades a
        day is zero in 99% of its buckets, and a Pearson coefficient over two
        mostly-zero vectors measures how often the two bots happened to be idle
        together, not how their PnL co-moves. Widening the bucket trades
        columns for density, and density is the scarcer resource here. So this
        starts coarse and only goes finer when the overlap window is too short
        to supply enough daily observations.
        """
        for label, width in _BUCKET_LADDER:
            if span_ms // width >= cls.MIN_BUCKETS:
                return label, width, (
                    f"widest bucket on the ladder still yielding "
                    f"{cls.MIN_BUCKETS}+ observations over the shared window"
                )
        label, width = _BUCKET_LADDER[-1]
        return label, width, (
            "finest bucket available; the shared window is too short for "
            f"{cls.MIN_BUCKETS} observations at any resolution"
        )

    @staticmethod
    def _closed_trades(bot: BotResult) -> List[Tuple[int, float]]:
        """(close_time, realized_pnl) for every usable closed trade."""
        rows: List[Tuple[int, float]] = []
        for trade in bot.trade_ledger_summary:
            close_time = int(trade.close_time or 0)
            if close_time <= 0:
                continue
            rows.append((close_time, float(trade.realized_pnl)))
        rows.sort(key=lambda item: item[0])
        return rows

    @classmethod
    def merge(
        cls,
        bots: Sequence[BotResult],
        labels: Optional[Sequence[str]] = None,
    ) -> AlignedSeries:
        resolved_labels = list(labels) if labels is not None else [
            bot.identity.nick_name or bot.identity.unique_code for bot in bots
        ]
        if len(resolved_labels) != len(bots):
            raise ValueError("labels must be the same length as bots")

        excluded: Dict[str, str] = {}
        warnings: List[str] = []
        usable: List[Tuple[int, BotResult, str, List[Tuple[int, float]]]] = []

        for index, bot in enumerate(bots):
            label = resolved_labels[index]
            trades = cls._closed_trades(bot)
            if len(trades) < cls.MIN_TRADES_PER_MEMBER:
                excluded[label] = (
                    f"only {len(trades)} closed trades with a usable close time "
                    f"(needs {cls.MIN_TRADES_PER_MEMBER})"
                )
                continue
            usable.append((index, bot, label, trades))

        if len(usable) < 2:
            # The one bot that WAS long enough is excluded too, and for a
            # different reason than the ones that were too short. Leaving it
            # out of `excluded` would make the report claim it was measured.
            for _, _, label, _ in usable:
                excluded[label] = (
                    "no other bot has a ledger long enough to correlate against"
                )
            return cls._empty(
                resolved_labels,
                bots,
                excluded,
                warnings
                + [
                    "Fewer than two bots have a ledger long enough to correlate; "
                    "no cross-bot measurement is possible"
                ],
            )

        # The window every remaining bot was actually trading in. Anything
        # outside it is a bot that had not started, or had stopped -- zeros
        # there are absence of data, not absence of PnL.
        overlap_start = max(trades[0][0] for _, _, _, trades in usable)
        overlap_end = min(trades[-1][0] for _, _, _, trades in usable)
        if overlap_end <= overlap_start:
            for _, _, label, _ in usable:
                excluded[label] = (
                    "its trading period does not overlap the other members'"
                )
            return cls._empty(
                resolved_labels,
                bots,
                excluded,
                warnings
                + [
                    "The bots' trading periods do not overlap at all, so they "
                    "were never running at the same time and cannot be compared"
                ],
            )

        span_ms = overlap_end - overlap_start
        bucket_label, bucket_ms, bucket_reason = cls._choose_bucket(span_ms)
        span_buckets = int(span_ms // bucket_ms) + 1
        if span_buckets > cls.MAX_BUCKETS:
            # Only reachable if the ladder's coarsest rung still over-resolves,
            # i.e. a shared window of ~55 years. Fold rather than allocate.
            bucket_ms = int(np.ceil(span_ms / cls.MAX_BUCKETS))
            bucket_label = f"{bucket_ms // _HOUR_MS}h"
            bucket_reason = "widened to keep the matrix within its size bound"
            span_buckets = int(span_ms // bucket_ms) + 1

        matrix = np.zeros((len(usable), span_buckets), dtype=np.float64)
        for row, (_, _, _, trades) in enumerate(usable):
            for close_time, pnl in trades:
                if close_time < overlap_start or close_time > overlap_end:
                    continue
                column = int((close_time - overlap_start) // bucket_ms)
                matrix[row, column] += pnl

        # Drop buckets in which NOBODY traded. They say nothing about
        # co-movement (every member is identically zero) while padding n, which
        # would make every p-value below look better resolved than it is.
        traded = np.any(matrix != 0.0, axis=0)
        dropped = int(span_buckets - int(np.count_nonzero(traded)))
        matrix = matrix[:, traded]
        bucket_starts = (
            overlap_start + np.arange(span_buckets, dtype=np.int64) * bucket_ms
        )[traded]

        evaluated = int(matrix.shape[1])
        active_counts = {
            label: int(np.count_nonzero(matrix[row]))
            for row, (_, _, label, _) in enumerate(usable)
        }
        active_share = {
            label: (count / evaluated if evaluated else 0.0)
            for label, count in active_counts.items()
        }

        if evaluated < cls.MIN_BUCKETS:
            warnings.append(
                f"Only {evaluated} shared {bucket_label} buckets contain any "
                f"trading (needs {cls.MIN_BUCKETS}); correlations over this "
                "window are not interpretable"
            )
        elif evaluated < cls.THIN_BUCKETS:
            warnings.append(
                f"Thin sample: {evaluated} shared {bucket_label} buckets. The "
                "coefficients are computable but carry a wide confidence "
                "interval -- read the p-value on each pair before acting"
            )
        for label, share in active_share.items():
            if share < 0.2:
                warnings.append(
                    f"[{label}] closed a trade in only {share:.0%} of the shared "
                    "buckets, so most of its series is zeros; its correlations "
                    "partly reflect when it was idle, not only how it performed"
                )

        overlap_days = span_ms / _DAY_MS
        diagnostics = AlignmentDiagnostics(
            bucket_label=bucket_label,
            bucket_ms=bucket_ms,
            bucket_reason=bucket_reason,
            overlap_start_ms=overlap_start,
            overlap_end_ms=overlap_end,
            overlap_days=round(overlap_days, 3),
            span_buckets=span_buckets,
            evaluated_buckets=evaluated,
            dropped_idle_buckets=dropped,
            active_buckets=active_counts,
            active_share={k: round(v, 4) for k, v in active_share.items()},
            included_labels=[label for _, _, label, _ in usable],
            excluded=excluded,
            is_valid=evaluated >= cls.MIN_BUCKETS,
            warnings=warnings,
        )
        return AlignedSeries(
            labels=[label for _, _, label, _ in usable],
            codes=[bot.identity.unique_code for _, bot, _, _ in usable],
            matrix=matrix,
            bucket_starts=bucket_starts,
            bucket_ms=bucket_ms,
            diagnostics=diagnostics,
        )

    @staticmethod
    def _empty(
        labels: Sequence[str],
        bots: Sequence[BotResult],
        excluded: Dict[str, str],
        warnings: List[str],
    ) -> AlignedSeries:
        return AlignedSeries(
            labels=[],
            codes=[],
            matrix=np.zeros((0, 0), dtype=np.float64),
            bucket_starts=np.zeros((0,), dtype=np.int64),
            bucket_ms=_DAY_MS,
            diagnostics=AlignmentDiagnostics(
                bucket_label="1d",
                bucket_ms=_DAY_MS,
                bucket_reason="no alignment was possible",
                excluded=excluded,
                is_valid=False,
                warnings=warnings,
            ),
        )

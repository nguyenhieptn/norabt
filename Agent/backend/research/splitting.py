"""Time-based train/test split for a bot's closed-trade ledger.

The split MUST be by time, never random. A random split lets a trade that
closed after the cutoff land in the training half purely by chance, which
leaks exactly the information this whole exercise exists to withhold: what
happened after the scoring moment. An out-of-sample test that lets tomorrow
leak into today's training data cannot tell you anything about tomorrow --
it would just be measuring how well the score fits data it has already seen.
So every trade in the training half must close at or before every trade in
the test half, with no exceptions, which is what TimeSplit guarantees by
construction (see split_by_close_time).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, List, Sequence


@dataclass(frozen=True)
class TimeSplit:
    """One bot's closed trades, cut in time at (approximately) train_fraction.

    `train` holds every trade closing at or before `cutoff_ms`; `test` holds
    every trade closing strictly after it. Trades that tie exactly on
    close_time with the nominal cutoff trade are never split across the two
    halves -- they all stay in `train` -- so the invariant
    max(t.close_time for t in train) <= min(t.close_time for t in test)
    always holds (when both halves are non-empty). This can push
    train_fraction_actual a little above train_fraction_target when many
    trades share one timestamp; that is reported explicitly rather than
    hidden.
    """

    train: List[Any]
    test: List[Any]
    cutoff_ms: int
    train_fraction_target: float
    train_fraction_actual: float


def split_by_close_time(
    trades: Sequence[Any], train_fraction: float = 0.6
) -> TimeSplit:
    """Split `trades` (anything with a `.close_time` attribute) in time.

    Raises ValueError if the split would leave either half empty -- an
    out-of-sample test needs both a training half to score and a test half to
    measure, and a caller with too few or too clustered trades should be
    told plainly rather than silently getting a one-sided "split".
    """
    if not 0.0 < train_fraction < 1.0:
        raise ValueError("train_fraction must be strictly between 0 and 1")
    n = len(trades)
    if n == 0:
        raise ValueError("cannot split an empty trade list")

    ordered = sorted(trades, key=lambda trade: trade.close_time)
    n_train_target = max(1, min(n - 1, round(n * train_fraction)))
    cutoff_ms = ordered[n_train_target - 1].close_time

    train = [t for t in ordered if t.close_time <= cutoff_ms]
    test = [t for t in ordered if t.close_time > cutoff_ms]
    if not train or not test:
        raise ValueError(
            "time split produced an empty half (too many trades share the "
            "same close_time around the cutoff); cannot form an "
            "out-of-sample test for this bot"
        )
    return TimeSplit(
        train=train,
        test=test,
        cutoff_ms=cutoff_ms,
        train_fraction_target=train_fraction,
        train_fraction_actual=len(train) / n,
    )

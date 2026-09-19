"""Label every hour of an asset's history as a market phase.

Why this exists: a bot's record only means something against the market it ran in.
A 70 % win rate earned entirely in a calm uptrend says nothing about what happens
in a volatile downdraft, and the ledger alone cannot tell those apart. This turns
the hourly candles we already hold into a phase timeline the trade history can be
bucketed against.

Phases are derived, not fetched, so the rule is stated here rather than buried:
trend comes from the EMA50/EMA200 gap, volatility from where current ATR sits in
its own trailing distribution. An hour with too little history behind it stays
UNKNOWN instead of being guessed.
"""

from __future__ import annotations

import bisect
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence

# A trend needs to be wide enough to not be noise; below this the market ranges.
TREND_GAP_PCT = 0.5
# ATR above this percentile of its own trailing window counts as volatile.
VOLATILE_PERCENTILE = 70.0
VOLATILITY_WINDOW_HOURS = 720  # 30 days
WARMUP_HOURS = 200  # EMA200 needs this much history before it means anything


class MarketPhase(str, Enum):
    UPTREND_CALM = "UPTREND_CALM"
    UPTREND_VOLATILE = "UPTREND_VOLATILE"
    DOWNTREND_CALM = "DOWNTREND_CALM"
    DOWNTREND_VOLATILE = "DOWNTREND_VOLATILE"
    RANGE_CALM = "RANGE_CALM"
    RANGE_VOLATILE = "RANGE_VOLATILE"
    UNKNOWN = "UNKNOWN"


TRENDING = (
    MarketPhase.UPTREND_CALM,
    MarketPhase.UPTREND_VOLATILE,
    MarketPhase.DOWNTREND_CALM,
    MarketPhase.DOWNTREND_VOLATILE,
)
DOWN_PHASES = (MarketPhase.DOWNTREND_CALM, MarketPhase.DOWNTREND_VOLATILE)


@dataclass(frozen=True)
class PhaseTimeline:
    """Hourly phase labels for one asset, queryable by timestamp."""

    symbol: str
    timestamps: Sequence[int]
    phases: Sequence[MarketPhase]
    closes: Sequence[float]

    def _index_at(self, ts_ms: int) -> Optional[int]:
        if not self.timestamps or ts_ms < self.timestamps[0]:
            return None
        index = bisect.bisect_right(self.timestamps, ts_ms) - 1
        return index if 0 <= index < len(self.timestamps) else None

    def phase_at(self, ts_ms: int) -> MarketPhase:
        index = self._index_at(ts_ms)
        return self.phases[index] if index is not None else MarketPhase.UNKNOWN

    def prior_return_pct(self, ts_ms: int, hours: int = 24) -> Optional[float]:
        """Move the market had just made when the bot opened, in percent."""
        index = self._index_at(ts_ms)
        if index is None or index < hours:
            return None
        then, now = self.closes[index - hours], self.closes[index]
        if not then:
            return None
        return (now - then) / then * 100.0

    def phases_present(self, since_ms: Optional[int] = None) -> Dict[MarketPhase, int]:
        """How many hours of each phase the market itself went through."""
        counts: Dict[MarketPhase, int] = {}
        for ts, phase in zip(self.timestamps, self.phases):
            if since_ms is not None and ts < since_ms:
                continue
            if phase is MarketPhase.UNKNOWN:
                continue
            counts[phase] = counts.get(phase, 0) + 1
        return counts


def _ema(values: Sequence[float], span: int) -> List[Optional[float]]:
    alpha = 2.0 / (span + 1.0)
    out: List[Optional[float]] = []
    current: Optional[float] = None
    for index, value in enumerate(values):
        current = value if current is None else alpha * value + (1 - alpha) * current
        out.append(current if index + 1 >= span else None)
    return out


def _true_ranges(
    highs: Sequence[float], lows: Sequence[float], closes: Sequence[float]
) -> List[float]:
    ranges = [highs[0] - lows[0]] if highs else []
    for i in range(1, len(highs)):
        prev = closes[i - 1]
        ranges.append(
            max(highs[i] - lows[i], abs(highs[i] - prev), abs(lows[i] - prev))
        )
    return ranges


def build_timeline(symbol: str, candles: List[Dict[str, Any]]) -> PhaseTimeline:
    ordered = sorted(candles, key=lambda c: int(c.get("timestamp", 0)))
    timestamps = [int(c["timestamp"]) for c in ordered]
    closes = [float(c["close"]) for c in ordered]
    highs = [float(c.get("high", c["close"])) for c in ordered]
    lows = [float(c.get("low", c["close"])) for c in ordered]

    ema_fast, ema_slow = _ema(closes, 50), _ema(closes, 200)
    true_ranges = _true_ranges(highs, lows, closes)
    atr = _ema(true_ranges, 14)

    phases: List[MarketPhase] = []
    for i in range(len(ordered)):
        fast, slow, current_atr = ema_fast[i], ema_slow[i], atr[i]
        if i < WARMUP_HOURS or fast is None or slow is None or not slow:
            phases.append(MarketPhase.UNKNOWN)
            continue

        gap_pct = (fast - slow) / slow * 100.0
        window_start = max(0, i - VOLATILITY_WINDOW_HOURS)
        window = [a for a in atr[window_start : i + 1] if a is not None]
        if current_atr is None or len(window) < 24:
            phases.append(MarketPhase.UNKNOWN)
            continue
        rank = sum(1 for a in window if a <= current_atr) / len(window) * 100.0
        volatile = rank >= VOLATILE_PERCENTILE

        if gap_pct >= TREND_GAP_PCT:
            phase = (
                MarketPhase.UPTREND_VOLATILE if volatile else MarketPhase.UPTREND_CALM
            )
        elif gap_pct <= -TREND_GAP_PCT:
            phase = (
                MarketPhase.DOWNTREND_VOLATILE
                if volatile
                else MarketPhase.DOWNTREND_CALM
            )
        else:
            phase = MarketPhase.RANGE_VOLATILE if volatile else MarketPhase.RANGE_CALM
        phases.append(phase)

    return PhaseTimeline(symbol, timestamps, phases, closes)

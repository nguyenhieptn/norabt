"""Reconstruct how a bot actually trades, by replaying its ledger across phases.

Why this exists: the observed profile used to be a label off trade frequency and
hold time, which says nothing about latent risk. A bot that only ever ran in a
calm uptrend has an untested strategy no matter how good its win rate looks, and
a bot whose entire profit comes from one phase is one regime change from losing
it. Both are visible from the public ledger once each trade is placed against the
market phase in force when it opened.

Nothing here is inferred where the evidence is absent: a trade on an instrument we
hold no candles for contributes to coverage as UNKNOWN rather than being assigned
a phase, and a characterisation with too few trades behind it stays UNKNOWN.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence

from Agent.backend.bot.mcp.analytics.strategy.phases import (
    DOWN_PHASES,
    TRENDING,
    MarketPhase,
    PhaseTimeline,
)
from Agent.backend.bot.mcp.schemas.bot_result import (
    PhasePerformance,
    PositionSide,
    StrategyObservations,
    TradeLedgerItem,
)

# Below this a per-phase figure is noise, so the phase is reported but not used
# to characterise the strategy.
MIN_TRADES_PER_PHASE = 5
# A characterisation needs this much of the ledger placed on a known phase.
MIN_COVERAGE_PCT = 30.0
# Side mix beyond this counts as a one-way book rather than a two-way one.
ONE_WAY_SHARE_PCT = 85.0
TILTED_SHARE_PCT = 65.0
# Prior move that has to be there before an entry counts as following or fading.
ENTRY_MOVE_PCT = 1.0
ENTRY_STYLE_MARGIN_PCT = 60.0
# A market phase the bot never touched only counts as untested if the market
# actually offered it for this long.
UNTESTED_PHASE_MIN_HOURS = 24 * 14


def base_symbol(instrument: Optional[str]) -> str:
    """`H-USDT-SWAP` -> `H`. Ledger rows carry the full instrument id."""
    return str(instrument or "").split("-")[0].strip().upper()


class StrategyPhaseAnalyzer:
    """Bucket a ledger by market phase and describe the strategy behind it."""

    @staticmethod
    def _side_shares(trades: Sequence[TradeLedgerItem]) -> Optional[float]:
        sided = [t for t in trades if t.side in (PositionSide.LONG, PositionSide.SHORT)]
        if not sided:
            return None
        longs = sum(1 for t in sided if t.side is PositionSide.LONG)
        return longs / len(sided) * 100.0

    @classmethod
    def _phase_row(
        cls, phase: MarketPhase, trades: List[TradeLedgerItem], gross_profit: float
    ) -> PhasePerformance:
        pnls = [t.realized_pnl for t in trades]
        wins = [p for p in pnls if p > 0]
        holds = [
            t.holding_time_minutes for t in trades if t.holding_time_minutes is not None
        ]
        leverages = [t.leverage for t in trades if t.leverage]
        won = sum(p for p in pnls if p > 0)
        return PhasePerformance(
            phase=phase.value,
            trades=len(trades),
            win_rate=len(wins) / len(pnls) * 100.0 if pnls else None,
            total_pnl=sum(pnls),
            expectancy=statistics.fmean(pnls) if pnls else None,
            long_share_pct=cls._side_shares(trades),
            average_leverage=statistics.fmean(leverages) if leverages else None,
            median_hold_minutes=statistics.median(holds) if holds else None,
            profit_share_pct=(won / gross_profit * 100.0) if gross_profit > 0 else None,
        )

    @staticmethod
    def _entry_style(
        trades: Sequence[TradeLedgerItem], timelines: Dict[str, PhaseTimeline]
    ) -> tuple[str, Optional[str]]:
        """Does the bot buy strength or buy weakness?

        Compares the move the market had just made against the side taken. Only
        entries after a move worth naming are counted; entering a flat tape says
        nothing either way.
        """
        following = fading = 0
        for trade in trades:
            timeline = timelines.get(base_symbol(trade.symbol))
            if timeline is None or trade.side not in (
                PositionSide.LONG,
                PositionSide.SHORT,
            ):
                continue
            move = timeline.prior_return_pct(trade.open_time)
            if move is None or abs(move) < ENTRY_MOVE_PCT:
                continue
            with_move = (move > 0) == (trade.side is PositionSide.LONG)
            following += 1 if with_move else 0
            fading += 0 if with_move else 1

        total = following + fading
        if total < MIN_TRADES_PER_PHASE:
            return "UNKNOWN", None
        follow_pct = following / total * 100.0
        evidence = f"{following}/{total} entries opened in the direction of the prior 24h move"
        if follow_pct >= ENTRY_STYLE_MARGIN_PCT:
            return "TREND_FOLLOWING", evidence
        if follow_pct <= 100.0 - ENTRY_STYLE_MARGIN_PCT:
            return "MEAN_REVERSION", evidence
        return "MIXED", evidence

    @classmethod
    def analyze(
        cls,
        trades: Sequence[TradeLedgerItem],
        timelines: Dict[str, PhaseTimeline],
        declared: Optional[str] = None,
        fallback_profile: str = "UNKNOWN",
    ) -> StrategyObservations:
        buckets: Dict[MarketPhase, List[TradeLedgerItem]] = {}
        unknown = 0
        for trade in trades:
            timeline = timelines.get(base_symbol(trade.symbol))
            phase = (
                timeline.phase_at(trade.open_time)
                if timeline is not None
                else MarketPhase.UNKNOWN
            )
            if phase is MarketPhase.UNKNOWN:
                unknown += 1
                continue
            buckets.setdefault(phase, []).append(trade)

        total = len(trades)
        coverage = (total - unknown) / total * 100.0 if total else 0.0
        gross_profit = sum(t.realized_pnl for t in trades if t.realized_pnl > 0)

        rows = [
            cls._phase_row(phase, bucket, gross_profit)
            for phase, bucket in sorted(buckets.items(), key=lambda kv: kv[0].value)
        ]
        judged = [r for r in rows if r.trades >= MIN_TRADES_PER_PHASE]

        best = worst = None
        dependence = None
        if judged:
            best = max(judged, key=lambda r: r.total_pnl).phase
            worst = min(judged, key=lambda r: r.total_pnl).phase
            top_share = max((r.profit_share_pct or 0.0) for r in judged)
            dependence = top_share

        losing = [r.phase for r in judged if r.total_pnl < 0]

        # A phase the market offered for weeks and the bot never traded is an
        # untested regime, which is a different thing from a phase it lost in.
        offered: Dict[MarketPhase, int] = {}
        for timeline in timelines.values():
            for phase, hours in timeline.phases_present().items():
                offered[phase] = offered.get(phase, 0) + hours
        untested = [
            phase.value
            for phase, hours in sorted(offered.items(), key=lambda kv: kv[0].value)
            if hours >= UNTESTED_PHASE_MIN_HOURS and phase not in buckets
        ]

        long_share = cls._side_shares(trades)
        if long_share is None:
            bias = "UNKNOWN"
        elif long_share >= ONE_WAY_SHARE_PCT:
            bias = "LONG_ONLY"
        elif long_share <= 100.0 - ONE_WAY_SHARE_PCT:
            bias = "SHORT_ONLY"
        elif long_share >= TILTED_SHARE_PCT:
            bias = "LONG_TILTED"
        elif long_share <= 100.0 - TILTED_SHARE_PCT:
            bias = "SHORT_TILTED"
        else:
            bias = "TWO_WAY"

        style, style_evidence = (
            cls._entry_style(trades, timelines)
            if coverage >= MIN_COVERAGE_PCT
            else ("UNKNOWN", None)
        )

        tested_down = any(
            r.phase in {p.value for p in DOWN_PHASES}
            and r.trades >= MIN_TRADES_PER_PHASE
            for r in rows
        )
        tested_trend = any(
            r.phase in {p.value for p in TRENDING} and r.trades >= MIN_TRADES_PER_PHASE
            for r in rows
        )

        return StrategyObservations(
            observed_profile=fallback_profile,
            declared_strategy=declared,
            directional_bias=bias,
            long_share_pct=long_share,
            entry_style=style,
            entry_style_evidence=style_evidence,
            phase_coverage_pct=coverage,
            trades_without_phase=unknown,
            phase_breakdown=rows,
            best_phase=best,
            worst_phase=worst,
            regime_dependence_pct=dependence,
            losing_phases=losing,
            untested_phases=untested,
            tested_in_downtrend=tested_down,
            tested_in_trend=tested_trend,
        )

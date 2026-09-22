"""Fold N bots into ONE synthetic bot, so a portfolio reads like a single bot.

WHY A SYNTHETIC BOT AND NOT A NEW REPORT SHAPE. A portfolio owner asks the
same questions of three bots that they ask of one: what is the drawdown, what
does the loss tail look like, is the leverage sane, is the record earned in
one regime. Answering those with a bespoke portfolio schema would mean a
second renderer, a second set of lenses and two definitions of every metric
that would drift apart. Instead the members' ledgers are merged into one
`BotResult` and the EXISTING Logic 2 analytics and Logic 3 lenses run over it
unchanged, so the portfolio comes back as an ordinary `BotRiskAssessment` that
every existing reader -- the three report tabs included -- already knows how
to display. The only thing the portfolio adds is the correlation section,
which is the one question a single bot cannot be asked.

WHY MERGING THE LEDGER IS THE RIGHT AGGREGATION. The alternative, averaging
each member's finished metrics, produces numbers that describe nothing: the
mean of three max-drawdowns is not a drawdown any account ever suffered,
because the three did not bottom out on the same day. Concatenating the trades
and running one equity curve over the summed capital reproduces what the
combined account actually experienced, including the offsetting that makes a
portfolio worth building.

WHAT CHANGES MEANING WHEN MERGED, AND IS FLAGGED RATHER THAN HIDDEN. A few
per-bot measurements answer a subtly different question once the ledgers are
one: a losing streak becomes the portfolio's run of losing closes across all
members rather than one bot's, and the averaging-down detector sees the
portfolio adding to a losing instrument even when two independent bots did it.
Both are legitimate portfolio-level readings -- that is what the combined
account did -- but they are not the member's own number, so `combine` says so
in the result's warnings instead of letting a reader assume otherwise.
"""

from __future__ import annotations

import hashlib
from typing import Dict, List, Optional, Sequence

from Agent.backend.bot.mcp.analytics.behavior.detector import BehavioralPatternDetector
from Agent.backend.bot.mcp.analytics.drawdown.underwater import DrawdownUnderwaterAnalyzer
from Agent.backend.bot.mcp.analytics.performance.deferred_loss import DeferredLossAnalyzer
from Agent.backend.bot.mcp.analytics.performance.distribution import (
    TradeStatisticsCalculator,
)
from Agent.backend.bot.mcp.analytics.performance.metrics import PerformanceMetricsCalculator
from Agent.backend.bot.mcp.analytics.simulation.monte_carlo import (
    MonteCarloSimulationEngine,
)
from Agent.backend.bot.mcp.analytics.simulation.stress import StressSimulator
from Agent.backend.bot.mcp.analytics.strategy.exit_rule import ExitRuleAnalyzer
from Agent.backend.bot.mcp.analytics.strategy.phases import PhaseTimeline
from Agent.backend.bot.mcp.analytics.strategy.profile import (
    StrategyPhaseAnalyzer,
    base_symbol,
)
from Agent.backend.bot.mcp.capital.equity_curve import (
    CapitalModel,
    EquityCurve,
    WeeklyEquityPoint,
)
from Agent.backend.bot.mcp.schemas.bot_result import (
    BotCurrentState,
    BotIdentity,
    BotResult,
    DataQualityAssessment,
    LedgerReconciliation,
    OpenPosition,
    PositionSide,
    RiskMeasurementMode,
    TradeLedgerItem,
)

# Most limited wins: a portfolio is only as measurable as its least measurable
# member, and claiming FULL because two of three members were fully observed
# would overstate the whole.
_MODE_SEVERITY = {
    RiskMeasurementMode.FULL: 0,
    RiskMeasurementMode.PARTIAL: 1,
    RiskMeasurementMode.LIMITED: 2,
}
# Worst reconciliation status wins, for the same reason.
_RECON_SEVERITY = ("RECONCILED", "PARTIAL_LEDGER", "MISMATCH", "UNKNOWN")


class PortfolioAggregator:
    """Combine several `BotResult`s into one that stands for the whole book."""

    DEFAULT_SIMULATION_ITERATIONS = 10_000

    # ------------------------------------------------------------------ #

    @staticmethod
    def portfolio_id(codes: Sequence[str]) -> str:
        """Stable across ordering: the same set of bots is the same portfolio."""
        digest = hashlib.sha256("|".join(sorted(codes)).encode("utf-8")).hexdigest()
        return f"PORT_{digest[:12].upper()}"

    @staticmethod
    def _merge_trades(bots: Sequence[BotResult]) -> List[TradeLedgerItem]:
        """One chronological ledger. Trade ids are namespaced by owner.

        Two bots can legitimately carry the same `trade_id` (OKX numbers them
        per account), and a collision would make two distinct fills look like
        one row to anything that de-duplicates downstream.
        """
        merged: List[TradeLedgerItem] = []
        for bot in bots:
            prefix = bot.identity.unique_code[:8]
            for trade in bot.trade_ledger_summary:
                merged.append(
                    trade.model_copy(update={"trade_id": f"{prefix}:{trade.trade_id}"})
                )
        merged.sort(key=lambda trade: (trade.close_time, trade.open_time))
        return merged

    @staticmethod
    def _merge_positions(bots: Sequence[BotResult]) -> List[OpenPosition]:
        positions: List[OpenPosition] = []
        for bot in bots:
            prefix = bot.identity.unique_code[:8]
            for position in bot.current_state.open_positions:
                positions.append(
                    position.model_copy(
                        update={"position_id": f"{prefix}:{position.position_id}"}
                    )
                )
        return positions

    @classmethod
    def _merge_state(cls, bots: Sequence[BotResult]) -> BotCurrentState:
        states = [bot.current_state for bot in bots]

        def total(attr: str) -> Optional[float]:
            values = [getattr(state, attr) for state in states]
            present = [value for value in values if value is not None]
            # All-or-nothing: summing the members that happen to report a field
            # and presenting it as the portfolio's total would understate it
            # silently. Absent beats wrong.
            return sum(present) if len(present) == len(values) else None

        exposure: Dict[str, float] = {}
        for state in states:
            for symbol, value in (state.exposure_by_symbol or {}).items():
                exposure[base_symbol(symbol)] = exposure.get(
                    base_symbol(symbol), 0.0
                ) + float(value)

        sides = {
            state.current_position_side
            for state in states
            if state.current_position_side
            not in (PositionSide.FLAT, PositionSide.UNKNOWN)
        }
        if not sides:
            side = PositionSide.FLAT
        elif len(sides) == 1:
            side = next(iter(sides))
        else:
            # Members pointing different ways is a NET book, not a LONG one.
            side = PositionSide.NET

        gross = total("current_notional")
        long_notional = sum(
            state.current_notional or 0.0
            for state in states
            if state.current_position_side == PositionSide.LONG
        )
        short_notional = sum(
            state.current_notional or 0.0
            for state in states
            if state.current_position_side == PositionSide.SHORT
        )
        equity = total("current_equity")
        margin = total("used_margin")
        # Recomputed from the merged totals, never averaged: a ratio of sums is
        # not the sum of ratios, and averaging member margin ratios would give
        # a number no account holds.
        margin_ratio = (
            margin / equity if margin is not None and equity and equity > 0 else None
        )
        leverage = (
            gross / equity if gross is not None and equity and equity > 0 else None
        )

        return BotCurrentState(
            current_equity=equity,
            reference_capital=total("reference_capital"),
            reference_capital_source="PORTFOLIO_SUM",
            available_balance=total("available_balance"),
            used_margin=margin,
            margin_ratio=margin_ratio,
            capital_consistency="PORTFOLIO_AGGREGATE",
            current_position_side=side,
            current_notional=gross,
            gross_exposure=gross,
            net_exposure=long_notional - short_notional,
            current_leverage=leverage,
            unrealized_pnl=total("unrealized_pnl"),
            # Deliberately omitted: a liquidation price and its distance belong
            # to one position on one instrument. A portfolio has neither, and a
            # fabricated one would be read as a real margin-call level.
            liquidation_price=None,
            liquidation_distance_pct=None,
            long_notional=long_notional or None,
            short_notional=short_notional or None,
            open_positions_count=sum(s.open_positions_count for s in states),
            attributed_positions_count=sum(s.attributed_positions_count for s in states),
            observed_positions_count=sum(s.observed_positions_count for s in states),
            inferred_positions_count=sum(s.inferred_positions_count for s in states),
            positions_outside_ledger_universe=sum(
                s.positions_outside_ledger_universe for s in states
            ),
            unknown_positions_count=sum(s.unknown_positions_count for s in states),
            instrument_withheld_upstream=any(
                s.instrument_withheld_upstream for s in states
            ),
            open_position_symbols=sorted(
                {sym for s in states for sym in s.open_position_symbols}
            ),
            exposure_by_symbol=exposure,
            open_positions=cls._merge_positions(bots),
        )

    @staticmethod
    def _merge_equity_curve(bots: Sequence[BotResult]) -> Optional[EquityCurve]:
        """Add the members' weekly equity curves into one portfolio curve.

        WHY THIS IS WORTH THE TROUBLE. Without a combined curve the drawdown
        lens has no denominator and comes back UNKNOWN, which loses one of the
        ten dimensions for every portfolio -- the portfolio report would be
        structurally poorer than the single-bot report it is supposed to
        match. A drawdown in money is not a drawdown until it is measured
        against the equity that was standing at the time.

        WHAT MAKES THE SUM LEGITIMATE, AND WHERE IT STOPS. Each member's
        `equity_at` forward-fills from its own observed weeks, so summing at a
        shared timestamp is adding three real observations, not interpolating
        between them. That only holds from the week every member has started
        reporting: before that, `equity_at` falls back to a member's FIRST
        observation, which would project today's account size backwards into a
        period it did not exist. The curve therefore begins at the latest
        member start, and if any member has no usable curve at all there is no
        combined curve -- the lens stays UNKNOWN rather than being fed a total
        that is missing a member.
        """
        curves = [bot.capital.equity_curve for bot in bots]
        if not all(curve is not None and curve.is_usable for curve in curves):
            return None
        starts = []
        weeks: set[int] = set()
        for curve in curves:
            usable = [
                point for point in curve.points if point.usable and point.start_equity
            ]
            if not usable:
                return None
            starts.append(min(point.week_start_ms for point in usable))
            weeks.update(point.week_start_ms for point in usable)
        floor = max(starts)
        grid = sorted(week for week in weeks if week >= floor)
        if len(grid) < 2:
            return None

        totals: List[float] = []
        for week in grid:
            values = [curve.equity_at(week) for curve in curves]
            if any(value is None or value <= 0 for value in values):
                return None
            totals.append(float(sum(values)))

        points: List[WeeklyEquityPoint] = []
        for index, (week, equity) in enumerate(zip(grid, totals)):
            end = totals[index + 1] if index + 1 < len(totals) else equity
            pnl = end - equity
            points.append(
                WeeklyEquityPoint(
                    week_start_ms=week,
                    pnl=pnl,
                    pnl_ratio=pnl / equity if equity else 0.0,
                    start_equity=equity,
                    end_equity=end,
                    usable=True,
                )
            )
        peak = totals[0]
        max_dd = 0.0
        for equity in totals:
            peak = max(peak, equity)
            max_dd = max(max_dd, (peak - equity) / peak)
        return EquityCurve(
            basis="WEEKLY_EQUITY_CURVE",
            points=points,
            usable_points=len(points),
            coverage_weeks=len(points),
            start_equity=totals[0],
            latest_equity=totals[-1],
            peak_equity=peak,
            max_drawdown_pct=min(100.0, max_dd * 100.0),
            consistency="PORTFOLIO_SUM",
            warnings=[
                "Summed from the members' own weekly curves, starting at the week "
                "every member had begun reporting; earlier weeks are outside the "
                "portfolio's shared history and are not projected backwards"
            ],
        )

    @staticmethod
    def _merge_capital(bots: Sequence[BotResult]) -> CapitalModel:
        capitals = [bot.capital for bot in bots]
        at_risk = [item.capital_at_risk for item in capitals]
        warnings: List[str] = []
        for bot, item in zip(bots, capitals):
            warnings.extend(
                f"[{bot.identity.nick_name}] {line}" for line in item.warnings
            )
        if any(value is None or value <= 0 for value in at_risk):
            missing = [
                bot.identity.nick_name
                for bot, value in zip(bots, at_risk)
                if value is None or value <= 0
            ]
            warnings.append(
                "Portfolio capital cannot be summed: no capital at risk resolved for "
                + ", ".join(f"[{name}]" for name in missing)
                + ". Every percentage-of-capital figure is withheld rather than "
                "computed against a partial total."
            )
            total = None
        else:
            total = float(sum(at_risk))
        reported = [item.reported_aum for item in capitals]
        curve = PortfolioAggregator._merge_equity_curve(bots)
        if curve is None:
            warnings.append(
                "No combined weekly equity curve could be built, so drawdowns are "
                "reported in money only -- a percentage would need a denominator "
                "that does not exist for this set"
            )
        return CapitalModel(
            basis="PORTFOLIO_SUM_OF_MEMBERS",
            capital_at_risk=total,
            reported_aum=(
                float(sum(value for value in reported if value is not None))
                if all(value is not None for value in reported)
                else None
            ),
            equity_curve=curve or EquityCurve(),
            supports_historical_pct=curve is not None,
            warnings=warnings,
        )

    @staticmethod
    def _merge_quality(
        bots: Sequence[BotResult], mode: RiskMeasurementMode, extra: Sequence[str]
    ) -> DataQualityAssessment:
        qualities = [bot.data_quality for bot in bots]
        coverages = [item.coverage_days for item in qualities]
        warnings: List[str] = list(extra)
        for bot, item in zip(bots, qualities):
            warnings.extend(
                f"[{bot.identity.nick_name}] {line}" for line in item.warnings
            )
        return DataQualityAssessment(
            # Minimum, not mean: the portfolio's evidence is as good as its
            # weakest member's, because that member's gaps are in every
            # combined number.
            completeness_score=min(item.completeness_score for item in qualities),
            freshness_score=min(item.freshness_score for item in qualities),
            overall_score=min(item.overall_score for item in qualities),
            freshness_ms=max(item.freshness_ms for item in qualities),
            coverage_days=(
                min(value for value in coverages if value is not None)
                if any(value is not None for value in coverages)
                else None
            ),
            capital_reference_source="PORTFOLIO_SUM",
            capital_basis="PORTFOLIO_SUM_OF_MEMBERS",
            measurement_mode=mode,
            valid_trade_count=sum(item.valid_trade_count for item in qualities),
            rejected_trade_count=sum(item.rejected_trade_count for item in qualities),
            sources=[source for item in qualities for source in item.sources],
            warnings=warnings,
        )

    @staticmethod
    def _merge_reconciliation(bots: Sequence[BotResult]) -> LedgerReconciliation:
        entries = [bot.reconciliation for bot in bots]
        status = max(
            (entry.status for entry in entries),
            key=lambda value: _RECON_SEVERITY.index(value)
            if value in _RECON_SEVERITY
            else len(_RECON_SEVERITY),
        )
        reported = [entry.reported_pnl for entry in entries]
        ledger_pnl = float(sum(entry.ledger_pnl for entry in entries))
        reported_total = (
            float(sum(value for value in reported if value is not None))
            if all(value is not None for value in reported)
            else None
        )
        difference = (
            reported_total - ledger_pnl if reported_total is not None else None
        )
        warnings: List[str] = []
        for bot, entry in zip(bots, entries):
            warnings.extend(
                f"[{bot.identity.nick_name}] {line}" for line in entry.warnings
            )
        return LedgerReconciliation(
            status=status,
            reported_pnl=reported_total,
            reported_pnl_provenance="PORTFOLIO_SUM",
            ledger_pnl=ledger_pnl,
            difference=difference,
            difference_pct=(
                abs(difference) / abs(reported_total) * 100.0
                if difference is not None and reported_total
                else None
            ),
            ledger_truncated=any(entry.ledger_truncated for entry in entries),
            ledger_coverage_days=min(
                (
                    entry.ledger_coverage_days
                    for entry in entries
                    if entry.ledger_coverage_days is not None
                ),
                default=None,
            ),
            warnings=warnings,
        )

    # ------------------------------------------------------------------ #

    @classmethod
    def combine(
        cls,
        bots: Sequence[BotResult],
        *,
        timelines: Optional[Dict[str, PhaseTimeline]] = None,
        nick_name: Optional[str] = None,
        simulation_iterations: int = DEFAULT_SIMULATION_ITERATIONS,
        simulation_horizon: Optional[int] = None,
        seed: int = 42,
    ) -> BotResult:
        if len(bots) < 2:
            raise ValueError("A portfolio needs at least two bots to combine")
        codes = [bot.identity.unique_code for bot in bots]
        if len(set(codes)) != len(codes):
            raise ValueError("The same bot was supplied more than once")

        trades = cls._merge_trades(bots)
        if not trades:
            raise ValueError("No member has any closed trade to combine")

        state = cls._merge_state(bots)
        capital = cls._merge_capital(bots)
        mode = max(
            (bot.data_quality.measurement_mode for bot in bots),
            key=lambda value: _MODE_SEVERITY.get(value, 99),
        )

        # Exposure share across the whole book, so the dominant market -- the
        # one the market-alignment lens will judge against -- is the one the
        # portfolio actually has most of its money in.
        exposure = dict(state.exposure_by_symbol or {})
        if not exposure:
            for bot in bots:
                weight = bot.capital.capital_at_risk or 1.0
                for symbol, share in (bot.identity.symbol_exposure_share or {}).items():
                    exposure[base_symbol(symbol)] = exposure.get(
                        base_symbol(symbol), 0.0
                    ) + float(share) * weight
        if exposure:
            dominant = max(exposure, key=lambda key: exposure[key])
            total_exposure = sum(exposure.values()) or 1.0
            share_map = {
                symbol: value / total_exposure for symbol, value in exposure.items()
            }
        else:
            # No open book anywhere: fall back to whichever instrument the
            # merged ledger traded most, which is still a measured fact.
            counts: Dict[str, int] = {}
            for trade in trades:
                key = base_symbol(trade.symbol)
                counts[key] = counts.get(key, 0) + 1
            dominant = max(counts, key=lambda key: counts[key])
            total_count = sum(counts.values()) or 1
            share_map = {k: v / total_count for k, v in counts.items()}

        drawdown = DrawdownUnderwaterAnalyzer.analyze(trades, capital)
        performance = PerformanceMetricsCalculator.calculate(
            trades, capital, None, drawdown
        )
        deferred_loss = DeferredLossAnalyzer.analyze(
            trades,
            state.open_positions,
            state.unrealized_pnl,
            capital.capital_at_risk,
        )
        trade_statistics = TradeStatisticsCalculator.calculate(trades, mode)
        behavior = BehavioralPatternDetector.analyze(
            trades, state.open_positions_count, open_positions=state.open_positions
        )
        strategy = StrategyPhaseAnalyzer.analyze(
            trades,
            timelines or {},
            declared=None,
            fallback_profile="PORTFOLIO",
        )
        # Stationary bootstrap over the MERGED ledger: that sequence is the
        # portfolio's own trade history, and resampling it in blocks keeps the
        # short-run clustering the members produced together. It answers "what
        # could this book's next stretch look like". It is NOT the same
        # question as the correlation layer's joint simulation, which resamples
        # whole time buckets to price what the members' co-movement costs --
        # both are reported, and neither replaces the other.
        simulation = MonteCarloSimulationEngine.run_simulation(
            trades,
            capital.capital_at_risk,
            iterations=simulation_iterations,
            horizon_trades=simulation_horizon,
            seed=seed,
            capital_basis="PORTFOLIO_SUM_OF_MEMBERS",
            current_drawdown_pct=drawdown.current_dd_pct,
            trade_frequency_per_day=performance.trade_frequency_per_day,
        )
        stress = StressSimulator.run_stress(trades, capital.capital_at_risk)
        exit_rule = ExitRuleAnalyzer.analyze(trades)

        caveats = [
            f"Synthetic portfolio of {len(bots)} bots: every figure is the merged "
            "book, not any one member's own number",
            "Streaks, averaging-down and re-entry patterns are read across the "
            "merged ledger, so they describe what the combined account did -- two "
            "independent members adding to the same losing instrument counts here, "
            "as it does to the account",
        ]
        if not capital.capital_at_risk:
            caveats.append(
                "No portfolio capital could be summed, so every percentage-of-capital "
                "figure is absent rather than estimated"
            )

        fingerprint = hashlib.sha256(
            "|".join(
                sorted(
                    f"{bot.identity.unique_code}:{bot.identity.ledger_fingerprint or ''}"
                    for bot in bots
                )
            ).encode("utf-8")
        ).hexdigest()[:32]
        venues = {bot.identity.venue for bot in bots}

        return BotResult(
            identity=BotIdentity(
                bot_id=cls.portfolio_id(codes),
                unique_code=cls.portfolio_id(codes),
                nick_name=nick_name or f"Portfolio of {len(bots)} bots",
                symbol=dominant,
                asset_context=dominant,
                primary_traded_symbol=dominant,
                venue=next(iter(venues)) if len(venues) == 1 else "MIXED",
                declared_strategy=None,
                observed_symbols=sorted(share_map),
                symbol_exposure_share=share_map,
                identity_warnings=[
                    "Members: " + ", ".join(sorted(codes)),
                    f"Market-facing figures are judged against [{dominant}], the "
                    f"portfolio's largest exposure "
                    f"({share_map.get(dominant, 0.0):.0%} of the book); the rest of "
                    "the book is not covered by the market lenses",
                ],
                ledger_fingerprint=fingerprint,
            ),
            timestamp=max(bot.timestamp for bot in bots),
            as_of_ms=min(bot.as_of_ms for bot in bots),
            current_state=state,
            performance=performance,
            deferred_loss=deferred_loss,
            trade_statistics=trade_statistics,
            trade_ledger_summary=trades,
            behavioral_observations=behavior,
            strategy_observations=strategy,
            drawdown_analysis=drawdown,
            simulation_results=simulation,
            stress_results=stress,
            exit_rule=exit_rule,
            reconciliation=cls._merge_reconciliation(bots),
            capital=capital,
            data_quality=cls._merge_quality(bots, mode, caveats),
        )

"""LOGIC 3, portfolio scope: what N bots are together that none of them is alone.

BOUNDARY, AND WHY IT IS DRAWN HERE. The ten lenses keep their monopoly on
judging a single bot; nothing in this module re-scores a member, overrides a
verdict, or reaches into a `DimensionEvaluation`. It consumes the finished
per-bot assessments and adds only the three things that are invisible from
inside one bot: whether the members move together, whether the book is
concentrated behind their apparent spread, and what the combination's loss
tail looks like when both of those are taken into account.

That is also why `portfolio_risk_score` is allowed to come out ABOVE every
member's own score. It is not a re-scoring of the members and it is not an
average that went wrong: three bots at 40 that are one bet carry more risk
together than any of them carries alone, and a scale that could not say so
would be unable to express the finding this whole feature exists to surface.
`score_adjustments` itemises every point of the difference, so the base and
the portfolio effect are never conflated.
"""

from __future__ import annotations

import numpy as np

import json
import time
import uuid
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from Agent.backend.bot.mcp.analytics.strategy.exit_rule import ExitRuleAnalyzer
from Agent.backend.bot.mcp.analytics.strategy.profile import base_symbol
from Agent.backend.bot.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
from Agent.backend.report.qc.portfolio.book_metrics import compute_book_metrics
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.public_series import PublicPnlProfile
from Agent.backend.report.qc.portfolio.schemas import (
    CorrelationMatrix,
    ExposureConcentration,
    SymbolExposure,
    PairStyle,
    PortfolioMember,
    PortfolioRiskAssessment,
    PortfolioVerdict,
    StyleVerdict,
)
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger
from Agent.backend.report.qc.schemas.risk_assessment import BotRiskAssessment

# (label_a, label_b, pearson, exit-rule distance) for a pair whose results look
# independent while its trading does not.
PairCorrelationConflict = Tuple[str, str, float, float]


@dataclass(frozen=True)
class PortfolioCandidate:
    """One bot offered to the portfolio layer, with its own finished assessment.

    `assessment` is optional because a member can legitimately be observable
    without being scoreable (an opaque bot OKX answers 60004 for). Such a
    member still contributes exposure and, if it has a ledger, co-movement.
    """

    bot: BotResult
    assessment: Optional[BotRiskAssessment] = None


class PortfolioQCService:
    METHODOLOGY_VERSION = "portfolio_qc.v1"

    MIN_MEMBERS = 2
    # Style bands, set from the measured spread of exit-rule distances across
    # the bots in this dataset (66 pairs: min 0.06, p25 0.16, median 0.27).
    # They are descriptive cut points on an observed distribution, not a claim
    # that 0.15 is a universal constant.
    SAME_PLAYBOOK_DISTANCE = 0.15
    PARTIAL_OVERLAP_DISTANCE = 0.30
    # A pair whose results look independent while its trading does not. The
    # PnL bar is generous on purpose: "not visibly correlated" is exactly the
    # reading this trap hides behind.
    CONFLICT_PEARSON_MAX = 0.2
    # Verdict bands on the AVERAGE pairwise Pearson, with a separate trip on
    # the single worst pair: a portfolio whose average is a comfortable 0.3
    # because one pair sits at 0.9 and the rest near zero is still holding one
    # doubled-up position, and an average alone cannot see it.
    MODERATE_AVG_PEARSON = 0.3
    HIGH_AVG_PEARSON = 0.6
    HIGH_MAX_PEARSON = 0.8
    # Below this SHARE of pairs actually reaching significance, the verdict
    # is not entitled to an opinion at all -- see `_verdict`'s own docstring
    # for why "at least one significant pair" was not a strong enough bar
    # (project owner, 2026-09-23: a 2-bot portfolio at r=0.65/p=0.12 is one
    # pair, and that one pair being the only one measured does not make it
    # trustworthy).
    MIN_SIGNIFICANT_PAIR_SHARE = 0.5

    # Below this measured-coverage percentage, a "good news" verdict
    # (DIVERSIFIED / MODERATE_CO_MOVEMENT) is not entitled to stand: more
    # than a quarter of the submitted book is a bot nobody can see into, so
    # what looks measured and comfortable might not be the book the reader
    # actually holds. See `_measurement_coverage` for how the percentage
    # itself is computed, and the comment at its one call site in
    # `assess_portfolio` for why HIGH_CORRELATION_CLUSTER is exempt.
    MIN_MEASUREMENT_COVERAGE_PCT = 75.0

    # ------------------------------------------------------------------ #
    # Member assembly
    # ------------------------------------------------------------------ #

    @staticmethod
    def _labels(candidates: Sequence[PortfolioCandidate]) -> List[str]:
        """Readable, and unique even when two bots share a nickname.

        Nicknames on OKX are not unique and are frequently blank. A label
        collision would make two different bots indistinguishable in the
        matrix, the heatmap and every warning string, so any repeat falls back
        to carrying the code.
        """
        names = [
            (candidate.bot.identity.nick_name or "").strip()
            or candidate.bot.identity.unique_code
            for candidate in candidates
        ]
        seen: Dict[str, int] = {}
        for name in names:
            seen[name] = seen.get(name, 0) + 1
        labels: List[str] = []
        for index, name in enumerate(names):
            code = candidates[index].bot.identity.unique_code
            labels.append(name if seen[name] == 1 else f"{name} ({code[:6]})")
        return labels

    @classmethod
    def _members(
        cls,
        candidates: Sequence[PortfolioCandidate],
        labels: Sequence[str],
    ) -> List[PortfolioMember]:
        capitals = [
            candidate.bot.capital.capital_at_risk for candidate in candidates
        ]
        # All-or-nothing on purpose: one missing capital makes every weight in
        # the set wrong, not just its own.
        total = (
            sum(value for value in capitals if value)
            if all(value and value > 0 for value in capitals)
            else None
        )

        members: List[PortfolioMember] = []
        for index, candidate in enumerate(candidates):
            bot = candidate.bot
            assessment = candidate.assessment
            closes = [
                int(trade.close_time)
                for trade in bot.trade_ledger_summary
                if trade.close_time
            ]
            capital = capitals[index]
            members.append(
                PortfolioMember(
                    bot_id=bot.identity.bot_id,
                    unique_code=bot.identity.unique_code,
                    nick_name=bot.identity.nick_name,
                    symbol=bot.identity.symbol,
                    venue=bot.identity.venue,
                    label=labels[index],
                    risk_score=assessment.risk_score if assessment else None,
                    quality_score=assessment.quality_score if assessment else None,
                    risk_tier=assessment.risk_tier.value if assessment else None,
                    verdict=assessment.verdict if assessment else None,
                    closed_trade_count=len(bot.trade_ledger_summary),
                    realized_pnl=bot.performance.total_pnl,
                    capital_at_risk=capital,
                    capital_weight=(
                        round(capital / total, 6)
                        if total and capital and total > 0
                        else None
                    ),
                    current_notional=bot.current_state.current_notional,
                    position_side=bot.current_state.current_position_side.value,
                    observed_symbols=list(bot.identity.observed_symbols),
                    symbol_exposure_share=dict(bot.identity.symbol_exposure_share),
                    first_close_ms=min(closes) if closes else None,
                    last_close_ms=max(closes) if closes else None,
                    ledger_capital=capital if capital and capital > 0 else None,
                    open_positions=len(bot.current_state.open_positions),
                    unrealized_pnl=cls._unrealized(bot),
                )
            )
        return members

    @staticmethod
    def _unrealized(bot: BotResult) -> Optional[float]:
        """Marked PnL of the open book: the state's own figure, else the sum
        over positions -- but only when every open position carries one."""
        state_value = getattr(bot.current_state, "unrealized_pnl", None)
        if state_value is not None:
            return float(state_value)
        positions = list(bot.current_state.open_positions)
        if not positions:
            return 0.0
        values = [p.unrealized_pnl for p in positions]
        if any(value is None for value in values):
            return None
        return float(sum(values))

    # ------------------------------------------------------------------ #
    # Concentration
    # ------------------------------------------------------------------ #

    @staticmethod
    def _concentration(
        candidates: Sequence[PortfolioCandidate],
    ) -> ExposureConcentration:
        """Where the open book actually sits, across every member at once.

        This deliberately reads the OPEN positions rather than the ledger:
        concentration is a statement about the risk being carried right now,
        and a bot that used to be heavy in one symbol and has since flattened
        is not concentrating anything today.
        """
        by_symbol: Dict[str, float] = {}
        gross = 0.0
        net = 0.0
        measured = 0
        warnings: List[str] = []

        for candidate in candidates:
            state = candidate.bot.current_state
            notional = state.current_notional
            if notional is None or notional <= 0.0:
                if state.current_position_side not in (
                    PositionSide.FLAT,
                    PositionSide.UNKNOWN,
                ):
                    warnings.append(
                        f"[{candidate.bot.identity.nick_name}] holds an open position "
                        "with no notional value, so it is missing from the "
                        "concentration figures"
                    )
                continue
            measured += 1
            gross += notional
            sign = -1.0 if state.current_position_side == PositionSide.SHORT else 1.0
            net += sign * notional
            exposure = state.exposure_by_symbol or {
                candidate.bot.identity.symbol: notional
            }
            for symbol, value in exposure.items():
                by_symbol[symbol] = by_symbol.get(symbol, 0.0) + float(value)

        if gross <= 0.0:
            return ExposureConcentration(
                measured_members=measured,
                warnings=warnings
                or ["No member carries open exposure, so there is nothing to concentrate"],
            )

        total_symbol = sum(by_symbol.values()) or gross
        shares = {
            symbol: value / total_symbol for symbol, value in by_symbol.items()
        }
        largest_symbol = max(shares, key=lambda key: shares[key])
        hhi = sum(share**2 for share in shares.values())
        symbol_count = len(shares)
        # Raw HHI floors at 1/k, which moves with how many symbols are held, so
        # two portfolios of different breadth could not otherwise be compared.
        normalised = (
            (hhi - 1.0 / symbol_count) / (1.0 - 1.0 / symbol_count)
            if symbol_count > 1
            else 1.0
        )
        return ExposureConcentration(
            by_symbol={
                symbol: round(value, 6) for symbol, value in sorted(
                    shares.items(), key=lambda item: -item[1]
                )
            },
            largest_symbol=largest_symbol,
            largest_symbol_share_pct=round(shares[largest_symbol] * 100.0, 2),
            normalised_hhi=round(max(0.0, min(1.0, normalised)), 4),
            gross_notional=round(gross, 2),
            net_notional=round(net, 2),
            directional_alignment=round(min(1.0, abs(net) / gross), 4),
            measured_members=measured,
            warnings=warnings,
        )

    @staticmethod
    def _symbol_breakdown(
        candidates: Sequence[PortfolioCandidate],
        labels: Sequence[str],
        concentration: ExposureConcentration,
    ) -> List[SymbolExposure]:
        """One row per instrument, carrying what the book DID and what it HOLDS.

        Built here rather than in the renderer because it needs the merged
        ledger, which only this layer has. The market side of the row -- trend,
        volatility, price -- is attached by the presentation layer from the
        coverage the pipeline resolved, so neither side has to reach into the
        other's data.
        """
        rows: Dict[str, Dict[str, Any]] = {}
        for index, candidate in enumerate(candidates):
            label = labels[index]
            for trade in candidate.bot.trade_ledger_summary:
                symbol = base_symbol(trade.symbol)
                if not symbol:
                    continue
                row = rows.setdefault(
                    symbol,
                    {"closed": 0, "pnl": 0.0, "wins": 0, "members": set()},
                )
                row["closed"] += 1
                row["pnl"] += float(trade.realized_pnl)
                if trade.realized_pnl > 0:
                    row["wins"] += 1
                row["members"].add(label)

        open_notional: Dict[str, float] = {}
        open_count: Dict[str, int] = {}
        for candidate in candidates:
            state = candidate.bot.current_state
            # Same fallback `_concentration` uses: a bot that reports a
            # notional but no per-symbol split still has that money in its
            # primary instrument. Without it this column read 0 while the
            # exposure column next to it read 55%, which is not a gap in the
            # data -- it is two columns disagreeing about the same fact.
            exposure = state.exposure_by_symbol or (
                {candidate.bot.identity.symbol: state.current_notional}
                if state.current_notional
                else {}
            )
            for symbol, value in exposure.items():
                key = base_symbol(symbol)
                if not key or value is None:
                    continue
                open_notional[key] = open_notional.get(key, 0.0) + float(value)
            for position in state.open_positions:
                key = base_symbol(position.symbol or position.instrument or "")
                if key:
                    open_count[key] = open_count.get(key, 0) + 1

        shares = concentration.by_symbol or {}
        out: List[SymbolExposure] = []
        for symbol in set(rows) | set(open_notional):
            row = rows.get(symbol, {"closed": 0, "pnl": 0.0, "wins": 0, "members": set()})
            closed = int(row["closed"])
            out.append(
                SymbolExposure(
                    symbol=symbol,
                    closed_trades=closed,
                    realized_pnl=round(float(row["pnl"]), 2),
                    win_rate=(
                        round(row["wins"] / closed * 100.0, 2) if closed else None
                    ),
                    members=sorted(row["members"]),
                    open_notional=open_notional.get(symbol),
                    exposure_share=shares.get(symbol),
                    open_positions=open_count.get(symbol, 0),
                )
            )
        # Biggest exposure first, then by how much was traded there: a symbol
        # the book no longer holds but made or lost money in still belongs on
        # the list, just below the ones carrying risk right now.
        out.sort(
            key=lambda item: (
                -(item.exposure_share or 0.0),
                -(item.open_notional or 0.0),
                -item.closed_trades,
            )
        )
        return out

    # ------------------------------------------------------------------ #
    # Verdict
    # ------------------------------------------------------------------ #

    @classmethod
    def _verdict(
        cls, correlation: CorrelationMatrix
    ) -> tuple[PortfolioVerdict, str]:
        if not correlation.is_valid or correlation.average_pearson is None:
            return (
                PortfolioVerdict.INSUFFICIENT_EVIDENCE,
                "Co-movement between these bots could not be measured: "
                + (
                    correlation.warnings[0]
                    if correlation.warnings
                    else "no shared trading window"
                ),
            )

        # DIVERSIFIED and HIGH_CORRELATION_CLUSTER are both claims of
        # confident knowledge -- "we can tell these bots move together" or
        # "we can tell they don't". `correlation.average_pearson`/
        # `max_pearson` are the mean and max over EVERY pair with a numeric
        # coefficient, significant or not (see `CorrelationAnalyzer.analyze`:
        # `measured = [pair.pearson for pair in pairs if pair.pearson is not
        # None]`), so a portfolio near MIN_BUCKETS can produce r=0.65 that is
        # pure sampling noise (p=0.12, `is_significant=False`) and still push
        # `average` over `HIGH_AVG_PEARSON` -- a verdict reading more
        # confident than the evidence licenses. `CorrelationAnalyzer` itself
        # already flags exactly this per pair (`_note`: "not distinguishable
        # from zero at this sample size -- treat as unmeasured"); the verdict
        # has to honour that flag rather than average right past it.
        #
        # So the verdict is decided on the SIGNIFICANT subset only. The raw,
        # unfiltered `average_pearson`/`max_pearson` are left untouched on
        # the model -- the stat cards and the pair table report what was
        # actually measured, significant or not, which is a different and
        # legitimate thing to show than what the verdict is confident enough
        # to CONCLUDE from.
        significant_pairs = [
            item
            for item in correlation.pairs
            if item.is_significant and item.pearson is not None
        ]
        total_pairs = len(correlation.pairs)
        significant_share = len(significant_pairs) / total_pairs if total_pairs else 0.0
        # Not just "zero significant pairs" -- a MAJORITY of pairs has to
        # clear the bar. One lucky pair out of four is not a portfolio-wide
        # finding; it is one pair-wide finding wearing a portfolio-wide
        # verdict. `MIN_SIGNIFICANT_PAIR_SHARE` is the floor below which
        # the verdict declines to have an opinion rather than speak for
        # pairs it could not actually measure.
        if not significant_pairs or significant_share < cls.MIN_SIGNIFICANT_PAIR_SHARE:
            return (
                PortfolioVerdict.INSUFFICIENT_EVIDENCE,
                f"Only {len(significant_pairs)} of {total_pairs} pair(s) are "
                "distinguishable from zero at this sample size -- fewer than "
                f"{cls.MIN_SIGNIFICANT_PAIR_SHARE:.0%} of the pairs measured, so "
                "there is not enough evidence to call these bots diversified or "
                "correlated either way.",
            )
        significant = [item.pearson for item in significant_pairs]
        average = float(np.mean(significant))
        strongest_pair = max(significant_pairs, key=lambda item: item.pearson)
        strongest = strongest_pair.pearson
        pair = [strongest_pair.label_a, strongest_pair.label_b]
        if len(significant) < len(correlation.pairs):
            excluded = len(correlation.pairs) - len(significant)
            note_suffix = (
                f" ({excluded} of {len(correlation.pairs)} pair(s) excluded as not "
                "statistically significant)"
            )
        else:
            note_suffix = ""
        if average >= cls.HIGH_AVG_PEARSON:
            return (
                PortfolioVerdict.HIGH_CORRELATION_CLUSTER,
                f"The bots move as one: average pairwise correlation {average:+.2f} "
                f"across {len(significant)} significant pair(s). Splitting capital "
                f"between them spreads the position, not the risk.{note_suffix}",
            )
        if strongest is not None and strongest >= cls.HIGH_MAX_PEARSON:
            names = " and ".join(f"[{name}]" for name in pair) if pair else "two members"
            return (
                PortfolioVerdict.HIGH_CORRELATION_CLUSTER,
                f"Average correlation is a moderate {average:+.2f}, but {names} sit at "
                f"{strongest:+.2f} -- that pair is effectively one position held "
                f"twice.{note_suffix}",
            )
        if average >= cls.MODERATE_AVG_PEARSON:
            return (
                PortfolioVerdict.MODERATE_CO_MOVEMENT,
                f"Partial diversification: average pairwise correlation {average:+.2f} "
                f"across {len(significant)} significant pair(s). The bots overlap in "
                f"bad periods but do not track each other fully.{note_suffix}",
            )
        return (
            PortfolioVerdict.DIVERSIFIED,
            f"Genuinely spread: average pairwise correlation {average:+.2f} across "
            f"{len(significant)} significant pair(s), so a bad period for one member "
            f"is not automatically a bad period for the others.{note_suffix}",
        )

    # ------------------------------------------------------------------ #
    # Style: how alike they TRADE, which the results can contradict
    # ------------------------------------------------------------------ #

    @classmethod
    def _attach_style(
        cls,
        correlation: CorrelationMatrix,
        by_code: Dict[str, BotResult],
    ) -> tuple[StyleVerdict, str, bool]:
        """Fill `pairs[].style` and decide the playbook verdict.

        Kept apart from the correlation verdict on purpose. A pair can be
        uncorrelated in PnL and identical in behaviour, and collapsing the two
        into one label would delete exactly the case worth reporting.
        """
        distances: List[float] = []
        conflicts: List[PairCorrelationConflict] = []

        for pair in correlation.pairs:
            left = by_code.get(pair.code_a)
            right = by_code.get(pair.code_b)
            if left is None or right is None:
                continue
            if left.exit_rule is None or right.exit_rule is None:
                continue
            compared = ExitRuleAnalyzer.compare(left.exit_rule, right.exit_rule)
            if compared is None:
                continue
            distance = float(compared["distance"])
            distances.append(distance)
            conflict = bool(
                pair.pearson is not None
                and pair.pearson <= cls.CONFLICT_PEARSON_MAX
                and distance <= cls.SAME_PLAYBOOK_DISTANCE
            )
            if conflict:
                conflicts.append((pair.label_a, pair.label_b, pair.pearson, distance))
            if conflict:
                note = (
                    f"Results look independent (r = {pair.pearson:+.2f}) but the exit "
                    f"discipline is nearly identical (distance {distance:.2f}"
                    + (
                        f", both {left.exit_rule.exit_style.value}"
                        if compared["same_exit_style"]
                        else ""
                    )
                    + "). The offset is a property of this window, not of the "
                    "strategies -- do not bank on it."
                )
            elif distance <= cls.SAME_PLAYBOOK_DISTANCE:
                note = (
                    f"Same playbook (distance {distance:.2f}); their results move "
                    "together too, which is at least consistent"
                )
            elif distance >= cls.PARTIAL_OVERLAP_DISTANCE:
                note = (
                    f"Genuinely different trading (distance {distance:.2f}), driven by "
                    f"{'holding period' if compared['driver'] == 'HOLDING_PERIOD' else compared['top_rule_component']}"
                )
            else:
                note = (
                    f"Partly overlapping trading (distance {distance:.2f}); closest on "
                    f"{compared['top_rule_component']}"
                )
            pair.style = PairStyle(
                exit_distance=distance,
                exit_similarity=float(compared["similarity"]),
                rule_distance=compared["rule_distance"],
                hold_distance=compared["hold_distance"],
                driver=str(compared["driver"]),
                top_rule_component=str(compared["top_rule_component"]),
                top_rule_gap=compared["top_rule_gap"],
                exit_style_a=left.exit_rule.exit_style.value,
                exit_style_b=right.exit_rule.exit_style.value,
                same_exit_style=bool(compared["same_exit_style"]),
                shared_patterns=list(compared["shared_patterns"]),
                style_vs_pnl_conflict=conflict,
                note=note,
            )

        if not distances:
            return (
                StyleVerdict.INSUFFICIENT_EVIDENCE,
                "No pair has two ledgers long enough to fingerprint their exit "
                "discipline",
                False,
            )
        if conflicts:
            worst = min(conflicts, key=lambda item: item[3])
            return (
                StyleVerdict.SAME_PLAYBOOK,
                f"[{worst[0]}] and [{worst[1]}] trade almost identically (exit-rule "
                f"distance {worst[3]:.2f}) while their PnL looks unrelated "
                f"(r = {worst[2]:+.2f}). Their offset is timing, not design.",
                True,
            )
        average = sum(distances) / len(distances)
        if average <= cls.SAME_PLAYBOOK_DISTANCE:
            return (
                StyleVerdict.SAME_PLAYBOOK,
                f"One playbook run several times: average exit-rule distance "
                f"{average:.2f}",
                False,
            )
        if average <= cls.PARTIAL_OVERLAP_DISTANCE:
            return (
                StyleVerdict.PARTIAL_OVERLAP,
                f"Partly shared behaviour: average exit-rule distance {average:.2f}",
                False,
            )
        return (
            StyleVerdict.DISTINCT_PLAYBOOKS,
            f"The members genuinely trade differently: average exit-rule distance "
            f"{average:.2f}",
            False,
        )

    @staticmethod
    def _score_coverage(
        members: Sequence[PortfolioMember], coverage_pct: Optional[float]
    ) -> Optional[float]:
        """Share of the submitted book the merged-book figures describe.

        `coverage_pct` already discounts members that were not measured at
        all; this further removes the ledger-hidden ones, which reach the
        matrix but not the order-book-based score. By capital when every
        member has one, else by headcount -- the same all-or-nothing rule as
        the weights.
        """
        if coverage_pct is None or not members:
            return None
        hidden = [member for member in members if member.ledger_hidden]
        if not hidden:
            return coverage_pct
        capitals = [member.capital_at_risk for member in members]
        if all(value and value > 0 for value in capitals):
            total = sum(capitals)
            ledger = sum(
                member.capital_at_risk for member in members if not member.ledger_hidden
            )
            share = ledger / total if total else 0.0
        else:
            share = (len(members) - len(hidden)) / len(members)
        return round(coverage_pct * share, 2)

    @staticmethod
    def _ledger_hidden_member(profile: PublicPnlProfile, label: str) -> PortfolioMember:
        """A member OKX withholds the order book of, described from what it
        still publishes: its daily PnL (in the matrix), its capital
        (`investAmt`) and what it trades (currency preference)."""
        symbol = (
            max(profile.exposure, key=lambda key: profile.exposure[key])
            if profile.exposure
            else "UNKNOWN"
        )
        realized = sum(pnl for _, pnl in profile.daily)
        return PortfolioMember(
            bot_id=f"okx:{profile.unique_code}",
            unique_code=profile.unique_code,
            nick_name=profile.nick_name or profile.unique_code,
            symbol=symbol,
            label=label,
            closed_trade_count=0,
            # Mark-to-market PnL over the public window -- the only PnL
            # figure there is for a bot with no ledger.
            realized_pnl=round(realized, 2),
            capital_at_risk=profile.capital,
            observed_symbols=sorted(profile.exposure),
            symbol_exposure_share=dict(profile.exposure),
            first_close_ms=profile.daily[0][0] if profile.daily else None,
            last_close_ms=profile.last_day_ms,
            ledger_hidden=True,
            capital_source="OKX_INVEST_AMT",
            pnl_basis="PUBLIC_MARK_TO_MARKET",
            public_window_days=profile.days,
        )

    @staticmethod
    def _reweight(members: Sequence[PortfolioMember]) -> None:
        """Capital weights over the full member list, all-or-nothing -- the
        same rule `_members` applies, re-run once ledger-hidden members join."""
        capitals = [member.capital_at_risk for member in members]
        total = (
            sum(value for value in capitals if value)
            if all(value and value > 0 for value in capitals)
            else None
        )
        for member in members:
            member.capital_weight = (
                round(member.capital_at_risk / total, 6)
                if total and member.capital_at_risk
                else None
            )

    @classmethod
    def _measurement_coverage(
        cls,
        members: Sequence[PortfolioMember],
        concealed_codes: Sequence[str],
        concealed_capital_usdt: Dict[str, float],
    ) -> Optional[float]:
        """% of the SUBMITTED book covered by measured members, 0-100.

        Capital-weighted when every concealed code's AUM happens to be
        known (see `PortfolioMemberFailure.approx_capital_usdt` -- OKX still
        publishes it for most LIMITED bots even though the ledger is
        blocked). Falls back to plain headcount the moment even ONE
        concealed member's capital is unknown: a partial capital picture
        would silently misweight the ratio in whichever direction the known
        subset happens to skew, which is worse than the honest, cruder
        headcount fallback.
        """
        if not concealed_codes:
            return 100.0 if members else None
        measured_capital = [
            member.capital_at_risk for member in members if member.capital_at_risk
        ]
        known_concealed_capital = [
            concealed_capital_usdt[code]
            for code in concealed_codes
            if code in concealed_capital_usdt
        ]
        if len(known_concealed_capital) == len(concealed_codes) and measured_capital:
            total = sum(measured_capital) + sum(known_concealed_capital)
            return 100.0 * sum(measured_capital) / total if total else None
        total_count = len(members) + len(concealed_codes)
        return 100.0 * len(members) / total_count if total_count else None

    # ------------------------------------------------------------------ #
    # Entry point
    # ------------------------------------------------------------------ #

    @classmethod
    def assess_portfolio(
        cls,
        candidates: Sequence[PortfolioCandidate],
        *,
        combined: Optional[BotRiskAssessment] = None,
        iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
        seed: Optional[int] = 42,
        as_of_ms: Optional[int] = None,
        concealed_members: Sequence[str] = (),
        concealed_capital_usdt: Optional[Dict[str, float]] = None,
        error_members: Sequence[str] = (),
        public_profiles: Optional[Dict[str, PublicPnlProfile]] = None,
    ) -> PortfolioRiskAssessment:
        """Build the diversification section for a set of bots.

        `combined` is the ONE assessment the portfolio report is built from
        (the ten lenses over the merged ledger). It is mirrored here for
        listings; nothing in this method recomputes or second-guesses it.

        `concealed_members` names every bot that was SUBMITTED but hides its
        order book (see `PortfolioMemberFailure.kind`), so it never reaches
        `candidates` at all -- `combine()` never sees its trades, and every
        figure below (`correlation`, `joint_simulation`, `concentration`) is
        computed over the visible members only, exactly as if that bot had
        never been asked for. That is precisely the failure mode its own
        field docstring warns about: the survivors are all disclosers, so
        their measured correlation reads lower and their diversification
        reads better than the book actually held. `_verdict` cannot see this
        on its own -- it only ever receives the correlation matrix of the
        bots that loaded -- so the guard has to live here, the one place that
        knows both what was measured and who was left out of the measuring.

        `concealed_capital_usdt` is a best-effort AUM per concealed code
        (see `PortfolioMemberFailure.approx_capital_usdt`), used ONLY to
        weight `measurement_coverage_pct` by capital instead of headcount
        when every concealed member's capital happens to be known.

        `error_members` names every bot that was SUBMITTED but simply could
        not be read (OKX unreachable, a bad file -- `kind="error"`, no
        finding about the bot). Not folded into `concealed_members`: it
        exists only so `submitted_member_count` below counts every code that
        was actually asked for, not just the concealed ones. It does NOT
        feed `measurement_coverage_pct` or the verdict downgrade -- a
        transient read failure says nothing about how trustworthy the
        MEASURED members' diversification reading is, which is the one
        question those two exist to answer.

        `public_profiles` is OKX's public daily PnL (and currency preference,
        capital) per code, for every member AND every concealed code. When
        it covers every ledger member the whole matrix is measured on that
        mark-to-market basis, and a concealed code with its own series joins
        the matrix as a `ledger_hidden` member instead of being dropped --
        OKX withholds that bot's order book, not its daily PnL.
        """
        if len(candidates) < cls.MIN_MEMBERS:
            raise ValueError(
                f"A portfolio needs at least {cls.MIN_MEMBERS} bots; "
                f"got {len(candidates)}"
            )
        codes = [candidate.bot.identity.unique_code for candidate in candidates]
        if len(set(codes)) != len(codes):
            raise ValueError("The same bot was supplied more than once")

        labels = cls._labels(candidates)
        members = cls._members(candidates, labels)
        bots = [candidate.bot for candidate in candidates]
        by_code = {bot.identity.unique_code: bot for bot in bots}
        exposure_by_code = {
            candidate.bot.identity.unique_code: dict(
                candidate.bot.identity.symbol_exposure_share
            )
            for candidate in candidates
        }

        # ONE ruler for the whole matrix (see `AlignmentDiagnostics.
        # pnl_basis`). Mark-to-market daily PnL when OKX's public series is in
        # hand for EVERY ledger member -- which is also the only basis that
        # can include a member whose order book OKX withholds, because that
        # series survives 60004. If even one ledger member lacks it, everyone
        # stays on the realized-ledger basis rather than mixing the two in
        # one matrix: a pair measured on two different rulers would read as
        # a finding about the bots when it is a finding about the rulers
        # (validated 2026-09-24: median |r_ledger - r_public| 0.16 on 42
        # pairs over the same window).
        profiles = dict(public_profiles or {})
        min_days = TimeSeriesMerger.MIN_BUCKETS
        mark_to_market = bool(candidates) and all(
            profiles.get(code) is not None and profiles[code].days >= min_days
            for code in codes
        )
        recovered: List[PublicPnlProfile] = []
        if mark_to_market:
            for code in concealed_members:
                profile = profiles.get(code)
                if profile is not None and profile.days >= min_days:
                    recovered.append(profile)
            taken = set(labels)
            for profile in recovered:
                label = profile.nick_name or profile.unique_code
                if label in taken:
                    label = f"{label} ({profile.unique_code[:6]})"
                taken.add(label)
                members.append(cls._ledger_hidden_member(profile, label))
                exposure_by_code[profile.unique_code] = dict(profile.exposure)
            # One ruler for CAPITAL too. A ledger member's capital comes from
            # its equity-curve model; a hidden one's can only be OKX's public
            # `investAmt`. Measured on the three ledger members of a live
            # portfolio (2026-09-24), model/investAmt ran 0.75x to 5.27x -- mixed,
            # the hidden bot's weight read 75% on numbers not on one scale.
            # `investAmt` is also what OKX's own daily `pnlRatio` divides by
            # (191,805 / 0.068 ~= 2.82M = investAmt), so it is the capital the
            # daily PnL series is denominated in. All-or-nothing, as always.
            public_capital = {
                member.unique_code: profiles[member.unique_code].capital
                for member in members
            }
            if all(value and value > 0 for value in public_capital.values()):
                for member in members:
                    member.capital_at_risk = public_capital[member.unique_code]
                    member.capital_source = "OKX_INVEST_AMT"
            cls._reweight(members)
            series = TimeSeriesMerger.merge_daily(
                [
                    (member.label, member.unique_code, profiles[member.unique_code].daily)
                    for member in members
                ]
            )
        else:
            series = TimeSeriesMerger.merge(bots, labels)
        recovered_codes = {profile.unique_code for profile in recovered}
        # Concealed members the public series could NOT bring back: these are
        # the ones genuinely absent from every figure below, and the only ones
        # the coverage guard and the "absent" limitation are about.
        still_concealed = [
            code for code in concealed_members if code not in recovered_codes
        ]
        member_codes = [member.unique_code for member in members]
        correlation = CorrelationAnalyzer.analyze(series, exposure_by_code)

        included = set(series.labels)
        for member in members:
            if member.label not in included:
                member.excluded_reason = series.diagnostics.excluded.get(
                    member.label,
                    "no overlap with the other members' trading window",
                )

        joint = None
        if series.is_valid:
            joint = JointMonteCarloEngine.run(
                series,
                [
                    next(
                        member.capital_at_risk
                        for member in members
                        if member.label == label
                    )
                    for label in series.labels
                ],
                iterations=iterations,
                seed=seed,
            )

        concentration = cls._concentration(candidates)
        style_verdict, style_reason, has_conflict = cls._attach_style(
            correlation, by_code
        )
        verdict, reason = cls._verdict(correlation)
        coverage_pct = cls._measurement_coverage(
            members, still_concealed, concealed_capital_usdt or {}
        )
        # A verdict that reads as GOOD news (genuinely spread, or only
        # partial overlap) cannot be trusted once enough of the submitted
        # book is invisible to every number above -- the concealed capital
        # might be the one thing that would have moved it. Gated on
        # `MIN_MEASUREMENT_COVERAGE_PCT`, not on "any concealment at all":
        # one small concealed bot in a twenty-member book barely dents the
        # measurement and forcing INSUFFICIENT_EVIDENCE over it would make
        # the verdict useless in exactly the cases where it is most needed.
        # `coverage_pct is None` (no members at all measured) is treated as
        # BELOW the threshold -- there being no coverage number to check is
        # not a reason to trust the verdict more.
        #
        # A verdict that already reads as a WARNING (HIGH_CORRELATION_
        # CLUSTER) is exempt from the downgrade regardless of coverage:
        # adding an unmeasured bot cannot make a portfolio that already
        # looks correlated look MORE dangerous than stated, and silencing a
        # real warning because part of the book is unmeasured would trade a
        # true positive for a false negative -- the one direction this
        # feature must never move in. The warning text already states that
        # the figure describes only the measured members.
        if still_concealed and verdict in (
            PortfolioVerdict.DIVERSIFIED,
            PortfolioVerdict.MODERATE_CO_MOVEMENT,
        ) and (coverage_pct is None or coverage_pct < cls.MIN_MEASUREMENT_COVERAGE_PCT):
            names = ", ".join(sorted(still_concealed))
            coverage_text = (
                f"{coverage_pct:.0f}%" if coverage_pct is not None else "an unknown share"
            )
            reason = (
                f"Measured correlation says {reason[0].lower()}{reason[1:]} -- but "
                f"only {coverage_text} of the submitted book was actually measured: "
                f"{len(still_concealed)} bot(s) hide their order book "
                f"({names}) and are absent from every figure above, so this cannot "
                "be called diversification with confidence."
            )
            verdict = PortfolioVerdict.INSUFFICIENT_EVIDENCE

        # The members' own data-quality notes, in full, kept HERE rather than
        # merged into the combined bot. The combined bot carries a count per
        # member (see `PortfolioAggregator._merge_quality`) because whatever
        # sits there is rendered as page body copy; the full text belongs
        # somewhere a reader opens deliberately, which is the chip in the
        # diversification section.
        limitations: List[str] = []
        for candidate in candidates:
            for line in candidate.bot.data_quality.warnings:
                limitations.append(f"[{candidate.bot.identity.nick_name}] {line}")
        unscored = [member for member in members if member.risk_score is None]
        if unscored:
            limitations.append(
                f"{len(unscored)} of {len(members)} members carry no individual risk "
                "score of their own; they are still inside every combined figure"
            )
        if still_concealed:
            coverage_note = (
                f"{coverage_pct:.0f}% of the book" if coverage_pct is not None
                else "an unknown share of the book"
            )
            limitations.append(
                f"{len(still_concealed)} submitted bot(s) hide their order book "
                f"({', '.join(sorted(still_concealed))}) and are absent from "
                "correlation, joint simulation and concentration alike -- only "
                f"{coverage_note} is actually measured below"
            )
        if recovered:
            limitations.append(
                f"{len(recovered)} submitted bot(s) hide their order book on OKX "
                f"({', '.join(sorted(recovered_codes))}); they are measured from "
                "OKX's public daily PnL in the correlation matrix and the joint "
                "simulation, but have no exit-rule fingerprint (d), no open "
                "positions for concentration, and no trades in the merged "
                "ten-lens score"
            )

        evidence: List[str] = []
        if correlation.is_valid:
            evidence.append(
                f"Measured over {correlation.alignment.evaluated_buckets} shared "
                f"{correlation.alignment.bucket_label} buckets spanning "
                f"{correlation.alignment.overlap_days:.1f} days"
            )
            for pair in correlation.pairs:
                if pair.pearson is None:
                    continue
                evidence.append(f"[{pair.label_a}] vs [{pair.label_b}]: {pair.note}")
                if pair.style is not None and pair.style.style_vs_pnl_conflict:
                    evidence.append(
                        f"[{pair.label_a}] vs [{pair.label_b}] (behaviour): "
                        f"{pair.style.note}"
                    )
        if joint is not None and joint.is_valid:
            evidence.append(
                f"Joint 95% VaR {joint.var_95_pct:.1f}% of "
                f"{joint.capital_at_risk:,.0f} USDT, against "
                f"{joint.sum_individual_var_95_pct:.1f}% undiversified"
                + (
                    f" -- diversification removed {joint.diversification_ratio:.0%} "
                    "of the loss tail"
                    if joint.diversification_ratio is not None
                    else ""
                )
            )
        if concentration.largest_symbol:
            evidence.append(
                f"{concentration.largest_symbol_share_pct:.0f}% of open exposure sits "
                f"in {concentration.largest_symbol}; "
                f"{concentration.directional_alignment:.0%} of the book points the "
                "same way"
            )

        warnings = list(correlation.warnings)
        warnings.extend(concentration.warnings)
        if joint is not None:
            warnings.extend(joint.warnings)
        for member in members:
            if member.excluded_reason:
                warnings.append(
                    f"[{member.label}] is not part of the correlation measurement: "
                    f"{member.excluded_reason}"
                )
            # OKX's `investAmt` is the only capital a ledger-hidden member has,
            # so on the public basis it is every member's capital. When a
            # bot's own closed-trade PnL dwarfs it, the figure is not the
            # capital that PnL was made on, and this bot's weight (and its
            # share of the joint VaR) reads low.
            if (
                member.capital_source == "OKX_INVEST_AMT"
                and not member.ledger_hidden
                and member.capital_at_risk
                and abs(member.realized_pnl) > member.capital_at_risk
            ):
                warnings.append(
                    f"[{member.label}] OKX lists {member.capital_at_risk:,.0f} USDT invested, "
                    f"but its closed trades made {member.realized_pnl:+,.0f} USDT "
                    f"({abs(member.realized_pnl) / member.capital_at_risk:.1f}x that); its "
                    "capital weight is probably understated"
                )

        if has_conflict:
            action = (
                "The offsetting PnL is not diversification: at least one pair "
                "trades the same way, so those members are likely to lose together "
                "when the regime turns"
            )
        elif verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER:
            action = (
                "The members behave as one position rather than several: their "
                "results and drawdowns overlap heavily"
            )
        elif verdict is PortfolioVerdict.MODERATE_CO_MOVEMENT:
            action = (
                "The members partly move together: drawdowns are likely to overlap, "
                "most of all in the most correlated pair"
            )
        elif verdict is PortfolioVerdict.DIVERSIFIED:
            action = (
                "The spread is real on both results and behaviour; it rests on the "
                "pair correlations staying low, not on the count of bots"
            )
        else:
            action = (
                "Not enough overlapping history yet to tell whether these bots form "
                "a diversified set"
            )

        as_of = as_of_ms or min(bot.as_of_ms for bot in bots)
        portfolio_id = "PORT_" + uuid.uuid5(
            uuid.NAMESPACE_URL, "|".join(sorted(member_codes))
        ).hex[:12].upper()
        digest = json.dumps(
            {
                "methodology": cls.METHODOLOGY_VERSION,
                "portfolio": portfolio_id,
                "combined": combined.assessment_id if combined else None,
                # Two requests over the SAME measured book are not the same
                # request when one of them also submitted a bot that turned
                # out to be concealed or unreachable: `measurement_coverage_
                # pct`, `submitted_member_count` and the verdict's own
                # confidence can all legitimately differ, and the rendered
                # page shows a different "Submitted but not measured"
                # section. Without these two in the digest, re-running the
                # same 2 measured bots with vs without a 3rd, concealed one
                # produced the IDENTICAL `assessment_id` (found live,
                # 2026-09-24) -- `PortfolioHistoryStore.append`'s own dedup
                # check ("same id -> no-op") then silently kept whichever
                # run happened to land first, discarding the other's
                # submitted-count/concealed-list forever.
                "concealed_members": sorted(concealed_members),
                # The ruler and how far each public series reached: the same
                # bots re-measured a day later on OKX's daily PnL are a new
                # measurement, not a replay of the old one.
                "pnl_basis": series.diagnostics.pnl_basis,
                "public_series": sorted(
                    (code, profiles[code].last_day_ms, profiles[code].days)
                    for code in member_codes
                    if mark_to_market and code in profiles
                ),
                "error_members": sorted(error_members),
                "members": sorted(
                    (
                        candidate.bot.identity.unique_code,
                        candidate.bot.as_of_ms,
                        candidate.bot.identity.ledger_fingerprint,
                    )
                    for candidate in candidates
                ),
            },
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=True,
        )
        assessment_id = (
            "PQC_" + uuid.uuid5(uuid.NAMESPACE_URL, digest).hex[:16].upper()
        )

        return PortfolioRiskAssessment(
            methodology_version=cls.METHODOLOGY_VERSION,
            portfolio_id=portfolio_id,
            assessment_id=assessment_id,
            timestamp=int(time.time() * 1000),
            as_of_ms=as_of,
            members=members,
            member_codes=member_codes,
            measurable_member_count=len(series.labels),
            correlation=correlation,
            joint_simulation=joint,
            concentration=concentration,
            symbol_breakdown=cls._symbol_breakdown(candidates, labels, concentration),
            book=compute_book_metrics(series, members),
            combined_bot_id=combined.bot_id if combined else None,
            combined_assessment_id=combined.assessment_id if combined else None,
            combined_risk_score=combined.risk_score if combined else None,
            combined_quality_score=combined.quality_score if combined else None,
            combined_risk_tier=combined.risk_tier.value if combined else None,
            combined_verdict=combined.verdict if combined else None,
            verdict=verdict,
            verdict_reason=reason,
            measurement_coverage_pct=coverage_pct,
            score_coverage_pct=cls._score_coverage(members, coverage_pct),
            score_member_count=sum(1 for member in members if not member.ledger_hidden),
            submitted_member_count=(
                len(members) + len(still_concealed) + len(error_members)
            ),
            concealed_member_codes=list(concealed_members),
            style_verdict=style_verdict,
            style_verdict_reason=style_reason,
            style_vs_pnl_conflict=has_conflict,
            evidence=evidence,
            warnings=warnings,
            limitations=limitations,
            recommended_action=action,
        )

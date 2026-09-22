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

import json
import time
import uuid
from dataclasses import dataclass
from typing import Dict, List, Optional, Sequence, Tuple

# (label_a, label_b, pearson, exit-rule distance) for a pair whose results look
# independent while its trading does not.
PairCorrelationConflict = Tuple[str, str, float, float]

from Agent.backend.bot.mcp.analytics.strategy.exit_rule import ExitRuleAnalyzer
from Agent.backend.bot.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.schemas import (
    CorrelationMatrix,
    ExposureConcentration,
    PairStyle,
    PortfolioMember,
    PortfolioRiskAssessment,
    PortfolioVerdict,
    StyleVerdict,
)
from Agent.backend.report.qc.portfolio.timeseries import TimeSeriesMerger
from Agent.backend.report.qc.schemas.risk_assessment import BotRiskAssessment


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
                )
            )
        return members

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
        average = correlation.average_pearson
        strongest = correlation.max_pearson
        pair = correlation.max_pearson_pair or []
        if average >= cls.HIGH_AVG_PEARSON:
            return (
                PortfolioVerdict.HIGH_CORRELATION_CLUSTER,
                f"The bots move as one: average pairwise correlation {average:+.2f} "
                f"across {len(correlation.labels)} bots. Splitting capital between "
                "them spreads the position, not the risk.",
            )
        if strongest is not None and strongest >= cls.HIGH_MAX_PEARSON:
            names = " and ".join(f"[{name}]" for name in pair) if pair else "two members"
            return (
                PortfolioVerdict.HIGH_CORRELATION_CLUSTER,
                f"Average correlation is a moderate {average:+.2f}, but {names} sit at "
                f"{strongest:+.2f} -- that pair is effectively one position held twice.",
            )
        if average >= cls.MODERATE_AVG_PEARSON:
            return (
                PortfolioVerdict.MODERATE_CO_MOVEMENT,
                f"Partial diversification: average pairwise correlation {average:+.2f}. "
                "The bots overlap in bad periods but do not track each other fully.",
            )
        return (
            PortfolioVerdict.DIVERSIFIED,
            f"Genuinely spread: average pairwise correlation {average:+.2f}, so a bad "
            "period for one member is not automatically a bad period for the others.",
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
    ) -> PortfolioRiskAssessment:
        """Build the diversification section for a set of bots.

        `combined` is the ONE assessment the portfolio report is built from
        (the ten lenses over the merged ledger). It is mirrored here for
        listings; nothing in this method recomputes or second-guesses it.
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

        series = TimeSeriesMerger.merge(bots, labels)
        exposure_by_code = {
            candidate.bot.identity.unique_code: dict(
                candidate.bot.identity.symbol_exposure_share
            )
            for candidate in candidates
        }
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

        limitations: List[str] = []
        unscored = [member for member in members if member.risk_score is None]
        if unscored:
            limitations.append(
                f"{len(unscored)} of {len(members)} members carry no individual risk "
                "score of their own; they are still inside every combined figure"
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

        if has_conflict:
            action = (
                "Do not treat the offsetting PnL as diversification: at least one "
                "pair trades the same way and will fail together when the regime "
                "turns"
            )
        elif verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER:
            action = (
                "Treat this as one position, not several: size it as a single bet "
                "and cut the overlap before adding capital"
            )
        elif verdict is PortfolioVerdict.MODERATE_CO_MOVEMENT:
            action = (
                "Usable as a set, but size it expecting the members to draw down "
                "together; the strongest pair is the one to thin first"
            )
        elif verdict is PortfolioVerdict.DIVERSIFIED:
            action = (
                "The spread is real on both results and behaviour; keep it by "
                "watching the pair correlations rather than the count of bots"
            )
        else:
            action = (
                "Collect more overlapping history before treating these bots as a "
                "diversified set"
            )

        as_of = as_of_ms or min(bot.as_of_ms for bot in bots)
        portfolio_id = "PORT_" + uuid.uuid5(
            uuid.NAMESPACE_URL, "|".join(sorted(codes))
        ).hex[:12].upper()
        digest = json.dumps(
            {
                "methodology": cls.METHODOLOGY_VERSION,
                "portfolio": portfolio_id,
                "combined": combined.assessment_id if combined else None,
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
            member_codes=codes,
            measurable_member_count=len(series.labels),
            correlation=correlation,
            joint_simulation=joint,
            concentration=concentration,
            combined_bot_id=combined.bot_id if combined else None,
            combined_assessment_id=combined.assessment_id if combined else None,
            combined_risk_score=combined.risk_score if combined else None,
            combined_quality_score=combined.quality_score if combined else None,
            combined_risk_tier=combined.risk_tier.value if combined else None,
            combined_verdict=combined.verdict if combined else None,
            verdict=verdict,
            verdict_reason=reason,
            style_verdict=style_verdict,
            style_verdict_reason=style_reason,
            style_vs_pnl_conflict=has_conflict,
            evidence=evidence,
            warnings=warnings,
            limitations=limitations,
            recommended_action=action,
        )

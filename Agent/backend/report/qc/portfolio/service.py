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
from typing import Dict, List, Optional, Sequence

from Agent.backend.bot.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.report.qc.evaluator.common import tier_for
from Agent.backend.report.qc.portfolio.correlation import CorrelationAnalyzer
from Agent.backend.report.qc.portfolio.joint_monte_carlo import JointMonteCarloEngine
from Agent.backend.report.qc.portfolio.schemas import (
    CorrelationMatrix,
    ExposureConcentration,
    PortfolioMember,
    PortfolioRiskAssessment,
    PortfolioVerdict,
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
    # Verdict bands on the AVERAGE pairwise Pearson, with a separate trip on
    # the single worst pair: a portfolio whose average is a comfortable 0.3
    # because one pair sits at 0.9 and the rest near zero is still holding one
    # doubled-up position, and an average alone cannot see it.
    MODERATE_AVG_PEARSON = 0.3
    HIGH_AVG_PEARSON = 0.6
    HIGH_MAX_PEARSON = 0.8
    # Points added to the capital-weighted member average. Each is bounded and
    # attributed in `score_adjustments`; none of them can act twice.
    CORRELATION_PENALTY_MAX = 25.0
    CONCENTRATION_PENALTY_MAX = 12.0
    DIRECTIONAL_PENALTY_MAX = 8.0
    NO_BENEFIT_PENALTY = 10.0
    NO_BENEFIT_THRESHOLD = 0.05

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
    # Entry point
    # ------------------------------------------------------------------ #

    @classmethod
    def assess_portfolio(
        cls,
        candidates: Sequence[PortfolioCandidate],
        *,
        iterations: int = JointMonteCarloEngine.DEFAULT_ITERATIONS,
        seed: Optional[int] = 42,
        as_of_ms: Optional[int] = None,
    ) -> PortfolioRiskAssessment:
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

        # ---- score -----------------------------------------------------
        scored = [member for member in members if member.risk_score is not None]
        weighted: Optional[float] = None
        limitations: List[str] = []
        if scored:
            weights = [member.capital_weight for member in scored]
            if all(weight is not None for weight in weights) and sum(weights) > 0:
                weighted = sum(
                    member.risk_score * member.capital_weight for member in scored
                ) / sum(weights)
            else:
                weighted = sum(member.risk_score for member in scored) / len(scored)
                limitations.append(
                    "Members are weighted equally because at least one has no "
                    "resolvable capital at risk; a capital-weighted average would "
                    "have required inventing that figure"
                )
        if len(scored) != len(members):
            limitations.append(
                f"{len(members) - len(scored)} of {len(members)} members carry no "
                "individual risk score, so the portfolio score rests on the rest"
            )

        adjustments: Dict[str, float] = {}
        if correlation.is_valid and correlation.average_pearson is not None:
            adjustments["correlation"] = round(
                max(0.0, correlation.average_pearson) * cls.CORRELATION_PENALTY_MAX, 2
            )
        if concentration.normalised_hhi is not None:
            adjustments["concentration"] = round(
                concentration.normalised_hhi * cls.CONCENTRATION_PENALTY_MAX, 2
            )
        if concentration.directional_alignment is not None:
            adjustments["directional_alignment"] = round(
                concentration.directional_alignment * cls.DIRECTIONAL_PENALTY_MAX, 2
            )
        if (
            joint is not None
            and joint.is_valid
            and joint.diversification_ratio is not None
            and joint.diversification_ratio < cls.NO_BENEFIT_THRESHOLD
        ):
            adjustments["no_diversification_benefit"] = cls.NO_BENEFIT_PENALTY

        portfolio_score = (
            min(100.0, max(0.0, weighted + sum(adjustments.values())))
            if weighted is not None
            else None
        )

        verdict, reason = cls._verdict(correlation)

        # ---- narrative --------------------------------------------------
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
                evidence.append(
                    f"[{pair.label_a}] vs [{pair.label_b}]: {pair.note}"
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

        if verdict is PortfolioVerdict.HIGH_CORRELATION_CLUSTER:
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
                "The spread is real; keep it by watching the pair correlations "
                "rather than the count of bots"
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
                "members": sorted(
                    (
                        candidate.bot.identity.unique_code,
                        candidate.bot.as_of_ms,
                        candidate.bot.identity.ledger_fingerprint,
                        candidate.assessment.assessment_id
                        if candidate.assessment
                        else None,
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
            member_weighted_risk_score=(
                round(weighted, 2) if weighted is not None else None
            ),
            portfolio_risk_score=(
                round(portfolio_score, 2) if portfolio_score is not None else None
            ),
            risk_tier=(
                tier_for(portfolio_score).value
                if portfolio_score is not None
                else "UNKNOWN"
            ),
            score_adjustments=adjustments,
            verdict=verdict,
            verdict_reason=reason,
            evidence=evidence,
            warnings=warnings,
            limitations=limitations,
            recommended_action=action,
        )

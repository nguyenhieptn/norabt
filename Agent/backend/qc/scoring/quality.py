"""Score how good a bot is, separately from how risky it is.

Why both numbers: the risk score answers "how much can this hurt me" and a low
one is good. It does not answer "is this bot any good" -- a bot that barely
trades and never risks anything scores safe on every dimension while earning
nothing. Ranking on risk alone put such a bot above a strong, well-run one.

Quality is read off the closed ledger and the open book together, so a record
built by holding losers cannot count as good. Anything unmeasurable contributes
nothing rather than a middling default, and `measured_on` says what was actually
used so a thin score is never mistaken for a confident one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import List, Optional

from Agent.backend.mcp.schemas.bot_result import BotResult

# Each component is scored 0-100 and carries its own weight. A component with no
# evidence drops out of both the numerator and the denominator.
WEIGHTS = {
    "profitability": 1.3,
    "consistency": 1.0,
    "drawdown_control": 1.1,
    "honesty": 1.2,
    "robustness": 0.9,
}


@dataclass
class QualityScore:
    score: Optional[float]
    components: dict = field(default_factory=dict)
    measured_on: List[str] = field(default_factory=list)
    notes: List[str] = field(default_factory=list)


def _band(value: Optional[float], stops: List[tuple]) -> Optional[float]:
    """Map a metric onto 0-100 through explicit stops, no curve fitting."""
    if value is None:
        return None
    for threshold, points in stops:
        if value >= threshold:
            return points
    return 0.0


def assess(bot: BotResult) -> QualityScore:
    perf = bot.performance
    deferred = bot.deferred_loss
    drawdown = bot.drawdown_analysis
    strategy = bot.strategy_observations

    components: dict = {}
    notes: List[str] = []

    # 1. Profitability, judged on the marked book where one exists: a profit
    # factor that only holds while the losers stay open is not profitability.
    effective_pf = deferred.marked_profit_factor
    if effective_pf is None:
        effective_pf = perf.profit_factor
    else:
        notes.append(
            f"The profit factor used for scoring is the one after closing the "
            f"open book ({effective_pf:.2f})"
        )
    components["profitability"] = _band(
        effective_pf, [(3.0, 100.0), (2.0, 85.0), (1.5, 70.0), (1.2, 55.0), (1.0, 35.0)]
    )

    # 2. Consistency: a positive expectancy per trade, and enough trades to mean it.
    if perf.trade_count >= 30 and perf.expectancy is not None:
        expectancy_points = 80.0 if perf.expectancy > 0 else 10.0
        if perf.sharpe_ratio is not None:
            expectancy_points += min(20.0, max(-20.0, perf.sharpe_ratio * 10.0))
        components["consistency"] = max(0.0, min(100.0, expectancy_points))

    # 3. Drawdown control. A capped figure is a floor, not a measurement, so it
    # cannot be read as "shallow drawdown".
    if drawdown.max_dd_pct is not None and not drawdown.max_dd_pct_capped:
        components["drawdown_control"] = _band(
            -drawdown.max_dd_pct,
            [(-5.0, 100.0), (-10.0, 85.0), (-20.0, 65.0), (-35.0, 40.0), (-60.0, 15.0)],
        )
    elif drawdown.max_dd_pct_capped:
        notes.append("Drawdown exceeds the recorded capital, so drawdown control cannot be scored")

    # 4. Honesty of the headline: how far the book moves once open positions are
    # marked. This is what separates a real record from a curated one.
    booked, marked = deferred.booked_profit_factor, deferred.marked_profit_factor
    if booked is not None and marked is not None and booked > 0:
        ratio = marked / booked
        components["honesty"] = _band(
            ratio, [(0.9, 100.0), (0.7, 80.0), (0.5, 55.0), (0.3, 30.0), (0.1, 10.0)]
        )
        if ratio < 0.5:
            notes.append(
                f"Closing the open book leaves profit factor at only {ratio:.0%} of its "
                f"value on the closed book"
            )
    elif deferred.never_realized_a_loss:
        components["honesty"] = 10.0
        notes.append("Not a single losing trade has ever been booked: the closed book is filtered")

    # 5. Robustness across market phases, when enough of the ledger could be placed.
    if strategy.phase_coverage_pct is not None and strategy.phase_coverage_pct >= 30:
        points = 100.0
        if strategy.regime_dependence_pct is not None:
            points -= max(0.0, strategy.regime_dependence_pct - 40.0)
        points -= 12.0 * len(strategy.losing_phases)
        if not strategy.tested_in_downtrend and perf.trade_count >= 20:
            points -= 25.0
        components["robustness"] = max(0.0, min(100.0, points))

    measured = {k: v for k, v in components.items() if v is not None}
    if not measured:
        return QualityScore(None, components, [], ["Not enough evidence to score"])

    total_weight = sum(WEIGHTS[k] for k in measured)
    score = sum(v * WEIGHTS[k] for k, v in measured.items()) / total_weight
    return QualityScore(round(score, 1), measured, sorted(measured), notes)

from __future__ import annotations

from Agent.backend.bot.mcp.schemas.bot_result import BotResult
from Agent.backend.report.qc.evaluator.common import available, unknown

# Below this the ledger has not been placed against enough market history to say
# anything about robustness, so the dimension abstains instead of scoring.
MIN_COVERAGE_PCT = 30.0
CONCENTRATED_PCT = 70.0
LEANING_PCT = 50.0
# A bot needs this many fills before "never traded a downtrend" means it avoided
# one rather than simply not having existed for long.
MIN_TRADES_FOR_UNTESTED = 20
BROAD_LOSS_PHASES = 3


class StrategyDriftLens:
    """How well the observed strategy holds up across market regimes.

    Why this replaced a declared-vs-observed check: OKX does not publish a
    declared strategy for any lead trader, so the old lens returned NOT_APPLICABLE
    for every bot and the whole dimension was dead weight. What is measurable from
    the public ledger is where the record was earned -- a bot whose profit comes
    from one regime, or that has never traded a downtrend, carries risk that its
    win rate hides. Declared drift is still folded in when a strategy is declared.
    """

    @staticmethod
    def evaluate(bot: BotResult):
        obs = bot.strategy_observations
        coverage = obs.phase_coverage_pct

        if coverage is None or coverage < MIN_COVERAGE_PCT:
            return unknown(
                "Strategy durability across phases",
                0.8,
                f"Only {coverage:.0f}% of trades could be placed into a market phase"
                if coverage is not None
                else "Could not place any trade into a market phase",
            )

        score = 15.0
        findings = [
            f"Placed {coverage:.0f}% of trades into a market phase; "
            f"directional bias {obs.directional_bias}, entry style {obs.entry_style}"
        ]

        dependence = obs.regime_dependence_pct
        if dependence is not None and dependence >= CONCENTRATED_PCT:
            score += 35
            findings.append(
                f"{dependence:.0f}% of gross profit comes from phase {obs.best_phase} "
                "alone: a change of market regime means losing the edge"
            )
        elif dependence is not None and dependence >= LEANING_PCT:
            score += 20
            findings.append(f"{dependence:.0f}% of gross profit is concentrated in phase {obs.best_phase}")

        if (
            bot.performance.trade_count >= MIN_TRADES_FOR_UNTESTED
            and not obs.tested_in_downtrend
        ):
            score += 25
            findings.append(
                "Not enough trades in a downtrend phase yet: the strategy has not "
                "been tested on the way down"
            )

        losing = len(obs.losing_phases)
        if losing >= BROAD_LOSS_PHASES:
            score += min(30.0, 10.0 * (losing - BROAD_LOSS_PHASES + 1))
            findings.append(
                f"Losing in {losing}/6 market phases, not just one regime"
            )

        if obs.directional_bias in ("LONG_ONLY", "SHORT_ONLY"):
            score += 15
            side = "long" if obs.directional_bias == "LONG_ONLY" else "short"
            findings.append(
                f"One-way book ({side}): the result depends on the market moving "
                "in exactly one direction"
            )

        if obs.untested_phases:
            findings.append(
                "Market phases that occurred but the bot never experienced: "
                + ", ".join(obs.untested_phases)
            )

        if obs.declared_strategy and obs.strategy_drift_score is not None:
            score += obs.strategy_drift_score * 20.0
            findings.append(
                f"Declared {obs.declared_strategy}, observed {obs.observed_profile}"
            )

        # Confidence follows how much of the ledger could actually be placed.
        return available(
            "Strategy durability across phases", score, 0.8, findings, coverage / 100.0
        )

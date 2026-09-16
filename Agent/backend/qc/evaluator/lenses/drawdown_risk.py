from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown


class DrawdownRiskLens:
    @staticmethod
    def evaluate(bot: BotResult):
        dd = bot.drawdown_analysis
        if dd.wiped_out:
            return available(
                "Drawdown Risk",
                100.0,
                1.1,
                [
                    "Weekly equity reached zero inside the observed window: this account "
                    "has already been wiped out at least once",
                    f"Maximum drawdown in currency: {dd.max_dd_abs:,.0f} USDT"
                    if dd.max_dd_abs is not None
                    else "Drawdown amount unavailable",
                ],
                0.9,
            )
        if dd.max_dd_pct is None or dd.current_dd_pct is None:
            return unknown(
                "Drawdown Risk",
                1.1,
                "No capital basis supports a percentage drawdown; only the currency "
                "amount is measurable",
            )
        score = 15.0
        findings = [
            f"Max drawdown {dd.max_dd_pct:.1f}%; current drawdown {dd.current_dd_pct:.1f}% "
            f"(basis {dd.capital_basis})"
        ]
        if dd.weekly_equity_max_dd_pct is not None:
            findings.append(
                f"Weekly equity curve drawdown {dd.weekly_equity_max_dd_pct:.1f}%"
            )
        if dd.max_dd_pct > 30:
            score += 50
        elif dd.max_dd_pct > 15:
            score += 25
        if dd.current_dd_pct > 10:
            score += 25
        if dd.loss_clustering_index is not None and dd.loss_clustering_index > 0.35:
            score += 20
            findings.append(f"Loss clustering {dd.loss_clustering_index:.2f}")
        if dd.time_underwater_hours is not None:
            findings.append(
                f"Longest observed underwater duration {dd.time_underwater_hours:.1f} hours"
            )
        return available("Drawdown Risk", score, 1.1, findings, 0.7)

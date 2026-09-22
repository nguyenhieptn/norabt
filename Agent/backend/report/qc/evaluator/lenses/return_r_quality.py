from __future__ import annotations

from Agent.backend.bot.mcp.schemas.bot_result import BotResult, RiskMeasurementMode
from Agent.backend.report.qc.evaluator.common import available, unknown


class ReturnRQualityLens:
    @staticmethod
    def evaluate(bot: BotResult):
        if not bot.trade_ledger_summary:
            return unknown("Return / R quality", 0.9, "No trade results available")
        mode = bot.data_quality.measurement_mode
        stats = bot.trade_statistics
        findings = [
            f"Measurement mode: {mode.value}; return basis: {stats.return_basis}"
        ]
        score = 20.0
        confidence = 1.0
        if mode == RiskMeasurementMode.LIMITED:
            score += 20.0
            confidence = 0.4
            findings.append(
                "Only absolute PnL could be analyzed; normalised return and R are unavailable"
            )
        elif mode == RiskMeasurementMode.PARTIAL:
            confidence = 0.75
            findings.append("Normalised return is available; no R relative to initial risk")
        elif stats.mean_r_multiple is not None:
            findings.append(f"Average R: {stats.mean_r_multiple:.2f}R")
            if stats.mean_r_multiple <= 0:
                score += 35.0

        negative_tails = [
            trade
            for trade in bot.trade_ledger_summary
            if trade.realized_pnl_pct is not None and trade.realized_pnl_pct < -20.0
        ]
        if negative_tails:
            score += min(40.0, 10.0 + len(negative_tails) * 5.0)
            findings.append(
                f"{len(negative_tails)} trades have a normalised return below -20%"
            )
        if stats.pnl_skew is not None and stats.pnl_skew < -1.0:
            score += 15.0
            findings.append(f"PnL distribution is negatively skewed ({stats.pnl_skew:.2f})")
        return available("Return / R quality", score, 0.9, findings, confidence)

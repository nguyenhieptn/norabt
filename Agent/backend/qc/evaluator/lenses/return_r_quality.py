from __future__ import annotations

from Agent.backend.mcp.schemas.bot_result import BotResult, RiskMeasurementMode
from Agent.backend.qc.evaluator.common import available, unknown


class ReturnRQualityLens:
    @staticmethod
    def evaluate(bot: BotResult):
        if not bot.trade_ledger_summary:
            return unknown("Return / R Quality", 0.9, "No trade outcomes are available")
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
                "Only absolute PnL analysis is valid; normalized return and R are unavailable"
            )
        elif mode == RiskMeasurementMode.PARTIAL:
            confidence = 0.75
            findings.append(
                "Normalized returns are available; initial-risk R is unavailable"
            )
        elif stats.mean_r_multiple is not None:
            findings.append(f"Mean R multiple: {stats.mean_r_multiple:.2f}R")
            if stats.mean_r_multiple <= 0:
                score += 35.0

        negative_tails = [
            trade
            for trade in bot.trade_ledger_summary
            if trade.realized_pnl_pct is not None and trade.realized_pnl_pct < -20.0
        ]
        if negative_tails:
            score += min(40.0, 10.0 + len(negative_tails) * 5.0)
            findings.append(f"{len(negative_tails)} normalized returns below -20%")
        if stats.pnl_skew is not None and stats.pnl_skew < -1.0:
            score += 15.0
            findings.append(
                f"Negatively skewed PnL distribution ({stats.pnl_skew:.2f})"
            )
        return available("Return / R Quality", score, 0.9, findings, confidence)

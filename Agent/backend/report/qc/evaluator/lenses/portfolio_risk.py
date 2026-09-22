from __future__ import annotations

from typing import List, Optional

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.bot.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.report.qc.evaluator.common import available, unknown


class PortfolioRiskLens:
    @staticmethod
    def evaluate(
        market: Optional[MarketResult],
        bot: BotResult,
        portfolio_bots: Optional[List[BotResult]] = None,
    ):
        if not portfolio_bots:
            return unknown(
                "Portfolio risk",
                0.8,
                "No multi-bot portfolio snapshot to compare against yet",
            )
        active = [
            item
            for item in portfolio_bots
            if item.current_state.current_position_side
            not in (PositionSide.FLAT, PositionSide.UNKNOWN)
        ]
        if not active:
            return available(
                "Portfolio risk",
                5.0,
                0.8,
                ["The portfolio has no open directional exposure"],
            )
        known = [
            item for item in active if item.current_state.current_notional is not None
        ]
        if len(known) != len(active):
            return unknown(
                "Portfolio risk",
                0.8,
                "One or more active bots are missing a notional value",
            )
        gross = sum(item.current_state.current_notional or 0.0 for item in known)
        signed = []
        by_asset = {}
        for item in known:
            notional = item.current_state.current_notional or 0.0
            sign = (
                -1.0
                if item.current_state.current_position_side == PositionSide.SHORT
                else 1.0
            )
            signed.append(sign * notional)
            by_asset[item.identity.symbol] = (
                by_asset.get(item.identity.symbol, 0.0) + notional
            )
        directional = abs(sum(signed)) / max(gross, 1e-12)
        concentration = max(by_asset.values()) / max(gross, 1e-12)
        score = 15.0 + directional * 35.0 + concentration * 25.0
        findings = [
            f"Gross exposure ${gross:,.0f}; directional concentration {directional:.0%}; "
            f"largest asset {concentration:.0%}"
        ]
        return available("Portfolio risk", score, 0.8, findings)

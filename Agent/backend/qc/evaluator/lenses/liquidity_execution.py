from __future__ import annotations

from typing import Optional

from Agent.backend.market.schemas.market_result import LiquidityStateEnum, MarketResult
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown


class LiquidityExecutionLens:
    """Can the bot exit its position into the depth this market actually has?"""

    @staticmethod
    def evaluate(market: Optional[MarketResult], bot: BotResult):
        state = bot.current_state
        if state.open_positions_count == 0:
            return available(
                "Liquidity / Execution Risk",
                5.0,
                0.9,
                ["No open position requires execution"],
            )
        if market is None:
            return unknown(
                "Liquidity / Execution Risk",
                0.9,
                "No order-book observation exists for the instrument this bot trades",
            )
        depth = market.liquidity_state.total_depth_02_usd
        if market.liquidity_state.state_tier == LiquidityStateEnum.UNKNOWN or not depth:
            return unknown(
                "Liquidity / Execution Risk",
                0.9,
                f"No depth evidence collected for {market.symbol}",
            )

        attributed = state.exposure_by_symbol.get(market.symbol)
        confidence = 1.0
        findings = []
        if attributed is not None:
            notional = attributed
            inferred = [
                p
                for p in state.open_positions
                if p.symbol == market.symbol and p.attribution_source == "INFERRED"
            ]
            if inferred:
                confidence = 0.75
                findings.append(
                    f"{market.symbol} exposure {notional:,.0f} USDT, of which "
                    f"{len(inferred)} position(s) attributed by implied price move"
                )
            else:
                findings.append(
                    f"{market.symbol} exposure {notional:,.0f} USDT attributed from "
                    f"published instrument ids"
                )
        elif state.gross_exposure:
            notional = state.gross_exposure
            confidence = 0.5
            findings.append(
                f"Positions are unattributed; using full gross exposure "
                f"{notional:,.0f} USDT as the worst case"
            )
        else:
            return unknown(
                "Liquidity / Execution Risk",
                0.9,
                "Position notional is unavailable",
            )

        share = notional / depth * 100.0
        findings.append(
            f"Position is {share:.1f}% of ±0.2% book depth ({depth:,.0f} USDT, "
            f"{market.liquidity_state.state_tier.value})"
        )
        score = 15.0
        if market.liquidity_state.state_tier in (
            LiquidityStateEnum.THIN,
            LiquidityStateEnum.ILLIQUID,
        ):
            score += 35
        if share > 100:
            score += 60
            findings.append("Exit size exceeds the whole visible book at ±0.2%")
        elif share > 15:
            score += 45
        elif share > 5:
            score += 20
        return available("Liquidity / Execution Risk", score, 0.9, findings, confidence)

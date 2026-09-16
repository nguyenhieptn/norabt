from __future__ import annotations

from typing import Optional

from Agent.backend.market.schemas.market_result import (
    MarketResult,
    TrendState,
    VolatilityState,
)
from Agent.backend.mcp.schemas.bot_result import BotResult, PositionSide
from Agent.backend.qc.evaluator.common import available, unknown

CONFLICT = {
    PositionSide.LONG: (TrendState.BEARISH, TrendState.BREAKOUT_BEAR),
    PositionSide.SHORT: (TrendState.BULLISH, TrendState.BREAKOUT_BULL),
}


class MarketAlignmentLens:
    """Is the bot positioned against the market it is actually trading?"""

    @staticmethod
    def evaluate(market: Optional[MarketResult], bot: BotResult):
        state = bot.current_state
        if state.open_positions_count == 0:
            return available(
                "Market Alignment",
                5.0,
                1.2,
                ["No open position; no directional conflict"],
            )
        if market is None:
            return unknown(
                "Market Alignment",
                1.2,
                "No market observation exists for the instrument this bot trades",
            )
        trend = market.structure_state.trend_state
        if trend == TrendState.UNKNOWN:
            return unknown("Market Alignment", 1.2, "Market trend is unavailable")

        attributed = [
            position
            for position in state.open_positions
            if position.symbol == market.symbol
            and position.side in (PositionSide.LONG, PositionSide.SHORT)
        ]
        findings = []
        inferred = [p for p in attributed if p.attribution_source == "INFERRED"]
        confidence = 1.0
        if attributed and inferred:
            confidence = 0.75
            findings.append(
                f"{len(inferred)}/{len(attributed)} position(s) on {market.symbol} were "
                f"attributed by implied price move, not a published instId"
            )

        if attributed:
            long_notional = sum(
                p.notional or 0.0 for p in attributed if p.side == PositionSide.LONG
            )
            short_notional = sum(
                p.notional or 0.0 for p in attributed if p.side == PositionSide.SHORT
            )
            net_side = (
                PositionSide.LONG
                if long_notional >= short_notional
                else PositionSide.SHORT
            )
            exposure = max(long_notional, short_notional)
            findings.append(
                f"{len(attributed)} position(s) attributed to {market.symbol}: "
                f"net {net_side.value} {exposure:,.0f} USDT"
            )
            share = exposure / state.gross_exposure if state.gross_exposure else None
            if share is not None:
                findings.append(
                    f"{market.symbol} is {share:.0%} of the bot's gross exposure"
                )
        elif state.unknown_positions_count and state.current_position_side in (
            PositionSide.LONG,
            PositionSide.SHORT,
            PositionSide.NET,
        ):
            net_side = state.current_position_side
            confidence = 0.5
            findings.append(
                f"Positions carry no instrument id; judged on portfolio direction "
                f"({net_side.value}) against {market.symbol}"
            )
        else:
            return unknown(
                "Market Alignment",
                1.2,
                f"No open position can be attributed to {market.symbol}",
            )

        score = 20.0
        findings.append(f"Market trend {trend.value}")
        if net_side == PositionSide.NET:
            score += 10.0
            findings.append(
                "Bot holds both directions; net directional risk partly offset"
            )
        elif trend in CONFLICT.get(net_side, ()):
            score += 45.0
            findings.append(
                f"Position {net_side.value} conflicts with a {trend.value} market"
            )
            if market.structure_state.volatility_state in (
                VolatilityState.EXPANDING,
                VolatilityState.EXTREME,
            ):
                score += 20.0
                findings.append("Expanding volatility amplifies the conflict")
            if (state.current_leverage or 0.0) > 10.0:
                score += 15.0
                findings.append(
                    f"Leverage {state.current_leverage:.0f}x amplifies the conflict"
                )
        else:
            score -= 10.0
            findings.append("Position direction agrees with the market trend")
        return available("Market Alignment", score, 1.2, findings, confidence)

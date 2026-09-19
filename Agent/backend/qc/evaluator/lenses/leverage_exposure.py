from __future__ import annotations

from typing import Optional

from Agent.backend.market.schemas.market_result import MarketResult
from Agent.backend.mcp.schemas.bot_result import BotResult
from Agent.backend.qc.evaluator.common import available, unknown


class LeverageExposureLens:
    """Leverage and exposure, separating real leverage from an unreliable capital base."""

    @staticmethod
    def evaluate(market: Optional[MarketResult], bot: BotResult):
        state = bot.current_state
        if state.open_positions_count == 0:
            return available(
                "Leverage / exposure", 5.0, 1.1, ["No open exposure"]
            )
        if state.current_leverage is None and state.gross_exposure is None:
            return unknown(
                "Leverage / exposure",
                1.1,
                "No leverage or exposure data for the open position",
            )

        score = 15.0
        findings = []
        confidence = 1.0

        if state.current_leverage is not None:
            findings.append(f"Highest position leverage {state.current_leverage:.0f}x")
            if state.current_leverage > 20:
                score += 45
            elif state.current_leverage > 10:
                score += 25
        else:
            confidence = 0.7
            findings.append("No per-position leverage available")

        if state.gross_exposure is not None:
            detail = f"Gross exposure {state.gross_exposure:,.0f} USDT"
            if state.net_exposure is not None:
                detail += f", net {state.net_exposure:,.0f} USDT"
            findings.append(detail)

        if state.capital_consistency == "MARGIN_EXCEEDS_CAPITAL":
            score += 35
            confidence = min(confidence, 0.5)
            findings.append(
                f"Margin used {state.used_margin:,.0f} USDT exceeds the declared capital "
                f"{state.reference_capital:,.0f} USDT — either the declared capital is "
                f"wrong, or the account has exceeded its margin capacity; either way "
                f"this needs clarifying"
            )
        elif (
            state.margin_ratio is not None or state.margin_to_reference_pct is not None
        ):
            ratio = (
                state.margin_ratio
                if state.margin_ratio is not None
                else state.margin_to_reference_pct
            )
            label = (
                "margin/current capital"
                if state.margin_ratio is not None
                else "margin/reference capital"
            )
            findings.append(f"Observed {label} ratio {ratio:.1f}%")
            if ratio > 50:
                score += 35
            elif ratio > 30:
                score += 15
        else:
            confidence = min(confidence, 0.7)
            findings.append("No margin usage available")

        if state.unrealized_pnl is not None and state.unrealized_pnl < 0:
            findings.append(
                f"Unrealised loss on the open position: {state.unrealized_pnl:,.0f} USDT"
            )
            if (
                state.gross_exposure
                and abs(state.unrealized_pnl) / state.gross_exposure > 0.02
            ):
                score += 15

        if (
            state.liquidation_distance_pct is not None
            and state.liquidation_distance_pct < 5
        ):
            score += 40
            findings.append(
                f"Distance to liquidation price is only {state.liquidation_distance_pct:.1f}%"
            )
        if state.unknown_positions_count:
            confidence = min(confidence, 0.6)
            findings.append(
                f"{state.unknown_positions_count} positions carry no instrument code"
            )
        return available("Leverage / exposure", score, 1.1, findings, confidence)

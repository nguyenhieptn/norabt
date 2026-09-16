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
            return available("Leverage / Exposure Risk", 5.0, 1.1, ["No open exposure"])
        if state.current_leverage is None and state.gross_exposure is None:
            return unknown(
                "Leverage / Exposure Risk",
                1.1,
                "Open-position leverage and exposure are unavailable",
            )

        score = 15.0
        findings = []
        confidence = 1.0

        if state.current_leverage is not None:
            findings.append(f"Maximum position leverage {state.current_leverage:.0f}x")
            if state.current_leverage > 20:
                score += 45
            elif state.current_leverage > 10:
                score += 25
        else:
            confidence = 0.7
            findings.append("Per-position leverage is unavailable")

        if state.gross_exposure is not None:
            detail = f"Gross exposure {state.gross_exposure:,.0f} USDT"
            if state.net_exposure is not None:
                detail += f", net {state.net_exposure:,.0f} USDT"
            findings.append(detail)

        if state.capital_consistency == "MARGIN_EXCEEDS_CAPITAL":
            score += 35
            confidence = min(confidence, 0.5)
            findings.append(
                f"Committed margin {state.used_margin:,.0f} USDT exceeds reported capital "
                f"{state.reference_capital:,.0f} USDT — either the capital figure is wrong "
                f"or the account is beyond its margin capacity; both need resolving"
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
                "margin/current-equity"
                if state.margin_ratio is not None
                else "margin/capital-reference"
            )
            findings.append(f"Observed {label} ratio {ratio:.1f}%")
            if ratio > 50:
                score += 35
            elif ratio > 30:
                score += 15
        else:
            confidence = min(confidence, 0.7)
            findings.append("Margin utilization is unavailable")

        if state.unrealized_pnl is not None and state.unrealized_pnl < 0:
            findings.append(
                f"Unrealized loss carried on open positions: {state.unrealized_pnl:,.0f} USDT"
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
                f"Liquidation distance is only {state.liquidation_distance_pct:.1f}%"
            )
        if state.unknown_positions_count:
            confidence = min(confidence, 0.6)
            findings.append(
                f"{state.unknown_positions_count} position(s) lack an instrument id"
            )
        return available("Leverage / Exposure Risk", score, 1.1, findings, confidence)

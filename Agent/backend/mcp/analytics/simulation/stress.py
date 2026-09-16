from __future__ import annotations

from typing import List, Optional

from Agent.backend.mcp.schemas.bot_result import StressTestResults, TradeLedgerItem


class StressSimulator:
    """Apply transparent stress assumptions to the observed ledger."""

    @staticmethod
    def run_stress(
        trades: List[TradeLedgerItem], total_equity: Optional[float]
    ) -> StressTestResults:
        if not trades or total_equity is None or total_equity <= 0:
            return StressTestResults(
                stress_survival_verdict="UNKNOWN",
                is_valid=False,
                warnings=["Trades and positive reference equity are required"],
            )

        known_notionals = [
            trade.notional for trade in trades if trade.notional is not None
        ]
        if len(known_notionals) != len(trades):
            return StressTestResults(
                volatility_2x_pnl_impact=-0.5
                * abs(sum(t.realized_pnl for t in trades if t.realized_pnl < 0)),
                stress_survival_verdict="UNKNOWN",
                is_valid=False,
                warnings=[
                    "Notional is missing for one or more trades; execution stress cannot be calculated"
                ],
            )

        total_pnl = sum(trade.realized_pnl for trade in trades)
        total_notional = sum(known_notionals)
        loss_sum = abs(
            sum(trade.realized_pnl for trade in trades if trade.realized_pnl < 0)
        )
        volatility_impact = -loss_sum * 0.5
        spread_impact = -total_notional * 0.001
        liquidity_impact = -total_notional * 0.0015
        stressed_equity = (
            total_equity
            + total_pnl
            + volatility_impact
            + spread_impact
            + liquidity_impact
        )
        stressed_return = (stressed_equity - total_equity) / total_equity
        verdict = (
            "LIQUIDATED"
            if stressed_equity <= 0
            else "VULNERABLE"
            if stressed_return < -0.30
            else "SURVIVED"
        )
        return StressTestResults(
            volatility_2x_pnl_impact=volatility_impact,
            spread_3x_slippage_impact=spread_impact,
            liquidity_half_exit_impact=liquidity_impact,
            stress_survival_verdict=verdict,
            is_valid=True,
        )

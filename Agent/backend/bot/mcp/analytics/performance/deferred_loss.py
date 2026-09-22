from __future__ import annotations

from typing import List, Optional, Sequence

from Agent.backend.bot.mcp.schemas.bot_result import (
    DeferredLossProfile,
    OpenPosition,
    TradeLedgerItem,
)


class DeferredLossAnalyzer:
    """Mark the open book to market and recompute the headline metrics."""

    # What matters is not how far the number moves but whether the conclusion
    # drawn from it changes. A profit factor of 41 falling to 10 still says
    # "sustainable"; one of 11 falling to 0.16 says the opposite.
    PF_BANDS = ((1.0, "LOSING"), (1.3, "FRAGILE"))
    SUSTAINABLE = "SUSTAINABLE"
    IMMATERIAL_CAPITAL_PCT = 1.0
    MATERIAL_CAPITAL_PCT = 10.0

    @classmethod
    def profit_factor_band(cls, profit_factor: Optional[float]) -> str:
        """A profit factor read as a verdict, not a number."""
        if profit_factor is None:
            # No loss was ever booked, so the record reads as flawless.
            return cls.SUSTAINABLE
        for ceiling, name in cls.PF_BANDS:
            if profit_factor < ceiling:
                return name
        return cls.SUSTAINABLE

    @classmethod
    def _band_rank(cls, band: str) -> int:
        return {"LOSING": 0, "FRAGILE": 1, cls.SUSTAINABLE: 2}[band]

    @classmethod
    def analyze(
        cls,
        trades: Sequence[TradeLedgerItem],
        positions: Sequence[OpenPosition],
        net_unrealized: Optional[float],
        capital_at_risk: Optional[float],
    ) -> DeferredLossProfile:
        realized = sum(trade.realized_pnl for trade in trades)
        wins = [t for t in trades if t.realized_pnl > 0]
        closed_losses = [t for t in trades if t.realized_pnl < 0]
        gross_profit = sum(t.realized_pnl for t in wins)
        gross_loss = abs(sum(t.realized_pnl for t in closed_losses))

        marked = [p.unrealized_pnl for p in positions if p.unrealized_pnl is not None]
        coverage = len(marked) / len(positions) if positions else 1.0
        losing = [value for value in marked if value < 0]
        winning = [value for value in marked if value > 0]

        if marked:
            open_loss = abs(sum(losing)) if losing else 0.0
        elif net_unrealized is not None:
            open_loss = abs(net_unrealized) if net_unrealized < 0 else 0.0
        else:
            open_loss = None

        booked_pf = gross_profit / gross_loss if gross_loss > 0 else None
        booked_win_rate = len(wins) / len(trades) * 100.0 if trades else None

        marked_pf = marked_win_rate = marked_total = None
        if marked or open_loss is not None:
            open_gain = sum(winning) if marked else 0.0
            marked_gross_profit = gross_profit + open_gain
            marked_gross_loss = gross_loss + (open_loss or 0.0)
            marked_pf = (
                marked_gross_profit / marked_gross_loss
                if marked_gross_loss > 0
                else None
            )
            total_events = len(trades) + (len(marked) if marked else 0)
            if total_events:
                marked_win_rate = (len(wins) + len(winning)) / total_events * 100.0
            marked_total = realized + (
                sum(marked) if marked else (net_unrealized or 0.0)
            )

        ratio_to_loss = (
            open_loss / gross_loss if open_loss is not None and gross_loss > 0 else None
        )
        capital_pct = (
            open_loss / capital_at_risk * 100.0
            if open_loss is not None and capital_at_risk
            else None
        )
        never_realized_a_loss = bool(trades) and not closed_losses

        warnings: List[str] = []
        representativeness = cls._classify(
            trades=trades,
            positions=positions,
            open_loss=open_loss,
            capital_pct=capital_pct,
            booked_pf=booked_pf,
            marked_pf=marked_pf,
            never_realized_a_loss=never_realized_a_loss,
            warnings=warnings,
        )

        if representativeness in ("PARTIAL", "UNREPRESENTATIVE"):
            if booked_pf is not None and marked_pf is not None:
                warnings.append(
                    f"Profit factor falls from {booked_pf:.2f} to {marked_pf:.2f} once the "
                    f"{open_loss:,.0f} USDT of open loss is booked"
                )
            elif marked_pf is not None:
                warnings.append(
                    f"No loss was ever booked, so profit factor is undefined; marking the "
                    f"open book gives {marked_pf:.2f}"
                )
            if capital_pct is not None and capital_pct >= cls.MATERIAL_CAPITAL_PCT:
                warnings.append(
                    f"Open loss is {capital_pct:.1f}% of the capital at risk"
                )
        if positions and coverage < 1.0:
            warnings.append(
                f"Only {coverage:.0%} of open positions publish an unrealised PnL, so the "
                f"marked figures are a lower bound"
            )

        return DeferredLossProfile(
            realized_pnl=realized,
            unrealized_pnl=net_unrealized,
            open_loss=open_loss,
            gross_realized_profit=gross_profit,
            gross_realized_loss=gross_loss,
            open_loss_to_realized_loss=ratio_to_loss,
            open_loss_to_capital_pct=capital_pct,
            booked_profit_factor=booked_pf,
            marked_profit_factor=marked_pf,
            booked_win_rate=booked_win_rate,
            marked_win_rate=marked_win_rate,
            marked_total_pnl=marked_total,
            mark_coverage=coverage,
            closed_loss_count=len(closed_losses),
            losing_open_positions=len(losing),
            never_realized_a_loss=never_realized_a_loss,
            representativeness=representativeness,
            warnings=warnings,
        )

    @classmethod
    def _classify(
        cls,
        *,
        trades,
        positions,
        open_loss,
        capital_pct,
        booked_pf,
        marked_pf,
        never_realized_a_loss,
        warnings: List[str],
    ) -> str:
        if not trades:
            warnings.append(
                "No closed trade exists, so there are no realised metrics to distort"
            )
            return "NO_CLOSED_TRADES"
        if not positions or not open_loss:
            return "REPRESENTATIVE"
        if open_loss is None:
            warnings.append(
                "Unrealised PnL is unavailable, so the closed-trade metrics cannot be "
                "checked against the open book"
            )
            return "UNKNOWN"
        if capital_pct is not None and capital_pct < cls.IMMATERIAL_CAPITAL_PCT:
            return "REPRESENTATIVE"

        if marked_pf is None:
            return "PARTIAL"

        booked_band = cls.profit_factor_band(booked_pf)
        marked_band = cls.profit_factor_band(marked_pf)
        downgraded = cls._band_rank(marked_band) < cls._band_rank(booked_band)

        if downgraded:
            warnings.append(
                f"Booking the open loss moves the record from {booked_band} to "
                f"{marked_band}"
            )
            return "UNREPRESENTATIVE"
        if never_realized_a_loss:
            warnings.append(
                f"No closed trade ever realised a loss while open positions carry "
                f"{open_loss:,.0f} USDT of loss: the win rate describes only the trades "
                f"the bot chose to close"
            )
            return "PARTIAL"
        if capital_pct is not None and capital_pct >= cls.MATERIAL_CAPITAL_PCT:
            # The verdict holds, but the unbooked amount is material to the account.
            return "PARTIAL"
        return "REPRESENTATIVE"
